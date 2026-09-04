"""Properties of the schemas themselves, checked mechanically.

Everything here is a rule that would otherwise live in a review checklist, and a
rule that only works because someone remembers it is a defect.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_FILES = sorted((ROOT / "schemas").rglob("*.json"))
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# The three angle-stream payloads each carry their own copy of the `link` object
# so that every payload schema stands alone for a generator and for a
# firmware-adjacent reader. The copies are allowed; drifting apart is not.
LINK_CARRIERS = (
    "angle-stream/frame-heartbeat.json",
    "angle-stream/frame-inclination.json",
    "angle-stream/frame-theta.json",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text())


@pytest.mark.parametrize("path", SCHEMA_FILES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_schema_is_valid_2020_12(path: Path) -> None:
    jsonschema.Draft202012Validator.check_schema(load(path))


@pytest.mark.parametrize("path", SCHEMA_FILES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_schema_declares_an_id_and_an_x_version(path: Path) -> None:
    schema = load(path)
    assert isinstance(schema.get("$id"), str) and schema["$id"], "every contract needs a $id"
    version = schema.get("x-version")
    assert isinstance(version, str) and SEMVER.match(version), (
        "x-version is the number that decides compatibility between builds; it is required "
        "and it is semver."
    )


def test_ids_are_unique() -> None:
    ids = [load(path)["$id"] for path in SCHEMA_FILES]
    assert len(set(ids)) == len(ids)


def test_angle_stream_link_copies_are_identical() -> None:
    """The `link` sub-object is duplicated on purpose; it must not drift."""
    copies = {
        name: load(ROOT / "schemas" / name)["properties"]["link"] for name in LINK_CARRIERS
    }
    reference = copies[LINK_CARRIERS[0]]
    for name, copy in copies.items():
        assert copy == reference, (
            f"schemas/{name}'s `link` has drifted from schemas/{LINK_CARRIERS[0]}'s. "
            "The duplication is deliberate; the divergence is not."
        )


def test_each_schema_is_closed_or_open_on_purpose() -> None:
    """Two different answers to `additionalProperties`, each on purpose.

    CLOSED (`false`) is for a wire that carries an instruction:

    * The **device** schemas own both ends -- the firmware writes them and the
      host reads them -- so an unexpected key is a bug and is rejected.
    * The **plan channel** carries a plan that moves a laser and a readout in
      front of an operator. A key the receiver does not understand is a part of
      the plan it would silently drop, and half a plan applied is worse than no
      plan applied. The cost is an ordered rollout (bump the receiver's pin
      before the sender emits a new field), which is ADR-0003's to state.

    OPEN (`true`) is for read-only telemetry: the angle stream and the tracker
    hello are read by clients deployed on a different schedule from their
    servers, and both servers state that additive optional fields do NOT bump
    the protocol version. A strict reader there would reject a peer that is, by
    its own contract, compatible.

    The list is by directory rather than per file, so a new schema in either
    place inherits its neighbours' answer and a new *directory* has to come
    here and say which it is.
    """
    closed_dirs = ("device/", "plan-channel/")
    seen_closed = seen_open = 0
    for path in SCHEMA_FILES:
        schema = load(path)
        relative = path.relative_to(ROOT / "schemas").as_posix()
        if relative.startswith(closed_dirs):
            assert schema.get("additionalProperties") is False, relative
            seen_closed += 1
        else:
            assert schema.get("additionalProperties") is True, relative
            seen_open += 1
    # A prefix tuple that stopped matching anything would leave this test green
    # while checking one half of its own point.
    assert seen_closed and seen_open


def test_envelope_then_branches_only_pin_constants() -> None:
    """A `then` may pin a sibling of `payload`, and only to a string const.

    `tools/bundle.mjs` carries exactly that into the generated types and
    validators -- it is how the plan-channel envelope binds `kind` to `type`.
    Anything richer would be a constraint the schema states and the generated
    validators drop, which is the failure mode this repository refuses. Checked
    here as well as there so the rule does not live in one language.
    """
    for path in SCHEMA_FILES:
        for branch in load(path).get("allOf") or []:
            for key, value in branch["then"]["properties"].items():
                if key == "payload":
                    continue
                assert set(value) <= {"const", "description", "$comment"}, f"{path}: {key}"
                assert isinstance(value["const"], str), f"{path}: {key}"


def test_plan_channel_binds_direction_to_message_type() -> None:
    """`kind` is pinned per `type`, so an answer cannot wear a request's type.

    Without it a receiver dispatching on `type` alone would take a `plan_ack`
    labelled `req` for a command, and a request/response channel whose two
    halves are interchangeable is not one.
    """
    envelope = load(ROOT / "schemas" / "plan-channel" / "envelope.json")
    pinned = {
        branch["if"]["properties"]["type"]["const"]: branch["then"]["properties"]["kind"]["const"]
        for branch in envelope["allOf"]
    }
    assert pinned == {"plan": "req", "plan_ack": "res"}
    assert sorted(envelope["properties"]["kind"]["enum"]) == sorted(set(pinned.values()))


def test_every_envelope_branch_has_a_payload_schema() -> None:
    """`type` may not offer a value that no `allOf` branch gives a payload."""
    by_id = {load(path)["$id"]: path for path in SCHEMA_FILES}
    for path in SCHEMA_FILES:
        schema = load(path)
        branches = schema.get("allOf")
        if not branches:
            continue
        declared = schema["properties"]["type"]["enum"]
        covered = []
        for branch in branches:
            (key,) = branch["if"]["properties"].keys()
            assert key == "type", f"{path}: discriminates on {key}, not type"
            covered.append(branch["if"]["properties"]["type"]["const"])
            ref = branch["then"]["properties"]["payload"]["$ref"]
            assert ref in by_id, f"{path}: payload $ref {ref} names no schema"
        assert sorted(covered) == sorted(declared), path


def test_the_enum_order_gate_sees_every_schema_directory() -> None:
    """`tools/check-enum-order.py` finds schemas by glob, so this stays true.

    Enum order is load-bearing (the generated C enum's value IS the array
    index), and the gate that protects it walks `schemas/` itself rather than a
    list. A narrowed glob, or a contract parked outside `schemas/`, would leave
    the gate green while gating nothing -- and it already reports "nothing
    checked" as a PASS when there is no tag to compare against, so a quiet loss
    of coverage looks exactly like a healthy run.
    """
    spec = importlib.util.spec_from_file_location(
        "check_enum_order", ROOT / "tools" / "check-enum-order.py"
    )
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)

    covered = sorted(gate.SCHEMA_DIR.rglob("*.json"))
    assert covered == SCHEMA_FILES

    envelope = ROOT / "schemas" / "plan-channel" / "envelope.json"
    found = gate.enums_of(load(envelope))
    assert found["/properties/kind"] == ["req", "res"]
    assert found["/properties/type"] == ["plan", "plan_ack"]
    assert gate.enums_of(load(ROOT / "schemas" / "plan-channel" / "payload-plan-ack.json"))[
        "/properties/result"
    ] == ["applied", "pending_confirm", "rejected"]


def test_generated_artifacts_exist() -> None:
    """gen/ is committed, so a missing file means someone deleted it by hand."""
    for relative in (
        "gen/ts/types.ts",
        "gen/ts/zod.ts",
        "gen/ts/constants.ts",
        "gen/ts/angles.ts",
        "gen/ts/index.ts",
        "gen/py/needle_protocol/models.py",
        "gen/py/needle_protocol/constants.py",
        "gen/py/needle_protocol/angles.py",
        "gen/py/needle_protocol/__init__.py",
        "gen/c/schema_keys.h",
    ):
        assert (ROOT / relative).is_file(), relative


def test_generated_files_say_they_are_generated() -> None:
    for relative in ("gen/ts/types.ts", "gen/py/needle_protocol/models.py", "gen/c/schema_keys.h"):
        assert "DO NOT EDIT" in (ROOT / relative).read_text(), relative


def test_c_header_carries_every_device_x_version() -> None:
    header = (ROOT / "gen" / "c" / "schema_keys.h").read_text()
    for path in SCHEMA_FILES:
        relative = path.relative_to(ROOT / "schemas").as_posix()
        if not relative.startswith("device/"):
            continue
        macro = "SCHEMA_" + re.sub(r"[^A-Za-z0-9]+", "_", relative[: -len(".json")]).upper() + "_XVERSION"
        assert f'#define {macro} "{load(path)["x-version"]}"' in header, macro


def test_status_sample_reports_the_current_envelope_x_version() -> None:
    """The sample's `envelope_schema_version` must BE the envelope's x-version.

    The field exists so a host can read which envelope contract a firmware was
    built against. A sample carrying a stale number still parses -- the schema
    only constrains the shape -- so nothing but this would notice that the two
    had drifted apart, and the one fixture consumers copy their expectations
    from would be quietly wrong.
    """
    envelope = load(ROOT / "schemas" / "device" / "envelope.json")
    samples = json.loads((ROOT / "tests" / "samples.json").read_text())
    carriers = [
        sample
        for sample in samples["valid"]
        if sample["contract"] == "DeviceEnvelope"
        and "envelope_schema_version" in sample["frame"].get("payload", {})
    ]
    assert carriers, (
        "no valid sample exercises envelope_schema_version, so the field ships "
        "with no evidence that a real frame carrying it parses"
    )
    for sample in carriers:
        assert sample["frame"]["payload"]["envelope_schema_version"] == envelope["x-version"], (
            f"{sample['name']} reports envelope x-version "
            f"{sample['frame']['payload']['envelope_schema_version']}, but "
            f"schemas/device/envelope.json is at {envelope['x-version']}."
        )

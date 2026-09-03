"""Properties of the schemas themselves, checked mechanically.

Everything here is a rule that would otherwise live in a review checklist, and a
rule that only works because someone remembers it is a defect.
"""

from __future__ import annotations

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


def test_device_schemas_are_closed_and_host_schemas_are_open() -> None:
    """Two different answers to `additionalProperties`, each on purpose.

    The device schemas own both ends of their wire -- the firmware writes them
    and the host reads them -- so an unexpected key is a bug and is rejected.
    The host-side contracts are read by clients that are deployed on a different
    schedule from their servers, and both of those servers state that additive
    optional fields do NOT bump the protocol version. A strict reader there
    would reject a peer that is, by its own contract, compatible.
    """
    for path in SCHEMA_FILES:
        schema = load(path)
        relative = path.relative_to(ROOT / "schemas").as_posix()
        if relative.startswith("device/"):
            assert schema.get("additionalProperties") is False, relative
        else:
            assert schema.get("additionalProperties") is True, relative


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

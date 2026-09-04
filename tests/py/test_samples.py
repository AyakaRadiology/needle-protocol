"""The generated pydantic models against the same real frames the TS suite uses.

``tests/samples.json`` holds frames as the actual emitters produce them, with
provenance on each. The ``invalid`` half matters more than the ``valid`` half: a
generated model that accepts everything passes every positive test there is,
which is precisely what the off-the-shelf rendering of the envelopes' ``allOf``
if/then table would do.
"""

from __future__ import annotations

import json
from pathlib import Path

import pydantic
import pytest

from needle_protocol import models

ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLES = json.loads((ROOT / "tests" / "samples.json").read_text())


def adapter(contract: str) -> pydantic.TypeAdapter:
    target = getattr(models, contract, None)
    assert target is not None, f"needle_protocol.models has no {contract}"
    # The envelopes are `Annotated[Union[...], Field(discriminator=...)]` rather
    # than plain classes, so everything goes through a TypeAdapter.
    return pydantic.TypeAdapter(target)


def parse(contract: str, frame: dict):
    """Parse a frame the way a consumer must: as strict JSON.

    Both wires carry JSON text, and JSON has a real number type. So a quoted
    "12.5" where a number belongs is a MALFORMED frame, not a value to coerce --
    and pydantic's default (lax) mode would coerce it, turning a wire bug into a
    plausible angle. `validate_json(..., strict=True)` is the mode that says so;
    it still accepts an ISO-8601 string for `ts`, because JSON has no datetime
    and there is nothing ambiguous to guess at there.

    This is also the faster path: pydantic parses the bytes itself instead of
    handing them to `json.loads` first. README documents it as THE way to
    consume these models, and this suite is what keeps that true.
    """
    return adapter(contract).validate_json(json.dumps(frame), strict=True)


@pytest.mark.parametrize(
    "sample", SAMPLES["valid"], ids=[s["name"] for s in SAMPLES["valid"]]
)
def test_accepts_real_frames(sample: dict) -> None:
    parse(sample["contract"], sample["frame"])


@pytest.mark.parametrize(
    "sample", SAMPLES["invalid"], ids=[s["name"] for s in SAMPLES["invalid"]]
)
def test_rejects_malformed_frames(sample: dict) -> None:
    with pytest.raises(pydantic.ValidationError):
        parse(sample["contract"], sample["frame"])


def test_samples_cover_the_contracts_the_generators_get_wrong() -> None:
    contracts = {s["contract"] for s in SAMPLES["valid"] + SAMPLES["invalid"]}
    assert "DeviceEnvelope" in contracts
    assert "AngleStreamEnvelope" in contracts
    assert "TrackerHello" in contracts
    assert "PlanChannelEnvelope" in contracts


def test_the_deferred_confirm_sequence_is_one_exchange() -> None:
    """`pending_confirm` then `applied` must be two acks of ONE request.

    That is the whole shape of the confirm semantics: needle-guide answers
    immediately to say the frame was understood, and again -- minutes later,
    under the SAME envelope `id` -- when the operator presses Apply. A sample
    set where the second ack quietly carried a fresh id would document a
    request/response channel that closes on the first answer, which is the one
    thing a sender must not do here. Nothing else notices: both frames validate
    perfectly well on their own.
    """
    by_name = {sample["name"]: sample["frame"] for sample in SAMPLES["valid"]}
    request = by_name["plan-channel-plan-request"]
    pending = by_name["plan-channel-plan-ack-pending-confirm"]
    applied = by_name["plan-channel-plan-ack-applied"]

    assert pending["id"] == applied["id"] == request["id"]
    for ack in (pending, applied):
        assert ack["payload"]["plan_id"] == request["payload"]["plan_id"]
        assert ack["payload"]["plan_revision"] == request["payload"]["plan_revision"]
    assert pending["payload"]["result"] == "pending_confirm"
    assert applied["payload"]["result"] == "applied"
    # The revision in effect only moves when the operator acts: it is the
    # PREVIOUS one while the plan is still on screen awaiting a press.
    assert pending["payload"]["applied_revision"] == request["payload"]["plan_revision"] - 1
    assert applied["payload"]["applied_revision"] == request["payload"]["plan_revision"]


def test_envelope_narrowing_reaches_the_payload(samples: dict) -> None:
    """A parsed frame must hand back a typed payload, not a bare dict.

    This is the property the tagged union exists for; asserting it here means a
    regression to `payload: dict[str, Any]` fails loudly instead of quietly
    accepting the wrong payload under the right `type`.
    """
    frame = next(s for s in samples["valid"] if s["name"] == "device-data")["frame"]
    parsed = parse("DeviceEnvelope", frame)
    assert isinstance(parsed, models.DeviceEnvelopeData)
    assert parsed.payload.accel_z == pytest.approx(0.99)

    heartbeat = next(
        s for s in samples["valid"] if s["name"] == "angle-stream-heartbeat-versioned"
    )["frame"]
    parsed_heartbeat = parse("AngleStreamEnvelope", heartbeat)
    assert isinstance(parsed_heartbeat, models.AngleStreamEnvelopeHeartbeat)
    assert parsed_heartbeat.payload.protocol_package_version == "0.1.0"
    assert parsed_heartbeat.payload.link.live is True

    plan = next(s for s in samples["valid"] if s["name"] == "plan-channel-plan-request")["frame"]
    parsed_plan = parse("PlanChannelEnvelope", plan)
    assert isinstance(parsed_plan, models.PlanChannelEnvelopePlan)
    assert parsed_plan.payload.plan_inclination_deg == pytest.approx(22.5)
    # The direction the schema pins per `type`, carried all the way into the
    # model rather than left as the base's two-value enum.
    assert parsed_plan.kind == "req"

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

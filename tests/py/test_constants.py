"""Properties of the shared constants, and of the schemas that quote them.

`tests/py/test_angles.py` already pins every generated constant to its value in
`constants/constants.json`. This file checks the things a value has to satisfy
*relative to the others*, which no single-value comparison can see.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Below the ephemeral range every operating system here allocates from, and
# above the privileged range that needs root to bind. A default outside it is a
# port that either needs privileges the apps do not have or gets handed to
# something else while the app is not running.
LOWEST_UNPRIVILEGED_PORT = 1024
LOWEST_EPHEMERAL_PORT = 49152


def constants() -> dict:
    return json.loads((ROOT / "constants" / "constants.json").read_text())["constants"]


def ports() -> dict[str, int]:
    return {name: spec["value"] for name, spec in constants().items() if name.endswith("_PORT")}


def test_every_default_port_is_distinct() -> None:
    """Three servers, one operator machine, three different numbers.

    needle-guide runs the angle stream and the plan channel; needle-simulator's
    Jetson tracker runs its own WebSocket; all three are expected on the same
    box. Two servers sharing a number means whichever binds second does not bind
    at all, and an operator who points one URL at another reaches a REAL server
    speaking a protocol the peer cannot read -- a healthy-looking open socket
    showing nothing. Both apps used to carry the constraint as a comment saying
    "must not be the other one" (docs/decisions.md ADR-0001); this is that
    comment, checked.
    """
    assigned = ports()
    # Name-based, so a port constant added later joins this check without
    # anybody remembering to. The floor is what stops the filter matching
    # nothing and passing while checking nothing.
    assert len(assigned) >= 3, f"expected the three known default ports, found {sorted(assigned)}"
    collisions = {
        value: sorted(name for name, port in assigned.items() if port == value)
        for value in set(assigned.values())
        if list(assigned.values()).count(value) > 1
    }
    assert not collisions, f"default ports collide: {collisions}"


def test_every_default_port_is_bindable_and_not_ephemeral() -> None:
    for name, port in ports().items():
        assert LOWEST_UNPRIVILEGED_PORT <= port < LOWEST_EPHEMERAL_PORT, f"{name}={port}"


def test_plan_channel_protocol_version_is_the_envelope_version() -> None:
    """`v` on the wire and PLAN_CHANNEL_PROTOCOL_VERSION are one number.

    A receiver refuses any other `v`, so if the constant a sender stamps and the
    const the schema pins ever parted company, every plan would be refused by a
    check that reads as a version mismatch and is really a typo here.
    """
    envelope = json.loads((ROOT / "schemas" / "plan-channel" / "envelope.json").read_text())
    assert envelope["properties"]["v"]["const"] == constants()["PLAN_CHANNEL_PROTOCOL_VERSION"]["value"]


def test_the_ack_timeout_outlasts_a_stale_link() -> None:
    """The first ack may take longer to arrive than a link takes to look dead.

    PLAN_ACK_TIMEOUT_MS bounds "was the frame understood at all". If it were
    shorter than HEARTBEAT_STALE_MS the sender would give up on a plan while the
    other app was still, by its own liveness rule, present -- and would re-send
    a plan into an app already showing it.
    """
    values = constants()
    assert values["PLAN_ACK_TIMEOUT_MS"]["value"] > values["HEARTBEAT_STALE_MS"]["value"]

"""Canonical angle conversions shared by Needle Guide, Needle Simulator and
anything else that has to move a needle angle between the two conventions.

Semantically identical to ``angles/ts/src/index.ts``; the shared test vectors in
``angles/vectors.json`` are run against both, so the two cannot drift.

Read ``angles/SPEC.md`` first. In one line: **inclination** is the angle from
vertical (0 = vertical, growing as the needle lies over) and is the quantity
every app measures, stores and displays; **console theta** is the CT console's
scale, ``theta = 90 - inclination``, and exists only at the edges.

Why ``None``, and why not ``nan``
---------------------------------
Every function here returns ``float | None``, and every missing or non-finite
input produces ``None``. That is deliberately stricter than the per-app helpers
this module consolidates, which happily returned ``nan`` for ``90 - nan``.

A ``nan`` angle is not an error state anyone notices: it flows through a
subtraction, through a rounding, and lands on screen. ``None`` is the answer
that cannot be mistaken for a measurement, and every readout in both apps
already has a branch for "no angle" because the sensor legitimately reports one.

Pure: standard library only, no pydantic, no numpy. Importing this module costs
nothing, which is why ``needle_protocol.models`` (and therefore pydantic) is a
separate, optional import.
"""

from __future__ import annotations

import math
from typing import Any, Final, NamedTuple

__all__ = [
    "CONSOLE_THETA_VERTICAL_DEG",
    "HORIZONTAL_INCLINATION_DEG",
    "MIN_NEEDLE_LENGTH_MM",
    "NeedleInclination",
    "angle_between_deg",
    "console_alpha_input_from_inclination",
    "console_theta_error",
    "console_theta_from_inclination",
    "inclination_error",
    "inclination_from_console_alpha",
    "inclination_from_console_theta",
    "needle_inclination_from_vertical",
]

#: The CT console's theta for a perfectly vertical needle; the single number
#: that ties the two conventions. Mirrors ``CONSOLE_THETA_VERTICAL_DEG`` in
#: ``constants/constants.json``, and a test fails if the two ever disagree.
CONSOLE_THETA_VERTICAL_DEG: Final[float] = 90.0

#: Angle-from-down of a horizontal needle, and therefore the boundary above
#: which the axis has a component against gravity: it points up. Numerically
#: equal to :data:`CONSOLE_THETA_VERTICAL_DEG` and deliberately separate --
#: that one is a theta on the console's scale, this one an inclination on ours.
HORIZONTAL_INCLINATION_DEG: Final[float] = 90.0

#: Entry->tip shorter than this is not a needle axis but two nearly coincident
#: points whose difference is mostly detection noise.
MIN_NEEDLE_LENGTH_MM: Final[float] = 20.0


class NeedleInclination(NamedTuple):
    """What :func:`needle_inclination_from_vertical` answers for a usable pose."""

    #: Angle between the needle axis (entry->tip) and straight down, 0..180.
    inclination_deg: float
    #: The same pose on the console's scale. Negative when ``points_up``.
    console_theta_deg: float
    #: True when the axis points UP rather than down. Every surface that prints
    #: an inclination must check this and print a placeholder instead: the
    #: number is a real angle but not the quantity the label promises.
    points_up: bool


def _finite(value: Any) -> float | None:
    """The one gate every scalar input passes through: a finite number, or None.

    ``bool`` is rejected explicitly. It is a subclass of ``int`` in Python, so
    without this a stray ``True`` would silently become 1 degree.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    v = float(value)
    return v if math.isfinite(v) else None


def console_theta_from_inclination(inclination_deg: Any) -> float | None:
    """inclination -> the console's theta (``theta = 90 - inclination``)."""
    i = _finite(inclination_deg)
    return None if i is None else CONSOLE_THETA_VERTICAL_DEG - i


def inclination_from_console_theta(console_theta_deg: Any) -> float | None:
    """The console's theta -> inclination (``inclination = 90 - theta``).

    The conversion is its own inverse, so this is the same arithmetic as
    :func:`console_theta_from_inclination`. Both names exist because a call site
    reading one where it means the other is exactly the mistake this module is
    here to prevent -- and is the mistake that let a 5 degree pitch error
    survive as long as it did.
    """
    t = _finite(console_theta_deg)
    return None if t is None else CONSOLE_THETA_VERTICAL_DEG - t


def console_alpha_input_from_inclination(inclination_deg: Any) -> float | None:
    """The number to type into the guide's legacy Alpha field.

    The guide derives its own target as ``theta = Alpha + 90``, and its theta
    never exceeds :data:`CONSOLE_THETA_VERTICAL_DEG`. So the input it wants is
    the negated inclination, always <= 0.
    """
    i = _finite(inclination_deg)
    if i is None:
        return None
    # ``-0.0`` is not a legible angle; normalise it so a readout never prints
    # "-0.0" for a perfectly vertical plan.
    return 0.0 if i == 0.0 else -i


def inclination_from_console_alpha(console_alpha_deg: Any) -> float | None:
    """The inverse of :func:`console_alpha_input_from_inclination`."""
    a = _finite(console_alpha_deg)
    if a is None:
        return None
    return 0.0 if a == 0.0 else -a


def console_theta_error(sensor_theta_deg: Any, target_theta_deg: Any) -> float | None:
    """Residual on the CONSOLE's scale: measured theta minus the plan's theta.

    Positive means the needle is MORE vertical than the plan (its theta is
    higher, so its inclination is lower).

    None whenever either half is missing -- a residual against an absent target
    would read as "on plan" at 0 degrees.
    """
    s = _finite(sensor_theta_deg)
    t = _finite(target_theta_deg)
    return None if s is None or t is None else s - t


def inclination_error(sensor_inclination_deg: Any, plan_inclination_deg: Any) -> float | None:
    """The same residual in the INCLINATION convention: the negation of
    :func:`console_theta_error`.

    Inclination and theta run in opposite directions, and that minus sign is the
    thing nobody may re-derive at a call site.

    Positive means the needle is laid over FURTHER than the plan calls for.
    """
    s = _finite(sensor_inclination_deg)
    p = _finite(plan_inclination_deg)
    return None if s is None or p is None else s - p


def _vec3(value: Any) -> tuple[float, float, float] | None:
    """A finite ``{x, y, z}`` mapping (or 3-sequence) as a tuple, else None."""
    if isinstance(value, dict):
        parts = [value.get("x"), value.get("y"), value.get("z")]
    elif isinstance(value, (list, tuple)) and len(value) == 3:
        parts = list(value)
    else:
        return None
    out: list[float] = []
    for part in parts:
        f = _finite(part)
        if f is None:
            return None
        out.append(f)
    return (out[0], out[1], out[2])


def angle_between_deg(a: Any, b: Any) -> float | None:
    """Angle between two vectors in degrees, or None if either has no direction.

    The dot product of the unit vectors is clamped to [-1, 1] before ``acos``:
    for near-parallel inputs floating-point error pushes it a few ulps past 1,
    and ``acos`` of that raises -- which would surface as a crash somewhere far
    from the cause rather than as an answer here.
    """
    va = _vec3(a)
    vb = _vec3(b)
    if va is None or vb is None:
        return None
    na = math.sqrt(va[0] ** 2 + va[1] ** 2 + va[2] ** 2)
    nb = math.sqrt(vb[0] ** 2 + vb[1] ** 2 + vb[2] ** 2)
    if na == 0.0 or nb == 0.0 or not math.isfinite(na) or not math.isfinite(nb):
        return None
    c = (va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2]) / (na * nb)
    return math.degrees(math.acos(min(1.0, max(-1.0, c))))


def needle_inclination_from_vertical(
    tip_mm: Any, entry_mm: Any, gravity_down_trk: Any
) -> NeedleInclination | None:
    """The live inclination of a needle from its endpoints and gravity.

    ``gravity_down_trk`` must be expressed in the SAME frame as ``tip_mm`` and
    ``entry_mm``. Passing a DICOM vector and a tracker vector returns a
    perfectly plausible angle that is simply wrong, which is why the frame is in
    the parameter name.

    None when the needle is too short to define an axis
    (:data:`MIN_NEEDLE_LENGTH_MM`), when either point is not a finite vector, or
    when the gravity vector carries no direction -- the last of those matters
    because a solved calibration also comes back through client-side storage,
    and a zero vector there must not become a silent 0 degrees.
    """
    tip = _vec3(tip_mm)
    entry = _vec3(entry_mm)
    if tip is None or entry is None:
        return None
    axis = (tip[0] - entry[0], tip[1] - entry[1], tip[2] - entry[2])
    if math.sqrt(axis[0] ** 2 + axis[1] ** 2 + axis[2] ** 2) < MIN_NEEDLE_LENGTH_MM:
        return None

    inclination_deg = angle_between_deg(axis, gravity_down_trk)
    if inclination_deg is None:
        return None

    console_theta_deg = console_theta_from_inclination(inclination_deg)
    if console_theta_deg is None:
        return None

    return NeedleInclination(
        inclination_deg=inclination_deg,
        console_theta_deg=console_theta_deg,
        points_up=inclination_deg > HORIZONTAL_INCLINATION_DEG,
    )

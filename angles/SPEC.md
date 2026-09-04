# Angle conventions

Three programs measure the same needle and call the answer three things. This
file says which quantity each one owns, how to convert, and which conversions
are the ones that have already gone wrong.

The executable half of this document is `vectors.json`, which is run against both
reference implementations (`ts/src/index.ts`, `py/needle_protocol/angles.py`).
If prose here and a vector there disagree, the vector wins and the prose is a
bug — fix it in the same change.

## The quantities

| Name | Symbol | 0 means | Grows as | Owned by |
|---|---|---|---|---|
| **Inclination** | `inclination_deg` | needle straight down (vertical) | the needle lies over toward horizontal | needle-guide (measures it), needle-simulator (computes it) — the canonical quantity everywhere |
| **Console θ** | `theta` | needle horizontal | the needle stands up | the CT console, and nothing else |
| **Console Alpha** | `ALPHA` | in-plane trajectory | the trajectory leaves the axial plane | the CT console's plan field |

```
inclination = 0            inclination = 45           inclination = 90
theta       = 90           theta       = 45           theta       = 0
      |                          \                        ____
      |                           \
      v  (down / gravity)          v
```

### The one identity

```
theta = CONSOLE_THETA_VERTICAL_DEG - inclination        (= 90 - inclination)
inclination = CONSOLE_THETA_VERTICAL_DEG - theta        (the same arithmetic)
```

`CONSOLE_THETA_VERTICAL_DEG` is defined once, in `constants/constants.json`, and
is the **only** place the two scales are allowed to meet. Both reference
implementations keep a local copy so they can stay dependency-free; the test
suites pin the copies to the shared value, so they cannot come to mean different
things.

The conversion being its own inverse is why there are two names for it. A call
site that reads `consoleThetaFromInclination` where it means the opposite is
still syntactically perfect and numerically wrong — and that is exactly how a 5°
pitch mismatch survived undetected between the guide and the simulator.

### Alpha

The guide derives its own target as `theta = Alpha + 90`, and its θ never exceeds
90. So the number to type into the Alpha field is the negated inclination, always
≤ 0:

```
Alpha = -inclination
inclination = -Alpha
```

`consoleAlphaInputFromInclination` normalises `-0` to `0`, because a readout that
prints `-0.0°` for a perfectly vertical plan is reporting a sign that does not
exist.

## Residuals, and the sign that keeps getting re-derived

Both residuals describe the same pose and are exact negations of each other:

```
consoleThetaError(sensorTheta, targetTheta) = sensorTheta - targetTheta
    positive → the needle is MORE VERTICAL than the plan

inclinationError(sensorIncl, planIncl)      = sensorIncl  - planIncl
    positive → the needle is LAID OVER FURTHER than the plan
```

Both exist as named functions precisely so that the minus sign between them is
never re-derived at a call site. During the dual-emit release both are on screen
at once, because the operator is reading one of each on two machines; a single
row would be right for one screen and backwards for the other.

## Components vs. spherical angles

The CT console does **not** ask for a spherical (inclination, azimuth) pair. It
asks for two independent *components* of the trajectory:

- **ALPHA — craniocaudal.** The part of the trajectory that leaves the DICOM
  axial plane.
- **BETA — mediolateral.** The in-axial-plane angle, measured from
  patient-anterior and sweeping toward patient-left.

Neither is the needle's inclination. `ALPHA` equals the inclination only when
`BETA` is zero *and* the phantom sits perfectly level — and neither holds at a
site visit. Typing `ALPHA` into the guide's plan field therefore aims the
operator at a target one or two degrees off the planned trajectory, with both
instruments individually correct. `consoleAlphaInputFromInclination` computes
the right number: it takes the plan's **total** inclination from vertical, which
is what the guide's gravity-referenced inclinometer actually measures.

## Frames

| Frame | Axes | Used by |
|---|---|---|
| **DICOM LPS** | +x patient left, +y patient posterior, +z patient superior (head) | the CT plan, everything read out of the image |
| **trk / phantom** | the tracker's own millimetre frame | needle-simulator's detections, and the solved gravity vector |

`needleInclinationFromVertical(tip, entry, down)` takes all three vectors **in
one frame**. The gravity vector is solved in the phantom frame, so a DICOM plan
direction is permuted into that frame before the angle is taken — DICOM→phantom
is a signed permutation, so it is direction-only: no translation, no
registration. Passing a DICOM vector and a tracker vector to the same call
returns a perfectly plausible angle that is simply wrong, which is why the frame
is spelled out in the parameter name.

### Sign and axis table (documentation, not code)

Copied from needle-simulator `apps/desktop/src/lib/ctConsole/navReadout.ts`,
which is the SSOT for these. Reproduced here so the conventions are legible in
one place; **do not** re-encode them anywhere — the constants live there and are
corrected there after a bench session.

| Console field | Meaning | DICOM axis | Sign | Status |
|---|---|---|---|---|
| `CT_X` | entry point, mediolateral | `x` | `+1` | provisional |
| `CT_Z` | entry point, axial (craniocaudal) | `z` | `+1` | provisional |
| `BETA` zero direction | in-axial-plane reference | `y` | `-1` (patient-anterior) | provisional |
| `BETA` sweep direction | in-axial-plane positive sense | `x` | `+1` (patient-left) | provisional |
| `ALPHA` | out-of-axial-plane component | `z` | `-1` (patient-inferior) | **bench-verified 2026-08-23** |

`ALPHA`'s sign is the one that was checked against the nav app and found
inverted from the original guess. The rest are documented guesses; treat a
disagreement in the field as evidence about the table, not about the arithmetic.

## Degenerate cases, and why every function returns null

- **Needle too short.** Entry→tip below `MIN_NEEDLE_LENGTH_MM` (20 mm) is not an
  axis: it is two nearly coincident detections whose difference is mostly noise,
  and the direction it implies swings wildly. Same floor as the gravity pose
  sampler, so a needle the calibration would refuse to capture is one the live
  readout refuses to report.
- **No gravity direction.** A zero vector where the solved gravity should be —
  uncalibrated, or restored from client-side storage that was cleared. `null`,
  never a silent 0°, which would read as a perfectly vertical needle.
- **Non-finite input.** `NaN` and `±Infinity` become `null`. This is stricter
  than the per-app helpers this package consolidates, which returned `90 - NaN`.
  A `NaN` angle is not an error state anyone notices: it survives a subtraction,
  a rounding and a `?? 0`, and lands on screen. Every readout in both apps
  already branches on "no angle", because the sensor legitimately reports one, so
  `null` has nowhere to hide.
- **Needle pointing up.** Past horizontal the needle points out of the patient,
  the console's θ goes negative, and no real insertion produces the pose. The
  angle is still returned unchanged — it is a true angle and the diagnostics want
  it — and `pointsUp` is what tells a surface to print a placeholder instead of
  the number. Exactly horizontal (90°) is **not** up; the boundary is strict.

## Who owns what

| Quantity | Produced by | Consumed by |
|---|---|---|
| `inclination_deg` (live) | needle-guide, from the SCL3300 against a calibrated zero-reference vector | needle-simulator's readouts; the `inclination` frame |
| `inclination_deg` (planned) | needle-simulator, from the CT plan direction against the solved gravity vector | the operator, who types the Alpha it implies into the guide |
| `theta` | needle-guide only, as the deprecated dual-emit copy; needle-simulator only at the point of display | the CT console screen the operator is reading next door |
| `ALPHA` / `BETA` / `CT_X` / `CT_Z` | needle-simulator's `navReadout.ts` | the operator, retyping into the CT console |

The **CT console** has no channel, and will not get one: anything the operator
types into it is a *declaration* that they typed it, which is why the simulator
tracks drift against an "armed" value rather than against what the console
actually holds.

Between the simulator and the guide there are now two channels, in opposite
directions — the one-way angle stream, and the plan channel below.

## Plan channel

`schemas/plan-channel/` carries a **plan** from needle-simulator into
needle-guide: the trajectory the simulator computed from the CT plan, pushed to
a separate inbound listener on the guide (`PLAN_CHANNEL_DEFAULT_PORT`) rather
than answered back down the angle stream. The angle stream is the guide's
*output* and is output-only as a medical-device posture — needle-guide
`SYSTEM_SPEC.md` §5.3: *"There is no code path by which a subscriber can
command, configure or calibrate this app."* A plan is a command, so it does not
travel on that wire; see README > The plan channel for the request/response
shape, the two-ack confirm, and the idempotency rule.

What matters *here* is which quantity crosses it, because this is the file
where that has gone wrong before:

| Field | Quantity | Range |
|---|---|---|
| `plan_inclination_deg` | **Inclination**, from vertical — the canonical quantity in the table above | 0…90 |
| `azimuth_deg` | Horizontal-plane angle, signed half-turn | −180…180 |

`plan_inclination_deg` is an **identity**, not a conversion: it is the same
quantity, under the same name, as needle-guide's own `plan_inclination_deg` in
`shared/planInputs.ts`. Nothing on this wire is console θ and nothing is
`ALPHA`. That is deliberate — `theta = 90 − inclination` is its own inverse, so
a channel that carried θ would be a channel where sending the wrong one is
syntactically perfect and 5° to 90° wrong, which is precisely the failure this
package exists to have removed. The operator still reads `ALPHA` off
needle-simulator and types it into the CT console; that path is unchanged and
still has no channel.

**Refuse, never clamp** — the same rule `shared/planInputs.ts` states, on the
wire as well as in the form. An inclination outside 0…90 is rejected and
reported; it is never quietly moved inside the range, because an entry point
silently pulled to ±1000 mm, or an inclination to 90°, would be a plan the
operator never planned.

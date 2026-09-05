# needle-protocol

The wire contracts, angle conventions and shared constants that
[needle-guide](https://github.com/AyakaRadiology/needle-guide),
[needle-simulator](https://github.com/AyakaRadiology/needle-simulator) and the
[scl3300-stream](https://github.com/AyakaRadiology/scl3300-stream) firmware all
have to agree on — held in one place, generated into three languages, and
verified in CI.

Before this repository each contract existed as two or three hand-kept copies:
the device schemas were forked into needle-guide's `server/schemas/firmware/`,
`90 − inclination` was written out in four files across two repos, and port
numbers and staleness thresholds were literals in whichever file needed them.
Copies do not stay equal; a 5° pitch mismatch between the two apps is what that
cost.

## Layout

```
schemas/         JSON Schema 2020-12, one per contract, each with an "x-version"
constants/       constants.json — the one place a shared literal is written
angles/          SPEC.md (the conventions), vectors.json (shared test cases,
                 PUBLISHED to consumers), and the two reference
                 implementations they are run against
gen/             GENERATED and committed: TypeScript, Python, C. CI diffs it.
dist/            GENERATED and committed: gen/ts compiled to ESM + CommonJS
                 JavaScript with declarations, which is what `needle-protocol`
                 resolves to. CI diffs it too.
tools/           gen.sh and the generators behind it
tests/           ts (vitest), py (pytest), c (gcc + g++), consumer (packs the
                 tarball and loads it with a stock node); samples.json is
                 shared with consumers too — it is PUBLISHED, not a fixture
docs/decisions.md  why this repository exists, and why in this shape
```

**Never hand-edit anything under `gen/` or `dist/`.** CI runs `tools/gen.sh` and
then `git diff --exit-code gen/ dist/`, so an edit there is a red build; and the
next regeneration would revert it anyway.

## What is in here

| Contract | Schema | Speakers |
|---|---|---|
| Device NDJSON envelope + payloads | `schemas/device/` | scl3300-stream firmware → needle-guide's serial reader |
| Inclination WebSocket stream | `schemas/angle-stream/` | needle-guide → needle-simulator |
| Plan channel (request/response) | `schemas/plan-channel/` | needle-simulator → needle-guide, and its ack back |
| Tracker hello | `schemas/tracker/hello.json` | needle-simulator's Jetson → its desktop client |

### The plan channel

The angle stream and the plan channel run between the same two apps and point
in opposite directions. They are two contracts, on two ports, on purpose.

**Direction.** needle-simulator authors a plan — a trajectory it computed from
the CT plan — and pushes it to a **separate inbound listener** on needle-guide
(`PLAN_CHANNEL_DEFAULT_PORT`, 8791, loopback). needle-guide answers. Today the
operator carries these numbers between two screens by hand and retypes them.

**Why not on the angle stream.** That stream is needle-guide's *output*, and its
being output-only is a medical-device posture rather than an implementation
detail — needle-guide `SYSTEM_SPEC.md` §5.3: *"There is no code path by which a
subscriber can command, configure or calibrate this app."* Its envelope pins
`kind` to the const `evt` to say so. A plan is a command, so it gets its own
contract, its own listener and its own port; a subscriber to the angle stream
gains nothing by connecting, and the two can never satisfy each other's schema.
`tests/samples.json` carries an `evt` frame aimed at the plan channel as a
**rejection** sample, because an operator who types 8791 for 8790 is the
realistic way that gets tested in the field.

**Request and response.** `kind` is `req` or `res`, `type` is `plan` or
`plan_ack`, and the envelope binds the two — a `plan_ack` labelled `req` is
refused. Every `res` echoes its `req`'s envelope `id` verbatim.

**Confirm semantics.** One request can produce **two** acks. needle-guide
answers `pending_confirm` at once — the frame was understood, and it is now in
front of an operator who has not pressed Apply — and then, under the *same*
`id`, `applied` when they do or `rejected` with a `reason` if they dismiss it. A
sender therefore does not close the correlation on the first answer.
`PLAN_ACK_TIMEOUT_MS` bounds the wait for the first ack only; nothing bounds an
operator.

**Idempotency.** A plan is identified by `plan_id` (opaque; today a DICOM
`SeriesInstanceUID`) and a monotonic `plan_revision`. Re-sending the same pair
is idempotent: the receiver answers with the ack it would have sent and does not
re-prompt someone who has already confirmed that revision.

**Refuse, never clamp.** Every bound in `payload-plan.json` mirrors
needle-guide's own `shared/planInputs.ts` — inclination 0…90 from vertical,
azimuth −180…180, entry lateral ±1000 mm, entry longitudinal ±3000 mm — and a
value outside one is **rejected and reported, never quietly moved inside**. So
is an unknown field: alone among the host-side contracts these schemas are
`additionalProperties: false`, because a key the receiver does not understand is
a part of the plan it would silently drop, and half a plan applied is worse than
no plan applied. The cost is an ordered rollout, and it is stated in
`docs/decisions.md` ADR-0003.

The two entry offsets carry different numbers on purpose. Lateral is an offset
*across* the patient, which the bore genuinely limits; longitudinal is a
position *along* the CT table, whose travel runs well past a metre, so the
bore's ruler was the wrong one for it and refused entry points real procedures
produced. Both bounds exist to catch garbage — a stray keystroke, a value typed
in the wrong unit — and neither states a clinical limit.

**Not on the Pico.** `tools/gen.sh` generates the C header from
`schemas/device/*.json` only, so the firmware gains no `KEY_*` macro for a wire
it never speaks.

### What is deliberately NOT in here

These are single-repo contracts: one program writes them and the same program
reads them, so a shared package would add a release cycle and buy nothing.
Listed so the omission reads as a decision rather than an oversight.

- **Session JSONL** (needle-simulator). A recording format, not a wire.
- **Tracker needle-frame bodies** (needle-simulator). The Jetson→desktop frame
  payloads change with the tracker's own vocabulary; only the `hello`
  handshake, which is what decides whether the two can talk at all, is shared.
- **needle-guide host WebSocket schemas** (`server/schemas/ws-envelope.json`
  and its payloads). Its own renderer is the only consumer. The angle-stream
  envelope here is modelled on it, and the two are expected to stay similar,
  but they are not the same contract.
- **Jetson debug endpoints** (`/healthz` and friends). Operational surface,
  changed at will.
- **The CT-console bridge.** There is no channel between needle-simulator and
  the CT console; a human retypes four numbers. `angles/SPEC.md` documents the
  conventions so both sides agree on what those numbers mean.

Any of these can move in later. Moving one in means adding a schema and a
sample; moving one in *badly* means coupling two release cycles that had no
reason to be coupled.

## Consuming it

Every consumer pins a **tag**. A branch pin means the contract can change under
a build that was passing an hour ago, which is the failure mode this repository
exists to remove.

### TypeScript / bun

```jsonc
// package.json
"dependencies": {
    "needle-protocol": "github:AyakaRadiology/needle-protocol#v0.1.0"
}
```

```ts
import { ANGLE_STREAM_DEFAULT_PORT, consoleThetaFromInclination } from 'needle-protocol';
import type { AngleStreamEnvelope } from 'needle-protocol';

// Validators are a SEPARATE entry point, and `zod` is an optional peer
// dependency. Nothing reachable from 'needle-protocol' imports it, so the
// 60 Hz angle-frame parse path stays free of a schema library.
import { AngleStreamEnvelopeSchema } from 'needle-protocol/zod';
```

#### Bundled and unbundled consumers both work

`needle-protocol` resolves to **compiled JavaScript** under `dist/`, in both
module systems, each with its own declarations:

| You load it with | You get |
|---|---|
| Vite, or any bundler | `dist/esm/*.js` — it compiles the ESM half like any other dependency |
| `node` / Electron **main**, ESM | `dist/esm/*.js` |
| Electron **preload**, CommonJS | `dist/cjs/*.js` |

That is not decoration. A consumer whose TypeScript is emitted by `tsc` and then
run unbundled — needle-guide's Electron main process is exactly that — used to
hit `ERR_UNSUPPORTED_NODE_MODULES_TYPE_STRIPPING` the moment it imported a
**value** rather than a type, because `exports` pointed at `gen/ts/*.ts` and
Node will not strip types inside `node_modules`. The workaround was to keep a
local copy of the constant, which is the drift this repository exists to remove.
`tests/consumer/run.sh` packs the tarball and loads it with a stock `node`,
through `import()` and `require()`, so that failure cannot come back unnoticed.

`dist/` is **generated and committed**, exactly like `gen/`: a git dependency has
no publish step and bun runs no `prepare` script for one, so an uncommitted
`dist/` is an empty `dist/` on the consumer's disk. `tools/gen.sh` builds it and
CI runs `git diff --exit-code gen/ dist/`. Never hand-edit a file under `dist/`.

If you would rather compile the source yourself, it is still shipped and
reachable at `needle-protocol/src/*` (`needle-protocol/src/angles` →
`gen/ts/angles.ts`). Nothing in this repository needs that; it is there so a
consumer with an unusual build does not have to fork the package.

### Python / uv

```toml
# pyproject.toml
dependencies = [
    "needle-protocol @ git+https://github.com/AyakaRadiology/needle-protocol@v0.1.0#subdirectory=gen/py",
]
```

Run `uv lock` and **commit the lock**: needle-simulator's offline-boot gate
installs the Jetson appliance from `uv.lock` with no network, so a dependency
that never reached the lock is a rig that will not boot.

```python
from needle_protocol import ANGLE_STALE_MS, console_theta_from_inclination
from needle_protocol.models import AngleStreamEnvelope   # needs the `models` extra
```

`needle_protocol.constants` and `needle_protocol.angles` are standard library
only. pydantic comes from the optional `models` extra, so a consumer that only
wants the shared literals adds no wheel to the offline set:

```toml
"needle-protocol[models] @ git+https://github.com/AyakaRadiology/needle-protocol@v0.1.0#subdirectory=gen/py",
```

**Parse as strict JSON.** Both wires carry JSON text, and JSON has a real number
type, so a quoted `"12.5"` where a number belongs is a malformed frame — not a
value to coerce. pydantic's default (lax) mode would coerce it into a plausible
angle:

```python
import pydantic
from needle_protocol.models import AngleStreamEnvelope

frames = pydantic.TypeAdapter(AngleStreamEnvelope)
frame = frames.validate_json(raw_bytes, strict=True)   # ISO-8601 `ts` still fine
```

### Pico firmware / CMake

The firmware takes this repository as a submodule pinned to a tag and generates
its header at build time. The header is **not** committed there: a committed
copy is a copy that can be edited, and an edited `KEY_*` macro is a wire-format
change that no schema records.

```bash
git submodule add https://github.com/AyakaRadiology/needle-protocol.git external/needle-protocol
git -C external/needle-protocol switch --detach v0.1.0
```

```cmake
set(NP_DIR ${CMAKE_SOURCE_DIR}/external/needle-protocol)
file(GLOB NP_DEVICE_SCHEMAS ${NP_DIR}/schemas/device/*.json)

add_custom_command(
    OUTPUT ${CMAKE_BINARY_DIR}/generated/schema_keys.h
    COMMAND ${Python3_EXECUTABLE} ${NP_DIR}/tools/gen_schema_header.py
            --schemas ${NP_DEVICE_SCHEMAS}
            --out ${CMAKE_BINARY_DIR}/generated/schema_keys.h
    DEPENDS ${NP_DEVICE_SCHEMAS} ${NP_DIR}/tools/gen_schema_header.py
    COMMENT "Generating schema_keys.h from needle-protocol"
    VERBATIM)
```

The header exposes `KEY_*` string macros, a C enum per schema enum, and
`SCHEMA_DEVICE_*_XVERSION` string macros so the firmware reports the contract it
was built against instead of a hand-kept literal beside it.

### Contract fixtures

Two data files are **published**, not private fixtures. Both are listed in
`files` and named in `exports`, so a consumer imports them by specifier and
never by filesystem path:

| Entry point | What it holds |
|---|---|
| `needle-protocol/angles/vectors.json` | The shared angle-conversion cases — `parameters` (constants both reference implementations must agree on) and `cases` (`fn`, `args`, `expect`) |
| `needle-protocol/tests/samples.json` | Wire frames as the real emitters produce them, split into `valid` and `invalid` |

```ts
import vectors from 'needle-protocol/angles/vectors.json' with { type: 'json' };
import samples from 'needle-protocol/tests/samples.json' with { type: 'json' };
```

`exports` names each file **exactly**, rather than exposing `angles/` through a
wildcard. `angles/ts` and `angles/py` are the reference implementations' sources
— generator input, compiled into `gen/` and `dist/` — and importing them
directly would pin a consumer to a layout this repository reserves the right to
move. `tests/consumer/run.sh` loads both JSON entry points out of the packed
tarball, through `import()` and `require()`, because an `exports` map that omits
one answers `ERR_PACKAGE_PATH_NOT_EXPORTED` and no suite reading these files
from the working tree can see that.

Each sample entry carries `contract`, `name`, a provenance string and the `frame`
itself; `invalid` entries carry `why` in place of `from`. A consumer with a
hand-written parser — needle-guide's serial reader is one — can assert that
every `valid` frame parses and every `invalid` one is rejected. That is what
stops a hand-written parser from drifting away from the generated validators
while both keep passing their own tests.

The **Python** package is built from `gen/py`, whose wheel contains
`needle_protocol` and nothing else, so a `uv` git dependency carries NEITHER
file. Python consumers that want them read them out of a source tree pinned to
the same tag. Said here rather than discovered at import time.

Being published makes both a contract surface: an entry may be added, and its
provenance or note text corrected, but **renaming or deleting one breaks a
consumer's test at its next pin bump**. That is the intended amount of friction
— a vanishing sample or angle case is precisely the event a consumer should be
made to notice.

## Versioning

Two numbers move here, independently, and conflating them is how a compatible
release gets refused and an incompatible one gets accepted.

- **A schema's `x-version`** decides whether a device and a host can talk. It
  moves when that one contract changes, and it does not move because some other
  schema did.
- **The package version** (the `v*` tag) is what consumers pin. It follows
  Conventional Commits through release-please and moves whenever anything in
  here does.

`.release-please-manifest.json` starts at `0.0.0`, which is the *last released*
version — there is none. That alone does not produce a `0.1.0` first release:
with no previous release to bump from, release-please skips its versioning
strategy entirely and hardcodes `1.0.0`, so `bump-minor-pre-major` never gets a
say. `"initial-version": "0.1.0"` in `release-please-config.json` is what makes
the first release PR `chore(main): release 0.1.0`, and merging it creates the
`v0.1.0` tag the pins above name. Setting the manifest to `0.1.0` instead would
tell release-please that 0.1.0 had already shipped, and its first
PR would propose 0.2.0 — leaving `v0.1.0` as a tag nobody ever creates.

Rules that are enforced, not remembered:

| Change | Version impact | Enforced by |
|---|---|---|
| Adding an optional field | minor | — |
| Adding an enum value at the END of the array | minor | `tools/check-enum-order.py` allows it |
| **Reordering an enum, or removing an element** | **MAJOR** | `tools/check-enum-order.py` fails the build |
| Renaming or removing a required field | MAJOR | review; the samples in `tests/samples.json` will fail |
| Editing anything under `gen/` or `dist/` by hand | rejected | `git diff --exit-code gen/ dist/` in CI |

Enum **order** is load-bearing because `tools/gen_schema_header.py` gives each C
enum constant the value of its index in the JSON array, and a flashed Pico
stores those integers. Reordering `["init", "ready", …]` is an edit every JSON
linter calls equivalent and that silently changes what `state == 1` means on a
device already in the field.

## Working on it

Toolchain: **bun** (installs the generators, runs the TypeScript suite, packs
the consumer tarball), **Node 24** (runs the generators and the `dist/` build —
both are diffed byte for byte in CI, so the runtime that produces them is part
of the contract), **uv** (Python), and **gcc/g++** (the firmware header).

```bash
bun install
uv sync --all-groups

tools/gen.sh          # regenerate gen/ AND dist/ — commit the result
bunx tsc --noEmit
bunx vitest run
uv run pytest tests/py -q
tests/c/run.sh
tests/consumer/run.sh
uv run python tools/check-enum-order.py
```

`tools/gen.sh` compiles `dist/` with the TypeScript pinned in `package.json`,
resolved from `node_modules` rather than `PATH` — the compiler version shows up
in the emitted bytes, and CI diffs those.

Adding a shared angle case means one line in `angles/vectors.json`; it runs
against both reference implementations automatically. Adding a frame means one
entry in `tests/samples.json`; it is validated by zod and by pydantic
automatically. Neither has a second place to remember.

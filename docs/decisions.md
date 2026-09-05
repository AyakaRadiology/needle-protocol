# Decisions

Architecture decision records for `needle-protocol`. Newest last.

---

## ADR-0001 — A separate repository, JSON Schema as the source of truth, git-dep consumers

**Date:** 2026-09-04
**Status:** accepted

### Context

Four programs speak to each other and none of them shared a definition:

- **scl3300-stream** (Pico firmware) emits NDJSON described by
  `schemas/*.json`, and generates a C header from them.
- **needle-guide** (Electron + FastAPI) reads that NDJSON over USB serial, and
  broadcasts a needle inclination over its own WebSocket. It carried a **forked
  copy** of the firmware's schemas in `server/schemas/firmware/`.
- **needle-simulator** (Tauri + Jetson) subscribes to that broadcast, and runs
  its own tracker WebSocket with its own `hello` handshake.
- The **CT console**, which nothing talks to; a human retypes four numbers.

The damage was already measurable rather than theoretical:

1. `90 − inclination` was written out in `needle-guide/shared/inclination.ts`,
   `needle-simulator/lib/gravity/inclination.ts`,
   `needle-simulator/lib/ctConsole/navTarget.ts` and the frame parser. A pitch
   mismatch of about 5° between the two apps survived for weeks, because each
   copy was individually correct and the question "which direction is this
   conversion going" was answered separately in each file.
2. The firmware schema fork drifted: needle-guide's copy of
   `device-envelope.json` was a different size from the canonical one at the
   time this repository was created.
3. `8790` (the broadcast port) and `8765` (the tracker port) appeared as
   literals in both apps, along with an explicit comment in each saying "must
   not be the other one" — a constraint that only held because two people
   remembered it.
4. Nothing tied needle-simulator's `SENSOR_HEARTBEAT_STALE_MS = 2000` to
   needle-guide's `HEARTBEAT_INTERVAL_MS = 500`, though the first is documented
   as "four missed heartbeats" of the second.

### Decision

**A separate repository**, rather than a package inside any of the three.

- Every candidate home is a *peer* of the others. Putting the contract in
  needle-guide would make the firmware depend on an Electron app; putting it in
  needle-simulator would make needle-guide depend on the thing it broadcasts to.
- The Pico consumes it as a git submodule, which can only point at a repository.
- The release cadences are genuinely different: the contract moves rarely and
  its consumers move weekly.

The cost is real and accepted: a contract change is now two pull requests, and
the second cannot merge until the first is tagged.

**JSON Schema 2020-12 as the single source of truth**, with code generated from
it — not TypeScript types with everything else derived, and not a hand-written
document.

- It is the only representation all three toolchains can read. The C header
  generator already existed and reads schemas; TypeScript, zod and pydantic all
  have mature generators.
- It is the representation the firmware's own validation tooling already used,
  so the device contracts moved here verbatim, `$id` and enum order intact.
- A schema carries `x-version`, which is the number that already decided
  device↔host compatibility in `scl3300-stream/SECURITY.md`. Keeping that
  meaning cost nothing.

Two things the off-the-shelf generators get wrong were fixed rather than
tolerated. Both envelope schemas select their payload with an `allOf` if/then
table; `json-schema-to-zod` renders that as `z.intersection(z.any(), z.any())`
and `datamodel-code-generator` as `payload: dict[str, Any]`. Either would
happily accept a heartbeat payload inside an `inclination` frame **and report
success** — a generated validator that silently does not validate is worse than
no validator, because it is trusted. `tools/gen-ts.mjs` and `tools/gen-py.py`
emit tagged unions from the same table, and throw rather than fall back if they
meet a conditional shape they do not recognise.

**Generated code is committed**, and CI regenerates and diffs it.

- A consumer can install by tag with no build step, which is what makes a bun
  git dep and a `uv` git dep work at all.
- The diff is the review artifact: a schema change whose generated consequence
  is surprising is visible in the same pull request.
- `tools/gen.sh` runs twice in CI, so a generator with a timestamp or an
  unordered set fails immediately rather than producing an unreadable diff on
  someone else's branch later.

**Git dependencies pinned to tags**, rather than a package registry.

- These are three private repositories on one organisation. A registry would
  mean either publishing a medical-adjacent contract publicly or running a
  private one, for three consumers.
- npm/bun and uv both resolve git tags natively, and uv writes the resolved
  commit into `uv.lock` — which the Jetson's offline-boot gate depends on.
- The cost: no semver range resolution. Every consumer names an exact tag and a
  bump is an explicit pull request in each. For a contract, that is the right
  amount of friction.

**The firmware header is generated, not committed there.** A committed header in
the firmware repo is a header somebody can edit, and an edited `KEY_*` macro is a
wire-format change that no schema records and no diff explains. It is committed
*here*, where its diff is the evidence that the generator and the schemas still
agree — which the firmware build has no way to check on its own.

### Consequences

- Changing a contract is a three-step dance: PR here, tag, PR in each consumer.
  Additive changes still deploy in any order; that is what `additionalProperties:
  true` on the host-side schemas and the "additive fields do not bump the
  protocol version" rule are for.
- needle-guide's `server/schemas/firmware/` fork is now redundant and is deleted
  by a follow-up consumer PR. Until then, two copies exist and only one is
  canonical.
- A stale pin is now possible where it was not before: a consumer can sit on
  `v0.1.0` while the contract has moved. The heartbeat's optional
  `protocol_package_version` exists for exactly that — an operator looking at
  two disagreeing screens can tell which side is behind without opening either
  build.
- The angle conversions gained a semantic change on the way in: every function
  returns `null` for a non-finite input, where the per-app helpers returned
  `NaN`. A `NaN` angle survives a subtraction, a rounding and a `?? 0` and lands
  on a display; `null` cannot, because every readout in both apps already
  branches on "no angle". Consumers adopting this package must check that branch
  exists where they call it.

### What breaks this in six months

- **Drift, in the one place generation cannot reach.** The shared constants are
  generated, but nothing forces a consumer to *use* them: needle-guide can keep
  its own `DEFAULT_INCLINATION_STREAM_PORT = 8790` beside the imported one. The
  fix is in the consumer PRs — each one deletes its local literal and imports,
  and that deletion is the thing to check when reviewing them. This repository
  cannot enforce it.
- **A stale pin nobody notices.** Mitigated, not solved, by
  `protocol_package_version` on the heartbeat. A real fix would be a check in
  each consumer's CI comparing its pin against the newest tag; that is a
  consumer-side change and is not built yet.
- **Silent failure through a weak generated validator.** The two known cases are
  fixed and asserted by the `invalid` half of `tests/samples.json`. A third
  would look the same: a validator that passes every positive test. Every new
  contract needs a *rejection* sample, not just an acceptance one.
- **The release-please secrets never being set.** Until `RELEASE_BOT_APP_ID` and
  `RELEASE_BOT_PRIVATE_KEY` exist on this repository, the release workflow fails
  its preflight on every push to main — loudly and by design, rather than
  quietly not tagging.

---

## ADR-0002 — The device reports its envelope contract on the first status payload

**Date:** 2026-09-04
**Status:** accepted

### Context

`gen/c/schema_keys.h` already gives the firmware
`SCHEMA_DEVICE_ENVELOPE_XVERSION` and its four payload siblings, generated from
the schemas so the device reports the contract it was built against instead of a
hand-kept literal beside it (ADR-0001). Nothing carried those numbers onto the
wire. A host reading the NDJSON stream could not tell which contract the rig on
the other end of the USB cable was built against, and the envelope's own `v` does
not answer it: `v` is `{ "const": 1 }` and has never moved, while the envelope's
`x-version` has — the `ts` → `t_boot_ms` rename took it to `2.0.0`.

So the only way to identify a rig was to infer it from a parse failure: a frame
carrying `ts` is pre-2.0.0 firmware. Diagnosing a mismatch by watching the
validator reject things is exactly the shape of problem this repository exists to
remove, and it is the same shape as the stale-pin problem the angle stream's
optional `protocol_package_version` already answers on the host side. The device
side had no equivalent.

### Decision

**The version rides the first `status` payload**, as an optional
`envelope_schema_version` string with a semver pattern.

Three places could carry it, and the choice is about what an *un-upgraded host*
pays when it meets an upgraded rig. The device schemas are
`additionalProperties: false` (deliberately — the firmware writes both ends of
that wire, so an unexpected key is a bug), which means a host still pinned to the
older payload schema will **reject** any frame carrying a key it has not heard
of. That cost is not avoidable; it is only placeable.

- **On the envelope.** Every frame pays it, forever, for a build-time constant —
  and a host pinned to the old envelope would reject *every frame*, turning a
  version bump into a dead rig.
- **As its own event type** (`type: "hello"`). A new value in the envelope's
  `type` enum, a new payload schema, and — because enum order is load-bearing for
  the C enum a flashed Pico stores — a change to the contract that decides
  whether the two can talk at all. That is a major envelope change to deliver an
  optional diagnostic, and an old host would reject the frame as an unknown type
  anyway.
- **On the first `status` payload.** The device already emits `status` first, so
  the field rides a frame the host is waiting for. The blast radius of the closed
  schema is one status line per session rather than the whole stream, and the
  bump is minor on one payload schema — `payload-status` `1.0.0` → `1.1.0` —
  leaving the envelope and the other three payloads untouched.

The third. The remaining cost is stated plainly under Consequences rather than
being described as backward compatible, which it is not in both directions.

**Once per session, not on every status event.** It is a constant from boot to
boot; the device cannot change it without being reflashed, and `seq` resets per
boot, so "the first status event" is unambiguous on the host side. Repeating it
would add bytes to a line the Pico assembles by hand, and — worse — would invite
a host to treat it as mutable, growing a "version changed mid-session" branch for
something that cannot happen without a power cycle. The host reads it once and
caches it against the session.

**The name says `envelope`, not `schema` or `version`,** even though the field
lives in the *status payload*. It reports the **envelope** schema's `x-version`,
not the status payload's, and that mismatch is the whole reason the name has to
be explicit. There are five device schemas with five independent `x-version`
numbers; a field called `schema_version` would leave every reader to guess which
one, and a wrong guess is a compatibility check that silently compares the wrong
pair of numbers. The envelope is the right one to report because it is the
contract that decides whether a host can frame the stream at all, and it is the
one that has actually moved. The firmware fills the field from
`SCHEMA_DEVICE_ENVELOPE_XVERSION`, so the macro it reads and the key it writes
say the same word.

### Consequences

- **An un-upgraded host rejects an upgraded rig's first status frame.** This is
  the closed-schema cost above, and it makes rollout ordered: bump the host's pin
  before flashing firmware that emits the field. What each host does with a
  rejected status line is a host-side decision — dropping one frame is fine,
  dropping the session is not — and it is the thing to check in the consumer pull
  request rather than something this repository can enforce.
- `tests/samples.json` gains both halves: a first-of-session status frame that
  must parse, and a two-part `"2.0"` that must not. The rejection sample is what
  keeps the semver `pattern` load-bearing; a version string no comparison can be
  trusted on is worse than an absent one, because an absent one is visible.
- `tests/py/test_schemas.py` asserts the sample's number *is*
  `schemas/device/envelope.json`'s current `x-version`. Nothing else would: a
  stale number still satisfies the schema, which only constrains the shape.
- The firmware gains `KEY_ENVELOPE_SCHEMA_VERSION` in its generated header, and
  `tests/c/main.c` pins it. The firmware change is a separate pull request in
  scl3300-stream, after this is tagged.

### What breaks this in six months

- **"Once per session" is a convention no schema can express.** A device that
  emits the field on every status frame validates fine. Accepted: nothing on the
  host breaks, and the cost is bytes. The failure it could cause is host-side —
  a reader that treats a second occurrence as a *change* — and is named here so
  the consumer pull request can check for it.
- **The firmware writing the literal instead of the macro.** The header exists so
  it does not have to, but nothing here can see the firmware's source.
  `tests/c/main.c` proves the macro exists and carries the schema's number; that the
  firmware *uses* it is the one thing the scl3300-stream pull request has to
  show.
- **Drift between the sample and the envelope's real version.** Fixed, not
  mitigated: the test above fails the build the moment the envelope's `x-version`
  moves without the sample following it.
- **The field arriving and nobody reading it.** The wire gains a number and the
  host logs it and no operator ever sees it — which is the same silent-drift
  ending the stale-pin note in ADR-0001 has. The fix is in the consumer: surface
  it where a mismatch is *acted on*, next to the pin it has to agree with, not in
  a debug log.

---

## ADR-0003 — The plan channel is its own contract, inbound, strict and fail-closed

**Date:** 2026-09-04
**Status:** accepted

### Context

needle-simulator computes a planned trajectory from the CT plan. needle-guide
measures the live needle against a plan an operator has typed into its settings
form. Today those are the same four numbers, carried between two screens by a
human: `plan_inclination_deg`, an azimuth, and two entry offsets, retyped by
hand into `shared/planInputs.ts`'s form. Retyping is how the plan gets across
and it is also how the plan gets wrong.

One channel already runs between the two apps, and it is the wrong one to reuse.
needle-guide's angle stream (`schemas/angle-stream/`) is **output only**, and
that is a medical-device posture rather than a convenience — `SYSTEM_SPEC.md`
§5.3: *"There is no code path by which a subscriber can command, configure or
calibrate this app."* Its envelope pins `kind` to the const `evt` to say so, and
`electron/modules/inclinationStreamServer.ts` attaches no `message` listener at
all: an inbound frame is read off the wire by `ws` and discarded.

### Decision

**A new contract directory, `schemas/plan-channel/`, on its own port** —
`PLAN_CHANNEL_DEFAULT_PORT` = 8791 — rather than a new frame type on the angle
stream.

Adding an inbound frame to the angle stream would mean attaching a `message`
listener to the one server whose *lacking* one is a documented safety property.
The stream's schema would have to stop pinning `kind: "evt"`, and every
statement §5.3 makes about it would need re-testing. A second listener costs a
port and buys back the ability to say the old sentence unchanged. The port is
adjacent to 8790 because the two are halves of one conversation between one pair
of apps; `tests/py/test_constants.py` fails if any two default ports here are
equal, so the constraint that used to be a comment in two repos saying "must not
be the other one" (ADR-0001) is now checked.

**Request/response with an explicit `id`.** `kind` ∈ {`req`, `res`}, `type` ∈
{`plan`, `plan_ack`}, and the envelope's `allOf` table **binds the two**: a
`plan` is always a `req` and a `plan_ack` always a `res`. `tools/bundle.mjs`
gained the ability to carry a `then`-pinned const into the generated types and
validators for this, and throws on anything richer than a string `const` —
because a constraint the schema states and the generated validator drops is the
same class of defect as the `allOf` if/then rendering ADR-0001 already refused.

**Two acks per request, under one `id`.** `pending_confirm` says the frame was
understood and is now in front of an operator who has not pressed Apply;
`applied` or `rejected` follows when they act, minutes later, echoing the same
envelope `id`. The alternative — acking `applied` on receipt and letting the
operator's press be invisible — would have the simulator draw a plan the guide
is not measuring against. `PLAN_ACK_TIMEOUT_MS` (5 s) therefore bounds only the
first ack, "was this frame understood at all". Nothing bounds an operator.

**`plan_id` + monotonic `plan_revision`, and re-sends are idempotent.** The
receiver answers a repeat of the same pair with the ack it would have sent and
does not re-prompt a confirm that has already been given, so a sender may retry
after a dropped connection without putting a second dialogue in front of the
operator. `plan_id` is opaque — today a DICOM `SeriesInstanceUID`, and the
pattern deliberately admits more than a UID does, because a rehearsal plan is
not a DICOM series and a receiver that parsed the id would break on the first
one that was not.

**`additionalProperties: false`, alone among the host-side contracts.** The
angle stream and the tracker hello are open because they are read-only telemetry
whose emitters state that additive optional fields do not bump the protocol
version, and a strict reader there would refuse a peer that is compatible by its
own rule. This wire is not telemetry. A key the receiver does not understand is
a part of the plan it would silently drop, and a plan half-applied is worse than
a plan not applied: the operator sees a plan on screen and has no way to know
which half of it arrived. Fail closed — refuse the frame, answer `rejected` with
a reason.

**Refuse, never clamp,** for every numeric bound, in the same words
`shared/planInputs.ts` already uses for the form. A value outside its range is
rejected and reported; an entry point silently pulled to ±1000 mm, or an
inclination to 90°, is a plan the operator never planned.

**`plan_inclination_deg` and nothing else.** The wire carries the canonical
quantity — inclination from vertical — under the name needle-guide already uses
for it. Not console θ, not `ALPHA`. `theta = 90 − inclination` is its own
inverse, so a channel carrying θ is a channel where sending the wrong one is
syntactically perfect and numerically wrong, which is the 5° mismatch ADR-0001
was written about.

### Consequences

- **Rollout is ordered.** Because the schemas are closed, a receiver pinned to
  `v0.2.0` will reject a frame from a sender that has adopted a later, additive
  field. Bump the receiver's pin first. This is the same cost ADR-0002 placed on
  the device wire, accepted for the same reason, and it is why the ack carries a
  `reason` the operator can be shown rather than a silent drop.
- **needle-guide grows an inbound listener,** which is a real change to an app
  whose current selling point is that it has none. It is a *second* server with
  its own port and its own posture, and §5.3's sentence about the angle stream
  stays true verbatim; the consumer pull request is where that gets written down
  on the guide's side, and where the listener's own default-off/loopback posture
  is decided.
- **The bounds are duplicated** between `payload-plan.json` and
  `shared/planInputs.ts` until the Stage 2 consumer change lands. Unlike a
  silent duplicate, a divergence announces itself: the channel refuses the frame
  and answers `rejected` with a reason, so the operator sees a refusal rather
  than a clamped plan. Named under six months below all the same.
- **`tests/samples.json` gains a contract whose emitters do not exist yet.** Its
  provenance strings say so; the file's `$comment` now distinguishes a frame
  copied off a wire from a frame the first emitter must be written to.

### What breaks this in six months

- **The bounds drift.** needle-guide widens `MAX_ENTRY_OFFSET_MM` and its own
  form starts accepting plans this wire refuses. Self-announcing rather than
  silent (a `rejected` ack with a reason), so it costs an afternoon and not a
  procedure. The durable fix is one-directional and belongs in the Stage 2
  consumer PR: `shared/planInputs.ts` takes its bounds from this package, at
  which point these numbers are the only ones. It is deliberately **not** done
  here, because exporting five range constants nothing imports yet would be
  guessing at the consumer's shape.

  **This happened, on 2026-09-05** — a day after it was written down, not in six
  months. needle-guide (issue #429, PR #456) split `MAX_ENTRY_OFFSET_MM` into
  `MAX_ENTRY_LATERAL_MM` 1000 and `MAX_ENTRY_LONGITUDINAL_MM` 3000, because a
  rehearsal produced a stored `entry_longitudinal_mm` of 1150.1 mm that the
  single shared bound refused. `payload-plan.json` followed at `x-version`
  1.1.0. It cost an afternoon and it announced itself, exactly as predicted — so
  the duplication is survivable, but its **frequency** is now measured rather
  than guessed, and the Stage 2 one-directional fix is worth more than this
  entry assumed.
- **`reason` is optional, and "required when `rejected`" is a rule no schema
  here states.** Conditional requirement needs an `if`/`then` inside a payload,
  which `json-schema-to-zod` renders as a validator that accepts anything — the
  exact failure ADR-0001 refused. So it is the emitter's rule, and the place it
  gets enforced is needle-guide's own tests. Check for it in the consumer PR; a
  rejection an operator cannot act on is the failure this leaves open.
- **A sender that closes the correlation on the first ack.** Then
  `pending_confirm` reads as "done", the operator never presses Apply, and the
  simulator draws a plan the guide is not measuring against — silently, because
  both frames validate. The sample set pins the two-ack sequence to one envelope
  `id` (`tests/py/test_samples.py`), which is as far as this repository can
  reach; the sender's own test is the other half.
- **A third listener taking 8791.** Checked, not remembered: any two default
  ports here being equal fails `tests/py/test_constants.py`, and the check finds
  new `*_PORT` constants by name rather than by a list somebody maintains.
- **The channel shipping and the operator still retyping.** The wire exists and
  nobody wires the UI to it, so the plan crosses by hand as before while a
  second, unused code path rots. That is a product decision, not a contract one,
  and it is Stage 2's to answer.

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

#!/usr/bin/env bash
#
# Regenerate everything under gen/ and dist/ from schemas/, constants/ and
# angles/.
#
# Idempotent by construction: every generator writes a pure function of the
# sources, with no timestamps and no host paths. CI runs this and then
# `git diff --exit-code gen/ dist/`, so an edit made directly to a generated file
# is a red build rather than a change that survives until the next regeneration
# quietly reverts it.
#
# Run from anywhere: paths are resolved against the repository root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Node, specifically, and not whatever JavaScript runtime happens to be around.
# gen/ is a committed artifact that CI diffs byte for byte, so the runtime that
# produces it is part of the contract: a generator run under a different engine
# can format or order its output differently, and the result is a red build on
# somebody else's pull request with no change of theirs to explain it. bun is
# required too (it installs the generators and runs the suites); it is simply
# not the thing that runs them.
for prerequisite in node uv; do
    if ! command -v "$prerequisite" >/dev/null 2>&1; then
        echo "tools/gen.sh needs \`$prerequisite\` on PATH and cannot find it." >&2
        echo "See README.md > Working on it for the toolchain this repository expects." >&2
        exit 127
    fi
done

echo "==> bundling schemas"
node tools/bundle.mjs

echo "==> TypeScript (types, zod, constants, angles, index)"
node tools/gen-ts.mjs

echo "==> Python (models, constants, angles, __init__)"
uv run --frozen python tools/gen-py.py

echo "==> compiled dist/ (ESM + CommonJS, from gen/ts)"
# After the TypeScript generator, never before: dist/ is the compiled form of
# gen/ts, so building it from a stale gen/ts would publish yesterday's contract
# to every consumer that loads this package through plain `node`.
node tools/build-ts.mjs

echo "==> C header (device schemas only)"
# Device schemas ONLY, and the glob is the exclusion: the firmware has no
# business knowing about the host-side angle stream, the tracker handshake or
# the plan channel, and generating KEY_* macros for them would put host
# vocabulary — plan_inclination_deg, pending_confirm — into the Pico's
# namespace and its flash for a wire it never speaks.
uv run --frozen python tools/gen_schema_header.py \
    --schemas schemas/device/*.json \
    --out gen/c/schema_keys.h

echo "==> done"

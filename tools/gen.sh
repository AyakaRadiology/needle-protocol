#!/usr/bin/env bash
#
# Regenerate everything under gen/ from schemas/, constants/ and angles/.
#
# Idempotent by construction: every generator writes a pure function of the
# sources, with no timestamps and no host paths. CI runs this and then
# `git diff --exit-code gen/`, so an edit made directly to a generated file is a
# red build rather than a change that survives until the next regeneration
# quietly reverts it.
#
# Run from anywhere: paths are resolved against the repository root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> bundling schemas"
node tools/bundle.mjs

echo "==> TypeScript (types, zod, constants, angles, index)"
node tools/gen-ts.mjs

echo "==> Python (models, constants, angles, __init__)"
uv run --frozen python tools/gen-py.py

echo "==> C header (device schemas only)"
# Device schemas ONLY. The firmware has no business knowing about the host-side
# angle stream or the tracker handshake, and generating KEY_* macros for them
# would put host vocabulary into the Pico's namespace.
uv run --frozen python tools/gen_schema_header.py \
    --schemas schemas/device/*.json \
    --out gen/c/schema_keys.h

echo "==> done"

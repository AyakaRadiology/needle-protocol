#!/usr/bin/env bash
#
# The unbundled-Node consumer test.
#
# needle-guide's Electron main process is tsc-emitted and run by plain `node`,
# with no bundler in the path. That consumer is the reason this package ships a
# compiled dist/: while `exports` pointed at gen/ts/*.ts, importing a VALUE from
# here threw ERR_UNSUPPORTED_NODE_MODULES_TYPE_STRIPPING and the consumer went
# back to keeping its own copy of the constant. Every other suite in this
# repository runs against the SOURCE, so not one of them can see that failure.
#
# What this checks, and why in this shape:
#
#   * `bun pm pack`, then extract — not a `file:` dependency on the working
#     tree. A file: dep is a symlink to the whole repo, so it resolves paths
#     `files` excludes; the tarball is what a consumer's `bun install` of the
#     git dependency actually materialises, so a dist/ missing from `files`
#     fails here and passes under a symlink.
#   * Values, not types. A type-only import survives type stripping, which is
#     what made the original breakage look like a packaging nit.
#   * `import()` AND `require()`, because needle-guide compiles its main process
#     to ESM and its preload to CommonJS and both graphs reach the files that
#     import this package.
#   * All five code entry points, `./zod` included. It is the one whose
#     resolution can break on its own, because it is the only one that reaches
#     the optional `zod` peer.
#   * Both published DATA files, `angles/vectors.json` and
#     `tests/samples.json`. A data file only reaches a consumer if it is BOTH
#     listed in `files` (or the tarball has no such file) and named in
#     `exports` (or Node answers ERR_PACKAGE_PATH_NOT_EXPORTED, which is what
#     sent needle-simulator back to reading `angles/vectors.json` off a
#     filesystem path). Neither half is visible to a suite that reads these
#     files from the working tree, and every other suite here does exactly
#     that.
#
# No network: pack, extract, and link the `zod` already in this repository's
# node_modules (v3 has no dependencies of its own, so the link is the whole
# install).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

for prerequisite in node bun tar; do
    if ! command -v "$prerequisite" >/dev/null 2>&1; then
        echo "tests/consumer/run.sh needs \`$prerequisite\` on PATH and cannot find it." >&2
        exit 127
    fi
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "==> packing the tarball a consumer would install"
bun pm pack --destination "$WORK" >/dev/null
TARBALL="$(find "$WORK" -maxdepth 1 -name '*.tgz' -print -quit)"
if [ -z "$TARBALL" ]; then
    echo "::error::bun pm pack produced no tarball." >&2
    exit 1
fi

CONSUMER="$WORK/consumer"
mkdir -p "$CONSUMER/node_modules/needle-protocol"
# The tarball's single top-level directory is `package/`; strip it.
tar -xzf "$TARBALL" -C "$CONSUMER/node_modules/needle-protocol" --strip-components=1

# The optional peer, so `needle-protocol/zod` is exercised too. A symlink, not a
# copy: Node resolves through it, and zod is the only package involved.
if [ ! -d "$ROOT/node_modules/zod" ]; then
    echo "::error::tests/consumer/run.sh needs the zod peer at $ROOT/node_modules/zod. Run \`bun install\` first." >&2
    exit 1
fi
ln -s "$ROOT/node_modules/zod" "$CONSUMER/node_modules/zod"

# A consumer, not a workspace member: `"type": "module"` so the ESM probe is a
# plain .js, and no dependency on this repo's node_modules.
cat >"$CONSUMER/package.json" <<'JSON'
{
    "name": "needle-protocol-consumer-probe",
    "private": true,
    "version": "0.0.0",
    "type": "module"
}
JSON

# The two values the probes assert on: one plain constant (the whole point of
# the package) and one function (which type stripping cannot fake).
EXPECTED_PORT=8790
# consoleThetaFromInclination(30) === 60, from angles/SPEC.md's `theta = 90 - inclination`.
EXPECTED_THETA=60

# The two data files are asserted on their CONTENT, not merely on resolving: a
# floor on the shared angle cases (they only ever get added to) and one sample
# named by hand. A probe that only checked the import would still pass against
# an empty file.
#
# Exported, and read by the probes out of the environment, because both probes
# make the same two assertions and neither can ride on the stdout comparison
# below: that one is an equality, and the angle-case count is expected to grow.
export MINIMUM_ANGLE_CASES=59
export EXPECTED_SAMPLE_NAME=device-status-ready-first-of-session

cat >"$CONSUMER/esm-probe.mjs" <<'JS'
import assert from 'node:assert/strict';
import { env } from 'node:process';
import {
    ANGLE_STREAM_DEFAULT_PORT,
    consoleThetaFromInclination,
} from 'needle-protocol';
import { ANGLE_STREAM_DEFAULT_PORT as fromConstants } from 'needle-protocol/constants';
import { consoleThetaFromInclination as fromAngles } from 'needle-protocol/angles';
import { DevicePayloadStatusSchema } from 'needle-protocol/zod';
import vectors from 'needle-protocol/angles/vectors.json' with { type: 'json' };
import samples from 'needle-protocol/tests/samples.json' with { type: 'json' };

assert.equal(typeof DevicePayloadStatusSchema.parse, 'function', 'needle-protocol/zod did not resolve to a validator');
assert.ok(
    vectors.cases.length >= Number(env.MINIMUM_ANGLE_CASES),
    `needle-protocol/angles/vectors.json carries ${vectors.cases.length} cases, fewer than the ${env.MINIMUM_ANGLE_CASES} this test expects`,
);
assert.ok(
    samples.valid.some((sample) => sample.name === env.EXPECTED_SAMPLE_NAME),
    `needle-protocol/tests/samples.json has no valid sample named ${env.EXPECTED_SAMPLE_NAME}`,
);
assert.equal(typeof ANGLE_STREAM_DEFAULT_PORT, 'number');
assert.equal(typeof consoleThetaFromInclination, 'function');
assert.equal(fromConstants, ANGLE_STREAM_DEFAULT_PORT, 'needle-protocol/constants disagrees with the root entry point');
assert.equal(fromAngles(30), consoleThetaFromInclination(30), 'needle-protocol/angles disagrees with the root entry point');

console.log(`${ANGLE_STREAM_DEFAULT_PORT} ${consoleThetaFromInclination(30)}`);
JS

cat >"$CONSUMER/cjs-probe.cjs" <<'JS'
const assert = require('node:assert/strict');
const { env } = require('node:process');
const { ANGLE_STREAM_DEFAULT_PORT, consoleThetaFromInclination } = require('needle-protocol');
const { ANGLE_STREAM_DEFAULT_PORT: fromConstants } = require('needle-protocol/constants');
const { consoleThetaFromInclination: fromAngles } = require('needle-protocol/angles');
const { DevicePayloadStatusSchema } = require('needle-protocol/zod');
const vectors = require('needle-protocol/angles/vectors.json');
const samples = require('needle-protocol/tests/samples.json');

assert.equal(typeof DevicePayloadStatusSchema.parse, 'function', 'needle-protocol/zod did not resolve to a validator');
assert.ok(
    vectors.cases.length >= Number(env.MINIMUM_ANGLE_CASES),
    `needle-protocol/angles/vectors.json carries ${vectors.cases.length} cases, fewer than the ${env.MINIMUM_ANGLE_CASES} this test expects`,
);
assert.ok(
    samples.valid.some((sample) => sample.name === env.EXPECTED_SAMPLE_NAME),
    `needle-protocol/tests/samples.json has no valid sample named ${env.EXPECTED_SAMPLE_NAME}`,
);
assert.equal(typeof ANGLE_STREAM_DEFAULT_PORT, 'number');
assert.equal(typeof consoleThetaFromInclination, 'function');
assert.equal(fromConstants, ANGLE_STREAM_DEFAULT_PORT, 'needle-protocol/constants disagrees with the root entry point');
assert.equal(fromAngles(30), consoleThetaFromInclination(30), 'needle-protocol/angles disagrees with the root entry point');

console.log(`${ANGLE_STREAM_DEFAULT_PORT} ${consoleThetaFromInclination(30)}`);
JS

expect() {
    local label="$1" probe="$2"
    echo "==> $label"
    local got
    # `--experimental-strip-types` is deliberately NOT passed: the point is that
    # a stock `node` loads this package.
    got="$(cd "$CONSUMER" && node "$probe")"
    if [ "$got" != "$EXPECTED_PORT $EXPECTED_THETA" ]; then
        echo "::error::$label loaded the package but read the wrong values: expected '$EXPECTED_PORT $EXPECTED_THETA', got '$got'." >&2
        exit 1
    fi
    echo "    ANGLE_STREAM_DEFAULT_PORT=$EXPECTED_PORT consoleThetaFromInclination(30)=$EXPECTED_THETA"
}

expect "import() from an ESM consumer" ./esm-probe.mjs
expect "require() from a CommonJS consumer" ./cjs-probe.cjs

echo "==> unbundled Node loads needle-protocol from the packed tarball"

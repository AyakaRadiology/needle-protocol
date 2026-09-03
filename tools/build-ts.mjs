/**
 * Compile gen/ts into the published `dist/` — ESM and CommonJS, each with its
 * own declarations.
 *
 * ## Why a build output exists at all
 *
 * `exports` used to point straight at `gen/ts/*.ts`. That works for a bundler
 * (Vite compiles the source it is handed) and fails for anything that loads
 * this package through plain `node`: needle-guide's Electron main process is
 * tsc-emitted and run unbundled, so importing a VALUE from here raised
 * ERR_UNSUPPORTED_NODE_MODULES_TYPE_STRIPPING and the consumer went back to
 * keeping its own copy of the constant — the drift this repository exists to
 * remove. Types alone survived, which made the failure look like a packaging
 * nit instead of the package not doing its job.
 *
 * ## Why both module systems
 *
 * needle-guide compiles its main process to ESM (tsconfig.node.json) and its
 * preload to CommonJS (tsconfig.preload.json), and tsc emits JavaScript for
 * every file an entry point's graph REACHES. Both graphs reach `shared/`, which
 * is precisely where the mirrored constants this package replaces live. So the
 * same import lands in an ESM emit and a CommonJS emit, and shipping ESM only
 * would leave the CommonJS half on Node's `require(esm)` interop — which is
 * real but narrower (no top-level await, namespace-object semantics) and not
 * something a shared contract should make a consumer reason about.
 *
 * ## Why it is committed
 *
 * Consumers pin a git tag; a git dependency has no publish step and bun runs no
 * `prepare` for one. An uncommitted `dist/` is therefore an empty `dist/` on
 * the consumer's disk. It is committed for the same reason `gen/` is, and CI
 * guards it the same way: regenerate, then `git diff --exit-code`, so a
 * hand-edit under dist/ is a red build rather than a change the next
 * regeneration quietly reverts.
 *
 * ## Why only gen/ts is compiled, when the sources are gen/ts AND angles/ts
 *
 * `gen/ts/angles.ts` IS `angles/ts/src/index.ts`, copied verbatim by
 * tools/gen-ts.mjs. Compiling the second copy too would put two independently
 * emitted angle modules in one package, and a consumer reaching the wrong one
 * is the class of bug this repository exists to prevent. `needle-protocol/angles`
 * resolves into this build, so the angles module ships; it just ships once.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, rmSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/\/$/, '');
const DIST = join(ROOT, 'dist');

/** tsc from node_modules, not from PATH: the compiler version is part of the
 *  emitted artifact CI diffs, and the one in package.json is the pinned one. */
const TSC = join(ROOT, 'node_modules', 'typescript', 'bin', 'tsc');
if (!existsSync(TSC)) {
    console.error('tools/build-ts.mjs needs the pinned TypeScript compiler and cannot find');
    console.error(`  ${TSC}`);
    console.error('Run `bun install` first. See README.md > Working on it.');
    process.exit(127);
}

/**
 * A directory-level `type` marker beside each half.
 *
 * The CommonJS one is load-bearing: the root package.json says
 * `"type": "module"`, which would otherwise make Node parse dist/cjs/*.js as
 * ESM. The ESM one is redundant today and written anyway, so that a future
 * change to the root `type` cannot silently reinterpret dist/esm as CommonJS.
 */
const TYPE_MARKERS = {
    esm: 'module',
    cjs: 'commonjs',
};

const PASSES = [
    { dir: 'esm', project: 'tsconfig.build.esm.json' },
    { dir: 'cjs', project: 'tsconfig.build.cjs.json' },
];

// Clean, not incremental: a file deleted from gen/ts must disappear from dist/
// too, and a stale leftover would otherwise sit there passing every check until
// somebody imported it.
rmSync(DIST, { recursive: true, force: true });

for (const { dir, project } of PASSES) {
    console.log(`==> dist/${dir} (${project})`);
    execFileSync(process.execPath, [TSC, '--project', project], {
        cwd: ROOT,
        stdio: 'inherit',
    });
    const out = join(DIST, dir);
    mkdirSync(out, { recursive: true });
    writeFileSync(
        join(out, 'package.json'),
        `${JSON.stringify({ type: TYPE_MARKERS[dir] }, null, 4)}\n`,
    );
}

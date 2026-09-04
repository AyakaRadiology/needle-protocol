/**
 * Resolve every cross-file `$ref` in schemas/ into one self-contained document
 * per contract, written to build/bundled/.
 *
 * Why this step exists at all: the schemas reference each other by `$id`
 * (`urn:pico:schema:payload-data`, `urn:needle:schema:angle-stream-frame-theta`),
 * which is correct — a URN is a name, not a URL, so nothing has to be published
 * anywhere for the contract to be readable. But none of the three generators
 * downstream resolve URNs across files: they each want a document that stands
 * alone. Rather than teaching three tools the same trick three times (and
 * getting three subtly different answers), the refs are inlined once, here, and
 * every generator reads the same bundled input.
 *
 * The bundles are BUILD OUTPUT, not committed: gen/ is the committed artifact
 * and build/ is gitignored. Inlining is safe because none of these schemas are
 * recursive — a cycle is detected and reported rather than expanded forever.
 *
 * Key order is preserved throughout. `x-version` and enum arrays both depend on
 * it (the C generator's enum values ARE the array indices), and a bundler that
 * sorted keys would be a silent ABI change.
 */
import { readdirSync, readFileSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { join, relative, dirname } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/\/$/, '');
const SCHEMA_DIR = join(ROOT, 'schemas');
const OUT_DIR = join(ROOT, 'build', 'bundled');

/** Every *.json under schemas/, depth-first, path-sorted for stable output. */
export function schemaFiles(dir = SCHEMA_DIR) {
    const out = [];
    for (const entry of readdirSync(dir, { withFileTypes: true }).sort((a, b) => (a.name < b.name ? -1 : 1))) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) out.push(...schemaFiles(full));
        else if (entry.name.endsWith('.json')) out.push(full);
    }
    return out;
}

/** Slug used for every generated artifact name: `device/envelope.json` →
 *  `device-envelope`. Derived from the path, so a file that moves renames its
 *  generated type — which is exactly the review signal you want. */
export function slugOf(file) {
    return relative(SCHEMA_DIR, file).replace(/\.json$/, '').replace(/[/\\]/g, '-');
}

function loadAll() {
    const byFile = new Map();
    const byId = new Map();
    for (const file of schemaFiles()) {
        const schema = JSON.parse(readFileSync(file, 'utf8'));
        byFile.set(file, schema);
        if (typeof schema.$id === 'string') {
            if (byId.has(schema.$id)) {
                throw new Error(`Duplicate $id ${schema.$id}: ${byId.get(schema.$id).file} and ${file}`);
            }
            byId.set(schema.$id, { file, schema });
        }
    }
    return { byFile, byId };
}

/**
 * Replace `{"$ref": "<some other file's $id>"}` with that file's schema.
 *
 * Refs beginning with `#` are internal JSON pointers and are left exactly as
 * they are: the generators handle those, and rewriting them would break the
 * `$defs` reuse in the envelope schemas.
 */
function inline(node, byId, stack) {
    if (Array.isArray(node)) return node.map((child) => inline(child, byId, stack));
    if (node === null || typeof node !== 'object') return node;

    const ref = node.$ref;
    if (typeof ref === 'string' && !ref.startsWith('#')) {
        const target = byId.get(ref);
        if (!target) {
            throw new Error(`Unresolvable $ref ${ref}. Known ids: ${[...byId.keys()].join(', ')}`);
        }
        if (stack.includes(ref)) {
            throw new Error(`Recursive $ref chain: ${[...stack, ref].join(' -> ')}`);
        }
        const { $id, $schema, ...body } = target.schema;
        // Sibling keys alongside a $ref are legal in 2020-12 and would be lost
        // by a blind replacement, so refuse rather than silently drop them.
        const siblings = Object.keys(node).filter((k) => k !== '$ref');
        if (siblings.length > 0) {
            throw new Error(`$ref to ${ref} has sibling keys ${siblings.join(', ')}; inlining would drop them.`);
        }
        return inline(body, byId, [...stack, ref]);
    }

    const out = {};
    for (const [key, value] of Object.entries(node)) out[key] = inline(value, byId, stack);
    return out;
}

export function bundleAll() {
    const { byFile, byId } = loadAll();
    /** `$id` → generated-artifact slug, so a generator can turn a `$ref` back
     *  into the NAME of the thing it points at instead of inlining it. */
    const idToSlug = new Map();
    for (const [id, target] of byId) idToSlug.set(id, slugOf(target.file));

    const bundles = [];
    for (const [file, schema] of byFile) {
        const slug = slugOf(file);
        const bundled = inline(schema, byId, [schema.$id ?? file]);
        bundles.push({ file, path: relative(ROOT, file), slug, schema, bundled });
    }
    bundles.sort((a, b) => (a.slug < b.slug ? -1 : 1));
    return { bundles, idToSlug };
}

/**
 * Every non-`payload` property a `then` branch pins to a literal, as
 * `{ key: value }` — the plan-channel envelope uses it to bind `kind` to
 * `type`, so a `res` cannot arrive wearing a request's `type`.
 *
 * Anything else under `then.properties` throws. That is the point: a
 * constraint the generators do not carry into the emitted validators is a
 * constraint the schema states and nothing enforces, which is the exact failure
 * this whole module exists to refuse.
 */
function pinnedConsts(thenProps, where) {
    const consts = {};
    for (const [key, value] of Object.entries(thenProps)) {
        if (key === 'payload') continue;
        const extra = Object.keys(value ?? {}).filter((k) => k !== 'const' && k !== 'description' && k !== '$comment');
        if (typeof value?.const !== 'string' || extra.length > 0) {
            throw new Error(
                `${where}: \`then\` constrains \`${key}\` with something other than a string \`const\`` +
                    `${extra.length > 0 ? ` (also: ${extra.join(', ')})` : ''}. The generators carry a ` +
                    `pinned const into the emitted types and validators and nothing else, so anything ` +
                    `richer would be stated in the schema and enforced nowhere.`
            );
        }
        consts[key] = value.const;
    }
    return consts;
}

/**
 * The `allOf: [{if, then}]` payload table of an envelope schema, or null when
 * the schema has no conditional shape at all.
 *
 * Throws on an `allOf` that is present but not this exact pattern: the whole
 * reason this function exists is that the fallback silently validates nothing.
 */
export function discriminatorTable(schema, idToSlug, where) {
    if (!Array.isArray(schema.allOf)) return null;

    const branches = [];
    let discriminator = null;
    for (const branch of schema.allOf) {
        const ifProps = branch?.if?.properties;
        const thenProps = branch?.then?.properties;
        const keys = ifProps ? Object.keys(ifProps) : [];
        const ref = thenProps?.payload?.$ref;
        if (keys.length !== 1 || typeof ifProps[keys[0]].const !== 'string' || typeof ref !== 'string') {
            throw new Error(
                `${where}: allOf branch is not the recognised "if <key> const, then payload $ref" shape. ` +
                    `Teach tools/gen-ts.mjs the new shape — do NOT fall back to the generic path, which ` +
                    `emits a validator that accepts anything.`
            );
        }
        if (discriminator === null) discriminator = keys[0];
        else if (discriminator !== keys[0]) {
            throw new Error(`${where}: allOf branches discriminate on both ${discriminator} and ${keys[0]}.`);
        }
        const slug = idToSlug.get(ref);
        if (!slug) throw new Error(`${where}: payload $ref ${ref} names no schema.`);
        const consts = pinnedConsts(thenProps, where);
        if (discriminator in consts) {
            throw new Error(`${where}: \`then\` re-pins the discriminator \`${discriminator}\`; the \`if\` already did.`);
        }
        branches.push({ value: ifProps[keys[0]].const, slug, consts });
    }

    const declared = schema.properties?.[discriminator]?.enum;
    if (Array.isArray(declared)) {
        const covered = branches.map((b) => b.value);
        const missing = declared.filter((v) => !covered.includes(v));
        if (missing.length > 0) {
            throw new Error(
                `${where}: \`${discriminator}\` allows ${missing.join(', ')} but no allOf branch gives ` +
                    `${missing.length > 1 ? 'those values' : 'that value'} a payload schema.`
            );
        }
    }
    return { discriminator, branches };
}

/** The schema minus its conditional table — the fields every variant shares. */
export function baseOf(schema) {
    const { allOf, ...rest } = schema;
    return rest;
}

function main() {
    rmSync(OUT_DIR, { recursive: true, force: true });
    mkdirSync(OUT_DIR, { recursive: true });
    const { bundles, idToSlug } = bundleAll();
    const contracts = [];
    for (const { slug, path, schema, bundled } of bundles) {
        const out = join(OUT_DIR, `${slug}.json`);
        mkdirSync(dirname(out), { recursive: true });
        writeFileSync(out, `${JSON.stringify(bundled, null, 2)}\n`);
        contracts.push({ slug, path, table: discriminatorTable(schema, idToSlug, path) });
    }
    // The manifest exists so the Python generator does not re-implement the
    // if/then-table reading in a second language, and cannot come to a
    // different answer about which contracts are discriminated unions.
    writeFileSync(join(ROOT, 'build', 'contracts.json'), `${JSON.stringify(contracts, null, 2)}\n`);
    console.log(`[bundle] ${bundles.length} schema(s) -> ${relative(ROOT, OUT_DIR)}/ (+ build/contracts.json)`);
}

if (import.meta.url === `file://${process.argv[1]}`) main();

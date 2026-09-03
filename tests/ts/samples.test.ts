/**
 * The generated zod validators against real frames.
 *
 * `tests/samples.json` holds frames as the actual emitters produce them, with
 * provenance on each, and is shared with `tests/py/test_samples.py`. The
 * `invalid` half matters more than the `valid` half: a generated validator that
 * accepts everything passes every positive test there is.
 */
import { describe, expect, it } from 'vitest';
import samples from '../samples.json' with { type: 'json' };
import * as validators from '../../gen/ts/zod.js';

type Sample = { contract: string; name: string; frame: unknown };

const SCHEMAS = validators as unknown as Record<string, { safeParse: (v: unknown) => { success: boolean } }>;

function schemaFor(contract: string) {
    const schema = SCHEMAS[`${contract}Schema`];
    if (!schema) throw new Error(`gen/ts/zod.ts exports no ${contract}Schema`);
    return schema;
}

describe('generated zod validators', () => {
    it('cover every contract the samples name', () => {
        const contracts = new Set(
            [...samples.valid, ...samples.invalid].map((s) => (s as Sample).contract)
        );
        for (const contract of contracts) expect(() => schemaFor(contract)).not.toThrow();
        // The envelopes are the ones the off-the-shelf generator gets wrong, so
        // a sample set that stopped covering them would stop covering the bug.
        expect(contracts).toContain('DeviceEnvelope');
        expect(contracts).toContain('AngleStreamEnvelope');
    });

    for (const sample of samples.valid as Sample[]) {
        it(`accepts ${sample.name}`, () => {
            const result = schemaFor(sample.contract).safeParse(sample.frame);
            expect(result.success, JSON.stringify(result, null, 2)).toBe(true);
        });
    }

    for (const sample of samples.invalid as Sample[]) {
        it(`rejects ${sample.name}`, () => {
            expect(schemaFor(sample.contract).safeParse(sample.frame).success).toBe(false);
        });
    }
});

describe('the parse hot path stays free of zod', () => {
    it('the default entry point does not import it', async () => {
        const { readFileSync } = await import('node:fs');
        const source = readFileSync(new URL('../../gen/ts/index.ts', import.meta.url), 'utf8');
        // needle-simulator parses angle frames at up to 60 Hz and needle-guide
        // reads these constants in Electron's main process at startup. A `zod`
        // import reachable from the default entry point would put a schema
        // library in both. Prose mentioning zod is fine and is why this looks
        // at import/export statements rather than at the whole file.
        const moduleSpecifiers = [...source.matchAll(/^\s*(?:import|export)\b[^\n]*?from\s+'([^']+)'/gm)].map(
            (match) => match[1],
        );
        expect(moduleSpecifiers.length).toBeGreaterThan(0);
        for (const specifier of moduleSpecifiers) {
            expect(specifier, `${specifier} is reachable from the default entry point`).not.toMatch(/zod/);
        }
    });
});

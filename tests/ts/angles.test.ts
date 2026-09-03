/**
 * The TypeScript half of the shared angle contract.
 *
 * Every case in `angles/vectors.json` runs here and, unchanged, in
 * `tests/py/test_angles.py`. That is the point: the two reference
 * implementations are the same contract in two languages, and a conversion that
 * is only tested on one side is a conversion that is only right on one side.
 */
import { describe, expect, it } from 'vitest';
import vectors from '../../angles/vectors.json' with { type: 'json' };
import constantsSource from '../../constants/constants.json' with { type: 'json' };
import * as angles from '../../angles/ts/src/index.js';
import { CONSOLE_THETA_VERTICAL_DEG as GENERATED_CONSOLE_THETA_VERTICAL_DEG } from '../../gen/ts/constants.js';

type Case = {
    id: string;
    fn: string;
    args: unknown[];
    expect: unknown;
    note?: string;
};

const TOLERANCE = vectors.parameters.TOLERANCE_DEG;

/** JSON has no NaN or Infinity literal; `angles/vectors.json` documents these
 *  stand-ins under `encoding`, and every harness decodes them the same way. */
const SENTINELS: Record<string, number> = {
    NaN: Number.NaN,
    Infinity: Number.POSITIVE_INFINITY,
    '-Infinity': Number.NEGATIVE_INFINITY,
};

function decode(value: unknown): unknown {
    if (typeof value === 'string' && value in SENTINELS) return SENTINELS[value];
    if (Array.isArray(value)) return value.map(decode);
    if (value !== null && typeof value === 'object') {
        return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, decode(v)]));
    }
    return value;
}

const IMPLEMENTATIONS = angles as unknown as Record<string, (...args: unknown[]) => unknown>;

describe('shared angle vectors', () => {
    it('covers enough of the surface to be worth trusting', () => {
        // A vector file that quietly shrank would still pass every case in it.
        expect(vectors.cases.length).toBeGreaterThanOrEqual(30);
        const ids = vectors.cases.map((c) => c.id);
        expect(new Set(ids).size).toBe(ids.length);
        const exercised = new Set(vectors.cases.map((c) => c.fn));
        for (const fn of [
            'consoleThetaFromInclination',
            'inclinationFromConsoleTheta',
            'consoleAlphaInputFromInclination',
            'inclinationFromConsoleAlpha',
            'consoleThetaError',
            'inclinationError',
            'angleBetweenDeg',
            'needleInclinationFromVertical',
        ]) {
            expect(exercised, `no vector exercises ${fn}`).toContain(fn);
        }
    });

    for (const testCase of vectors.cases as Case[]) {
        it(testCase.id, () => {
            const fn = IMPLEMENTATIONS[testCase.fn];
            if (typeof fn !== 'function') {
                throw new Error(`angles module exports no ${testCase.fn}`);
            }
            const actual = fn(...testCase.args.map(decode));
            const expected = testCase.expect;

            if (expected === null) {
                expect(actual).toBeNull();
                return;
            }
            if (typeof expected === 'object') {
                const record = expected as Record<string, number | boolean>;
                expect(actual).not.toBeNull();
                const got = actual as angles.NeedleInclination;
                expect(got.inclinationDeg).toBeCloseTo(record.inclinationDeg as number, 9);
                expect(got.consoleThetaDeg).toBeCloseTo(record.consoleThetaDeg as number, 9);
                expect(got.pointsUp).toBe(record.pointsUp);
                return;
            }
            expect(actual).not.toBeNull();
            expect(Math.abs((actual as number) - (expected as number))).toBeLessThan(TOLERANCE);
            if (expected === 0) {
                // `-0` renders as "-0.0" on a readout; the sign is part of the contract.
                expect(Object.is(actual, -0)).toBe(false);
            }
        });
    }
});

describe('constants agree across every place they are written', () => {
    it('the angles module matches angles/vectors.json', () => {
        expect(angles.CONSOLE_THETA_VERTICAL_DEG).toBe(
            vectors.parameters.CONSOLE_THETA_VERTICAL_DEG
        );
        expect(angles.HORIZONTAL_INCLINATION_DEG).toBe(
            vectors.parameters.HORIZONTAL_INCLINATION_DEG
        );
        expect(angles.MIN_NEEDLE_LENGTH_MM).toBe(vectors.parameters.MIN_NEEDLE_LENGTH_MM);
    });

    it('the angles module matches constants/constants.json', () => {
        // The angles module keeps its own copy so it can stay dependency-free.
        // This is what stops the two copies from ever meaning different things.
        expect(angles.CONSOLE_THETA_VERTICAL_DEG).toBe(
            constantsSource.constants.CONSOLE_THETA_VERTICAL_DEG.value
        );
    });

    it('the generated constants match their source', () => {
        expect(GENERATED_CONSOLE_THETA_VERTICAL_DEG).toBe(
            constantsSource.constants.CONSOLE_THETA_VERTICAL_DEG.value
        );
    });
});

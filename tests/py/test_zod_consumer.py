"""Published validators must type-check and compose with both Zod majors."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = json.loads((ROOT / "package.json").read_text())


@pytest.mark.parametrize("version", ["3.25.76", "4.6.5"])
def test_zod_consumer(version, tmp_path):
    assert PACKAGE["peerDependencies"]["zod"] == "^3.25.0 || ^4.0.0"
    (tmp_path / "package.json").write_text(json.dumps({
        "private": True, "dependencies": {"zod": version},
    }))
    subprocess.run(
        ["bun", "install", "--prefer-offline", "--ignore-scripts"],
        cwd=tmp_path, check=True, capture_output=True, text=True, timeout=120,
    )
    package = tmp_path / "node_modules" / "needle-protocol"
    package.mkdir()
    (package / "package.json").write_text(json.dumps(PACKAGE))
    shutil.copytree(ROOT / "dist", package / "dist")
    shutil.copytree(ROOT / "gen/ts", package / "gen/ts")
    source = """
import { z } from 'zod';
import * as validators from 'needle-protocol/zod';
import { AngleStreamFrameHeartbeatSchema, TrackerHelloSchema } from 'needle-protocol/zod';
type Hello = z.infer<typeof TrackerHelloSchema>;
declare const hello: Hello;
const protocolVersion: number = hello.protocol_version;
type Assert<T extends true> = T;
type ProtocolVersionIsNumber = Assert<number extends Hello['protocol_version'] ? true : false>;
const CaptureSchema = z.object({ hello: TrackerHelloSchema });
type CaptureVersionIsNumber = Assert<Equal<z.infer<typeof CaptureSchema>['hello']['protocol_version'], number>>;
const OptionalHelloSchema = TrackerHelloSchema.optional();
const NullableHelloSchema = TrackerHelloSchema.nullable();
const HelloArraySchema = TrackerHelloSchema.array();
const UnwrappedHelloSchema = OptionalHelloSchema.unwrap();
const ExtendedHelloSchema = TrackerHelloSchema.extend({ label: z.string() });
const OptionalExtendedHelloSchema = ExtendedHelloSchema.optional();
declare const optionalHello: z.infer<typeof OptionalHelloSchema>;
const optionalVersion: number | undefined = optionalHello?.protocol_version;
type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;
type OptionalHello = Assert<Equal<z.infer<typeof OptionalHelloSchema>, Hello | undefined>>;
type NullableHello = Assert<Equal<z.infer<typeof NullableHelloSchema>, Hello | null>>;
type HelloArray = Assert<Equal<z.infer<typeof HelloArraySchema>, Hello[]>>;
type UnwrappedHello = Assert<Equal<z.infer<typeof UnwrappedHelloSchema>, Hello>>;
type ExtendedHello = Assert<Equal<Pick<z.infer<typeof ExtendedHelloSchema>, 'type' | 'protocol_version' | 'label'>,
    { type: 'hello'; protocol_version: number; label: string }>>;
type OptionalExtendedHello = Assert<Equal<z.infer<typeof OptionalExtendedHelloSchema>,
    z.infer<typeof ExtendedHelloSchema> | undefined>>;
const heartbeat = AngleStreamFrameHeartbeatSchema.parse({calibrated: true, link: {state: 'ready', live: true}});
const calibrated: boolean = heartbeat.calibrated;
const parsed = validators.AngleStreamEnvelopeSchema.parse({
    v: 1, kind: 'evt', type: 'heartbeat', ts: '2026-09-04T01:02:03.004Z',
    payload: { calibrated: true, link: { state: 'ready', live: true } },
});
// @ts-expect-error Extra fields on other frame types do not guarantee an inclination number.
parsed.payload.inclination_deg.toFixed(1);
// @ts-expect-error The same applies to theta outside the theta frame.
parsed.payload.theta.toFixed(1);
if (parsed.type === 'inclination' && parsed.payload.inclination_deg !== null) {
    parsed.payload.inclination_deg.toFixed(1);
}
const status = validators.DevicePayloadStatusSchema.parse({ state: 'ready' });
const state: 'init' | 'ready' | 'running' | 'degraded' | 'lost' | 'stopping' | 'stopped' = status.state;
"""
    for extension in ("mts", "cts"):
        (tmp_path / f"consumer.{extension}").write_text(source)
    (tmp_path / "tsconfig.json").write_text(json.dumps({
        "compilerOptions": {
            "module": "NodeNext", "target": "ES2022", "strict": True,
            "skipLibCheck": False, "noEmit": True, "types": [],
        },
        "include": ["consumer.mts", "consumer.cts"],
    }))
    typecheck = subprocess.run(
        ["node", str(ROOT / "node_modules/typescript/bin/tsc"), "-p", str(tmp_path)],
        capture_output=True, text=True, timeout=60,
    )
    errors = []
    for extension in ("mjs", "cjs"):
        (tmp_path / f"runtime.{extension}").write_text(
            "import { z } from 'zod';\n"
            "import { DevicePayloadStatusSchema as status, TrackerHelloSchema } from 'needle-protocol/zod';\n"
            if extension == "mjs" else
            "const { z } = require('zod');\n"
            "const { DevicePayloadStatusSchema: status, TrackerHelloSchema } = require('needle-protocol/zod');\n"
        )
        with (tmp_path / f"runtime.{extension}").open("a") as runtime:
            runtime.write("if (!status.safeParse({state: 'ready'}).success || "
                          "status.safeParse({state: 'invalid'}).success) throw Error('validation');\n")
            runtime.write("""
const capture = z.object({ hello: TrackerHelloSchema });
if (!capture.safeParse({ hello: { type: 'hello', protocol_version: 1 } }).success ||
    capture.safeParse({ hello: { type: 'hello', protocol_version: '1' } }).success) {
    throw Error('nested tracker hello validation');
}
""")
        result = subprocess.run(
            ["node", f"runtime.{extension}"], cwd=tmp_path, capture_output=True, text=True, timeout=60,
        )
        if result.returncode:
            errors.append(f"{extension}: {result.stderr}")
    assert not errors, "\n".join(errors)
    assert typecheck.returncode == 0, typecheck.stdout + typecheck.stderr

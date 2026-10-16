"""Published validators must type-check against every advertised Zod major."""

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
    source = """
import * as validators from 'needle-protocol/zod';
import { AngleStreamFrameHeartbeatSchema } from 'needle-protocol/zod';
const heartbeat = AngleStreamFrameHeartbeatSchema.parse({calibrated: true, link: {state: 'ready', live: true}});
const calibrated: boolean = heartbeat.calibrated;
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
    result = subprocess.run(
        ["node", str(ROOT / "node_modules/typescript/bin/tsc"), "-p", str(tmp_path)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for extension in ("mjs", "cjs"):
        (tmp_path / f"runtime.{extension}").write_text(
            "import { DevicePayloadStatusSchema as status } from 'needle-protocol/zod';\n"
            if extension == "mjs" else
            "const { DevicePayloadStatusSchema: status } = require('needle-protocol/zod');\n"
        )
        with (tmp_path / f"runtime.{extension}").open("a") as runtime:
            runtime.write("if (!status.safeParse({state: 'ready'}).success || "
                          "status.safeParse({state: 'invalid'}).success) throw Error('validation');\n")
        subprocess.run(["node", f"runtime.{extension}"], cwd=tmp_path, check=True)

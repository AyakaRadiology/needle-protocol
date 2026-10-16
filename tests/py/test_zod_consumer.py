"""Published validators must type-check against every advertised Zod major."""

import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = json.loads((ROOT / "package.json").read_text())
PEERS = PACKAGE["peerDependencies"]["zod"].split(" || ")


@pytest.mark.parametrize("peer", PEERS)
def test_zod_consumer(peer, tmp_path):
    # Require an explicit case for each caret range rather than silently
    # overlooking a newly advertised major or a different range syntax.
    match = re.fullmatch(r"\^(\d+)\.\d+\.\d+", peer)
    assert match, peer
    version = {"3": "3.25.76", "4": "4.6.5"}[match[1]]
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

"""Paths and shared fixtures for the Python suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def vectors() -> dict:
    return json.loads((ROOT / "angles" / "vectors.json").read_text())


@pytest.fixture(scope="session")
def samples() -> dict:
    return json.loads((ROOT / "tests" / "samples.json").read_text())


@pytest.fixture(scope="session")
def constants_source() -> dict:
    return json.loads((ROOT / "constants" / "constants.json").read_text())


@pytest.fixture(scope="session")
def schema_files() -> list[Path]:
    return sorted((ROOT / "schemas").rglob("*.json"))

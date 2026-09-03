"""The Python half of the shared angle contract.

Every case in ``angles/vectors.json`` runs here and, unchanged, in
``tests/ts/angles.test.ts``. A conversion that is only tested on one side is a
conversion that is only right on one side -- which is how a 90-degree offset
lives in a codebase for months.
"""

from __future__ import annotations

import math
import re

import pytest

from needle_protocol import angles
from needle_protocol import constants as generated_constants

# JSON has no NaN or Infinity literal; ``angles/vectors.json`` documents these
# stand-ins under ``encoding`` and every harness decodes them the same way.
SENTINELS = {
    "NaN": float("nan"),
    "Infinity": float("inf"),
    "-Infinity": float("-inf"),
}

# The functions every release must keep working, named here rather than derived
# from the vector file: a vector file that lost a function would otherwise stop
# testing it silently.
REQUIRED_FUNCTIONS = (
    "consoleThetaFromInclination",
    "inclinationFromConsoleTheta",
    "consoleAlphaInputFromInclination",
    "inclinationFromConsoleAlpha",
    "consoleThetaError",
    "inclinationError",
    "angleBetweenDeg",
    "needleInclinationFromVertical",
)


def decode(value):
    if isinstance(value, str) and value in SENTINELS:
        return SENTINELS[value]
    if isinstance(value, dict):
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def snake(name: str) -> str:
    """`consoleThetaFromInclination` -> `console_theta_from_inclination`."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def test_vector_file_is_worth_trusting(vectors: dict) -> None:
    cases = vectors["cases"]
    assert len(cases) >= 30
    ids = [case["id"] for case in cases]
    assert len(set(ids)) == len(ids), "duplicate case ids"
    exercised = {case["fn"] for case in cases}
    assert set(REQUIRED_FUNCTIONS) <= exercised


def _ids(vectors_doc: dict) -> list[str]:
    return [case["id"] for case in vectors_doc["cases"]]


def pytest_generate_tests(metafunc):  # noqa: D103 - pytest hook
    if "case" in metafunc.fixturenames:
        import json
        from pathlib import Path

        doc = json.loads(
            (Path(__file__).resolve().parent.parent.parent / "angles" / "vectors.json").read_text()
        )
        metafunc.parametrize("case", doc["cases"], ids=_ids(doc))


def test_vector(case: dict, vectors: dict) -> None:
    tolerance = vectors["parameters"]["TOLERANCE_DEG"]
    fn = getattr(angles, snake(case["fn"]), None)
    assert callable(fn), f"angles module has no {snake(case['fn'])}"

    actual = fn(*[decode(arg) for arg in case["args"]])
    expected = case["expect"]

    if expected is None:
        assert actual is None
        return

    if isinstance(expected, dict):
        assert actual is not None
        assert abs(actual.inclination_deg - expected["inclinationDeg"]) < tolerance
        assert abs(actual.console_theta_deg - expected["consoleThetaDeg"]) < tolerance
        assert actual.points_up is expected["pointsUp"]
        return

    assert actual is not None
    assert abs(actual - expected) < tolerance
    if expected == 0:
        # ``-0.0`` renders as "-0.0" on a readout; the sign is part of the contract.
        assert not math.copysign(1.0, actual) < 0


@pytest.mark.parametrize(
    ("attribute", "parameter"),
    [
        ("CONSOLE_THETA_VERTICAL_DEG", "CONSOLE_THETA_VERTICAL_DEG"),
        ("HORIZONTAL_INCLINATION_DEG", "HORIZONTAL_INCLINATION_DEG"),
        ("MIN_NEEDLE_LENGTH_MM", "MIN_NEEDLE_LENGTH_MM"),
    ],
)
def test_angles_constants_match_vectors(attribute: str, parameter: str, vectors: dict) -> None:
    assert getattr(angles, attribute) == vectors["parameters"][parameter]


def test_angles_constant_matches_the_shared_source(constants_source: dict) -> None:
    """The angles module keeps its own copy so it can stay dependency-free.

    This is what stops the two copies from ever meaning different things.
    """
    assert (
        angles.CONSOLE_THETA_VERTICAL_DEG
        == constants_source["constants"]["CONSOLE_THETA_VERTICAL_DEG"]["value"]
    )


def test_generated_constants_match_their_source(constants_source: dict) -> None:
    for name, spec in constants_source["constants"].items():
        value = getattr(generated_constants, name)
        expected = tuple(spec["value"]) if spec["type"] == "integer[]" else spec["value"]
        assert value == expected, name


def test_typescript_and_python_export_the_same_surface() -> None:
    """The two reference implementations must offer the same functions.

    Read out of the TypeScript source rather than listed here: a function added
    on one side and forgotten on the other is exactly the drift this package
    exists to prevent, and a hand-kept list would drift with it.
    """
    from pathlib import Path

    ts = (
        Path(__file__).resolve().parent.parent.parent / "angles" / "ts" / "src" / "index.ts"
    ).read_text()
    ts_functions = {snake(name) for name in re.findall(r"^export function ([A-Za-z0-9_]+)", ts, re.M)}
    py_functions = {name for name in angles.__all__ if name.islower()}
    assert ts_functions == py_functions

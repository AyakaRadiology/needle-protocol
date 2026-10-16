"""Regression tests for Python literal generation."""

import ast
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
py_literal = runpy.run_path(str(ROOT / "tools" / "gen-py.py"))["py_literal"]


@pytest.mark.parametrize(
    "values, expected_literal, expected_value",
    [([], "()", ()), ([2], "(2,)", (2,)), ([1, 2], "(1, 2)", (1, 2))],
)
def test_integer_array_literal_is_a_tuple(values, expected_literal, expected_value):
    literal = py_literal({"type": "integer[]", "value": values})
    assert ast.literal_eval(literal) == expected_value
    assert literal == expected_literal

"""Regression tests for Python literal generation."""

import ast
import json
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


def test_swift_generator_refuses_what_it_cannot_express(tmp_path):
    """A schema edit the Swift types cannot enforce must fail generation, not be dropped."""
    gen_swift = runpy.run_path(str(ROOT / "tools" / "gen-swift.py"))
    render_struct, error = gen_swift["render_struct"], gen_swift["GenerationError"]

    def schema(**overrides):
        body = {
            "type": "object",
            "additionalProperties": True,
            "x-version": "1.0.0",
            "description": "d",
            "properties": {"a": {"type": "integer"}},
            "required": ["a"],
        }
        body.update(overrides)
        path = tmp_path / "s.json"
        path.write_text(json.dumps(body))
        return str(path)

    render_struct(schema())  # the baseline is accepted
    with pytest.raises(error, match="additionalProperties"):
        render_struct(schema(additionalProperties=False))
    with pytest.raises(error, match="maximum"):
        render_struct(schema(properties={"a": {"type": "integer", "maximum": 3}}))
    with pytest.raises(error, match="unsupported type"):
        render_struct(schema(properties={"a": {"type": "object"}}))

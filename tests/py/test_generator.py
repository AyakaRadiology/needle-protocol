"""Regression tests for Python literal generation."""

import ast
import json
from pathlib import Path
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
py_literal = runpy.run_path(str(ROOT / "tools" / "gen-py.py"))["py_literal"]


@pytest.mark.parametrize("entry", ["gen/ts", "dist/esm", "dist/cjs"])
def test_envelope_fields_survive_discriminated_union(entry, tmp_path):
    source = [f"import type * as T from {json.dumps(str(ROOT / entry / 'types.js'))};"]
    frames = [
        ("AngleStreamEnvelope", {"v": "1", "kind": "'evt'", "type": "'heartbeat'", "ts": "''"}),
        ("DeviceEnvelope", {"v": "1", "kind": "'evt'", "type": "'status'", "seq": "0", "t_boot_ms": "0"}),
        ("PlanChannelEnvelope", {"v": "1", "kind": "'req'", "type": "'plan'", "id": "'id'", "ts": "''"}),
    ]
    for name, fields in frames:
        source.append(f"declare const f{name}: T.{name};")
        source.append(f"const v{name}: 1 = f{name}.v;")
        kind = "'req' | 'res'" if name == "PlanChannelEnvelope" else "'evt'"
        source.append(f"const kind{name}: {kind} = f{name}.kind;")
        if "ts" in fields:
            source.append(f"Date.parse(f{name}.ts);")
        source.append(f"declare const p{name}: Extract<T.{name}, {{type: {fields['type']}}}>['payload'];")
        fields = {**fields, "payload": f"p{name}"}
        for missing in (None, *fields):
            literal = ", ".join(f"{key}: {value}" for key, value in fields.items() if key != missing)
            if missing is not None:
                source.append(f"// @ts-expect-error {missing} is required")
            source.append(f"const frame{name}{missing}: T.{name} = {{{literal}}};")
    # Open angle-stream envelopes must still accept forward-compatible extensions.
    source.append("const extended: T.AngleStreamEnvelope = {...frameAngleStreamEnvelopeNone, future: true};")
    consumer = tmp_path / "consumer.ts"
    consumer.write_text("\n".join(source))
    result = subprocess.run(
        ["node", str(ROOT / "node_modules/typescript/bin/tsc"), "--ignoreConfig",
         "--strict", "--noEmit", "--types", "node", "--module", "NodeNext", str(consumer)],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


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

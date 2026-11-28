"""Regression tests for Python literal generation."""

import ast
import json
import re
from pathlib import Path
import runpy
import shutil
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


@pytest.mark.parametrize(
    "wire_key, swift_key",
    [("server_bind", "serverBind"), ("client_addr", "clientAddr"), ("phantom", "phantom")],
)
def test_swift_hello_rejects_null_for_optional_fields(wire_key, swift_key):
    render_struct = runpy.run_path(str(ROOT / "tools" / "gen-swift.py"))["render_struct"]
    source = "\n".join(render_struct(str(ROOT / "schemas/tracker/hello.json")))
    assert (
        f"if container.contains(.{swift_key}), try container.decodeNil(forKey: .{swift_key}) {{\n"
        "            throw DecodingError.dataCorruptedError(\n"
        f"                forKey: .{swift_key}, in: container,\n"
        f'                debugDescription: "{wire_key} must not be null")\n'
        "        }\n"
        f"        self.{swift_key} = try container.decodeIfPresent("
    ) in source


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
        render_struct(schema(properties={"a": {"type": "null"}}))
    # A nested object is expressible only when it is open and says what is in it.
    with pytest.raises(error, match="nested object"):
        render_struct(schema(properties={"a": {"type": "object"}}))
    with pytest.raises(error, match="nested object"):
        render_struct(
            schema(
                properties={
                    "a": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {"b": {"type": "integer"}},
                    }
                }
            )
        )
    nested = render_struct(
        schema(
            properties={
                "a": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {"b": {"type": "number", "exclusiveMinimum": 0}},
                    "required": ["b"],
                }
            }
        )
    )
    assert any(line.startswith("public struct") and "Codable" in line for line in nested)
    assert any("b must be > 0" in line for line in nested)
    # Arrays: string enums, open objects, and arrays of numbers -- with their bounds.
    with pytest.raises(error, match="only arrays of"):
        render_struct(schema(properties={"a": {"type": "array", "items": {"type": "integer"}}}))
    with pytest.raises(error, match="array's object"):
        render_struct(
            schema(properties={"a": {"type": "array", "items": {"type": "object", "properties": {}}}})
        )
    with pytest.raises(error, match="unsupported schema keyword"):
        render_struct(
            schema(
                properties={
                    "a": {
                        "type": "array",
                        "items": {"type": "array", "uniqueItems": True, "items": {"type": "number"}},
                    }
                }
            )
        )
    with pytest.raises(error, match="only supported on arrays"):
        render_struct(schema(properties={"a": {"type": "string", "minItems": 1}}))
    listed = render_struct(
        schema(
            properties={
                "a": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {
                            "p": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "minItems": 3,
                                    "maxItems": 3,
                                    "items": {"type": "number"},
                                },
                            }
                        },
                    },
                }
            }
        )
    )
    text = "\n".join(listed)
    item = re.search(r"public struct (\w+AItem): Codable", text)
    assert item, text
    assert f"public var a: [{item[1]}]" in text
    assert "a must have at least 1 item(s)" in text and "a must have at most 4 item(s)" in text
    assert "public var p: [[Double]]?" in text
    assert "each element of p must have at least 3 number(s)" in text
    assert "each element of p must have at most 3 number(s)" in text


def test_swift_generator_preserves_output_on_schema_error(tmp_path, capsys):
    for directory in ("schemas/tracker", "constants", "tests/swift"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    generator = tmp_path / "tools" / "gen-swift.py"
    generator.parent.mkdir()
    shutil.copyfile(ROOT / "tools" / "gen-swift.py", generator)
    main = runpy.run_path(str(generator))["main"]

    output = tmp_path / "gen" / "swift"

    def snapshot():
        return {path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()}

    assert main() == 0
    before = snapshot()
    schema_path = tmp_path / "schemas" / "tracker" / "frame-needle.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["properties"]["frame_id"]["maximum"] = 100
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    assert main() == 1
    assert capsys.readouterr().err == (
        "[gen-swift] schemas/tracker/frame-needle.json.frame_id: "
        "unsupported schema keyword(s) ['maximum']\n"
    )
    after = snapshot()
    assert after.keys() == before.keys()
    assert after == before

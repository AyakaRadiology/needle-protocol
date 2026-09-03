"""Generate `schema_keys.h` -- the firmware's view of the JSON schemas.

Moved here from `scl3300-stream/tools/`. The firmware consumes this repository
as a git submodule pinned to a tag and runs this script from a CMake custom
command, so the header is BUILD OUTPUT there and is never committed in the
firmware repo: a committed copy is a copy that can be edited, and an edited
`KEY_*` macro is a wire-format change that no schema records.

`gen/c/schema_keys.h` in THIS repo is committed, and CI diffs it. That is not a
contradiction: here it is the artefact whose diff proves the generator and the
schemas still agree, which is exactly what the firmware build has no way to
check on its own.
"""

import argparse
import json
import re
import sys
from pathlib import Path

IDENT = re.compile(r"[^A-Za-z0-9]+")


def _strip_jsonc(s: str) -> str:
    """
    Remove // and /* */ comments and trailing commas to tolerate JSONC-like files.
    """
    # strip BOM if present (json module doesn't like it)
    if s and s[0] == "\ufeff":
        s = s[1:]
    # /* block */ comments
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    # // line comments
    s = re.sub(r"(^|\s)//.*?$", r"\1", s, flags=re.M)
    # trailing commas before } or ]
    s = re.sub(r",\s*(\})", r"\1", s)
    s = re.sub(r",\s*(\])", r"\1", s)
    return s


def load_json_tolerant(path: Path):
    """
    Load JSON allowing BOM, comments, and trailing commas.
    If parsing still fails, raise with the path for easier debugging.
    """
    raw = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        stripped = _strip_jsonc(raw)
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON schema: {path}") from e


def to_macro(name: str) -> str:
    return IDENT.sub("_", name).upper()


def to_enum_name(prop: str) -> str:
    return IDENT.sub("_", prop).lower()


def to_enum_item(prefix: str, val: str) -> str:
    return prefix + "_" + IDENT.sub("_", val).upper()


def to_xversion_macro(path: Path) -> str:
    """`schemas/device/envelope.json` -> `SCHEMA_DEVICE_ENVELOPE_XVERSION`.

    Built from the file's own directory and stem rather than from the path the
    caller happened to pass, so the firmware's CMake invocation and this repo's
    `tools/gen.sh` produce the same macro whatever their working directory is.
    """
    return "SCHEMA_" + to_macro(f"{path.parent.name}_{path.stem}") + "_XVERSION"


def extract_from_schema(obj, keys, enums, path=""):
    if not isinstance(obj, dict):
        return
    # properties -> key names
    props = obj.get("properties")
    if isinstance(props, dict):
        for k, v in props.items():
            keys.add(k)
            # enum -> enumeration (preserve declaration order: the generated enum's
            # integer value IS the array index, so ordering must be stable and
            # match the schema, never alphabetized)
            if isinstance(v, dict) and "enum" in v and isinstance(v["enum"], list):
                bucket = enums.setdefault(k, [])
                for x in v["enum"]:
                    sx = str(x)
                    if sx not in bucket:
                        bucket.append(sx)
            extract_from_schema(v, keys, enums, path + "/properties/" + k)

    # descend into allOf/anyOf/oneOf/items as well
    for tag in ("allOf", "anyOf", "oneOf"):
        arr = obj.get(tag)
        if isinstance(arr, list):
            for e in arr:
                extract_from_schema(e, keys, enums, path + f"/{tag}")

    items = obj.get("items")
    if items:
        extract_from_schema(items, keys, enums, path + "/items")

    # also look through nested definitions
    defs = obj.get("$defs") or obj.get("definitions")
    if isinstance(defs, dict):
        for v in defs.values():
            extract_from_schema(v, keys, enums, path + "/defs")


HEADER_TEMPLATE = """\
/*
 * AUTO-GENERATED FILE. DO NOT EDIT.
 * Source schemas: {schema_count} file(s)
 */
#ifndef SCHEMA_KEYS_H_
#define SCHEMA_KEYS_H_

/* ---- Schema x-version (device<->host compatibility, per SECURITY.md) ----
 * These are the numbers that decide whether a host can read this device, and
 * they move INDEPENDENTLY of the envelope's `v` and of the package version.
 * Emitted so the firmware can report the contract it was built against rather
 * than a hand-kept literal that drifts from the schema beside it.
 */
{xversion_macros}

/* ---- Key name string macros ---- */
{key_macros}

/* ---- C++ friendly string_view (optional) ---- */
#ifdef __cplusplus
#include <string_view>
namespace schema_keys {{
{key_sv}
}} // namespace schema_keys
extern "C" {{
#endif

/* ---- Enums derived from schema enums ---- */
{enum_defs}

/* ---- Lookup helpers (header-only, internal linkage) ---- */
{helpers}

#ifdef __cplusplus
}} // extern "C"
#endif
#endif /* SCHEMA_KEYS_H_ */
"""

ENUM_DEF_TEMPLATE = """\
typedef enum {enum_type} {{
{items}
}} {enum_type};
"""

HELPER_IMPL_TEMPLATE = """\
/* Header-only helpers with internal linkage */
#include <stddef.h>
#include <string.h>
{arrays}

{from_funcs}
"""

ARRAY_TEMPLATE = """\
static const char* {enum_type}_to_cstr[{count}] = {{
{arr_items}
}};
"""

FROM_FUNC_TEMPLATE = """\
static inline int {enum_type}_from_cstr(const char* s) {{
  if (!s) return -1;
  for (int i = 0; i < {count}; ++i) {{
    if (strcmp(s, {enum_type}_to_cstr[i]) == 0) return i;
  }}
  return -1;
}}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schemas", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    keys = set()
    enums = {}  # prop -> set(values)
    xversions = {}  # macro name -> x-version string

    for p in args.schemas:
        path = Path(p)
        if not path.is_file():
            print(f"[gen_schema_header] Skip non-file: {path}", file=sys.stderr)
            continue
        try:
            data = load_json_tolerant(path)
        except Exception as e:
            print(f"[gen_schema_header] {e}", file=sys.stderr)
            raise
        extract_from_schema(data, keys, enums)

        version = data.get("x-version") if isinstance(data, dict) else None
        if not isinstance(version, str) or not version:
            raise RuntimeError(
                f"[gen_schema_header] {path} has no string `x-version`. Every schema carries one: "
                "it is the number that decides device<->host compatibility, and a schema without it "
                "cannot tell a firmware build what contract it was compiled against."
            )
        macro = to_xversion_macro(path)
        if xversions.get(macro, version) != version:
            raise RuntimeError(
                f"[gen_schema_header] two schemas map to {macro} with different x-versions "
                f"({xversions[macro]} and {version}); rename one of the files."
            )
        xversions[macro] = version

    # Guard the codegen<->firmware contract. The C++ references these keys via
    # KEY_* macros; if a schema refactor drops one, fail loudly here instead of
    # emitting a header that breaks the build (or, worse, silently changes the
    # wire format). Add to this list when firmware starts depending on a key.
    REQUIRED_KEYS = (
        "v", "kind", "type", "seq", "t_boot_ms", "payload",
        "accel_x", "accel_y", "accel_z",
        "state", "code", "message", "level",
    )
    missing = [k for k in REQUIRED_KEYS if k not in keys]
    if missing:
        raise RuntimeError(
            f"[gen_schema_header] schemas are missing required keys used by firmware: {missing}"
        )

    keys = sorted(keys)
    # macros
    key_macros = "\n".join([f'#define KEY_{to_macro(k)} "{k}"' for k in keys])

    # C++ string_view
    key_sv = "\n".join(
        [f'inline constexpr std::string_view {to_enum_name(k)} = "{k}";' for k in keys]
    )

    # enum definitions
    enum_blocks = []
    arrays = []
    from_funcs = []

    for prop, values in sorted(enums.items()):
        # NOTE: values stay in schema declaration order (not sorted) so each
        # generated enum constant's integer == its position in the schema array.
        enum_type = f"{to_enum_name(prop)}_t"
        # items
        prefix = to_enum_name(prop).upper()
        items = []
        for i, v in enumerate(values):
            items.append(f"  {to_enum_item(prefix, v)} = {i}")
        enum_blocks.append(
            ENUM_DEF_TEMPLATE.format(enum_type=enum_type, items=",\n".join(items))
        )
        arrays.append(
            ARRAY_TEMPLATE.format(
                enum_type=enum_type,
                count=len(values),
                arr_items=",\n".join([f'  "{v}"' for v in values]),
            )
        )
        from_funcs.append(
            FROM_FUNC_TEMPLATE.format(enum_type=enum_type, count=len(values))
        )

    helpers = ""
    if enum_blocks:
        helpers = HELPER_IMPL_TEMPLATE.format(
            arrays="\n".join(arrays), from_funcs="\n".join(from_funcs)
        )

    xversion_macros = "\n".join(
        f'#define {macro} "{version}"' for macro, version in sorted(xversions.items())
    )

    out = HEADER_TEMPLATE.format(
        schema_count=len(args.schemas),
        xversion_macros=xversion_macros or "/* (no schemas with x-version) */",
        key_macros=key_macros or "/* (no keys found) */",
        key_sv=key_sv or "",
        enum_defs="\n".join(enum_blocks) or "/* (no enums found) */",
        helpers=helpers or "",
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())

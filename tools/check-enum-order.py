#!/usr/bin/env python3
"""Require a schema major bump for breaking enum changes since the last tag.

Why this is a gate and not a review habit
-----------------------------------------
`tools/gen_schema_header.py` turns every schema enum into a C enum whose integer
value IS the element's index in the JSON array. The Pico stores and compares
those integers. So reordering `["init", "ready", ...]` -- an edit that looks like
tidying, and that every JSON linter will call equivalent -- silently changes what
`state == 1` means on a device that is already flashed. Removing an element
renumbers everything after it, which is the same failure with a wider blast
radius.

Both are MAJOR changes. Bump the schema's `x-version` major above the released
schema's major and note the change in the commit.

Compares against the highest-version `v*` tag reachable from HEAD. If no such tag
is reachable, the check reports that it has no baseline and passes.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schemas"


def newest_tag() -> str | None:
    """The highest-version `v*` tag reachable from HEAD, or None if absent.

    `git for-each-ref` filters by ancestry and sorts by version semantics
    (`v0.10.0` after `v0.9.0`) in one call.
    """
    out = subprocess.run(
        [
            "git",
            "for-each-ref",
            "--merged=HEAD",
            "--sort=-v:refname",
            "--format=%(refname:short)",
            "refs/tags/v*",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return out[0] if out else None


def enums_of(schema: object, path: str = "") -> dict[str, list]:
    """Every `enum` array in a schema, keyed by its JSON pointer."""
    found: dict[str, list] = {}
    if isinstance(schema, dict):
        for key, value in schema.items():
            here = f"{path}/{key}"
            if key == "enum" and isinstance(value, list):
                found[path or "/"] = value
            else:
                found.update(enums_of(value, here))
    elif isinstance(schema, list):
        for index, item in enumerate(schema):
            found.update(enums_of(item, f"{path}/{index}"))
    return found


def at_tag(tag: str, relative: str) -> object | None:
    """A schema as it was at `tag`, or None if it did not exist then."""
    result = subprocess.run(
        ["git", "show", f"{tag}:{relative}"], cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def schema_major(schema: object) -> int | None:
    """Return the major of a numeric x-version, if the schema declares one."""
    version = schema.get("x-version") if isinstance(schema, dict) else None
    if isinstance(version, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        return int(version.split(".", 1)[0])
    return None


def main() -> int:
    tag = newest_tag()
    if tag is None:
        print(
            "[check-enum-order] No v* tag reachable from HEAD, so there is no released enum "
            "ordering to compare against. Nothing checked."
        )
        return 0

    problems: list[str] = []
    for file in sorted(SCHEMA_DIR.rglob("*.json")):
        relative = file.relative_to(ROOT).as_posix()
        before = at_tag(tag, relative)
        if before is None:
            continue  # A new schema has no prior ordering to violate.
        after = json.loads(file.read_text())
        old_major = schema_major(before)
        new_major = schema_major(after)
        if old_major is not None and new_major is not None and new_major > old_major:
            continue

        old = enums_of(before)
        new = enums_of(after)
        for pointer, old_values in old.items():
            new_values = new.get(pointer)
            if new_values is None:
                problems.append(f"{relative}{pointer}: the enum is gone (was {old_values}).")
                continue
            # Appending is fine: an added element takes the next index and every
            # existing value keeps the integer a flashed device already knows.
            if new_values[: len(old_values)] != old_values:
                problems.append(
                    f"{relative}{pointer}: order changed or an element was removed.\n"
                    f"    {tag}: {old_values}\n"
                    f"    now:  {new_values}\n"
                    f"    The generated C enum's value IS the array index, so this renumbers "
                    f"constants a flashed device already stores."
                )

    if problems:
        print(f"[check-enum-order] {len(problems)} breaking enum change(s) since {tag}:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nIf the change is intended, it is a MAJOR one: bump the schema's `x-version` major "
            "and say so in the commit. Do not reorder to satisfy a linter.",
            file=sys.stderr,
        )
        return 1

    print(f"[check-enum-order] enum order check passed against {tag}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

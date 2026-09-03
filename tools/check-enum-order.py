#!/usr/bin/env python3
"""Fail when an enum array is reordered or an element removed since the last tag.

Why this is a gate and not a review habit
-----------------------------------------
`tools/gen_schema_header.py` turns every schema enum into a C enum whose integer
value IS the element's index in the JSON array. The Pico stores and compares
those integers. So reordering `["init", "ready", ...]` -- an edit that looks like
tidying, and that every JSON linter will call equivalent -- silently changes what
`state == 1` means on a device that is already flashed. Removing an element
renumbers everything after it, which is the same failure with a wider blast
radius.

Neither is forbidden forever. Both are MAJOR changes: bump the schema's
`x-version` major, note it, and the tag you compare against moves on. What is
forbidden is doing it by accident.

Compares against the newest `v*` tag reachable in this checkout. With no tags at
all -- the first release -- there is nothing to compare against and the check
prints that and passes, rather than inventing a baseline.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schemas"


def newest_tag() -> str | None:
    """The highest `v*` tag in this checkout, or None when there are none.

    `git for-each-ref` rather than `git tag`: it sorts by version semantics
    (`v0.10.0` after `v0.9.0`, which a lexical sort gets wrong) in one call.
    """
    out = subprocess.run(
        ["git", "for-each-ref", "--sort=-v:refname", "--format=%(refname:short)", "refs/tags/v*"],
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


def main() -> int:
    tag = newest_tag()
    if tag is None:
        print(
            "[check-enum-order] No v* tag in this checkout, so there is no released enum ordering "
            "to compare against. Nothing checked. This is expected before the first release, and "
            "on a shallow clone that fetched no tags."
        )
        return 0

    problems: list[str] = []
    for file in sorted(SCHEMA_DIR.rglob("*.json")):
        relative = file.relative_to(ROOT).as_posix()
        before = at_tag(tag, relative)
        if before is None:
            continue  # A new schema has no prior ordering to violate.
        old = enums_of(before)
        new = enums_of(json.loads(file.read_text()))
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

    print(f"[check-enum-order] enum ordering unchanged since {tag}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

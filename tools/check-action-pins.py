#!/usr/bin/env python3
"""Fail when one GitHub Action is pinned to two different refs across the workflows.

Why this is a gate and not a review habit
-----------------------------------------
Dependabot's github-actions updater resolves ONE target version per action and
writes it over EVERY reference to that action in the repository. It does not
reconcile references that disagree -- it picks an answer and applies it
everywhere, including to references that were already newer.

That is not hypothetical here. Before #10, `astral-sh/setup-uv` was referenced
two ways: `@v10.0.1` in ci.yml and `@v5` in release-please.yml. astral-sh stopped
publishing moving short-form major tags at v8.0.0 ("Immutable releases and secure
tags") -- bare `v8`, `v9` and `v10` do not exist, and the newest short tag is
still `v7`. So the `@v5` reference made "latest" resolve to `v7`, and that single
answer was written over both references, DOWNGRADING ci.yml from v10.0.1 to v7.
A downgrade arrives looking exactly like every other green dependency bump, which
is what makes it worth a gate: nothing else in CI can tell the difference.

The rule is deliberately about AGREEMENT, not about pin style. Both styles are
legitimate and this repository uses both on purpose:

  * a moving major tag (`actions/checkout@v7`) keeps picking up that major's
    security patches, which is what GitHub recommends and what most actions here
    use;
  * a full version tag (`astral-sh/setup-uv@v10.0.1`) is the only option for an
    action whose publisher no longer ships moving major tags at all.

Forcing either style on every action would be wrong. Two refs for ONE action is
what nobody ever intends, and it is the shape that lets a bump run backwards.

Not checked here: whether a referenced tag exists upstream. That needs the
network, and a gate that goes red when github.com is slow teaches people to
ignore it.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = ROOT / ".github" / "workflows"

# `uses:` as the first thing on the line (after optional YAML list punctuation),
# so a `#`-comment mentioning an action cannot trip the check. Deliberately not a
# YAML parse: this needs the LINE NUMBER of each reference to say anything useful,
# and a parser would cost a dependency to lose that.
USES = re.compile(
    r"""^\s*(?:-\s*)?uses:\s*['"]?(?P<action>[^'"@\s]+)@(?P<ref>[^'"\s#]+)""",
)


def references() -> dict[str, dict[str, list[str]]]:
    """Map action -> ref -> ["file:line", ...] for every workflow reference."""
    found: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for workflow in sorted(WORKFLOW_DIR.glob("*.y*ml")):
        for number, line in enumerate(workflow.read_text().splitlines(), start=1):
            match = USES.match(line)
            if not match:
                continue
            action = match.group("action")
            # Local (`./.github/actions/x`) and container (`docker://`) steps are
            # not versioned by a git ref and have nothing to disagree about.
            if action.startswith((".", "docker://")):
                continue
            # `owner/repo/sub/path@ref` is still the repo `owner/repo`; a
            # subdirectory action shares its parent's tags.
            owner_repo = "/".join(action.split("/")[:2]).lower()
            where = f"{workflow.relative_to(ROOT)}:{number}"
            found[owner_repo][match.group("ref")].append(where)
    return found


def main() -> int:
    found = references()
    if not found:
        print(
            f"::error::{WORKFLOW_DIR.relative_to(ROOT)} has no `uses:` references at all. "
            "Either the workflows moved or this check's parser stopped matching them; "
            "either way it is now guarding nothing.",
            file=sys.stderr,
        )
        return 1

    conflicts = {action: refs for action, refs in found.items() if len(refs) > 1}
    for action, refs in sorted(conflicts.items()):
        listed = ", ".join(sorted(refs))
        print(
            f"::error::{action} is pinned to {len(refs)} different refs ({listed}). "
            "Dependabot resolves one version per action and writes it over every "
            "reference, so disagreeing pins let a bump run BACKWARDS. Pin every "
            "reference to this action to the same ref.",
            file=sys.stderr,
        )
        for ref in sorted(refs):
            for where in refs[ref]:
                print(f"    {where}: @{ref}", file=sys.stderr)
    if conflicts:
        return 1

    total = sum(len(refs[ref]) for refs in found.values() for ref in refs)
    print(f"[check-action-pins] {total} reference(s) to {len(found)} action(s); every action agrees with itself.")
    for action, refs in sorted(found.items()):
        print(f"    {action}@{next(iter(refs))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

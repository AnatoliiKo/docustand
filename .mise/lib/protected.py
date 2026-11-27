"""Protected paths of `.claude/settings.json` and the glob syntax shared by `report`, `check-md-placement` and `maintain`.

Glob: `*` matches within one path segment, `**` any number of segments (also zero), `?` one character
of a segment when `question` is set and itself otherwise.
"""
import json
import re
from pathlib import Path

ASK_EDIT = re.compile(r"^Edit\(/(.+)\)$")


def glob_to_regex(pattern: str, question: bool = False) -> re.Pattern[str]:
    """Regex of a glob; match it with `fullmatch` or `match`."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?" and question:
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def patterns(settings: str) -> list[str]:
    """The `Edit(/<path>)` rules of `permissions.ask` in the text of `settings.json`."""
    rules = (json.loads(settings).get("permissions") or {}).get("ask") or []
    return [m.group(1) for rule in rules if (m := ASK_EDIT.match(rule))]


def load_protected(root: Path) -> list[str]:
    """Protected paths of the working tree."""
    return patterns((root / ".claude" / "settings.json").read_text())

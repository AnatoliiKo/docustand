"""Shared language detector of `check-comments`, `check-md-language` and `detect-language`.

A block is `(first line, text)`. Quoted text, code spans, URLs and tool directives are not prose.
The script of the words decides: Cyrillic or Latin, so no dependency is needed.
"""
import re
from pathlib import Path

LANGUAGES = ("en", "ru", "auto")
QUOTED = re.compile(r"«[^»]*»|`[^`\n]*`|\"[^\"\n]*\"")
DATE = re.compile(r"\b(?:\d{4}|YYYY)-(?:\d{2}|MM)-(?:\d{2}|DD)\b")
URL = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.I)
# Only the directive and its rule are cut: the reason after `--` or `:` is prose.
_RULES = r"[A-Za-z0-9@/_-]+(?:\s*,\s*[A-Za-z0-9@/_-]+)*"
DIRECTIVE = re.compile(
    rf"\beslint-[A-Za-z-]+(?:\s+(?!--){_RULES})?|@ts-[A-Za-z-]+|\bprettier-ignore|"
    rf"\bnoqa\b(?::\s*[A-Z]+\d+(?:\s*,\s*[A-Z]+\d+)*)?|\btype:|"
    rf"\btflint-ignore(?:-file)?:?(?:\s*{_RULES})?|\bMISE\b")
CYRILLIC_PROSE = re.compile(r"[А-Яа-яЁё]+(?:[\s,.;:()-]+[А-Яа-яЁё]+){2,}")
LATIN_PROSE = re.compile(r"[A-Za-z]+(?:[\s,.;:()-]+[A-Za-z]+){2,}")
CYRILLIC_WORD = re.compile(r"[А-Яа-яЁё]{2,}")
MESSAGES = {"en": "English", "ru": "Russian"}
LANGUAGE_KEY = re.compile(r"^language:\s*[\"']?([\w-]+)", re.M)


def read_language(root: Path) -> str:
    """`language` of `.repo.yaml`; `en` when the file or the key is missing."""
    path = root / ".repo.yaml"
    match = LANGUAGE_KEY.search(path.read_text()) if path.is_file() else None
    return match.group(1) if match else "en"


# Files the template renders, by exact name. Under `ru` their English text is the standard's, not project text;
# under `en` every file is checked, so project files in the same folders stay covered.
RENDERED = frozenset({
    ".repo.yaml", "AGENTS.md", "CLAUDE.md",
    ".claude/settings.json", ".claude/hooks/_shell.py", ".claude/hooks/guard_bash.py",
    ".claude/hooks/guard_pr_create.py", ".claude/hooks/guard_pr_merge.py",
    ".config/commitlint.config.mjs", ".config/hk.pkl", ".config/lychee.toml", ".config/rumdl.toml",
    ".config/typos.toml", ".config/dependency-cruiser.standard.cjs",
    ".tflint.hcl", "eslint.config.mjs",
    ".github/workflows/standard-ci.yml", ".github/workflows/standard-report.yml",
    ".github/pull_request_template.md", ".github/repo.schema.json", ".mise/conf.d/standard.toml",
    ".mise/lib/language.py",
    *(f".mise/tasks/{name}" for name in (
        "check-adr", "check-adr-history", "check-agents-md", "check-baseline", "check-comments",
        "check-doc-paths", "check-env-example", "check-eslint-suppressions", "check-gitignore-block",
        "check-md-language", "check-md-placement", "check-pr-body", "check-pr-commits", "check-repo-yaml",
        "check-root", "check-size", "check-tasks-format", "ci-merged-pr", "detect-language", "detect-stack",
        "pr-ready", "report", "tf-validate")),
})
# ADRs, temporary files and the changelog record the state of their date, as in `check-doc-paths`.
DOCUMENTS_SKIPPED = re.compile(r"^(?:docs/decisions/|docs/temp/|CHANGELOG\.md$)")


def is_standard(path: str, language: str) -> bool:
    """A rendered file is exempt only under `ru`: the template has no Russian text for it."""
    return language == "ru" and path in RENDERED


def _blank(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group())


def _mask(match: re.Match[str]) -> str:
    """`_` is outside the word separators, so a cut fragment still splits the words around it."""
    return re.sub(r"[^\n]", "_", match.group())


def prose(text: str, comment: bool = False) -> str:
    """Text without quoted strings, code spans and URLs; in a comment also without tool directives."""
    text = QUOTED.sub(_blank, text)
    for pattern in (URL, DATE, *((DIRECTIVE,) if comment else ())):
        text = pattern.sub(_mask, text)
    return text


def match_of(text: str, language: str, comment: bool = False) -> re.Match[str] | None:
    """The prose that is not in `language`: Cyrillic under `en`, Latin without Cyrillic under `ru`."""
    text = prose(text, comment)
    if language == "en":
        return CYRILLIC_PROSE.search(text)
    if language == "ru" and not CYRILLIC_WORD.search(text):
        return LATIN_PROSE.search(text)
    return None


def violations(blocks: list[tuple[int, str]], language: str, comment: bool = False) -> list[int]:
    """Line of the first foreign prose in each block that is not in `language`."""
    found = []
    for line, text in blocks:
        match = match_of(text, language, comment)
        if match:
            found.append(line + prose(text, comment).count("\n", 0, match.start()))
    return found


def shares(blocks: list[tuple[int, str]], comment: bool = False) -> dict[str, int]:
    """Number of blocks in prose of each language; a block without prose is not counted."""
    count = {"en": 0, "ru": 0}
    for _, text in blocks:
        text = prose(text, comment)
        if CYRILLIC_PROSE.search(text):
            count["ru"] += 1
        elif LATIN_PROSE.search(text):
            count["en"] += 1
    return count


def group(comments: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Blocks of consecutive comment lines; a UI string may wrap to the next line."""
    blocks: list[list[tuple[int, str]]] = []
    for number, text in comments:
        if blocks and blocks[-1][-1][0] + 1 == number:
            blocks[-1].append((number, text))
        else:
            blocks.append([(number, text)])
    return [(block[0][0], "\n".join(text for _, text in block)) for block in blocks]


FENCE = re.compile(r"^\s*(```|~~~)")
STARTS_BLOCK = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|\|)")
LINK_TARGET = re.compile(r"\]\([^)\n]*\)")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
INDENTED_CODE = re.compile(r"^(?: {4}|\t)")


def markdown_blocks(text: str) -> list[tuple[int, str]]:
    """Prose blocks of a Markdown text: paragraphs, list items, headings and table rows."""
    text = FRONT_MATTER.sub(_blank, text, count=1)
    text = HTML_COMMENT.sub(lambda m: re.sub(r"[^\n]", "", m.group()), text)
    blocks: list[tuple[int, list[str]]] = []
    fence = ""
    open_block = False
    for number, line in enumerate(text.splitlines(), 1):
        opening = FENCE.match(line)
        if opening and (not fence or opening.group(1) == fence):
            fence = "" if fence else opening.group(1)
            open_block = False
            continue
        if fence or not line.strip():
            open_block = False
            continue
        if not open_block and INDENTED_CODE.match(line) and not STARTS_BLOCK.match(line):
            continue
        line = LINK_TARGET.sub("]", line)
        if open_block and not STARTS_BLOCK.match(line):
            blocks[-1][1].append(line)
        else:
            blocks.append((number, [line]))
            open_block = not line.lstrip().startswith("|")
    return [(number, "\n".join(lines)) for number, lines in blocks]

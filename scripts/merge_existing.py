#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Merge a rendered docustand template into an existing repository.

  merge_existing.py conflicts <project_dir> <rendered_dir> [--template DIR]
  merge_existing.py merge <project_dir> <rendered_dir> [--audit]

`conflicts` prints, one per line and sorted, the files that exist both in the
rendered template and in the project with different content. Files listed in
`_skip_if_exists` of the template's `copier.yml` are left out: Copier never
overwrites them. `--template` defaults to the repository holding this script.

`merge` appends the `.gitignore` block lines the project lacks between
`# >>> repository standard` and `# <<< repository standard`, once, and prints
the project-owned files it leaves alone. With `--audit` it also adds block lines
missing inside the markers. The script never deletes or rewrites foreign lines.
"""
import argparse
import re
import sys
from pathlib import Path

START = "# >>> repository standard"
END = "# <<< repository standard"
GITIGNORE = ".gitignore"
STANDARD_WORKFLOW_PREFIX = "standard-"


def skip_if_exists(template: Path) -> set[str]:
    """Entries of the top-level `_skip_if_exists` list of `copier.yml` (no YAML library)."""
    entries: set[str] = set()
    active = False
    for line in (template / "copier.yml").read_text().splitlines():
        if re.match(r"^_skip_if_exists:\s*$", line):
            active = True
        elif active:
            item = re.match(r"^\s+-\s+(\S.*?)\s*(?:#.*)?$", line)
            if item:
                entries.add(item.group(1).strip("\"'"))
            elif line.strip() and not line.lstrip().startswith("#"):
                active = False
    return entries


def files(root: Path) -> list[str]:
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    )


def conflicts(project: Path, rendered: Path, template: Path) -> list[str]:
    skipped = skip_if_exists(template)
    return [
        rel for rel in files(rendered)
        if rel not in skipped
        and (project / rel).is_file()
        and (project / rel).read_bytes() != (rendered / rel).read_bytes()
    ]


def block_lines(rendered: Path) -> list[str]:
    """The standard block is the rendered `.gitignore`; `check-gitignore-block` keeps the same lines, and a test keeps both equal."""
    path = rendered / GITIGNORE
    if not path.is_file():
        sys.exit(f"merge_existing: {path} is missing; render the template first")
    return [l for l in path.read_text().splitlines() if l.strip() and l not in (START, END)]


def merge_gitignore(project: Path, rendered: Path, audit: bool) -> None:
    lines = block_lines(rendered)
    path = project / GITIGNORE
    text = path.read_text() if path.exists() else ""
    current = text.splitlines()
    if START in current and END in current:
        if not audit:
            return
        end = current.index(END)
        present = {l.strip() for l in current}
        missing = [l for l in lines if l not in present]
        if not missing:
            return
        current[end:end] = missing
        path.write_text("\n".join(current) + "\n")
        return
    if START in current or END in current:
        sys.exit(f"merge_existing: {path} has an unpaired marker; fix it by hand")
    present = {l.strip() for l in current}
    missing = [l for l in lines if l not in present]
    if not missing:
        return
    if text and not text.endswith("\n"):
        text += "\n"
    if text:
        text += "\n"
    path.write_text(text + "\n".join([START, *missing, END]) + "\n")


def project_owned(project: Path) -> list[str]:
    owned = [name for name in ("CLAUDE.md", "mise.toml") if (project / name).is_file()]
    workflows = project / ".github" / "workflows"
    if workflows.is_dir():
        owned += sorted(
            p.relative_to(project).as_posix()
            for p in workflows.iterdir()
            if p.is_file() and not p.name.startswith(STANDARD_WORKFLOW_PREFIX)
        )
    return owned


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("conflicts", "merge"):
        p = sub.add_parser(name)
        p.add_argument("project_dir", type=Path)
        p.add_argument("rendered_dir", type=Path)
    sub.choices["conflicts"].add_argument(
        "--template", type=Path, default=Path(__file__).resolve().parent.parent)
    sub.choices["merge"].add_argument("--audit", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "conflicts":
        for rel in conflicts(args.project_dir, args.rendered_dir, args.template):
            print(rel)
    else:
        merge_gitignore(args.project_dir, args.rendered_dir, args.audit)
        for rel in project_owned(args.project_dir):
            print(f"project-owned, not touched: {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

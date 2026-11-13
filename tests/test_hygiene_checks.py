import json
import os
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest

from conftest import REPO_ROOT

TASKS = REPO_ROOT / "template" / ".mise" / "tasks"
FUTURE = (date.today() + timedelta(days=30)).isoformat()
PAST = (date.today() - timedelta(days=1)).isoformat()


def run(repo: Path, name: str, *args: str) -> tuple[int, str]:
    result = subprocess.run(["uv", "run", "--quiet", "--script", str(TASKS / name), *args], cwd=repo,
                            env=os.environ, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def commit(repo: Path, message: str = "chore: change") -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


# check-root

def test_root_allows_standard_and_project_entries(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, ".mise/data/root-files.txt", "# comment\n.mise\nREADME.md\ntsconfig*.json\n")
    write(repo, ".repo.yaml", "root_files: [apps, Dockerfile]\n")
    for rel in ("README.md", "tsconfig.base.json", "apps/web/a.ts", "Dockerfile"):
        write(repo, rel, "x\n")
    git(repo, "add", "-A")
    write(repo, "untracked.txt", "not in git\n")

    assert run(repo, "check-root") == (1, ".repo.yaml: not allowed in the repository root; move it, or add it to "
                                          "root_files in .repo.yaml\n")


def test_root_rejects_an_unlisted_file(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, ".mise/data/root-files.txt", ".mise\n.repo.yaml\n")
    write(repo, ".repo.yaml", "root_files: []\n")
    write(repo, ".nvmrc", "22\n")
    git(repo, "add", "-A")

    code, out = run(repo, "check-root")

    assert code == 1 and out.startswith(".nvmrc: not allowed")


# check-adr

GOOD = """# 0001. Use X

Date: 2026-01-01
Status: accepted

## Context

- c

## Decision

- d

## Rejected

- r

## Consequences

- q
"""


def adr_repo(tmp_path, git_repo, **files):
    repo = git_repo(tmp_path / "r")
    for name, text in files.items():
        write(repo, f"docs/decisions/{name}.md", text)
    return repo


def test_adr_in_format_passes(tmp_path, git_repo):
    assert run(adr_repo(tmp_path, git_repo, **{"0001-use-x": GOOD}), "check-adr")[0] == 0


@pytest.mark.parametrize("text,message", [
    (GOOD.replace("## Rejected\n\n- r\n\n", ""), "sections must be"),
    (GOOD.replace("Status: accepted", "Status: plan"), "needs `Status:"),
    (GOOD + "- line\n" * 70, "lines, the limit is 80"),
])
def test_adr_out_of_format_fails(tmp_path, git_repo, text, message):
    code, out = run(adr_repo(tmp_path, git_repo, **{"0001-use-x": text}), "check-adr")

    assert code == 1 and message in out


def test_adr_superseded_needs_a_back_link(tmp_path, git_repo):
    old = GOOD.replace("Status: accepted", "Status: superseded by [ADR 0002](0002-use-y.md)")
    new = GOOD.replace("# 0001", "# 0002")
    repo = adr_repo(tmp_path, git_repo, **{"0001-use-x": old, "0002-use-y": new})

    code, out = run(repo, "check-adr")
    assert code == 1 and "name ADR 0001 in a `Supersedes:` line" in out

    write(repo, "docs/decisions/0002-use-y.md", new.replace("Status: accepted", "Status: accepted\nSupersedes: [ADR 0001](0001-use-x.md)"))
    assert run(repo, "check-adr")[0] == 0


def test_adr_baseline_caps_length_and_expires(tmp_path, git_repo):
    long = "# 0001. Old\n\nDate: 2026-01-01. Status: plan\n" + "text\n" * 100
    repo = adr_repo(tmp_path, git_repo, **{"0001-old": long})
    key = "docs/decisions/0001-old.md"

    write(repo, ".baselines/adr.json", json.dumps({key: {"lines": 103, "until": FUTURE}}))
    assert run(repo, "check-adr")[0] == 0

    write(repo, "docs/decisions/0001-old.md", long + "more\n")
    code, out = run(repo, "check-adr")
    assert code == 1 and "104 lines, the baseline allows 103" in out

    write(repo, ".baselines/adr.json", json.dumps({key: {"lines": 110, "until": PAST}}))
    code, out = run(repo, "check-adr")
    assert code == 1 and f"expired on {PAST}" in out


def test_adr_write_baseline_records_failing_adrs(tmp_path, git_repo):
    repo = adr_repo(tmp_path, git_repo, **{"0001-use-x": GOOD, "0002-old": "# 0002. Old\n"})

    assert run(repo, "check-adr", "--write-baseline")[0] == 0

    entries = json.loads((repo / ".baselines/adr.json").read_text())
    assert list(entries) == ["docs/decisions/0002-old.md"]
    assert entries["docs/decisions/0002-old.md"]["lines"] == 1
    assert run(repo, "check-adr")[0] == 0


# check-adr-history

def test_accepted_adr_changes_only_its_status(tmp_path, git_repo):
    repo = adr_repo(tmp_path, git_repo, **{"0001-use-x": GOOD})
    base = commit(repo)

    write(repo, "docs/decisions/0001-use-x.md", GOOD.replace("Status: accepted", "Status: deprecated"))
    write(repo, "docs/decisions/0002-new.md", GOOD.replace("- d", "- anything"))
    assert run(repo, "check-adr-history", base)[0] == 0

    write(repo, "docs/decisions/0001-use-x.md", GOOD.replace("- d", "- changed decision"))
    code, out = run(repo, "check-adr-history", base)
    assert code == 1 and "changes only its `Status:` line" in out


def test_accepted_adr_is_not_deleted_but_proposed_may_change(tmp_path, git_repo):
    proposed = GOOD.replace("Status: accepted", "Status: proposed")
    repo = adr_repo(tmp_path, git_repo, **{"0001-use-x": GOOD, "0002-draft": proposed})
    base = commit(repo)

    (repo / "docs/decisions/0001-use-x.md").unlink()
    write(repo, "docs/decisions/0002-draft.md", proposed.replace("- d", "- reworked"))
    code, out = run(repo, "check-adr-history", base)

    assert code == 1
    assert "0001-use-x.md: an accepted ADR is a record" in out and "0002" not in out


# check-comments history rules

def test_history_comments_fail_and_quoted_dates_pass(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, "src/a.ts", "\n".join([
        "// Retry once: the API drops the first request.",
        "// Format: `2026-01-31`, as in «2026-01-31».",
        "// Kept per ADR 0023, addendum.",
        "// Changed on 2026-01-31 by the owner's decision.",
        "// Previously the cache was global.",
        "const a = 1;",
    ]) + "\n")
    write(repo, "src/a.test.ts", "// The key expires on 2026-11-11 in this fixture.\n")
    write(repo, "src/b.ts", "// Reads fixtures/site-2026-10-05-ui.json.\n")
    git(repo, "add", "-A")

    code, out = run(repo, "check-comments")

    assert code == 1
    assert sorted(line.split(": ", 1)[1] for line in out.splitlines()) == [
        "addendum in a comment; link the ADR in one line",
        "change history in a comment",
        "date in a comment",
        "decision attribution in a comment",
    ]
    assert all(line.startswith("src/a.ts:") for line in out.splitlines())


def test_non_english_comment_fails_and_quoted_ui_strings_pass(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, "src/a.ts", "\n".join([
        "// The «Найти название в",
        "// письмах» (find in letters) icon searches the package name.",
        "// Files go to KDM\\<фильм>\\ and keep the ООО name.",
        "const a = 1;",
        "",
        "// Повторяем запрос один раз, потому что API теряет первый.",
        "const b = 2;",
    ]) + "\n")
    git(repo, "add", "-A")

    code, out = run(repo, "check-comments")

    assert code == 1
    assert out.splitlines() == ["src/a.ts:6: comment not in English; quote a UI string in «»"]


def test_comments_of_configs_known_by_name_are_checked(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, "deploy/Dockerfile", "# Сборка сервера для продакшена\nFROM node:26\n")
    write(repo, ".gitignore", "# Windows agent build\ndist/\n")
    write(repo, "tools/setup.ps1", "# Previously the VM was reset.\nexit 0\n")
    write(repo, ".config/dependency-cruiser.cjs", "// The owner's decision: no cycles.\nmodule.exports = {};\n")
    git(repo, "add", "-A")

    code, out = run(repo, "check-comments")

    assert code == 1
    assert sorted(line.split(": ")[0] for line in out.splitlines()) == [
        ".config/dependency-cruiser.cjs:1", "deploy/Dockerfile:1", "tools/setup.ps1:1",
    ]


def test_history_baseline_only_shrinks_and_expires(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, "src/a.ts", "// ADR 0023, addendum.\n// ADR 0024, addendum.\n")
    git(repo, "add", "-A")

    assert run(repo, "check-comments", "--write-baseline")[0] == 0
    assert json.loads((repo / ".baselines/comments.json").read_text())["src/a.ts"]["count"] == 2
    assert run(repo, "check-comments")[0] == 0

    write(repo, "src/a.ts", "// ADR 0023, addendum.\n// ADR 0024, addendum.\n// ADR 0025, addendum.\n")
    assert run(repo, "check-comments")[0] == 1

    write(repo, ".baselines/comments.json", json.dumps({"src/a.ts": {"count": 5, "until": PAST}}))
    code, out = run(repo, "check-comments")
    assert code == 1 and f"expired on {PAST}" in out


def test_status_line_added_with_a_blank_line_passes(tmp_path, git_repo):
    without = GOOD.replace("Date: 2026-01-01\nStatus: accepted\n", "")
    repo = adr_repo(tmp_path, git_repo, **{"0000-adopt": without})
    base = commit(repo)

    write(repo, "docs/decisions/0000-adopt.md", without.replace("# 0001. Use X\n\n", "# 0001. Use X\n\nStatus: accepted\n\n"))

    assert run(repo, "check-adr-history", base) == (0, "")


def test_root_names_the_new_place_of_a_moved_file(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, ".mise/data/root-files.txt", ".mise\n")
    write(repo, ".dependency-cruiser.cjs", "module.exports = {};\n")
    write(repo, ".size-baseline.json", "{}\n")
    git(repo, "add", "-A")

    code, out = run(repo, "check-root")

    assert code == 1
    assert ".size-baseline.json: moved to .baselines/size.json; run `git mv .size-baseline.json .baselines/size.json`" in out
    assert "then set `extends` to `./dependency-cruiser.standard.cjs`" in out


def moved_repo(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, ".mise/data/root-files.txt", ".mise\n.config\n")
    write(repo, "typos.toml", "[files]\nextend-exclude = [\"fixtures/\"]\n")
    return repo, commit(repo)


def test_since_fails_when_an_update_drops_project_content(tmp_path, git_repo):
    repo, base = moved_repo(tmp_path, git_repo)
    (repo / "typos.toml").unlink()
    write(repo, ".config/typos.toml", "[files]\nextend-exclude = []\n")
    git(repo, "add", "-A")

    code, out = run(repo, "check-root", "--since", base)

    assert code == 1 and f"git checkout {base} -- typos.toml && git mv -f typos.toml .config/typos.toml" in out


def test_since_passes_after_a_move(tmp_path, git_repo):
    repo, base = moved_repo(tmp_path, git_repo)
    (repo / ".config").mkdir()
    git(repo, "mv", "typos.toml", ".config/typos.toml")
    write(repo, ".config/typos.toml", (repo / ".config/typos.toml").read_text() + "[default]\n")

    assert run(repo, "check-root", "--since", base) == (0, "")


def test_since_allows_a_few_lines_edited_by_the_move(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, ".mise/data/root-files.txt", ".mise\n.config\n")
    write(repo, "eslint.project.mjs", "".join(f"const rule{i} = {i};\n" for i in range(10)))
    base = commit(repo)
    (repo / ".config").mkdir()
    git(repo, "mv", "eslint.project.mjs", ".config/eslint.project.mjs")
    write(repo, ".config/eslint.project.mjs", (repo / ".config/eslint.project.mjs").read_text().replace("rule0 = 0", "rule0 = 1"))

    assert run(repo, "check-root", "--since", base) == (0, "")


def test_jsdoc_on_internal_declarations_fails(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, "src/a.ts", "\n".join([
        "/** Module overview. */",
        "",
        "/** Public API. */",
        "export function a() {}",
        "/** Internal helper. */",
        "function b() {}",
        "/** @type {number} */",
        "const c = 1;",
        "class D {",
        "  /** Private state. */",
        "  #e = 1;",
        "  /** Public member. */",
        "  f() {}",
        "}",
    ]) + "\n")
    git(repo, "add", "-A")

    code, out = run(repo, "check-comments")

    assert code == 1
    assert out.splitlines() == [
        "src/a.ts:5: JSDoc on an internal declaration; use a line comment",
        "src/a.ts:10: JSDoc on an internal declaration; use a line comment",
    ]


def test_md_placement_allows_only_the_standard_docs(tmp_path, git_repo):
    repo = git_repo(tmp_path / "r")
    write(repo, ".repo.yaml", "md_exceptions: [docs/reference.md]\n")
    for rel in ("docs/architecture.md", "docs/operations.md", "docs/reference.md", "docs/journal.md"):
        write(repo, rel, "# x\n")
    git(repo, "add", "-A")

    code, out = run(repo, "check-md-placement")

    assert code == 1 and "docs/journal.md" in out and "reference" not in out and "architecture" not in out


def test_baselined_adr_may_be_rewritten_when_it_leaves_the_baseline(tmp_path, git_repo):
    old = "# 0001. Old\n\nDate: 2026-01-01. Status: plan\n\nold text\n"
    repo = adr_repo(tmp_path, git_repo, **{"0001-old": old})
    write(repo, ".baselines/adr.json", json.dumps({"docs/decisions/0001-old.md": {"lines": 5, "until": FUTURE}}))
    base = commit(repo)

    write(repo, "docs/decisions/0001-old.md", GOOD.replace("# 0001. Use X", "# 0001. Old"))
    code, out = run(repo, "check-adr-history", base)
    assert code == 1 and "changes only its `Status:` line" in out

    write(repo, ".baselines/adr.json", "{}")
    assert run(repo, "check-adr-history", base) == (0, "")

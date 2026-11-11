import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "template" / ".mise" / "tasks" / "check-size"
LIMITS = {".ts": 3, ".tsx": 4}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True).stdout


def check(repo: Path, *args: str, ci: bool = False):
    env = {k: v for k, v in os.environ.items() if k not in ("CI", "GITHUB_ACTIONS")}
    if ci:
        env["CI"] = "true"
    result = subprocess.run(["uv", "run", "--quiet", "--script", str(SCRIPT), *args], cwd=repo,
                            env=env, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def lines(n: int) -> str:
    return "".join(f"const v{i} = {i};\n\n" for i in range(n))


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def baseline(repo: Path) -> dict:
    path = repo / ".baselines/size.json"
    return json.loads(path.read_text()) if path.exists() else {}


def staged(repo: Path) -> set[str]:
    return set(git(repo, "diff", "--cached", "--name-only").split())


@pytest.fixture
def repo(tmp_path, git_repo):
    root = git_repo(tmp_path / "repo")
    write(root, ".mise/data/size-limits.json", json.dumps(LIMITS))
    return root


def commit_all(repo: Path, message: str = "chore: update") -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def test_small_file_passes_and_other_extensions_are_free(repo):
    write(repo, "a.ts", lines(3))
    write(repo, "b.md", lines(50))

    assert check(repo, "a.ts", "b.md") == (0, "")


def test_counts_only_non_empty_lines(repo):
    write(repo, "a.ts", "\n\n  \n" + lines(3))

    assert check(repo, "a.ts")[0] == 0


def test_new_file_over_limit_fails(repo):
    write(repo, "a.ts", lines(4))

    code, out = check(repo, "a.ts")

    assert code == 1
    assert "a.ts:1: 4 non-empty lines, limit 3" in out


def test_limit_per_extension(repo):
    write(repo, "c.tsx", lines(4))

    assert check(repo, "c.tsx")[0] == 0


def test_no_limits_file_checks_nothing(tmp_path, git_repo):
    root = git_repo(tmp_path / "plain")
    write(root, "a.ts", lines(500))

    assert check(root, "a.ts") == (0, "")


def test_write_baseline_records_tracked_files_over_limit(repo):
    write(repo, "big.ts", lines(5))
    write(repo, "small.ts", lines(2))
    write(repo, "src/huge.tsx", lines(9))
    commit_all(repo)

    code, _ = check(repo, "--write-baseline")

    assert code == 0
    assert baseline(repo) == {"big.ts": 5, "src/huge.tsx": 9}
    assert (repo / ".baselines/size.json").read_text().endswith("}\n")


def test_baselined_file_may_not_grow(repo):
    write(repo, "big.ts", lines(5))
    commit_all(repo)
    check(repo, "--write-baseline")
    write(repo, "big.ts", lines(6))

    code, out = check(repo, "big.ts")

    assert code == 1
    assert "big.ts:1: grew from 5 to 6 non-empty lines (baseline in .baselines/size.json)" in out
    assert baseline(repo) == {"big.ts": 5}


def test_shrunk_file_lowers_and_stages_entry(repo):
    write(repo, "big.ts", lines(7))
    commit_all(repo)
    check(repo, "--write-baseline")
    commit_all(repo)
    write(repo, "big.ts", lines(5))
    git(repo, "add", "big.ts")

    code, out = check(repo, "big.ts")

    assert code == 0, out
    assert baseline(repo) == {"big.ts": 5}
    assert ".baselines/size.json" in staged(repo)


def test_file_under_limit_leaves_baseline(repo):
    write(repo, "big.ts", lines(7))
    commit_all(repo)
    check(repo, "--write-baseline")
    write(repo, "big.ts", lines(2))

    assert check(repo, "big.ts")[0] == 0
    assert baseline(repo) == {}


def test_staged_rename_moves_entry(repo):
    write(repo, "old/big.ts", lines(6))
    commit_all(repo)
    check(repo, "--write-baseline")
    commit_all(repo)
    (repo / "features").mkdir()
    git(repo, "mv", "old/big.ts", "features/big.ts")

    code, out = check(repo, "features/big.ts")

    assert code == 0, out
    assert baseline(repo) == {"features/big.ts": 6}
    assert ".baselines/size.json" in staged(repo)


def test_staged_rename_still_may_not_grow(repo):
    write(repo, "old/big.ts", lines(6))
    commit_all(repo)
    check(repo, "--write-baseline")
    commit_all(repo)
    (repo / "new").mkdir()
    git(repo, "mv", "old/big.ts", "new/big.ts")
    write(repo, "new/big.ts", lines(7))
    git(repo, "add", "-A")

    code, out = check(repo, "new/big.ts")

    assert code == 1
    assert "new/big.ts:1: grew from 6 to 7" in out


def test_deleted_file_leaves_baseline(repo):
    write(repo, "big.ts", lines(6))
    commit_all(repo)
    check(repo, "--write-baseline")
    commit_all(repo)
    git(repo, "rm", "-q", "big.ts")

    assert check(repo, "big.ts")[0] == 0
    assert baseline(repo) == {}


def test_ci_never_writes(repo):
    write(repo, "big.ts", lines(7))
    commit_all(repo)
    check(repo, "--write-baseline")
    before = (repo / ".baselines/size.json").read_text()
    write(repo, "big.ts", lines(5))

    assert check(repo, "big.ts", ci=True)[0] == 0
    assert (repo / ".baselines/size.json").read_text() == before


def test_invalid_baseline_fails(repo):
    write(repo, ".baselines/size.json", "{not json")
    write(repo, "a.ts", lines(1))

    code, out = check(repo, "a.ts")

    assert code == 1
    assert ".baselines/size.json:1:" in out

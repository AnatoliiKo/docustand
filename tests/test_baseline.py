import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "template" / ".mise" / "tasks" / "check-baseline"
UNKNOWN = "deadbeef" * 5


def git(path: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True,
                          text=True).stdout.strip()


def run_baseline(cwd: Path, *args: str):
    result = subprocess.run(["uv", "run", "--script", str(SCRIPT), *args], cwd=cwd,
                            capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def commit_baseline(repo: Path, lines: int, message: str) -> None:
    (repo / "baseline.txt").write_text("".join(f"entry {i}\n" for i in range(lines)))
    git(repo, "add", "baseline.txt")
    git(repo, "commit", "-m", message)


def test_baseline_growth_fails(tmp_path, git_repo):
    repo = git_repo(tmp_path / "repo")
    commit_baseline(repo, 2, "chore: add baseline")
    base = git(repo, "rev-parse", "HEAD")
    commit_baseline(repo, 3, "chore: grow baseline")

    code, out = run_baseline(repo, "--file", "baseline.txt", base)

    assert code == 1
    assert "baseline.txt" in out and "2" in out and "3" in out


def test_baseline_same_or_smaller_passes(tmp_path, git_repo):
    repo = git_repo(tmp_path / "repo")
    commit_baseline(repo, 3, "chore: add baseline")
    base = git(repo, "rev-parse", "HEAD")
    commit_baseline(repo, 2, "chore: shrink baseline")

    assert run_baseline(repo, "--file", "baseline.txt", base)[0] == 0
    assert run_baseline(repo, "--file", "baseline.txt", "HEAD")[0] == 0


def test_baseline_terraform_profile_has_no_files(tmp_path, git_repo):
    repo = git_repo(tmp_path / "repo")
    (repo / ".repo.yaml").write_text("stack: [terraform]\n")
    base = git(repo, "rev-parse", "HEAD")

    assert run_baseline(repo, base)[0] == 0


def test_baseline_no_base_ref(tmp_path):
    repo = tmp_path / "fresh"
    repo.mkdir()
    git(repo, "init", "-b", "main")

    code, out = run_baseline(repo)

    assert code == 0
    assert "no base ref, skipped" in out


def test_baseline_unknown_ref_fails(tmp_path, git_repo):
    repo = git_repo(tmp_path / "repo")

    code, out = run_baseline(repo, UNKNOWN)

    assert code == 1
    assert f"base ref {UNKNOWN} not found" in out

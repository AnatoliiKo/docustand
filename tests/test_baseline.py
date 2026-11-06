import importlib.machinery
import importlib.util
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


def commit_repo_yaml(repo: Path, content: str | None, message: str) -> None:
    if content is None:
        return
    (repo / ".repo.yaml").write_text(content)
    git(repo, "add", ".repo.yaml")
    git(repo, "commit", "-m", message)


def new_baseline_case(repo: Path, base_yaml: str | None, head_yaml: str | None) -> str:
    commit_repo_yaml(repo, base_yaml, "chore: add answers")
    if base_yaml is None:
        (repo / "other.txt").write_text("x\n")
        git(repo, "add", "other.txt")
        git(repo, "commit", "-m", "chore: add file")
    base = git(repo, "rev-parse", "HEAD")
    commit_repo_yaml(repo, head_yaml, "chore: change answers")
    commit_baseline(repo, 2, "chore: add baseline")
    return base


@pytest.mark.parametrize("base_yaml,head_yaml,reason", [
    ("stack: []\n_commit: v1\n", "stack: [terraform]\n_commit: v1\n", "stack changed"),
    ("stack: []\n_commit: v1\n", "stack: []\n_commit: v2\n", "_commit changed"),
    (None, "stack: []\n_commit: v1\n", ".repo.yaml absent at base"),
])
def test_new_baseline_file_allowed(tmp_path, git_repo, base_yaml, head_yaml, reason):
    repo = git_repo(tmp_path / "repo")
    base = new_baseline_case(repo, base_yaml, head_yaml)

    code, out = run_baseline(repo, "--file", "baseline.txt", base)

    assert code == 0
    assert f"baseline.txt: new baseline file allowed: {reason}" in out


def test_new_baseline_file_without_repo_yaml_change_fails(tmp_path, git_repo):
    repo = git_repo(tmp_path / "repo")
    base = new_baseline_case(repo, "stack: []\n_commit: v1\n", "stack: []\n_commit: v1\nname: x\n")

    code, out = run_baseline(repo, "--file", "baseline.txt", base)

    assert code == 1
    assert "baseline.txt:1: new baseline file without .repo.yaml change" in out


def run_case(repo: Path, base_yaml: str | None, head_yaml: str | None, *args: str):
    """Base commit has `base_yaml`; the head adds baseline.txt and sets `.repo.yaml` to `head_yaml`."""
    commit_repo_yaml(repo, base_yaml, "chore: add answers")
    if base_yaml is None:
        (repo / "other.txt").write_text("x\n")
        git(repo, "add", "other.txt")
        git(repo, "commit", "-m", "chore: add file")
    base = git(repo, "rev-parse", "HEAD")
    if head_yaml is None:
        if (repo / ".repo.yaml").exists():
            git(repo, "rm", "-q", ".repo.yaml")
    else:
        (repo / ".repo.yaml").write_text(head_yaml)
    commit_baseline(repo, 2, "chore: add baseline")
    return run_baseline(repo, *args, base)


@pytest.mark.parametrize("head_yaml", [None, "", "- a\n"])
def test_new_baseline_with_missing_or_empty_repo_yaml_fails(tmp_path, git_repo, head_yaml):
    code, out = run_case(git_repo(tmp_path / "repo"), "stack: [a]\n", head_yaml, "--file", "baseline.txt")

    assert code == 1
    assert ".repo.yaml:1: missing or not a mapping" in out


def test_new_baseline_with_missing_repo_yaml_fails_even_after_migration(tmp_path, git_repo):
    code, out = run_case(git_repo(tmp_path / "repo"), None, None, "--file", "baseline.txt")

    assert code == 1 and ".repo.yaml:1:" in out


def test_stack_reorder_and_null_are_not_changes(tmp_path, git_repo):
    code, out = run_case(git_repo(tmp_path / "r1"), "stack: [a, b]\n", "stack: [b, a]\n", "--file", "baseline.txt")
    assert code == 1 and "without .repo.yaml change" in out
    code, out = run_case(git_repo(tmp_path / "r2"), "stack: null\n", "stack: []\n", "--file", "baseline.txt")
    assert code == 1 and "without .repo.yaml change" in out


def test_reason_shows_values(tmp_path, git_repo):
    _, out = run_case(git_repo(tmp_path / "r1"), "stack: [a]\n", "stack: [a, b]\n", "--file", "baseline.txt")
    assert "stack changed: [a] -> [a, b]" in out
    _, out = run_case(git_repo(tmp_path / "r2"), "_commit: '1.1'\n", "_commit: '1.10'\n", "--file", "baseline.txt")
    assert "_commit changed: 1.1 -> 1.10" in out


def test_invalid_yaml_fails_without_traceback(tmp_path, git_repo):
    code, out = run_case(git_repo(tmp_path / "r1"), "stack: [a]\n", "stack: [a\n", "--file", "baseline.txt")
    assert code == 1 and ".repo.yaml:1: invalid YAML" in out and "Traceback" not in out
    code, out = run_case(git_repo(tmp_path / "r2"), "stack: [a\n", "stack: [a]\n", "--file", "baseline.txt")
    assert code == 1 and ".repo.yaml:1: invalid YAML" in out and "Traceback" not in out


def test_growth_of_existing_baseline_fails_when_reason_exists(tmp_path, git_repo):
    repo = git_repo(tmp_path / "repo")
    commit_baseline(repo, 2, "chore: add baseline")
    commit_repo_yaml(repo, "stack: []\n", "chore: answers")
    base = git(repo, "rev-parse", "HEAD")
    (repo / ".repo.yaml").write_text("stack: [a]\n")
    commit_baseline(repo, 3, "chore: grow baseline")

    code, out = run_baseline(repo, "--file", "baseline.txt", base)

    assert code == 1 and "baseline grew from 2 to 3" in out


def test_two_new_files_are_each_printed(tmp_path, git_repo):
    repo = git_repo(tmp_path / "repo")
    base = new_baseline_case(repo, "_commit: v1\n", "_commit: v2\n")
    (repo / "second.txt").write_text("x\n")

    code, out = run_baseline(repo, "--file", "baseline.txt", "--file", "second.txt", base)

    assert code == 0
    assert "baseline.txt: new baseline file allowed" in out
    assert "second.txt: new baseline file allowed" in out


def test_stack_change_allows_only_added_profile_baselines(tmp_path, git_repo, monkeypatch, capsys):
    loader = importlib.machinery.SourceFileLoader("check_baseline_script", str(SCRIPT))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("check_baseline_script", loader))
    loader.exec_module(module)
    monkeypatch.setitem(module.PROFILE_BASELINES, "a", ["a.baseline"])
    monkeypatch.setitem(module.PROFILE_BASELINES, "b", ["b.baseline"])
    repo = git_repo(tmp_path / "repo")
    commit_repo_yaml(repo, "stack: [b]\n", "chore: answers")
    base = git(repo, "rev-parse", "HEAD")
    (repo / ".repo.yaml").write_text("stack: [a, b]\n")
    (repo / "a.baseline").write_text("x\n")
    (repo / "b.baseline").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "chore: adopt a")
    monkeypatch.chdir(repo)

    assert module.main([base]) == 1
    out = capsys.readouterr().out
    assert "a.baseline: new baseline file allowed" in out
    assert "b.baseline:1:" in out

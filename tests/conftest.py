"""Shared pytest fixtures for the docustand template tests."""

import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True)


def init_git_repo(path: Path) -> Path:
    """Create a git repo on `main` with local test identity and an empty commit."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "commit", "--allow-empty", "-m", "init")
    return path


@pytest.fixture
def git_repo():
    """Callable `git_repo(path) -> Path` that initialises a git repo at `path`."""
    return init_git_repo


def _as_answer(value) -> str:
    if isinstance(value, str):
        return value
    return yaml.safe_dump(value, default_flow_style=True).strip().removesuffix("\n...").strip()


def run_copier(dest: Path, src: Path = REPO_ROOT, **data) -> subprocess.CompletedProcess:
    overwrite = data.pop("overwrite", False)
    cmd = ["copier", "copy", "--defaults", "--vcs-ref", "HEAD"]
    if overwrite:
        cmd.append("--overwrite")
    for key, value in data.items():
        cmd += ["--data", f"{key}={_as_answer(value)}"]
    cmd += [str(src), str(dest)]
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True)


@pytest.fixture
def render():
    """Callable `render(tmp_path, src=REPO_ROOT, check=True, **data)`.

    Runs `copier copy` and returns the destination path. With `check=False`
    returns the CompletedProcess instead, so tests can assert non-zero exits.
    """

    def _render(tmp_path: Path, src: Path = REPO_ROOT, check: bool = True, **data):
        dest = tmp_path / "project"
        result = run_copier(dest, src, **data)
        if not check:
            return result
        if result.returncode != 0:
            pytest.fail(f"copier failed ({result.returncode}):\n{result.stderr}")
        return dest

    return _render

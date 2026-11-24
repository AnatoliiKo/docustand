"""Shared pytest fixtures for the docustand template tests."""

import json
import os
import shutil
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


GH_STUB = """#!/usr/bin/env python3
import json, os, subprocess, sys
path = os.path.join(os.environ["STUB_DIR"], "gh.json")
state = json.load(open(path))
args = sys.argv[1:]
open(os.environ["STUB_LOG"], "a").write("gh " + " ".join(args) + "\\n")
if args[:2] == ["pr", "list"]:
    print(json.dumps(state["prs"]))
elif args[:2] == ["pr", "create"]:
    if state.get("create_fail"):
        print("gh: create failed", file=sys.stderr)
        sys.exit(1)
    head = args[args.index("--head") + 1]
    tip = subprocess.run(["git", "ls-remote", "--heads", "origin", head], capture_output=True, text=True).stdout.split()[0]
    number = len(state["prs"]) + 1
    state["prs"].append({"number": number, "state": "OPEN", "headRefOid": tip, "isCrossRepository": False})
    json.dump(state, open(path, "w"))
    open(os.path.join(os.environ["STUB_DIR"], "body.txt"), "w").write(args[args.index("--body") + 1])
    print(f"https://example.test/pull/{number}")
"""
MISE_STUB = """#!/bin/sh
echo "mise $*" >> "$STUB_LOG"
if [ -f "$STUB_DIR/mise-fail" ]; then echo "check failed" >&2; exit 1; fi
if [ -f "$STUB_DIR/mise-edit" ]; then . "$STUB_DIR/mise-edit"; fi
"""
SIZE_SHIM = """#!/bin/sh
echo "check-size $*" >> "$STUB_LOG"
[ -f "$STUB_DIR/real-size" ] || exit 0
exec "$(dirname "$0")/check-size.real" "$@"
"""


def _git_out(path: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True).stdout


class World:
    """A project with a bare `origin` and stubs of `gh` and `mise` that log into `log`."""

    def __init__(self, root: Path, remote: Path, stub: Path) -> None:
        self.root, self.remote, self.stub = root, remote, stub

    def maintain(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        script = self.root / ".mise/tasks/maintain"
        return subprocess.run([str(script), *args], cwd=cwd or self.root, capture_output=True, text=True)

    def git(self, *args: str) -> str:
        return _git_out(self.root, *args)

    def remote_git(self, *args: str) -> str:
        return _git_out(self.remote, *args)

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit_base(self, message: str = "chore: update base") -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        self.git("push", "-q", "origin", "main")

    def real_size(self) -> None:
        """Let the logging stand-in of `check-size` run the real script."""
        (self.stub / "real-size").write_text("")

    def start(self, job: str = "docs-drift") -> None:
        result = self.maintain("start", job, "--local")
        assert result.returncode == 0, result.stdout + result.stderr

    def prs(self, *prs: dict, **extra: object) -> None:
        (self.stub / "gh.json").write_text(json.dumps({"prs": list(prs), **extra}))

    @property
    def log(self) -> str:
        path = self.stub / "log.txt"
        return path.read_text() if path.exists() else ""


@pytest.fixture(scope="session")
def maintain_template(tmp_path_factory):
    """Callable `maintain_template(**data) -> Path`: a rendered, committed project, rendered once per answers."""
    cache: dict[str, Path] = {}

    def _template(**data) -> Path:
        key = json.dumps(data, sort_keys=True)
        if key not in cache:
            root = tmp_path_factory.mktemp("maintain") / "project"
            result = run_copier(root, project_name="demo", **{"maintain_adapter": "manual", **data})
            assert result.returncode == 0, result.stderr
            init_git_repo(root)
            real = root / ".mise/tasks/check-size"
            real.rename(real.with_name("check-size.real"))
            real.write_text(SIZE_SHIM)
            real.chmod(0o755)
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "chore: base")
            cache[key] = root
        return cache[key]

    return _template


@pytest.fixture
def world(maintain_template, tmp_path, monkeypatch):
    """Callable `world(**data) -> World`: a copy of the rendered project with a bare `origin` on `main`."""

    def _world(**data) -> World:
        root = tmp_path / "project"
        shutil.copytree(maintain_template(**data), root, symlinks=True)
        remote = tmp_path / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(root), str(remote)], check=True, capture_output=True)
        _git(root, "remote", "add", "origin", str(remote))
        _git(root, "fetch", "-q", "origin")
        _git(root, "branch", "-q", "-u", "origin/main")
        stub = tmp_path / "stub"
        (stub / "bin").mkdir(parents=True)
        for name, body in (("gh", GH_STUB), ("mise", MISE_STUB)):
            (stub / "bin" / name).write_text(body)
            (stub / "bin" / name).chmod(0o755)
        (stub / "gh.json").write_text('{"prs": []}')
        monkeypatch.setenv("PATH", f"{stub / 'bin'}{os.pathsep}{os.environ['PATH']}")
        monkeypatch.setenv("STUB_DIR", str(stub))
        monkeypatch.setenv("STUB_LOG", str(stub / "log.txt"))
        monkeypatch.delenv("CI", raising=False)
        return World(root, remote, stub)

    return _world

"""Integration tests of the maintenance contract: real hooks and the full `mise run check`.

Needs mise and network on the first run. The agent of a job is a shell script.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from conftest import REPO_ROOT, init_git_repo, run_copier
from test_gates_fail import mise_env, sh

pytestmark = pytest.mark.integration

JOBS = ".maintain/manual/run"


def build(tmp_path: Path, files: dict[str, str] | None = None, **data) -> tuple[Path, dict[str, str]]:
    """A rendered project with its own files committed, tools and hooks installed, and a bare `origin`."""
    env = mise_env(tmp_path)
    root = tmp_path / "project"
    rendered = run_copier(root, project_name="demo", **{"maintain_adapter": "manual", **data})
    assert rendered.returncode == 0, rendered.stderr
    answers = root / ".repo.yaml"
    # The hash in a describe-style `_commit` can contain a word the spelling check rewrites.
    answers.write_text(re.sub(r"(?m)^_commit:.*$", "_commit: v0.0.0", answers.read_text()))
    init_git_repo(root)
    for rel, text in (files or {}).items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    sh(root, env, "git", "add", "-A", check=True)
    sh(root, env, "git", "commit", "-q", "-m", "chore: add project files", check=True)
    sh(root, env, "mise", "install", check=True)
    remote = tmp_path / "remote.git"
    sh(tmp_path, env, "git", "clone", "-q", "--bare", str(root), str(remote), check=True)
    sh(root, env, "git", "remote", "add", "origin", str(remote), check=True)
    sh(root, env, "git", "fetch", "-q", "origin", check=True)
    return root, env


def agent(root: Path, body: str) -> list[str]:
    script = root.parent / "agent.sh"
    script.write_text("#!/bin/sh\ncat > /dev/null\n" + body)
    script.chmod(0o755)
    return [str(script)]


@pytest.mark.parametrize("data", [
    {},
    {"language": "ru"},
    {"maintain_adapter": "codex"},
])
def test_project_with_adapter_passes_check(tmp_path, data):
    root, env = build(tmp_path, **data)

    result = sh(root, env, "mise", "run", "check")

    assert result.returncode == 0, result.stdout + result.stderr


def test_typescript_documents_pass_doc_paths(tmp_path):
    root = tmp_path / "project"
    assert run_copier(root, project_name="demo", stack=["typescript"], maintain_adapter="manual").returncode == 0
    init_git_repo(root)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "chore: base"], check=True, capture_output=True)

    result = subprocess.run(["uv", "run", "--script", str(root / ".mise/tasks/check-doc-paths")], cwd=root,
                            capture_output=True, text=True)

    assert result.returncode == 0 and result.stdout == "", result.stdout + result.stderr


def test_manual_run_commits_through_real_hooks(tmp_path):
    files = {"docs/runbooks/old.md": "# Old runbook\n\nRemove this runbook.\n"}
    root, env = build(tmp_path, files)
    body = ("printf '\\nMore text of the document.\\n' >> README.md\n"
            "printf '# Start the service\\n\\nRun the service with the script.\\n' > 'docs/runbooks/запуск.md'\n"
            "rm docs/runbooks/old.md\n")

    result = sh(root, env, JOBS, "docs-drift", "--local", "--", *agent(root, body))

    assert result.returncode == 0, result.stdout + result.stderr
    assert sh(root, env, "git", "rev-list", "--count", "origin/main..HEAD").stdout.strip() == "1"
    assert sh(root, env, "git", "branch", "--show-current").stdout.strip() == "maintain/docs-drift"
    names = sh(root, env, "git", "-c", "core.quotepath=off", "show", "--name-only", "--format=", "HEAD").stdout.split("\n")
    assert {"README.md", "docs/runbooks/запуск.md", "docs/runbooks/old.md"} <= set(names)
    assert sh(root, env, "uv", "run", "--script", ".mise/tasks/check-doc-paths").returncode == 0


def test_dead_code_shrinks_size_baseline_with_real_check(tmp_path):
    big = "".join(f"x{i} = {i}\n" for i in range(8))
    files = {
        "docs/big.dat": big,
        ".mise/data/size-limits.json": '{".dat": 3}',
        ".baselines/size.json": json.dumps({"docs/big.dat": {"lines": 8, "until": "2099-01-31"}}),
    }
    root, env = build(tmp_path, files)
    body = "".join(["printf '" + "".join(f"x{i} = {i}\\n" for i in range(5)) + "' > docs/big.dat\n"])

    result = sh(root, env, JOBS, "dead-code", "--local", "--", *agent(root, body))

    assert result.returncode == 0, result.stdout + result.stderr
    shown = sh(root, env, "git", "show", "HEAD:.baselines/size.json").stdout
    assert json.loads(shown)["docs/big.dat"]["lines"] == 5


def test_update_of_old_answers_adds_none_and_off(tmp_path):
    template = tmp_path / "template-repo"
    template.mkdir()
    shutil.copy(REPO_ROOT / "copier.yml", template / "copier.yml")
    shutil.copytree(REPO_ROOT / "template", template / "template", ignore=shutil.ignore_patterns("__pycache__"))
    init_git_repo(template)
    for args in (("add", "-A"), ("commit", "-qm", "v1"), ("tag", "v0.0.1")):
        subprocess.run(["git", "-C", str(template), *args], check=True, capture_output=True)
    env = mise_env(tmp_path)
    project = tmp_path / "project"
    subprocess.run(["copier", "copy", "--defaults", "--vcs-ref", "v0.0.1", "--data", "project_name=demo",
                    str(template), str(project)], check=True, capture_output=True, stdin=subprocess.DEVNULL)
    answers = project / ".repo.yaml"
    answers.write_text("".join(line + "\n" for line in answers.read_text().splitlines()
                               if not line.startswith("maintain_")))
    init_git_repo(project)
    sh(project, env, "git", "add", "-A", check=True)
    sh(project, env, "git", "commit", "-qm", "chore: base", check=True)
    marker = template / "template/.worktreeinclude"
    marker.write_text(marker.read_text() + "\n")
    for args in (("add", "-A"), ("commit", "-qm", "v2"), ("tag", "v0.0.2")):
        subprocess.run(["git", "-C", str(template), *args], check=True, capture_output=True)

    update = sh(project, env, "copier", "update", "-a", ".repo.yaml", "--defaults", "--vcs-ref", "v0.0.2")

    assert update.returncode == 0, update.stdout + update.stderr
    data = yaml.safe_load(answers.read_text())
    assert data["maintain_adapter"] == "none" and data["maintain_schedule"] == "off"
    assert not (project / ".maintain").exists() and not (project / ".mise/tasks/maintain").exists()
    sh(project, env, "mise", "install", check=True)
    sh(project, env, "git", "add", "-A", check=True)
    assert sh(project, env, "mise", "run", "check").returncode == 0

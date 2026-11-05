"""Integration test: a project detached from docustand works without it.

The detach procedure below (steps 1-5; step 6, the scheduled Claude task, does
not exist at the base level) is the one the `repo-init` skill carries.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from conftest import init_git_repo, run_copier
from test_gates_fail import MAIN_TF, mise_env, sh

pytestmark = pytest.mark.integration

REPO_YAML_HEADER = "# Project properties checked by .github/repo.schema.json.\n"
RENOVATE_IGNORED = {".mise/conf.d/standard.toml", ".github/workflows/standard-*.yml"}
AGENTS_LINE = "If docustand is installed: /docustand:pr-ready."


def detach_1_repo_yaml(root: Path) -> None:
    """Drop `_src_path` and `_commit`; replace the Copier header."""
    path = root / ".repo.yaml"
    data = yaml.safe_load(path.read_text())
    for key in ("_src_path", "_commit"):
        data.pop(key, None)
    path.write_text(REPO_YAML_HEADER + yaml.safe_dump(data, sort_keys=False))


def detach_2_mise_copier(root: Path) -> None:
    """Remove the `pipx:copier` tool line from the standard mise config."""
    path = root / ".mise/conf.d/standard.toml"
    lines = [ln for ln in path.read_text().splitlines(keepends=True)
             if not ln.lstrip().startswith('"pipx:copier"')]
    path.write_text("".join(lines))


def detach_3_claude_settings(root: Path) -> None:
    """Remove the docustand plugin and its marketplace."""
    path = root / ".claude/settings.json"
    data = json.loads(path.read_text())
    data.get("enabledPlugins", {}).pop("docustand@docustand", None)
    data.get("extraKnownMarketplaces", {}).pop("docustand", None)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def detach_4_agents_md(root: Path) -> None:
    """Remove the line that points to the docustand pr-ready command, with the
    blank line before it (two blank lines in a row fail the markdown lint)."""
    path = root / "AGENTS.md"
    text = path.read_text()
    updated = re.sub(rf"\n*^{re.escape(AGENTS_LINE)}\n", "\n", text, flags=re.M)
    assert updated != text, "docustand line not found in AGENTS.md"
    path.write_text(updated)


def detach_5_renovate(root: Path) -> None:
    """Remove the `copier` manager block and the standard-file `ignorePaths`."""
    path = root / "renovate.json"
    data = json.loads(path.read_text())
    data.pop("copier", None)
    remaining = [p for p in data.get("ignorePaths", []) if p not in RENOVATE_IGNORED]
    if remaining:
        data["ignorePaths"] = remaining
    else:
        data.pop("ignorePaths", None)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def detach(root: Path) -> None:
    for step in (detach_1_repo_yaml, detach_2_mise_copier, detach_3_claude_settings,
                 detach_4_agents_md, detach_5_renovate):
        step(root)


@pytest.fixture
def detached(tmp_path_factory):
    env = mise_env(tmp_path_factory.getbasetemp())
    rendered = tmp_path_factory.mktemp("rendered") / "project"
    result = run_copier(rendered, project_name="demo", stack=["terraform"])
    assert result.returncode == 0, result.stderr
    original = yaml.safe_load((rendered / ".repo.yaml").read_text())

    root = tmp_path_factory.mktemp("detached") / "project"
    shutil.copytree(rendered, root, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    init_git_repo(root)
    (root / "main.tf").write_text(MAIN_TF)
    sh(root, env, "mise", "install", check=True)
    sh(root, env, "git", "add", "-A", check=True)
    sh(root, env, "git", "commit", "-m", "chore: add project files", check=True)

    detach(root)
    sh(root, env, "git", "add", "-A", check=True)
    sh(root, env, "git", "commit", "-m", "chore: detach from docustand", check=True)
    return root, env, original


def test_detached_project_passes_without_docustand(detached):
    root, env, original = detached

    grep = subprocess.run(["grep", "-rIil", "docustand", "--exclude-dir=decisions",
                           "--exclude-dir=.git", "."], cwd=root, capture_output=True, text=True)
    assert grep.stdout == "", f"docustand is still mentioned in:\n{grep.stdout}"

    renovate = json.loads((root / "renovate.json").read_text())
    assert "copier" not in renovate
    assert not RENOVATE_IGNORED & set(renovate.get("ignorePaths", []))

    text = (root / ".repo.yaml").read_text()
    assert text.startswith(REPO_YAML_HEADER)
    assert "copier" not in text.splitlines()[0].lower()
    answers = yaml.safe_load(text)
    assert "_src_path" not in answers and "_commit" not in answers
    assert answers == {k: v for k, v in original.items() if k not in ("_src_path", "_commit")}

    assert "pipx:copier" not in (root / ".mise/conf.d/standard.toml").read_text()
    assert not (root / "mise.toml").exists()
    assert not (root / ".mise.toml").exists()

    repo_yaml = sh(root, env, "mise", "run", "check-repo-yaml")
    assert repo_yaml.returncode == 0, repo_yaml.stdout + repo_yaml.stderr
    result = sh(root, env, "mise", "run", "check")
    assert result.returncode == 0, result.stdout + result.stderr

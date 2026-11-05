import json
import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "template/.mise/tasks/detect-stack"


def detect(path, *extra):
    result = subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), *extra, str(path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def write(root: Path, rel: str, text: str = ""):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def repo(tmp_path, git_repo):
    return git_repo(tmp_path / "repo")


def test_detects_terraform(repo):
    write(repo, "main.tf")
    write(repo, "infra/net/vpc.tf")

    out = detect(repo)

    assert out["stack"] == ["terraform"]
    assert out["evidence"]["terraform"] == ["infra/net/vpc.tf", "main.tf"]


def test_ignores_dot_terraform_dir(repo):
    write(repo, ".terraform/modules/x/main.tf")
    write(repo, "infra/.terraform/y.tf")

    assert detect(repo) == {"stack": [], "evidence": {}}


def test_detects_laravel_by_artisan(repo):
    write(repo, "artisan", "#!/usr/bin/env php\n")

    out = detect(repo)

    assert out["stack"] == ["laravel"]
    assert out["evidence"]["laravel"] == ["artisan"]


def test_empty_repo_is_empty_stack(repo):
    assert detect(repo) == {"stack": [], "evidence": {}}


def test_no_commits_is_empty_stack(tmp_path):
    root = tmp_path / "fresh"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)

    assert detect(root) == {"stack": [], "evidence": {}}


def test_detects_nextjs_and_expo_from_package_json(repo):
    write(repo, "package.json", json.dumps(
        {"dependencies": {"next": "15.0.0"}, "devDependencies": {"expo": "~52.0.0"}}))

    out = detect(repo)

    assert out["stack"] == ["expo", "nextjs"]
    assert out["evidence"] == {"expo": ["package.json"], "nextjs": ["package.json"]}


def test_package_json_without_signals_or_broken(repo):
    write(repo, "package.json", json.dumps({"dependencies": {"react": "19"}}))
    assert detect(repo)["stack"] == []

    write(repo, "package.json", "{not json")
    assert detect(repo)["stack"] == []


def test_works_outside_git(tmp_path):
    root = tmp_path / "plain"
    write(root, "a/main.tf")
    write(root, "node_modules/pkg/x.tf")
    write(root, "vendor/y.tf")
    write(root, ".terraform/z.tf")
    write(root, ".git/w.tf")
    write(root, "artisan")

    out = detect(root)

    assert out["stack"] == ["laravel", "terraform"]
    assert out["evidence"]["terraform"] == ["a/main.tf"]


def test_defaults_to_cwd(tmp_path):
    write(tmp_path, "main.tf")

    result = subprocess.run(["uv", "run", "--script", str(SCRIPT)], cwd=tmp_path,
                            capture_output=True, text=True)

    assert json.loads(result.stdout)["stack"] == ["terraform"]


def test_evidence_is_capped_and_sorted(repo):
    for i in range(15):
        write(repo, f"m{i:02}/main.tf")

    paths = detect(repo)["evidence"]["terraform"]

    assert paths == sorted(paths) and len(paths) == 10


def test_tflint_config_rendered_only_for_terraform(render, tmp_path):
    with_tf = render(tmp_path / "a", project_name="demo", stack=["terraform"])
    without = render(tmp_path / "b", project_name="demo")

    text = (with_tf / ".tflint.hcl").read_text()
    assert "terraform_unused_declarations" in text and 'preset  = "recommended"' in text
    assert not (without / ".tflint.hcl").exists()

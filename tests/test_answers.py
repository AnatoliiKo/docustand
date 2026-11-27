import subprocess
from pathlib import Path

import pytest
import yaml

from conftest import REPO_ROOT

SCHEMA = REPO_ROOT / "template" / ".github" / "repo.schema.json"


def test_answers_file_is_repo_yaml(render, tmp_path):
    dest = render(tmp_path, project_name="demo")

    answers = yaml.safe_load((dest / ".repo.yaml").read_text())

    assert "_src_path" in answers
    assert "_commit" in answers
    assert answers["level"] == "base"
    assert answers["team"] == "solo"
    assert answers["report_schedule"] == "weekly"
    assert answers["language"] == "en"
    assert answers["overrides"] == []


def test_no_unsafe_features(tmp_path):
    config = yaml.safe_load((REPO_ROOT / "copier.yml").read_text())
    for key in ("_tasks", "_migrations", "_jinja_extensions"):
        assert key not in config

    dest = tmp_path / "project"
    result = subprocess.run(
        ["copier", "copy", "--defaults", "--vcs-ref", "HEAD",
         "--data", "project_name=demo", str(REPO_ROOT), str(dest)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_full_level_rejected_for_now(render, tmp_path):
    result = render(tmp_path, check=False, project_name="demo", level="full")

    assert result.returncode != 0
    assert "not supported yet" in result.stdout + result.stderr


def test_schema_rejects_unknown_key(render, tmp_path):
    dest = render(tmp_path, project_name="demo")
    schema = dest / ".github" / "repo.schema.json"
    answers = dest / ".repo.yaml"

    ok = subprocess.run(["check-jsonschema", "--schemafile", str(schema), str(answers)],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr

    answers.write_text(answers.read_text() + "foo: 1\n")
    bad = subprocess.run(["check-jsonschema", "--schemafile", str(schema), str(answers)],
                         capture_output=True, text=True)
    assert bad.returncode == 1


@pytest.mark.parametrize("value, valid", [
    ('{"apps/web/src": "fsd"}', True),
    ('{"apps/web/src": {"style": "fsd", "script": "lint:fsd"}}', True),
    ('{"apps/web/src": {"script": "lint:fsd"}}', False),
    ('{"apps/web/src": {"style": "fsd", "script": "lint:fsd && true"}}', False),
    ('{"apps/web/src": {"style": "fsd", "command": "x"}}', False),
])
def test_schema_checks_architecture_parts(render, tmp_path, value, valid):
    dest = render(tmp_path, project_name="demo")
    schema = dest / ".github" / "repo.schema.json"
    answers = dest / ".repo.yaml"
    answers.write_text(answers.read_text().replace("architecture: {}", f"architecture: {value}"))
    assert f"architecture: {value}" in answers.read_text()

    result = subprocess.run(["check-jsonschema", "--schemafile", str(schema), str(answers)],
                            capture_output=True, text=True)
    assert (result.returncode == 0) is valid, result.stdout + result.stderr


def test_schema_rejects_empty_ci_branches(render, tmp_path):
    dest = render(tmp_path, project_name="demo")
    schema = dest / ".github" / "repo.schema.json"
    answers = dest / ".repo.yaml"
    answers.write_text(answers.read_text().replace("required_ci_branches:\n- main", "required_ci_branches: []"))
    assert "required_ci_branches: []" in answers.read_text()

    result = subprocess.run(["check-jsonschema", "--schemafile", str(schema), str(answers)],
                            capture_output=True, text=True)
    assert result.returncode == 1


def test_copier_rejects_empty_ci_branches(render, tmp_path):
    for value in ([], ""):
        result = render(tmp_path / f"v{len(str(value))}", check=False, project_name="demo",
                        required_ci_branches=value)

        assert result.returncode != 0, value
        assert "non-empty list" in result.stdout + result.stderr


def test_schema_accepts_float_like_commit(render, tmp_path):
    dest = render(tmp_path, project_name="demo")
    schema = dest / ".github" / "repo.schema.json"
    answers = dest / ".repo.yaml"
    lines = [
        "_commit: 2239e11" if line.startswith("_commit:") else line
        for line in answers.read_text().splitlines()
    ]
    answers.write_text("\n".join(lines) + "\n")

    result = subprocess.run(["check-jsonschema", "--schemafile", str(schema), str(answers)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_maintain_answers_default_to_none_and_off(render, tmp_path):
    dest = render(tmp_path, project_name="demo")

    answers = yaml.safe_load((dest / ".repo.yaml").read_text())

    assert answers["maintain_adapter"] == "none"
    assert answers["maintain_schedule"] == "off"
    assert "maintain_schedule: 'off'" in (dest / ".repo.yaml").read_text()


@pytest.mark.parametrize("name", ["Bad Name", "../x", "jobs"])
def test_copier_rejects_invalid_maintain_adapter(render, tmp_path, name):
    result = render(tmp_path, check=False, project_name="demo", maintain_adapter=name)

    assert result.returncode != 0
    assert "maintain_adapter needs a name" in result.stdout + result.stderr


@pytest.mark.parametrize("schedule", ["weekly", "monthly"])
def test_copier_rejects_maintain_schedule_without_ci_adapter(render, tmp_path, schedule):
    result = render(tmp_path, check=False, project_name="demo", maintain_schedule=schedule)

    assert result.returncode != 0
    assert "not supported yet" in result.stdout + result.stderr


def _validate(dest, text: str) -> subprocess.CompletedProcess[str]:
    answers = dest / ".repo.yaml"
    answers.write_text(answers.read_text() + text)
    return subprocess.run(["check-jsonschema", "--schemafile", str(dest / ".github" / "repo.schema.json"),
                           str(answers)], capture_output=True, text=True)


@pytest.mark.parametrize("text, valid", [
    ("maintain_adapter: manual\nmaintain_schedule: weekly\n", True),
    ("maintain_adapter: codex-2\n", True),
    ("maintain_adapter: Bad Name\n", False),
    ("maintain_adapter: ../x\n", False),
    ("maintain_adapter: jobs\n", False),
    ("maintain_schedule: daily\n", False),
])
def test_schema_checks_maintain_answers(render, tmp_path, text, valid):
    dest = render(tmp_path, project_name="demo")
    answers = dest / ".repo.yaml"
    answers.write_text("".join(line + "\n" for line in answers.read_text().splitlines()
                               if not line.startswith("maintain_")))

    result = _validate(dest, text)

    assert (result.returncode == 0) is valid, result.stdout + result.stderr


def test_schema_accepts_missing_maintain_answers(render, tmp_path):
    dest = render(tmp_path, project_name="demo")
    answers = dest / ".repo.yaml"
    answers.write_text("".join(line + "\n" for line in answers.read_text().splitlines()
                               if not line.startswith("maintain_")))

    assert _validate(dest, "").returncode == 0


WORKFLOWS = (".github/workflows/standard-ci.yml", ".github/workflows/standard-report.yml")


def _runs_on(dest) -> list[str]:
    return [line.strip() for name in WORKFLOWS
            for line in (dest / name).read_text().splitlines() if line.strip().startswith("runs-on:")]


def test_ci_runner_defaults_to_github_hosted_ubuntu(render, tmp_path):
    dest = render(tmp_path, project_name="demo")

    assert yaml.safe_load((dest / ".repo.yaml").read_text())["ci_runner"] == "ubuntu-latest"
    assert _runs_on(dest) == ["runs-on: ubuntu-latest"] * 3
    assert "ci_runs_on" not in (dest / ".repo.yaml").read_text()


def test_ci_runner_label_selects_a_self_hosted_runner(render, tmp_path):
    dest = render(tmp_path, project_name="demo", ci_runner="vm-docker")

    assert _runs_on(dest) == ["runs-on: [self-hosted, vm-docker]"] * 3
    for name in WORKFLOWS:
        assert yaml.safe_load((dest / name).read_text())


def test_ci_runner_keeps_other_github_hosted_ubuntu_labels(render, tmp_path):
    dest = render(tmp_path, project_name="demo", ci_runner="ubuntu-24.04")

    assert _runs_on(dest) == ["runs-on: ubuntu-24.04"] * 3


@pytest.mark.parametrize("label", ["VM Docker", "-x", "a/b"])
def test_copier_rejects_invalid_ci_runner(render, tmp_path, label):
    result = render(tmp_path, check=False, project_name="demo", ci_runner=label)

    assert result.returncode != 0
    assert "ci_runner needs a runner label" in result.stdout + result.stderr


@pytest.mark.parametrize("text, valid", [
    ("ci_runner: vm-docker\n", True),
    ("ci_runner: ubuntu-24.04\n", True),
    ("ci_runner: VM Docker\n", False),
])
def test_schema_checks_ci_runner(render, tmp_path, text, valid):
    dest = render(tmp_path, project_name="demo")
    answers = dest / ".repo.yaml"
    answers.write_text("".join(line + "\n" for line in answers.read_text().splitlines()
                               if not line.startswith("ci_runner:")))

    result = _validate(dest, text)

    assert (result.returncode == 0) is valid, result.stdout + result.stderr

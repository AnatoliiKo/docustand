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

"""Tests of the `language` answer, the shared detector and the checks built on it."""
import json
import subprocess
from pathlib import Path

import pytest
import yaml

RU = "Повторить запрос позже после ошибки"
EN = "retry the request later after an error"


@pytest.fixture
def project(render, tmp_path, git_repo):
    def make(**data) -> Path:
        dest = render(tmp_path, project_name="demo", **data)
        git_repo(dest)
        return dest

    return make


def run(dest: Path, task: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["uv", "run", "--script", str(dest / ".mise/tasks" / task), *args],
                          cwd=dest, capture_output=True, text=True)


def write(dest: Path, rel: str, text: str) -> None:
    (dest / rel).parent.mkdir(parents=True, exist_ok=True)
    (dest / rel).write_text(text)


def test_en_fails_on_russian_comment(project):
    dest = project()
    write(dest, "src/a.ts", f"// {RU}\n")

    result = run(dest, "check-comments", "src/a.ts")

    assert result.returncode == 1
    assert "src/a.ts:1: comment not in English; quote a UI string in «» or backticks" in result.stdout


def test_ru_fails_on_english_comment(project):
    dest = project(language="ru")
    write(dest, "src/a.ts", f"// {EN}\n")

    result = run(dest, "check-comments", "src/a.ts")

    assert result.returncode == 1
    assert "comment not in Russian; quote a UI string in «» or backticks" in result.stdout


def test_ru_passes_mixed_comment_block(project):
    dest = project(language="ru")
    write(dest, "src/a.ts", "// Конфигурация читается из TypeScript config files\n")

    assert run(dest, "check-comments", "src/a.ts").returncode == 0


def test_en_passes_quoted_russian_in_comment(project):
    dest = project()
    write(dest, "src/a.ts", f"// shows «{RU}» to the user\n")

    assert run(dest, "check-comments", "src/a.ts").returncode == 0


def test_en_fails_on_russian_paragraph(project):
    dest = project()
    write(dest, "README.md", f"# Demo\n\n{RU}.\n")

    result = run(dest, "check-md-language", "README.md")

    assert result.returncode == 1
    assert "README.md:3:" in result.stdout


TABLE_HEAD = "# Demo\n\n| Phrase | Key | Screens |\n|---|---|---|\n"


@pytest.mark.parametrize("row", [
    pytest.param(f"| `{RU}` | key | home |", id="first-column"),
    pytest.param(f"| home | key | `{RU}` |", id="third-column"),
])
def test_en_passes_backticked_table_cell(project, row):
    dest = project()
    write(dest, "README.md", f"{TABLE_HEAD}{row}\n")

    result = run(dest, "check-md-language", "README.md")

    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize("row", [
    pytest.param(f"| {RU} | key | home |", id="first-column"),
    pytest.param(f"| {RU} | `key` | home |", id="first-column-backticked-neighbour"),
    pytest.param(f"| `home` | {RU} | `key` |", id="second-column-between-backticks"),
    pytest.param(f"| home | `key` | {RU} |", id="third-column-backticked-neighbour"),
])
def test_en_fails_on_unquoted_table_cell(project, row):
    dest = project()
    write(dest, "README.md", f"{TABLE_HEAD}{row}\n")

    result = run(dest, "check-md-language", "README.md")

    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        "README.md:5: prose not in English; quote a UI string in «» or backticks"]


def test_ru_fails_on_english_paragraph(project):
    dest = project(language="ru")
    write(dest, "README.md", f"{EN}.\n")

    result = run(dest, "check-md-language", "README.md")

    assert result.returncode == 1
    assert "README.md:1:" in result.stdout


def test_markdown_code_is_not_prose(project):
    dest = project()
    write(dest, "README.md", f"```\n{RU}\n```\n\nUse `{RU}` here.\n\n<!-- {RU} -->\n\n[link](https://example.com/{RU.replace(' ', '/')})\n")

    assert run(dest, "check-md-language", "README.md").returncode == 0


def test_markdown_indented_code_and_front_matter_are_not_prose(project):
    dest = project()
    write(dest, "README.md", f"---\ntitle: {RU}\n---\n\nText:\n\n    {RU}\n")

    assert run(dest, "check-md-language", "README.md").returncode == 0


def test_markdown_directive_words_do_not_hide_prose(project):
    dest = project()
    write(dest, "README.md", f"Content type: {RU}.\n")

    assert run(dest, "check-md-language", "README.md").returncode == 1


def test_missing_language_key_is_en(project):
    dest = project()
    repo_yaml = dest / ".repo.yaml"
    repo_yaml.write_text("".join(line for line in repo_yaml.read_text().splitlines(True)
                                 if not line.startswith("language:")))
    write(dest, "src/a.ts", f"// {RU}\n")

    assert run(dest, "check-repo-yaml").returncode == 0
    assert "comment not in English" in run(dest, "check-comments", "src/a.ts").stdout


@pytest.mark.parametrize("rel", [".config/dependency-cruiser.cjs", ".mise/tasks/own-task.py", ".mise/conf.d/own.toml"])
def test_en_checks_project_files_in_standard_folders(project, rel):
    dest = project()
    write(dest, rel, f"# {RU}\n" if rel.endswith(("toml", "own-task.py")) else f"// {RU}\n")

    result = run(dest, "check-comments", rel)

    assert result.returncode == 1
    assert "comment not in English" in result.stdout


def test_ru_checks_project_files_in_standard_folders(project):
    dest = project(language="ru")
    write(dest, ".mise/tasks/own-task.py", f"# {EN}\n")

    assert run(dest, "check-comments", ".mise/tasks/own-task.py").returncode == 1


def test_ru_rendered_project_passes_language_checks(project):
    dest = project(language="ru")
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)

    assert run(dest, "check-md-language").returncode == 0
    assert run(dest, "check-comments").returncode == 0


@pytest.mark.parametrize("stack", [["typescript"], ["terraform"]])
def test_ru_rendered_stack_project_passes_language_checks(project, stack):
    dest = project(language="ru", stack=stack)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)

    assert run(dest, "check-md-language").returncode == 0
    assert run(dest, "check-comments").returncode == 0


def test_ru_deployed_project_passes_language_checks(project):
    dest = project(language="ru", deployed=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)

    assert run(dest, "check-md-language").returncode == 0


def test_markdown_decisions_are_skipped(project):
    dest = project()
    write(dest, "docs/decisions/9999-x.md", f"{RU}.\n")

    assert run(dest, "check-md-language").returncode == 0


@pytest.mark.parametrize("task", ["check-comments", "check-md-language"])
def test_auto_fails_and_names_repo_init(project, task):
    dest = project(language="auto")

    result = run(dest, task)

    assert result.returncode == 1
    assert "repo-init" in result.stdout


def seed(dest: Path, russian: int, total: int) -> None:
    for rendered in dest.rglob("*.md"):
        rendered.unlink()
    for number in range(total):
        text = RU if number < russian else EN
        write(dest, f"docs/note{number}.md", f"{text}.\n")


def detected(dest: Path) -> dict:
    result = run(dest, "detect-language")
    assert result.returncode == 0
    return json.loads(result.stdout)


def test_detect_language_majority_is_ru(project):
    dest = project()
    seed(dest, 9, 10)

    assert detected(dest)["language"] == "ru"


def test_detect_language_without_majority_is_null(project):
    dest = project()
    seed(dest, 6, 10)

    assert detected(dest)["language"] is None


@pytest.mark.parametrize("value", ["ru", "auto"])
def test_repo_yaml_accepts_language(project, value):
    dest = project(language=value)

    assert yaml.safe_load((dest / ".repo.yaml").read_text())["language"] == value
    assert run(dest, "check-repo-yaml").returncode == 0


def test_agents_text_rules_follow_language(render, tmp_path):
    texts = {value: (render(tmp_path / value, project_name="demo", language=value) / "AGENTS.md").read_text()
             for value in ("en", "ru", "auto")}

    assert "engineering texts in English" in texts["en"]
    assert "engineering texts of the project in Russian" in texts["ru"]
    assert "run `repo-init`" in texts["auto"]


@pytest.mark.parametrize("task", ["check-comments", "check-md-language", "detect-language"])
def test_tasks_leave_no_bytecode_cache(project, task):
    dest = project()

    run(dest, task)

    assert not list(dest.rglob("__pycache__"))


@pytest.mark.parametrize("rel, text", [
    ("src/a.ts", "// eslint-disable-next-line no-console -- Причина отключения правила здесь\n"),
    ("src/a.py", "# noqa: E501 Строка слишком длинная тут\n"),
    ("src/b.py", "# type: Повторить запрос позже\n"),
    ("src/b.ts", "// @ts-expect-error Ошибка типов библиотеки\n"),
])
def test_en_checks_reason_after_directive(project, rel, text):
    dest = project()
    write(dest, rel, text)

    result = run(dest, "check-comments", rel)

    assert result.returncode == 1
    assert f"{rel}:1: comment not in English" in result.stdout


@pytest.mark.parametrize("task", ["check-comments", "check-md-language"])
def test_unknown_language_fails_without_traceback(project, task):
    dest = project()
    repo_yaml = dest / ".repo.yaml"
    repo_yaml.write_text(repo_yaml.read_text().replace("language: en", "language: fr"))

    result = run(dest, task)

    assert result.returncode == 1
    assert "`fr`" in result.stdout
    assert "Traceback" not in result.stderr


def test_repo_yaml_argument_checks_all_documents(project):
    dest = project()
    write(dest, "docs/other.md", f"{RU}.\n")

    result = run(dest, "check-md-language", ".repo.yaml")

    assert result.returncode == 1
    assert "docs/other.md:1:" in result.stdout


def test_ru_passes_mixed_markdown_block(project):
    dest = project(language="ru")
    write(dest, "README.md", "Конфигурация читается из TypeScript config files.\n")

    assert run(dest, "check-md-language", "README.md").returncode == 0


@pytest.mark.parametrize("text", [
    "# Запуск 2026-01-01 сервера ночью\n",
    "# Слово https://x.y слово слово\n",
])
def test_en_cut_fragment_still_splits_cyrillic_words(project, text):
    dest = project()
    write(dest, "src/a.py", text)

    assert "not in English" not in run(dest, "check-comments", "src/a.py").stdout


def commit_all(dest: Path) -> None:
    subprocess.run(["git", "-C", str(dest), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(dest), "commit", "-qm", "chore: base"], check=True, capture_output=True)


def test_ru_with_manual_passes_language_checks(project):
    dest = project(language="ru", maintain_adapter="manual")
    commit_all(dest)

    for task in ("check-md-language", "check-comments"):
        result = run(dest, task)
        assert result.returncode == 0, task + result.stdout + result.stderr


def test_ru_rejects_english_own_adapter_readme(project):
    dest = project(language="ru", maintain_adapter="codex")
    write(dest, ".maintain/codex/README.md", "# Adapter for the codex agent\n\nThis folder holds the adapter and its entry point.\n")
    commit_all(dest)

    result = run(dest, "check-md-language")

    assert result.returncode == 1
    assert ".maintain/codex/README.md:1:" in result.stdout

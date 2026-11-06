import subprocess

import pytest

SCRIPT = ".mise/tasks/check-comments"


@pytest.fixture
def project(render, tmp_path, git_repo):
    dest = render(tmp_path, project_name="demo")
    git_repo(dest)
    return dest


def check(project_dir, rel, text, *args):
    path = project_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    result = subprocess.run(
        ["uv", "run", "--script", str(project_dir / SCRIPT), *(args or (rel,))],
        cwd=project_dir, capture_output=True, text=True,
    )
    return result.returncode, result.stdout


def test_todo_without_ref_fails(project):
    code, out = check(project, "src/a.ts", "const a = 1;\n// TODO retry\n")

    assert code == 1
    assert "src/a.ts:2:" in out


def test_todo_with_issue_passes(project):
    assert check(project, "src/a.ts", "// TODO(#12) retry\n") == (0, "")


def test_todo_with_tasks_passes(project):
    assert check(project, "src/a.py", "# TODO(docs/tasks.md) retry\n") == (0, "")


def test_eslint_disable_without_reason_fails(project):
    code, out = check(project, "src/a.ts", "// eslint-disable-next-line no-console\nconsole.log(1);\n")

    assert code == 1
    assert "src/a.ts:1:" in out


def test_eslint_disable_with_reason_passes(project):
    text = "// eslint-disable-next-line no-console -- CLI output\nconsole.log(1);\n"
    assert check(project, "src/a.ts", text) == (0, "")


def test_tflint_ignore_without_reason_fails(project):
    code, out = check(project, "infra/main.tf", "# tflint-ignore: terraform_unused_declarations\n")

    assert code == 1
    assert "infra/main.tf:1:" in out


def test_added_by_fails(project):
    code, out = check(project, "src/a.py", "# Added by Claude for the report\n")

    assert code == 1
    assert "src/a.py:1:" in out


def test_path_with_space_is_checked(project):
    code, out = check(project, "src dir/my file.ts", "/* TODO fix */\n")

    assert code == 1
    assert "src dir/my file.ts:1:" in out


def test_unrelated_extension_is_ignored(project):
    assert check(project, "notes.md", "// TODO fix\n# added by me\n") == (0, "")


@pytest.mark.parametrize("rel, text", [
    ("src/a.ts", 'const u = "http://x"; // TODO(#1) retry\n'),
    ("src/a.php", "<?php\n#[Attribute]\nclass A {}\n"),
    ("bin/run.sh", "#!/usr/bin/env bash\necho hi\n"),
    ("src/a.py", 'x = "a # TODO"\n'),
    ("src/a.php", "<?php\n$x = f(); // @phpstan-ignore argument.type (legacy API)\n"),
])
def test_no_false_positive(project, rel, text):
    assert check(project, rel, text) == (0, "")


def test_phpstan_ignore_without_reason_fails(project):
    code, out = check(project, "src/a.php", "<?php\n$x = f(); // @phpstan-ignore argument.type\n")

    assert code == 1
    assert "src/a.php:2:" in out


def test_python_docstring_todo_is_not_a_comment(project):
    text = 'def f():\n    """Notes.\n\n    # TODO fix\n    """\n'
    assert check(project, "src/a.py", text) == (0, "")


def test_python_real_todo_comment_reports_its_line(project):
    code, out = check(project, "src/a.py", 'x = """\nq\n"""\n# TODO fix\n')

    assert code == 1
    assert "src/a.py:4:" in out


def test_python_string_todo_is_not_a_comment(project):
    assert check(project, "src/a.py", 'x = "# TODO"\ny = \'# TODO\'\n') == (0, "")


def test_python_untokenizable_file_uses_line_fallback(project):
    code, out = check(project, "src/a.py", 'x = (\n# TODO fix\n')

    assert code == 1
    assert "src/a.py:2:" in out

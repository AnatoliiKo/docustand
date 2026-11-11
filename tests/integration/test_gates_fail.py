"""Integration tests: every gate of a rendered project fails on one violation.

Needs mise on PATH and network on the first run (tools land in the shared mise
install directory, so later runs reuse them). One rendered, installed and
committed base project is built per session; each test works on a copy.
"""

import json
import os
import re
import shutil
import subprocess
import time
import tomllib
from pathlib import Path

import pytest

from conftest import init_git_repo, run_copier

pytestmark = pytest.mark.integration

PRE_COMMIT_BUDGET_S = 5.0

MAIN_TF = """\
terraform {
  required_version = ">= 1.5.0"
}

variable "name" {
  type        = string
  description = "Name stored in the resource."
  default     = "example"
}

resource "terraform_data" "this" {
  input = var.name
}

output "id" {
  description = "Identifier of the resource."
  value       = terraform_data.this.id
}
"""

# AWS key pair from the Betterleaks rule samples; the access key ID is reported
# only together with its secret (composite rule since Betterleaks 1.2.0).
AWS_KEYS = "".join(
    [
        "aws_access_key_id = ",
        "AKIALALE",
        "MEL33243OLIA\n",
        "aws_secret_access_key = ",
        "Tg0pz8Jii8hk",
        "Lx4+P",
        "nUisM8Gm",
        "Ks3a2DK+9qz/lie\n",
    ]
)


def mise_env(trusted: Path) -> dict[str, str]:
    """Environment for mise in a tmp project: trusted without `mise trust`, no
    leftovers of the outer `mise run test` or `uv run`."""
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("MISE_", "__MISE", "UV_", "HK_")) and k != "VIRTUAL_ENV"
    }
    env.update(MISE_TRUSTED_CONFIG_PATHS=str(trusted), MISE_YES="1")
    return env


def sh(cwd: Path, env: dict, *cmd: str, check: bool = False) -> subprocess.CompletedProcess:
    result = subprocess.run(
        cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
    )
    if check and result.returncode != 0:
        pytest.fail(f"{' '.join(cmd)} failed ({result.returncode}):\n{result.stdout}\n{result.stderr}")
    return result


@pytest.fixture(scope="session")
def base(tmp_path_factory):
    root = tmp_path_factory.getbasetemp()
    env = mise_env(root)
    dest = tmp_path_factory.mktemp("base") / "project"
    rendered = run_copier(dest, project_name="demo", stack=["terraform"])
    if rendered.returncode != 0:
        pytest.fail(f"copier failed:\n{rendered.stderr}")
    init_git_repo(dest)
    (dest / "main.tf").write_text(MAIN_TF)
    sh(dest, env, "mise", "install", check=True)
    sh(dest, env, "git", "add", "-A", check=True)
    sh(dest, env, "git", "commit", "-m", "chore: add project files", check=True)
    return dest, env


@pytest.fixture
def project(base, tmp_path):
    src, env = base
    dest = tmp_path / "project"
    shutil.copytree(src, dest, symlinks=True)
    return dest, env


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def check(project) -> subprocess.CompletedProcess:
    root, env = project
    sh(root, env, "git", "add", "-A", check=True)
    return sh(root, env, "mise", "run", "check")


def failed_steps(result: subprocess.CompletedProcess) -> set[str]:
    """Names of the steps hk marks as failed (`✗ <step>` lines)."""
    return set(re.findall(r"^✗ ([\w-]+)", result.stdout + result.stderr, re.M))


def assert_step_fails(result: subprocess.CompletedProcess, step: str) -> None:
    out = result.stdout + result.stderr
    assert result.returncode == 1, f"exit {result.returncode}\n{out}"
    assert step in failed_steps(result), f"step {step!r} did not fail:\n{out}"


def commit(project, message: str) -> subprocess.CompletedProcess:
    root, env = project
    return sh(root, env, "git", "commit", "--allow-empty", "-m", message)


def test_clean_project_passes(project):
    result = check(project)

    assert result.returncode == 0, result.stdout + result.stderr


def test_fails_on_secret(project):
    write(project[0], "notes.txt", AWS_KEYS)

    assert_step_fails(check(project), "betterleaks")


def test_betterleaks_ignore_keeps_known_findings_only(project):
    root, env = project
    write(root, "notes.txt", AWS_KEYS)
    report = root.parent / "leaks.json"
    sh(root, env, "mise", "x", "--", "betterleaks", "dir", "--no-banner", "--report-format", "json",
       "--report-path", str(report), "notes.txt")
    fingerprints = [item["Fingerprint"] for item in json.loads(report.read_text())]
    assert fingerprints
    write(root, ".betterleaksignore", "".join(f"{f}\n" for f in fingerprints))

    assert "betterleaks" not in failed_steps(check(project))
    write(root, "more.txt", AWS_KEYS)
    assert_step_fails(check(project), "betterleaks")


def test_fails_on_typo(project):
    root = project[0]
    write(root, "README.md", (root / "README.md").read_text() + "\nThis is te" + "h setup.\n")

    assert_step_fails(check(project), "typos")


def test_fails_on_md_lint(project):
    write(project[0], "docs/architecture.md", "# One\n\nText.\n\n# Two\n\nText.\n")

    assert_step_fails(check(project), "rumdl")


def test_fails_on_md_placement(project):
    write(project[0], "notes/a.md", "# Notes\n\nText.\n")

    assert_step_fails(check(project), "check-md-placement")


def test_fails_on_root_file(project):
    root, env = project
    write(root, "notes.txt", "draft\n")
    sh(root, env, "git", "add", "notes.txt", check=True)

    assert_step_fails(check(project), "check-root")


def test_fails_on_adr_without_sections(project):
    write(project[0], "docs/decisions/0001-use-x.md", "# 0001. Use X\n\nStatus: accepted\n\n## Context\n\n- c\n")

    assert_step_fails(check(project), "check-adr")


def test_fails_on_date_in_comment(project):
    write(project[0], "scripts/run.sh", "#!/bin/sh\n# Changed on 2026-01-31.\necho ok\n")

    assert_step_fails(check(project), "check-comments")


def test_fails_on_conflict_markers(project):
    # Markers a conflicting `copier update` leaves in a Markdown file.
    write(project[0], "docs/notes.md", "# Notes\n\n<<<<<<< before updating\nold\n=======\nnew\n>>>>>>> after updating\n")

    assert_step_fails(check(project), "check-merge-conflict")


def test_fails_on_tf_fmt(project):
    root = project[0]
    write(root, "main.tf", MAIN_TF.replace("input = var.name", "input    =    var.name"))

    assert_step_fails(check(project), "terraform-fmt")


def test_fails_on_tflint(project):
    root = project[0]
    unused = '\nvariable "unused" {\n  type        = string\n  description = "Unused."\n}\n'
    write(root, "main.tf", MAIN_TF + unused)

    assert_step_fails(check(project), "tflint")


def test_fails_on_tf_validate(project):
    root = project[0]
    missing = '\noutput "missing" {\n  description = "Broken reference."\n  value       = terraform_data.missing.id\n}\n'
    write(root, "main.tf", MAIN_TF + missing)

    assert_step_fails(check(project), "tf-validate")


def test_fails_on_dead_link(project):
    root = project[0]
    write(root, "README.md", (root / "README.md").read_text() + "\nSee [missing](docs/missing.md).\n")

    assert_step_fails(check(project), "lychee")


def test_commit_msg_rejects_claude_trailer(project):
    result = commit(project, "feat: add module\n\nCo-Authored-By: Claude <noreply@anthropic.com>")

    assert result.returncode != 0
    assert "trailer-no-claude" in result.stdout + result.stderr


@pytest.mark.parametrize("trailer", [
    "Reviewed-by: Claude",
    "co-authored-by: Bot <noreply@anthropic.com>",
])
def test_commit_msg_rejects_any_claude_trailer(project, trailer):
    result = commit(project, f"feat: add module\n\n{trailer}")

    assert result.returncode != 0
    assert "trailer-no-claude" in result.stdout + result.stderr


def test_commit_msg_rejects_session_trailer(project):
    result = commit(project, "feat: add module\n\nClaude-Session: https://claude.ai/code/session_x")

    assert result.returncode != 0
    assert "trailer-no-claude" in result.stdout + result.stderr


def test_commit_msg_rejects_generated_with_line(project):
    result = commit(project, "feat: add module\n\nGenerated with Claude Code")

    assert result.returncode != 0
    assert "body-no-generated-with" in result.stdout + result.stderr


def test_commit_msg_rejects_long_header(project):
    header = "feat: " + "x" * 67
    assert len(header) == 73

    result = commit(project, header)

    assert result.returncode != 0
    assert "header-max-length" in result.stdout + result.stderr
    assert commit(project, header[:72]).returncode == 0


def test_commit_msg_rejects_non_conventional_header(project):
    result = commit(project, "Add module")

    assert result.returncode != 0
    assert "type-empty" in result.stdout + result.stderr


def test_commit_msg_rejects_hand_written_merge_header(project):
    header = "Merge anything " + "x" * 60
    assert len(header) > 72

    result = commit(project, header)

    assert result.returncode != 0
    assert "header-max-length" in result.stdout + result.stderr


def test_commit_msg_rejects_fixup(project):
    result = commit(project, "fixup! x")

    assert result.returncode != 0
    assert "type-empty" in result.stdout + result.stderr


def test_commit_msg_allows_real_merge(project):
    root, env = project
    sh(root, env, "git", "switch", "-c", "feature", check=True)
    assert commit(project, "docs: add note").returncode == 0
    sh(root, env, "git", "switch", "main", check=True)

    result = sh(root, env, "git", "merge", "--no-ff", "--no-edit", "feature")

    assert result.returncode == 0, result.stdout + result.stderr
    subject = sh(root, env, "git", "log", "-1", "--format=%s", check=True).stdout.strip()
    assert subject == "Merge branch 'feature'"


def test_commit_msg_allows_real_revert(project):
    root, env = project
    long_subject = "docs: " + "y" * 66
    write(root, "README.md", (root / "README.md").read_text() + "\nOne more line.\n")
    sh(root, env, "git", "add", "README.md", check=True)
    assert commit(project, long_subject).returncode == 0

    result = sh(root, env, "git", "revert", "--no-edit", "HEAD")

    assert result.returncode == 0, result.stdout + result.stderr


def test_commit_msg_rejects_revert_header_without_git_body(project):
    result = commit(project, 'Revert "' + "z" * 70 + '"')

    assert result.returncode != 0


@pytest.mark.parametrize("reason", ["vendor file", "vendor file from claude.ai docs"])
def test_commit_msg_allows_skip_check_trailer(project, reason):
    result = commit(project, f"fix: vendor file\n\nSkip-Check: typos — {reason}")

    assert result.returncode == 0, result.stdout + result.stderr


def test_commit_msg_allows_claude_in_subject(project):
    result = commit(project, "docs: explain Claude Code hooks\n\nClaude Code reads AGENTS.md.")

    assert result.returncode == 0, result.stdout + result.stderr


def test_project_without_mise_toml_works(project):
    root, env = project
    assert not (root / "mise.toml").exists()
    assert not (root / ".mise.toml").exists()
    pinned = tomllib.loads((root / ".mise/conf.d/standard.toml").read_text())["tools"]["node"]

    tasks = sh(root, env, "mise", "tasks", "ls", check=True).stdout
    node = sh(root, env, "mise", "which", "node", check=True).stdout.strip()
    data_dir = sh(root, env, "mise", "dirs", "data", check=False).stdout.strip() or str(
        Path.home() / ".local/share/mise")

    assert re.search(r"^check\b", tasks, re.M), tasks
    assert re.search(r"^pr-ready\b", tasks, re.M), tasks
    assert Path(node).resolve().is_relative_to(Path(data_dir).resolve() / "installs"), node
    assert f"/node/{pinned}/" in node, node


def test_hooks_are_installed_by_mise_install(project):
    """hk writes shims to the hooks directory, or on Git 2.54+ the local config
    entries `hook.hk-<event>.event` (hk `src/cli/install.rs`)."""
    root, env = project
    hooks = sh(root, env, "git", "rev-parse", "--git-path", "hooks", check=True).stdout.strip()
    config = sh(root, env, "git", "config", "--local", "--get-regexp", r"^hook\.hk-.*\.event$").stdout
    events = {line.split(maxsplit=1)[1].strip() for line in config.splitlines() if " " in line}
    for name in ("pre-commit", "commit-msg", "pre-push"):
        assert (root / hooks / name).exists() or name in events, name


def test_pr_ready_records_head(project):
    root, env = project

    sh(root, env, "mise", "run", "pr-ready", check=True)

    head = sh(root, env, "git", "rev-parse", "HEAD", check=True).stdout.strip()
    marker = sh(root, env, "git", "rev-parse", "--git-path", "pr-ready", check=True).stdout.strip()
    assert (root / marker).read_text().strip() == head


def test_pr_ready_refuses_dirty_tree(project):
    root, env = project
    write(root, "docs/extra.md", "# Extra\n\nText.\n")

    result = sh(root, env, "mise", "run", "pr-ready")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "uncommitted changes" in result.stdout + result.stderr
    marker = sh(root, env, "git", "rev-parse", "--git-path", "pr-ready", check=True).stdout.strip()
    assert not (root / marker).exists()


def test_pre_commit_budget(project):
    root, env = project
    write(root, "README.md", (root / "README.md").read_text() + "\nOne more line.\n")
    sh(root, env, "git", "add", "README.md", check=True)
    sh(root, env, "mise", "x", "--", "hk", "run", "pre-commit", check=True)

    start = time.monotonic()
    sh(root, env, "mise", "x", "--", "hk", "run", "pre-commit", check=True)
    elapsed = time.monotonic() - start
    print(f"pre-commit on one changed file: {elapsed:.2f} s")

    assert elapsed <= PRE_COMMIT_BUDGET_S, f"pre-commit took {elapsed:.2f} s (budget {PRE_COMMIT_BUDGET_S} s)"


def test_path_with_space(project):
    write(project[0], "docs/my notes.md", "# My notes\n\nThis is te" + "h plan.\n")

    result = check(project)

    assert_step_fails(result, "typos")
    assert failed_steps(result) == {"typos"}, result.stdout + result.stderr
    assert "docs/my notes.md" in result.stdout + result.stderr


def test_project_without_stack_passes(tmp_path_factory):
    env = mise_env(tmp_path_factory.getbasetemp())
    dest = tmp_path_factory.mktemp("plain") / "project"
    rendered = run_copier(dest, project_name="demo")
    assert rendered.returncode == 0, rendered.stderr
    init_git_repo(dest)
    sh(dest, env, "mise", "install", check=True)
    sh(dest, env, "git", "add", "-A", check=True)

    result = sh(dest, env, "mise", "run", "check")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "tflint" not in result.stdout + result.stderr

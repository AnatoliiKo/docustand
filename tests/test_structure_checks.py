import os
import subprocess

import pytest

TASKS_DIR = ".mise/tasks"
SCRIPTS = [
    "check-md-placement", "check-agents-md", "check-tasks-format",
    "check-repo-yaml", "check-env-example", "check-gitignore-block",
]
VERBS = (
    "Add Fix Remove Move Update Create Replace Rename Migrate Document Enable "
    "Disable Split Merge Investigate Implement Refactor Configure Upgrade Deploy "
    "Set Write Test Review Clean Improve Support"
).split()

TASK = """## In progress
### {heading}
- Goal: alert when processing stops.
{done}- Stopped at: metric is published.
- Next: alarm definition.
- Refs: PR #96.

## Backlog
{backlog}
"""
DONE = "- Done when: the alarm fires in staging.\n"


@pytest.fixture
def project(render, tmp_path, git_repo):
    def _project(**data):
        dest = render(tmp_path, project_name="demo", **data)
        git_repo(dest)
        return dest

    return _project


def run(project_dir, script, *args):
    result = subprocess.run(
        ["uv", "run", "--script", str(project_dir / TASKS_DIR / script), *args],
        cwd=project_dir, capture_output=True, text=True,
    )
    return result.returncode, result.stdout


def write(project_dir, rel, text):
    path = project_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_scripts_are_executable_after_render(project):
    dest = project()

    for name in SCRIPTS:
        assert os.access(dest / TASKS_DIR / name, os.X_OK), name


def test_rendered_project_is_clean(project):
    dest = project()

    for name in ["check-md-placement", "check-agents-md", "check-tasks-format",
                 "check-repo-yaml", "check-gitignore-block"]:
        code, out = run(dest, name)
        assert code == 0, (name, out)


def test_md_outside_structure_fails(project):
    dest = project()
    write(dest, "notes/todo.md", "x\n")

    code, out = run(dest, "check-md-placement")

    assert code == 1
    assert "notes/todo.md" in out


def test_md_exception_allows(project):
    dest = project(md_exceptions=["notes/todo.md"])
    write(dest, "notes/todo.md", "x\n")

    code, out = run(dest, "check-md-placement")

    assert code == 0, out


def test_md_exception_glob_spans_directories(project):
    dest = project(md_exceptions=["vendor/**/*.md"])
    write(dest, "vendor/a/b/readme.md", "x\n")
    write(dest, "other/readme.md", "x\n")

    code, out = run(dest, "check-md-placement")

    assert code == 1
    assert "other/readme.md" in out
    assert "vendor" not in out


def test_md_path_with_space(project):
    dest = project()
    write(dest, "docs/my notes.md", "x\n")
    assert run(dest, "check-md-placement")[0] == 0

    write(dest, "src/my notes.md", "x\n")
    code, out = run(dest, "check-md-placement")

    assert code == 1
    assert "src/my notes.md" in out


def test_md_adr_name_pattern(project):
    dest = project()
    write(dest, "docs/decisions/0001-use-queue.md", "x\n")
    assert run(dest, "check-md-placement")[0] == 0

    write(dest, "docs/decisions/1-Use_Queue.md", "x\n")
    write(dest, "docs/decisions/notes.md", "x\n")
    code, out = run(dest, "check-md-placement")

    assert code == 1
    assert "1-Use_Queue.md" in out
    assert "decisions/notes.md" in out


def test_md_allowed_locations(project):
    dest = project()
    for rel in ["CHANGELOG.md", "docs/runbooks/a/b.md", "openspec/specs/x/spec.md",
                ".github/pull_request_template.md", ".claude/commands/x/y.md",
                ".claude/skills/s/SKILL.md", "docs/guide.md"]:
        write(dest, rel, "x\n")

    code, out = run(dest, "check-md-placement")

    assert code == 0, out


def test_md_nested_docs_and_args(project):
    dest = project()
    write(dest, "docs/sub/a.md", "x\n")
    write(dest, "ok/b.md", "x\n")

    code, out = run(dest, "check-md-placement", "ok/b.md")
    assert code == 1 and "ok/b.md" in out and "docs/sub/a.md" not in out

    code, out = run(dest, "check-md-placement")
    assert "docs/sub/a.md" in out


def test_agents_md_151_lines_fails(project):
    dest = project()
    write(dest, "AGENTS.md", "line\n" * 151)

    code, out = run(dest, "check-agents-md")

    assert code == 1
    assert "AGENTS.md" in out


def test_agents_md_150_lines_passes(project):
    dest = project()
    write(dest, "AGENTS.md", "line\n" * 150)

    code, out = run(dest, "check-agents-md")

    assert code == 0, out


def tasks_text(heading="Add queue heartbeat alert (api, infra)", done=DONE,
               backlog="- Move media transcoding off the API host — transcoding starves API requests."):
    return TASK.format(heading=heading, done=done, backlog=backlog)


def test_tasks_template_passes(project):
    dest = project()

    code, out = run(dest, "check-tasks-format")

    assert code == 0, out


def test_tasks_valid_with_system_passes(project):
    dest = project(system={"center": "infrastructure"})
    write(dest, "docs/tasks.md", tasks_text())

    code, out = run(dest, "check-tasks-format")

    assert code == 0, out


def test_tasks_parentheses_require_system(project):
    dest = project()
    write(dest, "docs/tasks.md", tasks_text())

    code, out = run(dest, "check-tasks-format")

    assert code == 1
    assert "docs/tasks.md:2:" in out


def test_tasks_missing_done_when_fails(project):
    dest = project(system={"center": "x"})
    write(dest, "docs/tasks.md", tasks_text(done=""))

    code, out = run(dest, "check-tasks-format")

    assert code == 1
    assert "Done when" in out


def test_tasks_backlog_without_reason_fails(project):
    dest = project(system={"center": "x"})
    write(dest, "docs/tasks.md", tasks_text(backlog="- Move media transcoding off the API host"))

    code, out = run(dest, "check-tasks-format")

    assert code == 1
    assert "docs/tasks.md:10:" in out


def test_tasks_heading_not_verb_fails(project):
    dest = project(system={"center": "x"})
    write(dest, "docs/tasks.md", tasks_text(heading="Queue heartbeat alert (api)"))

    code, out = run(dest, "check-tasks-format")

    assert code == 1
    assert "Queue" in out


def test_tasks_missing_section_fails(project):
    dest = project()
    write(dest, "docs/tasks.md", "## In progress\n")

    code, out = run(dest, "check-tasks-format")

    assert code == 1
    assert "Backlog" in out


def test_task_verbs_data_file_content(project):
    dest = project()

    text = (dest / ".mise/data/task-verbs.txt").read_text()

    assert text.split("\n") == VERBS + [""]


def test_task_verbs_from_data_file(project):
    dest = project()
    write(dest, "docs/tasks.md", tasks_text(heading="Refactor queue worker", backlog=""))
    assert run(dest, "check-tasks-format")[0] == 0

    write(dest, "docs/tasks.md", tasks_text(heading="Queue worker refactor", backlog=""))
    code, out = run(dest, "check-tasks-format")

    assert code == 1
    assert "Queue" in out


def test_repo_yaml_unknown_key_fails(project):
    dest = project()
    with open(dest / ".repo.yaml", "a") as f:
        f.write("surprise: 1\n")

    code, out = run(dest, "check-repo-yaml")

    assert code == 1
    assert ".repo.yaml:" in out
    assert "surprise" in out


def test_repo_yaml_bad_value_fails(project):
    dest = project()
    text = (dest / ".repo.yaml").read_text().replace("level: base", "level: huge")
    (dest / ".repo.yaml").write_text(text)

    code, out = run(dest, "check-repo-yaml")

    assert code == 1
    assert "level" in out


def test_gitignore_block_missing_line_fails(project):
    dest = project()
    path = dest / ".gitignore"
    path.write_text(path.read_text().replace("!.claude/hooks/\n", ""))

    code, out = run(dest, "check-gitignore-block")

    assert code == 1
    assert "!.claude/hooks/" in out


def test_gitignore_block_inside_foreign_rules_passes(project):
    dest = project()
    write(dest, ".gitignore", "node_modules/\n" + (dest / ".gitignore").read_text() + "*.log\n")

    code, out = run(dest, "check-gitignore-block")

    assert code == 0, out


def test_env_example_missing_var_fails(project):
    dest = project()
    write(dest, "src/app.ts", "const a = process.env.API_URL;\n")
    write(dest, ".env.example", "OTHER=1\n")

    code, out = run(dest, "check-env-example", "--stack", "nextjs")

    assert code == 1
    assert "API_URL" in out
    assert "src/app.ts:1:" in out


def test_env_example_declared_passes(project):
    dest = project()
    write(dest, "src/app.ts", "const a = process.env.API_URL;\n")
    write(dest, ".env.example", "API_URL=\n")

    code, out = run(dest, "check-env-example", "--stack", "nextjs")

    assert code == 0, out


def test_env_example_missing_file_fails(project):
    dest = project()
    write(dest, "app/Foo.php", "<?php $a = env('DB_HOST');\n")

    code, out = run(dest, "check-env-example", "--stack", "laravel")

    assert code == 1
    assert ".env.example" in out and "DB_HOST" in out


def test_env_example_expo_from_repo_yaml_flag_replaces(project):
    dest = project()
    write(dest, "App.tsx", "x(process.env.EXPO_PUBLIC_API, process.env.OTHER)\n")
    write(dest, ".env.example", "")

    code, out = run(dest, "check-env-example", "--stack", "expo")

    assert code == 1
    assert "EXPO_PUBLIC_API" in out
    assert "OTHER" not in out


def test_env_example_no_pattern_skips(project):
    dest = project(stack=["terraform"])

    code, out = run(dest, "check-env-example")

    assert code == 0
    assert "no env pattern for stack, skipped" in out


def test_env_example_builtin_vars_ignored(project):
    dest = project()
    write(dest, "src/app.ts", "x(process.env.NODE_ENV, process.env.NEXT_RUNTIME)\n")

    code, out = run(dest, "check-env-example", "--stack", "nextjs")

    assert code == 0, out


def test_md_extension_case_insensitive(project):
    dest = project()
    write(dest, "notes/NOTES.MD", "x\n")

    code, out = run(dest, "check-md-placement")

    assert code == 1
    assert "notes/NOTES.MD" in out


def test_path_outside_repo_is_skipped(project, tmp_path):
    dest = project()
    outside = tmp_path / "outside.md"
    outside.write_text("x\n")

    for script in ["check-md-placement", "check-agents-md", "check-tasks-format",
                   "check-repo-yaml", "check-gitignore-block", "check-env-example"]:
        code, out = run(dest, script, "--stack", "nextjs", str(outside)) \
            if script == "check-env-example" else run(dest, script, str(outside))
        assert code == 0, (script, out)


def test_gitignore_negation_before_block_fails(project):
    dest = project()
    write(dest, ".gitignore", "!.claude/hooks/\n" + (dest / ".gitignore").read_text())

    code, out = run(dest, "check-gitignore-block")

    assert code == 1
    assert ".gitignore:1:" in out and "after `.claude/*`" in out


def test_tasks_backlog_repos_with_system_passes(project):
    dest = project(system={"center": "x"})
    write(dest, "docs/tasks.md",
          "## In progress\n\n## Backlog\n- Move media transcoding off the API host (api) — it starves requests.\n")

    code, out = run(dest, "check-tasks-format")

    assert code == 0, out


def test_tasks_backlog_repos_without_system_fails(project):
    dest = project()
    write(dest, "docs/tasks.md",
          "## In progress\n\n## Backlog\n- Move media transcoding off the API host (api) — it starves requests.\n")

    code, out = run(dest, "check-tasks-format")

    assert code == 1
    assert "docs/tasks.md:4:" in out

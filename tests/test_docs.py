import re
import subprocess

from conftest import run_copier

GITIGNORE_BLOCK = """docs/temp/
CLAUDE.local.md
.claude/*
!.claude/settings.json
!.claude/skills/
!.claude/commands/
!.claude/hooks/
"""

SECTIONS = [
    "Structure", "Stack", "Architecture", "Working rules", "Text rules",
    "Before a PR", "Comments", "Use existing solutions first",
]
NO_TRAILERS = (
    'Commit messages and PR descriptions contain no Co-Authored-By, '
    'Claude-Session or "Generated with" lines.'
)
SCHEDULE_NOTE = "disables scheduled workflows after 60 days without activity"
ENABLE_CMD = "gh workflow enable standard-report.yml"


def test_claude_md_is_one_line(render, tmp_path):
    dest = render(tmp_path, project_name="demo")

    assert (dest / "CLAUDE.md").read_text() == "@AGENTS.md\n"


def test_agents_md_limit(render, tmp_path):
    dest = render(tmp_path, project_name="demo")
    text = (dest / "AGENTS.md").read_text()

    assert len(text.splitlines()) <= 150
    headings = re.findall(r"^#+\s+(.+?)\s*$", text, re.M)
    for section in SECTIONS:
        assert section in headings, section
    before_pr = text.split("## Before a PR", 1)[1].split("\n## ", 1)[0]
    assert "mise run check" in before_pr
    assert "mise run pr-ready" in before_pr
    assert NO_TRAILERS in text


def test_docustand_mentions(render, tmp_path):
    dest = render(tmp_path, project_name="demo")

    found = subprocess.run(
        ["grep", "-rn", "docustand", "--exclude-dir=decisions", "--exclude-dir=.git", "."],
        cwd=dest, capture_output=True, text=True,
    ).stdout.splitlines()
    allowed = (".repo.yaml", ".claude/settings.json")
    stray = [
        line for line in found
        if not line.split(":", 1)[0].removeprefix("./") in allowed
        and not line.split(":", 1)[0].removeprefix("./") == "AGENTS.md"
    ]
    assert stray == []
    agents = [line for line in found if line.startswith("./AGENTS.md:")]
    assert len(agents) == 1
    assert "If docustand is installed: /docustand:pr-ready." in agents[0]


def test_gitignore_block(render, tmp_path):
    dest = render(tmp_path, project_name="demo")
    assert GITIGNORE_BLOCK in (dest / ".gitignore").read_text()

    tf = render(tmp_path / "tf", project_name="demo", stack=["terraform"])
    lines = (tf / ".gitignore").read_text().splitlines()
    assert GITIGNORE_BLOCK in (tf / ".gitignore").read_text()
    assert ".terraform/" in lines
    assert "*.tfstate*" in lines


def test_worktreeinclude(render, tmp_path):
    dest = render(tmp_path, project_name="demo")

    assert (dest / ".worktreeinclude").read_text() == "CLAUDE.local.md\n"


def test_skip_if_exists(render, tmp_path):
    dest = render(tmp_path, project_name="demo")
    readme = dest / "README.md"
    readme.write_text("custom\n")

    result = run_copier(dest, project_name="demo", overwrite=True)

    assert result.returncode == 0, result.stderr
    assert readme.read_text() == "custom\n"


def test_standard_adr_is_0000(render, tmp_path):
    dest = render(tmp_path, project_name="demo")

    adrs = sorted(p.name for p in (dest / "docs" / "decisions").glob("*.md"))
    assert adrs == ["0000-adopt-repository-standard.md"]


def test_scheduled_workflow_note(render, tmp_path):
    dest = render(tmp_path, project_name="demo", deployed=True)

    readme = (dest / "README.md").read_text()
    maintenance = readme.split("## Maintenance", 1)[1]
    ops = (dest / "docs" / "operations.md").read_text()
    for text in (maintenance, ops):
        assert SCHEDULE_NOTE in text
        assert ENABLE_CMD in text


def test_operations_survives_recopy(render, tmp_path):
    dest = render(tmp_path, project_name="demo", deployed=True)
    ops = dest / "docs" / "operations.md"
    ops.write_text("custom\n")

    result = run_copier(dest, project_name="demo", deployed=True, overwrite=True)

    assert result.returncode == 0, result.stderr
    assert ops.read_text() == "custom\n"


def test_no_operations_when_not_deployed(render, tmp_path):
    dest = render(tmp_path, project_name="demo")

    assert not (dest / "docs" / "operations.md").exists()


def test_no_schedule_note_when_reports_off(render, tmp_path):
    dest = render(tmp_path, project_name="demo", report_schedule="off", deployed=True)

    for path in (dest / "README.md", dest / "docs" / "operations.md"):
        text = path.read_text()
        assert SCHEDULE_NOTE not in text
        assert ENABLE_CMD not in text


def test_update_command_is_consistent(render, tmp_path):
    dest = render(tmp_path, project_name="demo", report_schedule="off")
    command = "copier update -a .repo.yaml --defaults --data <key>=<value>"

    assert command in (dest / "AGENTS.md").read_text()
    readme = (dest / "README.md").read_text()
    assert "copier update" not in readme
    assert "changing the `report_schedule` answer in `.repo.yaml` as `AGENTS.md` describes" in readme


def test_no_blank_line_defects(render, tmp_path):
    for name, data in (("a", {}), ("b", {"stack": ["terraform"], "deployed": True,
                                         "architecture": {"backend": "layers"}})):
        dest = render(tmp_path / name, project_name="demo", **data)
        for path in dest.rglob("*.md"):
            text = path.read_text()
            assert "\n\n\n" not in text, path
            assert not text.endswith("\n\n"), path
        gitignore = (dest / ".gitignore").read_text()
        assert "\n\n" not in gitignore and gitignore.endswith("\n")


REPORT_APP_ROW = "| Report GitHub App: Contents read and write, Pull requests read and write, Administration read |"
CLAUDE_TASK_ROW = "| Scheduled Claude task for reports |"


def test_access_lists_report_app_at_base_level(render, tmp_path):
    text = (render(tmp_path, project_name="demo") / "docs" / "access.md").read_text()

    assert REPORT_APP_ROW in text
    assert "`REPORT_APP_ID`, `REPORT_APP_PRIVATE_KEY`" in text
    assert "| Renovate GitHub App on the repository | | GitHub App settings | never |" in text
    # The scheduled Claude task writes LLM reports, a full-level feature.
    assert CLAUDE_TASK_ROW not in text


def test_access_has_no_report_rows_when_reports_off(render, tmp_path):
    text = (render(tmp_path, project_name="demo", report_schedule="off") / "docs" / "access.md").read_text()

    assert REPORT_APP_ROW not in text
    assert CLAUDE_TASK_ROW not in text

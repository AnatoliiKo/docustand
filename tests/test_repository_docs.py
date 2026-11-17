import re
import subprocess

from conftest import REPO_ROOT


def run_check(name: str) -> subprocess.CompletedProcess:
    return subprocess.run(["uv", "run", "--quiet", "--script", f".mise/tasks/{name}"], cwd=REPO_ROOT,
                          capture_output=True, text=True)


def test_tasks_list_passes_format_and_paths_checks():
    for name in ("check-tasks-format", "check-doc-paths"):
        result = run_check(name)
        assert result.returncode == 0, result.stdout + result.stderr


def test_pilot_log_rows_have_six_columns_and_a_date():
    lines = (REPO_ROOT / "docs" / "pilot-log.md").read_text().splitlines()
    header = next(line for line in lines if line.startswith("| Date "))
    columns = header.count("|") - 1
    rows = [line for line in lines if line.startswith("| 20")]
    assert rows
    for row in rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split(" | ")]
        assert len(cells) == columns, row
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]), row


def adr_files() -> list:
    return sorted((REPO_ROOT / "docs" / "decisions").glob("[0-9][0-9][0-9][0-9]-*.md"))


def test_adr_numbers_are_unique():
    numbers = [path.name[:4] for path in adr_files()]
    assert len(numbers) == len(set(numbers))


def test_adr_references_exist():
    existing = {path.name[:4] for path in adr_files()}
    documents = [REPO_ROOT / "docs" / "tasks.md", *adr_files()]
    for document in documents:
        for number in re.findall(r"ADR (\d{4})", document.read_text()):
            assert number in existing, f"{document.name}: ADR {number}"

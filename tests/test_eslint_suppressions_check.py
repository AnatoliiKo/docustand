import json
import subprocess
from datetime import date, timedelta

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "template" / ".mise" / "tasks" / "check-eslint-suppressions"
BASELINE = ".baselines/eslint-suppressions.json"


def ahead(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def run(root, *args):
    result = subprocess.run(["uv", "run", "--quiet", "--script", str(SCRIPT), *args], cwd=root,
                            capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def write(root, data) -> None:
    (root / ".baselines").mkdir(exist_ok=True)
    (root / BASELINE).write_text(json.dumps(data))


def test_without_the_file_passes(tmp_path):
    assert run(tmp_path) == (0, "")


def test_dated_entries_pass(tmp_path):
    write(tmp_path, {"src/a.ts": {"complexity": {"count": 1, "until": ahead(0)}}})

    assert run(tmp_path, "src/b.ts") == (0, "")


def test_expired_entry_fails(tmp_path):
    write(tmp_path, {"src/a.ts": {"complexity": {"count": 1, "until": ahead(-1)}}})

    code, out = run(tmp_path, "README.md")

    assert code == 1
    assert f"src/a.ts:1: the complexity suppressions expired on {ahead(-1)}; fix the violations" in out


def test_entry_without_until_fails(tmp_path):
    write(tmp_path, {"src/a.ts": {"complexity": {"count": 1}}})

    code, out = run(tmp_path)

    assert code == 1
    assert "src/a.ts complexity needs until; run `mise run check-eslint-suppressions --stamp`" in out


def test_stamp_dates_only_entries_without_until(tmp_path):
    write(tmp_path, {"src/a.ts": {"complexity": {"count": 1}, "max-params": {"count": 2, "until": ahead(3)}}})

    assert run(tmp_path, "--stamp")[0] == 0

    text = (tmp_path / BASELINE).read_text()
    assert json.loads(text) == {"src/a.ts": {"complexity": {"count": 1, "until": ahead(90)},
                                             "max-params": {"count": 2, "until": ahead(3)}}}
    assert text.endswith("}\n")
    assert run(tmp_path)[0] == 0


def test_invalid_file_fails(tmp_path):
    (tmp_path / ".baselines").mkdir()
    (tmp_path / BASELINE).write_text("{x")

    code, out = run(tmp_path)

    assert code == 1
    assert f"{BASELINE}:1: invalid baseline" in out and "Traceback" not in out

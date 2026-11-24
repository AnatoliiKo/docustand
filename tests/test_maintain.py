"""Rendering of the maintenance contract and the `start` and `run` steps of `mise run maintain`."""

import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import yaml

from conftest import REPO_ROOT, init_git_repo

JOBS = ["docs-drift", "baseline-burndown", "dead-code"]
TITLE = re.compile(r"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9-]+\))?: \S.*[^.]$")
SQUASHED = "a" * 40


def files(root: Path, folder: str) -> list[Path]:
    return sorted(p for p in (root / folder).rglob("*") if p.is_file())


def out(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def test_none_renders_no_maintain_files(render, tmp_path):
    dest = render(tmp_path, project_name="demo")

    assert not (dest / ".maintain").exists()
    assert not (dest / ".mise/tasks/maintain").exists()
    assert not (dest / ".mise/lib/maintain.py").exists()
    assert (dest / ".mise/lib/protected.py").is_file()
    assert ".maintain" not in (dest / ".mise/data/root-files.txt").read_text().split()
    assert ".maintain/" not in (dest / "AGENTS.md").read_text()


def test_manual_renders_adapter_with_executable_run(maintain_template):
    dest = maintain_template()

    assert (dest / ".maintain/manual/README.md").is_file()
    assert (dest / ".maintain/manual/run").stat().st_mode & stat.S_IXUSR
    assert (dest / ".mise/tasks/maintain").stat().st_mode & stat.S_IXUSR
    assert ".maintain" in (dest / ".mise/data/root-files.txt").read_text().split()
    assert "`.maintain/`" in (dest / "AGENTS.md").read_text()


def test_custom_adapter_renders_contract_without_manual(maintain_template):
    dest = maintain_template(maintain_adapter="codex")

    assert (dest / ".maintain/jobs.yaml").is_file()
    assert (dest / ".mise/tasks/maintain").is_file()
    assert not (dest / ".maintain/manual").exists()
    assert yaml.safe_load((dest / ".repo.yaml").read_text())["maintain_adapter"] == "codex"


def test_manifest_jobs_have_instructions_paths_and_commit(maintain_template):
    dest = maintain_template()
    jobs = yaml.safe_load((dest / ".maintain/jobs.yaml").read_text())["jobs"]

    assert sorted(jobs) == sorted(JOBS)
    for name, job in jobs.items():
        assert (dest / job["instructions"]).is_file(), name
        assert job["paths"] and all(isinstance(p, str) for p in job["paths"]), name
        assert isinstance(job["exclude"], list), name
        assert job["commit"], name
    assert jobs["baseline-burndown"]["baselines"] is True
    assert "baselines" not in jobs["dead-code"]
    assert jobs["docs-drift"]["skip_md_exceptions"] and jobs["docs-drift"]["skip_generated"]


def test_maintain_files_do_not_name_the_template(maintain_template):
    dest = maintain_template()

    for path in files(dest, ".maintain"):
        text = path.read_text().lower()
        assert "docustand" not in text and "copier update" not in text, path


def test_custom_adapter_readme_names_no_manual_folder(maintain_template):
    text = (maintain_template(maintain_adapter="codex") / ".maintain/README.md").read_text()

    assert "manual" not in text and "mise run maintain -- run docs-drift --local" in text


def test_manual_readme_lists_manual_folder(maintain_template):
    text = (maintain_template() / ".maintain/README.md").read_text()

    assert "`manual/`" in text and ".maintain/manual/run docs-drift" in text


def test_commit_titles_fit_commitlint(maintain_template):
    jobs = yaml.safe_load((maintain_template() / ".maintain/jobs.yaml").read_text())["jobs"]

    for name, job in jobs.items():
        assert len(job["commit"]) <= 72 and TITLE.match(job["commit"]), name


def test_manual_readme_example_sets_permission_mode(maintain_template):
    text = (maintain_template() / ".maintain/manual/README.md").read_text()

    assert "--permission-mode acceptEdits" in text
    for word in ("--allowedTools", "adr.json", "comments.json", "betterleaks.ignore", "--local"):
        assert word in text


def test_update_reaches_maintain_readmes_and_keeps_the_project_readme(tmp_path):
    template = init_git_repo(tmp_path / "template-repo")
    shutil.copy(REPO_ROOT / "copier.yml", template / "copier.yml")
    shutil.copytree(REPO_ROOT / "template", template / "template", ignore=shutil.ignore_patterns("__pycache__"))
    project = init_git_repo(tmp_path / "project")

    def copier(*args: str) -> None:
        subprocess.run(["copier", *args], cwd=project, check=True, capture_output=True, stdin=subprocess.DEVNULL)

    def commit(root: Path, message: str) -> None:
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", message], check=True, capture_output=True)

    commit(template, "v1")
    subprocess.run(["git", "-C", str(template), "tag", "v0.0.1"], check=True, capture_output=True)
    copier("copy", "--defaults", "--vcs-ref", "v0.0.1", "--data", "project_name=demo", "--data",
           "maintain_adapter=manual", str(template), str(project))
    (project / "README.md").write_text("# Own project\n")
    commit(project, "chore: base")
    for source in (template / "template").rglob("README.md*"):
        source.write_text(source.read_text() + "\nAdded in v2.\n")
    commit(template, "v2")
    subprocess.run(["git", "-C", str(template), "tag", "v0.0.2"], check=True, capture_output=True)

    copier("update", "-a", ".repo.yaml", "--defaults", "--vcs-ref", "v0.0.2")

    assert "Added in v2." in (project / ".maintain/README.md").read_text()
    assert "Added in v2." in (project / ".maintain/manual/README.md").read_text()
    assert (project / "README.md").read_text() == "# Own project\n"
    commit(project, "chore: update")

    copier("update", "-a", ".repo.yaml", "--defaults", "--vcs-ref", "v0.0.2", "--data", "maintain_adapter=codex")

    assert "manual" not in (project / ".maintain/README.md").read_text()
    assert not (project / ".maintain/manual").exists()
    assert (project / "README.md").read_text() == "# Own project\n"


def test_prompt_prints_instruction_and_paths(world):
    w = world()

    result = w.maintain("prompt", "docs-drift")

    assert result.returncode == 0, out(result)
    assert "# Job docs-drift" in result.stdout and "`**/*.md`" in result.stdout


def test_unknown_job_and_broken_manifest_fail_with_one_line(world):
    w = world()
    unknown = w.maintain("prompt", "nope")
    w.write(".maintain/jobs.yaml", "jobs: [\n")
    w.git("commit", "-aq", "-m", "chore: break manifest")
    broken = w.maintain("prompt", "docs-drift")
    w.git("rm", "-q", ".maintain/jobs.yaml")
    w.git("commit", "-q", "-m", "chore: drop manifest")
    missing = w.maintain("prompt", "docs-drift")

    for result in (unknown, broken, missing):
        assert result.returncode == 1 and "Traceback" not in out(result)
        assert len([l for l in result.stderr.splitlines() if l.startswith("maintain:")]) == 1, result.stderr
    assert "unknown job" in unknown.stderr and "invalid" in broken.stderr and "does not exist" in missing.stderr


def test_start_refuses_dirty_tree(world):
    w = world()
    w.write("notes.txt", "x\n")

    result = w.maintain("start", "docs-drift", "--local")

    assert result.returncode == 1 and "uncommitted changes" in out(result)
    assert w.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "main"


def test_start_refuses_open_pull_request(world):
    w = world()
    w.prs({"number": 7, "state": "OPEN", "headRefOid": SQUASHED, "isCrossRepository": False})

    result = w.maintain("start", "docs-drift")

    assert result.returncode == 1 and "#7" in out(result)
    assert w.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "main"


def test_start_ignores_pull_request_from_a_fork(world):
    w = world()
    w.prs({"number": 7, "state": "OPEN", "headRefOid": SQUASHED, "isCrossRepository": True})

    assert w.maintain("start", "docs-drift").returncode == 0


def make_branch_with_commit(w) -> str:
    w.start()
    w.write("README.md", "# demo\n\nChanged.\n")
    w.git("commit", "-aq", "-m", "docs: agent edit")
    tip = w.git("rev-parse", "HEAD").strip()
    w.git("checkout", "-q", "main")
    return tip


def test_start_keeps_branch_with_commits(world):
    w = world()
    tip = make_branch_with_commit(w)

    result = w.maintain("start", "docs-drift", "--local")

    assert result.returncode == 1 and "git branch -D maintain/docs-drift" in out(result)
    assert w.git("rev-parse", "maintain/docs-drift").strip() == tip


def test_start_recreates_branch_of_squash_merged_pr(world):
    w = world()
    tip = make_branch_with_commit(w)
    w.prs({"number": 3, "state": "MERGED", "headRefOid": tip, "isCrossRepository": False})

    result = w.maintain("start", "docs-drift")

    assert result.returncode == 0, out(result)
    assert w.git("rev-parse", "maintain/docs-drift").strip() == w.git("rev-parse", "origin/main").strip()


def test_start_refuses_foreign_remote_branch(world):
    w = world()
    tip = make_branch_with_commit(w)
    w.git("push", "-q", "origin", "maintain/docs-drift")
    w.git("branch", "-q", "-D", "maintain/docs-drift")

    result = w.maintain("start", "docs-drift")

    assert result.returncode == 1 and "git push origin --delete maintain/docs-drift" in out(result)
    assert w.remote_git("rev-parse", "maintain/docs-drift").strip() == tip


def test_start_finds_default_branch_without_origin_head(world, tmp_path):
    w = world()
    w.git("branch", "-q", "dev")
    w.git("push", "-q", "origin", "dev")
    w.remote_git("symbolic-ref", "HEAD", "refs/heads/dev")
    clone = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "1", "-b", "dev", f"file://{w.remote}", str(clone)],
                   check=True, capture_output=True)
    assert subprocess.run(["git", "-C", str(clone), "symbolic-ref", "refs/remotes/origin/HEAD"],
                          capture_output=True).returncode != 0

    result = w.maintain("start", "docs-drift", "--local", cwd=clone)

    assert result.returncode == 0, out(result)
    assert subprocess.run(["git", "-C", str(clone), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True,
                          text=True).stdout.strip() == "maintain/docs-drift"
    assert "gh pr" not in w.log


def test_start_refuses_ignored_mise_local_toml(world):
    w = world()
    w.write(".gitignore", w.root.joinpath(".gitignore").read_text() + "mise.local.toml\n")
    w.git("commit", "-aq", "-m", "chore: ignore local config")
    w.git("push", "-q", "origin", "main")
    w.write("mise.local.toml", "[tasks.check]\nrun = 'true'\n")

    result = w.maintain("start", "docs-drift", "--local")

    assert result.returncode == 1 and "mise.local.toml" in out(result)


def test_start_local_calls_no_gh(world):
    w = world()

    result = w.maintain("start", "docs-drift", "--local")

    assert result.returncode == 0 and "not checked" in out(result)
    assert "gh " not in w.log
    assert w.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "maintain/docs-drift"


def test_start_sets_no_upstream(world):
    w = world()
    w.git("config", "branch.autoSetupMerge", "always")

    w.start()

    assert "branch.maintain/docs-drift." not in w.git("config", "--list")


def test_start_drops_the_marks_of_the_previous_run(world):
    w = world()
    w.start()
    w.write("README.md", "# demo\n\nChanged.\n")
    assert w.maintain("publish", "docs-drift", "--local").returncode == 0
    marks = w.root / w.git("rev-parse", "--git-path", "maintain-docs-drift").strip()
    assert marks.is_file()
    w.git("checkout", "-q", "main")
    w.git("branch", "-q", "-D", "maintain/docs-drift")

    w.start()

    assert not marks.exists()


def test_manual_run_stops_on_agent_failure(world):
    w = world()

    result = subprocess.run([str(w.root / ".maintain/manual/run"), "docs-drift", "--local", "--",
                             "sh", "-c", "echo edited >> README.md; exit 3"],
                            cwd=w.root, capture_output=True, text=True)

    assert result.returncode == 1 and "code 3" in out(result)
    assert "edited" in (w.root / "README.md").read_text()
    assert "mise run check" not in w.log
    assert w.git("rev-list", "--count", "origin/main..HEAD").strip() == "0"


def test_manual_run_without_command_prints_instruction(world):
    w = world()

    result = subprocess.run([str(w.root / ".maintain/manual/run"), "docs-drift", "--local"],
                            cwd=w.root, capture_output=True, text=True)

    assert result.returncode == 0, out(result)
    assert "# Job docs-drift" in result.stdout and "mise run maintain -- publish docs-drift" in result.stdout


def test_manual_run_commits_the_agent_edit(world):
    w = world()
    agent = "cat > /dev/null; printf '\\nMore.\\n' >> README.md"

    result = subprocess.run([str(w.root / ".maintain/manual/run"), "docs-drift", "--local", "--", "sh", "-c", agent],
                            cwd=w.root, capture_output=True, text=True)

    assert result.returncode == 0, out(result)
    assert w.git("log", "-1", "--format=%s").strip() == "docs: align documents with the code"
    assert w.git("show", "--name-only", "--format=", "HEAD").split() == ["README.md"]


def test_run_uses_code_loaded_before_agent(world):
    w = world()
    agent = ("cat > /dev/null; "
             "printf '#!/bin/sh\\nexit 0\\n' > .mise/tasks/maintain; "
             "printf 'def publish(*a):\\n    return 0\\n' > .mise/lib/maintain.py; "
             "printf '\\nMore.\\n' >> README.md")

    result = w.maintain("run", "docs-drift", "--local", "--", "sh", "-c", agent)

    assert result.returncode == 1
    assert ".mise/tasks/maintain" in out(result) and ".mise/lib/maintain.py" in out(result)
    assert "mise run check" not in w.log and w.git("rev-list", "--count", "origin/main..HEAD").strip() == "0"


def test_maintain_leaves_no_bytecode_cache(world):
    w = world()
    w.start()

    assert not list(w.root.rglob("__pycache__"))
    assert w.git("status", "--porcelain").strip() == ""

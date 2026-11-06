import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from conftest import REPO_ROOT, run_copier

TASKS = REPO_ROOT / "template" / ".mise" / "tasks"
ZEROS = "0" * 40
PR_IF = "${{ !cancelled() && github.event_name == 'pull_request' }}"
PUSH_IF = "${{ !cancelled() && github.event_name == 'push' }}"
LONG_HEADER = "feat: " + "x" * 74  # 80 characters, over the 72 limit


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    dest = tmp_path_factory.mktemp("ci") / "project"
    result = run_copier(dest, project_name="demo")
    assert result.returncode == 0, result.stderr
    return dest


@pytest.fixture(scope="module")
def workflow(rendered):
    return yaml.safe_load((rendered / ".github/workflows/standard-ci.yml").read_text())


@pytest.fixture(scope="module")
def renovate(rendered):
    return json.loads((rendered / "renovate.json").read_text())


def events(workflow):
    # PyYAML (YAML 1.1) reads the key `on` as boolean True.
    return workflow.get("on", workflow.get(True))


def steps(workflow):
    return workflow["jobs"]["check"]["steps"]


def step_text(workflow) -> str:
    return "\n".join(f"{s.get('if', '')}\n{s.get('run', '')}\n{s.get('env', '')}" for s in steps(workflow))


def test_ci_triggers_required_branches(workflow):
    on = events(workflow)

    assert on["push"]["branches"] == ["main"]
    assert on["pull_request"]["branches"] == ["main"]


def test_ci_triggers_follow_answers(tmp_path):
    dest = tmp_path / "project"
    assert run_copier(dest, project_name="demo", required_ci_branches=["main", "release"]).returncode == 0
    on = events(yaml.safe_load((dest / ".github/workflows/standard-ci.yml").read_text()))

    assert on["push"]["branches"] == ["main", "release"]


def test_ci_concurrency_and_permissions(workflow):
    assert workflow["concurrency"]["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"
    assert workflow["permissions"] == {"contents": "read"}
    checkout = next(s for s in steps(workflow) if s.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["fetch-depth"] == 0


def test_ci_pins_actions_by_sha(rendered):
    lines = [l for l in (rendered / ".github/workflows/standard-ci.yml").read_text().splitlines()
             if re.match(r"\s*(- )?uses:", l)]

    assert any("actions/checkout@" in l for l in lines)
    assert any("jdx/mise-action@" in l for l in lines)
    for line in lines:
        assert re.search(r"@[0-9a-f]{40}\s+# v\d+(\.\d+){0,2}\s*$", line), line
        assert "{{" not in line


def test_ci_baseline_base_refs(workflow):
    by_event = {}
    for step in steps(workflow):
        if "check-baseline" in step.get("run", ""):
            by_event[step["if"]] = step
    pr = by_event[PR_IF]
    push = by_event[PUSH_IF]

    assert pr["env"]["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
    assert push["env"]["BASE_SHA"] == "${{ github.event.before }}"
    assert 'check-baseline -- "$BASE_SHA"' in pr["run"]
    assert 'check-baseline -- "$BASE_SHA"' in push["run"]
    assert "new branch, no base" in push["run"]
    assert "${{" not in push["run"] and "${{" not in pr["run"]


def test_ci_baseline_push_skips_zero_before(tmp_path, workflow):
    """The shell guard of the push step skips an all-zero `before`."""
    push = next(s for s in steps(workflow) if s.get("if") == PUSH_IF
                and "check-baseline" in s["run"])
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "mise"
    fake.write_text('#!/bin/sh\necho "mise $*"\n')
    fake.chmod(0o755)

    def run(before):
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "BASE_SHA": before}
        return subprocess.run(["bash", "-e", "-c", push["run"]], env=env, capture_output=True, text=True)

    zero = run(ZEROS)
    real = run("a" * 40)

    assert zero.returncode == 0 and "new branch, no base" in zero.stdout and "mise" not in zero.stdout
    assert real.returncode == 0 and f"mise run check-baseline -- {'a' * 40}" in real.stdout


def test_ci_lints_all_pr_commits(workflow):
    step = next(s for s in steps(workflow) if "check-pr-commits" in s.get("run", ""))

    assert step["if"] == PR_IF
    assert step["env"]["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
    assert step["env"]["HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
    assert 'check-pr-commits -- "$BASE_SHA" "$HEAD_SHA"' in step["run"]


def test_ci_pr_body_via_env(workflow):
    step = next(s for s in steps(workflow) if "check-pr-body" in s.get("run", ""))

    assert step["if"] == PR_IF
    assert step["env"]["PR_BODY"] == "${{ github.event.pull_request.body }}"
    assert "${{" not in step["run"]


def test_ci_later_steps_run_after_failure(workflow):
    later = steps(workflow)[steps(workflow).index(next(s for s in steps(workflow)
                                                       if s.get("run") == "mise run check")) + 1:]

    assert len(later) == 4
    for step in later:
        assert step["if"].startswith("${{ !cancelled() && ")


def test_ci_runs_check(workflow):
    assert any(s.get("run") == "mise run check" for s in steps(workflow))


def test_ci_no_untrusted_expression_in_run(workflow):
    for step in steps(workflow):
        assert "${{" not in step.get("run", ""), step


def test_ci_scripts_are_executable():
    for name in ("check-baseline", "check-pr-body", "check-pr-commits"):
        assert (TASKS / name).stat().st_mode & stat.S_IXUSR, name


def test_renovate_copier_pattern(renovate):
    patterns = renovate["copier"]["managerFilePatterns"]

    assert patterns == ["/(^|/)\\.repo\\.yaml$/"]
    regex = re.compile(patterns[0][1:-1])
    assert regex.search(".repo.yaml") and regex.search("sub/.repo.yaml")
    assert not regex.search("x.repo.yaml")


def test_renovate_min_age_at_least_3_days(renovate):
    count, unit = renovate["minimumReleaseAge"].split()

    assert unit in ("days", "day", "weeks", "week")
    assert int(count) * (7 if unit.startswith("week") else 1) >= 3
    assert renovate["vulnerabilityAlerts"] == {"enabled": True, "minimumReleaseAge": None}
    assert renovate["extends"] == ["config:recommended"]
    assert renovate["semanticCommits"] == "enabled"


def test_renovate_merges_itself(renovate):
    assert renovate["platformAutomerge"] is False
    rule = next(r for r in renovate["packageRules"] if r.get("automerge"))
    assert rule["matchUpdateTypes"] == ["patch"]


COPIER_RULE = {"matchManagers": ["copier"], "minimumReleaseAge": None, "automerge": False}


@pytest.mark.parametrize("source", ["rendered", "root"])
def test_renovate_copier_updates_wait_for_review(renovate, source):
    # Git tags carry no release date, so the age check would hold copier updates forever.
    config = renovate if source == "rendered" else json.loads((REPO_ROOT / "renovate.json").read_text())
    rules = config["packageRules"]
    patch = rules.index({"matchUpdateTypes": ["patch"], "automerge": True})

    assert COPIER_RULE in rules
    assert rules.index(COPIER_RULE) > patch


SHORTHAND_RULES = [
    {"matchManagers": ["copier"], "matchDepNames": ["/^gh:/"],
     "overridePackageName": "{{{replace '^gh:' 'https://github.com/' depName}}}"},
    {"matchManagers": ["copier"], "matchDepNames": ["/^gl:/"],
     "overridePackageName": "{{{replace '^gl:' 'https://gitlab.com/' depName}}}"},
]


@pytest.mark.parametrize("source", ["rendered", "root"])
def test_renovate_expands_copier_shorthand(renovate, source):
    # Renovate passes `gh:owner/repo` to git-tags unchanged, and the tag lookup returns no result.
    config = renovate if source == "rendered" else json.loads((REPO_ROOT / "renovate.json").read_text())

    for rule in SHORTHAND_RULES:
        assert rule in config["packageRules"]
    pattern, url = re.search(r"replace '(.+)' '(.+)' depName", SHORTHAND_RULES[0]["overridePackageName"]).groups()
    assert re.sub(pattern, url, "gh:AnatoliiKo/docustand") == "https://github.com/AnatoliiKo/docustand"


def test_renovate_groups_updates(renovate):
    assert any("groupName" in r for r in renovate["packageRules"])


def test_renovate_ignores_standard_files(renovate):
    assert renovate["ignorePaths"] == [".mise/conf.d/standard.toml", ".github/workflows/standard-*.yml"]


def test_docustand_renovate_matches_template_files():
    root = json.loads((REPO_ROOT / "renovate.json").read_text())
    workflow = "template/.github/workflows/standard-ci.yml.jinja"
    mise = "template/.mise/conf.d/standard.toml.jinja"

    gha = root["github-actions"]["managerFilePatterns"]
    mise_patterns = root["mise"]["managerFilePatterns"]
    assert gha == ["/^template/\\.github/workflows/.+\\.ya?ml\\.jinja$/"]
    assert mise_patterns == ["/^template/\\.mise/conf\\.d/.+\\.toml\\.jinja$/"]
    assert any(re.search(p[1:-1], workflow) for p in gha)
    assert any(re.search(p[1:-1], mise) for p in mise_patterns)
    assert (REPO_ROOT / workflow).exists() and (REPO_ROOT / mise).exists()


def test_docustand_renovate_is_template_plus_documented_extras():
    root_text = (REPO_ROOT / "renovate.json").read_text()
    template_text = (REPO_ROOT / "template/renovate.json").read_text()
    root = json.loads(root_text)
    template = json.loads(template_text)

    # Same keys and values as the template, plus the keys that point Renovate at the template sources.
    assert set(root) - set(template) == {"github-actions", "mise", "customManagers"}
    for key, value in template.items():
        if key != "packageRules":
            assert root[key] == value, key
    rules, extra = root["packageRules"], root["packageRules"][len(template["packageRules"]):]
    assert rules[:len(template["packageRules"])] == template["packageRules"]
    assert {"matchManagers": ["custom.regex"], "groupName": "mise tools"} in extra
    assert {"matchFileNames": ["template/**"], "automerge": False} in extra

    # Template formatting is kept: every template line appears in order (trailing commas aside).
    root_lines = [ln.rstrip(",") for ln in root_text.splitlines()]
    position = 0
    for line in (ln.rstrip(",") for ln in template_text.splitlines()):
        position = root_lines.index(line, position) + 1

    # The deviation is recorded.
    answers = yaml.safe_load((REPO_ROOT / ".repo.yaml").read_text())
    assert "renovate.json" in [o["file"] for o in answers["overrides"]]


def test_docustand_renovate_bumps_hk_in_template_pkl():
    root = json.loads((REPO_ROOT / "renovate.json").read_text())
    manager = root["customManagers"][0]
    pkl = (REPO_ROOT / "template/hk.pkl.jinja").read_text()
    pattern = manager["managerFilePatterns"][0]

    assert re.search(pattern[1:-1], "template/hk.pkl.jinja")
    for expression in manager["matchStrings"]:
        assert re.findall(expression.replace("(?<", "(?P<"), pkl), expression
    assert manager["depNameTemplate"] == "jdx/hk"
    assert {"matchManagers": ["custom.regex"], "groupName": "mise tools"} in root["packageRules"]


def test_template_version_lines_have_no_jinja():
    text = (REPO_ROOT / "template/.github/workflows/standard-ci.yml.jinja").read_text()

    for line in text.splitlines():
        if "uses:" in line or "version" in line:
            assert "{{" not in line and "{%" not in line, line


def run_script(name, *args, env=None, cwd=None, stdin=None):
    result = subprocess.run(["uv", "run", "--script", str(TASKS / name), *args], cwd=cwd,
                            env={**os.environ, **(env or {})}, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def body(text):
    return run_script("check-pr-body", env={"PR_BODY": text})


def test_pr_body_generated_with_fails():
    code, out = body("## What\n\n🤖 Generated with Claude Code\n")

    assert code == 1
    assert "Generated with" in out


def test_pr_body_claude_link_fails():
    code, out = body("See https://claude.ai/code/session_x for details\n")

    assert code == 1
    assert "claude.ai" in out


def test_pr_body_clean_passes():
    assert body("## What\n\n- add the check\n\n## Why\n\nBecause.\n")[0] == 0


def test_pr_body_empty_passes():
    assert body("")[0] == 0
    assert run_script("check-pr-body", env={"PR_BODY": ""})[0] == 0


def test_pr_body_unset_passes():
    env = {k: v for k, v in os.environ.items() if k != "PR_BODY"}
    result = subprocess.run(["uv", "run", "--script", str(TASKS / "check-pr-body")], env=env,
                            capture_output=True, text=True)

    assert result.returncode == 0


FAKE_COMMITLINT = """#!/bin/sh
# Stand-in for commitlint: rejects a header longer than 72 characters.
header=$(head -n 1)
if [ "${#header}" -gt 72 ]; then
  echo "header-max-length: $header"
  exit 1
fi
"""


def commit_as(repo, author, message):
    env = {**os.environ, "GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": "a@example.com"}
    subprocess.run(["git", "-C", str(repo), "commit", "--allow-empty", "-m", message],
                   check=True, capture_output=True, env=env)


def head(repo):
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()


def test_pr_commits_skip_renovate(tmp_path, git_repo):
    fake = tmp_path / "commitlint"
    fake.write_text(FAKE_COMMITLINT)
    fake.chmod(0o755)
    env = {"COMMITLINT": str(fake)}
    repo = git_repo(tmp_path / "repo")
    base = head(repo)
    commit_as(repo, "renovate[bot]", LONG_HEADER)
    renovate_head = head(repo)

    assert run_script("check-pr-commits", base, renovate_head, env=env, cwd=repo)[0] == 0

    commit_as(repo, "Anatolii", LONG_HEADER)
    code, out = run_script("check-pr-commits", base, head(repo), env=env, cwd=repo)

    assert code == 1
    assert head(repo)[:7] in out


def test_pr_commits_passes_clean_range(tmp_path, git_repo):
    fake = tmp_path / "commitlint"
    fake.write_text(FAKE_COMMITLINT)
    fake.chmod(0o755)
    repo = git_repo(tmp_path / "repo")
    base = head(repo)
    commit_as(repo, "Anatolii", "feat: short")

    assert run_script("check-pr-commits", base, head(repo), env={"COMMITLINT": str(fake)}, cwd=repo)[0] == 0


def test_pr_commits_bad_args_fail(tmp_path, git_repo):
    repo = git_repo(tmp_path / "repo")

    assert run_script("check-pr-commits", cwd=repo)[0] == 1
    code, out = run_script("check-pr-commits", "deadbeef" * 5, "HEAD", cwd=repo)
    assert code == 1 and "deadbeef" in out


@pytest.mark.integration
def test_pr_commits_with_real_commitlint(tmp_path, git_repo):
    project = tmp_path / "project"
    assert run_copier(project, project_name="demo").returncode == 0
    git_repo(project)
    base = head(project)
    commit_as(project, "renovate[bot]", LONG_HEADER)
    ok_head = head(project)
    commit_as(project, "Anatolii", LONG_HEADER)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("MISE_", "__MISE", "UV_")) and k != "VIRTUAL_ENV"}
    env.update(MISE_TRUSTED_CONFIG_PATHS=str(tmp_path), MISE_YES="1")

    def run(end):
        return subprocess.run(
            ["mise", "x", "--", "uv", "run", "--script", str(project / ".mise/tasks/check-pr-commits"),
             base, end], cwd=project, env=env, capture_output=True, text=True)

    ok, bad = run(ok_head), run(head(project))

    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert bad.returncode == 1 and "header" in (bad.stdout + bad.stderr).lower()


def test_ci_logs_git_version(workflow):
    assert any(s.get("run") == "git --version" for s in steps(workflow))

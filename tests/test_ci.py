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
    return json.loads((rendered / ".github/renovate.json").read_text())


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
    assert workflow["permissions"] == {"contents": "read", "pull-requests": "read", "checks": "read"}
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

    assert len(later) == 7
    for step in later:
        assert step["if"].startswith("${{ !cancelled() && ")


def test_ci_runs_check(workflow):
    assert any(s.get("run") == "mise run check" for s in steps(workflow))


def check_step(workflow):
    return next(s for s in steps(workflow) if s.get("run") == "mise run check")


def test_ci_check_keeps_default_heap_without_node(workflow):
    assert "env" not in check_step(workflow)


def test_ci_check_raises_node_heap_for_typescript(tmp_path):
    dest = tmp_path / "project"
    assert run_copier(dest, project_name="demo", stack=["typescript"]).returncode == 0
    workflow = yaml.safe_load((dest / ".github/workflows/standard-ci.yml").read_text())

    assert check_step(workflow)["env"] == {"NODE_OPTIONS": "--max-old-space-size=4096"}


MERGED = "steps.merged.outputs.merged"


def test_ci_merged_push_skips_full_check(workflow):
    names = [s.get("id") or s.get("run") for s in steps(workflow)]
    detect = next(s for s in steps(workflow) if s.get("id") == "merged")
    check = next(s for s in steps(workflow) if s.get("run") == "mise run check")

    assert names.index("merged") < names.index("mise run check")
    assert detect["if"] == "${{ github.event_name == 'push' }}"
    assert detect["env"] == {"REPO": "${{ github.repository }}", "SHA": "${{ github.sha }}",
                             "GH_TOKEN": "${{ github.token }}"}
    assert 'mise run ci-merged-pr -- "$REPO" "$SHA"' in detect["run"]
    assert '>> "$GITHUB_OUTPUT"' in detect["run"]
    assert check["if"] == f"${{{{ github.event_name != 'push' || {MERGED} != 'true' }}}}"


def test_ci_merged_push_lints_pushed_range(tmp_path, workflow):
    step = next(s for s in steps(workflow) if "check-pr-commits" in s.get("run", "")
                and s["if"] != PR_IF)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "mise").write_text('#!/bin/sh\necho "mise $*"\n')
    (bin_dir / "mise").chmod(0o755)

    def run(before):
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "BASE_SHA": before,
               "HEAD_SHA": "b" * 40}
        return subprocess.run(["bash", "-e", "-c", step["run"]], env=env, capture_output=True, text=True)

    assert step["if"] == f"${{{{ !cancelled() && github.event_name == 'push' && {MERGED} == 'true' }}}}"
    assert step["env"] == {"BASE_SHA": "${{ github.event.before }}", "HEAD_SHA": "${{ github.sha }}"}
    zero = run(ZEROS)
    real = run("a" * 40)
    assert "new branch, no base" in zero.stdout and "mise" not in zero.stdout
    assert f"mise run check-pr-commits -- {'a' * 40} {'b' * 40}" in real.stdout


def test_ci_push_baseline_runs_for_merged_and_direct(workflow):
    push = next(s for s in steps(workflow) if s.get("if") == PUSH_IF and "check-baseline" in s["run"])

    assert MERGED not in push["if"]


def test_ci_no_untrusted_expression_in_run(workflow):
    for step in steps(workflow):
        assert "${{" not in step.get("run", ""), step


def test_ci_scripts_are_executable():
    for name in ("check-baseline", "check-pr-body", "check-pr-commits", "ci-merged-pr"):
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
    assert renovate["vulnerabilityAlerts"] == {"enabled": True, "minimumReleaseAge": None,
                                               "groupName": None, "schedule": ["at any time"]}
    assert renovate["extends"] == ["config:recommended"]
    assert renovate["semanticCommits"] == "enabled"


WEEKLY_RULE = {"matchUpdateTypes": ["minor", "patch", "pin", "digest"], "groupName": "non-major dependencies",
               "schedule": ["* 0-5 * * 1"]}


def test_renovate_groups_non_major_updates_weekly(renovate):
    # One pull request a week runs one CI check instead of one per dependency.
    rules = renovate["packageRules"]
    groups = [rules.index(r) for r in rules if r.get("groupName") in ("github actions", "mise tools")]

    assert WEEKLY_RULE in rules
    assert max(groups) < rules.index(WEEKLY_RULE)
    assert renovate["platformAutomerge"] is False
    assert not any(r.get("automerge") for r in rules)


def test_renovate_refreshes_lock_file_weekly(renovate):
    # Transitive dependencies change only in the lock file; their vulnerability alerts stay open otherwise.
    assert renovate["lockFileMaintenance"] == {"enabled": True, "schedule": WEEKLY_RULE["schedule"]}


COPIER_RULE = {"matchManagers": ["copier"], "minimumReleaseAge": None, "automerge": False,
               "groupName": None, "schedule": ["at any time"]}


@pytest.mark.parametrize("source", ["rendered", "root"])
def test_renovate_copier_updates_wait_for_review(renovate, source):
    # Git tags carry no release date, so the age check would hold copier updates forever.
    config = renovate if source == "rendered" else json.loads((REPO_ROOT / "renovate.json").read_text())
    rules = config["packageRules"]
    assert COPIER_RULE in rules
    assert rules.index(COPIER_RULE) > rules.index(WEEKLY_RULE)


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
    template_text = (REPO_ROOT / "template/.github/renovate.json").read_text()
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
    pkl = (REPO_ROOT / "template/.config/hk.pkl.jinja").read_text()
    pattern = manager["managerFilePatterns"][0]

    assert re.search(pattern[1:-1], "template/.config/hk.pkl.jinja")
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


SHA_A = "a" * 40


HEAD_B = "b" * 40
GREEN = json.dumps({"check_runs": [{"name": "check", "status": "completed", "conclusion": "success"}]})


def merged_pr(tmp_path, answer, code=0, sha=SHA_A, repo="owner/repo", checks=GREEN):
    """Run ci-merged-pr with a fake `gh` that answers the pulls and the check-runs requests."""
    fake = tmp_path / "gh"
    (tmp_path / "answer.json").write_text(answer)
    (tmp_path / "checks.json").write_text(checks)
    fake.write_text(f"""#!/bin/sh
echo "$*" >> "{tmp_path}/args"
case "$*" in
  *check-runs*) cat "{tmp_path}/checks.json" ;;
  *) cat "{tmp_path}/answer.json"; exit {code} ;;
esac
""")
    fake.chmod(0o755)
    return run_script("ci-merged-pr", repo, sha, env={"GH": str(fake)})


def merged(head=HEAD_B):
    return json.dumps([{"number": 7, "merged_at": "2026-11-06T10:00:00Z", "head": {"sha": head}}])


def test_merged_pr_true_for_merged_pull_request_with_green_check(tmp_path):
    code, out = merged_pr(tmp_path, merged())

    assert code == 0 and out.splitlines()[0] == "true"
    assert (tmp_path / "args").read_text().splitlines() == [
        f"api repos/owner/repo/commits/{SHA_A}/pulls",
        f"api repos/owner/repo/commits/{HEAD_B}/check-runs?check_name=check&per_page=100"]


@pytest.mark.parametrize("runs", [
    [],
    [{"status": "in_progress", "conclusion": None}],
    [{"status": "completed", "conclusion": "failure"}],
    [{"status": "completed", "conclusion": "cancelled"}],
    [{"status": "completed", "conclusion": "success"}, {"status": "completed", "conclusion": "failure"}],
])
def test_merged_pr_false_without_green_check(tmp_path, runs):
    # A pull request merged before its CI finished, or with red CI, was not checked.
    code, out = merged_pr(tmp_path, merged(), checks=json.dumps({"check_runs": runs}))

    assert code == 0 and out.splitlines()[0] == "false"


@pytest.mark.parametrize("checks", ["not json", "[]", "{}"])
def test_merged_pr_false_for_unreadable_checks(tmp_path, checks):
    code, out = merged_pr(tmp_path, merged(), checks=checks)

    assert code == 0 and out.splitlines()[0] == "false"


def test_merged_pr_false_for_invalid_head(tmp_path):
    code, out = merged_pr(tmp_path, merged(head="HEAD; rm -rf /"))

    assert code == 0 and out.splitlines()[0] == "false"
    assert len((tmp_path / "args").read_text().splitlines()) == 1


@pytest.mark.parametrize("answer", ["[]", json.dumps([{"number": 8, "merged_at": None, "head": {"sha": HEAD_B}}]),
                                    "not json", "{}"])
def test_merged_pr_false_without_merged_pull_request(tmp_path, answer):
    code, out = merged_pr(tmp_path, answer)

    assert code == 0 and out.splitlines()[0] == "false"


def test_merged_pr_false_when_api_fails(tmp_path):
    code, out = merged_pr(tmp_path, merged(), code=1)

    assert code == 0 and out.splitlines()[0] == "false"


@pytest.mark.parametrize("repo,sha", [("owner/repo;rm", SHA_A), ("owner/repo", "HEAD"), ("-x/y", SHA_A)])
def test_merged_pr_false_for_invalid_input(tmp_path, repo, sha):
    code, out = merged_pr(tmp_path, merged(), repo=repo, sha=sha)

    assert code == 0 and out.splitlines()[0] == "false"
    assert not (tmp_path / "args").exists()


def test_merged_pr_stdout_is_only_the_answer(tmp_path):
    fake = tmp_path / "gh"
    fake.write_text("#!/bin/sh\necho failure >&2\nexit 1\n")
    fake.chmod(0o755)
    result = subprocess.run(["uv", "run", "--quiet", "--script", str(TASKS / "ci-merged-pr"), "owner/repo", SHA_A],
                            env={**os.environ, "GH": str(fake)}, capture_output=True, text=True)

    assert result.stdout == "false\n"


def test_ci_typescript_installs_dependencies_and_checks_duplication(tmp_path, workflow):
    dest = tmp_path / "project"
    assert run_copier(dest, project_name="demo", stack=["typescript"]).returncode == 0
    ts = yaml.safe_load((dest / ".github/workflows/standard-ci.yml").read_text())
    names = [s.get("name") for s in steps(ts)]

    assert names.index("Node dependencies") < names.index("Checks")
    install = next(s for s in steps(ts) if s.get("name") == "Node dependencies")["run"]
    assert "pnpm install --frozen-lockfile" in install and "npm ci" in install
    duplication = next(s for s in steps(ts) if s.get("name") == "Duplication")
    assert duplication["if"] == PR_IF
    assert "jscpd --config .config/jscpd.json" in duplication["run"]
    assert "Node dependencies" not in [s.get("name") for s in steps(workflow)]
    assert "Duplication" not in [s.get("name") for s in steps(workflow)]


def test_ci_builds_typescript_after_checks(render, tmp_path):
    ts = yaml.safe_load((render(tmp_path / "ts", project_name="demo", stack=["typescript"])
                         / ".github/workflows/standard-ci.yml").read_text())
    plain = yaml.safe_load((render(tmp_path / "plain", project_name="demo")
                            / ".github/workflows/standard-ci.yml").read_text())
    names = [s.get("name") for s in steps(ts)]
    build = next(s for s in steps(ts) if s.get("name") == "Build")

    assert names.index("Build") == names.index("Checks") + 1
    assert build["run"] == "npm run --if-present build"
    assert build["if"] == next(s for s in steps(ts) if s.get("name") == "Checks")["if"]
    assert "Build" not in [s.get("name") for s in steps(plain)]

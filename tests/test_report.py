import json
import subprocess
import re
from datetime import UTC, date, datetime
from importlib import machinery, util

import pytest
import yaml

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "template" / ".mise" / "tasks" / "report"
NOW = datetime(2026, 11, 5, 6, 0, tzinfo=UTC)
CRONS = {"monthly": "17 6 1 * *", "weekly": "17 6 * * 1", "twice-weekly": "17 6 * * 1,4"}

ACCESS = """# Access

| Access | Owner | Where secrets live | Expires |
|---|---|---|---|
| Code hosting (GitHub repository) | | | never |
| CI token | | | YYYY-MM-DD |
| Deploy key | me | vault | 2026-11-20 |
| Old key | me | vault | 2026-10-01 |
| Far key | me | vault | 2027-06-01 |
| Odd key | me | vault | soon |
"""


def load():
    loader = machinery.SourceFileLoader("report_script", str(SCRIPT))
    spec = util.spec_from_loader("report_script", loader)
    module = util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def report():
    return load()


class Fake:
    """Replacement for report.fetch: answers by command text, records every call."""

    def __init__(self, vuln_enabled=True, commits=(), prs=(), files=None, detected=(), open_prs=(), added=(), renamed=(),
                 patches=None, pr_commits=None, commit_files=None):
        self.vuln_enabled, self.commits, self.prs = vuln_enabled, list(commits), list(prs)
        self.files, self.detected = files or {}, list(detected)
        self.patches, self.pr_commits, self.commit_files = patches or {}, pr_commits or {}, commit_files or {}
        self.open_prs, self.added, self.renamed = list(open_prs), set(added), set(renamed)
        self.calls: list[str] = []

    def __call__(self, cmd):
        text = " ".join(cmd)
        self.calls.append(text)
        if "vulnerability-alerts" in text:
            if self.vuln_enabled:
                return None
            raise subprocess.CalledProcessError(1, cmd)
        if match := re.search(r"pulls/(\d+)/commits", text):
            return self.pr_commits.get(int(match.group(1)), [])
        if match := re.search(r"/commits/(\w+)$", text):
            return {"files": [{"filename": f} for f in self.commit_files.get(match.group(1), [])]}
        if "/commits" in text:
            return self.commits
        if cmd[:3] == ["gh", "pr", "list"]:
            return self.open_prs if "open" in cmd else self.prs
        if "/files" in text:
            number = int(re.search(r"pulls/(\d+)/files", text).group(1))
            return [{"filename": f, "status": "added" if f in self.added else "renamed" if f in self.renamed else "modified",
                     "patch": self.patches.get((number, f), "")}
                    for f in self.files.get(number, [])]
        if "detect-stack" in text:
            return {"stack": self.detected, "evidence": {}}
        raise AssertionError(f"unexpected command: {text}")


def collect(report, fake, tmp_path, access=ACCESS, declared=(), schedule="weekly", manual=False, app=True):
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "access.md").write_text(access)
    (tmp_path / ".repo.yaml").write_text(yaml.safe_dump({"stack": list(declared)}))
    report.fetch = fake
    return report.collect("o/r", tmp_path, NOW, schedule, manual, protected=[".github/workflows/**"], app=app)


def commit(sha, message, when="2026-11-04T10:00:00Z"):
    return {"sha": sha, "commit": {"message": message, "committer": {"date": when}}}


@pytest.mark.parametrize("schedule", ["off", "monthly", "weekly", "twice-weekly"])
def test_cron_mapping(render, tmp_path, schedule):
    project = render(tmp_path, project_name="demo", report_schedule=schedule)
    path = project / ".github/workflows/standard-report.yml"
    if schedule == "off":
        assert not path.exists()
        return
    workflow = yaml.safe_load(path.read_text())
    on = workflow.get("on", workflow.get(True))
    assert on["schedule"] == [{"cron": CRONS[schedule]}]
    assert "workflow_dispatch" in on
    assert workflow["permissions"] == {"contents": "read", "pull-requests": "read"}
    text = path.read_text()
    assert "REPORT_APP_CLIENT_ID" in text and "REPORT_APP_PRIVATE_KEY" in text
    assert "REPORT_APP_ID" not in text and "app-id:" not in text
    assert "docustand" not in text.lower()


def test_workflow_runs_without_app(render, tmp_path):
    project = render(tmp_path, project_name="demo", report_schedule="weekly")
    jobs = yaml.safe_load((project / ".github/workflows/standard-report.yml").read_text())["jobs"]
    report_job = jobs["report"]
    steps = {s.get("id") or s.get("name"): s for s in report_job["steps"]}

    assert report_job["env"]["HAS_APP"] == "${{ secrets.REPORT_APP_CLIENT_ID != '' }}"
    assert steps["app"]["with"]["client-id"] == "${{ secrets.REPORT_APP_CLIENT_ID }}"
    assert steps["app"]["if"] == "${{ env.HAS_APP == 'true' }}"
    assert steps["Report"]["env"]["GH_TOKEN"] == "${{ steps.app.outputs.token || github.token }}"
    assert steps["Report"]["env"]["REPORT_APP_CONFIGURED"] == "${{ env.HAS_APP }}"
    assert steps["Report"]["env"]["REPORT_APP_SLUG"] == "${{ steps.app.outputs.app-slug }}"
    assert jobs["fresh-install"]["if"].startswith("${{ !cancelled() && ")


def run_main(report, tmp_path, monkeypatch, app: str | None):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "access.md").write_text(ACCESS)
    summary = tmp_path / "summary.md"
    monkeypatch.chdir(tmp_path)
    for name, value in {"GITHUB_REPOSITORY": "o/r", "GITHUB_STEP_SUMMARY": str(summary),
                        "REPORT_APP_CONFIGURED": app}.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    published = []
    monkeypatch.setattr(report, "fetch", Fake())
    monkeypatch.setattr(report, "publish", lambda sections, *_: published.append(sections))
    return report.main([]), summary, published


def test_main_without_app_fails_with_summary(report, tmp_path, monkeypatch, capsys):
    code, summary, published = run_main(report, tmp_path, monkeypatch, "false")

    assert code == 1
    assert not published
    assert report.NO_APP in capsys.readouterr().err
    text = summary.read_text()
    assert "## Report app" in text and report.NO_APP in text
    assert "Deploy key" in text
    assert report.VULN_NOT_CHECKED in text


def test_main_without_app_skips_the_slug_check(report, tmp_path, monkeypatch, capsys):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "access.md").write_text(ACCESS)
    summary = tmp_path / "summary.md"
    monkeypatch.chdir(tmp_path)
    for name, value in {"GITHUB_REPOSITORY": "o/r", "GITHUB_STEP_SUMMARY": str(summary),
                        "REPORT_APP_CONFIGURED": "false"}.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("REPORT_APP_SLUG", raising=False)
    monkeypatch.setattr(report, "fetch", Fake())
    monkeypatch.setattr(report, "run", lambda cmd: pytest.fail(f"ran {cmd}"))

    assert report.main([]) == 1

    err = capsys.readouterr().err
    assert report.NO_APP in err and "REPORT_APP_SLUG" not in err
    assert "Deploy key" in summary.read_text()


def test_main_with_app_publishes(report, tmp_path, monkeypatch):
    code, summary, published = run_main(report, tmp_path, monkeypatch, "true")

    assert code == 0
    assert len(published) == 1 and "Report app" not in published[0]
    assert "Deploy key" in summary.read_text()


def test_report_script_has_no_template_name():
    assert "docustand" not in SCRIPT.read_text().lower()


def test_since_from_schedule(report):
    expected = {"monthly": (10, 4), "weekly": (10, 28), "twice-weekly": (10, 31)}
    for schedule, (month, day) in expected.items():
        assert report.since_from_schedule(NOW, schedule) == datetime(2026, month, day, 6, tzinfo=UTC)
    assert report.since_from_schedule(NOW, "monthly", manual=True) == datetime(2026, 10, 28, 6, tzinfo=UTC)


def test_no_activity_skips_repo_checks(report, tmp_path):
    fake = Fake()
    sections = collect(report, fake, tmp_path, access="| Access | Expires |\n|---|---|\n")
    assert all(not v for v in sections.values())
    assert not any("/files" in c or "detect-stack" in c for c in fake.calls)
    assert any("/commits" in c for c in fake.calls)


def test_tokens_checked_without_activity(report, tmp_path):
    fake = Fake()
    sections = collect(report, fake, tmp_path)
    assert any("Deploy key" in f for f in sections["Tokens"])
    assert any(c.endswith("vulnerability-alerts") for c in fake.calls)
    assert not any("detect-stack" in c for c in fake.calls)


def test_vuln_alerts_disabled_is_finding(report, tmp_path):
    sections = collect(report, Fake(vuln_enabled=False), tmp_path, access="")
    assert sections["Vulnerability alerts"]


def test_vuln_alerts_not_checked_without_app(report, tmp_path):
    fake = Fake(vuln_enabled=False)
    sections = collect(report, fake, tmp_path, access="", app=False)
    assert sections["Vulnerability alerts"] == [report.VULN_NOT_CHECKED]
    assert not any("vulnerability-alerts" in c for c in fake.calls)


def test_expiring_token_within_30_days(report):
    found = report.expiring_tokens(ACCESS, date(2026, 11, 5))
    assert found == ["Deploy key", "Old key"]  # Old key is already expired
    assert report.expiring_tokens(ACCESS, date(2026, 11, 5), days=1) == ["Old key"]


def test_never_expires_ignored(report):
    # never, empty, the YYYY-MM-DD placeholder and non-dates never crash or count.
    assert report.expiring_tokens(ACCESS, date(2030, 1, 1)) == ["Deploy key", "Old key", "Far key"]
    assert report.expiring_tokens("no table here", date(2026, 11, 5)) == []
    assert report.expiring_tokens("| Access | Owner |\n|---|---|\n| x | y |", date(2026, 11, 5)) == []


def test_red_merge_detected(report):
    prs = [
        {"number": 1, "statusCheckRollup": [{"conclusion": "SUCCESS"}]},
        {"number": 2, "statusCheckRollup": [{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}]},
        {"number": 3, "statusCheckRollup": [{"state": "ERROR"}]},
        {"number": 4, "statusCheckRollup": []},
        {"number": 5},
    ]
    assert report.red_merges(prs) == [2, 3]


def test_skip_check_trailer_detected(report):
    commits = [
        commit("aaaaaaa1111", "feat: x\n\nbody"),
        commit("bbbbbbb2222", "fix: y\n\nSkip-Check: hk is broken"),
        commit("ccccccc3333", "docs: mention Skip-Check: in text"),
    ]
    assert report.skip_check_trailers(commits) == ["bbbbbbb fix: y"]


def test_monthly_due_weekly(report):
    assert report.monthly_due(date(2026, 11, 2), "weekly") is True
    assert report.monthly_due(date(2026, 11, 9), "weekly") is False


def test_monthly_due_twice_weekly(report):
    assert report.monthly_due(date(2026, 11, 2), "twice-weekly") is True
    assert report.monthly_due(date(2026, 11, 5), "twice-weekly") is False
    assert report.monthly_due(date(2026, 10, 1), "twice-weekly") is True
    assert report.monthly_due(date(2026, 10, 5), "twice-weekly") is False


def test_monthly_due_monthly(report):
    assert report.monthly_due(date(2026, 11, 17), "monthly") is True


def test_monthly_due_manual(report):
    assert report.monthly_due(date(2026, 11, 17), "weekly", manual=True) is True


def test_protected_changes_globs(report):
    protected = [".mise/tasks/**", ".repo.yaml", "mise.toml"]
    files = {1: ["src/a.ts", ".mise/tasks/x/y"], 2: ["src/b.ts"], 3: [".repo.yaml", "docs/mise.toml"]}
    assert report.protected_changes(files, protected) == {1: [".mise/tasks/x/y"], 3: [".repo.yaml"]}


def test_stack_drift(report):
    assert report.stack_drift(["terraform"], ["terraform"]) == []
    drift = report.stack_drift(["laravel", "terraform"], ["terraform", "expo"])
    assert len(drift) == 2 and "laravel" in drift[0] and "expo" in drift[1]


def test_new_baseline_files_section(report, tmp_path, monkeypatch):
    prs = [{"number": 7, "mergedAt": "2026-11-03T10:00:00Z", "statusCheckRollup": []},
           {"number": 8, "mergedAt": "2026-11-03T11:00:00Z", "statusCheckRollup": []}]
    fake = Fake(commits=[commit("ddddddd4444", "fix: z")], prs=prs, added={"a.baseline"},
                files={7: ["a.baseline", "src/x.py"], 8: ["a.baseline", "b.baseline"]})
    monkeypatch.setattr(report, "baseline_files", lambda root: ["a.baseline", "b.baseline"])
    sections = collect(report, fake, tmp_path, access="")
    assert sections["New baseline files"] == ["#7: `a.baseline`", "#8: `a.baseline`"]


def test_renamed_baseline_file_listed(report, tmp_path, monkeypatch):
    prs = [{"number": 9, "mergedAt": "2026-11-03T10:00:00Z", "statusCheckRollup": []}]
    fake = Fake(commits=[commit("ddddddd4444", "fix: z")], prs=prs, renamed={"new.baseline"},
                files={9: ["new.baseline"]})
    monkeypatch.setattr(report, "baseline_files", lambda root: ["new.baseline"])
    assert collect(report, fake, tmp_path, access="")["New baseline files"] == ["#9: `new.baseline`"]


def test_baseline_files_come_from_check_baseline(report, tmp_path, monkeypatch):
    (tmp_path / ".repo.yaml").write_text("stack: [terraform]\n")
    monkeypatch.setitem(report.check_baseline().PROFILE_BASELINES, "terraform", ["x.baseline"])
    assert report.baseline_files(tmp_path) == [".size-baseline.json", ".betterleaksignore", "x.baseline"]


def test_renamed_and_copied_count_as_added(report):
    assert report.ADDED == {"added", "renamed", "copied"}


def test_activity_findings_listed(report, tmp_path):
    prs = [{"number": 7, "mergedAt": "2026-11-03T10:00:00Z", "statusCheckRollup": [{"conclusion": "FAILURE"}]}]
    fake = Fake(commits=[commit("ddddddd4444", "fix: z\n\nSkip-Check: x")], prs=prs,
                files={7: [".github/workflows/standard-ci.yml"]}, detected=["laravel"])
    sections = collect(report, fake, tmp_path, access="")
    assert sections["Red merges"] == ["#7"]
    assert sections["Skip-Check"] == ["`ddddddd fix: z`"]
    assert sections["Protected files"] == ["#7: `.github/workflows/standard-ci.yml`"]
    assert sections["Stack"]


TEMPLATE_PATCH = "@@ -1,2 +1,2 @@\n-_commit: v0.1.4\n+_commit: v0.2.0\n _src_path: gh:o/docustand"
RENOVATE_PR = {"number": 4, "mergedAt": "2026-11-04T10:00:00Z", "statusCheckRollup": [],
               "author": {"login": "app/renovate", "is_bot": True}}


def renovate_commit(sha):
    return {"sha": sha, "author": {"login": "renovate[bot]"}}


def test_template_update_is_its_own_section(report, tmp_path):
    fake = Fake(prs=[RENOVATE_PR], files={4: [".repo.yaml", "hk.pkl", ".github/workflows/standard-ci.yml"]},
                patches={(4, ".repo.yaml"): TEMPLATE_PATCH}, pr_commits={4: [renovate_commit("aaa1")]})
    sections = collect(report, fake, tmp_path, access="")
    assert sections["Template updates"] == ["#4: `v0.2.0`"]
    assert sections["Protected files"] == []


def test_other_author_on_template_update_stays_protected(report, tmp_path):
    other = {"sha": "bbb2", "author": {"login": "someone"}}
    fake = Fake(prs=[RENOVATE_PR], files={4: [".repo.yaml", ".github/workflows/standard-ci.yml", ".github/workflows/x.yml"]},
                patches={(4, ".repo.yaml"): TEMPLATE_PATCH},
                pr_commits={4: [renovate_commit("aaa1"), other]},
                commit_files={"bbb2": [".github/workflows/x.yml", "src/a.py"]})
    sections = collect(report, fake, tmp_path, access="")
    assert sections["Template updates"] == ["#4: `v0.2.0`"]
    assert sections["Protected files"] == ["#4: `.github/workflows/x.yml`"]


def test_protected_change_without_template_bump_stays_protected(report, tmp_path):
    prs = [{**RENOVATE_PR, "number": 6}, {**RENOVATE_PR, "number": 7, "author": {"login": "someone"}}]
    fake = Fake(prs=prs, files={6: [".github/workflows/standard-ci.yml"], 7: [".repo.yaml", ".github/workflows/a.yml"]},
                patches={(7, ".repo.yaml"): TEMPLATE_PATCH})
    sections = collect(report, fake, tmp_path, access="")
    assert sections["Template updates"] == []
    assert sections["Protected files"] == ["#6: `.github/workflows/standard-ci.yml`", "#7: `.github/workflows/a.yml`"]


def test_template_updates_alone_open_no_pr(report, tmp_path):
    ran = []
    report.fetch = report_fetch(open_prs=[5])
    assert report.publish({"Template updates": ["#4: `v0.2.0`"]}, tmp_path, "2026-11-05", "repo-report",
                          runner=ran.append) is None
    assert ran == [["gh", "pr", "close", "5", "--comment", "no findings in the report of 2026-11-05"]]
    assert report.backlog_lines(report.findings_only({"Template updates": ["#4: `v0.2.0`"]})) == []


def test_protected_list_matches_settings(render, tmp_path, report):
    project = render(tmp_path, project_name="demo", stack=["terraform"])
    settings = json.loads((project / ".claude/settings.json").read_text())
    ask = [r[len("Edit(/"):-1] for r in settings["permissions"]["ask"] if r.startswith("Edit(/")]
    loaded = report.load_protected(project)
    assert loaded == ask
    assert ".mise/tasks/**" in loaded and ".github/repo.schema.json" in loaded
    assert ".tflint.hcl" in loaded


def test_empty_report_returns_none(report):
    assert report.render_report({}) is None
    assert report.render_report({"Tokens": [], "Red merges": []}) is None
    text = report.render_report({"Tokens": ["CI token"], "Red merges": []})
    assert "CI token" in text and "Red merges" not in text


def test_repo_without_history(report):
    assert report.has_activity([], [], NOW) is False
    since = report.since_from_schedule(NOW, "weekly")
    assert report.has_activity([commit("e", "m", "2026-10-01T00:00:00Z")], [], since) is False
    assert report.has_activity([commit("e", "m")], [], since) is True


def report_fetch(open_prs=()):
    """`fetch` for `publish`: the open `report` PR list and the bot user."""
    def fetch(cmd):
        if cmd[:3] == ["gh", "pr", "list"]:
            return [{"number": n} for n in open_prs]
        if cmd[:2] == ["gh", "api"] and cmd[2].startswith("/users/"):
            return {"id": 4242}
        raise AssertionError(f"unexpected command: {cmd}")
    return fetch


def test_no_findings_opens_no_pr(report, tmp_path):
    ran = []
    report.fetch = report_fetch()
    assert report.publish({"Tokens": []}, tmp_path, "2026-11-05", "repo-report", runner=ran.append) is None
    assert ran == []


def test_no_findings_closes_open_report_pr(report, tmp_path):
    ran = []
    report.fetch = report_fetch(open_prs=[5])

    assert report.publish({"Tokens": []}, tmp_path, "2026-11-05", "repo-report", runner=ran.append) is None

    assert ran == [["gh", "pr", "close", "5", "--comment", "no findings in the report of 2026-11-05"]]


def test_findings_open_pr(report, tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "tasks.md").write_text("## In progress\n\n## Backlog\n")
    ran = []
    report.fetch = report_fetch()
    body = report.publish({"Tokens": ["CI token (expires 2026-11-20)"]}, tmp_path, "2026-11-05", "repo-report",
                          runner=ran.append)
    tasks = (tmp_path / "docs" / "tasks.md").read_text()
    assert tasks.endswith("- Replace the expiring tokens of `docs/access.md` — they expire within 30 days or have expired.\n")
    assert "2026-11-05" not in tasks
    assert body.startswith("Report of 2026-11-05.\n")
    flat = [" ".join(c) for c in ran]
    assert any(c.startswith("gh pr create") and "--title report" in c for c in flat)


def test_findings_without_app_slug_stop(report, tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "tasks.md").write_text("## In progress\n\n## Backlog\n")
    report.fetch = report_fetch()
    with pytest.raises(SystemExit, match="REPORT_APP_SLUG"):
        report.publish({"Tokens": ["CI token"]}, tmp_path, "2026-11-05", "", runner=lambda c: None)


def test_report_commit_author_is_the_app_bot(report, tmp_path, git_repo, monkeypatch):
    repo = git_repo(tmp_path / "repo")
    (repo / "docs").mkdir()
    (repo / "docs" / "tasks.md").write_text("## In progress\n\n## Backlog\n")
    monkeypatch.chdir(repo)
    report.fetch = report_fetch()

    def runner(cmd):
        if cmd[0] == "git" and cmd[1] != "push":
            subprocess.run(cmd, check=True, capture_output=True)

    report.publish({"Tokens": ["CI token"]}, repo, "2026-11-05", "repo-report", runner=runner)

    author = subprocess.run(["git", "log", "-1", "--format=%an <%ae>"], check=True, capture_output=True,
                            text=True).stdout.strip()
    assert author == "repo-report[bot] <4242+repo-report[bot]@users.noreply.github.com>"
    assert author.split(" <")[0].endswith("[bot]")


def test_one_backlog_line_per_kind(report):
    lines = report.backlog_lines({
        "Protected files": ["#12: `hk.pkl`", "#14: `.claude/settings.json`, `mise.toml`"],
        "Red merges": ["#7"],
        "Tokens": [],
    })
    assert lines == [
        "- Review changes to protected files in #12, #14 — they change how checks run outside a template update.",
        "- Investigate failed checks of merged pull requests #7 — a merge with a red check skips the gate.",
    ]


ALL_FINDINGS = {
    "Tokens": ["Deploy key expires soon or has expired"],
    "Vulnerability alerts": ["Vulnerability alerts are not enabled or not readable"],
    "Red merges": ["#7", "#9"],
    "Skip-Check": ["`ddddddd fix: z (urgent)`"],
    "Protected files": ["#12: `hk.pkl`"],
    "New baseline files": ["#14: `.size-baseline.json`"],
    "Stack": ["`laravel` is in the code but not in `stack` of .repo.yaml"],
    "Contract": ["drift (api)"],
}


def test_backlog_lines_pass_tasks_format(report, render, tmp_path, git_repo):
    project = git_repo(render(tmp_path, project_name="demo"))
    tasks = project / "docs" / "tasks.md"
    tasks.write_text(tasks.read_text().rstrip("\n") + "\n" + "\n".join(report.backlog_lines(ALL_FINDINGS)) + "\n")

    result = subprocess.run([str(project / ".mise/tasks/check-tasks-format")], cwd=project,
                            capture_output=True, text=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(report.backlog_lines(ALL_FINDINGS)) == len(ALL_FINDINGS)


def test_cancelled_is_red_merge(report):
    assert report.red_merges([{"number": 9, "statusCheckRollup": [{"conclusion": "CANCELLED"}]}]) == [9]


def test_activity_scoped_to_default_branch(report, tmp_path):
    fake = Fake()
    (tmp_path / "docs").mkdir()
    (tmp_path / ".repo.yaml").write_text("stack: []\n")
    report.fetch = fake
    report.collect("o/r", tmp_path, NOW, "weekly", protected=[], base="trunk")
    listed = [c for c in fake.calls if c.startswith("gh pr list")]
    assert len(listed) == 2 and all("--base trunk" in c for c in listed)
    assert any("/commits" in c and "sha=trunk" in c for c in fake.calls)


def test_open_pr_counts_as_activity(report, tmp_path):
    fake = Fake(open_prs=[{"number": 5, "updatedAt": "2026-11-04T10:00:00Z"}], detected=[])
    collect(report, fake, tmp_path, access="")
    assert any("detect-stack" in c for c in fake.calls)
    stale = Fake(open_prs=[{"number": 5, "updatedAt": "2026-09-01T10:00:00Z"}])
    collect(report, stale, tmp_path, access="")
    assert not any("detect-stack" in c for c in stale.calls)


def test_untrusted_text_cannot_mention(report, tmp_path):
    sections = {"Skip-Check": [report.code("@octocat fix: `x`")]}
    body = report.render_report(sections)
    assert "`@octocat fix: 'x'`" in body
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "tasks.md").write_text("## In progress\n\n## Backlog\n")
    report.fetch = report_fetch()
    report.publish(sections, tmp_path, "2026-11-05", "repo-report", runner=lambda c: None)
    line = (tmp_path / "docs" / "tasks.md").read_text().splitlines()[-1]
    assert "`@octocat" in line
    assert line.startswith("- Review ") and " — " in line


def test_typescript_report_lists_project_check_configs(render, tmp_path, report):
    project = render(tmp_path, project_name="demo", stack=["typescript"])
    protected = report.load_protected(project)
    configs = ["eslint.project.mjs", "knip.json", ".dependency-cruiser.cjs", "steiger.config.ts",
               ".size-baseline.json", "eslint-suppressions.json", ".jscpd.json"]

    changes = report.protected_changes({5: [*configs, "src/a.ts"]}, protected)

    assert changes == {5: configs}

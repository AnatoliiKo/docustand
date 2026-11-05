"""Tests for the guard hooks and .claude/settings.json of the template."""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, init_git_repo

HOOKS = REPO_ROOT / "template" / ".claude" / "hooks"
PR_MSG = 'Run the "Before a PR" steps from AGENTS.md and mise run pr-ready first.'

PROTECTED = [
    ".repo.yaml", "renovate.json", "mise.toml", ".mise/conf.d/**", "hk.pkl",
    ".github/workflows/**", ".claude/settings.json", ".claude/hooks/**",
    ".mise/tasks/**", ".mise/data/**", ".github/repo.schema.json",
    "commitlint.config.mjs", "typos.toml", ".rumdl.toml", "lychee.toml",
]


def run_hook(name, command, cwd=None, env=None, tool="Bash", raw=None):
    payload = raw if raw is not None else json.dumps(
        {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(cwd or os.getcwd())}
    )
    return subprocess.run(
        [sys.executable, str(HOOKS / f"{name}.py")], input=payload,
        capture_output=True, text=True, env=env,
    )


def bash(command, **kw):
    return run_hook("guard_bash", command, **kw)


# --- guard_bash: blocked forms ------------------------------------------------

def test_blocks_no_verify():
    r = bash("git commit --no-verify -m x")
    assert r.returncode == 2 and "no-verify" in r.stderr


def test_blocks_short_n():
    assert bash("git commit -n -m x").returncode == 2


def test_blocks_combined_nm():
    assert bash('git commit -nm "x"').returncode == 2


def test_blocks_hookspath_c():
    assert bash("git -c core.hooksPath=/dev/null commit -m x").returncode == 2


def test_blocks_git_config_hookspath():
    assert bash("git config core.hooksPath /dev/null").returncode == 2
    assert bash("git config --local core.hooksPath .git/nope").returncode == 2


def test_blocks_hk_skip_env():
    for cmd in (
        "HK_SKIP_STEPS=typos git commit -m x",
        "HK_SKIP_STEP=typos git commit -m x",
        "HK_SKIP_HOOK=pre-commit git commit -m x",
        "HK_SKIP_HOOKS=pre-commit git commit -m x",
    ):
        assert bash(cmd).returncode == 2, cmd


def test_blocks_hk_zero():
    assert bash("HK=0 git commit -m x").returncode == 2


def test_blocks_hook_config_override():
    assert bash("git -c hook.hk.command=true commit -m x").returncode == 2


def test_blocks_git_config_hook_unset():
    assert bash("git config --unset-all hook.hk.command").returncode == 2
    assert bash("git config --unset hook.hk.command").returncode == 2
    assert bash("git config --remove-section hook.hk").returncode == 2
    assert bash("git config --global hook.hk.command true").returncode == 2


def test_blocks_push_no_verify():
    assert bash("git push --no-verify origin main").returncode == 2


@pytest.mark.parametrize("command", [
    "git -C repo commit --no-verify -m x",
    "git -C repo commit -n -m x",
    "env HK_SKIP_STEPS=typos git commit -m x",
    "env -i HK=0 git commit -m x",
    "export HK=0",
    "export FOO=1 HK_SKIP_HOOKS=pre-commit",
    "git add . && git commit -n -m x",
    "git add .; git commit --no-verify",
    "true | git commit -nm x",
    "git commit -m 'ok'\ngit commit --no-verify -m x",
    "git commit -am x -n",
    'bash -c "git commit -n -m x"',
    "git commit --no-ver -m x",
])
def test_blocks_more_forms(command):
    assert bash(command).returncode == 2, command


def test_blocks_unparsable_with_bypass():
    # Unterminated quote: shlex-style parsing fails, the regex fallback still blocks.
    r = bash('git commit --no-verify -m "unterminated')
    assert r.returncode == 2


def test_unparsable_without_bypass_allowed():
    assert bash('git commit -m "unterminated').returncode == 0


# --- guard_bash: allowed forms ------------------------------------------------

def test_allows_flag_words_in_message():
    assert bash('git commit -m "docs: explain -n and --no-verify"').returncode == 0


@pytest.mark.parametrize("command", [
    "git commit -m'fix: HK=0 and core.hooksPath'",
    "git commit -mx",
    "git commit --message 'say --no-verify'",
    "git commit --message='say -n'",
    "git commit -F msg.txt",
    "git commit -a -m 'note: git config hook.x'",
    "git push -n origin main",
    "git push --dry-run",
    "git status",
    "git config user.name me",
    "git config --get hook.hk.command",
    "git -C repo commit -m x",
    "echo HK=0",
    "git log --grep=--no-verify",
    "# git commit -n",
])
def test_allows_message_values_and_safe_forms(command):
    assert bash(command).returncode == 0, command


def test_allows_heredoc_message():
    cmd = (
        "git commit -F - <<'EOF'\n"
        "fix: stop using --no-verify and -n\n\n"
        "HK=0 git commit -n\n"
        "EOF\n"
    )
    assert bash(cmd).returncode == 0


def test_allows_heredoc_dash_and_commit_substitution():
    cmd = 'git commit -m "$(cat <<-EOF\n\t--no-verify\n\tEOF\n)"'
    assert bash(cmd).returncode == 0


def test_blocks_after_heredoc():
    cmd = "cat <<EOF\nhello\nEOF\ngit commit -n -m x\n"
    assert bash(cmd).returncode == 2


def test_allows_chain_without_bypass():
    assert bash("git add . && git commit -m x").returncode == 0


def test_ignores_non_bash_tool_and_bad_json():
    assert bash("git commit -n", tool="Edit").returncode == 0
    assert run_hook("guard_bash", "", raw="not json").returncode == 0


@pytest.mark.parametrize("command", [
    "{ git commit -n -m x; }",
    "if true; then git commit -n -m x; fi",
    "while true; do git commit -n -m x; done",
    "! git commit -n -m x",
    "(git commit -n -m x)",
    "$((1<<2))\ngit commit -n -m x",
    "x=$((a<<b))\ngit commit --no-verify -m x",
    "echo $((1<<2)) && HK=0 git commit -m x",
    "eval 'git commit -n -m x'",
    "eval git commit --no-verify -m x",
    "nice -n 5 git commit -n -m x",
    "timeout 10 git commit -n -m x",
    "timeout -s KILL 10 git commit -n -m x",
    "echo x | xargs git commit -n -m",
    "xargs -n 1 git commit --no-verify -m",
    "GIT_CONFIG_KEY_0=core.hooksPath git commit -m x",
    "GIT_CONFIG_KEY_1=HOOK.hk.command git commit -m x",
    "env GIT_CONFIG_KEY_0=core.hookspath git commit -m x",
    "export GIT_CONFIG_KEY_0=hook.hk.command",
    "GIT_CONFIG_PARAMETERS=\"'core.hookspath=/dev/null'\" git commit -m x",
    "env GIT_CONFIG_PARAMETERS=\"'hook.hk.command=true'\" git commit -m x",
])
def test_blocks_compound_and_wrapped_forms(command):
    assert bash(command).returncode == 2, command


@pytest.mark.parametrize("command", [
    "git config get core.hooksPath",
    "git config get --all hook.hk.command",
    "git config list",
    "GIT_CONFIG_KEY_0=user.name git commit -m x",
    "echo $((1<<2))\ngit commit -m x",
    "if true; then git commit -m x; fi",
    "timeout 10 git status",
])
def test_allows_safe_wrapped_and_read_forms(command):
    assert bash(command).returncode == 0, command


def test_blocks_git_config_new_syntax_writes():
    assert bash("git config set core.hooksPath /dev/null").returncode == 2
    assert bash("git config unset hook.hk.command").returncode == 2


# --- guard_pr_create ----------------------------------------------------------

def _mark(repo: Path, content=None):
    path = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--git-path", "pr-ready"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    path = Path(path) if os.path.isabs(path) else repo / path
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    path.write_text((content if content is not None else head) + "\n")


def test_pr_create_blocked_without_mark(tmp_path):
    repo = init_git_repo(tmp_path / "r")
    r = run_hook("guard_pr_create", "gh pr create --fill", cwd=repo)
    assert r.returncode == 2
    assert PR_MSG in r.stderr
    assert "docustand" not in r.stderr


def test_pr_create_blocked_with_stale_mark(tmp_path):
    repo = init_git_repo(tmp_path / "r")
    _mark(repo, "0" * 40)
    assert run_hook("guard_pr_create", "gh pr create", cwd=repo).returncode == 2


def test_pr_create_allowed_with_mark(tmp_path):
    repo = init_git_repo(tmp_path / "r")
    _mark(repo)
    assert run_hook("guard_pr_create", "git push && gh pr create --fill", cwd=repo).returncode == 0


def test_pr_create_blocked_after_new_commit(tmp_path):
    repo = init_git_repo(tmp_path / "r")
    _mark(repo)
    subprocess.run(["git", "-C", str(repo), "commit", "--allow-empty", "-m", "more"], check=True,
                   capture_output=True)
    assert run_hook("guard_pr_create", "gh pr create", cwd=repo).returncode == 2


def test_pr_create_in_worktree(tmp_path):
    repo = init_git_repo(tmp_path / "r")
    wt = tmp_path / "wt"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "feat", str(wt)],
                   check=True, capture_output=True)
    assert run_hook("guard_pr_create", "gh pr create", cwd=wt).returncode == 2
    _mark(wt)
    assert run_hook("guard_pr_create", "gh pr create", cwd=wt).returncode == 0


@pytest.mark.parametrize("command", [
    "gh pr new -t x",
    "{ gh pr create --fill; }",
    "if true; then gh pr create; fi",
    "timeout 30 gh pr create",
    "eval 'gh pr create --fill'",
])
def test_pr_create_alias_and_wrapped_forms_blocked(tmp_path, command):
    repo = init_git_repo(tmp_path / "r")
    assert run_hook("guard_pr_create", command, cwd=repo).returncode == 2


def test_pr_create_ignores_other_commands(tmp_path):
    repo = init_git_repo(tmp_path / "r")
    assert run_hook("guard_pr_create", "gh pr view 3", cwd=repo).returncode == 0
    assert run_hook("guard_pr_create", 'git commit -m "gh pr create"', cwd=repo).returncode == 0
    assert run_hook("guard_pr_create", "gh pr create", cwd=repo, tool="Edit").returncode == 0


# --- guard_pr_merge -----------------------------------------------------------

def fake_gh(tmp_path, stdout, code=0):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    script = bindir / "gh"
    script.write_text(
        "#!/bin/sh\n"
        f'echo "$@" > "{tmp_path}/gh-args"\n'
        f"cat <<'JSON'\n{stdout}\nJSON\n"
        f"exit {code}\n"
    )
    script.chmod(0o755)
    return {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}


def test_pr_merge_blocked_on_failure(tmp_path):
    env = fake_gh(tmp_path, '[{"name":"ci","state":"FAILURE"},{"name":"lint","state":"SUCCESS"}]')
    r = run_hook("guard_pr_merge", "gh pr merge 5 --squash", cwd=tmp_path, env=env)
    assert r.returncode == 2
    assert "ci" in r.stderr
    assert "lint" not in r.stderr
    assert (tmp_path / "gh-args").read_text().split() == ["pr", "checks", "5", "--json", "state,name"]


def test_pr_merge_allowed_on_success(tmp_path):
    env = fake_gh(tmp_path, '[{"name":"ci","state":"SUCCESS"},{"name":"opt","state":"SKIPPED"}]')
    assert run_hook("guard_pr_merge", "gh pr merge --squash", cwd=tmp_path, env=env).returncode == 0
    assert (tmp_path / "gh-args").read_text().split() == ["pr", "checks", "--json", "state,name"]


def test_pr_merge_blocked_on_pending(tmp_path):
    env = fake_gh(tmp_path, '[{"name":"ci","state":"PENDING"}]')
    r = run_hook("guard_pr_merge", "gh pr merge 5", cwd=tmp_path, env=env)
    assert r.returncode == 2 and "ci" in r.stderr


def test_pr_merge_blocked_without_checks(tmp_path):
    env = fake_gh(tmp_path, "[]")
    r = run_hook("guard_pr_merge", "gh pr merge 5", cwd=tmp_path, env=env)
    assert r.returncode == 2 and "no checks reported" in r.stderr

    env = fake_gh(tmp_path, "", code=1)
    r = run_hook("guard_pr_merge", "gh pr merge 5", cwd=tmp_path, env=env)
    assert r.returncode == 2 and "no checks reported" in r.stderr

    env = fake_gh(tmp_path, "not json")
    assert run_hook("guard_pr_merge", "gh pr merge 5", cwd=tmp_path, env=env).returncode == 2


def test_pr_merge_blocked_when_gh_missing(tmp_path):
    env = {**os.environ, "PATH": str(tmp_path / "empty")}
    r = run_hook("guard_pr_merge", "gh pr merge 5", cwd=tmp_path, env=env)
    assert r.returncode == 2 and "no checks reported" in r.stderr


def test_pr_merge_blocked_on_timeout(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text("#!/bin/sh\nsleep 5\n")
    gh.chmod(0o755)
    src = (HOOKS / "guard_pr_merge.py").read_text().replace("timeout=30", "timeout=0.5")
    patched = tmp_path / "guard_pr_merge.py"
    patched.write_text(src)
    (tmp_path / "_shell.py").write_text((HOOKS / "_shell.py").read_text())
    env = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}
    r = subprocess.run(
        [sys.executable, str(patched)], capture_output=True, text=True, env=env,
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "gh pr merge 5"}, "cwd": str(tmp_path)}),
    )
    assert r.returncode == 2 and "no checks reported" in r.stderr


def test_pr_merge_wrapped_form_blocked(tmp_path):
    env = fake_gh(tmp_path, "[]")
    assert run_hook("guard_pr_merge", "{ gh pr merge 5; }", cwd=tmp_path, env=env).returncode == 2


def test_pr_merge_ignores_other_commands(tmp_path):
    env = fake_gh(tmp_path, "[]")
    assert run_hook("guard_pr_merge", "gh pr view 5", cwd=tmp_path, env=env).returncode == 0
    assert run_hook("guard_pr_merge", "echo gh pr merge", cwd=tmp_path, env=env).returncode == 0


# --- settings.json ------------------------------------------------------------

def _settings(project):
    return json.loads((project / ".claude" / "settings.json").read_text())


def test_settings_json_valid(render, tmp_path):
    settings = _settings(render(tmp_path, project_name="demo"))

    assert settings["attribution"]["sessionUrl"] is False
    assert settings["attribution"]["commit"] == "" and settings["attribution"]["pr"] == ""
    assert settings["autoMemoryEnabled"] is False
    assert settings["includeGitInstructions"] is False
    ask = settings["permissions"]["ask"]
    for path in PROTECTED:
        assert f"Edit(/{path})" in ask, path
    assert "Edit(/.mise/tasks/**)" in ask and "Edit(/.github/repo.schema.json)" in ask
    assert "Edit(/.tflint.hcl)" not in ask
    assert sorted(ask) == sorted(f"Edit(/{p})" for p in PROTECTED)


def test_settings_terraform_protects_tflint(render, tmp_path):
    settings = _settings(render(tmp_path, project_name="demo", stack=["terraform"]))
    assert "Edit(/.tflint.hcl)" in settings["permissions"]["ask"]


def test_settings_deny_github_mcp(render, tmp_path):
    deny = _settings(render(tmp_path, project_name="demo"))["permissions"]["deny"]
    for prefix in ("mcp__github__", "mcp__plugin_github_github__"):
        for tool in ("merge_pull_request", "push_files", "create_or_update_file"):
            assert prefix + tool in deny


def test_settings_hooks_and_plugins(render, tmp_path):
    settings = _settings(render(tmp_path, project_name="demo"))

    pre = settings["hooks"]["PreToolUse"]
    assert len(pre) == 1 and pre[0]["matcher"] == "Bash"
    commands = [h["command"] for h in pre[0]["hooks"]]
    assert commands == [
        f'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/{n}.py"'
        for n in ("guard_bash", "guard_pr_create", "guard_pr_merge")
    ]
    assert all(h["type"] == "command" for h in pre[0]["hooks"])
    assert settings["enabledPlugins"] == {
        "docustand@docustand": True,
        "superpowers@superpowers-marketplace": True,
    }
    assert settings["extraKnownMarketplaces"] == {
        "docustand": {"source": {"source": "github", "repo": "AnatoliiKo/docustand"}},
        "superpowers-marketplace": {"source": {"source": "github", "repo": "obra/superpowers-marketplace"}},
    }


def test_hooks_rendered_executable_and_clean(render, tmp_path):
    dest = render(tmp_path, project_name="demo")
    for name in ("guard_bash", "guard_pr_create", "guard_pr_merge"):
        path = dest / ".claude" / "hooks" / f"{name}.py"
        assert path.stat().st_mode & stat.S_IXUSR, name
        assert "docustand" not in path.read_text()

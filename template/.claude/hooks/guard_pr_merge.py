#!/usr/bin/env python3
"""PreToolUse hook: `gh pr merge` only when every CI check is SUCCESS or SKIPPED.

The checks are read in the directory after `cd` or `pushd` in the same command, or for
`-R`/`--repo`/`GH_REPO` or a PR URL. A merge after a `cd` the hook cannot resolve is blocked
until it names the repository. `gh pr merge --auto` is blocked while checks are pending: intended,
because on the Free plan there is no branch protection to make auto-merge wait safely.
"""

import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _shell import block, read_bash_input, all_commands, gh_repo, with_directories  # noqa: E402

NO_CHECKS = "no checks reported; CI did not run"
NO_REPO = "cannot tell the repository after cd; pass -R OWNER/REPO or a PR URL"
OK_STATES = {"SUCCESS", "SKIPPED"}
# gh pr merge flags that take a value (the value must not be taken for the PR argument).
VALUE_FLAGS = {"-b", "--body", "-F", "--body-file", "-t", "--subject", "-A", "--author-email",
               "--match-head-commit", "-R", "--repo"}


def merge_target(words, assigns):
    """For `gh pr merge ...` return (pr_argument_or_None, repo_or_None); else None."""
    if words[:3] != ["gh", "pr", "merge"]:
        return None
    arg = None
    rest, i = words[3:], 0
    while i < len(rest):
        w = rest[i]
        if w in VALUE_FLAGS:
            i += 2
        elif w.startswith("-"):
            i += 1
        else:
            arg = arg or w
            i += 1
    return arg, gh_repo(rest, assigns, VALUE_FLAGS)


def check(arg, repo, cwd):
    cmd = ["gh", "pr", "checks"]
    if arg:
        cmd.append(arg)
    if repo:
        cmd += ["-R", repo]
    cmd += ["--json", "state,name"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)
        checks = json.loads(result.stdout)
        if not isinstance(checks, list):
            raise ValueError("not a list")
        bad = [f'{c["name"]} ({c["state"]})' for c in checks if c.get("state") not in OK_STATES]
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError, AttributeError):
        block(NO_CHECKS)
    if bad:
        block("CI checks are not green: " + ", ".join(bad))
    if result.returncode != 0 or not checks:
        block(NO_CHECKS)


def main():
    parsed = read_bash_input()
    if parsed is None:
        return
    command, cwd = parsed
    cwd = cwd if cwd and os.path.isdir(cwd) else os.getcwd()
    try:
        commands = all_commands(command)
    except ValueError:
        commands = [command.split()]
    for assigns, words, directory in with_directories(commands, cwd):
        target = merge_target(words, assigns)
        if not target:
            continue
        arg, repo = target
        if directory is None and not repo and "://" not in (arg or ""):
            block(NO_REPO)
        check(arg, repo, directory)


if __name__ == "__main__":
    main()

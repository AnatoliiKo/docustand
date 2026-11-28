#!/usr/bin/env python3
"""PreToolUse hook: `gh pr create` (and its alias `gh pr new`) only after `mise run pr-ready` on HEAD.

The mark is read in the checkout the PR comes from: the directory after `cd` or `pushd`
in the same command, or, with `-R`/`--repo`/`GH_REPO`, the checkout among the hook's cwd
and the `cd`, `pushd` and `git -C` directories of the command whose remote is that
repository. The call passes when no such checkout is known: the mark of an unknown
checkout cannot be read, and the CI of the target repository is the backstop.
"""

import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _shell import block, read_bash_input, all_commands, gh_repo, with_directories  # noqa: E402

MESSAGE = 'Run the "Before a PR" steps from AGENTS.md and mise run pr-ready first.'
# gh pr create flags that take a value (the value must not be taken for `-R`).
VALUE_FLAGS = {"-a", "--assignee", "-B", "--base", "-b", "--body", "-F", "--body-file", "-H", "--head",
               "-l", "--label", "-m", "--milestone", "-p", "--project", "-r", "--reviewer",
               "-T", "--template", "-t", "--title"}


def git(cwd, *args):
    result = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def is_pr_create(words):
    return words[:3] in (["gh", "pr", "create"], ["gh", "pr", "new"])  # `new` is gh's alias


def slug(repo):
    """`OWNER/REPO` in lower case from `OWNER/REPO`, `HOST/OWNER/REPO` or a remote URL."""
    parts = [p for p in re.split(r"[/:]", repo.strip().removesuffix("/").removesuffix(".git")) if p]
    return "/".join(parts[-2:]).lower() if len(parts) >= 2 else None


def has_remote(directory, repo):
    urls = git(directory, "config", "--get-regexp", r"^remote\..*\.url$") or ""
    return any(slug(line.split(None, 1)[-1]) == slug(repo) for line in urls.splitlines())


def git_c_dirs(words, directory):
    if words[:1] != ["git"]:
        return []
    found = []
    for flag, value in zip(words, words[1:]):
        if flag == "-C":
            path = os.path.join(directory or "", os.path.expanduser(value))
            if os.path.isabs(path) and os.path.isdir(path):
                found.append(os.path.normpath(path))
    return found


def is_ready(checkout):
    head = git(checkout, "rev-parse", "HEAD")
    mark = git(checkout, "rev-parse", "--git-path", "pr-ready")
    if head and mark:
        path = mark if os.path.isabs(mark) else os.path.join(checkout, mark)
        try:
            with open(path) as handle:
                return handle.read().strip() == head
        except OSError:
            pass
    return False


def main():
    parsed = read_bash_input()
    if parsed is None:
        return
    command, cwd = parsed
    cwd = cwd or os.getcwd()
    try:
        commands = all_commands(command)
    except ValueError:
        commands = [command.split()]
    steps = list(with_directories(commands, cwd))
    known = [cwd] + [d for _, _, d in steps if d] + [p for _, words, d in steps for p in git_c_dirs(words, d)]
    for assigns, words, directory in steps:
        if not is_pr_create(words):
            continue
        repo = gh_repo(words[3:], assigns, VALUE_FLAGS)
        if repo:
            checkout = next((d for d in [directory] + known if d and has_remote(d, repo)), None)
        else:
            checkout = directory
        if checkout and not is_ready(checkout):
            block(MESSAGE)


if __name__ == "__main__":
    main()

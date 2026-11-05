#!/usr/bin/env python3
"""PreToolUse hook: `gh pr create` (and its alias `gh pr new`) only after `mise run pr-ready` on HEAD.

The check uses the hook's cwd; a `cd` earlier in the same command is not followed
(CI is the backstop).
"""

import os
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _shell import block, read_bash_input, all_commands, strip_prefix  # noqa: E402

MESSAGE = 'Run the "Before a PR" steps from AGENTS.md and mise run pr-ready first.'


def git(cwd, *args):
    result = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def is_pr_create(words):
    return words[:3] in (["gh", "pr", "create"], ["gh", "pr", "new"])  # `new` is gh's alias


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
    if not any(is_pr_create(strip_prefix(words)[1]) for words in commands):
        return
    head = git(cwd, "rev-parse", "HEAD")
    mark = git(cwd, "rev-parse", "--git-path", "pr-ready")
    if head and mark:
        path = mark if os.path.isabs(mark) else os.path.join(cwd, mark)
        try:
            with open(path) as handle:
                if handle.read().strip() == head:
                    return
        except OSError:
            pass
    block(MESSAGE)


if __name__ == "__main__":
    main()

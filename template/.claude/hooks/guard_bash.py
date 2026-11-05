#!/usr/bin/env python3
"""PreToolUse hook: block ways of bypassing git hooks and hk checks.

Blocked: `--no-verify` / `-n` on git commit, `--no-verify` on push and friends,
core.hooksPath and hook.* git config (via `git -c` and `git config`), and
HK=0 / HK_SKIP_* variables (plain, via `env` or `export`).
Message values (-m, -F, --message, --file) and heredoc bodies are not analysed.

If the command cannot be parsed (for example an unterminated quote) the hook
falls back to a conservative regular-expression scan of the raw text.
"""

import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _shell import block, read_bash_input, split_commands, strip_prefix  # noqa: E402

SKIP_VARS = {"HK_SKIP_STEPS", "HK_SKIP_STEP", "HK_SKIP_HOOK", "HK_SKIP_HOOKS"}
NO_VERIFY_CMDS = {"commit", "push", "merge", "rebase", "am"}
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                  "--super-prefix", "--config-env"}
# Options of git subcommands whose value is a message or a file: never analysed.
VALUE_SHORT = set("mFCctSu")  # for commit: the rest of a cluster / next word is a value
VALUE_LONG = {"--message", "--file", "--author", "--date", "--template", "--cleanup",
              "--fixup", "--squash", "--reuse-message", "--reedit-message"}
CONFIG_READ = ("--get", "--get-all", "--get-regexp", "--get-urlmatch", "-l", "--list")


def bad_env(name, value):
    return name in SKIP_VARS or name.startswith("HK_SKIP_") or (name == "HK" and value.strip() in ("0", "false"))


def bad_config_key(key):
    key = key.lower()
    return key.startswith("hook.") or key == "core.hookspath"


def is_no_verify(arg):
    return arg.startswith("--no-v") and "--no-verify".startswith(arg)


def check_git(words):
    """Return a reason string if this `git ...` command bypasses hooks."""
    i = 1
    while i < len(words) and words[i].startswith("-"):
        opt = words[i]
        if opt == "-c" and i + 1 < len(words):
            if bad_config_key(words[i + 1].split("=", 1)[0]):
                return f"git -c {words[i + 1].split('=', 1)[0]} would change or disable git hooks"
        elif opt.startswith("--config-env="):
            if bad_config_key(opt.split("=", 2)[1]):
                return "--config-env would change or disable git hooks"
        elif opt == "--config-env" and i + 1 < len(words):
            if bad_config_key(words[i + 1].split("=", 1)[0]):
                return "--config-env would change or disable git hooks"
        i += 2 if opt in GIT_VALUE_OPTS else 1
    if i >= len(words):
        return None
    sub, args = words[i], words[i + 1:]
    if sub == "config":
        if any(a in CONFIG_READ for a in args):
            return None
        keys = [a for a in args if not a.startswith("-")]
        if any(bad_config_key(k) for k in keys):
            return "changing core.hooksPath or hook.* git config disables git hooks"
        return None
    if sub in NO_VERIFY_CMDS:
        j = 0
        while j < len(args):
            a = args[j]
            if a == "--":
                break
            if a.startswith("--"):
                if is_no_verify(a):
                    return f"git {sub} --no-verify skips the hooks"
                if a in VALUE_LONG:
                    j += 1
            elif a.startswith("-") and len(a) > 1:
                for k, ch in enumerate(a[1:], 1):
                    if ch == "n" and sub == "commit":
                        return "git commit -n (--no-verify) skips the hooks"
                    if sub in ("commit", "merge", "am", "rebase") and ch in VALUE_SHORT:
                        if k == len(a) - 1 and ch not in "Su":
                            j += 1  # value is the next word
                        break
            j += 1
    return None


def check_command(words, depth=0):
    assigns, rest = strip_prefix(words)
    for name, value in assigns:
        if bad_env(name, value):
            return f"{name} disables hk checks"
    if not rest:
        return None
    head = os.path.basename(rest[0])
    if head == "export":
        for w in rest[1:]:
            name, eq, value = w.partition("=")
            if eq and bad_env(name, value):
                return f"export {name} disables hk checks"
    elif head == "git":
        return check_git(rest)
    elif head in ("sh", "bash", "zsh", "dash") and depth < 3:
        for k, w in enumerate(rest[1:-1], 1):
            if w.startswith("-") and not w.startswith("--") and "c" in w:
                return check_text(rest[k + 1], depth + 1)
    return None


FALLBACK = [
    (re.compile(r"--no-v(e(r(i(f(y)?)?)?)?)?\b"), "--no-verify skips the hooks"),
    (re.compile(r"core\.hookspath", re.I), "core.hooksPath disables git hooks"),
    (re.compile(r"\bhook\.[\w-]+\.", re.I), "hook.* git config disables git hooks"),
    (re.compile(r"\bHK_SKIP_\w*="), "HK_SKIP_* disables hk checks"),
    (re.compile(r"\bHK=(0|false)\b"), "HK=0 disables hk checks"),
    (re.compile(r"\bgit\b[^;&|\n]*\bcommit\b[^;&|\n]*\s-[A-Za-z]*n"), "git commit -n skips the hooks"),
]


def check_text(text, depth=0):
    try:
        commands = split_commands(text)
    except ValueError:
        # Unparsable: scan the raw text conservatively instead of allowing silently.
        for pattern, reason in FALLBACK:
            if pattern.search(text):
                return reason + " (command could not be parsed; fix its quoting)"
        return None
    for words in commands:
        reason = check_command(words, depth)
        if reason:
            return reason
    return None


def main():
    parsed = read_bash_input()
    if parsed is None:
        return
    reason = check_text(parsed[0])
    if reason:
        block(f"Blocked: {reason}. Fix the cause of the failing check instead of bypassing it.")


if __name__ == "__main__":
    main()

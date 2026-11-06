#!/usr/bin/env python3
"""PreToolUse hook: block ways of bypassing git hooks and hk checks.

Blocked: `--no-verify` / `-n` on git commit, `--no-verify` on push and friends,
core.hooksPath and hook.* git config (via `git -c` and `git config`), and
HK=0 / HK_SKIP_* variables (plain, via `env` or `export`).
Also looks into `eval`, `sh -c` strings, wrappers such as `sudo`, `nohup`,
`nice` and `time`, and env-based git config (GIT_CONFIG_KEY_<n>, GIT_CONFIG_PARAMETERS).
Message values (-m, -F, --message, --file) and heredoc bodies are not analysed.

If the command cannot be parsed (for example an unterminated quote) the hook
falls back to a conservative regular-expression scan of the raw text.

Asked: a command that writes to a protected path, that is a path of an
`Edit(/<path>)` rule in `permissions.ask` of .claude/settings.json. Writes are
output redirections, `tee`, `sed -i`, `perl -i`, and the destination of `cp`
and `mv` (and the source of `mv`). A block wins over an ask. An unparsable
command asks when its raw text names a protected path next to a write marker.
"""

import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _shell import all_commands, ask, block, read_bash_input, redirects, strip_prefix  # noqa: E402

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
    if name == "GIT_CONFIG_PARAMETERS":
        return "hookspath" in value.lower() or "hook." in value.lower()
    if name.startswith("GIT_CONFIG_KEY_"):
        return bad_config_key(value)
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
        keys = [a for a in args if not a.startswith("-")]
        if any(a in CONFIG_READ for a in args) or (keys and keys[0] in ("get", "list")):
            return None
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


def check_command(words):
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
    return None


FALLBACK = [
    (re.compile(r"--no-v(e(r(i(f(y)?)?)?)?)?\b"), "--no-verify skips the hooks"),
    (re.compile(r"core\.hookspath", re.I), "core.hooksPath disables git hooks"),
    (re.compile(r"\bhook\.[\w-]+\.", re.I), "hook.* git config disables git hooks"),
    (re.compile(r"\bHK_SKIP_\w*="), "HK_SKIP_* disables hk checks"),
    (re.compile(r"\bGIT_CONFIG_(KEY_\d+|PARAMETERS)=\S*hook", re.I), "GIT_CONFIG_* hook override disables git hooks"),
    (re.compile(r"\bHK=(0|false)\b"), "HK=0 disables hk checks"),
    (re.compile(r"\bgit\b[^;&|\n]*\bcommit\b[^;&|\n]*\s-[A-Za-z]*n"), "git commit -n skips the hooks"),
]


def check_text(text):
    try:
        commands = all_commands(text)
    except ValueError:
        # Unparsable: scan the raw text conservatively instead of allowing silently.
        for pattern, reason in FALLBACK:
            if pattern.search(text):
                return reason + " (command could not be parsed; fix its quoting)"
        return None
    for words in commands:
        reason = check_command(words)
        if reason:
            return reason
    return None


ASK_EDIT = re.compile(r"^Edit\(/(.+)\)$")


def load_protected(root):
    """Protected paths: the `Edit(/<path>)` rules of `permissions.ask` in .claude/settings.json."""
    try:
        with open(os.path.join(root, ".claude", "settings.json")) as f:
            settings = json.load(f)
        rules = settings["permissions"]["ask"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    return [m.group(1) for rule in rules if isinstance(rule, str) and (m := ASK_EDIT.match(rule))]


def _glob_body(pattern):
    parts = re.split(r"(\*\*|\*)", pattern)
    return "".join(".*" if p == "**" else "[^/]*" if p == "*" else re.escape(p) for p in parts)


def glob(pattern):
    """Compile a protected pattern; `**` crosses directories, `*` does not.

    A `dir/**` pattern also matches `dir` itself. Matching ignores case, as the
    file systems of macOS and Windows do.
    """
    body = _glob_body(pattern)
    if pattern.endswith("/**"):
        body = f"(?:{body}|{_glob_body(pattern[:-3])})"
    return re.compile(body + r"\Z", re.IGNORECASE)


def literal_prefix(pattern):
    """The part of a pattern before its first wildcard, without a trailing slash."""
    return pattern.split("*", 1)[0].rstrip("/")


def parse_args(args, short_values="", long_values=()):
    """Split `args` into operands and (option, value) pairs of the options that take a value."""
    operands, values, i = [], [], 0
    while i < len(args):
        a = args[i]
        if a == "--":
            operands += args[i + 1:]
            break
        if a.startswith("--"):
            name, eq, value = a.partition("=")
            if name in long_values:
                if not eq and i + 1 < len(args):
                    i += 1
                    value = args[i]
                values.append((name, value))
        elif a.startswith("-") and len(a) > 1:
            for k, ch in enumerate(a[1:], 1):
                if ch in short_values:
                    value = a[k + 1:]
                    if not value and i + 1 < len(args):
                        i += 1
                        value = args[i]
                    values.append(("-" + ch, value))
                    break
        else:
            operands.append(a)
        i += 1
    return operands, values


def in_place(args, value_letters, long_name=None):
    """True when the short option `-i` (alone or in a cluster) or `long_name` is present."""
    for a in args:
        if a == "--":
            return False
        if long_name and (a == long_name or a.startswith(long_name + "=")):
            return True
        if a.startswith("-") and not a.startswith("--"):
            for ch in a[1:]:
                if ch == "i":
                    return True
                if ch in value_letters:
                    break
    return False


def write_targets(words):
    """Paths that this simple command writes to and paths that it removes, as written."""
    targets, removed = redirects(words), []
    rest = strip_prefix(words)[1]
    if not rest:
        return targets, removed
    head, args = os.path.basename(rest[0]), rest[1:]
    if head == "tee":
        targets += parse_args(args)[0]
    elif head == "sed" and in_place(args, "ef", "--in-place"):
        targets += parse_args(args, "ef", {"--expression", "--file"})[0]
    elif head == "perl" and in_place(args, "eE"):
        targets += parse_args(args, "eE")[0]
    elif head in ("cp", "mv"):
        operands, values = parse_args(args, "tS", {"--target-directory", "--suffix"})
        dirs = [v for o, v in values if o in ("-t", "--target-directory")]
        if not dirs and len(operands) >= 2:
            dirs, operands = operands[-1:], operands[:-1]
        for d in dirs:
            targets.append(d)
            targets += [os.path.join(d, os.path.basename(src.rstrip("/"))) for src in operands]
        if head == "mv":
            removed += operands
    return targets, removed


WRITE_MARKER = re.compile(r">|\btee\b|(^|\s)-[A-Za-z]*i|--in-place|\bcp\b|\bmv\b")


def fallback_writes(text, protected):
    """Protected patterns named in an unparsable command that also has a write marker."""
    if not WRITE_MARKER.search(text):
        return []
    low = text.lower()
    return [p for p in protected if literal_prefix(p).lower() in low]


def protected_writes(text, cwd, root):
    """Project-relative protected paths that the command writes to or removes."""
    protected = load_protected(root)
    if not protected:
        return []
    try:
        commands = all_commands(text)
    except ValueError:
        return fallback_writes(text, protected)
    patterns = [glob(p) for p in protected]
    prefixes = [literal_prefix(p).lower() for p in protected]
    root = os.path.realpath(root)
    hits = []

    def relative(target):
        if not target or target == "-" or target.startswith("/dev/"):
            return None
        path = os.path.realpath(os.path.join(cwd, os.path.expandvars(os.path.expanduser(target))))
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        return None if rel == ".." or rel.startswith("../") else rel

    for words in commands:
        targets, removed = write_targets(words)
        for target in targets + removed:
            rel = relative(target)
            if rel is None:
                continue
            hit = any(p.match(rel) for p in patterns)
            if not hit and target in removed:
                # Moving a parent directory moves the protected files inside it.
                hit = rel == "." or any(pre.startswith(rel.lower() + "/") for pre in prefixes)
            if hit and rel not in hits:
                hits.append(rel)
    return hits


def project_root():
    # The hooks live in <root>/.claude/hooks when CLAUDE_PROJECT_DIR is not set.
    here = os.path.dirname(os.path.abspath(__file__))
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(here))


def main():
    parsed = read_bash_input()
    if parsed is None:
        return
    command, cwd = parsed
    reason = check_text(command)
    if reason:
        block(f"Blocked: {reason}. Fix the cause of the failing check instead of bypassing it.")
    hits = protected_writes(command, cwd or os.getcwd(), project_root())
    if hits:
        ask(f"The command writes to protected files of the standard: {', '.join(hits)}. "
            "A change of these files needs the owner's approval.")


if __name__ == "__main__":
    main()

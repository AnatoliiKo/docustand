"""Shared helpers for the guard hooks: PreToolUse input and a small shell splitter.

Python 3 standard library only. The splitter is not a full shell parser; it
understands quotes, backslashes, comments, heredocs and the separators
`&&`, `||`, `;`, `|`, `&`, parentheses, backticks and newlines.
"""

import json
import sys

sys.dont_write_bytecode = True

_SEPARATORS = {"&", "|", ";", "(", ")", "`"}


def read_bash_input():
    """Return (command, cwd) for a Bash PreToolUse call, or None to allow."""
    try:
        data = json.loads(sys.stdin.read())
        if data.get("tool_name") != "Bash":
            return None
        command = data["tool_input"]["command"]
        if not isinstance(command, str):
            return None
        return command, data.get("cwd")
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def block(reason):
    sys.stderr.write(reason.rstrip("\n") + "\n")
    sys.exit(2)


def split_commands(text):
    """Split `text` into simple commands (lists of unquoted words).

    Heredoc bodies and comments are dropped. Raises ValueError on an
    unterminated quote.
    """
    commands, words = [], []
    cur, has = [], False
    heredocs = []  # (delimiter, strip_tabs) waiting for the next newline
    i, n = 0, len(text)

    def flush_word():
        nonlocal cur, has
        if has:
            words.append("".join(cur))
        cur, has = [], False

    def flush_command():
        nonlocal words
        flush_word()
        if words:
            commands.append(words)
        words = []

    while i < n:
        c = text[i]
        if c == "\\":
            if i + 1 < n:
                if text[i + 1] != "\n":
                    cur.append(text[i + 1])
                    has = True
                i += 2
            else:
                i += 1
        elif c == "'":
            end = text.find("'", i + 1)
            if end < 0:
                raise ValueError("unterminated single quote")
            cur.append(text[i + 1:end])
            has = True
            i = end + 1
        elif c == '"':
            i += 1
            while True:
                if i >= n:
                    raise ValueError("unterminated double quote")
                if text[i] == "\\" and i + 1 < n and text[i + 1] in '"\\$`\n':
                    if text[i + 1] != "\n":
                        cur.append(text[i + 1])
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                else:
                    cur.append(text[i])
                    i += 1
            has = True
        elif c in " \t\r":
            flush_word()
            i += 1
        elif c == "\n":
            flush_command()
            i += 1
            for delim, strip_tabs in heredocs:
                while i < n:
                    end = text.find("\n", i)
                    line = text[i:n if end < 0 else end]
                    i = n if end < 0 else end + 1
                    if (line.lstrip("\t") if strip_tabs else line) == delim:
                        break
            heredocs = []
        elif c == "#" and not has:
            while i < n and text[i] != "\n":
                i += 1
        elif c == "<" and text.startswith("<<", i) and not text.startswith("<<<", i):
            j = i + 2
            strip_tabs = j < n and text[j] == "-"
            if strip_tabs:
                j += 1
            while j < n and text[j] in " \t":
                j += 1
            delim = []
            while j < n and text[j] not in " \t\r\n;&|()<>":
                if text[j] in "'\"":
                    end = text.find(text[j], j + 1)
                    if end < 0:
                        raise ValueError("unterminated heredoc delimiter")
                    delim.append(text[j + 1:end])
                    j = end + 1
                elif text[j] == "\\":
                    j += 1
                else:
                    delim.append(text[j])
                    j += 1
            heredocs.append(("".join(delim), strip_tabs))
            flush_word()
            i = j
        elif c in _SEPARATORS:
            if c == "&" and ((i > 0 and text[i - 1] in "<>") or text[i + 1:i + 2] == ">"):
                cur.append(c)  # redirections such as 2>&1 and &>file
                has = True
            else:
                flush_command()
            i += 1
        else:
            cur.append(c)
            has = True
            i += 1
    flush_command()
    return commands


_WRAPPERS = {"command", "exec", "sudo", "nohup", "time", "builtin"}


def strip_prefix(words):
    """Drop leading VAR=value words and wrappers (env, command, sudo...).

    Returns (assignments, remaining_words) where assignments is a list of
    (name, value) pairs seen before the real command.
    """
    assigns, i = [], 0
    while i < len(words):
        w = words[i]
        name, eq, value = w.partition("=")
        if eq and name.replace("_", "a").isalnum() and not name[:1].isdigit():
            assigns.append((name, value))
            i += 1
        elif w == "env":
            i += 1
            while i < len(words) and words[i].startswith("-"):
                i += 2 if words[i] in ("-u", "--unset", "-C", "--chdir", "-S") else 1
        elif w in _WRAPPERS:
            i += 1
        else:
            break
    return assigns, words[i:]

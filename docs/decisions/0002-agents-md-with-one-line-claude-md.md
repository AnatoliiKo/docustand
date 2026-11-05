# 0002. AGENTS.md with a one-line CLAUDE.md

Date: 2026-11-05
Status: accepted

## Context

- Agent rules must be in git and readable by several agent tools.
- Claude Code stops reading `AGENTS.md` by itself when `CLAUDE.md` or `CLAUDE.local.md` is next to it.
- Options: `CLAUDE.md` outside git; `AGENTS.md` and `CLAUDE.md` in git; only `AGENTS.md`.

## Decision

- `AGENTS.md` holds the rules and is committed.
- `CLAUDE.md` is committed and contains one line: `@AGENTS.md`.
- Personal rules go to `CLAUDE.local.md` or the user-level `CLAUDE.md`.

## Rejected

- `CLAUDE.md` outside git: the rules do not travel with the repository.
- Only `AGENTS.md`: Claude Code does not read it when a local `CLAUDE.local.md` exists.

## Consequences

- The one-line `CLAUDE.md` works in every case.
- Other agent tools read `AGENTS.md` directly.
- The check on `AGENTS.md` size runs before commit.

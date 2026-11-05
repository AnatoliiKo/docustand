# 0009. Agent memory disabled

Date: 2026-11-05
Status: accepted

## Context

- Hidden memory makes a project non-transferable: knowledge sits outside the repository.
- Options: a memory MCP server; built-in auto memory.

## Decision

- Both are disabled.
- `repo-init` sets `autoMemoryEnabled: false` without a question.
- Knowledge lives in the repository: `README.md`, `AGENTS.md`, `docs/`, ADRs.

## Rejected

- Memory MCP server: state outside git.
- Built-in auto memory: state outside git.

## Consequences

- A new agent starts with the repository only.
- The handoff check asks an agent that sees one repository the six questions.
- Personal rules go to `CLAUDE.local.md` or the user-level `CLAUDE.md`.

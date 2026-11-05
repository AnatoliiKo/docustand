# 0003. Tasks in a repository file

Date: 2026-11-05
Status: accepted

## Context

- Project state and open tasks must be visible next to the code.
- Options: GitHub Issues; a file in the repository.

## Decision

- Tasks and state live in `docs/tasks.md`.
- The format of `docs/tasks.md` is checked before commit.
- The report pull request edits the backlog in the same file.

## Rejected

- GitHub Issues: state lives outside the repository and is not visible to an agent that reads one checkout.

## Consequences

- A new person or agent answers "what is in progress" from the repository.
- Task changes appear in pull request diffs.
- Concurrent edits can conflict in one file.

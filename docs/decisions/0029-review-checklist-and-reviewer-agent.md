# 0029. Review checklist and reviewer agent

Date: 2026-11-13
Status: accepted

## Context

- Rule 1 of the owner's hygiene rules asks for a check or a review checklist line for every rule.
- Rules on comment content, comment share, ADR content, duplicated facts, abstractions and existing solutions have no check; the audit of `cinema-ops` found violations of each.
- `AGENTS.md` pointed to `/docustand:pr-ready`, and the plugin had no such skill.

## Decision

- `AGENTS.md` of the template holds the section `Review checklist`: one line per rule without a check.
- The checklist lives in the repository, so a detached repository and a human reviewer keep it.
- The plugin skill `pr-ready` runs the checks, passes the branch diff to the agent `reviewer` and records the verified commit with `mise run pr-ready`.
- The agent `reviewer` is read-only, reads the checklist from `AGENTS.md` of the project and returns blocking findings and recommendations with a path and a line.
- The reviewer gets the diff and the task, not the conversation that produced the change.

## Rejected

- The checklist in `.github/pull_request_template.md`: the PR description is limited to 20 lines.
- A separate checklist document: `docs/` holds four standard documents, see ADR 0024.
- The checklist inside the agent: the rules would live in two places and leave the repository on detach.
- A CI check that every checklist box is ticked: an author ticks boxes without reviewing.

## Consequences

- `AGENTS.md` grows by 8 lines; `check-agents-md` keeps its 150-line limit, and `cinema-ops` reaches 148 lines.
- A repository updated to 0.9.0 gets the section through `copier update`.
- A finding of the reviewer is advice for the owner: no gate blocks a pull request on it.

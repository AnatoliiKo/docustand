# 0001. OpenSpec for behaviour

Date: 2026-11-05
Status: accepted

## Context

- Behaviour needs a specification that stays current as the code changes.
- Candidates: Spec Kit, Kiro, OpenSpec.

## Decision

- OpenSpec describes behaviour on the full level.
- A change delta merges into the shared specification in `openspec/specs/`.
- The base level has no OpenSpec. A change is a task in `docs/tasks.md` and a pull request.
- Deviation from the OpenSpec default flow: archiving happens inside the pull request.
- The `changes/archive/` directory does not exist.
- `openspec archive` runs before merge, then the change folder is deleted.

## Rejected

- Spec Kit: no living specification.
- Kiro: no living specification.

## Consequences

- Only OpenSpec keeps a living specification.
- The merged pull request already contains the updated `openspec/specs/`.
- The repository holds no archive of finished changes. History lives in git.

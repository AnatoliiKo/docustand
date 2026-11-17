# 0034. Automerge of non-major updates

Date: 2026-11-17
Status: accepted
Supersedes: [ADR 0018](0018-weekly-grouped-dependency-updates.md)

## Context

Weekly grouped pull requests need a manual merge in every repository. With several projects the merges decide whether dependencies stay current.

## Decision

- Minor, patch, pin and digest updates stay in one weekly pull request on the schedule of ADR 0018.
- Renovate merges the weekly pull request after the required checks pass and the update is 3 days old.
- Lock file maintenance pull requests merge after the required checks pass; the age wait does not apply to them (ADR 0032).
- Major updates stay outside the automatic merge and wait for approval on the dependency dashboard (ADR 0023).
- Pull requests of the `copier` manager are never merged automatically (ADR 0028).
- A repository without `standard-ci` on its branches keeps the automatic merge off.
- Vulnerability fixes and `copier` updates keep coming at once and outside the group.

## Rejected

- Platform automerge: needs branch protection that private Free repositories lack.
- Automerge of major updates: breaking changes pass without a decision.
- Dependabot: [ADR 0011](0011-renovate-over-dependabot.md).

## Consequences

- A broken update reaches the branch when the tests miss it; test quality gates the merge.
- The weekly report lists merged updates.
- The owner no longer merges the weekly pull request.

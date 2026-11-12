# 0023. Major updates after dashboard approval

Date: 2026-11-12
Status: accepted

## Context

- [ADR 0018](0018-weekly-grouped-dependency-updates.md) opens one pull request per major update at any time.
- In `cinema-ops` five major pull requests opened within 24 h: Node 26, pnpm 12, TypeScript 7, GitHub Actions v7 and `@types/node` 26.
- Three of them failed CI, and one changed the runtime of the deployed agent against an accepted ADR.
- A major update needs a decision of the owner before any work on it.

## Decision

- Major updates wait for approval in the Renovate Dependency Dashboard issue; the rule is `dependencyDashboardApproval` for `matchUpdateTypes: major`.
- The owner ticks an update in the dashboard; Renovate then opens its pull request.
- Non-major updates keep the weekly group of ADR 0018.
- Vulnerability fixes keep opening at once: Renovate does not apply dashboard approval to them.

## Rejected

- One pull request per major update: the pull request list fills with updates nobody decided to take, and a merge of a red or unplanned major is one click away.
- Majors in the weekly group: one breaking major blocks every minor and patch update.
- Approval for all updates: minor and patch updates stop arriving unless the dashboard is read every week.

## Consequences

- The pull request list holds the weekly group, vulnerability fixes, template updates and approved majors.
- Pending majors are listed in the Dependency Dashboard issue and in nothing else; the owner reads it to plan upgrades.

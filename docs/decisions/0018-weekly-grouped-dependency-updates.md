# 0018. Weekly grouped dependency updates

Date: 2026-11-11
Status: accepted

## Context

- [ADR 0011](0011-renovate-over-dependabot.md) sets one Renovate pull request per dependency and auto-merge of patches.
- Every pull request runs `standard-ci`. In `cinema-ops` one run takes 7 billed minutes.
- A private repository on the GitHub Free plan has 2000 Actions minutes a month.
- `cinema-ops` has 51 npm dependencies. One pull request per dependency costs 100–400 minutes a month.

## Decision

- Minor, patch, pin and digest updates go into one pull request `non-major dependencies` on Monday, 00:00–05:59 UTC.
- The weekly pull request waits for the owner's merge; no rule enables auto-merge.
- Major updates keep one pull request per dependency or per group, at any time.
- Vulnerability fixes and `copier` updates of the template come at once and outside the group.
- This decision replaces the auto-merge of patches in ADR 0011.

## Rejected

- One pull request per dependency with auto-merge of patches: one CI run per dependency.
- A weekly group with auto-merge: the group holds minor updates, which need review.
- A monthly group: a bug fix waits up to a month, and the pull request grows.

## Consequences

- Non-major updates cost about 5 CI runs a month.
- The owner merges one pull request a week.
- A failing update blocks the whole group until it is fixed or excluded in the pull request.

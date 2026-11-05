# 0011. Renovate over Dependabot

Date: 2026-11-05
Status: accepted

## Context

- Dependencies and the template version need automatic update pull requests.
- On the GitHub Free plan Dependabot auto-merge does not work.
- Options: Dependabot; Renovate.

## Decision

- Renovate updates dependencies and the template.
- Settings: grouping, `minimumReleaseAge` of at least 3 days, auto-merge of patches on green CI.
- Vulnerability alerts open pull requests at once through `vulnerabilityAlerts`, without `minimumReleaseAge`.
- The `copier` manager raises `_commit` in `.repo.yaml`.
- GitHub Dependabot alerts stay enabled as the alert source. They cost no Actions minutes.

## Rejected

- Dependabot for updates: no auto-merge on Free.

## Consequences

- One tool updates dependencies and the template.
- Stack exceptions live in the stack profile.
- `renovate.json` is a protected file.

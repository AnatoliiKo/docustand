# 0012. GitHub-hosted runners

Date: 2026-11-05
Status: accepted

## Context

- CI needs runners.
- Free plan: 2000 minutes per month across private repositories of an account. Team plan: 3000.
- Options: GitHub-hosted runners; a self-hosted runner.

## Decision

- CI uses GitHub-hosted runners.
- Workflows use `concurrency` with `cancel-in-progress` and path filters.
- Minute use is measured in the pilot.
- If minutes run short: path filters and fewer heavy jobs first, then an owner decision between a paid plan and a self-hosted runner.

## Rejected

- Self-hosted runner: permanent load on owner hardware.

## Consequences

- CI stops when minutes run out.
- The report warns about token expiry and disabled vulnerability alerts.

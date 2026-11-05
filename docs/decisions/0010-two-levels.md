# 0010. Two levels

Date: 2026-11-05
Status: accepted

## Context

- A small project does not repay the full set of tools.
- Options: everything for everyone; levels.

## Decision

- The level is the `level` field in `.repo.yaml`: base or full.
- Base: README, `AGENTS.md`, ADRs, `docs/tasks.md`, hk, CI, bypass protection, comment rules, deterministic report.
- Full: base plus OpenSpec, Danger, Vale, LLM reports.
- The API contract check depends on the `contract` field, not on the level.
- Changing the level is `copier update --data level=<value>`.

## Rejected

- Everything for everyone: cost exceeds value for a small project.

## Consequences

- The deterministic report runs on both levels and keeps the bypass count on the Free plan.
- A pilot shows what moves between levels.

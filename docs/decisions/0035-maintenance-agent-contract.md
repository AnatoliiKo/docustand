# 0035. Maintenance agent contract

Date: 2026-11-17
Status: accepted

## Context

Documents drift from the code, and old violations stay in `.baselines/` because only the owner removes them. [ADR 0027](0027-hygiene-sections-of-the-report.md) reports the drift; nothing acts on it. A fixed agent in every project costs tokens and secrets that personal projects do not need.

## Decision

- The answers `maintain_adapter` (`none` or an adapter name) and `maintain_schedule` (`off`, `monthly`, `weekly`) default to `none` and `off`.
- Jobs form the contract, independent of an agent: `docs-drift`, `baseline-burndown`, `dead-code`. A job states its name, its instruction file and the paths it may change.
- Every job ends in a pull request. No job merges or pushes to a protected branch.
- An adapter lives in `.maintain/<adapter>/` with a `README` (what the folder holds, how to run it) and an entry point `run`. Another agent is another folder; the contract stays.
- Adapters shipped: `manual` (local run) and one CI adapter. The CI adapter uses an existing maintained action when one fits; a custom runner needs its own ADR.

## Rejected

- One agent hard-wired into the template: ties every project to one vendor.
- The agent in every project: cost and secrets without value for rarely edited projects.
- Direct pushes by the agent: removes the review.

## Consequences

- A project that changes often enables a schedule; a project that changes rarely stays at `none` or runs `manual`.
- The `README` of `.maintain/` and the folder need entries in the Markdown and root file checks.
- The CI adapter adds one secret per repository; `docs/access.md` lists it.

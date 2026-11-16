## In progress

### Implement the owner's hygiene rules

- Goal: each of the 25 rules of 2026-11-11 has a check, a number or a review checklist line.
- Done when: `cinema-ops` passes `mise run check` on the rules of phases 1–3 with every `.baselines/` entry outside `betterleaks.ignore` dated, and the review checklist lists the unchecked rules.
- Stopped at: the review checklist in `v0.9.0`; dated size and ESLint baselines in `v0.10.0`.
- Next: `cinema-ops` on `v0.10.0` passes `mise run check`.
- Refs: ADR 0021, ADR 0029, ADR 0030, `docs/temp/hygiene-rules-plan.md`.

## Backlog

- Migrate the `infrastructure` project to the repository standard — second pilot project, results go to `docs/pilot-log.md`.
- Review changes to protected files in #2 — they change how checks run outside a template update.

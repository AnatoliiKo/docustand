## In progress

### Implement the owner's hygiene rules

- Goal: each of the 25 rules of 2026-11-11 has a check, a number or a review checklist line.
- Done when: `cinema-ops` passes `mise run check` on the rules of phases 1–3 with every `.baselines/` entry dated, and the review checklist lists the unchecked rules.
- Stopped at: phases 1–2 in `v0.7.1`, hygiene sections of the report (rule 25) in `v0.8.0`, the review checklist and the `reviewer` agent in `v0.9.0`; every `.baselines/` file of `cinema-ops` except `betterleaks.ignore` is empty.
- Next: expiry dates of the size, secrets and ESLint baselines.
- Refs: ADR 0021, ADR 0029, `docs/temp/hygiene-rules-plan.md`.

## Backlog

- Migrate the `infrastructure` project to the repository standard — second pilot project, results go to `docs/pilot-log.md`.
- Review changes to protected files in #2 — they change how checks run outside a template update.

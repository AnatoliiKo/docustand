## In progress

### Migrate `cinema-ops` to the repository standard

- Goal: first pilot on a repository with code; results go to `docs/pilot-log.md`.
- Done when: the success criteria of section 12 of the specification pass in `cinema-ops`.
- Stopped at: all criteria pass except the Renovate update; the Renovate app had no access to `cinema-ops`, access granted on 2026-11-11, first Renovate PR 103 opened; summary in `docs/pilot-log.md`.
- Next: the next docustand release opens a `copier update` PR in `cinema-ops`; merge it by README section `Update`.
- Refs: `docs/temp/pilot-cinema-ops-plan.md`, `cinema-ops` PR 83–102.

### Implement the owner's hygiene rules

- Goal: each of the 25 rules of 2026-11-11 has a check, a number or a review checklist line.
- Done when: `cinema-ops` passes `mise run check` on the rules of phases 1–3 with every `.baselines/` entry dated, and the review checklist lists the unchecked rules.
- Stopped at: phase 1 in `v0.4.0`: `check-root`, `check-adr`, `check-adr-history`, history rules of `check-comments`, `.baselines/`.
- Next: apply `v0.4.0` to `cinema-ops`; phase 2: standard files to `.config/`, old baselines to `.baselines/`, one source of truth, `deploy/`.
- Refs: ADR 0021, `docs/temp/hygiene-rules-plan.md`.

## Backlog

- Migrate the `infrastructure` project to the repository standard — second pilot project, results go to `docs/pilot-log.md`.

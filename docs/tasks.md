## In progress

### Implement the owner's hygiene rules

- Goal: each of the 25 rules of 2026-11-11 has a check, a number or a review checklist line.
- Done when: `cinema-ops` passes `mise run check` on the rules of phases 1–3 with every `.baselines/` entry outside `betterleaks.ignore` dated, and the review checklist lists the unchecked rules.
- Stopped at: `cinema-ops` `dev` at `4be090a` on template commit `01fb4fd` passes every step of `mise run check` except `rumdl` (MD076, 122 findings in 8 ADR files); `test` passes 1483 of 1483 at load average up to 22.8; the row of 2026-11-25 is in `docs/pilot-log.md`.
- Next: close the Backlog item of `cinema-ops` «Fix the 122 MD076 findings of rumdl 0.3.5 in 8 ADR files», then rerun `mise run check` there; the worker count of `test` stays at the default, the owner rejected a limit on 2026-11-25.
- Refs: ADR 0021, ADR 0029, ADR 0030, `docs/temp/hygiene-rules-plan.md`.

### Add project language setting

- Goal: one `language` answer (`ru`, `en`, `auto`) sets the language of comments and documents; no mixed languages in one project.
- Done when: `check-comments` fails on a comment outside `language`; `auto` resolves to `ru` or `en` in `.repo.yaml` during `repo-init` and asks the owner when neither language exceeds 80 % of the measured blocks; the rendered `AGENTS.md` follows `language`; tests cover the three values; `cinema-ops` passes `mise run check` with the answer set.
- Stopped at: `cinema-ops` `dev` at `4be090a` on template commit `01fb4fd` with `language: en` fails only in `rumdl` (MD076, 122 findings in 8 ADR files, `rumdl` 0.3.5); `check-md-language`, `check-comments` and `test` pass, load average 5.1 to 22.8; the row is in `docs/pilot-log.md`.
- Next: close the Backlog item of `cinema-ops` «Fix the 122 MD076 findings of rumdl 0.3.5 in 8 ADR files» and rerun `mise run check` there; close the task when it passes.
- Refs: ADR 0025, ADR 0033, `template/.mise/tasks/check-comments`.

### Add the maintenance agent contract

- Goal: a project runs scheduled maintenance jobs through an agent adapter that the owner picks per project.
- Done when: `.repo.yaml` accepts `maintain_adapter` and `maintain_schedule` with `none` and `off` as defaults; the adapter `manual` and one CI adapter run `docs-drift` and `baseline-burndown` on `cinema-ops` and open a PR; the adapter folder holds a `README` with the run command.
- Stopped at: the contract and the adapter `manual` are in the template and covered by tests; they did not run on `cinema-ops`, no PR is open and the template has no CI adapter.
- Next: run `docs-drift` and `baseline-burndown` on `cinema-ops` with the `manual` adapter; then the CI adapter of ADR 0035 with the action chosen by the owner.
- Refs: ADR 0027, ADR 0035, PR 24, `report_schedule` in `copier.yml`.

## Backlog

- Migrate the `infrastructure` project to the repository standard — second pilot project, results go to `docs/pilot-log.md`.
- Review changes to protected files in #2 — they change how checks run outside a template update.
- Review changes to protected files in #14 — they change how checks run outside a template update.
- Update the pins of docustand tools through Renovate and release automatically — tools of projects move only with a docustand release.
- Configure `typos` in the template to skip the `_commit` value of `.repo.yaml` — a commit hash in that value reads as a typo and fails the commit hook at random.

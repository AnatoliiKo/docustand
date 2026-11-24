## In progress

### Implement the owner's hygiene rules

- Goal: each of the 25 rules of 2026-11-11 has a check, a number or a review checklist line.
- Done when: `cinema-ops` passes `mise run check` on the rules of phases 1–3 with every `.baselines/` entry outside `betterleaks.ignore` dated, and the review checklist lists the unchecked rules.
- Stopped at: `cinema-ops` on `v0.10.2` passes every step of `mise run check` except `test`, which times out at 5000 ms under host load; passes with `--maxWorkers=2`; the row is in `docs/pilot-log.md`.
- Next: rerun `mise run check` in a clean clone of `cinema-ops` on an idle host, or set the worker count of the `test` step in `cinema-ops`.
- Refs: ADR 0021, ADR 0029, ADR 0030, `docs/temp/hygiene-rules-plan.md`.

### Add project language setting

- Goal: one `language` answer (`ru`, `en`, `auto`) sets the language of comments and documents; no mixed languages in one project.
- Done when: `check-comments` fails on a comment outside `language`; `auto` resolves to `ru` or `en` in `.repo.yaml` during `repo-init` and asks the owner when neither language exceeds 80 % of the measured blocks; the rendered `AGENTS.md` follows `language`; tests cover the three values; `cinema-ops` passes `mise run check` with the answer set.
- Stopped at: not started; ADR 0025 fixes English as the only comment language.
- Next: implement the `language` answer and the `check-comments` rule from ADR 0033.
- Refs: ADR 0025, ADR 0033, `template/.mise/tasks/check-comments`.

### Add the maintenance agent contract

- Goal: a project runs scheduled maintenance jobs through an agent adapter that the owner picks per project.
- Done when: `.repo.yaml` accepts `maintain_adapter` and `maintain_schedule` with `none` and `off` as defaults; the adapter `manual` and one CI adapter run `docs-drift` and `baseline-burndown` on `cinema-ops` and open a PR; the adapter folder holds a `README` with the run command.
- Stopped at: not started.
- Next: implement the answers, the jobs and the adapters from ADR 0035.
- Refs: ADR 0027, ADR 0035, `report_schedule` in `copier.yml`.

## Backlog

- Migrate the `infrastructure` project to the repository standard — second pilot project, results go to `docs/pilot-log.md`.
- Review changes to protected files in #2 — they change how checks run outside a template update.
- Review changes to protected files in #14 — they change how checks run outside a template update.
- Update the pins of docustand tools through Renovate and release automatically — tools of projects move only with a docustand release.

## In progress

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

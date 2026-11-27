## In progress

### Add self-hosted runners for private repositories

- Goal: CI of private projects runs on the owner's machines and stays within the $12 of included GitHub Actions compute per month.
- Done when: the template answer `ci_runner` sets `runs-on` of `standard-ci` and `standard-report`; a runner container on the VM `docker` runs one job at a time under the limits of ADR 0036 and re-registers after each job; `standard-ci` of `cinema-ops` passes on it; the Actions usage of `cinema-ops` for one month is under $2.
- Stopped at: ADR 0036 sets the image, the limits and the jobs that move. Actions of private repositories stopped on 2026-11-27: the $12 of included compute is used and the account has no payment method.
- Next: the owner creates the fine-grained token of `docs/access.md`; then the runner stack on the VM `docker`, the answer `ci_runner` and `runs-on` of `cinema-ops`, `stockpit` and `manifold`.
- Refs: ADR 0036, `template/.github/workflows/standard-ci.yml.jinja` and the report workflow of the template.

### Set up `cinema-ops` as the reference repository

- Goal: one repository shows the whole standard working before docustand reaches other projects.
- Done when: each condition holds and has a row in `docs/pilot-log.md`: `cinema-ops` is on the latest release and `mise run check` passes 3 times in a row with green CI; a Renovate template update merged without the owner; the scheduled report ran on its own; `docs-drift` and `baseline-burndown` ran on schedule and each opened a PR; `.baselines/` holds only `betterleaks.ignore`; a fresh clone passes `mise install && mise run check`; an agent without context answers the six questions of `README.md`.
- Stopped at: `cinema-ops` is on `v0.11.0` (PR 139); `.baselines/` holds only `betterleaks.ignore`; `mise run check` passed once and failed once in `apps/agent/src/station/settings.test.ts` under load.
- Next: the self-hosted runner task above; then automatic merge of template updates and the maintenance task below.
- Refs: ADR 0027, ADR 0034, ADR 0035, `cinema-ops` PR 139 and PR 140.

### Add the maintenance agent contract

- Goal: a project runs scheduled maintenance jobs through a model provider that the owner picks per project; without a provider every other part of the standard works.
- Done when: `.repo.yaml` accepts `maintain_adapter` and `maintain_schedule` with `none` and `off` as defaults; the `manual` adapter and the `manifold` provider run `docs-drift` and `baseline-burndown` on `cinema-ops` and open a PR; the adapter folder holds a `README` with the run command.
- Stopped at: the contract and the adapter `manual` are in the template and covered by tests; they did not run on `cinema-ops`. The owner chose a provider contract of the template instead of one CI action: a command reads a JSON request and writes JSON edits, and docustand applies the edits.
- Next: run `docs-drift` and `baseline-burndown` on `cinema-ops` with the `manual` adapter; then an ADR on the provider contract that supersedes the CI adapter of ADR 0035; then the `manifold` provider with a scheduled workflow through Tailscale Funnel.
- Refs: ADR 0027, ADR 0035, PR 24, `protocol/v1.md` of `manifold`.

## Backlog

- Merge Renovate template updates without conflicts after green CI automatically — each release needs a manual merge in every project; it changes ADR 0034.
- Deploy the Manifold gateway on the VM `docker` and expose only its client routes through Tailscale Funnel — the maintenance workflow of GitHub Actions reaches the gateway only this way, and the worker routes stay in the VPN.
- Add a triage task that sorts every finding of a new project into tool fixes, baseline entries, code errors and owner decisions — onboarding takes days because nothing sorts the findings; test it on `manifold`.
- Replace the six migration pull requests of `repo-init` with one pull request — each step waits for the merge of the previous one; the owner allows old violations in dated baselines of that pull request; target 30 min of owner time, at most 1 h.
- Set the `repo-init` answers from the code and ask only what the code does not decide — the questions take owner time that defaults save.
- Add a `github-setup` task for vulnerability alerts, branch protection and the report secrets — each project needs these steps by hand.
- Add a Python profile — `stockpit`, `ai-investing` and the Lambda code of `infrastructure` have no stack checks.
- Add a PHP profile for Laravel — `backend-api` has no stack profile.
- Support yarn classic in the `typescript` profile — `mobile-app` uses `yarn@1.22.22`.
- Move the macOS jobs of `manifold` to the owner's Mac — a macOS minute costs $0.062 on GitHub runners.
- Add a Swift profile — `mac/` of `manifold` gets only the standard checks.
- Implement maintenance jobs started by report findings — the report lists expiring baselines and drift, and nothing acts on them.
- Migrate the `infrastructure` project to the repository standard — second pilot project, results go to `docs/pilot-log.md`.
- Review changes to protected files in #2 — they change how checks run outside a template update.
- Review changes to protected files in #14 — they change how checks run outside a template update.
- Update the pins of docustand tools through Renovate and release automatically — tools of projects move only with a docustand release.

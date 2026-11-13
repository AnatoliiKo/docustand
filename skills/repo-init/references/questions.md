# Questions

<!-- doc-paths: another repository -->

One message with every applicable question, before any change.
When the question tool takes fewer questions per call than apply, ask them in consecutive calls without changing anything in between.
Each question names what reconnaissance found, then numbered options.
Each option says what it gives and what it costs; the recommended option is marked «(recommended)».
A question whose condition does not hold is not asked; a question `.repo.yaml` or an ADR already answers is not asked.

## Not asked: mandatory

Copier, hk and the tools through mise; the structure, the checks and the profile configs; `autoMemoryEnabled: false`; `team: solo`; vulnerability alerts.

## The list

| Question | Asked when | Answer goes to |
|---|---|---|
| Level: base or full | always | `level` |
| Report schedule: monthly, weekly (recommended), twice a week, off | always | `report_schedule` |
| Is the detected stack right? | the profile is ambiguous or missing | `stack` |
| Architecture: confirm the detected methodology, or decide whether one is needed | code repositories; not for infrastructure or documentation | `architecture`, ADR |
| Own configs found: keep the differences with a reason in `overrides`, or bring them to the template | the project already has configs that the template also brings | `overrides` or the template file |
| Is the repository part of a multi-repository system? Which repositories? Which is the center? | references to other repositories found, or sibling repositories that reference this one; siblings alone do not count; after «no», no other multi-repository question | `system` |
| Is there an API? Provider or consumer? For a new project: the contract approach | an API or a client of one found | `contract`, ADR |
| Branch protection: on which branches CI is required | the plan allows protection; otherwise a warning instead of the question and the long-lived branches as the answer | `required_ci_branches` |
| What to do with files outside git next to the repository | such files found | inventory (migration step 1) |
| Is the system deployed? | code with deploy signs (Dockerfile, deploy workflow, infrastructure code) | `deployed` (adds `docs/operations.md`) |
| Report secrets: set `REPORT_APP_CLIENT_ID` and `REPORT_APP_PRIVATE_KEY` now | `report_schedule` is not `off` | GitHub secrets, `docs/access.md` |

## Option texts

**Level.**

1. Base (recommended): README, `AGENTS.md`, ADRs, `docs/tasks.md`, hk, CI, bypass protection, comment rules, deterministic report. Costs: no OpenSpec, Danger, Vale or LLM reports.
2. Full: base plus OpenSpec, Danger, Vale and LLM reports in the summary. Not available yet: the template rejects `level: full`; choosing it now keeps `base` and the change waits for a template release.

**Report schedule.**

1. Weekly (recommended for a team): bypasses, red merges, protected-file changes and stale pull requests surface within a week. Costs: one scheduled workflow run a week.
2. Monthly (enough for a solo repository that changes rarely): fewer Actions minutes. Costs: findings arrive up to a month late.
3. Twice a week: the fastest feedback. Costs: twice the minutes of weekly.
4. Off: no report workflow. Costs: on Free without branch protection, nothing counts bypasses any more.

**Branch protection** (default: the default branch):

1. `<default branch>` only (recommended): a red CI blocks merges there. Costs: an urgent fix also waits for CI.
2. `<default branch>` and the other long-lived branches found: the same on each. Costs: every branch waits for CI.

Without protection on the plan: no question, the warning «CI only reports; local hooks are the only blocking layer».
The answer is still passed as `--data 'required_ci_branches=[<default branch>, <other long-lived branches>]'`: the branches also select where `standard-ci` runs, and the template default `[main]` leaves a repository with another default branch without CI.

**Stack.** The template offers the profiles in `${CLAUDE_PLUGIN_ROOT}/profiles/`: `terraform` and `typescript`.

1. The detected profiles are right (recommended when `detect-stack` evidence matches the manifests): their tools and checks are added. Costs: the profile tools are installed by mise.
2. Different profiles: name them from the available list. Costs: checks for what the code does not contain, or none for what it does.

Code without a profile (for example PHP): record nothing in `stack` for it and tell the owner that a new stack needs a profile in docustand first («new stack — profile first»). Until then the standard checks run, and the stack's own linters, types and tests do not.

**Multi-repository system** (only when references were found, not for siblings alone):

1. Not part of a system (recommended when the references are only external services): `system` stays empty. Costs: cross-repository tasks are not tracked.
2. Part of a system, this repository is the center: `system.repos` lists the others; cross-repository tasks live here. Costs: the center's report watches the whole system.
3. Part of a system, another repository is the center: `system.center` names it. Costs: cross-repository tasks are read from the center.

**API** (only when an API or a client was found):

1. Provider: the contract file lives here; `contract.role: provider`. For a new project, choose the approach: code-first (the contract is generated from code; costs: the generator in the build) or schema-first (code follows the contract; costs: the schema is written before the code).
2. Consumer: the client is generated from the provider's contract, pinned to its version; `contract.role: consumer`. Costs: a contract update is a separate PR.
3. No API contract: `contract` stays empty. Costs: no check catches a breaking API change.

**Deployed** (only for code with deploy signs):

1. Deployed: `docs/operations.md` is added for deploy, rollback, restore with the last check date and alerts. Costs: the owner keeps that file current.
2. Not deployed (recommended for libraries and tools): no operations document. Costs: none until the first deployment.

**Files outside git** (only when found; listed by name, secrets never read):

1. Into the inventory (recommended): each file gets a decision in migration step 1. Costs: one more table row per file.
2. Leave as they are: nothing changes. Costs: knowledge stays outside the repository and is lost with the machine.

**Architecture**, example:

> In `src/` there are `entities/`, `features/`, `widgets/`, `shared/` — looks like Feature-Sliced Design. `app/` is the Next.js router.
>
> 1. Yes, FSD (recommended): Steiger is added, the router is not a layer, layer violations and cross-imports fail before push.
> 2. Layers only: import directions are checked with eslint-plugin-boundaries, without slice rules.
> 3. No methodology: no architecture check; the structure is described in `docs/architecture.md`.

**Own configs**, per file listed by `merge_existing.py conflicts`:

1. Take the standard (recommended when the differences have no reason): the file matches the template and updates with it. Costs: project-specific rules in it are lost unless moved.
2. Keep own: the file stays, an `overrides` entry records the reason. Costs: every template update of this file is a manual merge.
3. Merge by hand: the standard file plus the needed project lines, with an `overrides` entry. Costs: the same update cost, smaller difference.

**Report secrets:**

1. Set them now (recommended): the report opens its PR from the first scheduled run. Costs: the owner installs the report GitHub App and provides its id and private key.
2. Later: nothing to do now. Costs: the report workflow fails until both secrets exist.

## Recording answers

- Answers of template questions go into `copier copy --data` (new, migration) or `copier update -a .repo.yaml --defaults --data` (audit).
- A decision with a reason and alternatives (architecture, contract approach, kept own config, report off) also gets an ADR in `docs/decisions/`.

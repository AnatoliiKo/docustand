# docustand

A Claude Code plugin and Copier template that brings a repository to one documentation and quality standard.

## What it is

- The repository explains itself: a new person or agent finds answers to six questions without the owner.
- The six questions: what it is, how to run it, how it is built, why it was decided so, which rules apply, what is in progress.
- The standard is delivered as files copied into the project by Copier.
- The project works without docustand and can detach from it.
- docustand connects nothing to the project: no shared workflows, no runtime dependency.
- The plugin contains skills, agents, stack profiles and the Copier template.
- Decisions are recorded in [`docs/decisions/`](docs/decisions/).

## How a project uses it

With the plugin:

```text
/docustand:repo-init
```

Without the plugin:

```sh
copier copy gh:AnatoliiKo/docustand .
```

`repo-init` modes:

| Repository state | Action |
|---|---|
| Empty | `copier copy`: structure, checks, configs, `AGENTS.md` |
| Code without the standard | Migration, one pull request per step |
| Standard installed | Audit and `copier update` to the current template version |
| Detach requested | Detach (see below) |

- `repo-init` inspects the repository first and asks only questions the code does not answer.
- Answers are stored in `.repo.yaml` (`_answers_file: .repo.yaml`).
- A repeated run reads `.repo.yaml` and does not ask again.

Files owned by the standard:

- `.mise/conf.d/standard.toml`
- `hk.pkl`
- `.mise/tasks/*`
- `.claude/hooks/*`
- `.github/workflows/standard-*.yml`

The template never creates or changes the project's `mise.toml` or the project's own workflows.

## Levels

The level is the `level` field in `.repo.yaml`.

| Level | Content | Status in this release |
|---|---|---|
| Base | README, `AGENTS.md`, ADRs, `docs/tasks.md`, hk, CI, bypass protection, comment rules, deterministic report | Supported |
| Full | Base plus OpenSpec, Danger, Vale, LLM reports | `repo-init` answers that the full level is not supported yet |

Stack profiles in this release:

| Profile | Format and lint | Types |
|---|---|---|
| Terraform | `terraform fmt`, tflint | `terraform validate` |

- The Terraform profile runs without secrets: `init -backend=false`, no `plan`.
- A new stack needs a profile first.

## Update

- Renovate with the `copier` manager opens a pull request that runs `copier update` to the new template version.
- The template version is `_commit` in `.repo.yaml`.
- Copier reapplies local changes. Conflicts are visible in the pull request.
- `.repo.yaml` differs from the Copier default `.copier-answers.yml`, so `renovate.json` lists it in `managerFilePatterns`.
- The template contains no `_tasks`, migrations or `_jinja_extensions`, so it needs no `--trust`.

Change an answer:

```sh
copier update -a .repo.yaml --defaults --data level=base
```

Change the report schedule:

```sh
copier update -a .repo.yaml --defaults --data report_schedule=monthly
```

## Detach

Detach is a `repo-init` step, not a separate command.

1. Remove `_src_path` and `_commit` from `.repo.yaml`.
2. Remove the plugin from `.claude/settings.json`.
3. Remove the docustand lines from `AGENTS.md`.
4. Delete the scheduled Claude task and its line in `docs/access.md`.

The repository keeps standard tools only: mise, hk, GitHub Actions, linters, README, ADRs.

## Requirements

| Requirement | Detail |
|---|---|
| mise | Installs Copier, hk and stack tools. `repo-init` stops and prints the install command if mise is missing |
| Trusted folder | Claude Code loads the plugin from the repository only after the folder is trusted |
| superpowers | External Claude Code plugin. `AGENTS.md` redirects its output: plans to `docs/temp/`, specifications to `openspec/changes/` |
| Git and GitHub | Copier reads the template from `gh:AnatoliiKo/docustand` without a token |

Run all checks with:

```sh
mise run check
```

## Changes

See [`CHANGELOG.md`](CHANGELOG.md).

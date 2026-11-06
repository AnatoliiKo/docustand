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

## Install

Add the marketplace and install the plugin in Claude Code:

```text
/plugin marketplace add AnatoliiKo/docustand
```

```text
/plugin install docustand@docustand
```

- A new repository needs these two commands: it has no `.claude/settings.json` that enables the plugin yet.
- A repository with the standard enables the plugin in `.claude/settings.json`; Claude Code loads it after the folder is trusted.

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

Files owned by the standard are the paths with an `ask` rule in `.claude/settings.json`:

- `.mise/conf.d/standard.toml`, `hk.pkl`, `.mise/tasks/*`, `.mise/data/*`
- `.claude/settings.json`, `.claude/hooks/*`
- `.github/workflows/standard-*.yml`, `.github/repo.schema.json`
- `.repo.yaml`, `renovate.json`
- `commitlint.config.mjs`, `typos.toml`, `.rumdl.toml`, `lychee.toml`, and `.tflint.hcl` with the Terraform stack

The `ask` list also guards the project's `mise.toml` and its own workflows, but the template never creates or changes them.

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

1. Remove `_src_path` and `_commit` from `.repo.yaml` and replace its Copier header comment.
2. Remove the `pipx:copier` line from `.mise/conf.d/standard.toml`.
3. Remove the plugin and its marketplace from `.claude/settings.json`.
4. Remove the docustand line from `AGENTS.md`.
5. Remove the `copier` manager and the standard-file `ignorePaths` from `renovate.json`.
6. Replace the `AGENTS.md` rule about changing answers with `copier update` by "Edit `.repo.yaml` by hand; the change needs the owner's approval."
7. Full level only: delete the scheduled Claude task and its line in `docs/access.md`.

The exact edits are in [`skills/repo-init/references/maintenance.md`](skills/repo-init/references/maintenance.md); `tests/integration/test_detach.py` tests steps 1-6.

The repository keeps standard tools only: mise, hk, GitHub Actions, linters, README, ADRs.

## Requirements

| Requirement | Detail |
|---|---|
| mise | Installs Copier, hk and stack tools. `repo-init` stops and prints the install command if mise is missing |
| Trusted folder | Claude Code loads the plugin from `.claude/settings.json` only after the folder is trusted; without that file, see [Install](#install) |
| superpowers | External Claude Code plugin. `AGENTS.md` redirects its output (plans, specifications) to `docs/temp/` |
| Git and GitHub | Copier reads the template from `gh:AnatoliiKo/docustand` without a token |

Run all checks with:

```sh
mise run check
```

## Development

Run Claude Code with the plugin from the working copy:

```sh
claude --plugin-dir ~/Dev/docustand
```

- `--plugin-dir` loads the plugin for one session and leaves `.claude/settings.json` as the template renders it.
- `/plugin` commands in this repository rewrite `.claude/settings.json`; restore the file with `git restore .claude/settings.json`.

## Changes

See [`CHANGELOG.md`](CHANGELOG.md).

## License

[MIT-0](LICENSE) (MIT No Attribution): copies need no copyright notice. The template does not add a license to projects.

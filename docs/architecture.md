# docustand: architecture

## Parts

| Part | Responsibility |
|---|---|
| `copier.yml`, `template/` | Copier template: questions, answers file `.repo.yaml`, files rendered into a project |
| `scripts/merge_existing.py` | Lists conflicts and merges the `.gitignore` block when the template meets an existing repository |
| `profiles/` | Stack profiles that `repo-init` reads to choose checks and answers |
| Plugin (`.claude-plugin/`, `skills/`, `agents/`) | Claude Code plugin and marketplace manifests; skills `repo-init`, `project-docs`, `quality-gates`; agent `inventory` |
| `tests/` | Unit tests render the template and run the check scripts; `tests/integration/` runs `hk` in a rendered repository |
| `docs/decisions/` | ADRs of the standard |
| Root `mise.toml`, `renovate.json` | docustand's own tools and Renovate settings; excluded from `copier update` |

## Data flows

`repo-init` to detachment:

1. `repo-init` inspects the repository and prepares answers.
2. `copier copy` renders `template/` into the project and writes `.repo.yaml`.
3. For an existing repository, `merge_existing.py conflicts` lists files that differ, then `merge` appends the missing `.gitignore` lines.
4. `mise install` installs the tools and the git hooks of `hk.pkl`.
5. Renovate raises a pull request that changes `_commit` in `.repo.yaml`, and `copier update -a .repo.yaml` brings the template files up to date.
6. Detachment removes `_src_path` and `_commit` from `.repo.yaml`, the plugin from `.claude/settings.json` and the docustand lines from `AGENTS.md`; the rendered files stay and work without docustand.

The scheduled `standard-report` workflow of a project reads the repository and opens a report issue through the report GitHub App.

## External services

| Service | Use |
|---|---|
| GitHub | Hosting, Actions, pull requests |
| Renovate GitHub App | Raises pull requests that update `_commit` and tool versions |
| Report GitHub App | Posts the scheduled report of a project |

## Data model

The data of a project is `.repo.yaml`, validated against `.github/repo.schema.json`. docustand stores no other data.

## Glossary

| Term | Meaning |
|---|---|
| Standard | The set of files and checks that `template/` renders |
| Level | `base` or `full`; only `base` is supported |
| Answers file | `.repo.yaml`, written by Copier |
| Override | An entry `{file, reason}` in `.repo.yaml` for a local deviation from a standard file |
| Detach | Removing the link to the template while keeping the files |

## Methodology

No architectural methodology is set.

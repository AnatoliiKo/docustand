# 0006. Copier for repository files

Date: 2026-11-05
Status: accepted

## Context

- Every repository needs the same workflows, configs, hook scripts and document templates.
- A project must work without docustand and must be transferable without it.
- Options: connection (shared workflows and `dangerfile` by tag, configs built in CI); copy with a custom builder; copy with the Copier templating tool.

## Decision

- Files arrive as a copy through `copier copy`.
- The answers file is `.repo.yaml` (`_answers_file: .repo.yaml`).
- Updates arrive as Renovate pull requests that run `copier update`.
- Copier reapplies local changes. Conflicts are visible in the pull request.
- The template does not use `_tasks`, migrations or `_jinja_extensions`. They need `--trust`, which cloud Renovate does not grant.
- `renovate.json` lists `.repo.yaml` in `managerFilePatterns`.
- The template never creates or changes the project's `mise.toml` or its own workflows.
- Standard-owned files: `.mise/conf.d/standard.toml`, `hk.pkl`, `.mise/tasks/*`, `.claude/hooks/*`, `.github/workflows/standard-*.yml`.

## Rejected

- Connection: the repository cannot be transferred without docustand.
- Custom builder: violates the rule "ready-made first".

## Consequences

- The repository works without docustand and detaches by removing `_src_path` and `_commit`.
- Local deviation from a template file is a visible diff.
- The template is limited to Copier features that need no trust.

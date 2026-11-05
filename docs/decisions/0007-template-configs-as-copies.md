# 0007. Template configs as copies

Date: 2026-11-05
Status: accepted

## Context

- Linter, formatter, analyzer, commitlint, typos, knip and Vale need configs.
- Some tools have no `extends` mechanism.
- Options: own configs per project; inheritance by each tool; a copy from the template.

## Decision

- Configs arrive as ready files from the Copier template.
- A project without own rules keeps files identical to the template.
- A local deviation edits a protected file and needs an `ask` rule, a report line and a reason in `overrides`.
- `copier update` keeps the deviation or shows a conflict in the pull request.

## Rejected

- Own configs per project: drift.
- Tool inheritance: unavailable for tools without `extends`.

## Consequences

- One mechanism covers every tool.
- A deviation is visible in the diff.
- Architecture check configs are written per project, not copied: layers differ between projects.

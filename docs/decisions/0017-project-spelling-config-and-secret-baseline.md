# 0017. Project spelling config and secret scan baseline

Date: 2026-11-09
Status: accepted

## Context

- The migration of `cinema-ops` found 26 thousand lines of `typos` output in test fixtures: mail, DCP XML, HTML pages and binary sync state of external systems.
- The same migration found about 70 `betterleaks` findings without a real secret: test passwords, i18n labels such as `auth.password`, a `NO_PASSWORD` constant, base64 in a mail fixture.
- `typos.toml` was a template file: a project could not exclude its fixtures without an entry in `overrides`.
- The standard had no baseline for the secret scan; inline `betterleaks:allow` comments spread over the code and are not counted.
- [0016](0016-project-owned-check-configs.md) makes check configs that depend on the project layout project-owned and protected.

## Decision

- `typos.toml` is written once by the template and belongs to the project, as in [0016](0016-project-owned-check-configs.md); it excludes external data, never source code.
- `.betterleaksignore` is a baseline of every stack: one fingerprint `<path>:<rule>:<line>` per known finding, read by `betterleaks` from the repository root.
- Both files are protected: an `ask` rule in `.claude/settings.json` and the protected section of the report.
- `check-baseline` fails when `.betterleaksignore` gets more entries than at the base; a moved entry keeps the count.

## Rejected

- `betterleaks:allow` comments in the code: they are not counted and need no approval.
- An allowlist in a `betterleaks` config by path or regex: it hides future secrets in the same files.
- Exclusions in the template `typos.toml`: project data differs per project.

## Consequences

- An edit above a known finding moves its line; the entry is updated in the same commit, and the count stays.
- A new finding fails the commit until it is removed or the owner approves a new entry.

# 0013. Public plugin repository

Date: 2026-11-05
Status: accepted

## Context

- Copier and Renovate fetch the template from every account and organization.
- Options: private repository; public repository.

## Decision

- The plugin repository `AnatoliiKo/docustand` is public.
- The template is read without a token: `copier copy gh:AnatoliiKo/docustand`.
- The plugin is loaded by a relative path inside the marketplace repository, without `claude plugin install`, once the folder is trusted.
- The repository follows its own standard and keeps a `CHANGELOG.md`.

## Rejected

- Private repository: Copier and Renovate need a token in each consuming account.

## Consequences

- The repository holds no secrets, no owner-specific data and no project-specific names.
- Tokens used by workflows are workflow tokens, not template-read tokens.
- Cloud Claude sessions do not load the plugin. Protective hooks live in the project `.claude/settings.json`.

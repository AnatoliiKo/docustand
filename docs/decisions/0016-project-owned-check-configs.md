# 0016. Project-owned check configs and the formatter

Date: 2026-11-07
Status: accepted

## Context

- Section 9 of the specification: configs of checks come from the template as ready files.
- The `typescript` profile ([0014](0014-typescript-profile-as-base-layer.md), [0015](0015-typescript-profile-dependencies.md)) meets configs that depend on the project layout: ESLint rules of the project, knip entries and workspaces, dependency-cruiser layers, Steiger.
- Prettier options are a code style, not a quality gate.

## Decision

- `eslint.project.mjs`, `knip.json` and `.dependency-cruiser.cjs` are written once by the template and belong to the project, because entries, workspaces and layers differ per project.
- They are protected like the configs of architecture checks: an `ask` rule in `.claude/settings.json` and the protected section of the report; Steiger configs too.
- The standard part stays in template files the project cannot weaken: `eslint.config.mjs` applies its rules last and drops global ignores of the project; `.dependency-cruiser.cjs` extends `.dependency-cruiser.standard.cjs`.
- The template brings no Prettier config; the project config or the Prettier defaults apply, and template files are excluded from the `prettier` step.

## Rejected

- Template-owned knip and dependency-cruiser configs: every project would deviate from them through `overrides`.
- A Prettier config in the template: it imposes a style, and the formatter already fails on unformatted code with any config.

## Consequences

- A change of these files needs the owner's approval, and the report lists it.
- Migration merges the standard entries into the own configs (`profiles/typescript.md`, «Migration notes»).

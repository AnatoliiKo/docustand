# 0015. Dependencies of the TypeScript profile

Date: 2026-11-07
Status: accepted

## Context

- The `typescript` profile ([0014](0014-typescript-profile-as-base-layer.md)) needs tools for the quality rules of section 9 of the specification.
- "Well-maintained" requires a release within 12 months and an organization or several maintainers.
- npm registry data as of 2026-11-06:

| Package | Version, date | License | Maintainers | Rule |
|---|---|---|---|---|
| `eslint`, `typescript-eslint` | 10.14.0, 8.72.1, 2026-10 | MIT | organization | passes |
| `prettier` | 3.9.10, 2026-10-10 | MIT | 11 | passes |
| `dependency-cruiser` | 18.7.2, 2026-11-02 | MIT | 2 | passes |
| `steiger`, `@feature-sliced/steiger-plugin` | 0.9.0, 0.8.2, 2026-11-01 | MIT | organization | passes |
| `eslint-plugin-sonarjs` | 4.2.2, 2026-09-28 | LGPL-3.0-only | SonarSource, 5 | passes; LGPL |
| `knip` | 6.44.1, 2026-10-31 | ISC | 1 | fails: one maintainer |
| `jscpd` | 5.4.2, 2026-10-20 | MIT | 1 | fails: one maintainer |
| `eslint-plugin-react` | 7.37.5, 2025-04-03 | MIT | jsx-eslint, 2 | fails: release older than 12 months |

## Decision

- ESLint with `typescript-eslint`, Prettier, dependency-cruiser and Steiger are project devDependencies.
- `eslint-plugin-sonarjs` is accepted for `sonarjs/cognitive-complexity`, as a devDependency only; LGPL-3.0-only is allowed for devDependencies ([licenses](../../skills/repo-init/references/licenses.md)).
- `knip` is an exception to the maintenance rule: frequent releases, no maintained alternative (`ts-prune` 2021-12, `unimported` deprecated, `ts-unused-exports` 2024-11, `depcheck` 2023-10), development only.
- `jscpd` is an exception to the maintenance rule: CI only, one standalone binary pinned in `.mise/conf.d/standard.toml`, the project holds only `.jscpd.json`. Agents tend to copy code, so the check stays.
- If `knip` or `jscpd` stops releasing, one commit removes its check.
- `react/no-multi-comp` is not part of the profile: Node projects without React get the profile too, and `check-size` with `max-lines-per-function` limits large components. A project with React enables the rule in `eslint.project.mjs`.

## Rejected

- `eslint-plugin-react` in the profile: the release is older than 12 months, and Node projects would install React rules.
- `@eslint-react/eslint-plugin`: one maintainer and no rule for several components in one file.
- PMD CPD and SonarQube for duplication: a Java runtime or a server.

## Consequences

- A `typescript` project installs `eslint`, `typescript-eslint`, `eslint-plugin-sonarjs`, `prettier`, `dependency-cruiser`, `knip`, and with FSD `steiger` and `@feature-sliced/steiger-plugin`.
- Renovate updates `jscpd` through the `mise` manager and the other tools in `package.json`.

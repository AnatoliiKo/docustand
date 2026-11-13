# TypeScript profile

<!-- doc-paths: another repository -->

Read by the `repo-init` skill when `typescript` is in the `stack` answer.
The profile is the base layer of `nextjs` and `expo` ([ADR 0014](../docs/decisions/0014-typescript-profile-as-base-layer.md)); the tools are in [ADR 0015](../docs/decisions/0015-typescript-profile-dependencies.md).

## Detection

- Signal: a root `package.json` and a `tsconfig.json` at any depth; `next` or `expo` in any `package.json` gives `nextjs` or `expo` instead.
- Run `.mise/tasks/detect-stack [PATH]`; the `typescript` entry of `evidence` lists up to 10 `tsconfig.json` paths.

## Project requirements

- `mise.toml` of the project pins `node` and, with `pnpm-lock.yaml`, `pnpm`. The project version wins over `node` of `.mise/conf.d/standard.toml`.
- The root `package.json` has the scripts `typecheck` (for example `tsc --noEmit`) and `test`.
- devDependencies: `eslint`, `typescript-eslint`, `eslint-plugin-sonarjs`, `prettier`, `dependency-cruiser`, `knip`, `typescript`; with FSD in `architecture` also `steiger` and `@feature-sliced/steiger-plugin` and a `steiger.config.*`.
- `tsconfig.json` sets `strict`.
- A lockfile: `pnpm-lock.yaml` or `package-lock.json`.

## Files

| File | Owner | Content |
|---|---|---|
| `eslint.config.mjs` | standard | Project rules first, then the parser and the standard rules; with `ESLINT_NO_TYPES=1` rules with type information are off |
| `.config/eslint.project.mjs` | project, written once, protected | Project ESLint rules; global ignores are dropped |
| `.config/dependency-cruiser.standard.cjs` | standard | `no-circular` |
| `.config/dependency-cruiser.cjs` | project, written once, protected | Architecture rules; `extends` the standard file |
| `.config/knip.json` | project, written once, protected | Ignores the tools that only the hooks call |
| `.config/jscpd.json` | project, written once, protected | Duplication threshold |
| `.mise/data/size-limits.json` | standard | 300 non-empty lines for `.ts`, `.tsx`, `.mts`, `.cts` |
| `.baselines/size.json` | project, protected | Files over the limit with their size |
| `.baselines/eslint-suppressions.json` | project, protected | Old ESLint violations |
| `package.json`, `tsconfig*.json`, `vitest.config.*`, `vitest.workspace.*` at any depth | project, protected | The scripts the hooks run, the strictness of typecheck and the tests that run |

The standard rules: `complexity` 10, `sonarjs/cognitive-complexity` 15, `max-depth` 4, `max-params` 4, `max-lines-per-function` 80 (`.tsx` 120).
A project rule cannot weaken them: `eslint.config.mjs` applies them after `.config/eslint.project.mjs`.
A stricter threshold is an edit of `eslint.config.mjs` with an entry in `overrides`.
An object of `.config/eslint.project.mjs` with only `ignores` would switch off the standard rules too, so `eslint.config.mjs` drops it with a warning; a global ignore of the project is an edit of `eslint.config.mjs` with an entry in `overrides`.
The template brings no Prettier config: formatting is a project setting ([ADR 0016](../docs/decisions/0016-project-owned-check-configs.md)).
The parser options of `eslint.config.mjs` come before `.config/eslint.project.mjs`, so a project setting such as `allowDefaultProject` refines them.

## Commands

| Stage | Step | Command |
|---|---|---|
| pre-commit | `prettier` | `prettier --check` on changed code files; files of the template are excluded |
| pre-commit | `eslint-fast` | `ESLINT_NO_TYPES=1 eslint` on changed code files |
| pre-commit | `check-size` | `.mise/tasks/check-size` on changed files |
| pre-push | `typecheck`, `test` | `npm run typecheck`, `npm run test` |
| pre-push | `eslint` | `eslint` with type information on the changed files of the push |
| pre-push | `dependency-cruiser-standard` | `depcruise --config .config/dependency-cruiser.standard.cjs .`: the standard `no-circular` that a project rule cannot replace |
| pre-push | `dependency-cruiser` | `depcruise --config .config/dependency-cruiser.cjs .` |
| pre-push | `knip` | `knip` |
| pre-push | `steiger-<n>` | `steiger <part>` for each part of `architecture` with FSD; `npm run <script>` for a part with `script` |
| CI, pull request and unchecked push | Build | `npm run --if-present build` |
| CI, pull request | Duplication | `jscpd --config .config/jscpd.json .` |

`mise run check` runs every step except `eslint-fast` on all files, so CI runs the full ESLint.
`mise install` installs the dependencies after the hooks: `pnpm install --frozen-lockfile` with `pnpm-lock.yaml`, `npm ci` with `package-lock.json`. CI runs the same command before the checks.
Steps call the tools from `node_modules/.bin/`; the dependencies are installed before the hooks run.

## Baselines

- `check-size` records nothing by itself; `check-size --write-baseline` records every tracked file over the limit at migration.
- Outside CI `check-size` moves an entry after a staged rename, lowers it when the file shrinks and stages `.baselines/size.json`.
- Old ESLint violations: `eslint --suppress-all`, then `eslint --prune-suppressions` as they are fixed.
- `.config/jscpd.json` gets the measured duplication percentage at migration: run `jscpd .` with the template config and write the total into `threshold`.
- `check-baseline` fails when the suppressions, the size baseline or the threshold grow.

## Migration notes

- An own ESLint config moves into `.config/eslint.project.mjs`; its global ignores go into `eslint.config.mjs` with an entry in `overrides`; its thresholds stricter than the standard ones go into `eslint.config.mjs` with an entry in `overrides`.
- An own `.config/dependency-cruiser.cjs` gets `extends: "./.dependency-cruiser.standard.cjs"`.
- An own knip config gets the `ignore` and `ignoreDependencies` entries of the template `.config/knip.json`.
- Variables: `process.env.X` and `process.env["X"]` in the code need a line in `.env.example`.
- Steiger exceptions that `steiger.config.*` cannot express (Steiger drops the files of an excluded slice and misses their imports): a `package.json` script runs Steiger and filters its report, and the part in `architecture` names it: `--data 'architecture={"apps/web/src": {"style": "fsd", "script": "lint:fsd"}}'`.

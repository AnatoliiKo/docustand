# 0020. Protected TypeScript build files

Date: 2026-11-11
Status: accepted

## Context

- The hooks run `npm run typecheck` and `npm run test`; the scripts live in `package.json`.
- `tsconfig*.json` sets the strictness of typecheck, and `vitest.config.*` sets which tests run.
- None of them was protected: a script `"test": "true"` passed every gate.
- The protected list held `/tsconfig.json`, which a monorepo with `tsconfig.base.json` does not have.

## Decision

- The TypeScript profile protects `package.json`, `tsconfig*.json`, `vitest.config.*` and `vitest.workspace.*` at any depth.
- The report skips the commits of Renovate in every Renovate pull request, not only in template updates: version bumps in protected manifests are its job, and `renovate.json` is protected.

## Rejected

- A check of the script names in `package.json`: it cannot judge what a script runs.
- Protecting only the root `package.json`: workspace packages define their own `test` and `typecheck` scripts.

## Consequences

- An agent asks the owner before it edits these files; `pnpm add` through the shell does not ask.
- A commit of another author in a Renovate pull request stays a finding.

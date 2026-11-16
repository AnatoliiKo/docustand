# 0032. Lock file maintenance age and failing updates

Date: 2026-11-16
Status: accepted

## Context

- The template sets `minimumReleaseAge` to 3 days for every Renovate update.
- Lock file maintenance lets the package manager resolve the versions, so Renovate has no release timestamp; since Renovate 42 the status `renovate/stability-days` of such a pull request stays pending for good.
- pnpm 11 and later resolve no version younger than its own `minimumReleaseAge`, 1 day by default.
- In `cinema-ops` the pull request of TypeScript 7 stayed open and red for days: typescript-eslint does not support TypeScript 7 yet.

## Decision

- Lock file maintenance has no `minimumReleaseAge` in Renovate; the age limit of the package manager applies to it.
- A Renovate pull request that fails for an outside reason is closed; Renovate skips the closed major version, and a backlog task names the condition to take it.

## Rejected

- `minimumReleaseAgePackageManagerSync`: experimental in Renovate, and its behaviour may change.
- Holding a version with `allowedVersions` in `.github/renovate.json`: a project rule in a standard file is a deviation in `overrides`, and closing the pull request has the same effect.
- Keeping a failing pull request open as a reminder: it hides the pull requests that need a decision.

## Consequences

- A lock file maintenance pull request passes when its checks pass.
- With the pnpm default, a lock file refresh takes versions 1 day old and older; a project that needs 3 days sets `minimumReleaseAge: 4320` in `pnpm-workspace.yaml`.
- A skipped major version returns through the Dependency Dashboard, where a closed update can be recreated.

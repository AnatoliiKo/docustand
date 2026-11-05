# 0008. Danger JS for pull request checks

Date: 2026-11-05
Status: accepted

## Context

- Pull request checks cover description format, protected file diffs and new dependencies.
- Options: separate scripts; Danger JS.

## Decision

- Pull request checks live in `dangerfile.ts` from the template, on the full level.
- The file is in the repository and is a protected file.
- Checks: description format, attribution lines and session links, protected file diff as a separate section, new dependency without ADR or change, license of a new dependency.

## Rejected

- Separate scripts: no common structure for reporting in the pull request.

## Consequences

- The base level has no Danger. Protected files rely on `ask` rules, hooks against bypass, baseline growth checks in CI and report lines.
- A Renovate pull request that changes `_commit` may change template files without an `overrides` line.
- This build does not deliver Danger.

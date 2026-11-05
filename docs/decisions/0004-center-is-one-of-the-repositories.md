# 0004. The center is one of the repositories

Date: 2026-11-05
Status: accepted

## Context

- A project of several repositories needs one place for cross-repository tasks.
- Options: one of the repositories; a new entry repository; OpenSpec Stores and Worksets.

## Decision

- The owner picks one existing repository as the center.
- The list of repositories is stored only in the center.
- Closed cross-repository tasks are reported in the center.

## Rejected

- A new entry repository.
- OpenSpec Stores and Worksets: in beta, deferred.

## Consequences

- The multi-repository questions in `repo-init` are asked only when sibling repositories are found.
- The center is the only place to update when a repository joins or leaves the system.

# 0037. macOS checks in the pre-push hook

Date: 2026-11-27
Status: accepted

## Context

A macOS minute of a GitHub-hosted runner costs $0.062, 10 times a Linux minute. On 2026-11-27 the macOS jobs of `stockpit` and `manifold` cost $5.83 of $6.94 of Actions compute.

The Apple license allows macOS virtual machines only on Apple hardware. The VM `docker` of [ADR 0036](0036-self-hosted-ci-runners.md) runs on server 1-3 and cannot run macOS.

The owner develops `stockpit` and `manifold` on a Mac with an Apple M3 Pro, 11 cores, 18 GB of memory and 47 GB of free disk on 2026-11-27. Every push of these repositories, including pushes of Purple Flow, starts on this Mac.

## Decision

- Private repositories run no macOS jobs in CI.
- The `pre-push` hook of the repository runs the macOS checks on the owner's Mac: the full checks in `stockpit`, `swift test` for changes of `mac/` and `protocol/` in `manifold`.
- The hook runs only during a push; nothing runs on the Mac between pushes.
- The Linux jobs stay in CI under [ADR 0036](0036-self-hosted-ci-runners.md).

## Rejected

- Tart VMs with a runner manager (`khoi/sand`, `framna-dk/tartelet`): a VM of 4 cores and 6 GB takes resources of the owner's work while it runs, and a base image takes tens of GB of the 47 GB of free disk. `sand` has one maintainer; `tartelet` has no release since 2025-06-13.
- `actions/runner` directly on the owner's macOS: jobs share the owner's Homebrew, files and databases.
- macOS jobs on GitHub-hosted runners for pull requests into `main` only: a cost for a check that the hook already makes.
- Anka and Orka: commercial products.

## Consequences

- A push waits for the checks: about 6 min in `stockpit`, about 30 s in `manifold` when `mac/` or `protocol/` changes.
- The hook works only after `git config core.hooksPath .githooks` in each clone; a push without it skips the macOS checks.
- A push from a machine other than a Mac checks no macOS.

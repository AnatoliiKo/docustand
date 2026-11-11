# 0022. Standard configs out of the root

Date: 2026-11-11
Status: accepted

## Context

- A TypeScript project on the standard had 17 standard files in the root; `cinema-ops` had 39 root entries.
- The owner's rule 13: preset, then `package.json`, then `.config/`, and only then the root; rule 4: baselines in one folder.
- `copier update` deletes a file that leaves the template and writes the template default at the new path.

## Decision

- Standard configs move to `.config/`: hk and rumdl find them there; typos, lychee, commitlint, knip, jscpd and dependency-cruiser get `--config`.
- Renovate config moves to `.github/renovate.json`; baselines move to `.baselines/` (`size.json`, `betterleaks.ignore`, `eslint-suppressions.json` through `--suppressions-location`).
- `eslint.config.mjs`, `.repo.yaml`, `mise.toml`, `.gitignore` and the agent files stay in the root: editors, Copier, Renovate and Claude Code look for them there.
- Project-owned configs move by `git mv` before the update; `check-root` names the new place, and `check-root --since` fails a pull request that lost their content.

## Rejected

- Copier migrations: they need `--trust`, which cloud Renovate does not grant ([ADR 0006](0006-copier-for-repository-files.md)).
- Keeping project-owned configs in the root: five TypeScript files would stay there for good.
- An npm preset package now: a later stage after the owner chooses a registry.

## Consequences

- The update to 0.5.0 is manual: a Renovate pull request fails until the project moves its files.
- Project scripts that call a tool with a moved config add `--config` or the new path.

## In progress

### Migrate `cinema-ops` to the repository standard

- Goal: first pilot on a repository with code; results go to `docs/pilot-log.md`.
- Done when: the success criteria of section 12 of the specification pass in `cinema-ops`.
- Stopped at: profile `typescript` released in `v0.2.0` (ADR 0015, ADR 0016); the first run of `ci-merged-pr` waits for the Renovate pull request to the template update (`v0.1.5` or `v0.2.0`).
- Next: after the owner merges that pull request, record the `standard-ci` push run in `docs/pilot-log.md`; then Task 2 in `cinema-ops`.
- Refs: `docs/temp/pilot-cinema-ops-plan.md`.

## Backlog

- Migrate the `infrastructure` project to the repository standard — second pilot project, results go to `docs/pilot-log.md`.
- Investigate Protected files: #4: `.claude/settings.json`, `.github/repo.schema.json`, `.github/workflows/standard-ci.yml`, `.mise/data/size-limits.json`, `.mise/tasks/check-baseline`, `.mise/tasks/check-env-example`, `.mise/tasks/check-gitignore-block`, `.mise/tasks/check-size`, `.mise/tasks/ci-merged-pr`, `.mise/tasks/detect-stack`, `.repo.yaml`, `hk.pkl` — report 2026-11-09
- Investigate Protected files: #3: `.mise/tasks/check-gitignore-block`, `.repo.yaml` — report 2026-11-09
- Investigate Protected files: #2: `.mise/tasks/report`, `.repo.yaml`, `hk.pkl` — report 2026-11-09

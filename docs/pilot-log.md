# Pilot log

Results of the standard on pilot projects. One row per observation.

| Date | Check | Caught | False positive | Maintenance time |
|---|---|---|---|---|
| 2026-11-06 | Pilot scope | `infrastructure` holds Python code: 45 `.py` files with pytest tests of the Lambda functions; the criterion of the first repository with code is not checked for Python by this pilot | — | — |
| 2026-11-06 | `check-gitignore-block` | Missed: a `.claude/` rule before the standard block disabled its negations, and the check passed; behaviour check with `git check-ignore` added | — | — |
| 2026-11-06 | Renovate `copier` manager | First run found no update: `gh:` source passed to the tag lookup unchanged, fixed in `v0.1.3`; then PR 2 `v0.1.0` → `v0.1.3` opened without automerge; 3 conflict markers in `hk.pkl` and `.mise/tasks/report` from hand-synced root files, caught by `standard-ci`, resolved with the `v0.1.3` side, merged | — | — |
| 2026-11-06 | Renovate `copier` manager | PR 3 `v0.1.3` → `v0.1.4` opened without conflicts or automerge, CI green, merged; the tag pushed at 14:45 UTC appeared in Renovate at 15:16 UTC, about 70 min after the previous tag lookup | — | — |
| 2026-11-06 | Betterleaks, `cinema-ops` history | 105 findings of generic rules over 633 commits, all false: i18n labels and test placeholders; no FTP passwords, Resilio keys, tokens or API keys | 105 | — |
| 2026-11-06 | History scan, `cinema-ops` | Internal LAN and Tailscale addresses in files, tests and captures; not secrets, the history was not rewritten | — | — |
| 2026-11-06 | Hook budget, `cinema-ops` | Type-aware ESLint on changed files takes 3–7 s and does not fit the 5 s pre-commit budget; full ESLint (37 s) with `tsc` and tests exceeds the 1 min pre-push budget; proposed section 9 change: full linter before push only within budget, otherwise changed files before push and the full run in CI | — | — |

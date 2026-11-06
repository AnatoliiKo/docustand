# Changelog

All notable changes to this repository are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.1.2 — 2026-11-06

### Added

- `README.md` section `Development`: `claude --plugin-dir` loads the plugin from the working copy without rewriting `.claude/settings.json`.

### Changed

- `LICENSE`: MIT-0 (MIT No Attribution) instead of MIT; copies of template scripts need no copyright notice. The copyright holder is Anatolii Kostenko.
- Template `report`: without the report app the vulnerability alert check does not run; the section `Vulnerability alerts` reads `Not checked, needs the report app` instead of the false finding `not enabled or not readable`.

### Fixed

- Template `hk.pkl`: the comment of `check-merge-conflict` no longer names `copier update`, so a detached project contains no `copier update` mention; the integration test `test_detached_project_passes_without_docustand` failed on `v0.1.1`.

## 0.1.1 — 2026-11-06

### Added

- `LICENSE`: MIT. The template does not render a license into projects.
- `README.md` section `Install`: the marketplace and plugin install commands for a repository without `.claude/settings.json`.
- Template `hk.pkl`: step `check-merge-conflict` (hk builtin, `--assume-in-merge`) in `pre-commit` and `check`, so conflict markers of a `copier update` fail CI.

### Changed

- Template `renovate.json`: the `copier` manager has no `minimumReleaseAge` and no automerge. Git tags carry no release date, so Renovate 42+ held template updates as pending forever; a patch update of the template automerged, also with unresolved conflicts.
- Template `standard-report.yml`: without the secret `REPORT_APP_ID` the job skips the app token, collects the findings with the default token (`contents: read`, `pull-requests: read`), writes them to the job summary and fails with `report app is not configured, see docs/access.md`; `fresh-install` still runs when due.
- Template `report`: the findings go to `GITHUB_STEP_SUMMARY` on every run.

### Fixed

- Skill `repo-init`: sibling repositories alone no longer trigger the multi-repository question; an empty GitHub plan field counts as `free`; questions over the question tool limit go in consecutive calls.

## 0.1.0 — 2026-11-06

### Added

- `README.md` with usage, levels, update, detach and requirements.
- Architecture decision records `0001` to `0013` in `docs/decisions/`.
- Plugin manifest `.claude-plugin/plugin.json` and marketplace `.claude-plugin/marketplace.json`; the plugin `version` equals the topmost released version of this file.
- Skill `repo-init`: new repository, migration, audit and update, answer changes, detach.
- Skills `project-docs` and `quality-gates`, ported to the repository standard.
- Agent `inventory`: read-only documentation inventory for the migration.
- Template `guard_bash.py`: a Bash command that writes to a path of an `Edit(/<path>)` rule in `permissions.ask` returns the PreToolUse decision `ask`; writes are redirections, `tee`, `sed -i`, `perl -i`, `cp` and `mv`; a block wins over an ask; a `dir/**` rule covers `dir` itself; matching ignores case; an unparsable command asks when its text names a protected path next to a write marker.
- Template `_shell.py`: the guard hooks unwrap `doas`, `setsid`, `stdbuf` and `find -exec`, and follow nested `eval` and `sh -c` up to 8 levels.

### Changed

- Template `standard-ci.yml`: the log records `git --version`, which shows whether hk hooks run in git config mode (Git 2.54+).
- `check-baseline`: a baseline file absent at the base ref passes only when `.repo.yaml` did not exist at the base, `_commit` changed, or `stack` changed and the file belongs to an added profile; a missing or invalid current `.repo.yaml` allows nothing; each new baseline file is printed with the reason.
- Scheduled `report`: section `New baseline files` lists the baseline files each merged pull request added, renamed or copied.

### Fixed

- Template `check-comments`: `.py` files are scanned with `tokenize`, so a `# TODO` inside a string or docstring is not a finding; a file that does not tokenize falls back to the line scan.
- Template `guard_bash.py`: options of `sudo` (including `-R`), `time`, `exec`, `command` and BSD `xargs` are skipped, so `sudo -u bob git commit -n` is blocked; a redirection before the command and `--` after `sh -c` no longer hide it.
- Template `docs/access.md`: the report GitHub App row with its secrets and permissions renders whenever reports are on; the scheduled Claude task row renders only at the full level.

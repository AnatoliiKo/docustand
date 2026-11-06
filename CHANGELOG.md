# Changelog

All notable changes to this repository are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

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

- `check-baseline`: a baseline file absent at the base ref passes only when `.repo.yaml` did not exist at the base, `_commit` changed, or `stack` changed and the file belongs to an added profile; a missing or invalid current `.repo.yaml` allows nothing; each new baseline file is printed with the reason.
- Scheduled `report`: section `New baseline files` lists the baseline files each merged pull request added, renamed or copied.

### Fixed

- Template `check-comments`: `.py` files are scanned with `tokenize`, so a `# TODO` inside a string or docstring is not a finding; a file that does not tokenize falls back to the line scan.
- Template `guard_bash.py`: options of `sudo` (including `-R`), `time`, `exec`, `command` and BSD `xargs` are skipped, so `sudo -u bob git commit -n` is blocked; a redirection before the command and `--` after `sh -c` no longer hide it.
- Template `docs/access.md`: the report GitHub App row with its secrets and permissions renders whenever reports are on; the scheduled Claude task row renders only at the full level.

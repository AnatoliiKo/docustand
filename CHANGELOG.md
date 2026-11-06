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

### Changed

- `check-baseline`: a baseline file absent at the base ref passes only when `.repo.yaml` did not exist at the base, `_commit` changed, or `stack` changed and the file belongs to an added profile; a missing or invalid current `.repo.yaml` allows nothing; each new baseline file is printed with the reason.
- Scheduled `report`: section `New baseline files` lists the baseline files each merged pull request added, renamed or copied.

### Fixed

- Template `docs/access.md`: the report GitHub App row with its secrets and permissions renders whenever reports are on; the scheduled Claude task row renders only at the full level.

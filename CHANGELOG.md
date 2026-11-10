# Changelog

All notable changes to this repository are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.3.9 — 2026-11-10

### Fixed

- Template `standard-report.yml` checks external links in the tracked Markdown files, as the `lychee` hook: `lychee .` of `cinema-ops` failed on HTML fixtures of external sites and the root-relative links of the web panel.

## 0.3.8 — 2026-11-10

### Fixed

- Template `standard-report.yml` gives type-aware ESLint of `fresh-install` the 4 GB heap of `standard-ci.yml`: the job of `cinema-ops` ran out of memory.
- The report GitHub App needs Checks read and Commit statuses read: `gh pr list` reads `statusCheckRollup`, and the `cinema-ops` report failed with «Resource not accessible by integration». `SKILL.md` and `docs/access.md` list the permissions.

## 0.3.7 — 2026-11-10

### Fixed

- Template `report` prints the error output of a failed `gh` call: the first `cinema-ops` report run failed on `gh pr list` with only an exit status in the log.

## 0.3.6 — 2026-11-10

### Fixed

- Template `standard.toml` of TypeScript projects installs the Node dependencies in the `mise install` hook: a fresh clone of `cinema-ops` set up by the README failed `mise run check` and `mise run test` without `node_modules`.

## 0.3.5 — 2026-11-10

### Fixed

- Template `check-gitignore-block` fails when a rule of `.gitignore` ignores a file the template renders for the answers of `.repo.yaml`: a project rule `data/` matched `.mise/data/`, so `size-limits.json` and `task-verbs.txt` stayed out of git. The check runs `git check-ignore --no-index` on the list of standard files; a test keeps the list equal to the rendered files.

## 0.3.4 — 2026-11-10

### Fixed

- Template `standard-ci.yml` sets `NODE_OPTIONS=--max-old-space-size=4096` for `mise run check` in TypeScript projects: type-aware ESLint of `cinema-ops` (1144 files, 2.6 GB peak) ran out of the 2 GB default heap of the runner.
- Skill `repo-init` passes `required_ci_branches` with the default branch also when the plan has no branch protection: `cinema-ops` with the default branch `dev` got `[main]` and no CI runs.

## 0.3.3 — 2026-11-09

### Fixed

- Template `check-env-example` reads the whole name of a variable: `process.env['SystemDrive']` was reported as `S`; names with lower case letters are OS variables and are ignored.

## 0.3.2 — 2026-11-09

### Changed

- Template `typos.toml` is written once and belongs to the project (ADR 0017); it is protected.
- Template `check-baseline`: `.betterleaksignore` is a baseline of every stack and may not grow; `.claude/settings.json` protects it.
- Template `check-env-example` ignores `CI` and variables starting with `GITHUB_` or `RUNNER_`.

## 0.3.1 — 2026-11-09

### Changed

- Template `hk.pkl`: a part of `architecture` may be a mapping `{style, script}`; for an FSD part with `script` the `steiger-<n>` step runs `npm run --silent <script>` instead of `steiger <part>`. `repo.schema.json` accepts that form.
- Template `eslint.config.mjs`: the parser options come before the rules of `eslint.project.mjs`, so `allowDefaultProject` of a project is kept; the standard rules still come last.

## 0.3.0 — 2026-11-09

### Changed

- Template `report`: the commit of the `report` pull request has the report app bot as its author (`<app-slug>[bot]`, `<id>+<app-slug>[bot]@users.noreply.github.com`); `standard-report.yml` passes `REPORT_APP_SLUG`.
- Template `report`: `docs/tasks.md` gets one backlog line `- <action> — <reason>` per kind of finding instead of one per item; the date moves to the pull request description.
- Template `report`: a run without findings closes the open `report` pull request with the comment `no findings in the report of <date>`.
- Template `standard-report.yml`: `create-github-app-token` takes `client-id` from the secret `REPORT_APP_CLIENT_ID` instead of the deprecated `app-id`; a repository sets `REPORT_APP_CLIENT_ID` before it merges this update, and deletes `REPORT_APP_ID` after a green report run.
- Template `report`: a Renovate pull request that changes `_commit` in `.repo.yaml` goes to the section `Template updates` with its version; such a section alone opens no pull request and adds no backlog line. Files changed by other authors in that pull request stay in `Protected files`.
- `repo-init` audit enables vulnerability alerts when `gh api repos/{owner}/{repo}/vulnerability-alerts` answers 404.

## 0.2.0 — 2026-11-07

### Added

- Profile `typescript` (`profiles/typescript.md`, ADR 0015): Prettier and ESLint without type information before a commit; types, ESLint with type information, tests, dependency-cruiser `no-circular`, knip and Steiger for FSD parts before a push; jscpd on pull requests. `eslint.config.mjs` applies the standard complexity rules after the project rules in `eslint.project.mjs` and drops global ignores of the project. CI installs the Node dependencies with pnpm or npm.
- ADR 0016: `eslint.project.mjs`, `knip.json` and `.dependency-cruiser.cjs` are written once, belong to the project and are protected; the template brings no Prettier config.
- `detect-stack` reports `typescript` for a root `package.json` with a `tsconfig.json` at any depth, and reads `next` and `expo` from every `package.json`.
- Task `check-size` for every stack: limits per extension in `.mise/data/size-limits.json`, old large files in `.size-baseline.json`; outside CI the baseline follows staged renames and shrinking files.
- `check-baseline` compares `eslint-suppressions.json` by the sum of counts, `.size-baseline.json` by entries, lines and each kept entry, and `.jscpd.json` by the threshold.
- Allowed licenses of dependencies in `skills/repo-init/references/licenses.md`.

### Changed

- `check-env-example` reads `process.env.X` and `process.env["X"]` for `typescript` and ignores `ESLINT_NO_TYPES`.
- `.claude/settings.json` asks before edits of `.size-baseline.json` and, for `typescript`, of the profile configs, the project-owned check configs, the Steiger config and the baselines; the report lists their changes.

## 0.1.5 — 2026-11-06

### Changed

- Template `standard-ci`: on a push to a required branch, a commit of a merged pull request skips `mise run check`; CI runs `check-baseline` against the previous tip and `check-pr-commits` over the pushed range. A direct push runs every check. The new task `ci-merged-pr` asks the pulls API and answers false on any error; the workflow reads pull requests (`pull-requests: read`).

### Added

- ADR 0014: the `typescript` profile is the base layer of the `nextjs` and `expo` profiles.
- `README.md` section `Update` and `repo-init` skill: resolving conflicts in a Renovate template update pull request on the Renovate branch; Renovate no longer rebases the branch after a commit by another author.

## 0.1.4 — 2026-11-06

### Fixed

- Template `check-gitignore-block`: `git check-ignore` confirms that `.claude/settings.json` and `.claude/hooks/guard_bash.py` are not ignored and `CLAUDE.local.md` is ignored. A rule `.claude/` before the block disabled the negations of the block, and the check passed.

## 0.1.3 — 2026-11-06

### Fixed

- Template `renovate.json`: rules with `overridePackageName` expand the Copier source shorthands `gh:` and `gl:` to `https://github.com/` and `https://gitlab.com/`. Renovate passed `gh:owner/repo` to the `git-tags` lookup unchanged, the lookup returned no result, and no `copier update` pull request opened.
- Template `renovate.json` has no `.jinja` suffix: Copier copies it unrendered, so the Handlebars templates of Renovate stay intact.

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

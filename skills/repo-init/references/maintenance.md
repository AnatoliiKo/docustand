# Audit, update, answers, detach

<!-- doc-paths: another repository -->

## Audit and update

A repeated run is safe: it reads `.repo.yaml` and asks only questions that have no answer yet.

1. `git status --porcelain` prints nothing; otherwise stop and tell the owner to commit first.
2. Reconnaissance (reconnaissance.md); compare `mise run detect-stack` with `stack`, the found methodology with `architecture`, the long-lived branches with `required_ci_branches`.
3. Compare `_commit` with the latest release tag of docustand. If it is older and Renovate has no open PR for it, update on a new branch:

   ```bash
   copier update -a .repo.yaml --defaults --vcs-ref <tag>
   ```

   Conflicts appear as inline markers or `.rej` files; show each to the owner, resolve, and keep or add the `overrides` entry.

   A Renovate pull request with conflicts: `gh pr checkout <number>`, show each marker and `.rej` file to the owner, resolve, commit `fix: resolve template update conflicts` and push to the same branch after the owner approves.
   After a commit by another author, Renovate no longer rebases or recreates the branch; the rebase checkbox recreates it and discards the resolution.
   The owner merges the pull request.
4. `mise install`, then `mise run check` exits 0.
5. Check the GitHub steps (SKILL.md section 6):
   - `gh api repos/{owner}/{repo}/vulnerability-alerts` answers 204; on 404 enable the alerts with SKILL.md section 6 step 1 and check again;
   - protection matches `required_ci_branches`;
   - the report secrets `REPORT_APP_CLIENT_ID` and `REPORT_APP_PRIVATE_KEY` exist when `report_schedule` is not `off` (`gh secret list`); a repository with only `REPORT_APP_ID` gets `REPORT_APP_CLIENT_ID` (SKILL.md section 6 step 3), then the owner deletes `REPORT_APP_ID` after a green report run.
6. Report the differences found and what changed.

## Update across 0.5.0

0.5.0 moves the standard configs from the root to `.config/` and the baselines to `.baselines/`.
`copier update` deletes a moved project file and writes the template default at the new path.
A commit that only moves the files fails the hooks of the old version, so the project files return after the update, in the same commit:

```bash
copier update -a .repo.yaml --defaults --vcs-ref v0.5.1
r() { [ -n "$(git ls-files "$1")" ] || return 0; git checkout HEAD -- "$1" && git mv -f "$1" "$2"; }
r typos.toml .config/typos.toml
r eslint.project.mjs .config/eslint.project.mjs
r .dependency-cruiser.cjs .config/dependency-cruiser.cjs
r knip.json .config/knip.json
r .jscpd.json .config/jscpd.json
r .size-baseline.json .baselines/size.json
r .betterleaksignore .baselines/betterleaks.ignore
r eslint-suppressions.json .baselines/eslint-suppressions.json
```

Then adjust the paths that the move changes:

- `.config/dependency-cruiser.cjs`: `extends` is `./dependency-cruiser.standard.cjs`.
- `.config/knip.json`: `ignore` names `.config/dependency-cruiser.cjs`, `.config/dependency-cruiser.standard.cjs` and `.config/commitlint.config.mjs`.
- `.config/eslint.project.mjs`: a path built from `import.meta.dirname`, such as `tsconfigRootDir`, goes one folder up with `dirname(import.meta.dirname)`.
- Project scripts that name a moved file follow it; `eslint` gets `--suppressions-location .baselines/eslint-suppressions.json`.

`check-root` names every file still in the root.
In CI `check-root --since` fails a pull request in which a project file kept under 80 % of its lines at the new path.

## Update across 0.6.0

0.6.0 narrows `docs/` to the standard documents and checks internal JSDoc.
Before the update:

1. Every other `docs/*.md` is removed or listed: `copier update -a .repo.yaml --defaults --data 'md_exceptions=[docs/<name>.md]'` (the list keeps its existing entries).
2. After the update, `mise run check-comments` lists JSDoc on internal declarations; convert them to line comments, or record them with `mise run check-comments -- --write-baseline` when the project decides so.

## Update across 0.7.0

0.7.0 checks the language of comments and the paths named in documents.
After the update:

1. `mise run check-comments` lists comments not in English and comments of newly read file types; translate them, or record them with `mise run check-comments -- --write-baseline` when the project decides so.
2. `mise run check-doc-paths` lists document paths that do not exist; fix the documents. The check has no baseline: a stale path misleads the next reader.
3. A deployed project keeps `## Maintenance` of `README.md` only when it differs from `docs/operations.md`; the template writes the note to `docs/operations.md` only.

## Changing an answer

Level, stack, report schedule, branches, `md_exceptions`, `overrides` and every other answer change only through Copier, never by editing `.repo.yaml`:

1. `git status --porcelain` prints nothing; otherwise stop and tell the owner to commit first.
2. Run on a new branch:

   ```bash
   copier update -a .repo.yaml --defaults --data <key>=<value>
   ```

   Examples: `--data report_schedule=monthly`, `--data 'stack=[terraform]'`, `--data 'required_ci_branches=[main,develop]'`. Lists and mappings in YAML flow form, single-quoted: brackets and braces are globs in zsh.
3. `--data level=full` fails with «Level "full" is not supported yet»: the full level is not available yet.
4. Copier adds and removes the files of the changed answer (profile configs, the report workflow, `docs/operations.md`). `mise install`, then `mise run check` exits 0.
5. A changed `required_ci_branches` also changes branch protection (SKILL.md section 6).

## Detach

The repository keeps working without docustand: only mise, hk, GitHub Actions, linters, README and ADRs stay.
The steps are the procedure tested by `tests/integration/test_detach.py` in docustand.
Edit the files textually and minimally: remove the lines named below and keep the rest of the formatting; do not re-serialize JSON or YAML.

1. `.repo.yaml`: delete the `_src_path` and `_commit` lines. Replace the first line, the Copier header comment, with `# Project properties checked by .github/repo.schema.json.`.
2. `.mise/conf.d/standard.toml`: delete the line that starts with `"pipx:copier"`.
3. `.claude/settings.json`: delete the `"docustand@docustand": true` entry from `enabledPlugins` and the `"docustand"` entry from `extraKnownMarketplaces`. Fix the commas so the JSON stays valid.
4. `AGENTS.md`: delete the line `If docustand is installed: /docustand:pr-ready.` and the blank line before it; two blank lines in a row fail the Markdown lint.
5. `.github/renovate.json`: delete the `"copier"` manager entry and, from `ignorePaths`, `.mise/conf.d/standard.toml` and `.github/workflows/standard-*.yml`; delete `ignorePaths` when it becomes empty. Fix the commas so the JSON stays valid.
6. `AGENTS.md`: replace the rule that starts with ``- Change answers in `.repo.yaml` only with `copier update` `` with ``- Edit `.repo.yaml` by hand; the change needs the owner's approval.``
7. Full level only: delete the scheduled Claude task of the reports and its row in `docs/access.md`. At the base level the task does not exist.

Then:

- `grep -rIil docustand --exclude-dir=decisions --exclude-dir=.git .` and `grep -rn "copier update" --exclude-dir=decisions --exclude-dir=.git .` print nothing;
- `mise run check-repo-yaml` and `mise run check` exit 0;
- commit `chore: detach from docustand` and open a PR.

After detaching, `copier update` no longer works, Renovate no longer raises template updates, and answers in `.repo.yaml` are edited by hand with the owner's approval, under the `ask` rule.

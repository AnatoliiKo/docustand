# Audit, update, answers, detach

## Audit and update

A repeated run is safe: it reads `.repo.yaml` and asks only questions that have no answer yet.

1. `git status --porcelain` prints nothing; otherwise stop and tell the owner to commit first.
2. Reconnaissance (reconnaissance.md); compare `mise run detect-stack` with `stack`, the found methodology with `architecture`, the long-lived branches with `required_ci_branches`.
3. Compare `_commit` with the latest release tag of docustand. If it is older and Renovate has no open PR for it, update on a new branch:

   ```bash
   copier update -a .repo.yaml --defaults --vcs-ref <tag>
   ```

   Conflicts appear as inline markers or `.rej` files; show each to the owner, resolve, and keep or add the `overrides` entry.
4. `mise install`, then `mise run check` exits 0.
5. Check the GitHub steps (SKILL.md section 6): vulnerability alerts answer 204, protection matches `required_ci_branches`, the report secrets exist when `report_schedule` is not `off` (`gh secret list`).
6. Report the differences found and what changed.

## Changing an answer

Level, stack, report schedule, branches, `md_exceptions`, `overrides` and every other answer change only through Copier, never by editing `.repo.yaml`:

1. `git status --porcelain` prints nothing; otherwise stop and tell the owner to commit first.
2. Run on a new branch:

   ```bash
   copier update -a .repo.yaml --defaults --data <key>=<value>
   ```

   Examples: `--data report_schedule=monthly`, `--data stack=[terraform]`, `--data required_ci_branches=[main,develop]`. Lists and mappings in YAML flow form.
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
5. `renovate.json`: delete the `"copier"` manager entry and, from `ignorePaths`, `.mise/conf.d/standard.toml` and `.github/workflows/standard-*.yml`; delete `ignorePaths` when it becomes empty.
6. Full level only: delete the scheduled Claude task of the reports and its row in `docs/access.md`. At the base level the task does not exist.

Then:

- `grep -rIil docustand --exclude-dir=decisions --exclude-dir=.git .` prints nothing;
- `mise run check-repo-yaml` and `mise run check` exit 0;
- commit `chore: detach from docustand` and open a PR.

After detaching, `copier update` no longer works, Renovate no longer raises template updates, and answers in `.repo.yaml` are edited by hand under the `ask` rule.

# Migration of an existing repository

Six steps, each on its own branch from the default branch and in its own PR.
The next step starts after the owner merges the previous one.
Temporary files go to `docs/temp/` of the project; until step 2 adds it to `.gitignore`, never stage that folder.

## 1. Inventory

1. Call the `docustand:inventory` agent with the project root, the files outside git from reconnaissance and the stack.
2. The agent returns the table `| Path | Kind | Decision (move/delete/keep) | Target |`; it has no tool to write files. Save the table to `docs/temp/inventory.md`.
3. Check the table against the files (project-docs, «Migrate», M1) and show it to the owner. Personal notes of the owner go to `CLAUDE.local.md` or `~/.claude/CLAUDE.md`, only with the owner's yes.
4. The owner approves the table, row by row where they disagree.
5. PR: the rows the owner approved as `delete`. Rows `move` wait for step 5.

## 2. Checks

The template meets existing files. The order below keeps every existing line; it is the order tested by `tests/test_migration_render.py` in docustand.

1. Render the template aside with the same answers. Until `mise install` brings Copier, run every `copier` command of this step as `mise exec uv@0.13.7 pipx:copier@9.19.1 -- copier ...`. Single-quote list and mapping values:

   ```bash
   copier copy --defaults --vcs-ref <ref> --data project_name=<name> --data 'stack=[...]' <more --data> \
     <template> docs/temp/rendered
   ```

2. List the files that exist in both with different content:

   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/merge_existing.py conflicts . docs/temp/rendered --template ${CLAUDE_PLUGIN_ROOT}
   ```

   Files in `_skip_if_exists` (`README.md`, `CLAUDE.md`, `.gitignore`, `docs/*.md` of the template) are not listed: Copier never overwrites them.
3. Apply the template with the same `--vcs-ref` and answers, skipping each listed file:

   ```bash
   copier copy --defaults --vcs-ref <ref> <same --data> --skip <file 1> --skip <file 2> <template> .
   ```

4. Merge what Copier cannot: `${CLAUDE_PLUGIN_ROOT}/scripts/merge_existing.py merge . docs/temp/rendered`. It appends the missing standard lines to `.gitignore` between `# >>> repository standard` markers and reports own files next to standard ones (`mise.toml`, `CLAUDE.md`, own workflows). It never deletes a line.
5. `mise trust`, `mise install` (runs `hk install --mise`).
6. Commit through the hooks: `chore: apply repository standard`. Then the hook probe from SKILL.md section 5, step 7.
7. For each conflict file, the owner decides (questions.md, «Own configs»); one commit per decision:
   - take the standard: copy the file from `docs/temp/rendered/`;
   - keep own: leave the file, add an `overrides` entry with the reason;
   - merge by hand: edit the file, add an `overrides` entry with the reason.

   `overrides` changes through `copier update -a .repo.yaml --defaults --data 'overrides=[...]'`, after `git status --porcelain` prints nothing.
8. Own `CLAUDE.md`: its rules move into `AGENTS.md` sections in step 5; `CLAUDE.md` becomes the line `@AGENTS.md`.
9. Old findings of the new checks: safe autofix one tool per commit, the rest into the tool's baseline (quality-gates). External data such as fixtures goes into `extend-exclude` of `typos.toml`; known `betterleaks` findings without a secret go into `.betterleaksignore` as fingerprints from `betterleaks dir --report-format json` ([ADR 0017](../../../docs/decisions/0017-project-spelling-config-and-secret-baseline.md)). The profile file lists its baselines and the merge of own configs (for example `profiles/typescript.md`, «Baselines» and «Migration notes»).
10. Root entries, ADRs and history comments: own source folders and files go into `root_files` (`copier update -a .repo.yaml --defaults --data 'root_files=[apps, packages]'`), stray root files move or go; `mise run check-adr -- --write-baseline` and `mise run check-comments -- --write-baseline` record the old violations in `.baselines/` with `until` 90 days ahead. Each baseline gets a cleanup task in `docs/tasks.md` with the entry count as its `Done when`.
11. Prove that each check fails on a violation (quality-gates, «Prove every gate fails»).
12. `mise run check` exits 0. Delete `docs/temp/rendered`.
13. GitHub steps (SKILL.md section 6).

## 3. Comment cleanup

1. `mise run check` already fails on comment mechanics and history (`check-comments`): bare `TODO`, «added by», `@author`, linter disables without a reason, dates, addenda, decision attribution, change history. Fix each finding; history findings may wait in `.baselines/comments.json` until its `until` date.
2. Remove comments that restate the code, commented-out code, names and dates. Keep comments that state why, type annotations and public API documentation.
3. Large deletions go to the owner as a list before the commit.

## 4. Translation of the documentation to English

project-docs, «Migrate», M2: a table «before → after» in `docs/temp/`, a back translation by a separate agent, differences in meaning listed in the PR.

## 5. Layout

project-docs, «Migrate», M3: apply the `move` rows of `docs/temp/inventory.md`.
`mise run check` fails on every `.md` left outside the structure.
Delete `docs/temp/inventory.md` after the merge.

## 6. API contract

Only if the repository has an API: the contract file (`openapi.yaml` or TypeSpec), the `contract` answer through `copier update -a .repo.yaml --defaults --data 'contract={role: provider, approach: code-first}'`, and an ADR on the approach (code-first or schema-first).

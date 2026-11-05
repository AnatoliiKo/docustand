---
name: project-docs
description: Use when writing, updating or auditing a repository's documentation under the docustand standard (README, AGENTS.md, docs/architecture.md, ADRs in docs/decisions, docs/tasks.md, docs/access.md), when docs may have drifted from the code, or when documentation is migrated or translated. Also for "напиши документацию", "обнови доки", "проверь документацию", "оформи решение", "ADR", "документация устарела", "доки расходятся с кодом".
---

# Project Docs

Goal: documentation that is true today and stays true.
Every path, command and ADR number in it exists.
Every list that mirrors code is checked against the code or points at it.
History stays in git and PRs, not in documents.

Layout, formats and language: [references/formats.md](references/formats.md). Read it first.

## Modes

- **Audit** («проверь документацию»): read-only. Steps A1–A4, report.
- **Sync** (after a code change, or «обнови доки»): fix the docs the change touches in the same branch. Steps S1–S3.
- **Write** («напиши», «оформи ADR», «опиши архитектуру»): one new document in the standard format. Steps W1–W3.
- **Migrate** (step 1 «Inventory», step 4 «Translation» and step 5 «Layout» of the `repo-init` migration): M1–M3.
- **Gates** («чтобы доки не расходились»): propose checks, wire them through `quality-gates`.

A repository without the standard gets it from `/docustand:repo-init`, not from this skill: the documents come from the Copier template.

## Audit

**A1. Mechanical check.** From the project root:

```bash
node ${CLAUDE_PLUGIN_ROOT}/skills/project-docs/scripts/check-doc-refs.mjs .
```

It checks backticked repo paths, relative Markdown links, `ADR NNNN` numbers and `pnpm`/`npm`/`yarn`/`mise run` commands (tasks from `mise.toml` and `.mise/conf.d/*.toml`).
It skips `docs/temp/`, `CHANGELOG.md`, dot-folders, absolute paths, placeholders and gitignored paths.
`--all` includes the skipped history, `--json` prints JSON, `--files a.md,b.md` limits the run.
For each hit, find what the path became (`git log --follow`, `find`) and report «was → now».
A path that exists on a machine but not in the repository goes into `.doc-refs-ignore` with a comment.

**A2. Lists that mirror code.** Compare every list in the docs that repeats something the code defines:

| Doc list | Compare with |
|---|---|
| allowed actions, commands, roles | the enum or const array in code |
| modules, packages, folders in `AGENTS.md` Structure | `ls` of those folders |
| tables in the data model | schema files, migrations |
| commands | `mise tasks`, `package.json` scripts, CLI subcommands |
| environment variables | `.env.example`, config schema |
| endpoints | router, the contract file |
| deployed versions and addresses | GitHub Deployments or deploy tags; they do not belong in docs |

Report each mismatch with both sides, for example: «`AGENTS.md` rule 2: no `utm.restart`; `packages/shared/src/actions.ts:14` has it».

**A3. Claims and contradictions.** Read `AGENTS.md`, `docs/architecture.md`, `README.md` and the guides.
Check concrete claims (numbers, limits, «implemented», «forbidden to import») against the code they name.
Look for two documents that state different things about one fact.
Facts from the owner's `~/.claude/CLAUDE.md` count as well.

**A4. Report.** In the owner's language, in this order: false statements and contradictions (file:line and the disagreeing code) → outdated → missing → what to fix, in order (a rule change in `AGENTS.md` needs the owner's decision) → how to keep the docs true (Gates).
End with what was checked by script, by reading, and not at all.

## Sync

**S1.** From `git diff <base>...HEAD --stat` and the changed code, list the facts that changed: action, module, table, command, environment variable, endpoint, port, threshold, moved file.

**S2.** `grep -rn` each changed name and old path in `README.md`, `AGENTS.md`, `docs/` (skip `docs/temp/`).
Fix each place.
A changed decision gets a new ADR that links the old one.
A rule change in `AGENTS.md`: propose the edit, apply it only after the owner's yes.

**S3.** Run `check-doc-refs.mjs`; it must exit 0.
Update `docs/tasks.md`: a finished task is deleted, its result stays in the PR.

## Write

**W1.** Read the documents next to the new one and follow their structure and headings.
Read the code the document describes.
Every fact comes from code, config, an ADR or the owner, never from what such projects usually have.

**W2.** Write in English in the style of `AGENTS.md` Text rules.
If the `humanizer` skill is available, do one pass with it, keeping every fact and identifier.
If the pass is skipped, say so in the report.

**W3.** Run `check-doc-refs.mjs --files <new file>` until it exits 0.
A hit on something the same change introduces is expected: report it as «appears with the change».
Link the new document from `README.md` or `docs/architecture.md`.

## Migrate

**M1. Inventory.** `repo-init` calls the `inventory` agent and saves its table to `docs/temp/inventory.md`.
Check the table against the files: every row has a decision and a target from formats.md.
The owner approves the table before anything moves.

**M2. Translation.** Engineering texts become English.
Produce a table «before → after» per document in `docs/temp/`.
A separate agent with fresh context translates the result back; list differences in meaning in the PR description.

**M3. Layout.** Apply the approved table, one PR for the step.
Move content with `git mv` where a file moves as a whole.
Personal notes of the owner go to `CLAUDE.local.md` (not in git) or `~/.claude/CLAUDE.md`, only with the owner's yes.
Run `mise run check`: `check-md-placement` fails on every `.md` left outside the structure.

## Gates

The template already brings `check-md-placement`, `check-agents-md`, `check-tasks-format`, rumdl, typos and lychee (`--offline` before push, online on schedule).
Propose to the owner, then wire through `quality-gates`:

- `check-doc-refs.mjs` as a check. Options: add it to the docustand template (every project gets it, no override), or a project task in `mise.toml` plus an `hk.pkl` step with an entry in `overrides`;
- a test per mirrored list from A2 that compares the list with the code, or generation of the list from code.

## Common mistakes

| Mistake | Instead |
|---|---|
| Hand-checking hundreds of paths | `check-doc-refs.mjs`, then only its hits |
| Writing deployment state into `docs/architecture.md` | GitHub Deployments or deploy tags |
| Rewriting an accepted ADR | A new ADR that links the old one |
| A journal or status file next to the docs | `docs/tasks.md` for work in progress, git and PRs for history |
| Plans and specs in `docs/` | `docs/temp/` (not in git) |
| Committing `CLAUDE.local.md` | It stays out of git; `AGENTS.md` and the one-line `CLAUDE.md` are in git |
| Describing what the project «probably» does | Only facts from code, config, ADRs or the owner |
| A long rule with exceptions in `AGENTS.md` | One line plus an ADR link |

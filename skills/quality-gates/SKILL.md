---
name: quality-gates
description: Use when a repository's code quality checks, linters, git hooks or CI gates under the docustand standard need to be audited, extended for a stack, or proven to fail on violations, especially so AI agents cannot degrade the codebase. Also for "quality gates", "настрой проверки качества", "линтеры и хуки", "чтобы агенты не портили код", "проверь, что проверки работают", "аудит качества репозитория".
---

# Quality Gates

<!-- doc-paths: another repository -->

Goal: a repository that checks itself.
Every gate exits non-zero on a violation, runs from one `mise run check` in hooks and CI, and has been seen failing.

Configs are not assembled by hand.
mise, hk, the check scripts, the tool configs, the CI workflows and the Claude Code guard hooks come from the docustand Copier template, which `/docustand:repo-init` applies.
The stack profile in `${CLAUDE_PLUGIN_ROOT}/profiles/<stack>.md` names the stack tools and commands.

Read [references/wiring.md](references/wiring.md) (standard files, tiers, overrides, baselines) and [references/environment.md](references/environment.md) (owner's machines) before any change.

## Modes

- **Audit** (default for «проверь», «аудит»): steps 1–3 and 7. Read-only.
- **Extend** («настрой», «добавь проверку»): all steps. Stop after step 3 and wait for the owner's approval of the plan.
- **Prove** («проверь, что проверки работают»): step 5 only.

## Steps

### 1. Inspect

- `.repo.yaml`: `level`, `stack`, `architecture`, `overrides`, `_commit` (template version).
- `mise run detect-stack`: compare its `stack` with `.repo.yaml`; a mismatch is a finding.
- `.config/hk.pkl`, `.mise/conf.d/standard.toml`, the project `mise.toml`, `.github/workflows/`.
- Tools outside the standard: husky, lefthook, pre-commit, `package.json` scripts, a `Makefile`, other workflows.
- Branch protection: `gh api repos/{owner}/{repo}/branches/<branch>/protection` (read-only; 404 means CI only reports).
- `git status` and the branch. Uncommitted changes belong to someone else: never stash, reset or commit them.

Run `mise run check` once and record the exit code and the failing steps.
Write captured output to the session scratchpad or `docs/temp/`, never into tracked files or `/tmp`.

Look for setups that do not enforce:

- a linter whose warnings exit 0, `continue-on-error: true` or `|| true` in CI;
- a check in a hook only, or in CI only, or CI running a different command than the hook;
- a formatter in write mode in CI;
- a standard file edited without an entry in `overrides`.

### 2. Compare with the template

Render the template version of the project aside (`_src_path` and `_commit` from `.repo.yaml`) and compare:

```bash
copier copy --defaults --vcs-ref <_commit> --data-file .repo.yaml <_src_path> docs/temp/rendered
${CLAUDE_PLUGIN_ROOT}/scripts/merge_existing.py conflicts . docs/temp/rendered --template ${CLAUDE_PLUGIN_ROOT}
```

Each listed file differs from the standard: it needs an entry in `overrides` with a reason, or a return to the template.
An outdated `_commit` is fixed by `copier update -a .repo.yaml --defaults` (the `repo-init` audit mode), not by hand.
Delete `docs/temp/rendered` afterwards.

### 3. Plan, then wait

For a gap, the order is:

1. The stack profile already has the tool: the answer `stack` is missing it; change it with `copier update -a .repo.yaml --defaults --data 'stack=[...]'`.
2. No profile for the stack: propose tools by the rule «use existing solutions first» in `AGENTS.md`, 2–3 options with registry data as of today, the recommended one marked. A new profile is a change of docustand (profile, template, test), not of the project.
3. A project-only check: a task in the project `mise.toml` and a step in `.config/hk.pkl` with an entry in `overrides`.

Check that each proposed tool is maintained and look up its latest release (`gh release view -R <repo>`).
Show the table, then the «not adopting» list with reasons:

| Tool | Job | Keeps / replaces / adds | Files touched | Tier (commit / push / CI) | Limit that matters here |
|---|---|---|---|---|---|

Ask only the owner's decisions: replacing a tool in use, a paid or copyleft tool, a check that fails on existing code and needs a baseline, a deviation from a standard file.

### 4. Apply (Extend mode, after approval)

One tool or one concern per commit.
A check red on the current tree gets a separate commit: safe autofix one tool at a time, the rest into the tool's baseline (wiring.md, «Existing code»).
Never lower a rule to a warning, add `|| true` or skip a step to get green.

### 5. Prove every gate fails

For each gate: clean `mise run check` → introduce one real violation → `mise run check` exits non-zero and names that step → revert → clean again.
Work on a scratch branch or a copy in `docs/temp/`; never leave the violation behind.
The violations used by `tests/integration/test_gates_fail.py` in docustand are the reference set: a fake secret, a typo, a Markdown lint error, a `.md` outside the structure, an unformatted `.tf`, a tflint finding, an invalid module, a dead internal link, a commit message with a Claude trailer.
Build secret-like strings at runtime, never as literals in a tracked file.

A gate not seen failing is reported as **unproven**, with the reason (needs network, a database, a token, the Docker VM).

### 6. Hooks installed

Hooks are proven by behaviour, not by files in `.git/hooks/`: commit `notes/probe.md`; `check-md-placement` must reject the commit.
Then `git reset` and delete `notes/probe.md`.
If the commit goes through, the hooks are not installed: `git reset --soft HEAD~1` and `git reset`, delete the file, run `hk install --mise` and probe again. Report it as a finding.

### 7. Report

Short, in the owner's language:

- added, kept, skipped, each with a reason; files per commit;
- setups that do not enforce, and whether they were fixed;
- standard files that differ from the template and their `overrides` state;
- baselines created, with finding counts;
- per gate: `seen failing: yes` or `unproven (reason)`;
- what was not run.

## Common mistakes

| Mistake | Instead |
|---|---|
| Writing `.config/hk.pkl` or a CI workflow by hand | Template files; `copier update` brings changes |
| Editing a standard file to get green | Fix the cause; a real deviation needs `overrides` and the owner's yes |
| Choosing tools from memory | Profile first; otherwise registry data as of today and the owner's choice |
| Assuming a check enforces because it exists | Run it, read the exit code and the CI wiring |
| A gate only in a hook | CI runs the same `mise run check` |
| Lowering a rule to `warn` | Baseline or one narrow exception with a reason |
| Checking `.git/hooks/` to prove hooks | A probe commit that must be rejected |
| Reporting done without a failing run | Prove each gate, or mark it unproven |

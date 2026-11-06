# Wiring gates so they enforce

## Standard files

The Copier template owns these files; `copier update` replaces them, and `.claude/settings.json` has an `ask` rule on each:

| File | Role |
|---|---|
| `.mise/conf.d/standard.toml` | Standard tools with pinned versions, the `check` task, `postinstall = "hk install --mise"` |
| `hk.pkl` | Steps per tier: `pre-commit`, `commit-msg`, `pre-push`, `check` |
| `.mise/tasks/*` | Check scripts: `check-md-placement`, `check-agents-md`, `check-tasks-format`, `check-repo-yaml`, `check-env-example`, `check-comments`, `check-baseline`, `detect-stack`, `pr-ready` and the profile scripts |
| `.github/workflows/standard-*.yml` | CI runs `mise run check`; the report workflow |
| `.claude/settings.json`, `.claude/hooks/*` | Guard hooks against bypasses, `ask` and `deny` rules |
| `commitlint.config.mjs`, `typos.toml`, `.rumdl.toml`, `lychee.toml`, profile configs such as `.tflint.hcl` | Tool configs as copies, no `extends` |

The project owns `mise.toml` (its own tools and tasks) and its own workflows; the template never writes them.

## Tiers

| Tier | Budget | Content |
|---|---|---|
| `pre-commit` | 5 s, changed files | Format, lint of changed files, secrets (Betterleaks), typos, comment mechanics, structure checks |
| `commit-msg` | | commitlint: Conventional Commits, no Claude or session trailers |
| `pre-push` | 1 min | Types, full lint, architecture rules, affected tests without Docker, internal links |
| CI | | Everything above plus the full test suite and the baseline growth check |
| Schedule | `report_schedule` | Run from scratch, stack detection, external links |

A check only in a hook is not enforced: CI runs the same `mise run check`.
Without branch protection, CI only reports; the scheduled report counts merges with red checks and bypasses.

## Deviations

A deviation from a standard file is an edit of that file plus an entry in `overrides` in `.repo.yaml`:

```yaml
overrides:
  - file: .rumdl.toml
    reason: generated API docs have no top-level heading
```

`overrides` changes only through `copier update -a .repo.yaml --defaults --data 'overrides=[...]'` (single-quoted: brackets are globs in zsh).
Copier keeps the edit on update or shows a conflict in the Renovate PR.
A deviation every project needs belongs in the docustand template instead.

## Existing code

1. Run each new tool over the whole project; count findings per rule.
2. Safe autofix, one tool per commit; read the diff. Never run a deleting autofix unattended.
3. The rest goes into the tool's baseline (PHPStan baseline, `eslint-suppressions.json`, dependency-cruiser known violations, `.size-baseline.json`). New violations fail, old ones are listed.
4. A rule that cannot be met: one path and one rule, with a reason. Never switch the rule off or lower it to a warning.
5. `check-baseline` in CI fails when a baseline file has more entries than at the base ref. A baseline file absent at the base is allowed only when `.repo.yaml` did not exist at the base or `_commit` changed, or `stack` changed and the file belongs to an added profile; the scheduled report lists new baseline files.

## Bypasses

- `--no-verify`, `git commit -n`, `git -c core.hooksPath=…`, `HK=0`, `HK_SKIP_*` and `hook.*` keys in `git -c` or `git config` are blocked by the guard hook.
- An emergency bypass of a local hook carries a `Skip-Check: <check> — <reason>` trailer; CI ignores the trailer and runs everything, and the report lists every such commit.

## AGENTS.md

The template renders the rules backed by checks (Working rules, Before a PR, Comments).
Add a project rule only when a check backs it, and keep `AGENTS.md` within 150 lines.

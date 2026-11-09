---
name: repo-init
description: Use to bring a repository to the docustand standard or keep it there — a new or empty repository, an existing codebase without the standard (migration), an audit and template update of a repository that already has `.repo.yaml`, a changed answer such as level, stack or report schedule, or detaching a repository from docustand. Also for "подключи стандарт", "заведи репозиторий", "мигрируй репозиторий", "обнови шаблон", "отвяжи от docustand".
---

# repo-init

The single entry point of docustand.
It inspects the repository, asks only what the code does not answer, applies the Copier template and switches on what GitHub needs.

Plugin root: `${CLAUDE_PLUGIN_ROOT}` — substitute this absolute path in every command from `references/`; those files are read raw, without substitution.

References, read when the step needs them:

- [references/reconnaissance.md](references/reconnaissance.md): what to find out before any question.
- [references/questions.md](references/questions.md): the questions, their conditions and the option format.
- [references/migration.md](references/migration.md): the six migration steps for an existing codebase.
- [references/maintenance.md](references/maintenance.md): audit, `copier update`, changing an answer, detach.

## Rules

- Inspect first, then ask all questions in one list, then change files.
- Mandatory steps run without a question; everything optional is asked first, with options (questions.md).
- Answers live in `.repo.yaml` and, when a decision has a reason and alternatives, in an ADR. A repeated run reads them and does not ask again.
- Temporary files go to `docs/temp/` of the target project, never to `/tmp`.
- While the repository follows the template, never edit `.repo.yaml` by hand. An answer changes only with `copier update -a .repo.yaml --defaults --data <key>=<value>`.
- Before any `copier update`, `git status --porcelain` must print nothing. Otherwise stop and tell the owner to commit first.
- Every manual `copier update` passes `-a .repo.yaml`: Copier 9.19.1 does not find a custom answers file by itself. Renovate passes `--answers-file` on its own.
- Single-quote every `--data` whose value is a list or a mapping (`--data 'stack=[terraform]'`): unquoted brackets and braces are globs in zsh and fail with «no matches found».
- Commits and PRs follow the target's `AGENTS.md`; hooks are never bypassed.
- Pushing to GitHub needs the owner's explicit yes.
- Rewrite git history only to remove credentials (passwords, keys, tokens), and only after the owner has changed them. Internal network addresses, MAC addresses and hardware serial numbers are not secrets; a history scan reports them, and the history stays.

## 1. Preconditions

1. `command -v mise`. If mise is missing, stop and show the install command (`brew install mise`, or `curl https://mise.run | sh`). Do not install it.
2. `gh auth status`. Without GitHub access, the GitHub steps below are reported as not done.

## 2. Mode

| What the repository has | Mode |
|---|---|
| No files besides `README.md`, `LICENSE`, `.gitignore`, or no repository at all | New |
| Code or documents, no `.repo.yaml` | Migration (migration.md) |
| `.repo.yaml` with `_src_path` | Audit and update (maintenance.md) |
| `.repo.yaml` without `_src_path` (detached) | Ask the owner what to do; re-attaching is out of scope |
| The owner asks to detach | Detach (maintenance.md) |

## 3. Reconnaissance and questions

Run reconnaissance.md, then ask questions.md in one message and wait for the answers.
Level `full` is offered with its description, and it is not available yet: the template rejects it with «Level "full" is not supported yet». Say so in the option and continue with `base`.

## 4. Template source

- Source: `gh:AnatoliiKo/docustand` at the latest tag, the tag name (`vX.Y.Z`) from the first line of `git ls-remote --tags --refs --sort=-v:refname https://github.com/AnatoliiKo/docustand 'v*' | head -1 | sed 's#.*refs/tags/##'`; the line itself is `<sha>`, a tab and `refs/tags/vX.Y.Z`. `_src_path` and `_commit` in `.repo.yaml` then let Renovate update the template.
- No tag yet: `--vcs-ref main`. `_commit` then records a commit, and Renovate follows tags only after a one-time `copier update -a .repo.yaml --defaults --vcs-ref <first tag>`.
- Repository unreachable (`git ls-remote` fails): use `${CLAUDE_PLUGIN_ROOT}` only if it is a git checkout (`git -C ${CLAUDE_PLUGIN_ROOT} rev-parse --show-toplevel` prints it); otherwise stop. Warn the owner: `_src_path` records a local path and Renovate cannot update the template. The remedy after publication is a one-time edit of `_src_path` to `gh:AnatoliiKo/docustand`, approved by the owner, then `copier update -a .repo.yaml --defaults --vcs-ref <first tag>`.

Below, `<template>` and `<ref>` are this source and ref.
Until `mise install` brings Copier from `standard.toml`, run Copier as `mise exec uv@0.13.7 pipx:copier@9.19.1 -- copier ...`.

## 5. New repository

1. `git init -b main` if there is no repository. A git repository must exist before `mise install`: the standard `postinstall` hook runs `hk install --mise`.
2. Apply the template with every answer as `--data` (lists and mappings in YAML flow form, single-quoted):

   ```bash
   mise exec uv@0.13.7 pipx:copier@9.19.1 -- copier copy --defaults --vcs-ref <ref> \
     --data project_name=<name> --data level=base --data 'stack=[terraform]' \
     --data report_schedule=weekly --data 'required_ci_branches=[main]' \
     <template> .
   ```

3. An existing `.gitignore` is kept (`_skip_if_exists`), so the standard lines are merged in: render the same answers into `docs/temp/rendered` (the command above with `docs/temp/rendered` as the destination), then `${CLAUDE_PLUGIN_ROOT}/scripts/merge_existing.py merge . docs/temp/rendered`, then delete `docs/temp/rendered`.
4. `mise trust`, then `mise install`: installs the tools and runs `hk install --mise`.
5. `mise run check` exits 0.
6. Commit the result through the hooks: `chore: apply repository standard`.
7. Prove the hooks by behaviour, not by `.git/hooks/`: write `notes/probe.md`, `git add notes/probe.md`, `git commit -m "chore: probe"`. `check-md-placement` must reject the commit. Then `git reset` and delete `notes/probe.md`. If the commit goes through, `git reset --soft HEAD~1` and `git reset`, delete the file, run `hk install --mise` and probe again.
8. GitHub steps (section 6).
9. For a repository with an API: an ADR on the contract approach (question «API»).

## 6. GitHub steps

With `{owner}/{repo}` from `gh repo view --json nameWithOwner -q .nameWithOwner`.
A new repository first needs a GitHub repository and a push: both only after the owner's explicit yes.
Branch protection waits until each branch exists on GitHub; until then report it as pending.

1. Vulnerability alerts, mandatory: `gh api -X PUT repos/{owner}/{repo}/vulnerability-alerts`. Check: `gh api repos/{owner}/{repo}/vulnerability-alerts` answers 204.
2. Branch protection per `required_ci_branches`, if the plan allows it (reconnaissance.md, «GitHub»). For each branch that exists on GitHub:

   ```bash
   gh api -X PUT repos/{owner}/{repo}/branches/<branch>/protection --input - <<'JSON'
   {"required_status_checks": {"strict": false, "contexts": ["check"]},
    "enforce_admins": false, "required_pull_request_reviews": null, "restrictions": null}
   JSON
   ```

   `check` is the job of `standard-ci.yml`. If the plan does not allow protection (Free, private repository), say plainly: CI only reports; local hooks are the only blocking layer; the scheduled report counts merges with red checks. The branches stay in `required_ci_branches`, so one command enables protection after a plan change.
3. Report secrets, only with the owner's explicit consent and only when `report_schedule` is not `off`. The report GitHub App needs Contents read and write, Pull requests read and write, Administration read. The owner installs it on the repository; then:

   ```bash
   gh secret set REPORT_APP_CLIENT_ID --repo {owner}/{repo}
   gh secret set REPORT_APP_PRIVATE_KEY --repo {owner}/{repo} < <path to the .pem the owner names>
   ```

   The Client ID is on the page of the App; the App ID works as the value too. The owner types or points to the values; they never appear in the chat. The template already lists the App in `docs/access.md`; fill in the owner.
4. Without consent, say that the report workflow fails until both secrets exist.

## 7. Finish

Report in the owner's language: mode, answers, files created, GitHub steps done or not done with the reason, hooks proven, `mise run check` result, what is left to the owner.
Delete what this run left in `docs/temp/` unless the owner still needs it (the inventory, the translation table).

---
name: repo-init
description: Use to bring a repository to the docustand standard or keep it there — a new or empty repository, an existing codebase without the standard (migration), an audit and template update of a repository that already has `.repo.yaml`, a changed answer such as level, stack or report schedule, or detaching a repository from docustand. Also for "подключи стандарт", "заведи репозиторий", "мигрируй репозиторий", "обнови шаблон", "отвяжи от docustand".
---

# repo-init

The single entry point of docustand.
It inspects the repository, asks only what the code does not answer, applies the Copier template and switches on what GitHub needs.

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
- Never edit `.repo.yaml` by hand. An answer changes only with `copier update -a .repo.yaml --defaults --data <key>=<value>`.
- Before any `copier update`, `git status --porcelain` must print nothing. Otherwise stop and tell the owner to commit first.
- Every manual `copier update` passes `-a .repo.yaml`: Copier 9.19.1 does not find a custom answers file by itself. Renovate passes `--answers-file` on its own.
- Commits and PRs follow the target's `AGENTS.md`; hooks are never bypassed.

## 1. Preconditions

1. `command -v mise`. If mise is missing, stop and show the install command (`brew install mise`, or `curl https://mise.run | sh`). Do not install it.
2. `gh auth status`. Without GitHub access, the GitHub steps below are reported as not done.

## 2. Mode

| What the repository has | Mode |
|---|---|
| No files besides `README.md`, `LICENSE`, `.gitignore`, or no repository at all | New |
| Code or documents, no `.repo.yaml` | Migration (migration.md) |
| `.repo.yaml` with `_src_path` | Audit and update (maintenance.md) |
| The owner asks to detach | Detach (maintenance.md) |

## 3. Reconnaissance and questions

Run reconnaissance.md, then ask questions.md in one message and wait for the answers.
Level `full` is offered with its description, and it is not available yet: the template rejects it with «Level "full" is not supported yet». Say so in the option and continue with `base`.

## 4. Template source

- Source: `gh:AnatoliiKo/docustand` at the latest release tag (`gh release view -R AnatoliiKo/docustand --json tagName -q .tagName`). `_src_path` and `_commit` in `.repo.yaml` then let Renovate update the template.
- No release yet: `--vcs-ref main`, and tell the owner that Renovate raises updates only after the first tag.
- Repository unreachable (`git ls-remote https://github.com/AnatoliiKo/docustand` fails): `${CLAUDE_PLUGIN_ROOT}` only if it is a git checkout, with the warning that `_src_path` then records a local path and Renovate cannot update the template.

Below, `<template>` and `<ref>` are this source and ref.

## 5. New repository

1. `git init -b main` if there is no repository. A git repository must exist before `mise install`: the standard `postinstall` hook runs `hk install --mise`.
2. Apply the template with every answer as `--data` (lists in YAML flow form). Copier is not installed before the template brings `standard.toml`, so the first run goes through mise:

   ```bash
   mise exec pipx:copier@9.19.1 -- copier copy --defaults --vcs-ref <ref> \
     --data project_name=<name> --data level=base --data stack=[terraform] \
     --data report_schedule=weekly --data required_ci_branches=[main] \
     <template> .
   ```

3. `mise trust`, then `mise install`: installs the tools and runs `hk install --mise`.
4. `mise run check` exits 0.
5. Commit the result through the hooks: `chore: apply repository standard`.
6. Prove the hooks by behaviour, not by `.git/hooks/`: write `notes/probe.md`, `git add notes/probe.md`, `git commit -m "chore: probe"`. `check-md-placement` must reject the commit. Then `git reset` and delete `notes/probe.md`. If the commit goes through, `git reset --soft HEAD~1` and `git reset`, delete the file, run `hk install --mise` and probe again.
7. GitHub steps (section 6).
8. For a repository with an API: an ADR on the contract approach (question «API»).

## 6. GitHub steps

With `{owner}/{repo}` from `gh repo view --json nameWithOwner -q .nameWithOwner`:

1. Vulnerability alerts, mandatory: `gh api -X PUT repos/{owner}/{repo}/vulnerability-alerts`. Check: `gh api repos/{owner}/{repo}/vulnerability-alerts` answers 204.
2. Branch protection per `required_ci_branches`, if the plan allows it (reconnaissance.md, «Plan»). For each branch:

   ```bash
   gh api -X PUT repos/{owner}/{repo}/branches/<branch>/protection --input - <<'JSON'
   {"required_status_checks": {"strict": false, "contexts": ["check"]},
    "enforce_admins": false, "required_pull_request_reviews": null, "restrictions": null}
   JSON
   ```

   `check` is the job of `standard-ci.yml`. If the plan does not allow protection (Free, private repository), say plainly: CI only reports; local hooks are the only blocking layer; the scheduled report counts merges with red checks. The branches stay in `required_ci_branches`, so one command enables protection after a plan change.
3. Report secrets, only with the owner's explicit consent and only when `report_schedule` is not `off`. The report GitHub App needs Contents read and write, Pull requests read and write, Administration read. The owner installs it on the repository; then:

   ```bash
   gh secret set REPORT_APP_ID --repo {owner}/{repo}
   gh secret set REPORT_APP_PRIVATE_KEY --repo {owner}/{repo} < <path to the .pem the owner names>
   ```

   The owner types or points to the values; they never appear in the chat. Record the App in `docs/access.md` (owner, «GitHub Actions secrets», `never`).
4. Without consent, say that the report workflow fails until both secrets exist.

## 7. Finish

Report in the owner's language: mode, answers, files created, GitHub steps done or not done with the reason, hooks proven, `mise run check` result, what is left to the owner.
Delete what this run left in `docs/temp/` unless the owner still needs it (the inventory, the translation table).

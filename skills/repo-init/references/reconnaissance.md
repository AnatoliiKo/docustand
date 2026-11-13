# Reconnaissance

<!-- doc-paths: another repository -->

Find out everything the code and GitHub answer before asking anything.
Record the findings in `docs/temp/recon.md` of the target project; they feed the questions and the final report.
Before the template adds `docs/temp/` to `.gitignore`, never stage that folder.

## Stack

- Before the template is in the repository: `uv run --script ${CLAUDE_PLUGIN_ROOT}/template/.mise/tasks/detect-stack <dir>`.
  Without `uv` on `PATH`: prefix the command with `mise exec uv@0.13.7 --`.
- After the template is in the repository: `mise run detect-stack`.
- Output: `{"stack": [...], "evidence": {profile: [paths]}}`. A profile in `stack` has a file in `${CLAUDE_PLUGIN_ROOT}/profiles/`; read it for tools and commands.
- Also read the manifests: `package.json`, `composer.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `*.tf`, Dockerfiles, compose files. Code without a profile is a finding: the question «Stack» applies.

## Architecture

From the folder structure, for code only (not for infrastructure or documentation repositories):

| Sign | Methodology |
|---|---|
| `entities/`, `features/`, `widgets/` (with `shared/`); `app/` and `pages/` alone are a Next.js router, not a sign | Feature-Sliced Design |
| `domain/`, `application/`, `infrastructure/` or `controllers/`, `services/`, `repositories/` | Layers |
| Framework layout only | Framework conventions of the profile |

Existing architecture configs: `.dependency-cruiser.js`, `deptrac.yaml`, Steiger config, eslint-plugin-boundaries rules.

## Existing checks and configs

Linters, formatters and their configs, git hooks (husky, lefthook, pre-commit, hk), CI workflows and the commands they run, `mise.toml`, `.tool-versions`, `.github/renovate.json`, Dependabot config.
For a migration, `merge_existing.py conflicts` later lists the exact files that differ from the template (migration.md).

## GitHub

- Repository: `gh repo view --json nameWithOwner,visibility,defaultBranchRef,isInOrganization`, or `gh api repos/{owner}/{repo}` (`visibility`, `default_branch`, `owner.type`).
- Plan: for a user account `gh api user -q .plan.name`; for an organization `gh api orgs/{org} -q .plan.name`.
  The field is empty when the token cannot read the plan (for a user account, without the `user` scope); an empty plan counts as `free`.
  Do not ask the owner to widen the token scopes for this.
- Plan allows branch protection: the repository is public, or the plan is not `free`.
- Branches: `gh api repos/{owner}/{repo}/branches -q '.[].name'`; long-lived branches are the default branch and branches such as `develop`, `staging`, `release/*`.
- Current protection: `gh api repos/{owner}/{repo}/branches/<branch>/protection` (404: none).
- Vulnerability alerts: `gh api repos/{owner}/{repo}/vulnerability-alerts` (204: on, 404: off).
- No GitHub repository yet: GitHub steps wait until the owner creates one; ask whether to create it with `gh repo create` (a public or private choice is the owner's).

## Neighbours and files outside git

- Sibling directories of the repository root that are git repositories: `ls ..` and `git -C ../<dir> remote get-url origin`.
  A sibling alone is not a sign of a system: a folder such as `~/Dev` holds unrelated projects.
  A sibling counts only when this repository references it (next item) or it references this repository.
- References to other repositories: URLs of the owner's repositories in docs, CI, `package.json` dependencies, `composer.json` repositories, API base URLs, an OpenAPI client.
- Files outside git next to the repository: untracked and ignored files with `git status --ignored --porcelain`, and files in the parent folder that belong to the project (notes, exports, `.env` copies). Never read the content of secret files; list them by name.

## API

- Provider signs: an OpenAPI or TypeSpec file, a router with HTTP endpoints, a GraphQL schema.
- Consumer signs: a generated client, a base URL of another service, an SDK of the owner's other repository.

## Existing answers

`.repo.yaml` and `docs/decisions/` already answer some questions; never ask those again.

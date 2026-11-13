---
name: pr-ready
description: Use before opening a pull request in a repository under the docustand standard — runs the checks, has the reviewer agent check the diff against the review checklist in AGENTS.md, records the verified commit and drafts the PR description. Also for "готово к PR", "проверь перед PR", "сделай ревью ветки", "pr-ready".
---

# pr-ready

<!-- doc-paths: another repository -->

The steps of the section `Before a PR` in `AGENTS.md`, with an independent review.
Temporary files go to `docs/temp/pr-review/`; it is ignored by git.

## Rules

- The reviewer gets the diff and the task, never this conversation or a summary of the implementation: the review stays independent.
- Pushing and creating the pull request need the owner's explicit yes.
- A blocking finding is fixed before the pull request or the owner decides in words to keep it; the decision goes to the PR description under `Why`.
- Hooks are never bypassed.

## Steps

1. `git status --porcelain` prints nothing; otherwise stop and tell the owner to commit first.
2. Base branch: `git symbolic-ref --short refs/remotes/origin/HEAD` without the `origin/` prefix; without a remote HEAD, the first branch of `required_ci_branches` in `.repo.yaml`. Base commit: `git merge-base HEAD origin/<base>`.
3. `mise run check` exits 0; otherwise fix the cause and commit.
4. Write the review input:

   ```bash
   mkdir -p docs/temp/pr-review
   git diff <base commit>...HEAD > docs/temp/pr-review/diff.patch
   git log --format='%h %s' <base commit>..HEAD > docs/temp/pr-review/commits.txt
   ```

5. Run the agent `docustand:reviewer` with the project root, both paths and the task heading from `docs/tasks.md` or the ADR of the branch.
6. Show the table to the owner. Fix the blocking findings with tests and commit; the owner chooses which recommendations to take. After fixes, repeat steps 3–5 once.
7. `mise run pr-ready`: it runs `mise run check` again and records the verified HEAD for the PR hook.
8. Draft the PR description in the format of `AGENTS.md` (`Text rules`) into `docs/temp/pr-review/description.md`, then check it:

   ```bash
   PR_BODY="$(cat docs/temp/pr-review/description.md)" mise run check-pr-body
   ```

9. Report: the findings and what was fixed, the verified commit, the path of the description. Push and `gh pr create --body-file docs/temp/pr-review/description.md` only after the owner's yes.
10. After the pull request exists, delete `docs/temp/pr-review/`.

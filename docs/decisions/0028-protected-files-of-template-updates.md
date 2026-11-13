# 0028. Protected files of template updates

Date: 2026-11-13
Status: accepted

## Context

- The report section «Protected files» counted a template update only when Renovate authored it.
- In `cinema-ops` the owner ran `copier update` by hand in 4 pull requests; each listed up to 30 standard files as protected changes.
- Pull requests that only shrank `.baselines/` files were listed too, although `check-baseline` already forbids growth.

## Decision

- A pull request that changes `_commit` in `.repo.yaml` is a template update, whatever its author; it appears in «Template updates».
- In a template update the files that the template renders for the answers of `.repo.yaml` are no protected-file findings.
- A changed or deleted `.baselines/` file is no protected-file finding; a new one stays in «New baseline files».
- Commits by other authors in a Renovate pull request stay findings.

## Rejected

- Comparing every rendered file with the template output of the new version: the report would need Copier and the template on the runner.
- Removing `.baselines/**` from the protected list: an agent must still ask before it edits a baseline.

## Consequences

- A hand edit of a standard file hidden in a template update is not reported; the review of the pull request and `check-root --since` cover it.
- The protected-file section of `cinema-ops` shrank from 16 pull requests to 9 in the dry run of 2026-11-13.

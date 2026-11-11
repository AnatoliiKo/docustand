# 0021. Checked hygiene rules

Date: 2026-11-11
Status: accepted

## Context

- The audit of `cinema-ops` on 2026-11-11 found 39 root entries, 18 of 43 ADRs over 80 lines, addenda inside accepted ADRs and 8435 comment lines.
- The owner set 25 rules; a rule without a check or a number drifts.
- Old violations are too many to fix before a check starts.

## Decision

- `check-root`: tracked root entries come from `.mise/data/root-files.txt` of the stack and `root_files` of `.repo.yaml`.
- `check-adr`: a `Status:` line, the sections Context, Decision, Rejected, Consequences, 80 lines at most, and a `Supersedes:` line in the ADR that supersedes another.
- `check-adr-history` in CI: an accepted ADR changes only its `Status:` line and is not deleted.
- `check-comments` fails on dates, addenda, decision attribution and change history in comments; quoted values, file names and dates in tests pass.
- Old violations go to `.baselines/` with `until` per entry; an entry only shrinks, `until` never moves later, and an expired entry fails.
- The rules live in `AGENTS.md`; `CLAUDE.md` imports it.

## Rejected

- Fix every old violation before the checks start: the checks would wait for weeks while new violations arrive.
- A baseline without a date: it never shrinks.
- Names in comments by pattern: a name has no pattern; review catches it.

## Consequences

- A template update adds `.baselines/` entries in projects with old ADRs and comments.
- A new root file needs `root_files` through `copier update --data`.
- The `cinema-ops` plan of the remaining rules is in `docs/temp/hygiene-rules-plan.md`.

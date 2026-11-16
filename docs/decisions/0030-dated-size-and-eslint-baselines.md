# 0030. Dated size and ESLint baselines

Date: 2026-11-16
Status: accepted

## Context

- ADR 0021 gives every `.baselines/` entry an `until` date; `adr.json` and `comments.json` have one, `size.json` and `eslint-suppressions.json` do not.
- Without a date an old violation stays in a baseline for good: the ratchet stops growth, not stagnation.
- ESLint owns the format of `eslint-suppressions.json`; ESLint 10 reads `count` of a rule and keeps the other fields of a rule when it prunes the file.
- `betterleaks.ignore` holds known false positives of the secrets scan, not violations to fix.

## Decision

- An entry of `size.json` holds `lines` and `until`; `check-size` fails on an entry without a date or past it.
- A rule entry of `eslint-suppressions.json` holds `until` next to `count`; `check-eslint-suppressions` fails on an entry without a date or past it.
- Both checks run on every commit, so an expired entry fails without a change of the file.
- A migration records new entries with `until` 90 days ahead; `check-baseline` fails when an `until` moves later.
- `betterleaks.ignore` stays without dates.

## Rejected

- A sidecar file with dates of the ESLint suppressions: two files describe one entry and drift apart.
- One date for a whole baseline file: an entry fixed early does not shorten the others, and the report cannot name the next due entry.
- Dates on `betterleaks.ignore`: a false positive does not expire; a periodic renewal teaches to renew without looking.

## Consequences

- An update to 0.10.0 rewrites a non-empty `size.json` and stamps the ESLint suppressions, see `skills/repo-init/references/maintenance.md`.
- `eslint --suppress-all` writes entries without `until`; `check-eslint-suppressions --stamp` dates them.
- A future ESLint version that rejects unknown fields breaks the format; the integration test of the `typescript` profile runs ESLint on a dated file.

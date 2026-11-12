# 0024. Document types and internal JSDoc

Date: 2026-11-12
Status: accepted

## Context

- `check-md-placement` allowed any `docs/*.md`; in `cinema-ops` a hand-written copy of the Telegram texts lived there next to the code that builds them.
- The rule «JSDoc documents the exported API only» had no check; `cinema-ops` held 822 JSDoc blocks on internal declarations.
- `check-adr-history` keeps an accepted ADR unchanged, so the 42 ADRs of the `cinema-ops` baseline could never reach the format.

## Decision

- `docs/` holds `architecture.md`, `tasks.md`, `access.md` and `operations.md`; any other document is an entry in `md_exceptions`, decided by the owner.
- A generated document names its generator in its first lines; a test or a check of the project keeps it current.
- `check-comments` reports a JSDoc block without tags above a non-exported declaration or a private member; the comments baseline covers old findings.
- An ADR of `.baselines/adr.json` may be rewritten into the format in the change that drops its baseline entry.

## Rejected

- A list of document types with headers to parse: the four standard documents and the exceptions list cover the repositories in use.
- An ESLint plugin rule for JSDoc: `check-comments` already reads every comment, with one baseline for all comment rules.
- A separate migration command for ADRs: the baseline entry already marks an ADR as not yet in the format.

## Consequences

- An update to 0.6.0 lists every other `docs/*.md` in `md_exceptions` or removes it.
- An update to 0.6.0 converts internal JSDoc or records it with `check-comments --write-baseline`.
- A rewritten ADR keeps its decision; the review of the pull request checks that only the structure changed.

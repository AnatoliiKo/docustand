# 0005. API contract approach

Date: 2026-11-05
Status: accepted

## Context

- Contracts between parts of a system drift when written by hand.
- Consumers differ from providers mostly in fields, not in methods and paths.
- Options for the contract: derived from code; derived from a schema; written by hand.
- Options for consumer verification: a code graph; a generated client.

## Decision

- Existing projects derive the contract from code and verify responses in tests.
- New projects record the approach in an ADR at creation. The default comes from the stack profile.
- Consumers verify the contract with a generated client.
- The contract check is enabled by the `contract` field in `.repo.yaml`, on any level.

## Rejected

- Handwritten contract: drifts.
- Code graph on consumers: sees method and path, misses field differences.

## Consequences

- Consumer CI checks that the pinned copy matches the source at the recorded commit and that regeneration produces no diff.
- Contract lag at the consumer appears in the report.

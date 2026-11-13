# 0026. Documents about other repositories

Date: 2026-11-13
Status: accepted

## Context

- `check-doc-paths` of ADR 0025 reported 30 paths in the skills, profiles and agents of docustand.
- These documents name files of the repositories that docustand sets up, such as `docs/operations.md` of a deployed project.
- `docs/decisions/NNNN-slug.md` is a name pattern, not a path.

## Decision

- A document with the line `<!-- doc-paths: another repository -->` is not checked by `check-doc-paths`.
- A path with a repeated capital (`NNNN`, `YYYY`, `XX`) is a placeholder and is not checked.

## Rejected

- Skipping every document of `md_exceptions`: in `cinema-ops` the stale `resolve.ts` path was in `docs/sources/direct.md`, an exception.
- A list of skipped documents in `.repo.yaml`: the marker stays with the document and moves with it.

## Consequences

- A skill, a profile or a guide about other repositories carries the marker after its title.
- A document with the marker gets no path check; its paths are reviewed in the pull request.

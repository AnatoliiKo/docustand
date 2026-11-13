# 0025. Comment language and document paths

Date: 2026-11-13
Status: accepted

## Context

- The audit of `cinema-ops` after 0.6.0 found Russian comments in a Dockerfile, `.gitignore`, a PowerShell script and configs; `check-comments` read none of these file types and had no language rule.
- Documents named paths absent from the code, such as a file that became a folder; no check compared document paths with the tree.
- The template wrote the scheduled workflow note to both `README.md` and `docs/operations.md`.

## Decision

- `check-comments` reads JavaScript and TypeScript variants, `.pkl`, `.ps1`, YAML, TOML, Dockerfiles and ignore files.
- A comment block with three Cyrillic words in a row outside «…», backticks or double quotes is not in English; the comments baseline covers old findings.
- `check-doc-paths` reads inline code spans of Markdown documents outside fenced blocks; a span that starts with a tracked root folder must exist, be ignored by git or end a tracked path.
- ADRs and `CHANGELOG.md` are not checked: they record the state of their date.
- A deployed project keeps the scheduled workflow note in `docs/operations.md`; `README.md` holds it only without that document.

## Rejected

- Any Cyrillic letter as a finding: UI strings wrap across comment lines, and folder names such as «ОБЛАКО» are data.
- «no longer» and «anymore» as history markers: in `cinema-ops` the sampled matches described runtime behaviour, not history.
- A baseline for `check-doc-paths`: a stale path is fixed in minutes, and a hidden one misleads the next reader.
- Strings of configs, such as dependency-cruiser rule comments: a string can be data, and the line scan cannot tell.

## Consequences

- An update to 0.7.0 translates comments or records them with `check-comments --write-baseline`, and fixes document paths.
- Every change runs `check-doc-paths`, since a moved file breaks a path in a document that the change does not touch.

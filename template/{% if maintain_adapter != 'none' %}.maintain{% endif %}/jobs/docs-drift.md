# Job docs-drift

## Goal

Align documents with the code: a path, command, name or number in a document that the code contradicts.

## Steps

1. Read each Markdown file the job may change and check every claim about the repository against the code.
2. Correct the document. Keep its structure, language and style.
3. Run `mise run check` and fix the findings in documents.

## Do not

- Change code, configuration, ADRs, `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, `docs/tasks.md`, generated documents or documents listed in `md_exceptions`.
- Add a baseline entry, a suppression or an exception.
- Move lines in a file that has an entry in `betterleaks.ignore`, rename a file that has a baseline entry, or add a suppression to code.
- Commit, push or open a pull request: `mise run maintain` does it.

## No changes

When every document matches the code, change nothing. The job then ends without a pull request.

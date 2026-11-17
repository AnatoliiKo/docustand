# 0033. Project language

Date: 2026-11-17
Status: accepted
Supersedes: [ADR 0025](0025-comment-language-and-document-paths.md) (the comment language rule)

## Context

The standard fixes English for every engineering text. Projects that keep documents in Russian end with Russian documents and English comments, or the reverse.

## Decision

- The answer `language` takes `en`, `ru` or `auto`; the default is `en`.
- One value covers comments, Markdown documents, ADRs, tasks, commit messages and PR texts.
- `check-comments` fails on a comment outside `language`; a Markdown check applies the same detector to prose. Code, identifiers, paths and quoted UI strings stay outside the check.
- Commit and PR texts follow `language` through the rendered `AGENTS.md`; no check enforces them.
- `auto` resolves once during `repo-init`. The detector counts prose blocks of documents first and comments second. A language above 80 % of the blocks wins; otherwise `repo-init` asks the owner. The resolved value `en` or `ru` is stored in `.repo.yaml`.
- The old text of the other language moves through a translation task with a dated baseline entry.
- The document path rule of ADR 0025 stays in force.

## Rejected

- English only: contradicts the language of the owner's projects.
- Separate languages for comments and documents: produces the mixed state the rule prevents.
- `auto` evaluated on every check run: the share changes with each commit, so the check flaps.

## Consequences

- `AGENTS.md.jinja` renders its text rules per language.
- Projects with the default `en` keep their behaviour.
- The detector needs tests for both languages and for mixed blocks.

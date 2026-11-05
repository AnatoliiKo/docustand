# Document formats

The layout is the repository standard of docustand.
The rendered `AGENTS.md` of the project is the source for its rules; this file explains the layout to the skill.

## Layout

| File | Holds | In git |
|---|---|---|
| `README.md` | What it is, how to install the tools and run it, where the other documents are | yes |
| `AGENTS.md` | Structure, stack, architecture and its rules, working rules, text rules; 150 lines at most | yes |
| `CLAUDE.md` | One line: `@AGENTS.md` | yes |
| `CLAUDE.local.md` | Owner's personal notes about the project | no |
| `docs/architecture.md` | System map: parts, links, data flows, external services, data model, glossary, architecture methodology | yes |
| `docs/decisions/NNNN-slug.md` | One project decision per file, one page at most | yes |
| `docs/tasks.md` | `In progress` and `Backlog` in the strict format | yes |
| `docs/access.md` | Required accesses, account owners, secret locations, expiry dates; never the secrets | yes |
| `docs/operations.md` or `docs/runbooks/` | Deployed systems only: deploy, rollback, restore with the last check date, alerts | yes |
| `docs/<topic>.md` | A guide, only when needed, linked from `README.md` or `docs/architecture.md` | yes |
| `CHANGELOG.md` | Only in versioned repositories | yes |
| `docs/temp/` | Temporary output of skills and agents, plans and specs of superpowers | no |

Any other `.md` file fails `check-md-placement` unless its path is in `md_exceptions` in `.repo.yaml`.
Removed during migration: journals, status snapshots, plan and spec folders, README files in subfolders, scattered notes.
A fact is stated once; documents link to the contract file, `mise tasks` and `.env.example` instead of copying them.

## ADR

```markdown
# 0007. Short decision title

Date: 2026-11-05
Status: accepted

## Context

What happened or what is in the way. Facts, two or three paragraphs.

## Decision

What is done: files, rules, thresholds, who runs what.

## Rejected

Each alternative in one line with the reason.

## Consequences

What changes for the code, the owner and the checks.
```

- Number: the next free number in `docs/decisions/`.
- Status: a decision the owner states is `accepted` with today's date; a proposal is `proposed` until the owner's yes.
- A changed decision is a new ADR that links the old one; the old one gets `Status: replaced by ADR NNNN`.

## architecture.md

Sections, each only if the project has it: Parts → Data flows → External services → Data model → Glossary → Architecture methodology.
It describes how the system is built, not its deployment state.
Link decisions as «ADR NNNN».

## AGENTS.md

The template renders the sections Structure, Stack, Architecture, Working rules, Text rules, Before a PR, Comments, Use existing solutions first.
Project facts go into these sections; the limit is 150 lines (`check-agents-md`).
A rule with a long list of exceptions moves to an ADR; `AGENTS.md` keeps one line and the link.
A list that mirrors code either has a check that compares it with the code or is replaced by a pointer to the code.

## docs/tasks.md

The format is in the Text rules of `AGENTS.md` and is checked by `check-tasks-format`.
A task taken into work moves to `In progress` with `Stopped at` and `Next`.
A finished task is deleted; its result stays in the PR.

## Language

Engineering texts are English: documentation, ADRs, tasks, comments, commits, PRs.
UI strings, localization and test data may use other languages.
Code identifiers, commands and paths stay as they are, in backticks.
Reports to the owner are in the owner's language.

# 0027. Hygiene sections of the report

Date: 2026-11-13
Status: accepted

## Context

- Rule 25 of the owner's hygiene rules asks for a regular hygiene review.
- The scheduled report covered tokens, alerts, merges and template updates, but not work that stops: a forgotten pull request, a task in progress without progress, a baseline that nobody shrinks.
- A solo repository changes rarely; `cinema-ops` keeps `report_schedule: monthly`.

## Decision

- The report frequency stays the `report_schedule` answer; `repo-init` recommends `weekly` for a team.
- The report lists open pull requests without an update for 14 days, except the `report` pull request.
- The report lists tasks of `In progress` in `docs/tasks.md` whose lines `git blame` dates more than 30 days back.
- The report lists the entry count of each non-empty `.baselines/` file as information, without a pull request.
- A baseline entry with `until` within 30 days is a finding.
- These sections run on every report, also without activity: inactivity is the finding.

## Rejected

- A weekly report for every project: a solo repository gets the same finding four times a month.
- A non-empty baseline as a finding: `cinema-ops` keeps 71 test passwords in `.baselines/betterleaks.ignore` on purpose, so the report would never close.
- An agent audit of documentation against code on schedule: it costs a model run each time; a manual audit covers it.

## Consequences

- A report pull request can contain only hygiene findings after a quiet month.
- The fresh checkout of the report workflow keeps `fetch-depth: 0`, since `git blame` needs the history.

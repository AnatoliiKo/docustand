# Job baseline-burndown

## Goal

Remove entries of the baseline files by fixing their cause.

## Steps

1. List the entries of every baseline file, oldest `until` first.
2. For an entry, fix the code, document or ADR that causes it, then remove the entry.
3. Run `mise run check` and `mise run check-baseline`.

## Do not

- Add an entry, raise a number, move an `until` date later or replace an entry with another.
- Remove an intentional entry of `betterleaks.ignore`; fix the finding it fingerprints, or leave the entry.
- Move lines in a file that has an entry in `betterleaks.ignore`, rename a file that has a baseline entry, or add a suppression to code.
- Change configuration, workflows, `.claude/`, `AGENTS.md`, `CLAUDE.md` or package lock files.
- Rewrite an ADR that has an entry in `adr.json` when the edit to the baseline file is declined. List the remaining entries in the final message for the owner.
- Commit, push or open a pull request: `mise run maintain` does it.

## No changes

When no entry can be fixed without breaking a rule above, change nothing. The job then ends without a pull request.

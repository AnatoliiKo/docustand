# Job dead-code

## Goal

Remove code that nothing references: unused functions, files, exports and parameters.

## Steps

1. Find candidates with the project tools, such as `knip` or the linter, and confirm each with a search for references, including dynamic ones.
2. Remove the code together with its tests and its documentation lines.
3. Run `mise run check`.

## Do not

- Remove code that holds the last import of a dependency: `package.json` is protected and `knip` fails on the dependency.
- Remove a doubtful candidate: leave it.
- Add a baseline entry, a suppression or an exception.
- Move lines in a file that has an entry in `betterleaks.ignore`, rename a file that has a baseline entry, or add a suppression to code.
- Create a new file in the repository root.
- Commit, push or open a pull request: `mise run maintain` does it.

## No changes

When no candidate is safe to remove, change nothing. The job then ends without a pull request.

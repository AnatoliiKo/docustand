# 0031. Template mise file is valid TOML

Date: 2026-11-16
Status: accepted

## Context

- Renovate updates the tool pins of the template through its mise manager on `template/.mise/conf.d/standard.toml.jinja`.
- The file held `{% if %}` blocks for the stack profiles, so it was not valid TOML.
- The mise manager skips a file that fails to parse and logs only at debug level: no tool of the template got an update pull request.
- Renovate drops a file whose path contains an `ignorePaths` entry; `.mise/conf.d/standard.toml` also hid the template source.
- Renovate PR #14 bumped hk in `hk.pkl.jinja` alone, and `test_hk_package_matches_hk_tool` failed.

## Decision

- Copier renders with the Jinja line statement prefix `#%`; a `#%` line is a Jinja statement and a TOML comment.
- `standard.toml.jinja` uses `#%` line statements and `{% %}` only inside string values, so its source parses as TOML.
- The Renovate config of docustand groups the mise and the custom regex managers into one `mise tools` pull request after the non-major rule, so hk moves in both files at once.
- `ignorePaths` names `**/.mise/conf.d/standard.toml`, a glob that matches the rendered file and is no substring of the template source.
- Renovate keeps `python` of the template below 3.14, the version the check scripts are tested on.
- A test parses the source of `standard.toml.jinja` as TOML.

## Rejected

- A custom regex manager per tool: it repeats the tool-to-datasource map that the mise manager already has.
- Separate files per stack profile in `.mise/conf.d/`: the hooks still differ per stack, and every reference to `standard.toml` changes in docs, checks and the detach steps.
- Manual tool updates: the pins drift, as the missing updates of 2026-11 show.

## Consequences

- Jinja line statements remove the whitespace that follows them; a `#%` block is placed before a non-blank line.
- In a project with a stack profile the rendered `standard.toml` lists `pipx:check-jsonschema` after the profile tools; the content is the same.
- A line that starts with `#%` in any template file is a Jinja statement.

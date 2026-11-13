# Allowed licenses of dependencies

<!-- doc-paths: another repository -->

A new dependency needs a license from this table; another license needs the owner's approval and an ADR.

| License | Allowed for |
|---|---|
| MIT | all dependencies |
| ISC | all dependencies |
| Apache-2.0 | all dependencies |
| LGPL-3.0-only | devDependencies only ([ADR 0015](../../../docs/decisions/0015-typescript-profile-dependencies.md)) |

- A devDependency stays out of the build output: a bundler takes only imported modules, and a production install skips devDependencies.
- The table lists the licenses of the dependencies approved so far.

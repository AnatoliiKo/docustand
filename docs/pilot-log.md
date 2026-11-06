# Pilot log

Results of the standard on pilot projects. One row per observation.

| Date | Check | Caught | False positive | Maintenance time |
|---|---|---|---|---|
| 2026-11-06 | Pilot scope | `infrastructure` holds Python code: 45 `.py` files with pytest tests of the Lambda functions; the criterion of the first repository with code is not checked for Python by this pilot | — | — |
| 2026-11-06 | `check-gitignore-block` | Missed: a `.claude/` rule before the standard block disabled its negations, and the check passed; behaviour check with `git check-ignore` added | — | — |

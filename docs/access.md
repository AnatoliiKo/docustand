# Access

Accesses the project depends on. Secrets are never stored here.
Expiry is a date in `YYYY-MM-DD` format or `never`.

| Access | Owner | Where secrets live | Expires |
|---|---|---|---|
| Code hosting: public repository `AnatoliiKo/docustand` | Owner | No secrets | never |
| Renovate GitHub App on the repositories that use the standard | Owner | GitHub App settings | never |
| Report GitHub App: Contents RW, Pull requests RW, Administration read | Owner | Repository secrets `REPORT_APP_ID` and `REPORT_APP_PRIVATE_KEY` in each repository | never |

## Owner steps

- Install the Renovate GitHub App on every repository that uses the standard.
- Create the report GitHub App with the permissions above; `repo-init` stores its ID and private key as the repository secrets above.

# Access

Accesses the project depends on. Secrets are never stored here.
Expiry is a date in `YYYY-MM-DD` format or `never`.

| Access | Owner | Where secrets live | Expires |
|---|---|---|---|
| Code hosting: public repository `AnatoliiKo/docustand` | Owner | No secrets | never |
| Renovate GitHub App on the repositories that use the standard | Owner | GitHub App settings | never |
| Report GitHub App `anatoliiko-repo-report` of `AnatoliiKo`, installed on that account only: Contents RW, Pull requests RW, Administration read, Checks read, Commit statuses read, Dependabot alerts read | Owner | Private key in the owner's keychain; repository secrets `REPORT_APP_CLIENT_ID` and `REPORT_APP_PRIVATE_KEY` in each repository | never |
| Fine-grained token of `AnatoliiKo` for self-hosted runners (ADR 0036): Administration read and write on `cinema-ops`, `stockpit`, `manifold`, `kids-wallet` and `my-visits-dashboard` only, name `vm-docker-ci-runners` | Owner | `/opt/stacks/sys-ci-runners/.env` on the VM `docker`, readable by its owner only | 2027-11-27 |

## Owner steps

- Install the Renovate GitHub App on every repository that uses the standard.
- Create the report GitHub App with the permissions above; `repo-init` stores its Client ID or App ID from the app page and its private key as the repository secrets above.
- Create the runner token above with the expiry date of the table and put it into `/opt/stacks/sys-ci-runners/.env` on the VM `docker`.
- Delete the downloaded `.pem` file after the private key is in the keychain and in the secrets.
- Without these secrets the scheduled report collects the findings into the job summary and fails with `report app is not configured, see docs/access.md`.

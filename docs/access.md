# Access

Accesses the project depends on. Secrets are never stored here.
Expiry is a date in `YYYY-MM-DD` format or `never`.

| Access | Owner | Where secrets live | Expires |
|---|---|---|---|
| Code hosting (GitHub repository) | | | never |
| CI token | | | YYYY-MM-DD |
| Scheduled Claude task for reports | | | never |
| Renovate GitHub App on the repositories that use the standard | Owner | GitHub App settings | never |
| Report GitHub App: Contents RW, Pull requests RW, Administration read | Owner | Repository secrets `REPORT_APP_ID` and `REPORT_APP_PRIVATE_KEY` in each repository | never |

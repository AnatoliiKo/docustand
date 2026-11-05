# Terraform profile

Read by the `repo-init` skill when `terraform` is in the `stack` answer.

## Detection

- Signal: any `*.tf` file outside a `.terraform/` directory.
- Run `.mise/tasks/detect-stack [PATH]` (works before the template is installed, also outside git); the
  `terraform` entry of `evidence` lists up to 10 matching paths.

## Tools

`terraform` and `tflint` in `.mise/conf.d/standard.toml` (pinned versions; added with the Task 7 fragments).
`.tflint.hcl` enables the bundled `terraform` ruleset with the `recommended` preset and
`terraform_unused_declarations`. It uses no plugins, so tflint needs no network.

## Commands

| Stage      | Command                                                                                       |
|------------|-----------------------------------------------------------------------------------------------|
| pre-commit | `terraform fmt -check {{files}}` (staged `*.tf` and `*.tfvars` files)                          |
| pre-push   | `tflint --recursive`                                                                           |
| pre-push   | for each root module: `terraform init -backend=false -input=false`, then `terraform validate` |

A root module is a directory with `*.tf` files that is not under `.terraform/` and is not used only as a
child module (not referenced by a `source = "./..."` of another module).

## Running without secrets

`init -backend=false` skips the remote backend, so no state, cloud credentials or tokens are needed.
`validate` checks syntax and internal consistency only. Do not run `plan` or `apply` in hooks or CI:
they need credentials and read live infrastructure.

## Notes

- `init` downloads providers and modules from public registries; the hooks therefore need network on the
  first run (providers are cached afterwards).
- `.terraform/` and `*.tfstate*` stay in `.gitignore`; `.terraform.lock.hcl` is committed.
- `terraform fmt -check` fails on unformatted files; fix with `terraform fmt`.

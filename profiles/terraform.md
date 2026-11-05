# Terraform profile

Read by the `repo-init` skill when `terraform` is in the `stack` answer.

## Detection

- Signal: any `*.tf` file outside a `.terraform/` directory.
- Run `.mise/tasks/detect-stack [PATH]` (works before the template is installed, also outside git); the
  `terraform` entry of `evidence` lists up to 10 matching paths.

## Tools

`terraform` and `tflint` in `.mise/conf.d/standard.toml` (pinned versions).
`.tflint.hcl` enables the bundled `terraform` ruleset with the `recommended` preset and
`terraform_unused_declarations`. It uses no plugins, so tflint needs no network.

## Commands

| Stage      | Command                                                                                       |
|------------|-----------------------------------------------------------------------------------------------|
| pre-commit | `terraform fmt -check {{files}}` (staged `*.tf` and `*.tfvars` files)                          |
| pre-push   | `tflint --recursive --config="$PWD/.tflint.hcl"` (one config for every module)               |
| pre-push   | `.mise/tasks/tf-validate`: in each root module `terraform validate`; on failure `terraform init -backend=false -input=false` and `validate` again |

A root module is a directory with `*.tf` files that is not under `.terraform/` and is not referenced as a
local child module (`source = "./..."` or `source = "../..."`) by another module. `tf-validate` checks every
root module on each run: a change in a child module can break any root module that uses it.
The hk steps are `terraform-fmt`, `tflint` and `tf-validate`; `mise run check` runs all of them.

## Running without secrets

`init -backend=false` skips the remote backend, so no state, cloud credentials or tokens are needed.
`validate` checks syntax and internal consistency only. Do not run `plan` or `apply` in hooks or CI:
they need credentials and read live infrastructure.

## Notes

- `init` downloads providers and modules from public registries; the hooks therefore need network on the
  first run (providers are cached afterwards).
- `.terraform/` and `*.tfstate*` stay in `.gitignore`; `.terraform.lock.hcl` is committed.
- `terraform fmt -check` fails on unformatted files; fix with `terraform fmt`.

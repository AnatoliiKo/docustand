# Owner environment

Facts about the owner's machines that change how gates run.
They come from `~/.claude/CLAUDE.md`; if that file disagrees with this one, the global file wins.

## Toolchain

- mise is required. Check with `command -v mise`. If it is missing, stop and show the install command (`brew install mise`); installing it is the owner's decision.
- Every other tool, Copier and hk included, comes from `.mise/conf.d/standard.toml` through `mise install`.
- `mise install` runs `hk install --mise` as a postinstall hook, so it needs a git repository: `git init` comes first.

## Docker

- Docker runs only on the VM `docker` (context `docker-vm`), never in Docker Desktop. Check with `docker context show`.
- Address the VM as `docker` in configs, never by IP or a full VPN name.
- Bind mounts of Mac folders do not work there. A gate that needs the sources inside a container runs from a native binary through mise, or in CI.
- Container ports are `docker:<port>`, not `localhost:<port>`.
- The VM is shared with production services: no long heavy scans; clean up images and stopped containers.
- Hooks never load the VM: tests that need Docker run in CI only.

## Git and GitHub

- No `Co-Authored-By: Claude`, no «Generated with Claude Code», no session links in commits, PRs, issues or releases; commitlint rejects them.
- Commit or push only when the owner asks. Branch first when on the default branch.

## iOS projects

The Simulator is shared between sessions. Builds and unit tests that need no booted device run without it; UI checks follow the Simulator rules in `~/.claude/CLAUDE.md`.

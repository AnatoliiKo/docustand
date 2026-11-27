# 0036. Self-hosted CI runners

Date: 2026-11-27
Status: accepted

## Context

GitHub-hosted runners of private repositories cost $0.006 per Linux minute. On 2026-11-27 the $12 of included compute of the account was used (`stockpit` $5.16, `cinema-ops` $4.83, `manifold` $1.96), and CI of private repositories stopped.

The VM `docker` has 8 vCPU and 16 GB of memory. From 2026-11-24 to 2026-11-27 its CPU peak was 11 %, and at least 13.5 GB of memory stayed available. Its host, server 1-3, has 32 threads and 64 GB of memory and also runs DCP encoding, ticket sales and the Kinoplan VM.

Public repositories use GitHub-hosted Linux runners at no cost. A self-hosted runner of a public repository runs code of any outside pull request.

## Decision

- Linux jobs of private repositories run on self-hosted runners in containers on the VM `docker`. Public repositories, including `docustand`, stay on GitHub-hosted runners.
- The image is `myoung34/github-runner`. A container registers itself through a token, takes one job, re-registers after the job and runs one job at a time.
- Each repository gets its own runner container, so jobs of different repositories share no files. Runners of the account are registered per repository: a personal account has no shared runners.
- All runner containers run in one systemd slice with a total limit of 6 vCPU and 10 GB of memory, and a CPU weight below the other containers of the VM. Each container has its own limit of 4 vCPU, 6 GB of memory and 4096 processes.
- Runner containers use a separate Docker network without access to the Docker socket, the LAN, NetBird or Tailscale: only the internet.
- The template answer `ci_runner` sets `runs-on` of the template workflows; the default stays `ubuntu-latest`.
- Windows jobs and jobs that build Docker images stay on GitHub-hosted runners. macOS checks follow [ADR 0037](0037-macos-checks-in-pre-push.md).

## Rejected

- `actions-runner-controller`: needs a Kubernetes cluster on the VM.
- GARM: has no Docker provider and needs Incus or LXD on the VM.
- The official `actions/runner` image with an own registration script: a script that the chosen image already provides.
- A free GitHub organization with one shared runner: moving the repositories changes their addresses and the connected services; it stays an option when the number of private repositories grows.
- A larger VM: the VM uses at most 11 % of its CPU, and a change of server 1-3 needs the owner.

## Consequences

- A new private repository needs one more runner service and access of the token to the repository.
- Jobs of one repository wait in a queue while its runner is busy.
- Downloads of CI jobs use the internet channel of the cinema.
- The token expires; `docs/access.md` lists its date.
- `myoung34/github-runner` is maintained mainly by one person; the official runner inside it follows each release within one day.

# AGENTS.md — Hypercube

Guidance for AI coding agents working in `~/hypercube`.

## What this project is

Hypercube is a small, secure, reproducible host for AI agents on Oracle Cloud
Infrastructure (Arm A1, Always Free tier), with an AgentMail email identity and
headless quality gates. Everything is deterministic code in git.

## Working rules

- Read this file first; it is binding.
- Use the `explore` subagent for reconnaissance against new code or docs.
- Keep a `SetTodoList` and keep exactly one task `in_progress` while work is
  underway.
- Use `AskUserQuestion` instead of guessing on anything that affects scope,
  cost, security, or external credentials.
- Default to read-only / dry-run. Cloud-mutating actions require an explicit
  `APPLY` from the human in this session. This includes:
  - `terraform apply` or `terraform destroy`
  - the capacity runner hitting real OCI
  - any `oci ... create|delete|terminate|update` command
- Always-Free guard is the default:
  - OCPU ≤ 2, memory ≤ 12 GB, boot volume ≥ 47 GB and ≤ 50 GB.
  - Paid shapes are only allowed if `allow_paid=true` is set by the human.
- Unverified versions, CLI flags, or API fields go to `docs/UNVERIFIED.md`,
  never into code as facts.
- Pin dependency versions; prefer releases at least 14 days old.
- One logical change per commit, using conventional commit messages.
- Tests ship with code; every gate must be green before claiming done.
- If a gate fails twice with the same root cause, stop, summarize, and ask.
- Never ask the human to paste secrets in chat. Request credentials via
  `AskUserQuestion` and tell them where to put the value (e.g. `.env`, `~/.oci`).

## Human-only steps

- OCI tenancy + home region, compartment OCID, API key + fingerprint in
  `~/.oci` (mode 600), admin SSH public key.
- AgentMail API key (`AGENTMAIL_API_KEY` in `.env`, gitignored) and desired
  inbox username.
- GitHub repo/remote and OCI budget alert email.
- Explicit `APPLY` approval for every cloud mutation.

## Non-goals

No Kubernetes, no multi-cloud, no custom domains/DNS unless explicitly asked,
no paid resources by default, no BaseRock automation, no GUI work, no
refactoring of unrelated files.

## Toolchain notes

- Control node is Arch-based (CachyOS/Omarchy): use `pacman`/`paru`/`uv` here.
- Target VM is Ubuntu 24.04 aarch64.
- Kimi Code CLI flags differ between old (`kimi-cli`) and new (`Kimi Code`)
  releases; check `kimi --help` before scripting any flag.

<!-- coding-agents-repair:begin -->
## Shared coding-agent workflow

These instructions apply to Codex, Claude Code, Kimi Code, Crush, and Amp.
- Inspect the repository's README, manifests, local instructions, and tests before editing.
- Prefer small, scoped edits; preserve user changes and keep diffs reviewable.
- Never commit secrets, credentials, `.env` files, or generated build artifacts.
- Do not delete files, force-push, deploy, or change access controls without approval.
- Follow the repository's existing build, lint, and test conventions. Run focused checks first.
- Report exact checks performed, results, and any verification gaps.
- Do not invent package commands or pretend a test was run.
<!-- coding-agents-repair:end -->

<!-- repo-evidence-harness:begin -->
## Verified repository orientation

> Auto-collected from repository-local filenames, manifests and README. Review these facts before treating them as project policy.

- **README**: `README.md`; introductory text: A small, secure, reproducible host for AI agents on Oracle Cloud Infrastructure (Arm A1, Always Free tier), with an AgentMail email identity
- **Root manifests**: `pyproject.toml`.
- **Existing directories**: `src/`, `tests/`, `docs/`, `.github/workflows/`.

### Commands supported by repository evidence

Check prerequisites and command behavior before execution:

- `uv run pytest` — pyproject.toml / tests directory; verify dependencies before running.

### Source-of-truth rule

Read the referenced manifests, CI workflows and README before changing architecture or running commands. Do not treat detected paths as proof of behavior.
<!-- repo-evidence-harness:end -->

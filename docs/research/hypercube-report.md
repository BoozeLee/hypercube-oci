Hypercube → Kimi Code CLI: audit, prompt science, and master plan prompt

Prepared 2026-10-11. Drop AGENTS.md (separate file) in the repo root, run /plan on in Kimi, then paste the block in Part E.

Part A — Audit of the research report

The report's architecture (OCI Arm + AgentMail + automated QA, agent-driven) is sound. Several facts are stale or wrong, and a lot is missing. Fix these before building.

#    Report claim / gap    Status    Fix in the plan
1    Always Free A1 = 4 OCPU / 24 GB    Stale. Oracle's docs now list 1,500 OCPU-h + 9,000 GB-h/month = 2 OCPU / 12 GB for Always Free tenancies. Free-only instances above that get shut down until resized; PAYG treatment is contested (Oracle docs say "all tenancies", support reportedly told PAYG users otherwise).    Default to 2 OCPU / 12 GB. Terraform variable validation blocks anything larger unless allow_paid=true. Budget alert mandatory.
2    "PAYG gets priority, fewer capacity errors"    Plausible (paid accounts reportedly use different capacity criteria and can open support tickets) but unverified for 2026. Capacity is never guaranteed.    Treat capacity as best-effort; build a fallback (see #4).
3    Idle instances are safe    Missing risk. Oracle can reclaim Always Free instances idle at p95 CPU < 20% over 7 days (secondary sources also cite network/memory thresholds for A1).    Run the real agent workload plus a lightweight health/job loop; add an alert on utilization; document reclaim recovery.
4    "Infinite retry loop"    Right idea, naive execution. Missing: error classification (500 "Out of host capacity" ≠ 429 ≠ 400 LimitExceeded quota ≠ auth), jitter, max runtime, per-AD rotation, and a fallback.    Deterministic runner (Part D). Fallback: smaller shape, other AD, 2× 1 OCPU, or paid E-series Flex for dev.
5    launch_instance with shape + AD only    Incomplete. Needs compartment, VCN, subnet, internet gateway, route table, security list/NSG, aarch64 image OCID, SSH public key, cloud-init.    Terraform owns all of it.
6    Generate infra scripts live with Gemini --yolo    Non-reproducible and risky.    Commit deterministic Terraform/Python; agent edits and verifies, never improvises. Human gates on every cloud mutation.
7    Webhook at http://<IP>:8000/webhook    Insecure. No TLS, no signature check, open port.    AgentMail delivers via Svix: verify svix-id/-timestamp/-signature on the raw body. Better: use WebSockets (outbound only, no public URL). Webhooks+WebSockets are on the AgentMail Free tier as of 2026-09-04 (3 inboxes, 3,000 emails/mo, 100/day, vendor blog).
8    event_types limited to message.received    Stale. Changelog shows more events (e.g. domain.verified), domains, pods, drafts, allow/block lists.    Pin SDK version; read the OpenAPI spec (docs.agentmail.to/openapi.json).
9    "BaseRock-ready scaffold" automates QA    Overstated. BaseRock is an IDE-first commercial plugin (freemium); no documented headless CLI.    Headless gate = pytest + coverage + hypothesis + mutmut + schemathesis. BaseRock stays an optional manual IDE step.
10    Ubuntu control node + apt    Your control node is Arch-based (CachyOS/Omarchy).    pacman/paru/uv on control node; Ubuntu 24.04 aarch64 only on the VM.
11    Gemini 2.5 Pro / Gemini CLI as orchestrator    Replaced by Kimi Code CLI (K2.7-Code).    See Part B for flag drift.
12    Missing entirely    Host firewall (Oracle Ubuntu images ship restrictive iptables, so security list and host rules must agree), SSH hardening, TLS, secrets management, state/backups, observability, cost guard, teardown, CI, SBOM/vuln scan, home-region constraint (Always Free resources live in the home region chosen at signup), runbook, rollback.    Phases 1–8 below.
13    "One hour"    Not guaranteeable: capacity is external.    Define done as "everything ready except the instance; instance created when capacity appears", with the runner as a background job.
14    Sources: Reddit/Medium, no versions    Weak provenance.    Pin versions; UNVERIFIED ledger.
Part B — What makes a prompt ultra-effective in Kimi Code

Provenance note: I found no official Moonshot "prompt engineering guide" for Kimi Code CLI. Items marked (S) come from docs/model pages I read. Items marked (I) are my synthesis of agentic-coding practice, so test them.

Persistent rules live in AGENTS.md, task in the prompt. (S) Kimi merges AGENTS.md from repo root to the working directory (incl. .kimi/AGENTS.md); /init generates one. Keep the prompt about this job.
Use Plan Mode for broad/risky work. (S) /plan on, Shift-Tab, or kimi --plan: Kimi inspects, proposes, you approve, then it edits. The Hypercube build is exactly that.
Delegate recon to subagents. (S) Built-ins: explore (read-only), plan (no shell/write), coder. Each has an isolated context, so say "use explore for repo/doc reconnaissance" to save main-context tokens.
Name the tools it should use. (S) Default agent has SetTodoList, AskUserQuestion, EnterPlanMode/ExitPlanMode, SearchWeb, FetchURL, Shell, etc. Tell it to keep a todo list and to ask via AskUserQuestion instead of guessing.
Machine-checkable stop condition. (S) Ralph loop (--max-ralph-iterations N) runs until the agent outputs <choice>STOP</choice> or the cap. Define STOP as "just verify green + checklist complete".
Thinking is always on in K2.7-Code. (S) Reported as non-disableable; Moonshot recommends preserving reasoning across turns. So don't pad with "think step by step"; spend words on constraints and acceptance tests. ~30% fewer thinking tokens than K2.6 (vendor-reported).
256K context, so don't paste docs. (S) Put the research report in docs/research/ and tell Kimi to read it. Use /compact when long.
Raw-API guidance (not the TUI). (S) Together's Kimi quickstarts: keep the system prompt minimal; temperature ≈0.6 (K2 instruct) / 1.0 (thinking variants).
Verified-facts block up front. (I) Models fill gaps from stale memory; your report is a live example (4/24 vs 2/12). State corrected facts explicitly and forbid "correcting" them.
Phase gates with runnable acceptance commands. (I) Every phase ends with commands whose exit codes decide pass/fail.
Explicit non-goals and ask-first list. (I) Prevents scope creep and silent cloud spend.
Evidence contract. (I) "Done" requires pasted command output, an UNVERIFIED ledger, and a risk list.
Separate human-only steps. (I) Account creation, API keys, budgets: Kimi must request them, never fabricate or ask for secrets in chat.
Headless later. (S) kimi --print -p "..." for CI; rejected in combination with --yolo/--auto/--plan in the newer Kimi Code docs.

Version drift warning (S): two doc sets exist. The older Python kimi-cli (uv tool install kimi-cli; --print implies --yolo/--afk) and the newer Kimi Code (npm i -g @moonshot-ai/kimi-code, curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash, brew install kimi-code; -m kimi-code/kimi-for-coding). Run kimi --version and kimi --help and trust them over this document. kimi migrate moves data from the old install. /import-from-cc-codex imports Claude Code/Codex instructions, skills and MCP settings.

Part C — Foundations, tools, repos, configs

Foundations checklist (project building): requirements → threat model → repo skeleton → reproducible toolchain → IaC → host bootstrap → app → tests/quality gates → CI → observability → backup → cost guard → docs/runbook → teardown. Each has a phase below.

Repos and tools (✔ = checked this session; ○ = standard tool, pin the version yourself before use)

Purpose    Tool / repo    Note
Agent TUI    ✔ MoonshotAI/kimi-cli (→ Kimi Code), MoonshotAI/zsh-kimi-cli    ACP via kimi acp (Zed/JetBrains), MCP via kimi mcp, Web UI, hooks (beta), plugins (beta)
Agent loop runner    ✔ ralph-tui Kimi plugin    Wraps kimi --print; optional
OCI capacity    ✔ hitrov/oci-arm-host-capacity (PHP, ~1.2k★, last push Aug 2024, many open issues)    Reference only; write your own typed runner
OCI capacity    ✔ mowirth/oci-instance-creator (Docker)    Alternative reference
OCI IaC    ○ oracle/terraform-provider-oci; ✔ oracle-terraform-modules/terraform-oci-landing-zones    Landing zone is overkill for one VM; borrow patterns
OCI skills for agents    ✔ acedergren/oci-agent-skills    Optional; review before installing
Email identity    ✔ agentmail (PyPI) + svix    Official Python/TS SDKs
Python toolchain    ○ uv, ruff, pyright, pytest, pytest-cov, hypothesis, mutmut, schemathesis    
Test generation    ○ Keploy (OSS traffic→tests), Pynguin (executes your code; check Python-version support)    BaseRock = optional IDE plugin
Security    ○ gitleaks, semgrep, trivy, pip-audit, sops+age    
Ops    ○ Caddy (TLS), Tailscale (SSH), fail2ban, unattended-upgrades, restic, node_exporter or Uptime Kuma    
Task/CI    ○ just, pre-commit, GitHub Actions (pin actions by SHA)    

Kimi configuration to set up (verify exact keys in kimi --help and docs):

/login (Kimi Code OAuth or Moonshot API key); default model kimi-code/kimi-for-coding or kimi-k2.7-code (-highspeed variant exists at ~2× price, ~6× throughput, vendor-reported). Rough pricing ≈ $0.95/M input, $4/M output, ~$0.19/M cache-read.
/init once, then replace with the supplied AGENTS.md.
.kimi/ project dir: custom skills (--skills-dir), optional custom agent via --agent-file (YAML with system_prompt_path, subagents).
Hooks (beta): add a pre-tool hook that blocks terraform apply|destroy, oci ... delete|terminate, rm -rf outside the repo. Syntax: UNVERIFIED, read customization/hooks first.
Sandbox: run Kimi in a throwaway devcontainer/VM or bubblewrap with only the repo mounted; OCI credentials scoped by IAM policy to one compartment (manage instance-family, virtual-network-family, volume-family in compartment hypercube; no tenancy-wide admin).
Part D — Reference designs (keep in repo as skeletons; Kimi implements fully)

Capacity runner (Python, oci SDK) — error policy

ServiceError.status == 500 and "Out of host capacity" → sleep 60–120 s + jitter, rotate AD, continue.
429 → exponential backoff, cap 15 min.
400/LimitExceeded (service limits, e.g. standard-a1 core/memory count) → stop, print quota, tell human.
401/403/404 → stop (auth/IAM/OCID wrong).
Max runtime flag, structured JSON logs, idempotency (look for an existing instance by display-name tag before launching), stop on success, notify via AgentMail to the human mailbox.
Prefer driving Terraform (apply in a retry wrapper) so state stays authoritative.

Terraform guard

variable "ocpus" { default = 2, validation { condition = var.allow_paid || var.ocpus <= 2 } }, same for memory ≤ 12; boot_volume_size_in_gbs = 50 (min 47).
Resources: compartment, VCN, public subnet, IGW, route table, security list (ingress: 443 optional, SSH only from admin CIDR or none if Tailscale), instance, cloud-init user_data, budget + alert rule.

Webhook handler skeleton (FastAPI)

Read raw body bytes → Webhook(secret).verify(raw, headers) → on failure 400 → dedupe on svix-id → enqueue → return 200/204 immediately → process async. Never call a model before verification. Allow-list sender domains.
WebSocket mode: outbound client.websockets.subscribe(...) (async), auto-reconnect with backoff; no inbound port.

Quality gates

Coverage ≥ 85% on src/ (branch), mutation score reported (target ≥ 60% on core modules), Schemathesis against the OpenAPI schema, hypothesis tests for parsers, gitleaks clean, pip-audit clean, terraform validate, terraform fmt -check.
Part E — MASTER PROMPT (paste into Kimi Code after /plan on)
text
ROLE
You are the lead engineer for "Hypercube": a small, secure, reproducible host for AI agents on Oracle Cloud (Arm), with an AgentMail email identity and headless quality gates. Work in ./hypercube (git repo). Read AGENTS.md first; it is binding. Use the explore subagent for reconnaissance, keep a SetTodoList, and use AskUserQuestion instead of guessing.

MISSION
Deliver a repo that, given credentials supplied by the human, can: (a) plan and provision ONE Arm VM on OCI inside Always Free limits, (b) bootstrap it hardened via cloud-init, (c) run an AgentMail agent service on it, (d) enforce automated quality gates locally and in CI, (e) be monitored, backed up, and torn down cleanly. Everything is deterministic code in git. You never improvise infrastructure at runtime.

INPUT DOCS
Read docs/research/hypercube-report.md (the original research report) and treat Part A of docs/AUDIT.md (corrections) as overriding it. Do not paste either back to me.

VERIFIED FACTS (as of 2026-10-11; do NOT "correct" these from memory — if you doubt one, verify via SearchWeb/FetchURL and log it)
1. OCI Always Free Ampere A1 = 1,500 OCPU-hours + 9,000 GB-hours/month ≈ 2 OCPU / 12 GB total. Old 4/24 is obsolete. Min boot volume 47 GB; total block storage ≤ 200 GB. Always Free resources live in the tenancy HOME region.
2. "Out of host capacity" is an HTTP 500 from launch; quota errors are LimitExceeded (400); 429 = rate limit. Capacity is best-effort.
3. Always Free instances can be reclaimed when idle (p95 CPU < 20% over 7 days per Oracle docs).
4. AgentMail webhooks are delivered via Svix (headers svix-id, svix-timestamp, svix-signature; verify on the raw body; reply 2xx fast). AgentMail also offers WebSockets (no public URL needed). Official SDKs: Python and TypeScript.
5. BaseRock is an IDE-first commercial plugin with no documented headless CLI. Do not depend on it. Headless QA = pytest, coverage, hypothesis, mutmut, schemathesis.
6. Control node is Arch-based (CachyOS/Omarchy): use pacman/paru/uv. Target VM is Ubuntu 24.04 aarch64.
7. Kimi Code CLI flags differ between old (kimi-cli) and new (Kimi Code) releases. Check `kimi --help` before using any flag in scripts.

HUMAN-ONLY STEPS (request via AskUserQuestion; never ask me to paste secrets in chat; never print secrets)
- OCI tenancy + home region, compartment OCID, API key + fingerprint (stored in ~/.oci, mode 600), admin SSH public key.
- AgentMail API key (AGENTMAIL_API_KEY in .env, gitignored) and desired inbox username.
- GitHub repo/remote, OCI budget alert email.
- Approval for every cloud-mutating action.

NON-GOALS
No Kubernetes, no multi-cloud, no custom domains/DNS unless I ask, no paid resources, no BaseRock automation, no GUI work, no refactoring unrelated files.

OPERATING RULES
- Default read-only/dry-run. `terraform apply|destroy`, capacity runner, `oci ... create|delete|terminate` need my explicit "APPLY" in this session. Show `terraform plan` output summary first.
- Free-tier guard: ocpus ≤ 2, memory ≤ 12, boot ≥ 47 GB unless allow_paid=true (which I must set myself).
- Unverified versions/flags/fields go to docs/UNVERIFIED.md, not into code as facts. Pin dependency versions; choose releases at least 14 days old.
- One logical change per commit (conventional commits). Tests ship with code.
- If a gate fails twice with the same cause, stop, summarize root cause, and ask.

PHASES (each ends with a GATE: commands must exit 0 and you paste the tail of their output)

Phase 0 — Recon (read-only; use explore): inventory repo, toolchain versions (`uv`, `terraform`, `just`, `oci`, `python`), confirm `kimi --version`. Output docs/AUDIT.md (Part A corrections) and docs/UNVERIFIED.md. GATE: files exist; no secrets present (`gitleaks detect`).

Phase 1 — Foundation: repo skeleton (src/, tests/, infra/terraform/, infra/cloud-init/, scripts/, docs/, .github/workflows/), pyproject with uv, ruff, pyright, pytest-cov, hypothesis, mutmut, schemathesis, svix, agentmail, oci, fastapi, uvicorn, pydantic-settings; justfile (setup, verify, plan, apply, capacity, destroy); pre-commit (ruff, gitleaks, terraform fmt/validate); .env.example; .gitignore (covers .env, *.pem, *.tfstate*, .oci). GATE: `just setup && just verify`.

Phase 2 — OCI infrastructure as code: Terraform for compartment reference, VCN, public subnet, IGW, route table, security list (SSH only from admin CIDR variable or none), aarch64 Ubuntu 24.04 image lookup, VM.Standard.A1.Flex instance (2 OCPU/12 GB default, validated), 50 GB boot volume, SSH key, cloud-init, budget+alert. Remote or encrypted local state with documented backup. GATE: `terraform fmt -check && terraform validate && terraform plan -input=false` (plan only; show me the summary and wait).

Phase 3 — Capacity runner: typed Python module with the error policy (500 retry+jitter+AD rotation, 429 backoff, 400 LimitExceeded stop, auth stop), max-runtime, idempotent (detect existing instance by tag), JSON logs, dry-run default, and a test suite using a fake OCI client (no network). Prefer wrapping terraform apply so state stays authoritative. GATE: unit tests + hypothesis tests for the classifier; coverage ≥ 90% on this module. Do NOT run against real OCI until I say APPLY.

Phase 4 — Host bootstrap (cloud-init + scripts): unattended-upgrades, ufw/iptables rules consistent with the security list, SSH hardening (keys only, no root), fail2ban, Tailscale (optional), Docker or systemd units for the agent service, Caddy only if I later provide a domain, node_exporter or Uptime Kuma, restic backup of app state to OCI Object Storage (Always Free) with a restore test script, a real scheduled workload so the VM is not idle. GATE: `shellcheck` + cloud-init schema validation (`cloud-init schema`) + a Docker/qemu-aarch64 dry run if available.

Phase 5 — AgentMail service: create-or-get inbox idempotently (client_id); WebSocket-first listener with reconnect; optional FastAPI webhook endpoint with Svix verification on raw body, dedupe by svix-id, async queue, sender allow-list, rate limits, structured logs, graceful shutdown; a pluggable handler interface (default: log + auto-reply stub; no model calls until I configure a provider). Contract tests with recorded fixtures; fuzz with schemathesis. GATE: `just verify`, coverage ≥ 85% (branch) on src/, mutmut report on core modules, schemathesis run green.

Phase 6 — CI: GitHub Actions (pinned by SHA): verify, terraform validate, gitleaks, pip-audit, trivy fs, SBOM artifact. No cloud credentials in CI. GATE: workflow YAML lints (actionlint) and `just verify` equals CI steps.

Phase 7 — Operations: runbook (provision, rotate keys, restore from backup, recover from idle reclaim, capacity fallback ladder, teardown), cost-guard doc, `just destroy` with confirmation, DECISIONS.md. GATE: docs complete; a "fresh clone" smoke test script passes (`just setup && just verify`).

Phase 8 — Final verification & handoff: run everything, produce the report below.

QUALITY BAR
Typed, small functions, no dead code, no TODOs left in main, errors never swallowed, logs never contain secrets, every external call has timeouts, every loop has a bound.

DONE CONTRACT (final message must contain)
1) Evidence table: phase → gate command → result (tail of output). 2) Files created/changed. 3) UNVERIFIED items and residual risks. 4) What still needs a human (APPLY, keys, budget). 5) Exact next commands. Only when all gates are green and the checklist in docs/COMPLETENESS.md is fully ticked, output <choice>STOP</choice>.
Part F — "Nothing missing" checklist (copy to docs/COMPLETENESS.md)
 Requirements & non-goals · [ ] Threat model (secrets, webhook spoofing, SSH exposure, prompt injection via inbound email)
 Toolchain reproducible (uv.lock, pinned Terraform/provider) · [ ] Pre-commit + secret scan
 IaC complete (network, instance, image, budget) · [ ] Free-tier guard · [ ] State storage + backup
 Capacity runner with error policy + fallback ladder · [ ] Idle-reclaim mitigation
 Host hardening (SSH, firewall parity with security list, updates, fail2ban)
 AgentMail: inbox idempotency, Svix verify or WebSocket, dedupe, allow-list, rate limit
 Inbound email treated as untrusted input (no tool execution from email content without policy)
 Quality gates: lint, types, tests, coverage, mutation, fuzz, supply-chain scan, SBOM
 CI without cloud creds · [ ] Observability + alerting · [ ] Backups + restore test
 Cost guard (budget alerts, allow_paid flag) · [ ] Teardown tested
 Runbook · [ ] DECISIONS.md · [ ] UNVERIFIED ledger empty or justified
 Kimi: AGENTS.md, hooks, sandbox, scoped IAM, human-approval gates

Assumptions I made (change if wrong): Python 3.13/uv, Terraform, Ubuntu 24.04 aarch64, WebSocket-first, no custom domain, 2 OCPU/12 GB, single VM.

Sources (read this session)

Kimi Code CLI docs and cheat sheet (kimi.com/code/docs, moonshotai.github.io/kimi-cli, kimi.ai/resources/kimi-code-cheat-sheet); Kimi K2.7 Code coverage (Vercel AI Gateway, eesel, SiliconFlow, OpenRouter listings; benchmarks are vendor-reported); Together AI Kimi quickstarts; InfoQ and Linuxiac on the Oracle A1 cut; AgentMail docs (webhook verification, changelog) and blog; BaseRock comparison pages; hitrov/oci-arm-host-capacity and related repos.

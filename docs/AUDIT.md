# Audit corrections — Hypercube research report

Date: 2026-10-11

These corrections override the original research report at
`docs/research/hypercube-report.md`.

| # | Report claim / gap | Status | Fix |
|---|--------------------|--------|-----|
| 1 | Always Free A1 = 4 OCPU / 24 GB | Stale. Current docs list 1,500 OCPU-h + 9,000 GB-h/month ≈ 2 OCPU / 12 GB total. | Default to 2 OCPU / 12 GB; Terraform validation blocks larger values unless `allow_paid=true`. |
| 2 | "PAYG gets priority, fewer capacity errors" | Unverified for 2026; capacity is never guaranteed. | Treat capacity as best-effort and build a fallback ladder. |
| 3 | Idle instances are safe | Missing risk. Oracle can reclaim Always Free instances with p95 CPU < 20% over 7 days. | Run real scheduled workload; alert on utilization; document reclaim recovery. |
| 4 | "Infinite retry loop" | Naive. Missing error classification, jitter, max runtime, AD rotation, fallback. | Deterministic runner: 500 capacity → retry+AD rotate; 429 → backoff; LimitExceeded/auth → stop. |
| 5 | `launch_instance` with shape + AD only | Incomplete. Needs VCN, subnet, IGW, security rules, image OCID, SSH key, cloud-init. | Terraform owns the full stack. |
| 6 | Generate infra scripts live with Gemini --yolo | Non-reproducible and risky. | Commit deterministic Terraform/Python; agent edits and verifies, never improvises. |
| 7 | Webhook at `http://<IP>:8000/webhook` | Insecure: no TLS, no signature, open port. | AgentMail uses Svix: verify `svix-id`, `svix-timestamp`, `svix-signature` on raw body. Prefer WebSockets (outbound only). |
| 8 | `event_types` limited to `message.received` | Stale. AgentMail has more events, domains, pods, drafts, allow/block lists. | Pin SDK version; read the OpenAPI spec. |
| 9 | "BaseRock-ready scaffold" automates QA | Overstated. BaseRock is IDE-first with no documented headless CLI. | Headless QA = pytest + coverage + hypothesis + mutmut + schemathesis. BaseRock optional manual IDE step. |
| 10 | Ubuntu control node + apt | Wrong. Control node is Arch-based (CachyOS/Omarchy). | Use `pacman`/`paru`/`uv` on control node; Ubuntu 24.04 aarch64 only on the VM. |
| 11 | Missing entirely | Host firewall parity, SSH hardening, TLS, secrets management, state/backups, observability, cost guard, teardown, CI, SBOM/vuln scan, home-region constraint, runbook, rollback. | Covered in the implementation phases. |
| 12 | "One hour" | Not guaranteeable because capacity is external. | Define done as "ready to create when capacity appears"; runner runs as background job. |
| 13 | Weak sources (Reddit/Medium) | No versions pinned. | Pin versions; keep `docs/UNVERIFIED.md` ledger. |

## Binding constraints

- OCI Always Free A1 = 2 OCPU / 12 GB max.
- Always Free resources live in the tenancy **home region**.
- Boot volume minimum 47 GB; total block storage ≤ 200 GB.
- Capacity is best-effort; `Out of host capacity` is HTTP 500, quota errors are
  `LimitExceeded` (400), rate limits are 429.

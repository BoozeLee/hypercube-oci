# UNVERIFIED ledger

Items that are not yet confirmed and must not be treated as facts in code.

| Item | Source / reason | Verification needed |
|------|-----------------|---------------------|
| Kimi Code hooks syntax | Plan marked UNVERIFIED; docs not checked. | Read `kimi --help` and customization/hooks docs before adding any hook. |
| Kimi K2.7-Code benchmark numbers | Vendor-reported only. | Treat as marketing until reproduced independently. |
| Oracle new Always Free limits for PAYG accounts | Docs say "all tenancies"; support reportedly told PAYG users otherwise. | Confirm with current OCI console + support if paid path is chosen. |
| PAYG priority / fewer capacity errors | Anecdotal reports only. | Do not rely on; build fallback ladder regardless. |
| Kimi CLI flag drift between old and new releases | Mentioned in docs but not exhaustively tested. | Check `kimi --version` and `kimi --help` on this machine before scripting. |

## Phase 0 toolchain inventory

| Tool | Version | Status |
|------|---------|--------|
| uv | 0.11.14 | OK |
| terraform | 1.15.9 | OK (1.16.5 available) |
| just | 1.58.0 | OK |
| python | 3.14.7 | OK |
| kimi | 2.1.1 | OK |
| oci-cli | not installed | Needed for manual OCI ops; capacity runner uses Python `oci` SDK instead. |

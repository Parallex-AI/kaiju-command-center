# Kaiju Command Center

AI agent lab for Kaiju Digital.

## Current milestone

**V5.22 — Controlled Real OAuth Ceremony Dry Run Execution** (branch: `v5.22-controlled-real-oauth-ceremony-dry-run` · base: `v5.21.0-beta`)

V5.22 executes a full dry-run rehearsal of the controlled Google Ads OAuth onboarding ceremony using V5.21 controls, validators, runbooks, and redacted placeholders only. Phase 1 is planning only. No real credentials. No OAuth execution. `GOOGLE_ADS_LIVE_ENABLED=false` throughout. No deploy. No GCP commands. No IAM/API/billing changes.

**Phase 1 — Branch setup and dry-run execution plan** (`docs/V5_22_IMPLEMENTATION_PLAN.md`): V5.22 implementation plan; 8-phase roadmap; dry-run execution scope; baseline controls from V5.21; non-authorization statement; stop conditions; deferred items; does not authorize OAuth, real credentials, Google Ads API, Secret Manager, GCP, deployment, or `GOOGLE_ADS_LIVE_ENABLED=true` activation.

**Phase 2 — Dry-run execution packet template** (`docs/GOOGLE_ADS_OAUTH_DRY_RUN_EXECUTION_PACKET.md`): documentation-only redacted packet template; 14 sections (A–N); 11-role participant placeholder table; 7 redacted target context fields; 12-field timed execution window with 8 window rules; 15 pre-flight gates; 24-step dry-run sequence checklist; 10-validator evidence field table; 16 no-execution confirmations (all pre-filled `NO`); allowed/forbidden evidence tables; 21 stop conditions; rollback and emergency revoke rehearsal fields; final dry-run decision block; documentation-only; no dry-run executed; no real credentials; no OAuth; no auth URL; no browser; no callback URL; no auth code; no token exchange; no Secret Manager; no Google Ads API; no GCP.

**Phase 3 — Dry-run execution validator** (`openclaw/oauth_dry_run_execution.py` · `openclaw/run_oauth_dry_run_execution_demo.py`): local-only dry-run execution packet validator; `OAuthDryRunExecutionInput` (45 boolean fields); 47 failure codes; validates packet completeness, gate PASS confirmation, no-execution confirmations, evidence package redaction, stop-condition and rollback rehearsal presence, final decision presence; enforces all 15 hard-stop fields are False; detects forbidden field names and value patterns; pure stdlib; no credentials; no OAuth; no auth URL; no browser; no callback URL; no auth code; no token exchange; no Secret Manager; no Google Ads API; no GCP; no deploy; `GOOGLE_ADS_LIVE_ENABLED` remains false; 55 demo scenarios, 112 assertions, all PASS; smoke suite updated to 35/35.

**Phase 4 — Local dry-run execution results** (`docs/V5_22_DRY_RUN_EXECUTION_RESULTS.md`): local-only dry-run execution result; PASS; 14 sections (A–N); 610 assertions from explicit-count demos; smoke suites 35/35 and 8/8 PASS; evidence redacted; no real OAuth; no credentials; no auth URL; no browser; no callback URL; no auth code; no token exchange; no Secret Manager; no Google Ads API; no GCP; no deploy; `GOOGLE_ADS_LIVE_ENABLED` remains false.

**Phase 5 — Stop-condition and rollback rehearsal results** (`docs/V5_22_STOP_AND_ROLLBACK_REHEARSAL_RESULTS.md`): documentation-only local rehearsal; result PASS; 10 sections (A–J); 26 stop conditions (H-01–H-26) walked through — all PASS, none triggered; 12-step stop procedure PASS; rollback rehearsal (16 fields R-01–R-16, all confirmed PASS/YES); emergency revoke rehearsal (10 checklist items, all PASS, no-real-state walkthrough); post-stop safety validation PASS; 15 no-real-state confirmations all NO; no real stop triggered; no real rollback/revoke; no real approval; no credentials; no OAuth; no auth URL; no browser; no callback URL; no auth code; no token exchange; no Secret Manager; no Google Ads API; no GCP; no deploy; `GOOGLE_ADS_LIVE_ENABLED` remains false.

**Phase 6 — Final dry-run review and gap analysis** (`docs/V5_22_FINAL_DRY_RUN_REVIEW.md`): documentation-only final review; final dry-run verdict PASS (dry-run only); 12 sections (A–L); phase-by-phase review of Phases 1–5 all PASS; 610 explicit assertions plus smoke suites 35/35 and 8/8 PASS; 16 gaps documented; 16 NOT APPROVED actions stated; real ceremony remains NOT APPROVED; no credentials; no OAuth; no auth URL; no browser; no callback URL; no auth code; no token exchange; no Secret Manager; no Google Ads API; no GCP; no deploy; `GOOGLE_ADS_LIVE_ENABLED` remains false.

*Latest shipped:* **v5.21.0-beta — Controlled Real Google Ads OAuth Onboarding Ceremony complete** — tag `v5.21.0-beta`. See [V5.21 Branch Closure](docs/V5_21_BRANCH_CLOSURE.md) and [v5.21.0-beta Release Notes](docs/RELEASE_NOTES_V5_21_0_BETA.md).

---

*Previous milestone:* **V5.21.0-beta — Controlled Real Google Ads OAuth Onboarding Ceremony complete** — tag `v5.21.0-beta`. See [V5.21 Branch Closure](docs/V5_21_BRANCH_CLOSURE.md) and [v5.21.0-beta Release Notes](docs/RELEASE_NOTES_V5_21_0_BETA.md).

## Architecture

```
Demo Client (HTTP POST)
    ↓
Router HTTP Server  (FastAPI · localhost:8000)
    ↓
Router Core         (route_request · validation · dispatch)
    ↓
Ads Agent           (n8n_client · request type routing)
    ↓
n8n Webhook         (flows.kaiju.digital · production)
    ↓
JSON Response
```

## Quick start

**1. Start the Router server**

```bash
cd ~/kaiju/agents/router
~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

**2. Run the Demo Client**

```bash
cd ~/kaiju/projects/demo-client
~/kaiju/.venv/bin/python3 client.py summary
~/kaiju/.venv/bin/python3 client.py cpa
~/kaiju/.venv/bin/python3 client.py conversions
~/kaiju/.venv/bin/python3 client.py raw
```

**3. Run the interactive chat client**

```bash
~/kaiju/.venv/bin/python3 chat_client.py
```

## Documentation

- [V0 Architecture](docs/V0_ARCHITECTURE.md)
- [V0 Runbook](docs/V0_RUNBOOK.md)
- [Roadmap](docs/ROADMAP.md)
- [V5.12 Release Notes](docs/V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [GCP Secret Manager Runbook](docs/GCP_SECRET_MANAGER_RUNBOOK.md)
- [V5.13 Branch Closure](docs/V5_13_BRANCH_CLOSURE.md)
- [v5.13.0-beta Release Notes](docs/RELEASE_NOTES_V5_13_0_BETA.md)
- [V5.13 Manual GCP Validation Plan](docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md)
- [V5.13 Live GCP Validation Results](docs/V5_13_LIVE_GCP_VALIDATION_RESULTS.md)
- [V5.14 Branch Closure](docs/V5_14_BRANCH_CLOSURE.md)
- [v5.14.0-beta Release Notes](docs/RELEASE_NOTES_V5_14_0_BETA.md)
- [V5.15 Branch Closure](docs/V5_15_BRANCH_CLOSURE.md)
- [v5.15.0-beta Release Notes](docs/RELEASE_NOTES_V5_15_0_BETA.md)
- [V5.16 Branch Closure](docs/V5_16_BRANCH_CLOSURE.md)
- [v5.16.0-beta Release Notes](docs/RELEASE_NOTES_V5_16_0_BETA.md)
- [V5.17 Branch Closure](docs/V5_17_BRANCH_CLOSURE.md)
- [v5.17.0-beta Release Notes](docs/RELEASE_NOTES_V5_17_0_BETA.md)
- [Credential Lifecycle Runbook](docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [V5.17 Rate Limiting Design](docs/V5_17_RATE_LIMITING_DESIGN.md)
- [V5.18 Live GCP Fake Validation Plan](docs/V5_18_LIVE_GCP_FAKE_VALIDATION_PLAN.md)
- [V5.18 Live GCP Fake Validation Results](docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md) (complete — Phases A–N PASS)
- [V5.18 Branch Closure](docs/V5_18_BRANCH_CLOSURE.md)
- [v5.18.0-beta Release Notes](docs/RELEASE_NOTES_V5_18_0_BETA.md)
- [V5.19 Implementation Plan](docs/V5_19_IMPLEMENTATION_PLAN.md)
- [V5.19 Branch Closure](docs/V5_19_BRANCH_CLOSURE.md)
- [v5.19.0-beta Release Notes](docs/RELEASE_NOTES_V5_19_0_BETA.md)
- [V5.20 Implementation Plan](docs/V5_20_IMPLEMENTATION_PLAN.md)
- [Google Ads Real Onboarding Checklist](docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md) — operator checklist only; does not authorize real onboarding
- [Google Ads First Live API Validation Plan](docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md) — design-only; does not authorize execution
- [V5.20 Final Readiness Review](docs/V5_20_FINAL_READINESS_REVIEW.md) — local readiness PASS; NOT approved for real execution
- [V5.20 Branch Closure](docs/V5_20_BRANCH_CLOSURE.md)
- [v5.20.0-beta Release Notes](docs/RELEASE_NOTES_V5_20_0_BETA.md)
- [V5.21 Implementation Plan](docs/V5_21_IMPLEMENTATION_PLAN.md) — planning only; does not authorize OAuth, real credentials, or Google Ads API
- [Google Ads OAuth Ceremony Checklist](docs/GOOGLE_ADS_OAUTH_CEREMONY_CHECKLIST.md) — documentation-only operator ceremony checklist; does not authorize OAuth or real onboarding
- [Google Ads Credential Handoff Protocol](docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md) — documentation-only secure handoff protocol; does not authorize real credential handoff or Secret Manager write
- [Google Ads OAuth Dry-Run Runbook](docs/GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md) — documentation-only operator rehearsal runbook; does not authorize OAuth, real credentials, or execution
- [V5.21 Final Readiness Review](docs/V5_21_FINAL_READINESS_REVIEW.md) — local OAuth ceremony readiness PASS; NOT approved for real OAuth/credentials/token exchange/API/GCP/Secret Manager/live flag
- [V5.21 Branch Closure](docs/V5_21_BRANCH_CLOSURE.md) — merged, tagged v5.21.0-beta, GitHub Release published 2026-08-22
- [v5.21.0-beta Release Notes](docs/RELEASE_NOTES_V5_21_0_BETA.md)
- [V5.22 Implementation Plan](docs/V5_22_IMPLEMENTATION_PLAN.md) — planning only; does not authorize OAuth, real credentials, Google Ads API, Secret Manager, GCP, deployment, or live flag activation
- [Google Ads OAuth Dry-Run Execution Packet](docs/GOOGLE_ADS_OAUTH_DRY_RUN_EXECUTION_PACKET.md) — documentation-only redacted packet template; does not authorize real OAuth execution, credentials, token exchange, GCP, or live flag activation
- [V5.22 Dry-Run Execution Validator](openclaw/oauth_dry_run_execution.py) — local-only; validates dry-run packet completeness and no-execution confirmations; pure stdlib; does not execute dry-run or authorize real OAuth
- [V5.22 Dry-Run Execution Results](docs/V5_22_DRY_RUN_EXECUTION_RESULTS.md) — local dry-run result PASS; redacted evidence only; does not authorize real OAuth execution, credentials, token exchange, GCP, or live flag activation
- [V5.22 Stop-Condition and Rollback Rehearsal Results](docs/V5_22_STOP_AND_ROLLBACK_REHEARSAL_RESULTS.md) — documentation-only rehearsal result PASS; 26 stop conditions walked through; rollback and emergency revoke rehearsed as no-real-state walkthrough; no real rollback/revoke, credentials, OAuth, token exchange, GCP, Secret Manager, Google Ads API, or live flag activation
- [V5.22 Final Dry-Run Review](docs/V5_22_FINAL_DRY_RUN_REVIEW.md) — final dry-run verdict PASS (dry-run only); 610 explicit assertions; 16 gaps documented; 16 NOT APPROVED actions; real ceremony NOT APPROVED; does not authorize real OAuth, credentials, token exchange, GCP, Secret Manager, Google Ads API, or live flag activation

## Admin credential configuration (V5.16+)

OpenClaw admin endpoints are scope-gated. Set the following env vars to control access. Use placeholders only — never commit real token values.

| Variable | Scope granted | Purpose |
|----------|--------------|---------|
| `OPENCLAW_ADMIN_KEYS` | `ADMIN` (all operations) | Comma-separated admin-scope tokens; required for WRITE, VALIDATE, ROTATE, DELETE |
| `OPENCLAW_READ_KEYS` | `READ` | Comma-separated read-only tokens |
| `OPENCLAW_API_KEYS` | `READ` (backward-compatible fallback) | Existing API key configurations continue to work as read-only |
| `OPENCLAW_ADMIN_DELETE_ENABLED` | — | Set to `true` to enable `DELETE /credentials/google-ads`; disabled by default |
| `OPENCLAW_AUDIT_RETAIN_DAYS` | — | Audit JSONL retention days for `prune_audit_files()`; default `90` |
| `OPENCLAW_TENANT_KEYS` | `` | Comma-separated `token:tenant_id` pairs; restricts listed tokens to their allowed tenants (V5.17+) |
| `OPENCLAW_ADMIN_RATE_LIMIT_RPM` | `0` | Max requests/min for STANDARD admin routes per token; `0` = disabled (V5.17+) |
| `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` | `0` | Max requests/min for SENSITIVE admin routes per token; `0` = disabled (V5.17+) |

Example (local dev only — use placeholder values):

```bash
export OPENCLAW_API_AUTH_ENABLED=true
export OPENCLAW_ADMIN_KEYS=<your-admin-token-here>
export OPENCLAW_READ_KEYS=<your-read-token-here>
```

A valid token with insufficient scope returns `403 scope_not_granted`. A missing or invalid token returns `401 unauthorized`.

## Roadmap summary

| Version | Focus | Status |
|---|---|---|
| V0 | Ads Agent · Router · n8n · Demo Client | **Complete** — `v0.0.1` |
| V1 | LangGraph · stateful analysis | **Complete** — `v1.4.1` |
| V2 | MemPalace · persistent client memory | **Beta complete** — `v2.0.0-beta` |
| V3 | OpenClaw · HTTP API · tenant context · audit log | **Alpha complete** — `v3.0.0-alpha` |
| V3.5 | Config · auth placeholder · CORS · Docker · GCP plan | **Beta complete** — `v3.5.0-beta` |
| V4 | Real integrations · Google Ads API · data source resolver | **Beta complete** — `v4.0.0-beta` |
| V4.5.1 | Live Google Ads read-only fetch · GAQL · credential safety gates | **Alpha** — `v4.5.1-alpha` |
| V5 | Tenant credentials · secure onboarding · secret store · OAuth | **Beta complete** — `v5.0.0-beta` |
| V5.12 | GCP Secret Manager backend · `GCPSecretManagerStore` · IAM · rotation | **Beta complete** — `v5.12.0-beta` |
| V5.13 | Live GCP validation · Phases A–F PASS · provider composition confirmed | **Beta complete** — `v5.13.0-beta` |
| V5.14 | Admin credential bundle GCP wiring · POST endpoint · TestClient smoke · live GCP validation | **Beta complete** — `v5.14.0-beta` |
| V5.15 | Credential lifecycle hardening · audit events · structural validation · revoke/delete endpoint | **Beta complete** — `v5.15.0-beta` |
| V5.16 | Admin RBAC · audit seq/digest · credential rotation endpoint | **Beta complete** — `v5.16.0-beta` |
| V5.17 | Production readiness · tenant isolation · rate limiting · audit locking · operator runbook | **Beta complete** — `v5.17.0-beta` |
| V5.18 | Live GCP fake-secret validation · write → validate → rotate → delete → audit | **Beta complete** — `v5.18.0-beta` |
| V5.19 | Real credential readiness gates · live-mode gate · approval workflow · preflight · guardrails · audit | **Beta complete** — `v5.19.0-beta` |
| V5.20 | Controlled real Google Ads onboarding readiness · ceremony · checklist · intake boundary · first-call plan · rollback drill · version lifecycle policy · final readiness review | **Beta complete** — `v5.20.0-beta` |
| V5.21 | Controlled real Google Ads OAuth onboarding ceremony · authorization URL design · callback boundary · credential handoff protocol · approval packet · dry-run runbook | **Beta complete** — `v5.21.0-beta` |
| V5.22 | Controlled real OAuth ceremony dry run execution · dry-run packet · execution validator · stop/rollback rehearsal · final dry-run review | **In progress** — `v5.22-controlled-real-oauth-ceremony-dry-run` |

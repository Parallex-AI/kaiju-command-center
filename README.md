# Kaiju Command Center

AI agent lab for Kaiju Digital.

## Current milestone

**V5.21 — Controlled Real Google Ads OAuth Onboarding Ceremony** (branch: `v5.21-controlled-real-google-ads-oauth-onboarding` · base: `v5.20.0-beta`)

V5.21 converts V5.20's readiness controls into an operator-safe OAuth ceremony design for a future real Google Ads onboarding event. Phase 1 is planning only. No real credentials. No OAuth execution. `GOOGLE_ADS_LIVE_ENABLED=false` throughout. No deploy. No GCP commands. No IAM/API/billing changes.

**Phase 1 — Planning and branch setup** (`docs/V5_21_IMPLEMENTATION_PLAN.md`): V5.21 implementation plan; 10-phase roadmap; ceremony control model; stop conditions; security model; non-authorization statement; does not authorize OAuth, real credentials, Google Ads API, Secret Manager, GCP, deployment, or `GOOGLE_ADS_LIVE_ENABLED=true` activation.

**Phase 2 — OAuth ceremony checklist** (`docs/GOOGLE_ADS_OAUTH_CEREMONY_CHECKLIST.md`): documentation-only operator ceremony checklist; 15-section structure covering participants/roles, preconditions, authorization URL review gate, scope confirmation gate, browser execution gate, callback/auth-code handling gate, token exchange boundary gate, credential storage gate, Google Ads API boundary gate, evidence package, stop conditions (25), rollback sequence (13 steps), sign-off block; does not generate OAuth URL, does not execute OAuth, does not use real credentials.

**Phase 3 — OAuth authorization URL design validator** (`openclaw/oauth_auth_url.py` · `openclaw/run_oauth_auth_url_demo.py`): pure stdlib local-only validator; `OAuthAuthUrlDesignInput` (26 fields); 26 failure codes; hard-stop detection for OAuth execution, real URL generation, browser interaction, and credential presence; redirect URI, scope, state, OAuth parameter, ceremony control, and forbidden-value checks; `validate_oauth_auth_url_design()`; 34 demo test scenarios (82 assertions, all pass); smoke section [32/33]; does not generate real OAuth URL, does not execute OAuth, does not use real credentials.

**Phase 4 — OAuth callback and token-exchange boundary validator** (`openclaw/oauth_callback.py` · `openclaw/run_oauth_callback_demo.py`): pure stdlib local-only validator; `OAuthCallbackDesignInput` (32 fields); 32 failure codes; hard-stop detection for callback URL receipt, auth code receipt/logging/commit/paste-to-chat, token exchange attempt, token response receipt/logging/commit, and credential presence; boundary requirement checks for state verification, secure channel, token exchange approval/window, redacted status verification, storage/rollback boundaries, audit/evidence requirements, and operator confirmation; `validate_oauth_callback_design()`; 40 demo test scenarios (98 assertions, all pass); smoke section [33/33]; does not receive real callback URL, does not receive real auth code, does not exchange tokens, does not call OAuth/Google Ads/GCP/Secret Manager.

**Phase 5 — Secure credential handoff protocol design** (`docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md`): documentation-only handoff protocol; 14 sections (A–N); credential classes covered (7: refresh token, access token, client ID, client secret, developer token, customer ID, login customer ID); forbidden transmission channels (9); acceptable transmission channels (4 with conditions); 12-step handoff sequence (E1–E12); Secret Manager write path reference (V5.15–V5.17 infrastructure, pre-write validators); audit requirements (7); forbidden content classes (12); boundary rules between OAuth ceremony and Secret Manager write (6); rollback and revocation integration (pre-write readiness confirmation + 7-step post-write revocation path R1–R7); participant confirmation requirements (7 roles); 15 stop conditions (L1–L15); revocation path summary; protocol compliance statement; no Python module; no real credentials; no Secret Manager write; no OAuth executed; no GCP; no network calls.

**Phase 6 — OAuth operator approval packet model** (`openclaw/oauth_approval_packet.py` · `openclaw/run_oauth_approval_packet_demo.py`): pure stdlib local-only validator; `OAuthApprovalPacketInput` (33 fields); 33 failure codes; approval record requirements (approval_present, approval_approved, approval_unexpired, approval_scope_valid); participant requirements (operator, reviewer, tenant ref, client ref, rollback owner, emergency revoke owner, evidence owner, stop authority); execution window requirements; validator gate requirements (oauth_auth_url_gate_present, oauth_callback_gate_present, credential_handoff_protocol_present, credential_intake_gate_present, secret_version_policy_gate_present, rollback_drill_gate_present, live_gate_requirement_present); audit/ceremony requirements (audit, safety grep, smoke test, final live-flag reset); hard-stop detections (real_credential_present, oauth_execution_detected, google_ads_api_called, gcp_commands_used, secret_manager_called, token_exchange_attempted); `validate_oauth_approval_packet()`; 41 demo test scenarios (110 assertions, all pass); smoke section [34/34]; does not create real approval; does not execute OAuth; does not use real credentials; does not call Google Ads API, GCP, or Secret Manager.

*Latest shipped:* **v5.20.0-beta — Controlled Real Google Ads Onboarding Readiness complete** — tag `v5.20.0-beta`. See [V5.20 Branch Closure](docs/V5_20_BRANCH_CLOSURE.md) and [v5.20.0-beta Release Notes](docs/RELEASE_NOTES_V5_20_0_BETA.md).

---

*Previous milestone:* **V5.19.0-beta — Real Credential Readiness Gates complete** — tag `v5.19.0-beta`. See [V5.19 Branch Closure](docs/V5_19_BRANCH_CLOSURE.md) and [v5.19.0-beta Release Notes](docs/RELEASE_NOTES_V5_19_0_BETA.md).

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
| V5.21 | Controlled real Google Ads OAuth onboarding ceremony · authorization URL design · callback boundary · credential handoff protocol · approval packet · dry-run runbook | **In progress** — `v5.21-controlled-real-google-ads-oauth-onboarding` |

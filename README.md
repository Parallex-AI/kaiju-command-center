# Kaiju Command Center

AI agent lab for Kaiju Digital.

## Current milestone

**V5.20 — Controlled Real Google Ads Onboarding Readiness** (branch: `v5.20-controlled-real-google-ads-onboarding-readiness` · base: `v5.19.0-beta`)

V5.20 defines and implements the final operator-controlled readiness process required before any real Google Ads credential onboarding or live API validation. No real credentials. `GOOGLE_ADS_LIVE_ENABLED=false` throughout. No deploy. No GCP commands. No IAM/API/billing changes.

**Phase 5 — First live API validation plan added.** v5.19.0-beta is the latest shipped beta.

See [V5.20 Implementation Plan](docs/V5_20_IMPLEMENTATION_PLAN.md) and the [Google Ads Real Onboarding Checklist](docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md) (operator checklist only — does not authorize real onboarding).

**Phase 3 — Onboarding ceremony validator** (`openclaw/onboarding_ceremony.py`): local-only `validate_onboarding_ceremony()` function; checks all readiness, approval, boundary, and forbidden-field/value conditions; does not execute real onboarding, OAuth, or API calls.

**Phase 4 — Credential intake dry-run validator** (`openclaw/credential_intake.py`): local-only `validate_credential_intake_dry_run()` function; enforces all 7 intake boundary rules, 4 plan requirements, 4 reference confirmations, and 6 hard-stop detection conditions; 25 failure codes; does not ingest real credentials, execute OAuth, call GCP, or make network calls.

**Phase 5 — First live API validation plan** (`docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md`): design-only plan for the first controlled read-only Google Ads API validation; 19-item precondition checklist; 17 stop conditions; 11-step rollback sequence; evidence package; no execution, no real credentials, no API calls.

**Phase 6 — Rollback and emergency revoke drill validator** (`openclaw/rollback_drill.py`): local-only `validate_rollback_drill()` function; validates the full rollback sequence including live flag confirmation, approval revocation, credential revocation, bundle deletion, audit chain verification, and live gate denial; 20 failure codes; does not revoke real credentials, call Secret Manager, or call Google Ads API.

**Phase 7 — Secret Manager version lifecycle policy validator** (`openclaw/secret_version_policy.py`): local-only `validate_secret_version_policy()` function; enforces V5.20 version lifecycle policy (`DISABLE_PREVIOUS_WITH_GRACE_PERIOD`; grace period 1–168 hours); 19 failure codes; does not call Secret Manager, disable or destroy real secret versions, or make GCP commands.

**Phase 8 — Final readiness review** (`docs/V5_20_FINAL_READINESS_REVIEW.md`): local-only readiness assessment; all V5.20 validators PASS; gap analysis complete; no open blockers; NOT approved for real credential onboarding, Google Ads API calls, OAuth execution, or `GOOGLE_ADS_LIVE_ENABLED=true` runtime activation.

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
| V5.20 | Controlled real Google Ads onboarding readiness · ceremony · checklist · intake boundary · first-call plan · rollback drill | **In progress** — `v5.20-controlled-real-google-ads-onboarding-readiness` |

# Kaiju Command Center

AI agent lab for Kaiju Digital.

## Current milestone

**V5.17 — Production Readiness Hardening complete** (branch: `v5.17-production-readiness` · tag candidate: `v5.17.0-beta`)

V5.17 delivers five production readiness phases for the OpenClaw admin credential lifecycle. Phase 1 adds a complete operator credential lifecycle runbook. Phase 2 adds a controlled live GCP lifecycle validation plan and unfilled results template. Phase 3 adds per-tenant token isolation: `OPENCLAW_TENANT_KEYS` restricts individual admin tokens to specific tenant namespaces (`403 tenant_access_denied` on violation; backward-compatible default). Phase 4 adds local admin endpoint rate limiting: sliding 60s window per token, STANDARD and SENSITIVE categories, `HTTP 429` with `retry_after_seconds`. Phase 5 adds audit append file locking: `fcntl.flock(LOCK_EX)` on Linux/Unix serializes seq/digest computation and write; safe fallback on non-Unix. Smoke suites 20/20 pass. Fake values only — no real credentials, no live Google Ads API calls, no GCP deployment, no fixed-cost infrastructure.

See [V5.17 Branch Closure](docs/V5_17_BRANCH_CLOSURE.md), [v5.17.0-beta Release Notes](docs/RELEASE_NOTES_V5_17_0_BETA.md), and [Credential Lifecycle Runbook](docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md).

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
| V5.17 | Production readiness · tenant isolation · rate limiting · audit locking · operator runbook | **Beta complete** — `v5.17.0-beta` (tag candidate) |

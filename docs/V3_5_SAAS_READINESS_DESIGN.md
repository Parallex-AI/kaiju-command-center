# V3.5 SaaS/GCP Readiness Design

**Branch:** `v3.5-saas-readiness`
**Status:** Design phase (V3.5.1)
**Depends on:** V3.0.0-alpha — OpenClaw local orchestration, HTTP server, context propagation, audit log

---

## 1. Purpose

V3.5 prepares Kaiju Command Center / OpenClaw for SaaS and GCP deployment readiness.

V3.5 does **not** implement production authentication, billing, or real tenant provisioning. It defines the scaffolding, contracts, environment variables, and deployment boundaries required before those layers can be safely added.

The goal is to make OpenClaw **production-shapeable**: the local developer experience remains frictionless, while every configuration surface, auth hook, and deployment boundary is clearly defined and ready to be wired.

---

## 2. Current Baseline (V3 Alpha)

### Architecture

```
Client / API Consumer
  ↓
OpenClaw HTTP Server        (FastAPI · port 8100 · server.py)
  ↓
process_request             (openclaw.py · envelope builder)
  ↓
policy / context / registry (policy.py · context.py · registry.py)
  ↓
Router                      (agents/router/router.py · route_request)
  ↓
Ads Agent Graph             (LangGraph · ads_graph.py)
  ↓
MemPalace                   (local file memory · mempalace.py)
  ↓
n8n                         (workflow orchestration · webhook)
  ↓
Response                    (normalized OpenClaw envelope)
  ↓
Audit Log                   (openclaw/audit/YYYY-MM-DD.jsonl)
```

### Current capabilities

- Normalized OpenClaw response envelope (`ok`, `openclaw` block, `data`, `errors`, `warnings`)
- FastAPI HTTP endpoint on port 8100 (`POST /openclaw/process`, `GET /openclaw/health`)
- Tenant / user / channel context resolution (HTTP headers → body metadata → defaults)
- `trace_id` / `request_id` propagation across systems
- Local append-only JSONL audit log (metadata only, no secrets)
- LangGraph multi-step analysis (validate → fetch → normalize → analyze → recommend → format)
- MemPalace local file memory (profile, snapshots, recommendations, insights)
- n8n webhook integration with retry/backoff
- Full smoke suite: V0 legacy / V1 graph / V2 memory / V3 core / V3 HTTP / V3 audit

---

## 3. V3.5 Target

V3.5 adds readiness scaffolding in six phases:

| Phase | Scope |
|---|---|
| V3.5.1 | Design doc + ROADMAP update |
| V3.5.2 | `openclaw/config.py` — typed env config helpers |
| V3.5.3 | `openclaw/auth.py` — API key auth placeholder (disabled by default) |
| V3.5.4 | CORS config in HTTP server (`OPENCLAW_ALLOWED_ORIGINS`) |
| V3.5.5 | Dockerfile and local container run notes |
| V3.5.6 | GCP Cloud Run deployment plan doc |

---

## 4. Non-Goals

V3.5 explicitly does **not** implement:

- Real user login or session management
- OAuth / OIDC product authentication
- Billing or subscription plans
- Database-backed tenant provisioning
- Google Ads API production integration
- Payment system
- Production-grade rate limiting
- Kubernetes or multi-region deployment
- Real Secret Manager integration (design only)
- GA4 or Meta Ads integration

---

## 5. Proposed Directory Structure

```
openclaw/
  config.py            ← V3.5.2: typed env config helpers
  auth.py              ← V3.5.3: API key auth placeholder
  openclaw.py          (existing)
  server.py            (existing — CORS added V3.5.4)
  registry.py          (existing)
  policy.py            (existing)
  context.py           (existing)
  schemas.py           (existing)
  audit.py             (existing)
  run_openclaw_demo.py (existing)

docker/
  openclaw.Dockerfile          ← V3.5.5
  docker-compose.openclaw.yml  ← V3.5.5

docs/
  V3_5_SAAS_READINESS_DESIGN.md  ← this file (V3.5.1)
  GCP_DEPLOYMENT_PLAN.md         ← V3.5.6
  ENVIRONMENT_VARIABLES.md       ← V3.5.6 or later
```

---

## 6. Environment Configuration

All OpenClaw configuration is read from environment variables. No config file is committed. A `.env.example` will be added in V3.5.6.

### Proposed variables

| Variable | Default | Description |
|---|---|---|
| `OPENCLAW_ENV` | `local` | Runtime environment: `local`, `staging`, `production` |
| `OPENCLAW_API_AUTH_ENABLED` | `false` | Enable API key enforcement |
| `OPENCLAW_API_KEYS` | `` | Comma-separated valid Bearer tokens (placeholder) |
| `OPENCLAW_ALLOWED_ORIGINS` | `*` | CORS allowed origins (comma-separated for production) |
| `OPENCLAW_DEFAULT_TENANT` | `demo-client` | Fallback tenant when none is supplied |
| `OPENCLAW_REQUIRE_TENANT_HEADER` | `false` | Reject requests without `X-Tenant-Id` header |
| `OPENCLAW_AUDIT_ENABLED` | `true` | Enable audit JSONL writes |
| `OPENCLAW_AUDIT_ROOT` | `openclaw/audit` (repo-relative) | Audit log directory |
| `MEMORY_ENABLED` | `true` | Enable MemPalace reads/writes |
| `MEMORY_ROOT` | `memory/client-memory` (repo-relative) | MemPalace storage root |
| `MEMORY_MAX_RECENT_SNAPSHOTS` | `5` | Snapshot window for historical comparison |
| `N8N_ADS_WEBHOOK_URL` | `https://flows.kaiju.digital/webhook/ads-agent-demo` | n8n webhook endpoint |
| `N8N_WEBHOOK_TIMEOUT` | `15` | n8n request timeout in seconds |

### Local defaults vs production expectations

In `local` mode all security controls default to off. In `production`:

- `OPENCLAW_API_AUTH_ENABLED=true`
- `OPENCLAW_API_KEYS` sourced from GCP Secret Manager (never hardcoded)
- `OPENCLAW_ALLOWED_ORIGINS` set to explicit frontend origin(s)
- `OPENCLAW_REQUIRE_TENANT_HEADER=true` (when multi-tenant is active)
- `MEMORY_ROOT` points to GCS/Firestore mount or is replaced by a production driver
- `OPENCLAW_AUDIT_ROOT` replaced by Cloud Logging or GCS bucket

### `config.py` design (V3.5.2)

`openclaw/config.py` will expose typed helpers:

```python
def get_openclaw_env() -> str          # "local" | "staging" | "production"
def is_auth_enabled() -> bool
def get_api_keys() -> list[str]        # parsed from comma-separated string
def get_allowed_origins() -> list[str]
def get_default_tenant() -> str
def is_tenant_header_required() -> bool
```

All helpers use `os.getenv` with safe fallbacks. No external dependencies.

---

## 7. Auth Placeholder Strategy

### Design intent

API key auth is the V3.5 placeholder for future OAuth/OIDC. It is disabled by default locally and must be explicitly enabled.

### Behavior when `OPENCLAW_API_AUTH_ENABLED=false` (default)

All requests pass through. No `Authorization` header is required.

### Behavior when `OPENCLAW_API_AUTH_ENABLED=true`

1. Request must include `Authorization: Bearer <token>` header
2. Token is looked up in `OPENCLAW_API_KEYS` (comma-separated list)
3. If missing or invalid: return normalized OpenClaw error envelope — `ok: false`, no traceback

```json
{
  "ok": false,
  "openclaw": { "version": "0.1.0", "request_id": "...", "trace_id": "..." },
  "data": null,
  "errors": [
    {
      "code": "unauthorized",
      "message": "Invalid or missing API key",
      "recoverable": true,
      "source": "openclaw"
    }
  ],
  "warnings": []
}
```

### What this is NOT

- Not OAuth. Not OIDC. Not JWT validation.
- Tokens are plaintext strings in an env var — **placeholder only**.
- Never store API keys in MemPalace memory files or audit logs.
- Never log the `Authorization` header.

### `auth.py` design (V3.5.3)

```python
def is_auth_enabled() -> bool
def validate_api_key(token: str | None) -> tuple[bool, dict | None]
    # returns (True, None) if valid or auth disabled
    # returns (False, error_dict) if invalid
```

`server.py` calls `validate_api_key` before `process_request`. If auth fails, returns 401 with the normalized error envelope.

---

## 8. Tenant Isolation Model

### Current local model (V3 alpha)

- `tenant` resolved from: `X-Tenant-Id` header → `metadata.tenant_id` → `client_id`
- `client_id` routes the agent workload and scopes MemPalace storage
- `tenant` appears in OpenClaw envelope and audit log
- MemPalace remains `client_id`-scoped local files

### Future SaaS model (post-V3.5)

- `tenant_id` owns many `client_id`s
- Tenant config (allowed agents, quotas, credentials) stored in database
- Secrets (API keys, Google Ads tokens) never stored in MemPalace or local files
- Tenant-specific credentials resolved via secure mapping (GCP Secret Manager)
- MemPalace migrates from local files to Firestore / Cloud Storage / vector store
- Audit log migrates from local JSONL to Cloud Logging or BigQuery

### V3.5 position

V3.5 does not implement database-backed tenants. It defines the `tenant` field contract and documents the future migration path. `OPENCLAW_REQUIRE_TENANT_HEADER` is a flag for future enforcement without code changes.

---

## 9. GCP Cloud Run Readiness

### Requirements

- OpenClaw HTTP server (`server.py`) must be fully containerizable
- Server must read port from `PORT` env var (Cloud Run sets this automatically)
- Request handling is stateless per request (no in-process session state)
- Startup must complete within Cloud Run's health check window

### Current gaps for production

| Concern | Current state | Production target |
|---|---|---|
| Audit log | Local JSONL files | Cloud Logging or GCS/BigQuery |
| MemPalace memory | Local files under `memory/client-memory/` | Firestore / Cloud Storage / SQL |
| n8n webhook URL | Env var (already correct) | GCP Secret Manager secret |
| API keys | Env var plaintext | GCP Secret Manager secret |
| Port | Hardcoded 8100 in start command | Read from `PORT` env var |
| CORS | Wildcard default | Explicit origin list from env |

### Cloud Run deployment shape (future)

```
Cloud Run Service: kaiju-openclaw
  Image: gcr.io/PROJECT/kaiju-openclaw:VERSION
  Port: $PORT (set by Cloud Run)
  Env:
    OPENCLAW_ENV=production
    OPENCLAW_API_AUTH_ENABLED=true
    OPENCLAW_API_KEYS → Secret Manager
    N8N_ADS_WEBHOOK_URL → Secret Manager
    OPENCLAW_ALLOWED_ORIGINS → Secret Manager or env
  Scaling: min 0, max N (configurable)
  Memory: 512Mi initial
  CPU: 1
```

### Dockerfile plan (V3.5.5)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY .venv/ .venv/          # or install from requirements.txt
COPY openclaw/ openclaw/
COPY agents/ agents/
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8080
CMD ["uvicorn", "openclaw.server:app", "--host", "0.0.0.0", "--port", "8080"]
```

Port 8080 is the Cloud Run convention; `PORT` env override will be wired in V3.5.5.

---

## 10. Secret Management

### Rules

- No secrets in the repository (`.env` is gitignored)
- No API keys, tokens, or credentials in MemPalace files
- No API keys, tokens, or credentials in audit logs
- Audit must never log the `Authorization` header or request body contents
- Local development uses `.env` (gitignored) or inline env var exports
- Production secrets resolved exclusively from GCP Secret Manager

### `.env.example` (to be added in V3.5.6)

```bash
OPENCLAW_ENV=local
OPENCLAW_API_AUTH_ENABLED=false
OPENCLAW_API_KEYS=
OPENCLAW_ALLOWED_ORIGINS=*
OPENCLAW_DEFAULT_TENANT=demo-client
OPENCLAW_REQUIRE_TENANT_HEADER=false
OPENCLAW_AUDIT_ENABLED=true
N8N_ADS_WEBHOOK_URL=https://flows.kaiju.digital/webhook/ads-agent-demo
N8N_WEBHOOK_TIMEOUT=15
MEMORY_ENABLED=true
```

---

## 11. CORS Strategy

### Local default

`OPENCLAW_ALLOWED_ORIGINS=*` — permissive for local development.

### Production requirement

- Explicit origin list: `OPENCLAW_ALLOWED_ORIGINS=https://app.kaiju.digital,https://dashboard.kaiju.digital`
- No wildcard (`*`) with credentials in production
- `allow_credentials=True` only when origins are explicit

### FastAPI implementation plan (V3.5.4)

```python
from fastapi.middleware.cors import CORSMiddleware

origins = get_allowed_origins()  # from config.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=(origins != ["*"]),
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
```

---

## 12. Rate Limiting / Quotas (Future)

Not implemented in V3.5. Design only.

### Future shape

- Per-tenant / per-user / per-API-key request counters
- Counters stored in Redis or Cloud Memorystore (not local files)
- Audit log entries may feed usage metrics aggregation
- Normalized error on limit exceeded:

```json
{
  "code": "rate_limited",
  "message": "Request quota exceeded",
  "recoverable": true,
  "source": "openclaw"
}
```

---

## 13. Deployment Artifacts

Artifacts to be created in later V3.5 phases:

| File | Phase | Description |
|---|---|---|
| `openclaw/config.py` | V3.5.2 | Typed env config helpers |
| `openclaw/auth.py` | V3.5.3 | API key auth placeholder |
| `docker/openclaw.Dockerfile` | V3.5.5 | Container image definition |
| `docker/docker-compose.openclaw.yml` | V3.5.5 | Local container run config |
| `docs/GCP_DEPLOYMENT_PLAN.md` | V3.5.6 | Cloud Run step-by-step plan |
| `docs/ENVIRONMENT_VARIABLES.md` | V3.5.6 | Full env var reference |
| `.env.example` | V3.5.6 | Local dev template (not committed as `.env`) |

---

## 14. Backward Compatibility

V3.5 must preserve all existing behavior at every phase:

- OpenClaw local demo (`run_openclaw_demo.py`)
- OpenClaw HTTP server (`server.py` on port 8100)
- OpenClaw V3 core smoke test (`scripts/smoke_test_v3_openclaw.sh`)
- OpenClaw V3 HTTP smoke test (`scripts/smoke_test_v3_openclaw_http.sh`)
- OpenClaw V3 audit smoke test (`scripts/smoke_test_v3_openclaw_audit.sh`)
- V2 MemPalace memory smoke test (`scripts/smoke_test_v2_memory.sh`)
- V1 LangGraph graph smoke test
- V0 legacy smoke test (`scripts/smoke_test_v0.sh`)
- Direct Router usage (`agents/router/router.py`)

Auth, CORS, and config modules must be **additive only** — no existing call site changes until new features are explicitly enabled via env vars.

---

## 15. Implementation Phases

### V3.5.1 — Design doc (this file)

- `docs/V3_5_SAAS_READINESS_DESIGN.md` created
- `docs/ROADMAP.md` updated with V3.5 phases

### V3.5.2 — Environment config module

- `openclaw/config.py` created
- Typed helpers for all env vars in §6
- No behavior changes to existing code
- Smoke tests: all existing suites pass unchanged

### V3.5.3 — Auth placeholder

- `openclaw/auth.py` created
- `validate_api_key()` function
- `server.py` updated to call auth check before `process_request`
- Default disabled (`OPENCLAW_API_AUTH_ENABLED=false`)
- New smoke test assertions: auth disabled passes, auth enabled with valid key passes, auth enabled with invalid key returns `unauthorized`

### V3.5.4 — CORS config

- `server.py` updated with `CORSMiddleware`
- Origins read from `OPENCLAW_ALLOWED_ORIGINS` via `config.py`
- Default `*` preserves local behavior
- Smoke test: existing HTTP smoke test continues to pass

### V3.5.5 — Dockerfile

- `docker/openclaw.Dockerfile` created
- `docker/docker-compose.openclaw.yml` created
- Local container run documented
- `PORT` env var wired to uvicorn
- No Cloud Run deployment yet

### V3.5.6 — GCP deployment plan

- `docs/GCP_DEPLOYMENT_PLAN.md` created
- `docs/ENVIRONMENT_VARIABLES.md` created
- `.env.example` created
- Cloud Run deployment steps documented
- Secret Manager integration plan documented

---

## 16. Acceptance Criteria for V3.5 Beta Readiness

- `openclaw/config.py` loads all env vars safely with correct defaults
- Auth placeholder works when enabled; local mode is frictionless with it disabled
- CORS middleware reads origins from env; wildcard default unchanged
- Dockerfile builds and container starts (`GET /openclaw/health` returns 200)
- All existing smoke tests pass at every phase (V0 / V1 / V2 / V3)
- No secrets committed anywhere in the repository
- `docs/GCP_DEPLOYMENT_PLAN.md` documents the Cloud Run path end-to-end
- `.env.example` documents all variables

---

## 17. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Premature SaaS complexity slows local development | Design and stubs only; no DB, no real auth, no billing until explicitly scoped |
| Placeholder API key auth gives false sense of security | Explicitly labeled as placeholder in code, docs, and error messages |
| Local file memory mistaken for production persistence | Design doc and deployment plan document the migration to GCP storage |
| Secrets leak into audit logs | Audit never logs headers, payloads, raw metrics, or recommendations — metadata only |
| CORS wildcard default carried into production | `OPENCLAW_ENV=production` check or explicit origin list enforcement |

---

## 18. Open Questions

1. **Should the public-facing entry point be OpenClaw exclusively?** Router HTTP server is currently accessible on port 8000 — should it become internal-only in production?

2. **Should Router be callable only via OpenClaw in SaaS mode?** Or remain accessible for internal tooling?

3. **Where should tenant configs live first?** Options: local JSON files (simplest), Firestore (GCP-native), Cloud SQL (relational). Decision needed before V4.

4. **Should audit migrate to Cloud Logging or BigQuery?** Cloud Logging is simpler; BigQuery enables SQL analytics on usage. Not mutually exclusive.

5. **Should MemPalace migrate to GCS, Firestore, or a vector store?** GCS is cheapest; Firestore is document-native; vector store enables semantic memory search. Depends on V4 AI feature scope.

6. **Should API keys be per tenant or per user?** Per-tenant is simpler; per-user enables finer-grained revocation. Recommend per-tenant first.

7. **Should n8n remain as the orchestration backend in SaaS?** n8n is currently self-hosted at `flows.kaiju.digital`. In Cloud Run production, consider whether n8n stays external or is replaced by direct API calls / Cloud Tasks / Pub/Sub.

8. **What is the first real integration milestone after V3.5?** Recommend: real Google Ads API read (replacing n8n fixture) as the V4 trigger event.

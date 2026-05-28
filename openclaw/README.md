# OpenClaw

OpenClaw is the V3 orchestration layer that sits above the existing Router in the Kaiju Command Center. It normalizes incoming requests, resolves tenant context, enforces policy, dispatches to the Router, and wraps every response in a consistent envelope with `request_id`, `trace_id`, and timing metadata.

## V3.1 / V3.2 Scope

V3.1 introduced the local orchestration layer (`process_request`). V3.2 adds a FastAPI HTTP server on port **8100** that delegates every request to `process_request(payload)` — no logic lives in the server itself.

## Architecture Position

```
Client
  ↓
OpenClaw  (normalize · context · policy · dispatch · envelope)
  ↓
Router    (agent dispatch · validation)
  ↓
Agent     (LangGraph · MemPalace)
  ↓
n8n       (workflow orchestration)
  ↓
Response
```

OpenClaw calls `route_request(payload)` from the Router. It does **not** call the Ads Agent, ads_graph, n8n, or MemPalace directly (except for an optional, non-fatal profile read in `context.py`).

## Entry Point

```python
from openclaw import process_request

result = process_request({
    "client_id": "demo-client",
    "agent": "ads-agent",
    "request": "summary",
})
```

## Response Envelope

Every response — success or failure — follows this shape:

```json
{
  "ok": true,
  "openclaw": {
    "version": "0.1.0",
    "request_id": "req_abc123def456",
    "trace_id": "trace_0123456789abcdef",
    "tenant": "demo-client",
    "agent": "ads-agent",
    "execution_mode": "graph",
    "started_at": "2026-05-26T10:00:00.000000+00:00",
    "finished_at": "2026-05-26T10:00:01.234000+00:00",
    "duration_ms": 1234
  },
  "data": {
    "router_response": { ... }
  },
  "errors": [],
  "warnings": []
}
```

On failure:

```json
{
  "ok": false,
  "openclaw": { "execution_mode": "none", ... },
  "data": {},
  "errors": [
    {
      "code": "unsupported_agent",
      "message": "Unsupported agent: 'analytics-agent'. Supported: ['ads-agent']",
      "recoverable": false,
      "source": "openclaw"
    }
  ],
  "warnings": []
}
```

## Supported Agents and Request Types

| Agent | Status | Supported Requests |
|---|---|---|
| `ads-agent` | active | `summary`, `cpa`, `conversions`, `raw` |

## HTTP Server (V3.2)

### Start

```bash
cd ~/kaiju/openclaw
~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8100
```

The server delegates all request processing to `process_request()` — no logic is duplicated in `server.py`.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Service metadata |
| `GET` | `/openclaw/health` | Health check |
| `POST` | `/openclaw/process` | Process an agent request |

### HTTP Header Propagation (V3.3)

The server reads the following optional headers and injects them into the request context. **Headers win over body metadata** for `trace_id` and `request_id`.

| Header | Maps to | Description |
|---|---|---|
| `X-Trace-Id` | `openclaw.trace_id` | Pin trace ID across systems |
| `X-Request-Id` | `openclaw.request_id` | Supply an external request ID |
| `X-User-Id` | `openclaw.user_id` | Caller identity |
| `X-Channel` | `openclaw.channel` | Call channel (e.g. `http`, `cli`, `web`) |
| `X-Tenant-Id` | `openclaw.tenant` / `openclaw.tenant_id` | Override tenant (future multi-tenancy) |

All headers are optional. Missing headers fall back to payload metadata or context defaults.

**Precedence:** HTTP headers > payload `metadata` > payload top-level fields > defaults

### curl examples

```bash
# Health
curl http://localhost:8100/openclaw/health

# Summary request with trace_id in body
curl -X POST http://localhost:8100/openclaw/process \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"summary","metadata":{"trace_id":"my-trace-id"}}'

# Full header propagation (V3.3)
curl -X POST http://localhost:8100/openclaw/process \
  -H "Content-Type: application/json" \
  -H "X-Trace-Id: my-trace-id" \
  -H "X-Request-Id: my-request-id" \
  -H "X-User-Id: user-123" \
  -H "X-Channel: http" \
  -H "X-Tenant-Id: tenant-abc" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"summary"}'

# Unsupported request (ok=false, code=unsupported_request)
curl -X POST http://localhost:8100/openclaw/process \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"invalid"}'

# Unsupported agent (ok=false, code=unsupported_agent)
curl -X POST http://localhost:8100/openclaw/process \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"analytics-agent","request":"summary"}'

# Malformed JSON (HTTP 400, code=invalid_json)
curl -X POST http://localhost:8100/openclaw/process \
  -H "Content-Type: application/json" \
  -d '{bad json}'
```

### Run the HTTP smoke test

```bash
cd ~/kaiju
./scripts/smoke_test_v3_openclaw_http.sh
```

The script starts and stops the server automatically. It refuses to run if port 8100 is already occupied.

## Modules

| File | Purpose |
|---|---|
| `openclaw.py` | `process_request(payload)` — main entry point |
| `server.py` | FastAPI HTTP server — delegates to `process_request` |
| `schemas.py` | Envelope builder, ID generators, `make_error` |
| `registry.py` | Agent registry and lookup functions |
| `policy.py` | `validate_request_policy(payload)` — agent/request validation |
| `context.py` | `resolve_context(payload)` — tenant, channel, optional profile |
| `run_openclaw_demo.py` | CLI demo |
| `config.py` | Typed env config helpers — `get_config()`, `redacted_config_dict()` |
| `run_config_demo.py` | Config demo — prints redacted config as JSON |
| `auth.py` | API key auth placeholder — `extract_bearer_token()`, `validate_api_auth()` |

## Run the Demo

```bash
cd ~/kaiju/openclaw

~/kaiju/.venv/bin/python3 run_openclaw_demo.py              # default: summary, ads-agent
~/kaiju/.venv/bin/python3 run_openclaw_demo.py summary
~/kaiju/.venv/bin/python3 run_openclaw_demo.py cpa
~/kaiju/.venv/bin/python3 run_openclaw_demo.py conversions
~/kaiju/.venv/bin/python3 run_openclaw_demo.py raw

# Error cases
~/kaiju/.venv/bin/python3 run_openclaw_demo.py invalid
~/kaiju/.venv/bin/python3 run_openclaw_demo.py summary analytics-agent
```

## Audit Log (V3.4)

OpenClaw appends one JSON event per request to a local JSONL file. Audit writes are **non-fatal** — if a write fails, OpenClaw returns `ok=true` with a `warnings` entry; it never fails the request.

### Location

```
openclaw/audit/YYYY-MM-DD.jsonl
```

One file per UTC day. Runtime audit files are ignored by Git.

### Audit event fields

| Field | Description |
|---|---|
| `timestamp` | UTC ISO-8601 started_at |
| `request_id` | OpenClaw request ID |
| `trace_id` | OpenClaw trace ID |
| `tenant` | Resolved tenant |
| `user_id` | Resolved user ID |
| `channel` | Resolved channel |
| `agent` | Target agent |
| `request` | Request type |
| `execution_mode` | `graph`, `legacy`, `none`, `unknown` |
| `ok` | True/False |
| `duration_ms` | Total OpenClaw duration |
| `error_codes` | List of error codes (empty on success) |
| `warning_count` | Number of warnings |
| `source` | Always `"openclaw"` |

**Not stored:** full payload, router_response, raw metrics, recommendations, tokens, or PII.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `OPENCLAW_AUDIT_ENABLED` | `true` | Set to `false` to disable all writes |
| `OPENCLAW_AUDIT_ROOT` | `openclaw/audit/` (repo-relative) | Override audit directory |

### Examples

```bash
# Audit enabled (default)
cd ~/kaiju/openclaw
~/kaiju/.venv/bin/python3 run_openclaw_demo.py summary

# Audit disabled — no crash, request still succeeds
OPENCLAW_AUDIT_ENABLED=false ~/kaiju/.venv/bin/python3 run_openclaw_demo.py summary

# Read today's audit log
tail -n 5 ~/kaiju/openclaw/audit/*.jsonl
```

### Run the audit smoke test

```bash
cd ~/kaiju
./scripts/smoke_test_v3_openclaw_audit.sh
```

The script uses an isolated temporary audit directory and cleans up on exit.

## Configuration (V3.5.2)

`openclaw/config.py` provides typed, safe helpers for all OpenClaw environment variables. It does **not** change runtime behavior — it is a read-only config loader used by future V3.5 modules (auth, CORS, Dockerfile).

### Run the config demo

```bash
cd ~/kaiju/openclaw
~/kaiju/.venv/bin/python3 run_config_demo.py

# Production env override example
OPENCLAW_ENV=production \
OPENCLAW_API_AUTH_ENABLED=true \
OPENCLAW_API_KEYS="key1,key2" \
OPENCLAW_ALLOWED_ORIGINS="https://app.kaiju.digital" \
PORT=9000 \
~/kaiju/.venv/bin/python3 run_config_demo.py
```

API keys are **never printed** — the demo output shows count only:

```json
"api_keys": {
  "configured": true,
  "count": 2
}
```

### Supported environment variables

| Variable | Default | Description |
|---|---|---|
| `OPENCLAW_ENV` | `local` | Runtime environment: `local`, `staging`, `production` |
| `OPENCLAW_API_AUTH_ENABLED` | `false` | Enable API key enforcement (V3.5.3) |
| `OPENCLAW_API_KEYS` | `` | Comma-separated Bearer tokens (placeholder) |
| `OPENCLAW_ALLOWED_ORIGINS` | `*` | CORS allowed origins (V3.5.4) |
| `OPENCLAW_DEFAULT_TENANT` | `demo-client` | Fallback tenant when none supplied |
| `OPENCLAW_REQUIRE_TENANT_HEADER` | `false` | Reject requests without `X-Tenant-Id` |
| `OPENCLAW_AUDIT_ENABLED` | `true` | Enable audit JSONL writes |
| `OPENCLAW_AUDIT_ROOT` | `openclaw/audit` | Audit log directory |
| `MEMORY_ENABLED` | `true` | Enable MemPalace reads/writes |
| `MEMORY_ROOT` | `memory/client-memory` | MemPalace storage root |
| `N8N_ADS_WEBHOOK_URL` | `None` | n8n webhook endpoint |
| `N8N_WEBHOOK_TIMEOUT` | `15.0` | n8n request timeout in seconds |
| `PORT` | `8100` | HTTP server port (Cloud Run sets this automatically) |

Invalid values fall back to the default silently — no crash, no error log.

## CORS Configuration (V3.5.4)

OpenClaw applies `CORSMiddleware` to all endpoints. Origins are read from `OPENCLAW_ALLOWED_ORIGINS` at server startup.

### Environment variable

| Variable | Default | Description |
|---|---|---|
| `OPENCLAW_ALLOWED_ORIGINS` | `*` | Comma-separated list of allowed origins |

### Local default — permissive

```bash
# Default (no env var set): allow all origins
OPENCLAW_ALLOWED_ORIGINS="*"
```

`allow_credentials` is `False` when `*` is used (required by CORS spec — wildcard and credentials cannot coexist).

### Production — explicit origins

```bash
OPENCLAW_ALLOWED_ORIGINS="https://app.kaiju.digital,https://admin.kaiju.digital"
```

`allow_credentials` is `True` when explicit origins are configured, allowing cookies and auth headers to be forwarded.

### Behavior summary

| `OPENCLAW_ALLOWED_ORIGINS` | `allow_credentials` | Effect |
|---|---|---|
| `*` (default) | `False` | All origins allowed, no credentials |
| Explicit list | `True` | Only listed origins allowed, credentials permitted |

### Preflight example

```bash
# Wildcard: returns access-control-allow-origin: *
curl -i -X OPTIONS http://localhost:8100/openclaw/process \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"

# Explicit allowed origin: returns access-control-allow-origin: https://app.kaiju.digital
OPENCLAW_ALLOWED_ORIGINS="https://app.kaiju.digital" \
  uvicorn openclaw.server:app --port 8100
curl -i -X OPTIONS http://localhost:8100/openclaw/process \
  -H "Origin: https://app.kaiju.digital" \
  -H "Access-Control-Request-Method: POST"
```

## API Key Auth Placeholder (V3.5.3)

API key authentication is a **placeholder** for future OAuth/OIDC. It is **disabled by default** — local and demo usage requires no token.

### Enable auth

```bash
export OPENCLAW_API_AUTH_ENABLED=true
export OPENCLAW_API_KEYS="my-secret-key,another-key"
```

### HTTP Authorization header

```
Authorization: Bearer <token>
```

Token must appear in `OPENCLAW_API_KEYS`. Scheme is case-insensitive (`bearer` accepted).

### Auth applies to HTTP server only

`POST /openclaw/process` is protected when auth is enabled. Direct calls to `process_request()` (e.g. `run_openclaw_demo.py`) are not affected — the HTTP boundary is the enforcement point.

### Error responses

**Missing or malformed header:**
```json
{
  "ok": false,
  "errors": [{ "code": "unauthorized", "message": "Missing or malformed Authorization header...", "recoverable": true }]
}
```

**Invalid token:**
```json
{
  "ok": false,
  "errors": [{ "code": "unauthorized", "message": "Invalid bearer token.", "recoverable": true }]
}
```

**Auth enabled but no keys configured (misconfiguration):**
```json
{
  "ok": false,
  "errors": [{ "code": "auth_not_configured", "recoverable": false }]
}
```

### curl examples

```bash
# Auth disabled (default) — no token needed
curl -X POST http://localhost:8100/openclaw/process \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"summary"}'

# Auth enabled — valid token
OPENCLAW_API_AUTH_ENABLED=true OPENCLAW_API_KEYS="my-key" \
  uvicorn openclaw.server:app --port 8100
curl -X POST http://localhost:8100/openclaw/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-key" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"summary"}'

# Auth enabled — missing token (401, code=unauthorized)
curl -X POST http://localhost:8100/openclaw/process \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"summary"}'

# Auth enabled — invalid token (401, code=unauthorized)
curl -X POST http://localhost:8100/openclaw/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer wrong-key" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"summary"}'
```

### What this is NOT

This is not OAuth, OIDC, or JWT validation. Tokens are plaintext strings in an env var. **Never use in production without replacing with a proper auth system.** API keys are never printed by `run_config_demo.py` — output shows count only.

## What OpenClaw Does Not Own

- Agent execution (Router owns dispatch)
- n8n workflow execution
- MemPalace read/write (except optional profile read in context resolution)
- Authentication (V3.5.3)
- CORS enforcement (V3.5.4)
- Billing (V4+)

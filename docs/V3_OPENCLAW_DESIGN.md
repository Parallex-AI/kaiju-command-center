# Kaiju Command Center — V3 OpenClaw Design

**Branch:** `v3-openclaw`  
**Status:** V3.1 complete — smoke test passing

---

## Implementation Status

| Phase | Description | Commit | Status |
|---|---|---|---|
| Design | V3 OpenClaw design document | `823232c` | Complete |
| V3.1 | `process_request`, registry, policy, schemas, context, trace_id propagation, CLI demo, smoke test | `927262c` | Complete |
| V3.2 | OpenClaw HTTP server (`POST /openclaw/request`, `GET /openclaw/health`) | — | Pending |
| V3.3 | Tenant context from MemPalace, `request_id`/`trace_id` propagation | — | Pending |
| V3.4 | Usage log / local observability audit trail | — | Pending |
| V3.5 | SaaS/auth/GCP preparation | — | Pending |

---

## 1. Purpose

OpenClaw is the orchestration layer that sits **above** the Router and agents. It provides a stable, normalized public entry point for all agent requests, enforcing contract consistency across clients, tenants, and future integrations.

OpenClaw coordinates:

- Request intake and schema normalization
- Tenant / client context resolution
- Agent registry lookup
- Policy validation
- Routing decisions and dispatch
- Response envelope normalization
- Observability hooks (`request_id`, `trace_id`, timing)
- Future SaaS boundaries (auth, billing, quotas)

OpenClaw does **not** replace:

| Component | Reason |
|---|---|
| Router Core | Still owns agent dispatch and execution mode selection |
| Ads Agent Graph | Still owns LangGraph execution and analysis logic |
| LangGraph | Still owns stateful graph execution |
| MemPalace | Still owns local-first client memory reads/writes |
| n8n | Still owns live campaign data retrieval |

---

## 2. Current System Baseline (V2)

```
Client
  ↓
Router HTTP Server     (FastAPI · localhost:8000)
  ↓
Router Core            (route_request · validation · dispatch)
  ↓
Ads Agent              (execution mode selection)
  ↓
Ads Agent Graph        (LangGraph StateGraph)
  ↓
load_client_memory     (MemPalace read)
  ↓
n8n Client             (fetch live metrics · retry/backoff)
  ↓
normalize → compare_with_history → analyze → recommend → format
  ↓
write_memory           (MemPalace write)
  ↓
Router response
```

### Current V2 capabilities

- LangGraph graph execution (default); legacy opt-out via `ADS_AGENT_EXECUTION_MODE=legacy`
- Derived metrics: `ctr`, `cpc`, `conversion_rate`, `cpm`
- Structured recommendation schema: `type`, `severity`, `priority`, `area`, `action`, `expected_impact`, `rationale`
- `executive_summary`: `headline`, `summary`, `next_best_action`, `confidence`
- MemPalace local memory: profile, snapshots, `latest_summary.json`, `recommendations.jsonl`, `insights.jsonl`
- Enriched `historical_comparison`: trend direction for CPA, CTR, conversion rate, performance score
- Recurring risk flag and recommendation area detection
- n8n client retry/backoff: 3 attempts, 1s → 2s backoff, configurable timeout
- `MEMORY_ENABLED=false` safe degradation
- Raw mode skips memory write

---

## 3. Target V3 Architecture

```
Client / API Consumer
  ↓
OpenClaw Gateway       (request intake · schema normalization)
  ↓
Request Normalizer     (field defaults · type coercion · sanitization)
  ↓
Tenant Context Resolver (client_id → profile · org · plan)
  ↓
Policy Layer           (agent allowed · request allowed · tenant rules)
  ↓
Agent Registry         (lookup agent metadata · routing target)
  ↓
Router Dispatch        (calls existing route_request)
  ↓
Agent Graph            (LangGraph StateGraph)
  ↓
Tools / n8n / APIs     (live data retrieval)
  ↓
Memory                 (MemPalace read/write)
  ↓
Response Normalizer    (OpenClaw envelope · metadata injection)
  ↓
Observability          (request_id · trace_id · duration · warnings)
  ↓
Client Response
```

### ASCII system diagram

```
┌─────────────────────────────────────────────────────────┐
│                   CLIENT / API CONSUMER                 │
└───────────────────────────┬─────────────────────────────┘
                            │ POST payload
┌───────────────────────────▼─────────────────────────────┐
│                  OPENCLAW GATEWAY                        │
│   normalize · tenant context · policy · registry        │
│   request_id · trace_id · error normalization           │
└───────────────────────────┬─────────────────────────────┘
                            │ route_request(payload)
┌───────────────────────────▼─────────────────────────────┐
│                  ROUTER CORE                             │
│   validation · dispatch · execution mode                │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│               ADS AGENT GRAPH (LangGraph)                │
│   load_memory → fetch → normalize → analyze             │
│   recommend → format → write_memory                     │
└───────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
        n8n / APIs                   MemPalace
        (live data)              (local memory)
```

---

## 4. OpenClaw Responsibilities

### OpenClaw owns

- API-facing request contract (public schema)
- Authentication placeholder (pass-through for V3.1; enforced in V3.5)
- Tenant / client resolution (`client_id` → context object)
- Agent registry lookup (validate agent exists and is active)
- Policy validation (agent allowed, request allowed, tenant rules)
- Dispatch to Router (`route_request`)
- Response metadata injection (`request_id`, `trace_id`, `openclaw` envelope)
- `request_id` generation (UUID per request)
- `trace_id` propagation (from upstream or generated)
- Error normalization (structured `code`, `message`, `recoverable`, `source`)
- Future billing / usage hooks (placeholder in V3.1)

### OpenClaw does not own

- Campaign metric calculations
- Recommendation logic
- Performance scoring
- Direct Google Ads API calls
- Direct n8n tool calls
- Memory file writes (MemPalace responsibility)
- Graph node internals (LangGraph responsibility)
- Router execution mode selection

---

## 5. Proposed V3 Request Contract

### Full request

```json
{
  "client_id": "demo-client",
  "agent": "ads-agent",
  "request": "summary",
  "channel": "api",
  "user_id": "local-user",
  "metadata": {
    "source": "demo-client",
    "priority": "normal"
  }
}
```

### Required fields

| Field | Type | Description |
|---|---|---|
| `client_id` | string | Client or tenant identifier |
| `agent` | string | Target agent name |
| `request` | string | Request type (`summary`, `cpa`, `conversions`, `raw`) |

### Optional fields

| Field | Type | Default | Description |
|---|---|---|---|
| `channel` | string | `"api"` | Request origin (`api`, `cli`, `chat`) |
| `user_id` | string | `null` | Requesting user (for future auth) |
| `metadata` | object | `{}` | Pass-through context metadata |

Unknown metadata fields are accepted and passed through without validation.

---

## 6. Proposed V3 Response Envelope

### Success response

```json
{
  "ok": true,
  "openclaw": {
    "version": "0.1.0",
    "request_id": "a3f2c1d8-...",
    "trace_id": "b7e4a0f9-...",
    "tenant": "demo-client",
    "agent": "ads-agent",
    "execution_mode": "graph"
  },
  "data": {
    "router_response": { "...": "..." }
  },
  "errors": [],
  "warnings": []
}
```

### Error response

```json
{
  "ok": false,
  "openclaw": {
    "version": "0.1.0",
    "request_id": "a3f2c1d8-...",
    "trace_id": "b7e4a0f9-...",
    "tenant": "demo-client",
    "agent": "ads-agent",
    "execution_mode": null
  },
  "data": null,
  "errors": [
    {
      "code": "unsupported_agent",
      "message": "Agent 'unknown-agent' is not registered.",
      "recoverable": false,
      "source": "openclaw"
    }
  ],
  "warnings": []
}
```

### Error codes

| Code | Source | Recoverable | Description |
|---|---|---|---|
| `invalid_payload` | openclaw | false | Payload is not a valid dict |
| `missing_required_field` | openclaw | false | Required field absent |
| `unsupported_agent` | openclaw | false | Agent not in registry |
| `unsupported_request` | openclaw | false | Request type not supported by agent |
| `policy_violation` | openclaw | false | Policy check failed |
| `router_error` | router | varies | Router returned an error |
| `agent_error` | agent | varies | Agent graph returned an error |
| `internal_error` | openclaw | false | Unexpected failure |

---

## 7. Directory Proposal

```
openclaw/
  README.md               — module overview and usage
  openclaw.py             — main orchestration: process_request()
  registry.py             — agent registry: supported agents, metadata, routing target
  policy.py               — validation rules, allowed requests, tenant/agent compatibility
  context.py              — client context loading, MemPalace profile bridge
  schemas.py              — request/response schema helpers, error constructors
  server.py               — optional HTTP server (V3.2+)
  run_openclaw_demo.py    — local CLI demo (V3.1)
  chat_openclaw_demo.py   — interactive chat demo (future)
```

**V3.1 initial scope:** `openclaw.py`, `registry.py`, `policy.py`, `schemas.py`, `run_openclaw_demo.py`. The HTTP server (`server.py`) is deferred to V3.2.

---

## 8. OpenClaw Modules

### `openclaw.py` — main orchestration

```python
def process_request(payload: dict) -> dict:
    """
    Normalize, validate, resolve context, check policy,
    dispatch to Router, and return OpenClaw envelope.
    """
```

Responsibilities:
1. Generate `request_id` and `trace_id`
2. Normalize payload (defaults, type coercion)
3. Resolve tenant context (via `context.py`)
4. Validate policy (via `policy.py`)
5. Look up agent in registry (via `registry.py`)
6. Dispatch to `route_request(payload)` (Router Core)
7. Wrap response in OpenClaw envelope (via `schemas.py`)
8. Return normalized response

### `registry.py` — agent registry

```python
AGENT_REGISTRY = {
    "ads-agent": {
        "status": "active",
        "description": "Google Ads performance analysis agent",
        "supported_requests": ["summary", "cpa", "conversions", "raw"],
        "router_agent": "ads-agent",
        "memory_enabled": True,
    }
}

def get_agent(agent_name: str) -> dict | None: ...
def is_agent_supported(agent_name: str) -> bool: ...
def is_request_supported(agent_name: str, request_type: str) -> bool: ...
```

Future agents: `analytics-agent`, `dev-agent`, `seo-agent`, `creative-agent`.

### `policy.py` — validation rules

```python
def validate(payload: dict, context: dict) -> list[dict]:
    """
    Returns list of policy violations (empty = pass).
    Each violation: {"code": "...", "message": "...", "recoverable": false}
    """
```

Initial policies:
- Payload must be a dict
- `client_id` required (or defaulted to `demo-client`)
- `agent` must be registered and active
- `request` must be supported by the agent
- `raw` request allowed in all modes (future: dev-only flag)
- Unknown `metadata` keys passed through without error

Future policies: auth required, tenant subscription check, quota/rate limits, billing usage event, data access permission.

### `context.py` — tenant context

```python
def resolve_context(client_id: str) -> dict:
    """
    Returns tenant context dict.
    V3.1: minimal context, optional MemPalace profile read.
    """
```

Initial context shape:
```json
{
  "client_id": "demo-client",
  "profile": { "...": "..." },
  "resolved": true
}
```

Future: tenant id, org id, user id, role, plan, allowed agents, allowed integrations.

### `schemas.py` — schema helpers

```python
def make_error(code, message, recoverable=False, source="openclaw") -> dict: ...
def make_openclaw_envelope(request_id, trace_id, tenant, agent, execution_mode) -> dict: ...
def make_success_response(envelope, data, warnings) -> dict: ...
def make_error_response(envelope, errors, warnings) -> dict: ...
```

### `server.py` — HTTP server (V3.2+)

FastAPI app exposing:
- `POST /openclaw/request` → calls `process_request(payload)`
- `GET /openclaw/health` → liveness check

Not implemented in V3.1. The first V3 implementation uses `process_request` directly.

---

## 9. Relationship with Existing Router

OpenClaw does **not** replace or modify Router in V3.1. It wraps it.

```
OpenClaw.process_request(payload)
    ↓ pre-processing
    route_request(payload)   ← existing Router Core function (unchanged)
    ↓ post-processing
    OpenClaw response envelope
```

**Pre-processing (OpenClaw):** normalize, validate, context, policy  
**Dispatch:** existing `route_request(payload)` — no changes to Router  
**Post-processing (OpenClaw):** wrap response, inject `request_id`/`trace_id`, normalize errors

Router remains responsible for:
- Selecting execution mode (`graph` vs `legacy`)
- Dispatching to the correct Ads Agent function
- Returning the router envelope (`ok`, `agent`, `execution_mode`, `client_id`, `request`, `data`)

---

## 10. Agent Registry Design

### V3.1 initial registry

```json
{
  "ads-agent": {
    "status": "active",
    "description": "Google Ads performance analysis agent",
    "supported_requests": ["summary", "cpa", "conversions", "raw"],
    "router_agent": "ads-agent",
    "memory_enabled": true
  }
}
```

### Future registry entries

| Agent | Status | Description |
|---|---|---|
| `ads-agent` | Active (V3.1) | Google Ads performance analysis |
| `analytics-agent` | Planned | Cross-channel analytics aggregation |
| `seo-agent` | Planned | SEO performance and keyword analysis |
| `creative-agent` | Planned | Ad creative analysis and suggestions |
| `dev-agent` | Planned | Internal tooling and dev support |

---

## 11. Policy Layer

### V3.1 initial policies

| Policy | Rule | Violation code |
|---|---|---|
| Payload shape | Must be a dict | `invalid_payload` |
| `client_id` | Required; defaults to `demo-client` if absent | `missing_required_field` |
| `agent` | Must exist in registry and be active | `unsupported_agent` |
| `request` | Must be in agent's `supported_requests` | `unsupported_request` |
| Unknown metadata | Accepted; passed through | — (no violation) |

### Future policies

- Auth token required and valid
- Tenant subscription active and agent included in plan
- Request quota not exceeded
- Billing usage event emitted before dispatch
- Data access permission check (client_id scoped)
- `raw` request restricted to dev/local channel

---

## 12. Tenant Context

### V3.1 — minimal context

- `demo-client` only; no auth
- Optional: read `profile.json` from MemPalace if it exists
- Context is informational only; does not gate requests in V3.1

### Future context fields

| Field | Description |
|---|---|
| `tenant_id` | Stable internal tenant identifier |
| `org_id` | Organization the tenant belongs to |
| `user_id` | Requesting user within the tenant |
| `role` | User role (`admin`, `analyst`, `viewer`) |
| `plan` | Subscription plan (`free`, `pro`, `enterprise`) |
| `allowed_agents` | List of agents this tenant may access |
| `allowed_integrations` | External data sources authorized |

---

## 13. Observability

OpenClaw injects the following into every response:

| Field | Description |
|---|---|
| `request_id` | UUID generated per request |
| `trace_id` | UUID propagated from upstream or generated |
| `tenant` | Resolved `client_id` |
| `agent` | Dispatched agent name |
| `execution_mode` | `graph`, `legacy`, or `null` on error |
| `warnings` | Non-fatal issues collected during processing |

**V3.1:** All fields stored in the response envelope only — no external observability sink.

**V3.4+:** Local audit log file (JSONL) per run for usage tracking and debugging.

No external APM, metrics, or tracing tool is required in V3.

---

## 14. Error Strategy

All errors are normalized into a structured object. Raw Python tracebacks must never reach the client.

```json
{
  "code": "unsupported_agent",
  "message": "Agent 'unknown-agent' is not registered.",
  "recoverable": false,
  "source": "openclaw"
}
```

| Field | Description |
|---|---|
| `code` | Machine-readable error identifier (snake_case) |
| `message` | Human-readable description |
| `recoverable` | `true` if retrying with corrected input may succeed |
| `source` | Where the error originated (`openclaw`, `router`, `agent`, `tool`) |

Errors from Router or Agent are caught by OpenClaw and re-normalized before reaching the client. Internal exceptions produce an `internal_error` code without exposing stack traces.

---

## 15. V3 Implementation Phases

### V3.1 — Core orchestration and CLI demo

- `openclaw/openclaw.py` — `process_request(payload)`
- `openclaw/registry.py` — agent registry
- `openclaw/policy.py` — initial validation rules
- `openclaw/schemas.py` — envelope and error helpers
- `openclaw/run_openclaw_demo.py` — local CLI demo
- No HTTP server yet

### V3.2 — OpenClaw HTTP server

- `openclaw/server.py` — FastAPI app
- `POST /openclaw/request` endpoint
- `GET /openclaw/health` endpoint

### V3.3 — Tenant context and trace propagation

- `openclaw/context.py` — `resolve_context(client_id)`
- Read MemPalace `profile.json` if available
- `request_id` and `trace_id` fully propagated through response

### V3.4 — Observability and audit log

- Local JSONL audit log per run
- Duration measurement
- Request/response summary persisted locally

### V3.5 — SaaS/auth/GCP preparation

- Auth placeholder to real token validation
- Multi-tenant isolation enforcement
- GCP Cloud Run deployment readiness
- Billing/usage event hooks

---

## 16. Backward Compatibility

V3 must not break any existing contract or test.

| Contract | Requirement |
|---|---|
| Router HTTP server | Must remain functional and testable independently |
| Demo Client | Must continue to work for all 4 request types |
| Ads Agent Graph | Must run unmodified |
| V2 memory smoke test | Must pass (`scripts/smoke_test_v2_memory.sh`) |
| V1 graph smoke test | Must pass (`scripts/smoke_test_v1_graph.sh`) — 33/33 |
| V0 legacy smoke test | Must pass (`ADS_AGENT_EXECUTION_MODE=legacy ./scripts/smoke_test_v0.sh`) — 20/20 |
| `MEMORY_ENABLED=false` | Must continue to degrade cleanly |
| Legacy opt-out | `ADS_AGENT_EXECUTION_MODE=legacy` must still work |

OpenClaw adds a new entry point. It does not modify the existing one.

---

## 17. Acceptance Criteria for First V3 Implementation (V3.1)

- [ ] `process_request(payload)` works locally without a server
- [ ] Unsupported agent returns a normalized OpenClaw error (`unsupported_agent`)
- [ ] Unsupported request type returns a normalized OpenClaw error (`unsupported_request`)
- [ ] Valid `ads-agent` + `summary` dispatches through Router and returns `ok: true`
- [ ] OpenClaw response includes `request_id` and `trace_id`
- [ ] OpenClaw response wraps Router response under `data.router_response`
- [ ] `run_openclaw_demo.py` runs successfully from CLI
- [ ] V2 memory smoke test passes (33/33)
- [ ] V1 graph smoke test passes (33/33)
- [ ] V0 legacy smoke test passes (20/20)

---

## 18. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| OpenClaw duplicates Router validation logic | OpenClaw validates contract and policy; Router validates dispatch mechanics — no duplication if boundaries are respected |
| Architecture becomes too abstract for the current scale | V3.1 must be CLI-only, call existing `route_request`, and produce a runnable demo before any server work begins |
| Future auth/multi-tenant assumptions leak into V3.1 | Placeholders only; no fake auth tokens or mock tenant resolution |
| Response schema drift between OpenClaw and Router | OpenClaw wraps the Router response verbatim under `data.router_response` — never rewrites it |
| Snapshot accumulation in MemPalace during V3 testing | Use isolated test client IDs; `MEMORY_ENABLED=false` available for dry runs |

---

## 19. Open Questions

The following should be resolved before or during V3 implementation:

1. **Single entry point** — Should OpenClaw eventually replace the Router HTTP server as the only public HTTP entry point, or should Router remain independently accessible?
2. **Router server in production** — Should `agents/router/server.py` remain reachable in production, or be internal-only behind OpenClaw?
3. **`request_id` origin** — Should `request_id` always be generated by OpenClaw, or should upstream clients be allowed to supply their own?
4. **MemPalace context depth** — In V3.3, how much MemPalace context should OpenClaw load? Profile only, or recent snapshots too?
5. **`raw` request access control** — Should `raw` request type require a dev/local channel flag, or remain open?
6. **Audit log location** — Should usage/audit logs live under `memory/` (co-located with client memory), a separate `logs/` directory, or GCP Logging in V3.5?
7. **OpenClaw smoke test** — Resolved: dedicated `scripts/smoke_test_v3_openclaw.sh` created in V3.1.

---

## 20. V3.1 OpenClaw Smoke Test

A dedicated smoke test validates the OpenClaw V3.1 local orchestration layer end-to-end.

### Coverage

| Section | Assertions |
|---|---|
| [1/5] Environment | Python venv exists; all OpenClaw modules importable |
| [2/5] Valid requests | `summary`, `cpa`, `conversions`, `raw` — `ok=true`, full envelope shape, `request_id`, `trace_id`, `tenant`, `agent`, `data.router_response` |
| [3/5] Error handling | Unsupported request → `ok=false`, `code=unsupported_request`; unsupported agent → `ok=false`, `code=unsupported_agent`; no traceback exposed |
| [4/5] trace_id propagation | `metadata.trace_id` is propagated to `openclaw.trace_id` in response |
| [5/5] CLI demo | `run_openclaw_demo.py` exits cleanly for valid, invalid, and unsupported-agent cases |

### Isolation

Uses dedicated client ID `openclaw-smoke-client` — never touches `demo-client` memory.

### Run

```bash
cd ~/kaiju
./scripts/smoke_test_v3_openclaw.sh
```

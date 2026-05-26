# OpenClaw

OpenClaw is the V3 orchestration layer that sits above the existing Router in the Kaiju Command Center. It normalizes incoming requests, resolves tenant context, enforces policy, dispatches to the Router, and wraps every response in a consistent envelope with `request_id`, `trace_id`, and timing metadata.

## V3.1 Scope

V3.1 is a local-only implementation. There is no HTTP server yet. OpenClaw is called directly via `process_request(payload)` from the demo script or other local callers.

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

## Modules

| File | Purpose |
|---|---|
| `openclaw.py` | `process_request(payload)` — main entry point |
| `schemas.py` | Envelope builder, ID generators, `make_error` |
| `registry.py` | Agent registry and lookup functions |
| `policy.py` | `validate_request_policy(payload)` — agent/request validation |
| `context.py` | `resolve_context(payload)` — tenant, channel, optional profile |
| `run_openclaw_demo.py` | CLI demo |

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

## What OpenClaw Does Not Own

- Agent execution (Router owns dispatch)
- n8n workflow execution
- MemPalace read/write (except optional profile read in context resolution)
- HTTP transport (V3.2)
- Authentication (V3.5)
- Billing (V3.5)

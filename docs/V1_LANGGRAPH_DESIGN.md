# Kaiju Command Center — V1 LangGraph Design

## Overview

V1 introduces LangGraph as the execution framework inside the Ads Agent layer. The goal is to replace the single stateless `fetch_ads_data_from_n8n()` call with a multi-step `StateGraph` that fetches metrics, normalizes them, analyzes performance, and generates structured recommendations.

The Router contract, Demo Client, and all V0 interfaces remain unchanged.

---

## Design constraints

### 1. Router contract must remain stable

The Router receives the same payload in V1 as in V0:

```json
{
  "client_id": "demo-client",
  "agent": "ads-agent",
  "request": "summary"
}
```

And returns the same envelope:

```json
{
  "ok": true,
  "router": "kaiju-command-center-router",
  "agent": "ads-agent",
  "client_id": "demo-client",
  "request": "summary",
  "data": { ... }
}
```

`route_request()` in `agents/router/router.py` does not change. The Router does not need to know whether the Ads Agent is running in legacy or graph mode.

### 2. LangGraph enters inside the Ads Agent layer

LangGraph replaces the internal execution of the Ads Agent. It does not replace the Router.

```
V0 path:
  Router Core → fetch_ads_data_from_n8n() → n8n → dict

V1 path:
  Router Core → run_ads_graph() → StateGraph → [nodes] → dict
```

The return type from the agent call site is the same in both cases: a plain Python `dict` that the Router wraps in its `ok: true` envelope.

### 3. n8n remains an external tool / data source

n8n is not replaced. In V1 it becomes one node in the graph rather than the sole operation:

```
V0: entire agent = one n8n call
V1: n8n call = one node among several
```

The existing `fetch_ads_data_from_n8n()` function in `n8n_client.py` is reused as-is inside the `fetch_metrics_from_n8n` graph node. It is not modified.

---

## V1 target chain

```
Demo Client (HTTP POST)
    ↓
Router HTTP Server  (server.py — unchanged)
    ↓
Router Core         (router.py — unchanged)
    ↓
Ads Agent Graph Runner
    ads_graph.py → run_ads_graph(client_id, request_type)
    ↓
LangGraph StateGraph
    ┌─────────────────────────────────────┐
    │  validate_input                     │
    │       ↓                             │
    │  fetch_metrics_from_n8n             │
    │       ↓                             │
    │  normalize_metrics                  │
    │       ↓                             │
    │  analyze_performance                │
    │       ↓                             │
    │  generate_recommendations           │
    │       ↓                             │
    │  format_response                    │
    └─────────────────────────────────────┘
    ↓
dict  (same shape as V0 data field)
    ↓
Router response envelope  (ok: true / ok: false — unchanged)
```

---

## Proposed state object

```python
class AdsAgentState(TypedDict):
    client_id: str
    request_type: str          # summary | cpa | conversions | raw
    raw_metrics: dict          # raw JSON from n8n
    normalized_metrics: dict   # safe-typed, currency-normalized values
    analysis: dict             # computed KPIs: cpa, efficiency rating, etc.
    recommendations: list      # list of recommendation dicts
    response: dict             # final formatted output
    errors: list               # error messages collected during execution
```

All nodes read from and write to this shared state object. Nodes are pure functions: `(AdsAgentState) -> dict` (partial state update).

---

## Graph node definitions

### `validate_input`
Checks that `client_id` is non-empty and `request_type` is in the valid set. Writes to `errors` if invalid. Acts as a gate — downstream nodes do not execute if validation fails.

### `fetch_metrics_from_n8n`
Calls `fetch_ads_data_from_n8n(client_id, request_type)` (the existing `n8n_client.py` function, unmodified). Writes the raw JSON response to `state["raw_metrics"]`. On failure, writes to `state["errors"]`.

### `normalize_metrics`
Casts all numeric fields to typed Python values using `safe_float` / `safe_int`. Resolves currency. Writes to `state["normalized_metrics"]`. Makes downstream nodes independent of n8n's string/number inconsistencies.

### `analyze_performance`
Computes derived KPIs from `normalized_metrics`: CPA, efficiency band (low/medium/high), conversion rate. Writes to `state["analysis"]`. This node is where future Claude-powered reasoning will be added in V1.4+.

### `generate_recommendations`
Produces a list of structured recommendations based on `analysis`. Each recommendation has a `type`, `severity`, and `message`. Writes to `state["recommendations"]`. Empty list is valid (efficient campaign).

### `format_response`
Builds the final `response` dict from `normalized_metrics`, `analysis`, and `recommendations`. Shape varies by `request_type` to preserve backward compatibility with V0 data shapes.

---

## Request type behavior in V1

### `summary`
Executes full graph: validate → fetch → normalize → analyze → recommend → format.
Returns: campaign, spend, conversions, clicks, impressions, CPA, efficiency rating, recommendations.

### `cpa`
Executes: validate → fetch → normalize → analyze → format (CPA-focused).
Skips `generate_recommendations`. Returns: spend, conversions, CPA, efficiency band.

### `conversions`
Executes: validate → fetch → normalize → format (conversions-focused).
Skips analysis and recommendations. Returns: campaign, conversions.

### `raw`
Executes: validate → fetch → format (pass-through).
Skips normalize, analyze, recommend. Returns raw n8n payload with minimal processing.

---

## Backward compatibility

All V0 interfaces must continue to function during V1 development:

| Interface | Compatibility requirement |
|---|---|
| `router.py route_request()` | Unchanged — Router does not know about the graph |
| `server.py /route` | Unchanged — HTTP contract is identical |
| `n8n_client.py fetch_ads_data_from_n8n()` | Unchanged — reused as a node function |
| `run_n8n_demo.py` | Must continue to work (calls n8n_client directly) |
| `chat_n8n_demo.py` | Must continue to work |
| `run_router_demo.py` | Must continue to work |
| `chat_router_demo.py` | Must continue to work |
| `projects/demo-client/client.py` | Must continue to work |
| `scripts/smoke_test_v0.sh` | Must pass throughout all V1 phases |

---

## Implementation phases

### Phase V1.1 — Graph scaffold (no Router integration)

- Add LangGraph to `agents/ads-agent/requirements.txt` (new file)
- Create `agents/ads-agent/ads_graph.py` with `AdsAgentState`, node functions, and `StateGraph` wiring
- Create `agents/ads-agent/run_graph_demo.py` as a standalone CLI demo
- `n8n_client.py` is untouched
- Router is untouched
- V0 smoke test still passes

### Phase V1.2 — Execution mode flag

- Add `ADS_AGENT_EXECUTION_MODE` environment variable: `legacy` (default) | `graph`
- When `graph`, Router dispatches to `run_ads_graph()` instead of `fetch_ads_data_from_n8n()`
- Both paths return the same dict shape
- V0 smoke test still passes (runs in `legacy` mode)

```bash
# Example: run Router in graph mode
export ADS_AGENT_EXECUTION_MODE=graph
~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

### Phase V1.3 — Graph mode as default ✓ Complete

From V1.3, `graph` is the default execution mode. No env var is needed to run in graph mode.

- `ADS_AGENT_EXECUTION_MODE` unset → `graph`
- `ADS_AGENT_EXECUTION_MODE=graph` → `graph`
- `ADS_AGENT_EXECUTION_MODE=legacy` → `legacy` (explicit opt-out)
- `ADS_AGENT_EXECUTION_MODE=<invalid>` → `graph` fallback

To run the Router in legacy mode:
```bash
ADS_AGENT_EXECUTION_MODE=legacy ~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

The V1 graph smoke test (`scripts/smoke_test_v1_graph.sh`) now validates both default graph mode (no env var) and explicit legacy opt-out in a single run.

### Phase V1.4 — Richer analysis and recommendations

- Expand `analyze_performance` node with more KPIs
- Add structured recommendation schema (type, severity, action, expected impact)
- Add report generation: human-readable executive summary block
- Consider adding a Claude API call inside `analyze_performance` for LLM-powered diagnosis

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Breaking the V0 path during graph integration | Keep Router contract stable; `smoke_test_v0.sh` runs before every merge |
| Overengineering too early | V1.1 graph wraps the existing n8n call — no new logic, just structure |
| LangGraph dependency friction | Isolate in `agents/ads-agent/requirements.txt`; keep legacy path as fallback |
| Response schema drift between legacy and graph mode | Document and test the `data` dict shape for each request type before V1.3 |
| Graph state becoming too large | State fields are typed; analysis and recommendations are optional for non-summary requests |

---

## V1 acceptance criteria

The first V1 implementation (Phase V1.1) is complete when:

- [ ] `agents/ads-agent/ads_graph.py` exists with a working `StateGraph`
- [ ] `agents/ads-agent/run_graph_demo.py` runs and produces output
- [ ] Graph returns the same or richer data than the legacy n8n call for `summary`
- [ ] `scripts/smoke_test_v0.sh` still passes without modification
- [ ] Router does not import or reference `ads_graph.py`
- [ ] `n8n_client.py` is not modified
- [ ] LangGraph is the only new dependency

---

## V1 Graph Smoke Test

A dedicated smoke test validates the full graph-mode flow end to end.

```bash
cd ~/kaiju
./scripts/smoke_test_v1_graph.sh
```

**Key behaviours:**
- Intentionally refuses to run if port 8000 is already in use — this prevents accidentally testing legacy mode from a running server. Stop any existing Router server first.
- Starts the Router with `ADS_AGENT_EXECUTION_MODE=graph` in the background.
- Stops the server on exit via `trap cleanup`.
- Does **not** replace or modify `scripts/smoke_test_v0.sh`. Both tests are independent and must pass.

**What it validates:**
1. Virtual environment and all dependencies (`fastapi`, `uvicorn`, `requests`, `langgraph`)
2. Router starts cleanly in graph mode
3. HTTP routes: `/health`, `/route summary`, `/route cpa`, `/route conversions`, `/route raw` — each checked for `ok: true` and `execution_mode: "graph"`
4. `summary` response contains `analysis` and `recommendations` fields
5. Demo Client (`client.py`) output contains `ok: true` and `execution_mode: "graph"` for all request types
6. Direct graph demo (`run_graph_demo.py`) output contains `ok: true` and `execution_mode: "graph"` for all request types

---

## File map for V1.1

```
agents/ads-agent/
  n8n_client.py          ← unchanged
  run_n8n_demo.py        ← unchanged
  chat_n8n_demo.py       ← unchanged
  run_demo.py            ← unchanged
  chat_demo.py           ← unchanged
  ads_graph.py           ← NEW: StateGraph definition
  run_graph_demo.py      ← NEW: CLI demo for graph mode
  requirements.txt       ← NEW: langgraph dependency

agents/router/
  router.py              ← unchanged until V1.2
  server.py              ← unchanged until V1.2
```

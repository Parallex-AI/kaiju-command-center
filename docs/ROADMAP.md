# Kaiju Command Center — Roadmap

## V0 — Foundation (Complete)

**Tag:** `v0.0.1`

Goal: Establish a working end-to-end flow from client to agent to n8n.

### Completed

- [x] Repository workspace setup
- [x] Ads Agent local demo (local JSON fixture, no network)
- [x] n8n webhook integration (production webhook)
- [x] Dynamic request type routing: `summary`, `cpa`, `conversions`, `raw`
- [x] Router Core layer (`route_request` with validation and dispatch)
- [x] Router HTTP server (FastAPI, `/health` + `/route`)
- [x] Demo Client CLI (`client.py`, `chat_client.py`)
- [x] Virtual environment setup (`.venv`, FastAPI, uvicorn, requests)
- [x] `.gitignore`, root `README.md`, architecture and runbook docs
- [x] Git tag `v0.0.1`

### V0 chain

```
Demo Client → Router HTTP Server → Router Core → Ads Agent → n8n → Response
```

---

## V1 — LangGraph (Complete)

Goal: Replace stateless agent dispatch with a stateful LangGraph workflow for multi-step campaign analysis.

**Design document:** [docs/V1_LANGGRAPH_DESIGN.md](V1_LANGGRAPH_DESIGN.md)

### Implementation phases

- [x] **V1.1** — Graph scaffold: `ads_graph.py`, `run_graph_demo.py`, no Router integration
- [x] **V1.2** — Execution mode flag: `ADS_AGENT_EXECUTION_MODE=legacy|graph`
- [x] **V1.3** — Graph mode as default; `ADS_AGENT_EXECUTION_MODE=legacy` as explicit opt-out
- [x] **V1.4** — Richer analysis, structured recommendations, executive summary — **[spec: docs/V1_4_ANALYSIS_SPEC.md](V1_4_ANALYSIS_SPEC.md)**

### V1.4 completed capabilities

- Derived metrics: `ctr`, `cpc`, `conversion_rate`, `cpm`
- `unavailable_metrics` declaration in response (e.g. `roas`, `revenue`)
- `performance_score` — deterministic integer 0–100
- Metric classification: `cpa_level`, `ctr_level`, `conversion_rate_level`, `spend_efficiency`
- Structured recommendation schema: `type`, `severity`, `priority`, `area`, `action`, `expected_impact`, `rationale`
- `executive_summary` block: `headline`, `summary`, `next_best_action`, `confidence`
- V1 graph smoke test assertions for all V1.4 fields (33/33 passing)

- [x] **V1.4.1** — n8n client resilience hotfix: retry/backoff, configurable timeout, clearer errors

### V1.4.1 completed capabilities

- Retry on transient Timeout / ConnectionError: 3 attempts, backoff 1s → 2s
- Configurable timeout via `N8N_WEBHOOK_TIMEOUT` env var (default: 15s, safe fallback on invalid values)
- No retry on HTTP errors (4xx/5xx)
- Clearer error messages: attempt count, URL, and root cause in every error
- Stderr retry logging with UTC timestamp
- Motivation: transient n8n webhook timeouts observed during V1.4 smoke test runs

### Design notes

The Router Core dispatch interface (`route_request`) remains stable throughout V1. LangGraph replaces the internals of the Ads Agent execution only. The V0 smoke test must pass at every phase.

---

## V2 — MemPalace (Beta complete — branch: `v2-mempalace`)

Goal: Add a persistent memory layer so agents have context across sessions and clients.

**Design document:** [docs/V2_MEMPALACE_DESIGN.md](V2_MEMPALACE_DESIGN.md)

### Implementation phases

- [x] **V2.1** — Memory utility module: read/write profile, snapshots, recommendations, insights
- [x] **V2.2** — Memory nodes in Ads Graph: load and write memory around analysis
- [x] **V2.3** — Historical comparison: trend detection, recurring recommendation detection
- [x] **V2.4** — Memory smoke test and runbook update
- [ ] **V2.5** — Retention controls and raw payload opt-in flag *(deferred — not required for V2 beta)*

### V2.1 completed capabilities

- Local-first memory utility module (`mempalace.py`) — standard library only, no external dependencies
- Profile read/write: `profile.json` per client with atomic temp-file replacement
- Snapshot write: timestamped JSON files under `snapshots/`
- `latest_summary.json` updated on every summary run
- `recommendations.jsonl` append: deterministic 12-char SHA-256 `recommendation_id`
- `insights.jsonl` append
- Recent snapshots reader with configurable limit (`MEMORY_MAX_RECENT_SNAPSHOTS`)
- Memory root anchored to repo root via `Path(__file__).parents[2]`
- Runtime memory files ignored via `.gitignore` (`memory/client-memory/`)
- `MEMORY_ENABLED=false` disables all reads/writes without crashing

### V2.2 completed capabilities

- `load_client_memory` graph node: loads profile, latest_summary, and recent_snapshots before n8n fetch
- `compare_with_history` graph node: compares CPA and conversions vs. previous snapshot; produces `cpa_direction`, `conversions_direction`, `notes`
- `write_memory` graph node: writes snapshot, recommendations, insight after response formatting; skips raw mode
- `AdsAgentState` extended with `memory_context`, `historical_comparison`, `memory_write_result`, `warnings`
- `memory` block injected into all non-raw graph responses under `data.memory`
- Raw requests skip full payload storage (`write_result.skipped: true, reason: "raw mode"`)
- `MEMORY_ENABLED=false` flows through graph cleanly; `data.memory.enabled: false` in response
- Memory failures are non-fatal warnings — graph continues and returns `ok: true`
- Historical notes from `compare_with_history` surface in `analysis.notes` as `[History] ...`

### V2.3 completed capabilities

- `extract_snapshot_metrics` and `extract_snapshot_analysis` — defensive helpers for multi-shape snapshot extraction
- `compare_numeric_direction` — tolerance-based direction helper (3% band, `lower_is_better` flag)
- `compare_with_history` enriched to use `recent_snapshots` window (not only `latest_summary`)
- `historical_comparison` enriched: `history_count`, `comparison_window`, `ctr_direction`, `conversion_rate_direction`, `recurring_risk_flags`, `recurring_recommendation_areas`
- `performance_score_direction` finalized in `write_memory` after analysis completes
- `analyze_performance` generates specific `[History]` notes: CPA/conversions direction, recurring risk flags
- Backward-compatible: `has_history`, `cpa_direction`, `conversions_direction`, `notes` preserved

### V2.4 completed capabilities

- Dedicated memory smoke test: `scripts/smoke_test_v2_memory.sh`
- Isolated test client: `memory-smoke-client` (cleaned at test start; never touches `demo-client`)
- 20 assertions across 7 sections: environment, utility functions, memory disabled, graph integration, raw skip, graph disabled, Git ignore
- V2 memory smoke test: all assertions pass
- V1 graph smoke test: 33/33 passed
- V0 legacy smoke test: 20/20 passed

### V2 beta completed capabilities

- Local-first memory utilities (`mempalace.py`) — standard library only, no external dependencies
- Graph memory integration: `load_client_memory`, `compare_with_history`, `write_memory` nodes
- Enriched historical comparison: trend direction for CPA, CTR, conversion rate, performance score
- Recurring recommendation area and risk flag detection across snapshot window
- Memory smoke test (`scripts/smoke_test_v2_memory.sh`) — 20 assertions, isolated test client
- Runtime memory (`memory/client-memory/`) ignored by Git
- `MEMORY_ENABLED=false` safe degradation — no crash, `ok: true`, `memory.enabled: false`
- Raw mode skips full payload storage (`write_result.skipped: true`)
- All memory failures non-fatal warnings — graph always returns `ok: true`

**V2.5 is deferred.** Snapshot pruning and `MEMORY_STORE_RAW_PAYLOADS=true` are improvements, not blockers for the V2 beta milestone.

### Design principles

- Client-scoped file storage under `memory/client-memory/`
- Additive: memory off or missing → graph continues unchanged
- No database required in V2 (local files only)
- Compatible with future GCP/multi-tenant migration
- No credentials, secrets, or PII in memory files

---

## V3 — OpenClaw + SaaS (In progress — branch: `v3-openclaw`)

Goal: Add an orchestration layer (OpenClaw) above the Router for request normalization, tenant context, agent registry, policy enforcement, and structured response envelopes — laying the foundation for a production-ready multi-tenant SaaS platform.

**Design document:** [docs/V3_OPENCLAW_DESIGN.md](V3_OPENCLAW_DESIGN.md)

### Implementation phases

- [x] **V3.1** — OpenClaw local orchestrator: `openclaw.py`, `registry.py`, `policy.py`, `schemas.py`, `context.py`, `run_openclaw_demo.py`; `trace_id` propagation; dedicated smoke test
- [x] **V3.2** — HTTP server: `server.py` — FastAPI, port 8100, `GET /`, `GET /openclaw/health`, `POST /openclaw/process`; delegates to `process_request`; malformed JSON handled; dedicated HTTP smoke test (`scripts/smoke_test_v3_openclaw_http.sh`)
- [ ] **V3.3** — Tenant context: per-client config, scoped memory root, tenant-aware dispatch
- [ ] **V3.4** — Audit log: append-only JSONL request/response log under `openclaw/audit/`
- [ ] **V3.5** — SaaS + GCP: Cloud Run deployment, real Google Ads API, GA4, Meta Ads, CI/CD

### V3.1 completed capabilities

- `process_request(payload)` — main entry point: context resolution → policy validation → Router dispatch → normalized envelope
- Agent registry (`registry.py`): `ads-agent` active, `get_agent`, `list_agents`, `get_supported_agents`, `get_supported_requests`
- Policy layer (`policy.py`): validates agent, request type, and client_id before dispatch
- Tenant context (`context.py`): resolves `client_id`, `tenant`, `channel`, `user_id`, metadata; optional non-fatal MemPalace profile read
- Normalized envelope: `ok`, `openclaw` block (`version`, `request_id`, `trace_id`, `tenant`, `agent`, `execution_mode`, `started_at`, `finished_at`, `duration_ms`), `data.router_response`, `errors`, `warnings`
- `trace_id` propagation: caller may supply `metadata.trace_id` to pin the trace ID across systems
- Unsupported agent and unsupported request return `ok=false` with structured error — no Python traceback exposed
- Router dispatch: calls existing `route_request(payload)` — does not touch Ads Agent or MemPalace directly
- Dedicated smoke test (`scripts/smoke_test_v3_openclaw.sh`): 5 sections, validates all of the above with isolated client `openclaw-smoke-client`

### V3 architecture target

```
Client
  ↓
OpenClaw  (request normalization · tenant context · agent registry · policy · dispatch)
  ↓
Router    (agent dispatch · validation)
  ↓
Agent     (LangGraph · MemPalace)
  ↓
n8n       (workflow orchestration)
  ↓
GCP       (data · storage · compute)
  ↓
Response
```

### OpenClaw responsibilities

- Owns: request normalization, `request_id` / `trace_id` generation, agent registry lookup, policy enforcement, response envelope, error normalization
- Does not own: agent logic, graph execution, memory reads/writes, n8n communication

### V3.1 acceptance criteria (met)

- `process_request(...)` returns a valid V3 envelope with `ok`, `openclaw` block, `data.router_response`, `errors`, `warnings`
- `request_id`, `trace_id`, `tenant`, `agent`, `execution_mode`, `duration_ms` present in every response
- `metadata.trace_id` propagated to `openclaw.trace_id` when supplied
- Unsupported agent returns `ok=false`, `errors[0].code="unsupported_agent"`, no traceback
- Unsupported request returns `ok=false`, `errors[0].code="unsupported_request"`, no traceback
- All V0, V1, and V2 smoke tests pass

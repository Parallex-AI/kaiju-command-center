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

## V2 — MemPalace (Planned)

Goal: Add a persistent memory layer so agents have context across sessions and clients.

### Proposed scope

- [ ] MemPalace memory store (client-specific, structured)
- [ ] Historical campaign snapshots
- [ ] Trend detection across sessions
- [ ] Memory-augmented agent prompts
- [ ] Client memory API (read, write, summarize)
- [ ] Integration with Router payload (memory context passed to agent)

---

## V3 — OpenClaw + SaaS (Planned)

Goal: Production-ready multi-tenant platform with real data integrations.

### Proposed scope

- [ ] OpenClaw gateway (public-facing API, request parsing, client auth)
- [ ] Multi-tenant architecture (client isolation, scoped data)
- [ ] Authentication and authorization
- [ ] Client management interface
- [ ] Billing readiness
- [ ] Production GCP deployment (Cloud Run or GKE)
- [ ] Real Google Ads API integration
- [ ] Real GA4 integration
- [ ] Meta Ads integration
- [ ] Docker production containers
- [ ] CI/CD pipeline

### Architecture target

```
Client
  ↓
OpenClaw  (auth · routing · rate limiting)
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

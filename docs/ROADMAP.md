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

## V1 — LangGraph (Planned)

Goal: Replace stateless agent dispatch with a stateful LangGraph workflow for multi-step campaign analysis.

### Proposed scope

- [ ] Introduce LangGraph as the agent execution framework
- [ ] Define agent state object (campaign data, analysis steps, recommendations)
- [ ] Multi-step reasoning: ingest → analyze → diagnose → recommend
- [ ] Structured output: typed recommendation objects
- [ ] Report generation: executive summary with action items
- [ ] Router updated to invoke LangGraph graph instead of bare n8n call

### Design notes

The Router Core dispatch interface (`route_request`) will remain stable. LangGraph replaces the internals of the Ads Agent execution, not the Router API.

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

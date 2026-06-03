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

## V3 — OpenClaw + SaaS (Alpha complete — tag: `v3.0.0-alpha`)

Goal: Add an orchestration layer (OpenClaw) above the Router for request normalization, tenant context, agent registry, policy enforcement, and structured response envelopes — laying the foundation for a production-ready multi-tenant SaaS platform.

**Design document:** [docs/V3_OPENCLAW_DESIGN.md](V3_OPENCLAW_DESIGN.md)

### Implementation phases

- [x] **V3.1** — OpenClaw local orchestrator: `openclaw.py`, `registry.py`, `policy.py`, `schemas.py`, `context.py`, `run_openclaw_demo.py`; `trace_id` propagation; dedicated smoke test
- [x] **V3.2** — HTTP server: `server.py` — FastAPI, port 8100, `GET /`, `GET /openclaw/health`, `POST /openclaw/process`; delegates to `process_request`; malformed JSON handled; dedicated HTTP smoke test (`scripts/smoke_test_v3_openclaw_http.sh`)
- [x] **V3.3** — Tenant context enrichment: `channel`, `user_id`, `tenant_id` in envelope; HTTP header propagation (`X-Trace-Id`, `X-Request-Id`, `X-User-Id`, `X-Channel`, `X-Tenant-Id`); `request_id` external supply; headers win over body metadata
- [x] **V3.4** — Audit log: append-only JSONL under `openclaw/audit/YYYY-MM-DD.jsonl`; non-fatal writes; `OPENCLAW_AUDIT_ENABLED` / `OPENCLAW_AUDIT_ROOT` env vars; audit files ignored by Git; dedicated smoke test (`scripts/smoke_test_v3_openclaw_audit.sh`)
- [x] **V3.5.1** — SaaS/GCP readiness design doc + ROADMAP update — **[spec: docs/V3_5_SAAS_READINESS_DESIGN.md](V3_5_SAAS_READINESS_DESIGN.md)**
- [x] **V3.5.2** — `openclaw/config.py`: typed env config helpers
- [x] **V3.5.3** — `openclaw/auth.py`: API key auth placeholder (disabled by default)
- [x] **V3.5.4** — CORS config in HTTP server (`OPENCLAW_ALLOWED_ORIGINS` env var)
- [x] **V3.5.5** — Dockerfile and local container run notes (`docker/openclaw.Dockerfile`)
- [x] **V3.5.6** — GCP Cloud Run deployment plan doc + `.env.example` + `ENVIRONMENT_VARIABLES.md`

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

---

## V3.5 — SaaS/GCP Readiness (Beta complete — branch: `v3.5-saas-readiness`)

Goal: Add configuration scaffolding, auth placeholder, CORS policy, Dockerfile, and GCP Cloud Run deployment plan to make OpenClaw production-shapeable without implementing real auth, billing, or database-backed tenants.

**Design document:** [docs/V3_5_SAAS_READINESS_DESIGN.md](V3_5_SAAS_READINESS_DESIGN.md)

### Implementation phases

- [x] **V3.5.1** — Design doc + ROADMAP update
- [x] **V3.5.2** — `openclaw/config.py`: typed env config helpers
- [x] **V3.5.3** — `openclaw/auth.py`: API key auth placeholder (disabled by default)
- [x] **V3.5.4** — CORS config in HTTP server (`OPENCLAW_ALLOWED_ORIGINS`)
- [x] **V3.5.5** — `docker/openclaw.Dockerfile` + `docker-compose.openclaw.yml`
- [x] **V3.5.6** — `docs/GCP_DEPLOYMENT_PLAN.md` + `docs/ENVIRONMENT_VARIABLES.md` + `.env.example`

### V3.5 non-goals

V3.5 does not implement: real user login, OAuth, billing, database-backed tenants, Google Ads API production integration, Kubernetes, or multi-region deployment.

### V3.5 design principles

- Local developer experience remains frictionless (all security controls default off)
- Every env var has a safe local default
- Auth, CORS, and config are additive — no existing call site changes until features are enabled
- No secrets committed; production secrets from GCP Secret Manager
- All existing smoke suites (V0/V1/V2/V3) pass at every phase

---

## V4 — Real Integrations (Beta complete — branch: `v4-real-integrations` · tag pending: `v4.0.0-beta`)

Goal: Replace demo-only campaign data with real data source adapters, beginning with the Google Ads API. All real integrations are additive and feature-flagged. The n8n demo path remains available as a fallback and default.

**Design document:** [docs/V4_REAL_INTEGRATIONS_DESIGN.md](V4_REAL_INTEGRATIONS_DESIGN.md)

### Implementation phases

- [x] **V4.1** — Design doc + ROADMAP update
- [x] **V4.2** — Integration resolver (`resolver.py`) · `ADS_DATA_SOURCE` config · mock fixture adapter · canonical metrics schema
- [x] **V4.3** — Graph uses resolver instead of hardcoded n8n call · `n8n_demo` adapter wraps existing n8n client · all existing smoke tests pass
- [x] **V4.4** — Google Ads adapter skeleton: credential loading and validation only · `GOOGLE_ADS_LIVE_ENABLED=false` by default · no live calls
- [x] **V4.5.0** — Live integration runbook: `docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md` · OAuth2 steps · GAQL query · secret safety rules · manual test plan · production implications
- [x] **V4.5.1** — Live Google Ads fetch · `google-ads>=23.1.0` · GAQL LAST_30_DAYS query · canonical metrics · `google_ads_api_error` / `no_data` / `integration_timeout` error codes · credential sanitization · branch `v4.5.1-google-ads-live-fetch`
- [x] **V4.6** — V4 smoke test suite (`scripts/smoke_test_v4_integrations.sh`) · 37 assertions · mock fixture, resolver, Google Ads safety gates, graph integration · no live network required
- [x] **V4.7** — Release notes (`docs/V4_BETA_RELEASE_NOTES.md`) · final documentation pass · V4 beta complete

### New env vars (added in V4.2)

| Variable | Default | Secret | Purpose |
|---|---|---|---|
| `ADS_DATA_SOURCE` | `n8n_demo` | No | Data source adapter selection |
| `GOOGLE_ADS_LIVE_ENABLED` | `false` | No | Gate for live Google Ads API calls |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | `` | **Yes** | Google Ads API developer token |
| `GOOGLE_ADS_CLIENT_ID` | `` | **Yes** | OAuth2 client ID |
| `GOOGLE_ADS_CLIENT_SECRET` | `` | **Yes** | OAuth2 client secret |
| `GOOGLE_ADS_REFRESH_TOKEN` | `` | **Yes** | OAuth2 refresh token |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | `` | **Yes** | MCC/manager account ID |
| `GOOGLE_ADS_CUSTOMER_ID` | `` | **Yes** | Target advertising account ID |

### V4 design principles

- `ADS_DATA_SOURCE=n8n_demo` is the default — no behavior change unless explicitly configured
- Real integrations are additive: new code paths live behind env var flags
- All smoke suites (V0–V3) remain green at every phase
- No credentials committed; production credentials from GCP Secret Manager
- Google Ads errors are normalized — no tokens or secrets in logs, audit, or MemPalace
- OpenClaw remains the sole external API entry point

---

## V5 — Tenant Credentials & Secure Onboarding (In progress — branch: `v5-tenant-credentials`)

Goal: Allow clients to connect their Google Ads accounts through a secure onboarding flow — without exposing credentials to logs, audit records, MemPalace, or Git at any point. Introduce a tenant credential store, a secret store abstraction, and OpenClaw admin endpoints for credential management.

**Design document:** [docs/V5_TENANT_CREDENTIALS_AND_ONBOARDING_DESIGN.md](V5_TENANT_CREDENTIALS_AND_ONBOARDING_DESIGN.md)

### Implementation phases

- [x] **V5.1** — Design doc + ROADMAP update
- [x] **V5.2** — `CredentialReference` data model · `CredentialStatus` enum · `IntegrationType` enum · metadata filtering · redacted response contract · validation helper · `credentials/` package · demo · all existing smoke tests pass
- [x] **V5.3** — `CredentialStore` abstraction interface · `InMemoryCredentialStore` mock implementation · `make_store_key` / `missing_credential_status` / `assert_no_secret_material` helpers · demo · all existing smoke tests pass
- [x] **V5.4** — `LocalFileCredentialReferenceStore` · atomic JSON writes · `CREDENTIAL_REFERENCE_STORE_PATH` env var · ignored runtime path · `load_reference_store_file` / `write_reference_store_file` / `dict_to_credential_reference` helpers · demo · all existing smoke tests pass
- [x] **V5.5** — `GET /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/status` · read-only · auth placeholder applies · redacted response · no secret material accepted or returned · `admin.py` helper · demo · all existing smoke tests pass
- [x] **V5.6** — `POST /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads` · upsert CredentialReference metadata only · recursive secret-key rejection · no raw secrets accepted or stored · auth placeholder applies · redacted response · `admin.py` helper · write demo · all existing smoke tests pass
- [x] **V5.7** — `credentials/resolver.py` credential resolver bridge · `ResolvedCredentialReference` dataclass (no secret fields) · `resolve_credential_reference` resolves metadata only · missing/invalid/unavailable error codes · `assert_resolved_reference_has_no_secret_material` scanner · resolver demo · no adapter wiring yet (deferred) · all existing smoke tests pass
- [x] **V5.8** — `SecretStore` ABC · `InMemorySecretStore` (in-memory, no disk writes) · `SecretRecord` (redacted, no values) · `GOOGLE_ADS_SECRET_FIELDS` · `redact_secret_status` · `assert_allowed_secret_fields` · `assert_no_secret_values_in_payload` · secret store demo (14 sections) · no adapter wiring yet · all existing smoke tests pass
- [ ] **V5.9** — `GCPSecretManagerStore` production implementation · IAM guidance · Cloud Run integration
- [ ] **V5.10** — Front-end onboarding integration · status page · validation result display

### V5 capabilities (planned)

- Secure tenant credential store: secret material in secret backend; only `credential_ref` in metadata store
- Two onboarding modes: manual entry (internal/beta) and OAuth connect flow (SaaS/professional)
- OpenClaw admin API for credential submission, status check, live validation, and deletion
- `CredentialStore` abstraction with `EnvCredentialStore` (local/transitional) and `GCPSecretManagerStore` (production)
- Google Ads adapter retrieves credentials from credential resolver — never from request payloads or graph state
- Credential redaction: secret values never appear in API responses, logs, audit JSONL, or MemPalace
- Audit policy: tenant/client/status metadata only; no developer tokens, client secrets, refresh tokens, or OAuth codes
- GCP Secret Manager as production secret backend; IAM scoped to the secrets the service account needs
- Front-end onboarding UX: write-only credential submission; status page shows only metadata

### V5 security principles

- Credentials never stored in Git, MemPalace, audit logs, or API responses
- All secret values redacted before any observable output
- Credentials encrypted at rest in the secret backend
- Least-privilege OAuth scope (`adwords` read-only)
- Tenant isolation enforced at credential resolver level
- Admin endpoints require authentication before any credential write

### V5 non-goals (early phases)

Billing, full user management, public self-serve onboarding, production OAuth consent screen, multi-region secrets, write access to Google Ads.

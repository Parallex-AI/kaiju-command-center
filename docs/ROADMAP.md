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

## V5 — Tenant Credentials & Secure Onboarding (Beta complete — branch: `v5-tenant-credentials` · tag: `v5.0.0-beta`)

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
- [x] **V5.9** — `GoogleAdsCredentialProviderResult` · `compose_google_ads_credentials` composition layer · resolves `CredentialReference` metadata + `SecretStore` bundle → `GoogleAdsCredentials` internally · redacted output only · `repr=False` on credentials field · provider demo (11 sections) · adapter wiring deferred · all existing smoke tests pass
- [x] **V5.10** — `GOOGLE_ADS_CREDENTIAL_SOURCE` feature flag (`env` default / `provider` opt-in) · `get_google_ads_credential_source()` · `load_google_ads_credentials_from_provider()` · `fetch_google_ads_metrics()` extended with optional `tenant_id` / `secret_store` params · backward-compatible 2-arg callers unchanged · error codes `tenant_id_required` / `credential_provider_failed` / `unsupported_credential_source` · provider demo (6 sections, no live API calls) · all existing smoke tests pass
- [x] **V5.11** — `scripts/smoke_test_v5_credentials.sh` (8-section credential chain smoke test) · full import checks · all credential demos · adapter provider non-live checks · OpenClaw admin endpoints (POST/GET/forbidden/malformed/auth) · secret-safety grep · git hygiene · all 8 smoke suites pass · `docs/V5_BETA_RELEASE_NOTES.md` · V5 beta closure

> **V5 beta is complete.** Recommended tag: `v5.0.0-beta`
>
> Remaining V5 work is deferred to new branches:
> - `v5.12-gcp-secret-manager` — production secret backend (GCP Secret Manager; IAM; Cloud Run integration)
> - `v5.12-frontend-onboarding` — frontend credential submission UI; OAuth connect flow; status page

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

---

## V5.12 — GCP Secret Manager Backend (Branch: `v5.12-gcp-secret-manager`)

Goal: Replace `InMemorySecretStore` with a production-grade `GCPSecretManagerStore` implementation — enabling real tenant secrets to be stored, retrieved, and rotated in GCP Secret Manager without any secret material touching disk, logs, or API responses.

**Design document:** [docs/V5_12_GCP_SECRET_MANAGER_DESIGN.md](V5_12_GCP_SECRET_MANAGER_DESIGN.md)

### Implementation phases

- [x] **V5.12.1** — Design doc (`docs/V5_12_GCP_SECRET_MANAGER_DESIGN.md`) · ROADMAP update · no code, no dependencies, no runtime changes
- [x] **V5.12.2** — Add `google-cloud-secret-manager>=2.20.0` dependency · lazy import guard · `GCPSecretManagerStore` scaffold (disabled mode fully functional, enabled stubs raise `NotImplementedError`) · env config helpers · `build_gcp_secret_id` / `build_gcp_secret_resource_name` · `gcp_secret_manager_status()` · `credentials/__init__.py` re-exports · demo (`run_gcp_secret_manager_store_demo.py`) · all existing smoke tests pass
- [x] **V5.12.3** — `get_secret_bundle()` live read via `access_secret_version` · `get_secret_status()` redacted status from bundle result · `build_gcp_secret_version_resource_name()` · `parse_gcp_secret_payload()` (decode/validate/reject forbidden fields) · `_map_gcp_exception_to_error_code()` (NotFound/PermissionDenied/InvalidArgument) · mock client injection demo (`run_gcp_secret_manager_read_mock_demo.py`, 8 sections) · `put/delete/list` remain deferred · no real GCP credentials required · all existing smoke tests pass
- [x] **V5.12.4** — `put_secret_bundle()` via `create_secret` + `add_secret_version` · `AlreadyExists` handled safely (proceeds to add version) · `build_gcp_project_resource_name()` · `build_gcp_secret_payload()` (validated JSON bytes) · `_is_gcp_already_exists()` · `_map_gcp_write_exception_to_error_code()` · mock write demo (`run_gcp_secret_manager_write_mock_demo.py`, 9 sections) · `delete/list` remain deferred (V5.12.5) · no real GCP credentials required · all existing smoke tests pass
- [x] **V5.12.5** — `delete_secret_bundle()` via `delete_secret` · `list_secret_records()` via `list_secrets` (no payload access) · `parse_gcp_secret_id()` (reverse secret naming) · `_is_gcp_not_found()` · all-safe error returns (False/[]) for NotFound/PermissionDenied/generic · mock delete/list demo (`run_gcp_secret_manager_delete_list_mock_demo.py`, 11 sections) · no real GCP credentials required · all existing smoke tests pass
- [x] **V5.12.6** — `credentials/secret_store_factory.py` · `create_secret_store()` / `get_secret_store_backend_name()` / `secret_store_factory_status()` · auto-selects `InMemorySecretStore` (default) or `GCPSecretManagerStore` (when `GCP_SECRET_MANAGER_ENABLED=true`) · `compose_google_ads_credentials` uses factory when no `secret_store` arg passed · explicit `secret_store=` injection unchanged · mock demo (`run_secret_store_factory_demo.py`, 11 sections) · no real GCP credentials required · all existing smoke tests pass
- [ ] **V5.12.6** — OpenClaw admin credential write path wired to `GCPSecretManagerStore` · end-to-end credential submission smoke test (no live Google Ads call required)
- [x] **V5.12.7** — `scripts/smoke_test_v5_12_gcp_secret_manager.sh` · 8 sections · 28 checks · import verification · disabled mode · read/write/delete/list mock paths · SecretStoreFactory behavior · provider/factory integration · secret-safety and git hygiene · no real GCP credentials required · no live GCP calls · all existing smoke tests pass
- [x] **V5.12.8** — Cloud Run deployment guide update · IAM setup instructions · secret rotation runbook · `docs/GCP_SECRET_MANAGER_RUNBOOK.md`
- [x] **V5.12.9** — V5.12 closure · all smoke suites (V0–V5.12) pass · release notes update · `docs/V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md`

**V5.12 beta complete.** Recommended next branch: `v5.13-manual-gcp-validation`

---

## V5.13 — Manual GCP Validation (branch: `v5.13-manual-gcp-validation` · tag: `v5.13.0-beta`)

**Goal:** Validate the V5.12 `GCPSecretManagerStore` implementation against a real GCP project using operator-controlled credentials. No credentials committed. No automated GCP calls.

- [x] **V5.13.1** — Validation plan (`docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md`) · pre-flight checklist · IAM validation plan · manual command plan · env var plan · 7 validation phases (A–G) · safety stop conditions · output rules · result template · rollback plan
- [x] **V5.13.2** — Pre-flight checks documented (`docs/V5_13_PREFLIGHT_CHECKS.md`) · operator confirmed: `gcloud` installed · account authenticated · project active · Secret Manager API enabled · service account identified · IAM reviewed · no broad roles · smoke baseline 28/28 · no service account JSON in repo · **result: PASS**
- [x] **V5.13.3** — Operator manual validation · Phases A–F PASS · results in `docs/V5_13_LIVE_GCP_VALIDATION_RESULTS.md` · fake Google Ads values only · no live Google Ads API calls · no fixed-cost infrastructure · temporary test secrets cleaned up · no credentials committed
- [x] **V5.13.4** — Provider validation complete · Phase F `compose_google_ads_credentials` verified against live Secret Manager · `GCPSecretManagerStore` confirmed end-to-end · `GOOGLE_ADS_LIVE_ENABLED=false` throughout
- [x] **V5.13.5** — V5.13 closure docs · release notes · final smoke suite pass · merge to master · tag `v5.13.0-beta` · `docs/V5_13_BRANCH_CLOSURE.md` · `docs/RELEASE_NOTES_V5_13_0_BETA.md` · smoke suites PASS · ready for merge

### New env vars (added in V5.12)

| Variable | Default | Secret | Purpose |
|---|---|---|---|
| `GCP_PROJECT_ID` | `` | No | GCP project for Secret Manager API calls |
| `GCP_SECRET_MANAGER_ENABLED` | `false` | No | Gate for live Secret Manager calls |
| `GCP_SECRET_MANAGER_PREFIX` | `kaiju` | No | Secret name prefix (e.g. `kaiju-prod-google-ads-...`) |
| `GCP_SECRET_MANAGER_ENV` | `local` | No | Env segment in secret names (`local`, `dev`, `staging`, `prod`) |
| `GCP_SECRET_MANAGER_LOCATION` | `global` | No | Secret Manager location |

### V5.12 design principles

- `GCP_SECRET_MANAGER_ENABLED=false` by default — no live calls without explicit opt-in
- `InMemorySecretStore` remains default for local dev and all existing smoke tests
- Secret naming: `{prefix}-{env}-{integration_type}-{credential_ref}` (e.g. `kaiju-prod-google-ads-cred_google_ads_abcd1234ef56`)
- Secret payload: `developer_token`, `client_id` (OAuth), `client_secret`, `refresh_token` only — no `customer_id`, no access tokens
- IAM: `secretAccessor` for read paths; `secretVersionAdder`+`secretCreator` for write paths; per-prefix conditions
- Lazy import: `google-cloud-secret-manager` imported only inside `GCPSecretManagerStore` methods
- All 9 error codes defined in design doc; no secrets in any error message or log line

### V5.12 non-goals

Kubernetes, multi-region replication, cross-project secret sharing, frontend credential UI, OAuth consent screen, write access to Google Ads.

---

## V5.14 — Admin Credential Bundle GCP Wiring (branch: `v5.14-admin-gcp-wiring` · tag candidate: `v5.14.0-beta`)

**Goal:** Wire the OpenClaw admin credential write endpoint to `SecretStore` — completing the deferred V5.12.6 item. `POST /credentials/google-ads` with known Google Ads secret fields now writes through the bundle write path; metadata-only payloads continue to use the existing upsert path.

- [x] **Phase 2** — `write_google_ads_credential_bundle()` in `openclaw/admin.py` · server routing in `openclaw/server.py` · forbidden-field guard on non-secret partition · `secret_bundle_incomplete` for partial bundles · `secret_material_rejected` for disallowed fields · combined redacted response (`credential_status` + `secret_status`) · `run_admin_credentials_gcp_write_demo.py` (7 sections) · `smoke_test_v5_credentials.sh` section 9 · metadata-only path preserved
- [x] **Phase 3** — API-level FastAPI TestClient smoke · `run_admin_credentials_api_write_demo.py` · scenarios A–E: metadata-only POST, full bundle POST, incomplete bundle rejection, forbidden field rejection, cross-response leak assertion · `smoke_test_v5_credentials.sh` section 10 · 10/10 PASS
- [x] **Phase 4** — Live GCP endpoint validation · POST `/credentials/google-ads` → `GCPSecretManagerStore` via factory · fake values only · `status_code=200` · `ok=true` · `secret_status.configured=true` · all 4 fields confirmed · temporary secret deleted · `post_delete_configured=false` · `GOOGLE_ADS_LIVE_ENABLED=false` throughout · no fixed-cost infrastructure
- [x] **Closure** — branch closure doc · release notes · ROADMAP update · README update · final smoke suites PASS · ready for merge and tag

**V5.14 complete.** Recommended tag: `v5.14.0-beta`

### V5.14 design notes

- Payload routing is field-based: presence of any key from `GOOGLE_ADS_SECRET_FIELDS` routes to `write_google_ads_credential_bundle()`; all others fall through to `upsert_google_ads_credential_reference()`
- `SecretStore` is factory-selected: `InMemorySecretStore` (default) or `GCPSecretManagerStore` (`GCP_SECRET_MANAGER_ENABLED=true`)
- `secret_store=` injection bypasses the factory for test isolation
- No secret values appear in any response, log, or demo output

### V5.14 non-goals

Production deployment, real Google Ads credentials, credential validation/rotation/delete endpoints, admin RBAC hardening, frontend UI, OAuth consent screen.

---

## V5.15 — Credential Lifecycle Hardening (branch: `v5.15-credential-lifecycle-hardening` · tag candidate: `v5.15.0-beta`)

**Goal:** Complete the credential lifecycle story following V5.14's bundle write: add safe audit events on all write paths, add a structural validation endpoint, and add an env-gated revoke/delete endpoint.

- [x] **Phase 1** — Credential audit events · `build_credential_audit_event()` in `openclaw/audit.py` · `_emit_credential_audit_event()` helper · audit emission on `upsert_google_ads_credential_reference()` (`operation="metadata_upsert"`) and `write_google_ads_credential_bundle()` (`operation="bundle_write"`) · audit events never include `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, or any secret value · lifecycle demo sections A–D (audit assertions)
- [x] **Phase 2** — Structural validation endpoint · `validate_google_ads_credentials()` in `openclaw/admin.py` · `POST /credentials/google-ads/validate` route · uses `get_secret_status()` only — never calls `get_secret_bundle()` or Google Ads API · updates `CredentialReference` to `ACTIVE` or `VALIDATION_FAILED` · sets `last_validated_at` · emits `operation="validate"` audit event · lifecycle demo sections E–G · FastAPI TestClient demo (Validate B/A/C)
- [x] **Phase 3** — Revoke/delete endpoint · `delete_google_ads_credentials()` in `openclaw/admin.py` · `DELETE /credentials/google-ads` route · `OPENCLAW_ADMIN_DELETE_ENABLED=true` required (403 by default) · calls `delete_secret_bundle()` only — never reads secrets · marks `CredentialReference` as `REVOKED` · idempotent (`warnings=["secret_already_absent"]` when already absent) · emits `operation="delete"` audit event · lifecycle demo sections H–K (76/76 PASS) · FastAPI TestClient demo Delete E/A/D/B/C
- [x] **Closure** — branch closure doc · release notes · ROADMAP update · README update · `smoke_test_v5_credentials.sh` extended to 14/14 · final smoke suites PASS · ready for merge and tag

**V5.15 complete.** Recommended tag: `v5.15.0-beta`

### V5.15 design notes

- `build_credential_audit_event()` is a new function separate from `build_audit_event()` — shaped for credential operations, not OpenClaw process responses
- Validate path: `get_secret_status()` only; field presence booleans only; `live_api_tested=false` always
- Delete path: `delete_secret_bundle()` + `get_secret_status()` only; `get_secret_bundle()` never called
- `_is_admin_delete_enabled()` reads `os.environ` at call time — no caching; safe to toggle without restart
- Idempotent delete: `delete_secret_bundle()` returning `False` → `ok=true`, `warnings=["secret_already_absent"]`

### V5.15 non-goals

Production deployment, real Google Ads credentials, live API validation, RBAC hardening, audit log tamper-resistance, secret rotation endpoint, live GCP delete validation, frontend UI.

---

## V5.16 — Admin RBAC and Audit Hardening (branch: `v5.16-admin-rbac-audit-hardening` · tag candidate: `v5.16.0-beta`)

**Goal:** Harden the OpenClaw admin credential lifecycle across three dimensions: token-scoped RBAC, audit sequence/digest hardening, and a credential rotation endpoint.

- [x] **Phase 1** — Token-scoped RBAC · `AdminScope` enum (`READ`, `WRITE`, `VALIDATE`, `ROTATE`, `DELETE`, `ADMIN`) · `OPENCLAW_ADMIN_KEYS` / `OPENCLAW_READ_KEYS` env vars · per-endpoint minimum-scope enforcement · `401 unauthorized` / `403 scope_not_granted` distinction · backward-compatible `OPENCLAW_API_KEYS` fallback (`READ`-only)
- [x] **Phase 2** — Audit seq/digest hardening · `seq` (1-based, monotonic per file) + `file_digest` (SHA-256 pre-append) on every credential audit event · `verify_audit_file()` · `prune_audit_files()` · `OPENCLAW_AUDIT_RETAIN_DAYS` (default 90) · `audit_append_failed` warning visibility on all five write paths
- [x] **Phase 3** — Credential rotation endpoint · `rotate_google_ads_credentials()` in `openclaw/admin.py` · `POST /credentials/google-ads/rotate` route · `AdminScope.ROTATE` required · `put_secret_bundle()` only — no `get_secret_bundle()` · `get_secret_status()` structural validation · `operation="rotate"` audit event · lifecycle demo sections P–T · API demo scenarios A–F
- [x] **Closure** — branch closure doc · release notes · ROADMAP update · README update · `smoke_test_v5_credentials.sh` extended to 17/17 · final smoke suites PASS · ready for merge and tag

**V5.16 complete.** Recommended tag: `v5.16.0-beta`

### V5.16 design notes

- `AdminScope.ADMIN` grants all scopes; all other scopes are discrete (no implicit promotion)
- `OPENCLAW_API_KEYS` is now `READ`-only; callers needing WRITE/VALIDATE/ROTATE/DELETE must use `OPENCLAW_ADMIN_KEYS`
- Rotate path: pre-write validation requires all four fields before any write occurs; `REVOKED` credentials return `409 invalid_status_for_rotation`
- Audit `seq`/`file_digest` is tamper-evident but not cryptographically signed; not concurrent-writer safe

### V5.16 non-goals

Production deployment, real Google Ads credentials, live API validation, per-tenant IAM RBAC, cryptographic audit signing, BigQuery audit replication, GCP Secret Manager version destruction on rotate, rate limiting, frontend UI.

---

## V5.17 — Production Readiness Hardening (branch: `v5.17-production-readiness` · tag candidate: `v5.17.0-beta`)

**Goal:** Prepare OpenClaw admin credential lifecycle for controlled real-credential onboarding, with operator runbook, live GCP lifecycle validation plan, per-tenant token isolation, local rate limiting, and concurrent-writer-safe audit append.

- [x] **Phase 1 — Operator runbook** — `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` · step-by-step lifecycle guide: onboard, validate, rotate, revoke · fake-values-only rehearsal checklist · real credential readiness gates · full error reference
- [x] **Phase 2 — Controlled live GCP lifecycle validation plan** — `docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md` (eight-phase fake-secret plan A–H) · `docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md` (unfilled operator template — not yet executed)
- [x] **Phase 3 — Per-tenant admin permission model** — `OPENCLAW_TENANT_KEYS` env var · `parse_tenant_keys()` in `config.py` · `validate_tenant_access()` in `auth.py` · `403 tenant_access_denied` · backward-compatible default (unlisted tokens retain global access)
- [x] **Phase 4 — Rate limiting and abuse protection** — `openclaw/rate_limit.py` · STANDARD and SENSITIVE categories · sliding 60s window per token · `OPENCLAW_ADMIN_RATE_LIMIT_RPM` / `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` · `HTTP 429` with `retry_after_seconds` · denied requests do not consume budget
- [x] **Phase 5 — Audit persistence hardening** — `fcntl.flock(LOCK_EX)` on Linux/Unix · seq/digest computed and written atomically under lock · `lock_used` return field · safe fallback for non-Unix
- [x] **Closure** — branch closure doc · release notes · ROADMAP update · README update · `smoke_test_v5_credentials.sh` 20/20 · `smoke_test_v5_12_gcp_secret_manager.sh` 8/8 · ready for merge and tag

**V5.17 complete.** Recommended tag: `v5.17.0-beta`

### V5.17 deferred items (future branches)

- Cloud Run deployment (requires service account, IAM, billing authorization)
- GCP Secret Manager version destruction / disable policy on rotate
- Redis/Memorystore distributed rate limiting (rate limiter is currently process-local)
- BigQuery audit replication / Cloud Storage audit archival with optional object lock
- KMS/HSM cryptographic audit signing
- OAuth2 / admin identity provider integration
- Real Google Ads OAuth credential onboarding and live API validation
- Live GCP lifecycle validation execution (results template is unfilled)

---

## V5.18 — Live GCP Fake-Secret Validation (branch: `v5.18-live-gcp-fake-validation` · tag: `v5.18.0-beta`)

**Goal:** Execute the controlled live GCP Secret Manager lifecycle validation that V5.17 planned but did not execute. Validate the full HTTP → `server.py` → `admin.py` → `GCPSecretManagerStore` chain using fake Google Ads credential values only — write, status, validate, rotate, delete, audit verification, and cleanup.

**Base release:** `v5.17.0-beta`

- [x] **Phase A — Local and tool preflight** — branch state, smoke suite baseline (20/20 + 8/8), GOOGLE_ADS_LIVE_ENABLED=false confirmed
- [x] **Phase B — GCP CLI/auth preflight** — gcloud 579.0.0, ADC confirmed, no existing rehearsal secret, IAM deferred to implicit validation via write/delete
- [x] **Phase C — Secret Manager API availability check** — API enabled, secret count 0
- [x] **Phase D — Local env setup** — fake tokens only; temp audit root and credential store paths outside repo
- [x] **Phase E — Start local OpenClaw server** — `GCP_SECRET_MANAGER_ENABLED=true`, `GOOGLE_ADS_LIVE_ENABLED=false`, health check PASS, 9 routes registered
- [x] **Phase F — Write fake credential bundle** — `POST /credentials/google-ads` → `GCPSecretManagerStore.put_secret_bundle()` → all 4 fields confirmed (2 prior attempts blocked by missing project env + ADC expiry)
- [x] **Phase G — Read metadata/status** — `GET /credentials/google-ads/status` → metadata only via `LocalFileCredentialReferenceStore`; no GCP call
- [x] **Phase H — Structural validate** — `POST /credentials/google-ads/validate` → `structurally_complete: true`, `live_api_tested: false` (1 prior attempt blocked by ADC re-expiry)
- [x] **Phase I — Rotate fake bundle** — `POST /credentials/google-ads/rotate` → V2 fake values written; `structurally_complete: true`; prior version retained until Phase J
- [x] **Phase J — Delete/revoke** — `DELETE /credentials/google-ads` → `GCPSecretManagerStore.delete_secret_bundle()` → secret and all versions deleted; `OPENCLAW_ADMIN_DELETE_ENABLED=true` in server env only
- [x] **Phase K — Post-delete status** — `GET /credentials/google-ads/status` → `status: revoked`, `secret_status.configured: false`; no GCP call
- [x] **Phase L — Audit verification** — `verify_audit_file()` on 3 audit files; 15 events; seq/digest chain valid; all 5 expected operations present; forbidden fields absent
- [x] **Phase M — Secret Manager cleanup verification** — evidence-only; cleanup confirmed by Phase J/K/L; no additional GCP command
- [x] **Phase N — Final results redaction and documentation** — `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md` filled, redacted, safety-grep clean, committed; final decision: PASS
- [x] **Closure** — branch closure doc · release notes · ROADMAP update · README update · final smoke suites PASS

**V5.18 complete.** Recommended tag: `v5.18.0-beta`

**Scope constraints (met):**
- No real Google Ads credentials used
- `GOOGLE_ADS_LIVE_ENABLED=false` throughout
- No Cloud Run deployment
- No new fixed-cost infrastructure beyond deleted rehearsal secret
- No IAM changes
- No billing changes
- All GCP operations executed only under explicit operator authorization per-prompt

**Deferred from V5.18:**
- Real Google Ads OAuth credential onboarding (requires separate gating and approval)
- Cloud Run deployment (requires service account, IAM, billing authorization)
- GCP Secret Manager version destruction / disable policy on rotate
- Redis/Memorystore distributed rate limiting
- BigQuery audit replication / Cloud Storage audit archival
- KMS/HSM cryptographic audit signing

---

## V5.19 — Real Credential Readiness Gates (branch: `v5.19-real-credential-readiness-gates`)

**Goal:** Build the safety controls, approval workflow, preflight infrastructure, runtime guardrails, audit requirements, and operator documentation needed before any real Google Ads credential onboarding or live API validation can occur. Does not perform real onboarding or live API calls.

**Base release:** `v5.18.0-beta`

**Implementation plan:** `docs/V5_19_IMPLEMENTATION_PLAN.md`

### Phase breakdown

- [x] **Phase 1 — Planning and branch setup** — `V5_19_IMPLEMENTATION_PLAN.md`; ROADMAP update; README update; branch `v5.19-real-credential-readiness-gates`
- [x] **Phase 2 — Live-mode gate design** — `check_live_gate()` in `openclaw/live_gate.py`; all gate conditions; error codes; unit tests
- [x] **Phase 3 — Approval record model** — `ApprovalRecord` dataclass; `ApprovalStore` interface; `LocalFileApprovalStore`; `is_approval_valid()`; unit tests
- [x] **Phase 4 — Preflight checker** — `run_live_preflight()` function; per-check result structure; integration with gate; unit tests
- [x] **Phase 5 — API/server guardrails** — server route guard for any live-mode path; `live_mode_disabled` short-circuit; FastAPI TestClient tests
- [x] **Phase 6 — Audit event additions** — `op=live_gate_check`, `op=live_mode_denied`, `op=preflight_check`, `op=adapter_invoked`; smoke test extension
- [x] **Phase 7 — Runbook updates** — `CREDENTIAL_LIFECYCLE_RUNBOOK.md` V5.19 gates + approval procedure; `GCP_SECRET_MANAGER_RUNBOOK.md` version lifecycle policy
- [x] **Phase 8 — Test coverage** — new smoke test section for gate denial paths; full test pass
- [ ] **Phase 9 — Closure docs and release notes** — `V5_19_BRANCH_CLOSURE.md`; `RELEASE_NOTES_V5_19_0_BETA.md`; ROADMAP/README updates
- [ ] **Phase 10 — Merge, tag, release** — merge to master; `v5.19.0-beta` tag; GitHub Release

### Gate conditions (`check_live_gate()`)

| Condition | Error code on failure |
|-----------|----------------------|
| `GOOGLE_ADS_LIVE_ENABLED=true` | `live_mode_disabled` |
| Approval record present and valid | `approval_missing` / `approval_expired` / `approval_revoked` |
| Preflight checks pass | `preflight_failed` |
| Credential status ACTIVE | `credential_not_ready` |
| Structural completeness confirmed | `credential_incomplete` |
| Tenant token boundary enforced | `tenant_gate_failed` |
| Audit enabled | `audit_not_enabled` |

### V5.19 scope constraints

- No real Google Ads credentials
- `GOOGLE_ADS_LIVE_ENABLED=false` throughout
- No Cloud Run deployment
- No IAM changes
- No API enablement
- No billing changes
- No fixed-cost infrastructure

**Explicitly deferred from V5.19 until separate authorization:**
- Real Google Ads OAuth credential onboarding
- Real Google Ads live API validation (`GOOGLE_ADS_LIVE_ENABLED=true`)
- Cloud Run deployment
- IAM hardening beyond current validated posture
- Secret Manager prior-version destruction (irreversible; separate authorization required)
- External approval UI
- BigQuery audit replication / Cloud Storage archival

# V4 Real Integrations — Design Document

**Branch:** `v4-real-integrations`
**Status:** V4.1 complete; V4.2 complete; V4.3 complete; V4.4 complete; V4.5.0 complete (runbook); V4.6 complete (smoke test)
**Roadmap:** [docs/ROADMAP.md](ROADMAP.md)

### V4.6 Implementation Notes

- `scripts/smoke_test_v4_integrations.sh` created — 37 assertions across 6 sections
- Section 1: environment and import checks (5 assertions)
- Section 2: `ADS_DATA_SOURCE` resolution — valid values, invalid fallback, whitespace/case handling (5 assertions)
- Section 3: canonical metrics normalization — derived fields, empty payload, client/campaign preservation, error schema (4 assertions)
- Section 4: mock fixture adapter — ok flag, data_source, source, client override, base metrics, derived metrics (6 assertions)
- Section 5: Google Ads safety gates — three-tier error progression via resolver, credential redaction (9 assertions)
- Section 6: graph integration with mock_fixture — all four request types, performance_score, executive_summary, cpa_level (13 assertions)
- Final: runtime file git status check (1 assertion)
- No live network, no credentials required; `ADS_DATA_SOURCE=mock_fixture` used for all graph tests
- `PYTHONPATH="$AGENT_DIR"` set in all helper invocations (required: Python resolves imports from CWD, not temp script dir)
- All V0–V3 smoke suites pass with no `ADS_DATA_SOURCE` set

### V4.5 Implementation Notes

- `docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md` created — full manual test plan before live code
- V4.5.0 (this runbook) documents: required credentials, OAuth2 refresh token acquisition, local `.env` setup, secret safety rules, proposed V4.5.1 implementation approach, GAQL query, manual test commands, expected success/failure shapes, testing policy, production implications
- V4.5.1 (live fetch) deferred — `google-ads` library not yet added; no live API calls made
- Runbook marks all V4.5.0 acceptance criteria as complete; V4.5.1 criteria remain pending

### V4.4 Implementation Notes

- `agents/ads-agent/integrations/google_ads_adapter.py` created — standard library only, no `google-ads` package
- `GoogleAdsCredentials` dataclass: 6 fields (`developer_token`, `client_id`, `client_secret`, `refresh_token`, `login_customer_id`, `customer_id`)
- `is_google_ads_live_enabled()` — parses `GOOGLE_ADS_LIVE_ENABLED`; defaults `false`
- `load_google_ads_credentials()` — reads env vars; empty strings become `None`; no values printed
- `validate_google_ads_credentials()` — checks 5 required fields; returns `(True, [])` or `(False, [credentials_missing error])`; lists missing field *names*, never values
- `redacted_google_ads_credentials()` — returns `{"field": {"configured": bool}}` for all 6 fields; values never exposed
- `fetch_google_ads_metrics()` — three-tier logic: live disabled → `google_ads_live_disabled`; credentials missing → `credentials_missing`; credentials valid → `google_ads_live_not_implemented`; no real API call at any tier
- `resolver.py` updated: `google_ads` path now calls `fetch_google_ads_metrics()` instead of returning a static not-implemented error
- `run_google_ads_adapter_demo.py` — prints redacted credentials, validation result, and fetch result; never prints secret values
- `docs/ENVIRONMENT_VARIABLES.md` and `.env.example` updated with all 8 new V4 env vars

### V4.3 Implementation Notes

- `ads_graph.py` fetch node renamed `fetch_metrics`; calls `resolve_ads_data()` instead of `fetch_ads_data_from_n8n()` directly
- `n8n_demo` path: resolver returns original n8n response as `raw_data`; graph normalize_metrics node consumes it exactly as before — zero behavior change
- `mock_fixture` path: resolver returns canonical metrics; graph normalize_metrics node re-derives CPM and unavailable_metrics as usual; full analysis/recommendations/executive_summary generated
- `google_ads` path: resolver returns `ok=false`; graph routes to `format_response` with controlled error — no traceback
- `data_source` field added to `AdsAgentState` TypedDict and surfaced in graph response (additive only)
- `n8n_client.py` **not modified**; `fetch_ads_data_from_n8n` still called via resolver, not removed
- All V0–V3 smoke suites pass with no `ADS_DATA_SOURCE` set (default n8n_demo)

### V4.2 Implementation Notes

- `agents/ads-agent/integrations/` package created: `__init__.py`, `schemas.py`, `resolver.py`, `mock_fixture_adapter.py`
- `agents/ads-agent/fixtures/google_ads_summary_fixture.json` — realistic fixture data, no secrets
- `agents/ads-agent/run_integration_demo.py` — standalone demo; tests all four `ADS_DATA_SOURCE` modes
- `ADS_DATA_SOURCE` env var governs adapter selection; defaults to `n8n_demo`
- `normalize_metrics()` derives `ctr`, `cpc`, `cpa`, `conversion_rate` from base fields
- `google_ads` mode returns structured `google_ads_not_implemented` error — no crash, recoverable
- Invalid `ADS_DATA_SOURCE` falls back silently to `n8n_demo`
- **Graph not modified** — `ads_graph.py` untouched; graph integration deferred to V4.3
- **All V0–V3 smoke suites pass unchanged**

---

## 1. Purpose

V4 introduces real data integrations into Kaiju Command Center, beginning with the Google Ads API. The Ads Agent currently fetches demo campaign data via an n8n webhook. V4 replaces that fixture-backed path with a real data source adapter layer, while preserving the existing demo path as a safe fallback.

V4 must not break any of the following:
- n8n demo data path
- existing LangGraph execution
- MemPalace memory reads and writes
- OpenClaw HTTP API and envelope shape
- all smoke test suites (V0–V3)
- local development flow (no credentials required by default)

---

## 2. Current Baseline

The Ads Agent currently operates on a fully demo-backed data path:

```
OpenClaw (process_request)
  ↓
Router (route_request · validation · dispatch)
  ↓
Ads Agent Graph (LangGraph)
  ↓
n8n Client (HTTP POST to webhook)
  ↓
n8n Webhook (flows.kaiju.digital)
  ↓
Demo Google Ads-like metrics (fixture JSON)
  ↓
analyze_performance node
  ↓
format_response node (recommendations · executive_summary)
  ↓
write_memory node (MemPalace snapshot · recommendations · insights)
  ↓
audit log (OpenClaw JSONL)
  ↓
OpenClaw response envelope
```

All campaign metrics returned by n8n are static fixture values. No real Google Ads credentials, accounts, or API calls are involved at any stage.

---

## 3. V4 Target Architecture

### Primary path (real integration enabled)

```
OpenClaw (process_request)
  ↓
Router (route_request · validation · dispatch)
  ↓
Ads Agent Graph (LangGraph)
  ↓
Integration Resolver (ADS_DATA_SOURCE routing)
  ↓
Google Ads Adapter
  ↓
Google Ads API (google-ads-python client)
  ↓
Normalized metrics (canonical schema)
  ↓
analyze_performance node (unchanged)
  ↓
format_response node (unchanged)
  ↓
write_memory node (unchanged)
  ↓
audit log (unchanged)
  ↓
OpenClaw response envelope (unchanged)
```

### Fallback path (real integration disabled or credentials missing)

```
Integration Resolver
  ↓
n8n Demo Adapter  (current behavior — ADS_DATA_SOURCE=n8n_demo)
  ↓
n8n Webhook (unchanged)
  ↓
Demo metrics (unchanged)
```

The resolver is the only new node inserted into the graph. All downstream nodes (analysis, memory, audit, envelope) are unchanged.

---

## 4. Core Design Principle

**Real integrations must be additive and feature-flagged.**

- `ADS_DATA_SOURCE=n8n_demo` is the default. No behavior change unless explicitly configured.
- All new code paths live behind env var flags.
- No existing stable route is broken at any phase.
- Smoke tests remain green by always running against the demo or mock fixture path.

---

## 5. Proposed Execution Modes

The `ADS_DATA_SOURCE` environment variable controls which data source adapter the Integration Resolver selects.

| Value | Behavior |
|---|---|
| `n8n_demo` | Current n8n webhook path — default |
| `google_ads` | Real Google Ads API adapter (requires credentials) |
| `mock_fixture` | Local JSON fixture — no network, for tests |

### Default

```
ADS_DATA_SOURCE=n8n_demo
```

### Behavior rules

- `n8n_demo`: resolver delegates to the existing n8n client — no change to current behavior.
- `google_ads`: resolver delegates to the Google Ads adapter. Requires valid credentials. Requires `GOOGLE_ADS_LIVE_ENABLED=true`.
- `mock_fixture`: resolver loads a local JSON fixture file. No network. No credentials. Used by smoke tests for V4 assertions.

### Resolver rejection rules

- If `ADS_DATA_SOURCE=google_ads` but `GOOGLE_ADS_LIVE_ENABLED=false` (default): resolver falls back to `n8n_demo` and emits a warning.
- If `ADS_DATA_SOURCE=google_ads` and credentials are missing: resolver returns a structured error (`credentials_missing`) — does not fall back silently.
- If `ADS_DATA_SOURCE` is unknown: resolver returns a structured error (`unsupported_data_source`).

---

## 6. Google Ads API Integration Scope

### V4 initial scope

- Fetch account/customer-level summary metrics
- Fetch campaign-level metrics
- Support a configurable date range (default: last 30 days)
- Support the following metrics:
  - `impressions`
  - `clicks`
  - `cost` (spend)
  - `conversions`
  - `ctr`
  - `cpc`
  - `cpa`
  - `conversion_rate`

### Out of scope for V4

- Campaign mutations (budget changes, bid changes, pause/enable)
- Asset uploads
- OAuth UI or browser-based auth flow
- MCC (Manager Account) hierarchy automation
- Billing and invoicing
- Offline conversions
- GA4 joins
- Multi-currency normalization
- Attribution model configuration

---

## 7. Credential Strategy

### Local / development

Credentials are supplied via environment variables only. A local `.env` file (gitignored) is the expected developer workflow. No credential file is committed to the repository.

Proposed environment variables:

| Variable | Purpose |
|---|---|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads API developer token |
| `GOOGLE_ADS_CLIENT_ID` | OAuth2 client ID |
| `GOOGLE_ADS_CLIENT_SECRET` | OAuth2 client secret |
| `GOOGLE_ADS_REFRESH_TOKEN` | Long-lived OAuth2 refresh token |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | MCC/manager account ID (if applicable) |
| `GOOGLE_ADS_CUSTOMER_ID` | Target advertising account (customer) ID |

All six are `Secret: Yes`. None are printed in logs, audit events, or MemPalace snapshots.

### Production (GCP)

- All Google Ads credentials sourced from GCP Secret Manager.
- Credentials are resolved at request time per tenant (see §8).
- No credentials in the container image.
- No credentials in audit logs.
- No credentials in MemPalace files.

### Credential validation

At startup (when `ADS_DATA_SOURCE=google_ads`), the adapter checks that all required env vars are present. Missing vars produce an `credentials_missing` error at resolution time, not at import time. This avoids crashing the server on startup if credentials are absent and the live path is not the active source.

---

## 8. Tenant Credential Mapping

### Initial local model (V4)

- `client_id` determines data source via config or fixture.
- `demo-client` continues to use `n8n_demo` regardless of global `ADS_DATA_SOURCE`.
- A local mapping file (gitignored) may associate `client_id` → `GOOGLE_ADS_CUSTOMER_ID` for local multi-client testing.

### Future SaaS model (post-V4)

- `tenant_id` owns one or more `client_id` records.
- Each `client_id` has an integration credential reference (a Secret Manager path, not the secret itself).
- At request time, the resolver fetches credentials from Secret Manager by reference.
- Credentials are never returned in API responses, stored in MemPalace, or written to audit logs.
- Credential references (not values) may appear in audit events for traceability.

---

## 9. Proposed File Structure

The following files are proposed for V4 implementation phases. None exist yet.

```
agents/ads-agent/
  integrations/
    __init__.py
    resolver.py             # ADS_DATA_SOURCE routing and mode selection
    google_ads_client.py    # google-ads-python wrapper; credential loading
    google_ads_adapter.py   # fetch + normalize → canonical metrics schema
    mock_fixture_adapter.py # loads local fixture JSON; no network
    schemas.py              # canonical metrics dataclass / TypedDict

  fixtures/
    google_ads_summary_fixture.json   # realistic sample metrics for tests

docs/
  V4_REAL_INTEGRATIONS_DESIGN.md     # this file
  GOOGLE_ADS_INTEGRATION_PLAN.md     # detailed step-by-step integration runbook (V4.7)
```

No files outside `agents/ads-agent/integrations/`, `agents/ads-agent/fixtures/`, and `docs/` are modified during V4.

---

## 10. Data Normalization Contract

All adapters (n8n demo, Google Ads, mock fixture) must return a canonical metrics dict. The graph's `analyze_performance` node reads only from this schema. Adapters must not pass raw API objects downstream.

### Canonical metrics schema

```json
{
  "source": "google_ads",
  "client": "client-id",
  "campaign": "campaign-name-or-id",
  "date_range": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD"
  },
  "currency": "ARS",
  "spend": 0.0,
  "conversions": 0,
  "clicks": 0,
  "impressions": 0,
  "ctr": null,
  "cpc": null,
  "cpa": null,
  "conversion_rate": null,
  "raw_source": "google_ads"
}
```

### Field rules

- `source`: adapter identifier string — `"n8n_demo"`, `"google_ads"`, `"mock_fixture"`.
- `raw_source`: mirrors `source`; reserved for future use when `MEMORY_STORE_RAW_PAYLOADS=true`.
- Derived metrics (`ctr`, `cpc`, `cpa`, `conversion_rate`) are `null` when base values are zero. The graph's existing derived-metric logic computes these from `spend`, `clicks`, `conversions`, `impressions`.
- `campaign`: may be `null` for account-level summaries.
- `currency`: ISO 4217 code; defaults to the account currency.

### Adapter contract

Each adapter must implement:

```python
def fetch_metrics(client_id: str, request_type: str, params: dict) -> dict:
    """Returns a canonical metrics dict or raises IntegrationError."""
```

`IntegrationError` carries a structured `code` field (see §11). The resolver catches `IntegrationError` and maps it to the graph's `errors` list without exposing raw exception messages or credentials.

---

## 11. Error Strategy

All integration errors are normalized to a structured code before reaching the OpenClaw envelope. Raw Google Ads API errors, OAuth errors, and network errors are never surfaced directly.

| Error code | Trigger |
|---|---|
| `credentials_missing` | One or more required Google Ads env vars absent |
| `credentials_invalid` | OAuth2 token rejected or developer token invalid |
| `google_ads_api_error` | Google Ads API returned a non-transient error |
| `customer_not_found` | `GOOGLE_ADS_CUSTOMER_ID` does not exist or is inaccessible |
| `no_data` | API returned zero rows for the requested date range |
| `integration_timeout` | Google Ads API request exceeded timeout |
| `unsupported_data_source` | `ADS_DATA_SOURCE` value is not recognized |

### Rules

- Error messages must not include API tokens, refresh tokens, client secrets, or developer tokens.
- Error messages may include the error code, account ID (not secret), and date range.
- Credential-related errors must be logged to stderr (not stdout, not audit log) with the credential field name but not its value.
- All integration errors result in `ok: false` in the OpenClaw response envelope.

---

## 12. Testing Strategy

### Smoke tests

- All existing smoke suites (V0–V3, 6 suites) must remain green throughout V4.
- V4 smoke tests (`scripts/smoke_test_v4_integration.sh`) use `ADS_DATA_SOURCE=mock_fixture` only — no network, no credentials required.
- The mock fixture adapter returns a deterministic canonical metrics dict from `agents/ads-agent/fixtures/google_ads_summary_fixture.json`.

### Live Google Ads tests

- Live API tests are optional and manual.
- They require `GOOGLE_ADS_LIVE_ENABLED=true` and all credential env vars.
- They are not part of the CI smoke suite.
- A manual runbook will be documented in `docs/GOOGLE_ADS_INTEGRATION_PLAN.md` (V4.7).

### Graph regression

- The `analyze_performance` node, `format_response` node, and `write_memory` node are not modified in V4.
- Their existing V1/V2 smoke test assertions continue to cover them.

---

## 13. Feature Flags

| Flag | Default | Purpose |
|---|---|---|
| `ADS_DATA_SOURCE` | `n8n_demo` | Select data source adapter |
| `GOOGLE_ADS_LIVE_ENABLED` | `false` | Gate for live Google Ads API calls |

### Rules

- `GOOGLE_ADS_LIVE_ENABLED=false` (default): resolver treats `ADS_DATA_SOURCE=google_ads` as `n8n_demo` with a warning. No Google Ads credentials are loaded or validated.
- `GOOGLE_ADS_LIVE_ENABLED=true`: resolver allows real Google Ads API calls. Missing credentials produce a structured error.
- These flags are parsed by the config module (`openclaw/config.py` or a new `ads_agent/config.py`) and never change OpenClaw's behavior directly.

---

## 14. Backward Compatibility

V4 must preserve all of the following at every implementation phase:

| Suite | Current status |
|---|---|
| V0 legacy smoke test | 20/20 pass |
| V1 graph smoke test | 33/33 pass |
| V2 memory smoke test | 20 assertions pass |
| V3 OpenClaw core smoke test | pass |
| V3 OpenClaw HTTP smoke test | pass |
| V3 OpenClaw audit smoke test | pass |

Additional compatibility requirements:
- Existing n8n demo path is preserved and remains the default.
- Response shape (OpenClaw envelope, `data`, `analysis`, `recommendations`, `executive_summary`, `memory`) does not change.
- MemPalace snapshot format does not change.
- Audit log JSONL format does not change.

---

## 15. V4 Implementation Phases

### V4.1 — Design and roadmap *(this phase)*

- Create `docs/V4_REAL_INTEGRATIONS_DESIGN.md`
- Update `docs/ROADMAP.md`

**Deliverable:** Design doc committed on `v4-real-integrations` branch.

---

### V4.2 — Integration resolver and mock fixture adapter

- Create `agents/ads-agent/integrations/__init__.py`
- Create `agents/ads-agent/integrations/resolver.py` — reads `ADS_DATA_SOURCE`, dispatches to adapter
- Create `agents/ads-agent/integrations/schemas.py` — canonical metrics TypedDict
- Create `agents/ads-agent/integrations/mock_fixture_adapter.py` — loads fixture JSON
- Create `agents/ads-agent/fixtures/google_ads_summary_fixture.json` — realistic sample data
- Add `ADS_DATA_SOURCE` to `.env.example` and `docs/ENVIRONMENT_VARIABLES.md`

No live Google Ads API. No n8n changes.

---

### V4.3 — Graph uses resolver instead of hardcoded n8n call

- Introduce `fetch_data` node in `ads_graph.py` that calls `resolver.fetch_metrics()`
- `n8n_demo` adapter wraps the existing n8n client — default behavior unchanged
- Graph state extended with `data_source` field
- All existing graph smoke test assertions must pass

---

### V4.4 — Google Ads adapter skeleton

- Create `agents/ads-agent/integrations/google_ads_client.py` — credential loading from env
- Create `agents/ads-agent/integrations/google_ads_adapter.py` — stub `fetch_metrics()` that validates credentials but does not make live calls
- `GOOGLE_ADS_LIVE_ENABLED=false` by default — no real API calls
- Credential validation errors produce structured `credentials_missing` / `credentials_invalid` errors

---

### V4.5 — Optional live Google Ads fetch

- `google_ads_adapter.py` implements real `fetch_metrics()` behind `GOOGLE_ADS_LIVE_ENABLED=true`
- Uses `google-ads-python` library to query the Google Ads API
- Returns canonical metrics dict
- Live calls are opt-in only; smoke tests still use mock fixture

---

### V4.6 — V4 smoke test suite

- Create `scripts/smoke_test_v4_integration.sh`
- Tests: resolver mode selection, mock fixture fetch, `n8n_demo` fallback, error codes for unknown source, `GOOGLE_ADS_LIVE_ENABLED=false` guard
- All tests use `ADS_DATA_SOURCE=mock_fixture` or `n8n_demo` — no live network
- All prior smoke suites (V0–V3) must remain green

---

### V4.7 — Documentation and live integration runbook

- Create `docs/GOOGLE_ADS_INTEGRATION_PLAN.md`: step-by-step for obtaining developer token, OAuth2 credentials, configuring env vars, running live test manually
- Update `docs/ENVIRONMENT_VARIABLES.md` with all new V4 env vars
- Update `.env.example` with V4 env var stubs
- Update `openclaw/README.md` if relevant

---

## 16. Acceptance Criteria for V4 Beta

| Criterion | Requirement |
|---|---|
| n8n demo path | Works unchanged with `ADS_DATA_SOURCE=n8n_demo` (default) |
| Mock fixture path | Works with `ADS_DATA_SOURCE=mock_fixture`; no network; no credentials |
| Data source resolver | Correctly routes to adapter based on `ADS_DATA_SOURCE` |
| Google Ads adapter | Exists; validates credentials; no live calls by default |
| Feature flag guard | `GOOGLE_ADS_LIVE_ENABLED=false` prevents live calls |
| Secret hygiene | No credentials committed; no tokens in logs or audit |
| Smoke tests | All V0–V4 suites pass |
| Response shape | OpenClaw envelope and analysis fields unchanged |
| OpenClaw entrypoint | OpenClaw remains the sole external API entry point |

---

## 17. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Google Ads credentials leak into repo or logs | Env-only credential loading; explicit redaction in error messages; no credential fields in audit or MemPalace |
| Live API instability breaks smoke tests | Mock fixture is default for all automated tests; live tests are manual only |
| Response schema drift between adapters | Canonical metrics schema enforced at adapter boundary; `analyze_performance` node reads only canonical fields |
| n8n demo path broken by resolver introduction | `n8n_demo` adapter wraps existing n8n client without modification; V0 smoke test covers this path |
| Google Ads API quota or rate limits in dev | Dev/test uses mock fixture by default; live calls require explicit `GOOGLE_ADS_LIVE_ENABLED=true` |
| `google-ads-python` dependency conflicts | New dependency isolated to `agents/ads-agent/requirements.txt`; existing suites run without it |

---

## 18. Open Questions

The following questions are deferred to later V4 phases or post-V4 planning:

1. **n8n long-term role** — Should Google Ads integration bypass n8n entirely, or should n8n remain an orchestration layer for some clients (e.g., transformation, alerting)?

2. **n8n coexistence** — If some clients use n8n and some use the direct Google Ads adapter, how should the resolver distinguish them? By `client_id` mapping, by tenant config, or by explicit request metadata?

3. **client_id → customer_id mapping** — How should `client_id` (OpenClaw tenant context) map to `GOOGLE_ADS_CUSTOMER_ID`? Static env var, local mapping file, or future Secret Manager reference?

4. **Date range specification** — Should date range be specified in the request payload, as env vars, or as a per-client profile setting in MemPalace?

5. **OpenClaw integration status** — Should `GET /openclaw/health` or a new `GET /openclaw/integrations` endpoint expose which data sources are configured and reachable?

6. **MemPalace and real data** — Should real Google Ads metrics write to MemPalace by default? If so, are there PII or data residency concerns with storing raw campaign data locally?

7. **Audit granularity for live errors** — Should Google Ads API errors (e.g., quota exceeded, invalid customer) be written to the audit log as a separate event type, or folded into the existing request audit entry?

---

## Further Reading

| Document | Purpose |
|---|---|
| [docs/ROADMAP.md](ROADMAP.md) | Full milestone history and V4 phases |
| [docs/ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) | All env var definitions (V4 vars added in V4.2) |
| [.env.example](.env.example) | Local dev template |
| [docs/V3_5_SAAS_READINESS_DESIGN.md](V3_5_SAAS_READINESS_DESIGN.md) | V3.5 config, auth, CORS, Docker, GCP design |
| [docs/GCP_DEPLOYMENT_PLAN.md](GCP_DEPLOYMENT_PLAN.md) | Cloud Run deployment plan |
| docs/GOOGLE_ADS_INTEGRATION_PLAN.md | Live integration runbook *(created in V4.7)* |

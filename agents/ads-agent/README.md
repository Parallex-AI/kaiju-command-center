# Ads Agent

**V4.5.1 — Live Google Ads Fetch** — branch `v4.5.1-google-ads-live-fetch` · base tag `v4.0.0-beta`

> **Live Google Ads fetch is implemented** behind `GOOGLE_ADS_LIVE_ENABLED=true`. Default behavior (`n8n_demo`) is unchanged. Use `ADS_DATA_SOURCE=mock_fixture` for credential-free local development. For credentials setup and OAuth2 steps see [docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md](../../docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md). For V4 full scope see [docs/V4_BETA_RELEASE_NOTES.md](../../docs/V4_BETA_RELEASE_NOTES.md).

The Ads Agent is responsible for analyzing Google Ads performance data and generating actionable recommendations for clients.

## Responsibilities

- Ingest and interpret Google Ads metrics (spend, conversions, CPA, ROAS)
- Detect anomalies and performance trends
- Generate optimization recommendations
- Respond to client queries about campaign performance

## Inputs

- Campaign metrics from Google Ads (via n8n or direct API)
- Client memory context (from `memory/client-memory`)
- Router instructions

## Outputs

- Structured analysis report
- Optimization recommendations
- Natural language response to client

## Architecture Position

```
Router → Ads Agent → Response
```

## Local Demo

Runs against a local JSON fixture at `projects/demo-client/demo-data.json`. Does not require n8n.

```bash
cd ~/kaiju/agents/ads-agent
python3 run_demo.py
python3 chat_demo.py
```

## n8n Webhook Integration

The agent fetches live campaign data from an n8n workflow via HTTP webhook.

**Production webhook URL:**
```
https://flows.kaiju.digital/webhook/ads-agent-demo
```

**Environment variable override (optional):**
```bash
export N8N_ADS_WEBHOOK_URL=https://flows.kaiju.digital/webhook/ads-agent-demo
```

### Supported request types

| Type | Description |
|---|---|
| `summary` | Full campaign metrics and executive summary |
| `cpa` | Spend, conversions, and CPA only |
| `conversions` | Campaign name and conversion count only |
| `raw` | Raw JSON returned by n8n, formatted with indentation |

### curl examples

```bash
# summary
curl -X POST https://flows.kaiju.digital/webhook/ads-agent-demo \
  -H "Content-Type: application/json" \
  -d '{"client_id": "demo-client", "agent": "ads-agent", "request": "summary"}'

# cpa
curl -X POST https://flows.kaiju.digital/webhook/ads-agent-demo \
  -H "Content-Type: application/json" \
  -d '{"client_id": "demo-client", "agent": "ads-agent", "request": "cpa"}'

# conversions
curl -X POST https://flows.kaiju.digital/webhook/ads-agent-demo \
  -H "Content-Type: application/json" \
  -d '{"client_id": "demo-client", "agent": "ads-agent", "request": "conversions"}'

# raw
curl -X POST https://flows.kaiju.digital/webhook/ads-agent-demo \
  -H "Content-Type: application/json" \
  -d '{"client_id": "demo-client", "agent": "ads-agent", "request": "raw"}'
```

### Run the n8n report demo

```bash
cd ~/kaiju/agents/ads-agent
python3 run_n8n_demo.py              # defaults to summary
python3 run_n8n_demo.py summary
python3 run_n8n_demo.py cpa
python3 run_n8n_demo.py conversions
python3 run_n8n_demo.py raw
```

### Run the n8n chat demo (Spanish)

```bash
cd ~/kaiju/agents/ads-agent
python3 chat_n8n_demo.py
```

Available chat commands: `CPA`, `Conversiones`, `Resumen`, `¿Cómo viene la campaña?`, `Raw`, `JSON`, `salir`

> **Note:** The `/webhook-test/` URL is a temporary n8n test endpoint. The agent must always use `/webhook/ads-agent-demo` (production). Never use `/webhook-test/` in Python agent code.

## V1 LangGraph Graph Demo

The graph demo runs a multi-step LangGraph `StateGraph` through the Ads Agent pipeline: validate → fetch → normalize → analyze → recommend → format. It is isolated and does not affect the Router or any V0 path.

**Dependency install (into `.venv`):**
```bash
~/kaiju/.venv/bin/python3 -m pip install langgraph
```

Or install from the requirements file:
```bash
~/kaiju/.venv/bin/pip install -r ~/kaiju/agents/ads-agent/requirements.txt
```

**Run the graph demo:**
```bash
cd ~/kaiju/agents/ads-agent

~/kaiju/.venv/bin/python3 run_graph_demo.py              # defaults to summary
~/kaiju/.venv/bin/python3 run_graph_demo.py summary
~/kaiju/.venv/bin/python3 run_graph_demo.py cpa
~/kaiju/.venv/bin/python3 run_graph_demo.py conversions
~/kaiju/.venv/bin/python3 run_graph_demo.py raw
```

The graph response envelope includes `execution_mode: "graph"`, `metrics`, `analysis`, and `recommendations` for `summary`; focused subsets for `cpa` and `conversions`; and the raw n8n payload for `raw`.

> The legacy scripts `run_n8n_demo.py` and `chat_n8n_demo.py` are unchanged and continue to work independently of the graph.

## n8n Client Resilience

The n8n client (`n8n_client.py`) retries transient network failures automatically.

| Behavior | Detail |
|---|---|
| Attempts | 3 |
| Backoff | 1s after attempt 1, 2s after attempt 2 |
| Retries on | `Timeout`, `ConnectionError`, other request errors without an HTTP response |
| Does not retry | HTTP errors (4xx / 5xx) |
| Retry logging | Each non-final failure prints a timestamped line to stderr |

**Configurable timeout:**

```bash
# Default is 15 seconds. Override with:
export N8N_WEBHOOK_TIMEOUT=30

# Or inline:
N8N_WEBHOOK_TIMEOUT=30 python3 run_n8n_demo.py summary
```

If `N8N_WEBHOOK_TIMEOUT` is missing, invalid, zero, or negative, the client falls back to 15 seconds.

## V2 MemPalace Local Memory

MemPalace provides a local-first, file-based memory layer for client-scoped campaign context. V2.1 implements the utility module; V2.2 integrates it into the Ads Agent Graph.

### V2.1 — Memory utility module (`mempalace.py`)

Creates and manages `memory/client-memory/<client_id>/ads-agent/` with:
- `profile.json` — client metadata (read/write, atomic replacement)
- `snapshots/<timestamp>_<request_type>.json` — per-run analysis snapshots
- `latest_summary.json` — most recent summary for quick history loading
- `recommendations.jsonl` — append-only log with deterministic `recommendation_id`
- `insights.jsonl` — append-only trend/risk/opportunity log

Generated runtime memory is stored under `memory/client-memory/` and is **ignored by Git**.

### V2.2 — Graph integration (`ads_graph.py`)

The Ads Agent Graph now includes three memory nodes:

| Node | Position | Behavior |
|---|---|---|
| `load_client_memory` | Before n8n fetch | Loads profile, latest_summary, recent_snapshots into state |
| `compare_with_history` | After normalize, before analyze | Compares CPA and conversions vs. previous run |
| `write_memory` | After format_response | Writes snapshot, recommendations, insight; skips raw mode |

All non-raw graph responses include a `data.memory` block:
```json
{
  "enabled": true,
  "has_history": true,
  "historical_comparison": { "cpa_direction": "stable", ... },
  "write_result": { "ok": true, "results": { ... } },
  "warnings": []
}
```

**Raw requests** skip memory write and return `write_result.skipped: true`.  
**Memory failures** are non-fatal warnings — graph continues and returns `ok: true`.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `MEMORY_ENABLED` | `true` | Set to `false` to disable all memory reads/writes |
| `MEMORY_ROOT` | `memory/client-memory` (repo-relative) | Root directory for client memory |
| `MEMORY_MAX_RECENT_SNAPSHOTS` | `5` | Number of recent snapshots to load per run |

### Run the memory utility demo

```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_mempalace_demo.py demo-client

# With memory disabled (no crash, ok: true, enabled: false):
MEMORY_ENABLED=false ~/kaiju/.venv/bin/python3 run_mempalace_demo.py demo-client

# Custom memory root:
MEMORY_ROOT=/tmp/kaiju-memory ~/kaiju/.venv/bin/python3 run_mempalace_demo.py demo-client
```

## Status

V2 beta complete (branch: `v2-mempalace`). Memory utility module, graph integration, enriched historical comparison, and memory smoke test are implemented and tested. V2.5 retention controls are deferred.

### Run the V2 memory smoke test

```bash
cd ~/kaiju
./scripts/smoke_test_v2_memory.sh
```

---

## V4.2 Integration Resolver

V4.2 adds a data source resolver layer that decouples the Ads Agent from the n8n webhook. The graph is **not yet modified** — the resolver is standalone in V4.2 and will be wired into the graph in V4.3.

### ADS_DATA_SOURCE

| Value | Behavior |
|---|---|
| `n8n_demo` | Current n8n webhook path — **default** |
| `mock_fixture` | Local JSON fixture (`fixtures/google_ads_summary_fixture.json`) — no network, no credentials |
| `google_ads` | Real Google Ads API — **not implemented yet** (returns structured error) |

The default is `n8n_demo`. No behavior change unless `ADS_DATA_SOURCE` is explicitly set.

### Run the integration resolver demo

```bash
cd ~/kaiju/agents/ads-agent

# Default (n8n_demo)
~/kaiju/.venv/bin/python3 run_integration_demo.py summary

# Mock fixture — no network, no credentials
ADS_DATA_SOURCE=mock_fixture ~/kaiju/.venv/bin/python3 run_integration_demo.py summary
ADS_DATA_SOURCE=mock_fixture ~/kaiju/.venv/bin/python3 run_integration_demo.py cpa
ADS_DATA_SOURCE=mock_fixture ~/kaiju/.venv/bin/python3 run_integration_demo.py conversions
ADS_DATA_SOURCE=mock_fixture ~/kaiju/.venv/bin/python3 run_integration_demo.py raw

# Google Ads (not implemented — returns structured error, no crash)
ADS_DATA_SOURCE=google_ads ~/kaiju/.venv/bin/python3 run_integration_demo.py summary

# Invalid source — falls back to n8n_demo silently
ADS_DATA_SOURCE=bad ~/kaiju/.venv/bin/python3 run_integration_demo.py summary
```

### Integration package

```
agents/ads-agent/integrations/
  __init__.py               # re-exports resolve_ads_data, get_ads_data_source, normalize_metrics
  schemas.py                # VALID_DATA_SOURCES, get_ads_data_source(), normalize_metrics(), make_integration_error()
  resolver.py               # resolve_ads_data(client_id, request_type) — routes by ADS_DATA_SOURCE
  mock_fixture_adapter.py   # load_mock_fixture() — loads fixtures/google_ads_summary_fixture.json

agents/ads-agent/fixtures/
  google_ads_summary_fixture.json   # realistic sample metrics, no secrets
```

---

## V4.4 Google Ads Adapter Skeleton

V4.4 adds a Google Ads adapter with credential loading and validation. No live API calls are made. `GOOGLE_ADS_LIVE_ENABLED` defaults to `false`.

### Error progression

| Condition | Error code |
|---|---|
| `GOOGLE_ADS_LIVE_ENABLED=false` (default) | `google_ads_live_disabled` |
| Live enabled, credentials missing | `credentials_missing` (lists missing field *names*, never values) |
| Live enabled, credentials present | `google_ads_live_not_implemented` (V4.5 will add real fetch) |

### Google Ads environment variables

| Variable | Default | Secret |
|---|---|---|
| `ADS_DATA_SOURCE` | `n8n_demo` | No |
| `GOOGLE_ADS_LIVE_ENABLED` | `false` | No |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | `` | **Yes** |
| `GOOGLE_ADS_CLIENT_ID` | `` | **Yes** |
| `GOOGLE_ADS_CLIENT_SECRET` | `` | **Yes** |
| `GOOGLE_ADS_REFRESH_TOKEN` | `` | **Yes** |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | `` | No |
| `GOOGLE_ADS_CUSTOMER_ID` | `` | No |

Never commit credential values. Use `.env` locally (gitignored). In production, source from GCP Secret Manager.

**Full credential setup, OAuth2 refresh token acquisition, GAQL query, and manual test steps:**
→ [docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md](../../docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md)

### Run the adapter demo

```bash
cd ~/kaiju/agents/ads-agent

# Default — live disabled
~/kaiju/.venv/bin/python3 run_google_ads_adapter_demo.py

# Live enabled, credentials missing
GOOGLE_ADS_LIVE_ENABLED=true ADS_DATA_SOURCE=google_ads \
  ~/kaiju/.venv/bin/python3 run_integration_demo.py summary

# Live enabled, fake credentials — returns google_ads_live_not_implemented
GOOGLE_ADS_LIVE_ENABLED=true \
  GOOGLE_ADS_DEVELOPER_TOKEN=... \
  GOOGLE_ADS_CLIENT_ID=... \
  GOOGLE_ADS_CLIENT_SECRET=... \
  GOOGLE_ADS_REFRESH_TOKEN=... \
  GOOGLE_ADS_CUSTOMER_ID=... \
  ADS_DATA_SOURCE=google_ads \
  ~/kaiju/.venv/bin/python3 run_integration_demo.py summary
```

The demo **never prints secret values** — only `{"configured": true/false}` per field.

---

## V4.3 Graph Integration

As of V4.3, the Ads Agent Graph uses the integration resolver as its data fetch layer. The `fetch_metrics_from_n8n` node has been replaced by `fetch_metrics`, which calls `resolve_ads_data()` to select the correct adapter based on `ADS_DATA_SOURCE`.

The default remains `n8n_demo` — **no behavior change for existing callers**.

### Graph data source behavior

| `ADS_DATA_SOURCE` | Graph behavior |
|---|---|
| `n8n_demo` (default) | Fetches from n8n webhook; analysis/recommendations/memory unchanged |
| `mock_fixture` | Loads fixture JSON; full analysis and recommendations generated from fixture metrics |
| `google_ads` | Returns controlled `ok=false` with `google_ads_not_implemented` error; no traceback |

### `data_source` in graph response

All graph responses now include `data_source` at the top level:

```json
{
  "ok": true,
  "agent": "ads-agent",
  "execution_mode": "graph",
  "data_source": "n8n_demo",
  "data": { ... }
}
```

This field is additive — existing response fields are unchanged.

### Run the graph with mock fixture

```bash
cd ~/kaiju/agents/ads-agent

# Full analysis from fixture data (spend 150000, conversions 75, cpa 2000)
ADS_DATA_SOURCE=mock_fixture ~/kaiju/.venv/bin/python3 run_graph_demo.py summary
ADS_DATA_SOURCE=mock_fixture ~/kaiju/.venv/bin/python3 run_graph_demo.py cpa
ADS_DATA_SOURCE=mock_fixture ~/kaiju/.venv/bin/python3 run_graph_demo.py conversions
ADS_DATA_SOURCE=mock_fixture ~/kaiju/.venv/bin/python3 run_graph_demo.py raw
```

### Run the graph with google_ads (not implemented)

```bash
ADS_DATA_SOURCE=google_ads ~/kaiju/.venv/bin/python3 run_graph_demo.py summary
# Returns: ok=false, errors: [google_ads_not_implemented] ...
```

### Canonical metrics schema

All adapters return a normalized dict:

```json
{
  "source": "mock_fixture",
  "client": "demo-client",
  "campaign": "...",
  "date_range": { "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" },
  "currency": "ARS",
  "spend": 150000.0,
  "conversions": 75,
  "clicks": 4200,
  "impressions": 95000,
  "ctr": 0.0442,
  "cpc": 35.71,
  "cpa": 2000.0,
  "conversion_rate": 0.0179,
  "raw_source": "mock_fixture"
}
```

Derived metrics (`ctr`, `cpc`, `cpa`, `conversion_rate`) are computed from base fields; `null` when base values are zero.

---

## V5 Credential Chain Smoke Test

`scripts/smoke_test_v5_credentials.sh` — 8-section end-to-end test covering the full V5 credential stack. No real credentials required, no live API calls.

| Section | Coverage |
|---|---|
| `[1/8]` | Import checks: all 7 credential modules + `openclaw.admin` |
| `[2/8]` | `CredentialReference` model demo (all assertions) |
| `[3/8]` | `CredentialStore` + `LocalFileCredentialReferenceStore` demos |
| `[4/8]` | Credential resolver demo |
| `[5/8]` | `SecretStore` + Google Ads provider demos |
| `[6/8]` | Adapter provider mode: non-live checks, feature flag branching, in-memory compose |
| `[7/8]` | OpenClaw admin endpoints: POST/GET/forbidden/malformed/auth-disabled/auth-enabled |
| `[8/8]` | Secret-safety grep + git hygiene |

```bash
cd ~/kaiju
./scripts/smoke_test_v5_credentials.sh
```

---

## V4.6 Integration Resolver Smoke Test

`scripts/smoke_test_v4_integrations.sh` — 37 assertions across 6 sections. No live network, no credentials required.

| Section | Coverage |
|---|---|
| Environment | Imports for all integration modules |
| `ADS_DATA_SOURCE` resolution | Valid values, invalid fallback, whitespace/case |
| Canonical metrics normalization | Derived fields, empty payload, client/campaign, error schema |
| Mock fixture adapter | ok flag, data_source, source, client override, base and derived metrics |
| Google Ads safety gates | Three-tier error progression, credential redaction (4 secret values) |
| Graph integration | All four request types with mock_fixture; performance_score, executive_summary, cpa_level |

```bash
cd ~/kaiju
./scripts/smoke_test_v4_integrations.sh
```

> **V4.5.1 note:** The smoke test assertion on line 304 (`google_ads_live_not_implemented`) was written for the V4.4 placeholder. After V4.5.1, fake credentials return `google_ads_api_error` (the library attempts OAuth). This assertion must be updated before the test fully passes (36/37 pass as-is).

---

## V4.5.1 Live Google Ads Fetch

Live read-only Google Ads API fetch is implemented in `integrations/google_ads_adapter.py` behind `GOOGLE_ADS_LIVE_ENABLED=true`.

**Dependency:** `google-ads>=23.1.0` — install via:
```bash
~/kaiju/.venv/bin/pip install -r ~/kaiju/agents/ads-agent/requirements.txt
```

**GAQL query:** LAST_30_DAYS campaign-level metrics (impressions, clicks, cost_micros, conversions) aggregated across up to 20 enabled campaigns.

**Error behavior:**

| Condition | Error code |
|---|---|
| `GOOGLE_ADS_LIVE_ENABLED=false` (default) | `google_ads_live_disabled` |
| Credentials missing | `credentials_missing` |
| `google-ads` library not installed | `google_ads_dependency_missing` |
| API auth / network error | `google_ads_api_error` |
| No campaign rows returned | `no_data` |
| Request timeout | `integration_timeout` |

**Currency:** Controlled by `GOOGLE_ADS_CURRENCY` env var (default `ARS`).

**Run the adapter demo (live disabled — safe default):**
```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_google_ads_adapter_demo.py
```

**Manual live test (requires real credentials):**
```bash
cd ~/kaiju/agents/ads-agent
ADS_DATA_SOURCE=google_ads \
GOOGLE_ADS_LIVE_ENABLED=true \
~/kaiju/.venv/bin/python3 run_integration_demo.py summary
```

See [docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md](../../docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md) for credential setup, OAuth2 steps, and secret safety rules.

---

## V5.2 Credential Reference Model

V5.2 introduces the `credentials/` package — a metadata-only model for tenant/client credential references. No secret values are stored, returned, or passed through this layer.

### Package location

```
agents/ads-agent/credentials/
  __init__.py    — public re-exports
  models.py      — dataclass, enums, helpers
```

### CredentialStatus values

| Status | Meaning |
|---|---|
| `missing` | No credentials configured yet |
| `configured` | Credentials stored, not yet validated |
| `invalid` | Credentials stored but failed shape or API validation |
| `validation_failed` | Live API validation returned an error |
| `active` | Credentials validated and working |
| `revoked` | Credentials explicitly revoked |

`configured: true` is returned when status is `configured` or `active`.

### CredentialReference fields

| Field | Type | Secret | Notes |
|---|---|---|---|
| `tenant_id` | str | No | Sanitized on creation |
| `client_id` | str | No | Sanitized on creation |
| `integration_type` | str | No | Must be a valid `IntegrationType` value |
| `credential_ref` | str | No | Opaque pointer to secret backend (SHA-256 prefix) |
| `customer_id` | str or None | No | Google Ads account ID |
| `login_customer_id` | str or None | No | MCC manager account ID |
| `status` | str | No | One of `CredentialStatus` values |
| `last_validated_at` | str or None | No | UTC ISO timestamp |
| `created_at` | str or None | No | UTC ISO timestamp |
| `updated_at` | str or None | No | UTC ISO timestamp |
| `metadata` | dict or None | No | Safe keys only — secret-like keys filtered |

The dataclass never contains `developer_token`, `client_secret`, `refresh_token`, `access_token`, or OAuth codes.

### Metadata filtering

`filter_safe_metadata()` drops any metadata key whose name (case-insensitive) contains:
`token`, `secret`, `password`, `credential`, `authorization`, `auth_header`, `oauth_code`, `refresh`, `access`

### Redacted response

`credential_reference_to_redacted_response()` returns an API-safe dict including `configured: bool`. This shape is safe to return from any endpoint — no secret values are present.

### Run the credentials model demo

```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_credentials_model_demo.py
```

The demo creates a `CredentialReference`, shows metadata filtering, prints full dict and redacted response, runs validation checks, and asserts no secret values appear in any output. All assertions pass without network access or real credentials.

---

## V5.3 CredentialStore Abstraction

V5.3 adds the `CredentialStore` interface and `InMemoryCredentialStore` — a reference-only in-memory credential metadata store for development and testing. No secret material is stored anywhere.

### Package location

```
agents/ads-agent/credentials/
  store.py    — CredentialStore ABC, InMemoryCredentialStore, helpers
```

### What is stored

`CredentialStore` stores `CredentialReference` metadata only. Secret values (developer tokens, client secrets, refresh tokens, OAuth codes) are never accepted, stored, or returned.

### What is rejected

`put_reference` raises `ValueError` if:
- The `CredentialReference` fails `validate_credential_reference` (missing fields, invalid status, unknown integration type)
- The `metadata` dict contains any key whose name includes: `token`, `secret`, `password`, `authorization`, `oauth_code`, `refresh`, or `access`

### `get_status` behavior

| State | `status` | `configured` | `credential_ref` |
|---|---|---|---|
| Reference in store, `status=missing` | `missing` | `false` | present |
| Reference in store, `status=configured` or `active` | value | `true` | present |
| Reference not in store | `missing` | `false` | `null` |

### Helpers

| Helper | Purpose |
|---|---|
| `make_store_key(tenant_id, client_id, integration_type)` | Deterministic composite key (`tenant/client/type`) |
| `missing_credential_status(tenant_id, client_id, integration_type)` | Redacted status shape when no credential is configured |
| `assert_no_secret_material(payload)` | Recursively scans dict keys for secret-like names; returns `(True, [])` or `(False, [offending paths])` |

### Run the credentials store demo

```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_credentials_store_demo.py
```

The demo covers 15 sections: put/get/update/list/delete, missing status after delete, secret-metadata rejection, `assert_no_secret_material` with nested detection, and unit-style checks for all operations. All assertions pass without network access or real credentials.

---

## V5.4 LocalFileCredentialReferenceStore

V5.4 adds `LocalFileCredentialReferenceStore` — a file-backed implementation of `CredentialStore` that persists credential reference metadata to a local JSON file.

> **This is not a secret store.** Secret values (developer tokens, client secrets, refresh tokens, OAuth codes) are never written to this file. This stores reference metadata only. The secret store (GCP Secret Manager) is a separate V5.9 concern.

### Package location

```
agents/ads-agent/credentials/
  local_file_store.py    — LocalFileCredentialReferenceStore, helpers
```

### Store file location

Controlled by `CREDENTIAL_REFERENCE_STORE_PATH` environment variable.

| Setting | Path used |
|---|---|
| `CREDENTIAL_REFERENCE_STORE_PATH` set | Value of env var |
| Not set (default) | `runtime/credential-references/credential_references.json` (repo-root relative) |

The default path is ignored by Git (`runtime/credential-references/` in `.gitignore`).

### JSON file shape

```json
{
  "version": 1,
  "references": {
    "tenant-id/client-id/google_ads": {
      "tenant_id": "...",
      "client_id": "...",
      "integration_type": "google_ads",
      "credential_ref": "cred_google_ads_...",
      "customer_id": "...",
      "status": "...",
      "created_at": "...",
      "updated_at": "...",
      "metadata": {}
    }
  }
}
```

No secret fields appear in this file. The `credential_ref` value is an opaque hash-based pointer, not a raw secret value.

### Helpers

| Helper | Purpose |
|---|---|
| `get_default_credential_reference_store_path()` | Reads env var or returns repo-root default |
| `load_reference_store_file(path)` | Loads JSON; missing file → empty store; invalid JSON → `ValueError` |
| `write_reference_store_file(payload, path)` | Atomic write via tempfile + `os.replace`; creates parent dir |
| `dict_to_credential_reference(payload)` | Deserializes stored dict to validated `CredentialReference`; rejects unsafe metadata |

### Atomic writes

All mutations use `tempfile.mkstemp` + `os.replace` — the store file is never in a partial-write state even if the process crashes mid-write.

### Run the local file store demo

```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_credentials_local_file_store_demo.py
```

The demo uses `/tmp/kaiju-credential-reference-store-demo.json` as a safe temp path. It covers 14 sections: file creation, put/get/update/list/delete, JSON structure verification (no secret-like keys), unsafe-metadata rejection, unit-style checks including invalid-JSON error handling, env-var path override, and cleanup. All assertions pass without network access or real credentials. The temp file is removed at the end.

---

## V5.7 Credential Resolver Bridge

V5.7 adds `credentials/resolver.py` — a bridge that resolves safe `CredentialReference` metadata from a `CredentialStore` by tenant/client/integration.

> **This is not a secret resolver.** No developer tokens, client secrets, refresh tokens, access tokens, or OAuth codes are read, returned, or inspected. The resolver returns metadata only: `tenant_id`, `client_id`, `integration_type`, `status`, `configured`, `customer_id`, `login_customer_id`, and the opaque `credential_ref` pointer.

### Package location

```
agents/ads-agent/credentials/
  resolver.py    — ResolvedCredentialReference, resolve_credential_reference, helpers
```

### ResolvedCredentialReference

```python
@dataclass
class ResolvedCredentialReference:
    ok: bool
    tenant_id: str
    client_id: str
    integration_type: str
    credential_ref: Optional[str] = None
    status: Optional[str] = None
    configured: bool = False
    customer_id: Optional[str] = None
    login_customer_id: Optional[str] = None
    metadata: Optional[dict] = None
    errors: Optional[list[dict]] = None
```

No secret fields. `credential_ref` is an opaque hash-based pointer, not a raw secret value.

### resolve_credential_reference

```python
from credentials.resolver import resolve_credential_reference

result = resolve_credential_reference(
    tenant_id="acme",
    client_id="c1",
    integration_type="google_ads",   # default
    store=None,                      # default: LocalFileCredentialReferenceStore()
)

if result.ok:
    print(result.customer_id)   # e.g. "111-222-3333"
    print(result.configured)    # True when status is "configured" or "active"
else:
    print(result.errors[0]["code"])  # e.g. "credentials_missing"
```

### Resolution outcomes

| Condition | `ok` | `status` | `errors[0].code` |
|---|---|---|---|
| No reference stored | `false` | `missing` | `credentials_missing` |
| Reference found, valid | `true` | stored status | — |
| Reference found, invalid | `false` | — | `credential_reference_invalid` |
| Store unavailable | `false` | — | `credential_store_unavailable` |

### Helpers

| Helper | Purpose |
|---|---|
| `make_resolver_error(code, message, recoverable)` | Safe error dict with `source: credential_resolver` |
| `resolved_credential_reference_to_dict(resolved)` | Convert to safe JSON-serializable dict |
| `assert_resolved_reference_has_no_secret_material(payload)` | Recursive key-name scanner, same forbidden substrings as store layer |

### Future adapter integration (V5.7+ continuation)

The Google Ads adapter (`integrations/google_ads_adapter.py`) currently reads credentials from `os.getenv()`. The resolver bridge is the first step toward wiring the adapter to read `customer_id` and `login_customer_id` from the `CredentialReference` store. Secret resolution (developer token, client secret, refresh token) requires a `SecretStore` implementation (V5.9, GCP Secret Manager) and is not handled here.

### Run the resolver demo

```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_credentials_resolver_demo.py
```

The demo uses a temp file under `/tmp`. It covers 9 sections: missing reference, configured reference, active reference, multi-tenant isolation, dict shape check, secret-material scanner (clean and dirty cases), `make_resolver_error` shape, default-store resolution, and secret-safety assertion on all outputs. The temp file is removed at the end.

---

## V5.8 SecretStore Abstraction

V5.8 adds `credentials/secret_store.py` — the abstract contract and in-memory implementation for storing and retrieving secret bundles (developer_token, client_id, client_secret, refresh_token).

> **In-memory only, dev/test only.** `InMemorySecretStore` does not write to disk. Secrets are lost on process restart. Production storage (GCP Secret Manager) is deferred to V5.9. The adapter is not yet wired to use this store — that integration is deferred.

### What belongs here vs CredentialReference

| Field | Where it lives |
|---|---|
| `developer_token` | SecretStore (secret) |
| `client_id` | SecretStore (secret) |
| `client_secret` | SecretStore (secret) |
| `refresh_token` | SecretStore (secret) |
| `customer_id` | CredentialReference (metadata) |
| `login_customer_id` | CredentialReference (metadata) |

### Package location

```
agents/ads-agent/credentials/
  secret_store.py    — SecretRecord, SecretStore, InMemorySecretStore, helpers
```

### SecretRecord — redacted, no values

```python
@dataclass
class SecretRecord:
    credential_ref: str
    integration_type: str
    configured_fields: list[str]   # field names only, no values
    created_at: Optional[str]
    updated_at: Optional[str]
    metadata: Optional[dict]
```

`configured_fields` is a list of which field names have been stored. Values are never exposed.

### InMemorySecretStore usage

```python
from credentials.secret_store import InMemorySecretStore

store = InMemorySecretStore()

# Store bundle (values stay inside the store)
record = store.put_secret_bundle(
    credential_ref="cred_google_ads_abc123",
    integration_type="google_ads",
    secrets={
        "developer_token": "...",
        "client_id": "...",
        "client_secret": "...",
        "refresh_token": "...",
    },
)

# Safe for logging or API responses
status = store.get_secret_status("cred_google_ads_abc123", "google_ads")
# {"configured": true, "configured_fields": {"developer_token": true, ...}}

# Internal adapter use only — never log or return this
bundle = store.get_secret_bundle("cred_google_ads_abc123", "google_ads")
```

### Forbidden fields

`access_token`, `oauth_code`, `password`, `authorization`, `auth_header`, and any field not in the integration's allowed list are rejected by `put_secret_bundle`. Empty values are also rejected.

### Helpers

| Helper | Purpose |
|---|---|
| `GOOGLE_ADS_SECRET_FIELDS` | Tuple of 4 allowed secret field names |
| `make_secret_store_key(ref, type)` | `"credential_ref/integration_type"` composite key |
| `assert_allowed_secret_fields(secrets, type)` | Validate fields against allowed set |
| `redact_secret_status(ref, type, configured_fields, metadata)` | Safe status dict for logging/API |
| `assert_no_secret_values_in_payload(payload)` | Recursive value scanner for demo/test output safety |

### Run the secret store demo

```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_secret_store_demo.py
```

The demo uses `InMemorySecretStore` (no disk writes). It covers 14 sections: unconfigured status, put full bundle, configured status, internal retrieval (values asserted but not printed), list records, delete, post-delete status, forbidden field rejection (6 variants), empty value rejection, `assert_allowed_secret_fields` standalone, `redact_secret_status` with partial bundle, `make_secret_store_key`, and value-safety assertion on all printed outputs. All assertions pass without network access or real credentials.

---

## V5.9 Google Ads CredentialProvider

V5.9 adds `credentials/google_ads_provider.py` — the composition layer that combines a `CredentialReference` (metadata) and a `SecretStore` bundle (secrets) into a `GoogleAdsCredentials` object for adapter use.

> **Not wired into the live adapter yet.** The existing `fetch_google_ads_metrics()` path in `google_ads_adapter.py` continues to use `load_google_ads_credentials()` (env-var loading). The provider layer is a standalone bridge, ready for future wiring.

### What it composes

| Source | Fields |
|---|---|
| `CredentialReference` (metadata store) | `customer_id`, `login_customer_id` |
| `SecretStore` bundle | `developer_token`, `client_id`, `client_secret`, `refresh_token` |
| → `GoogleAdsCredentials` | all 6 fields |

### Package location

```
agents/ads-agent/credentials/
  google_ads_provider.py    — GoogleAdsCredentialProviderResult, compose_google_ads_credentials, helpers
```

### Usage

```python
from credentials.google_ads_provider import (
    compose_google_ads_credentials,
    google_ads_provider_result_to_redacted_dict,
)
from credentials.secret_store import InMemorySecretStore

secret_store = InMemorySecretStore()
secret_store.put_secret_bundle(
    credential_ref="cred_google_ads_abc123",
    integration_type="google_ads",
    secrets={
        "developer_token": "...",
        "client_id": "...",
        "client_secret": "...",
        "refresh_token": "...",
    },
)

result = compose_google_ads_credentials(
    tenant_id="acme",
    client_id="c1",
    secret_store=secret_store,
)

if result.ok:
    # Internal use only — never log or return result.credentials
    creds = result.credentials
else:
    print(result.errors[0]["code"])

# Safe for logging or API responses
print(google_ads_provider_result_to_redacted_dict(result))
```

### Composition outcomes

| Condition | `ok` | `errors[0].code` |
|---|---|---|
| No credential reference | `false` | `credentials_missing` |
| Reference not configured/active | `false` | `credential_reference_not_configured` |
| No secret bundle | `false` | `secret_bundle_missing` |
| Bundle missing required fields | `false` | `secret_bundle_incomplete` |
| Both present and valid | `true` | — |

### Redacted output shape

```json
{
  "ok": true,
  "tenant_id": "acme",
  "client_id": "c1",
  "credential_ref": "cred_google_ads_...",
  "source": "credential_provider",
  "credentials_configured": true,
  "configured_fields": {
    "developer_token": true,
    "client_id": true,
    "client_secret": true,
    "refresh_token": true,
    "customer_id": true,
    "login_customer_id": true
  },
  "metadata": null,
  "errors": []
}
```

Actual credential values are never included. `credentials_configured` and `configured_fields` show only presence (True/False).

### Run the provider demo

```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_google_ads_provider_demo.py
```

The demo uses a temp `LocalFileCredentialReferenceStore` path and `InMemorySecretStore`. It covers 11 sections: missing reference, unconfigured reference (revoked), missing bundle, successful composition, internal credentials check (values not printed), `configured_fields` correctness, active reference, error shape, `repr` safety, output safety assertion on all printed outputs, and dirty payload detection. No credentials are stored on disk or printed. All assertions pass without network access or real credentials.

---

## V5.10 Google Ads Adapter — Credential Source Flag

V5.10 wires the CredentialProvider into `fetch_google_ads_metrics()` behind the `GOOGLE_ADS_CREDENTIAL_SOURCE` feature flag.

### Feature flag

| `GOOGLE_ADS_CREDENTIAL_SOURCE` | Behaviour |
|---|---|
| `env` (default) | Load credentials from environment variables — existing path, unchanged |
| `provider` | Load via `compose_google_ads_credentials()`; requires `tenant_id` at call time |
| any other value | Falls back to `env` |

The flag defaults to `env`. Existing callers (the integration resolver, demo scripts) pass only `(client_id, request_type)` and are unaffected.

### Updated signature

```python
fetch_google_ads_metrics(
    client_id: str,
    request_type: str,
    tenant_id: Optional[str] = None,   # required when GOOGLE_ADS_CREDENTIAL_SOURCE=provider
    secret_store=None,                  # optional; uses in-memory store if None
) -> dict
```

### New error codes

| Code | Trigger |
|---|---|
| `tenant_id_required` | `provider` mode with no `tenant_id` supplied |
| `credential_provider_failed` | Provider returned `ok=False` |
| `credential_provider_unavailable` | Provider module import failed |
| `unsupported_credential_source` | Flag resolved to an unsupported value |

### Run the provider adapter demo

```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_google_ads_adapter_provider_demo.py
```

The demo covers 6 sections without making any live Google Ads API calls: credential source flag resolution, live-disabled guard, missing `tenant_id` error, no-store provider failure, in-memory store with valid credential loading, and backward-compatible 2-arg call. All existing demos continue to run unchanged.

---

## V5.12.2 GCP Secret Manager Store Scaffold

V5.12.2 adds `credentials/gcp_secret_manager_store.py` — the scaffold for the production GCP Secret Manager backend. The dependency `google-cloud-secret-manager>=2.20.0` is added to `requirements.txt`.

> **No live GCP calls are made in V5.12.2.** Disabled mode is fully functional. Enabled mode stubs raise `NotImplementedError` — live read/write is implemented in V5.12.3.

### New env vars

| Variable | Default | Purpose |
|---|---|---|
| `GCP_SECRET_MANAGER_ENABLED` | `false` | Gate for all live GCP calls — `false` by default |
| `GCP_PROJECT_ID` | `` | GCP project; fallback: `GOOGLE_CLOUD_PROJECT` |
| `GCP_SECRET_MANAGER_PREFIX` | `kaiju` | Secret name prefix segment |
| `GCP_SECRET_MANAGER_ENV` | `local` | Env segment: `local`, `dev`, `staging`, `prod` |

### Secret naming

```
{prefix}-{env}-{integration_type}-{credential_ref}
e.g. kaiju-prod-google_ads-cred_google_ads_abcd1234ef56
```

### Disabled mode behavior (default)

| Method | Returns |
|---|---|
| `put_secret_bundle(...)` | Raises `RuntimeError("GCP Secret Manager is disabled")` |
| `get_secret_bundle(...)` | `None` |
| `get_secret_status(...)` | Redacted unconfigured shape with `backend_status: "disabled"` |
| `delete_secret_bundle(...)` | `False` |
| `list_secret_records(...)` | `[]` |

### Run the scaffold demo (no GCP credentials required)

```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_gcp_secret_manager_store_demo.py
```

The demo covers 9 sections: env helpers, edge cases, secret ID builder, status dict, lazy import guard, disabled mode (all 5 methods), default-env construction, field validation order, and secret-safety assertion. No GCP credentials required. All assertions pass.

---

## V5.12.3 GCP Secret Manager Read/Status Behavior

V5.12.3 implements `get_secret_bundle()` and `get_secret_status()` with live GCP reads behind an injected mock client. `put_secret_bundle`, `delete_secret_bundle`, and `list_secret_records` remain deferred.

### New functions

| Function | Purpose |
|---|---|
| `build_gcp_secret_version_resource_name(project_id, secret_id, version="latest")` | Version resource name: `projects/{p}/secrets/{s}/versions/{v}` |
| `parse_gcp_secret_payload(payload_bytes, integration_type)` | Decode bytes, JSON parse, validate allowed fields, reject empty values |

### get_secret_bundle behavior

| Condition | Returns |
|---|---|
| `enabled=False` | `None` |
| Init errors (missing project, dependency unavailable) | `None` |
| Valid bundle from GCP | secret dict (internal use only — never print or log) |
| GCP NotFound / PermissionDenied / parse error | `None` |

### get_secret_status behavior

| Condition | `configured` | `metadata.error_code` |
|---|---|---|
| Disabled | `false` | — (`backend_status: disabled`) |
| Init error | `false` | — (`backend_status: init_error`) |
| Bundle retrieved | `true` | — (`available: true`) |
| GCP NotFound | `false` | `gcp_secret_not_found` |
| Invalid JSON | `false` | `gcp_secret_payload_invalid` |
| Forbidden field | `false` | `gcp_secret_payload_invalid` |
| Permission denied | `false` | `gcp_secret_access_denied` |

### Mock client testing

No real GCP credentials are required. Inject a mock via the `client=` constructor parameter:

```python
from credentials.gcp_secret_manager_store import GCPSecretManagerStore

store = GCPSecretManagerStore(
    enabled=True,
    project_id="my-project",
    client=MyMockClient(),
)
status = store.get_secret_status("cred_google_ads_abc123", "google_ads")
# {"configured": True/False, "metadata": {"backend": "gcp_secret_manager", ...}}
```

### Run the mock read demo (no GCP credentials required)

```bash
cd ~/kaiju/agents/ads-agent
~/kaiju/.venv/bin/python3 run_gcp_secret_manager_read_mock_demo.py
```

The demo covers 8 sections: `parse_gcp_secret_payload` valid input, rejection cases, `build_gcp_secret_version_resource_name`, valid mock client (configured=true), NotFound mock (gcp_secret_not_found), invalid JSON mock (gcp_secret_payload_invalid), forbidden field mock, and missing project_id init error. All 5 printed status dicts are asserted free of secret markers.

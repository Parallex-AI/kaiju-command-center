# Ads Agent

**V4 beta — Real Integrations Foundation** — branch `v4-real-integrations` · tag pending `v4.0.0-beta`

> **Note:** Live Google Ads API fetch is **not yet implemented**. `ADS_DATA_SOURCE=google_ads` returns a structured `google_ads_live_not_implemented` error. Use `ADS_DATA_SOURCE=mock_fixture` for local development without network access. See [docs/V4_BETA_RELEASE_NOTES.md](../../docs/V4_BETA_RELEASE_NOTES.md) for full release scope and [docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md](../../docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md) for the live integration plan.

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

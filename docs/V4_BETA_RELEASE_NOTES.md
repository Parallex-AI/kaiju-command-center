# Kaiju Command Center V4 beta — Real Integrations Foundation

**Branch:** `v4-real-integrations`
**Tag pending:** `v4.0.0-beta`
**Status:** Beta-ready — not yet merged or tagged
**Date:** 2026-05-30
**Design document:** [docs/V4_REAL_INTEGRATIONS_DESIGN.md](V4_REAL_INTEGRATIONS_DESIGN.md)
**Runbook:** [docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md](GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md)

---

## Summary

V4 introduces the data integration architecture required to move from demo-only campaign metrics toward real Google Ads data. All new code paths are additive and feature-flagged. The existing `n8n_demo` default path is unchanged — no behavior change for current callers.

The core addition is a resolver layer (`ADS_DATA_SOURCE`) that decouples the Ads Agent Graph from any specific data source. The graph now routes through the resolver; adapters implement a common response contract. V4 beta ships the resolver, mock fixture adapter, and Google Ads adapter skeleton — with full credential validation and safety gates, but no live API calls.

---

## What is included

### Integration resolver (`ADS_DATA_SOURCE`)

- `integrations/resolver.py` — `resolve_ads_data(client_id, request_type)` routes by `ADS_DATA_SOURCE` env var
- `integrations/schemas.py` — `get_ads_data_source()`, `normalize_metrics()`, `make_integration_error()`
- `integrations/__init__.py` — re-exports public API

### `n8n_demo` path (default)

- Existing n8n webhook client (`n8n_client.py`) wrapped as an adapter
- Zero behavior change when `ADS_DATA_SOURCE` is unset
- All V0–V3 smoke suites continue to pass

### `mock_fixture` path

- `integrations/mock_fixture_adapter.py` — loads `fixtures/google_ads_summary_fixture.json`
- No network, no credentials required
- Full analysis, recommendations, and executive summary generated from fixture metrics
- Safe for CI and local development with no external dependencies

### Canonical metrics normalization

- Shared `normalize_metrics()` derives `ctr`, `cpc`, `cpa`, `conversion_rate` from base fields
- Common response shape used by all adapters
- `null` for derived fields when base values are zero

### Ads Graph wired to resolver

- `ads_graph.py` `fetch_metrics` node calls `resolve_ads_data()` instead of `fetch_ads_data_from_n8n()` directly
- `data_source` field added additively to `AdsAgentState` and all graph responses
- Existing n8n response shape preserved for `n8n_demo` mode — no downstream changes

### Google Ads adapter skeleton

- `integrations/google_ads_adapter.py` — standard library only, no `google-ads` package
- `GoogleAdsCredentials` dataclass: 6 fields
- `load_google_ads_credentials()` — reads env vars; empty values become `None`
- `validate_google_ads_credentials()` — checks 5 required fields; lists missing field *names*, never values
- `redacted_google_ads_credentials()` — returns `{"field": {"configured": bool}}` for all 6 fields; values never exposed
- `run_google_ads_adapter_demo.py` — prints redacted credential status and fetch result; no secret values in output

### `GOOGLE_ADS_LIVE_ENABLED` safety gate

Three-tier error progression when `ADS_DATA_SOURCE=google_ads`:

| Condition | Error code | Recoverable |
|---|---|---|
| `GOOGLE_ADS_LIVE_ENABLED=false` (default) | `google_ads_live_disabled` | Yes |
| Live enabled, credentials missing | `credentials_missing` | Yes |
| Live enabled, credentials present | `google_ads_live_not_implemented` | Yes |

No live API call is made at any tier. No credential values appear in any error response or log output.

### Google Ads live integration runbook

- `docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md` — full pre-implementation preparation
- Required credentials and field-level descriptions
- OAuth2 refresh token acquisition (3 options: OAuth Playground, custom script, existing Cloud project)
- Local `.env` setup and secret safety rules
- Proposed V4.5.1 implementation approach (not yet implemented)
- Initial GAQL query for last-30-days campaign metrics
- Manual live test commands (for use after V4.5.1)
- Expected success response shape
- All normalized error codes
- Testing policy: no live credentials in CI
- Production implications: Secret Manager, per-tenant credential mapping, rate limiting

### V4 integration smoke test

- `scripts/smoke_test_v4_integrations.sh` — 37 assertions, 6 sections
- No live network, no credentials required
- Covers: imports, resolver resolution, normalization, mock fixture, Google Ads safety gates, credential redaction, graph integration with all four request types

---

## What is not included

| Item | Notes |
|---|---|
| Live Google Ads API calls | `GOOGLE_ADS_LIVE_ENABLED` defaults `false`; fetch not implemented |
| `google-ads` Python library | Not added to `requirements.txt`; V4.5.1 deferred |
| Campaign mutations (create/update/pause) | Read-only design only |
| OAuth2 UI / web flow | Refresh token acquired manually per runbook |
| Tenant credential database | Per-tenant credential mapping is design-only |
| Real production credentials | No credentials committed; `.env` is gitignored |
| Billing or subscription model | Out of scope for V4 |
| Multi-region or Kubernetes deployment | V3.5 GCP plan covers single-region Cloud Run |

---

## Default behavior

`ADS_DATA_SOURCE` defaults to `n8n_demo`. No environment variable changes are required to preserve existing behavior. All V0–V3 tests pass with no new configuration.

---

## Supported data source modes

| `ADS_DATA_SOURCE` | Behavior |
|---|---|
| `n8n_demo` | Fetches from n8n webhook — **default**; no behavior change |
| `mock_fixture` | Local JSON fixture; no network; no credentials; full analysis |
| `google_ads` | Safety-gated adapter skeleton; returns structured error; no live calls |

Invalid values fall back silently to `n8n_demo`.

---

## New environment variables

| Variable | Default | Secret | Purpose |
|---|---|---|---|
| `ADS_DATA_SOURCE` | `n8n_demo` | No | Data source adapter selection |
| `GOOGLE_ADS_LIVE_ENABLED` | `false` | No | Gate for live Google Ads API calls |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | `` | **Yes** | Google Ads API developer token |
| `GOOGLE_ADS_CLIENT_ID` | `` | **Yes** | OAuth2 client ID |
| `GOOGLE_ADS_CLIENT_SECRET` | `` | **Yes** | OAuth2 client secret |
| `GOOGLE_ADS_REFRESH_TOKEN` | `` | **Yes** | OAuth2 refresh token |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | `` | No (tenant-sensitive) | MCC/manager account ID |
| `GOOGLE_ADS_CUSTOMER_ID` | `` | No (tenant-sensitive) | Target advertising account ID |

All credential vars default to empty. Secret vars must never be committed. In production, source from GCP Secret Manager.

---

## Test coverage

| Suite | Assertions | Result |
|---|---|---|
| V4 integration smoke test | 37 | Pass |
| V3 OpenClaw audit smoke test | — | Pass |
| V3 OpenClaw HTTP smoke test | — | Pass |
| V3 OpenClaw core smoke test | — | Pass |
| V2 MemPalace memory smoke test | 20 | Pass |
| V1 LangGraph graph smoke test | 33 | Pass |
| V0 legacy smoke test | 20 | Pass |

No smoke test requires live credentials or network access to external services beyond the n8n webhook (V0–V3 default path).

---

## Release risks

| Risk | Detail |
|---|---|
| Live Google Ads not implemented | `ADS_DATA_SOURCE=google_ads` always returns `google_ads_live_not_implemented` until V4.5.1 |
| n8n still required for default path | `n8n_demo` is the default; n8n webhook availability affects V0–V3 live runs |
| Fixture is static | `fixtures/google_ads_summary_fixture.json` uses fixed metrics; not representative of all real scenarios |
| Credential mapping is env-based | Production per-tenant credential resolution is design-only; not implemented in V4 |
| No real API validation | Credential structure validation passes on any non-empty string; OAuth token validity is not checked |

---

## Recommended next steps

### Immediate

- Tag `v4.0.0-beta` on the current `v4-real-integrations` tip
- Merge `v4-real-integrations` into `master`

### Next branch

**`v4.5.1-google-ads-live-fetch`** — recommended next branch after tagging.

Scope:
1. Add `google-ads>=23.1.0` to `agents/ads-agent/requirements.txt`
2. Implement real GAQL fetch in `fetch_google_ads_metrics()` behind `GOOGLE_ADS_LIVE_ENABLED=true`
3. Map GAQL rows to canonical metrics schema via `normalize_metrics()`
4. Handle `GoogleAdsException` and `TransportError` → normalized error codes
5. Manual live test against real account per runbook §9
6. Verify no credential values appear in logs, audit, or MemPalace

All automated smoke tests must remain green with `GOOGLE_ADS_LIVE_ENABLED=false` (default).

---

## Files added or changed in V4

```
agents/ads-agent/integrations/__init__.py          (new)
agents/ads-agent/integrations/schemas.py           (new)
agents/ads-agent/integrations/resolver.py          (new)
agents/ads-agent/integrations/mock_fixture_adapter.py  (new)
agents/ads-agent/integrations/google_ads_adapter.py    (new)
agents/ads-agent/fixtures/google_ads_summary_fixture.json  (new)
agents/ads-agent/ads_graph.py                      (modified — fetch node wired to resolver)
agents/ads-agent/run_integration_demo.py           (new)
agents/ads-agent/run_google_ads_adapter_demo.py    (new)
agents/ads-agent/README.md                         (updated)
docs/V4_REAL_INTEGRATIONS_DESIGN.md               (new)
docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md       (new)
docs/ROADMAP.md                                    (updated)
docs/ENVIRONMENT_VARIABLES.md                      (updated)
docs/V4_BETA_RELEASE_NOTES.md                     (new — this file)
scripts/smoke_test_v4_integrations.sh              (new)
.env.example                                       (updated — Google Ads block added)
README.md                                          (updated)
```

Files explicitly not changed: `openclaw/`, `agents/router/`, `agents/ads-agent/n8n_client.py`, `agents/ads-agent/mempalace.py`, `docker/`, `memory/`, `.venv/`, `.gitignore`

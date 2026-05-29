# Google Ads Live Integration Runbook

**Status:** Runbook only — no live API code implemented yet (V4.5.0)
**Implements:** V4.5 preparation — live fetch will be implemented in V4.5.1
**Branch:** `v4-real-integrations`
**Related:** [docs/V4_REAL_INTEGRATIONS_DESIGN.md](V4_REAL_INTEGRATIONS_DESIGN.md) · [docs/ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)

---

## 1. Purpose

This runbook documents the exact manual steps, environment requirements, and safety rules needed before enabling real Google Ads API calls in Kaiju Command Center.

V4.4 implemented the adapter skeleton: credential loading, validation, and the `GOOGLE_ADS_LIVE_ENABLED` guard. No live API calls are made yet. This runbook prepares V4.5.1 (live fetch implementation) without writing that code.

---

## 2. Current State

As of V4.4:

| Component | Status |
|---|---|
| `google_ads_adapter.py` | Exists — credential loading + validation only |
| `GOOGLE_ADS_LIVE_ENABLED` | Defaults `false` — no live calls |
| `ADS_DATA_SOURCE=google_ads` | Returns controlled error, no crash |
| `n8n_demo` path | Unchanged — default behavior |
| `mock_fixture` path | Functional — no network, no credentials |
| `google-ads` Python library | Not yet installed |
| Real Google Ads API calls | Not yet implemented |

### Current error progression (`ADS_DATA_SOURCE=google_ads`)

| Condition | Error code | Meaning |
|---|---|---|
| `GOOGLE_ADS_LIVE_ENABLED=false` (default) | `google_ads_live_disabled` | Live calls intentionally blocked |
| Live enabled, credentials missing | `credentials_missing` | Lists missing field names, never values |
| Live enabled, all credentials present | `google_ads_live_not_implemented` | Placeholder until V4.5.1 |

---

## 3. Required Credentials

The following environment variables must be set before `GOOGLE_ADS_LIVE_ENABLED=true` can succeed:

| Variable | Required | Secret | Description |
|---|---|---|---|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Yes | **Yes** | Issued by Google per developer account; grants API access |
| `GOOGLE_ADS_CLIENT_ID` | Yes | **Yes** | OAuth2 client ID from a Google Cloud project |
| `GOOGLE_ADS_CLIENT_SECRET` | Yes | **Yes** | OAuth2 client secret paired with the client ID |
| `GOOGLE_ADS_REFRESH_TOKEN` | Yes | **Yes** | Long-lived token granting offline access to the Ads account |
| `GOOGLE_ADS_CUSTOMER_ID` | Yes | No (tenant-sensitive) | The Google Ads account (customer) ID to query |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | Optional | No (tenant-sensitive) | MCC / manager account ID; required only if accessing sub-accounts through a hierarchy |

### Field details

**`GOOGLE_ADS_DEVELOPER_TOKEN`**
Issued by Google Ads through the API Center in your Google Ads manager account. Every API project requires one. Apply at `ads.google.com` → Tools → API Center. Approval may take several days for production access; test accounts use basic access.

**`GOOGLE_ADS_CLIENT_ID`**
The OAuth2 client ID from a Google Cloud Console project with the Google Ads API enabled. Created under APIs & Services → Credentials → OAuth 2.0 Client IDs. Use type "Desktop app" or "Web application" depending on the auth flow used.

**`GOOGLE_ADS_CLIENT_SECRET`**
The secret paired with the client ID above. Treat as a password. Never log or expose.

**`GOOGLE_ADS_REFRESH_TOKEN`**
A long-lived OAuth2 token that allows the application to obtain fresh access tokens without user interaction. Obtained once during the initial OAuth2 authorization flow (see §4).

**`GOOGLE_ADS_CUSTOMER_ID`**
The 10-digit Google Ads account ID of the advertising account to query. Visible in the Google Ads UI in the top bar. Use digits only — no hyphens (e.g. `1234567890` not `123-456-7890`). The `google-ads-python` library expects no hyphens.

**`GOOGLE_ADS_LOGIN_CUSTOMER_ID`**
Required only when the OAuth2 credentials belong to a manager (MCC) account and you are querying a sub-account. Set to the MCC account ID. Omit if credentials directly belong to the advertising account being queried.

---

## 4. OAuth2 Refresh Token Acquisition

The refresh token is obtained once via an authorization flow. Three options:

### Option A — Google OAuth Playground (recommended for testing)

1. Go to `https://developers.google.com/oauthplayground`
2. In settings (gear icon), check "Use your own OAuth credentials" and enter your client ID and secret
3. In the scope field, enter: `https://www.googleapis.com/auth/adwords`
4. Click "Authorize APIs" — complete the Google sign-in for the account that owns the Ads data
5. Click "Exchange authorization code for tokens"
6. Copy the `refresh_token` value from the response
7. Store it in your local `.env` file — never paste into chat or logs

### Option B — Custom OAuth script

A minimal Python script using `google-auth-oauthlib` can be added later as a one-off utility. It runs the local server flow, prints the refresh token once, and exits. This will be documented in a future runbook update.

### Option C — Existing Google Cloud OAuth client

If a Google Cloud project is already configured for this workspace with the Ads API enabled, re-use the existing client credentials and authorize the required scope.

### Required OAuth scope

```
https://www.googleapis.com/auth/adwords
```

No other scope is needed for read-only campaign metrics access.

---

## 5. Local `.env` Setup

Copy `.env.example` to `.env` (already gitignored) and fill in real values:

```bash
# Data source and live flag
ADS_DATA_SOURCE=google_ads
GOOGLE_ADS_LIVE_ENABLED=true

# Google Ads credentials — NEVER commit these values
GOOGLE_ADS_DEVELOPER_TOKEN="your-developer-token"
GOOGLE_ADS_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_ADS_CLIENT_SECRET="your-client-secret"
GOOGLE_ADS_REFRESH_TOKEN="your-refresh-token"
GOOGLE_ADS_CUSTOMER_ID="1234567890"
GOOGLE_ADS_LOGIN_CUSTOMER_ID=""
```

Source the file before running demos:

```bash
set -a && source .env && set +a
```

Or prefix commands inline (for quick testing):

```bash
ADS_DATA_SOURCE=google_ads \
GOOGLE_ADS_LIVE_ENABLED=true \
GOOGLE_ADS_DEVELOPER_TOKEN="..." \
GOOGLE_ADS_CUSTOMER_ID="..." \
python3 agents/ads-agent/run_google_ads_adapter_demo.py
```

---

## 6. Secret Safety Rules

**These rules are mandatory and must be preserved in all V4.5 implementation work.**

| Rule | Detail |
|---|---|
| Never commit `.env` | `.env` is gitignored; `.env.example` contains only empty placeholders |
| Never paste credentials into chat | Including this chat, Slack, GitHub issues, PR descriptions |
| Never print raw env var values | `redacted_google_ads_credentials()` exists for this; always use it |
| No credentials in audit logs | The OpenClaw audit JSONL must not record any credential field values |
| No credentials in MemPalace | Snapshots, profiles, and insights must never contain credential data |
| No credentials in error messages | Error messages list missing field *names*, never values |
| No credentials in graph state | `AdsAgentState` must not carry credential values |
| Production: Secret Manager only | All credentials sourced from GCP Secret Manager in production |

### Verification checklist before any credential-related commit

```bash
# Check staged diff for common secret patterns
git diff --cached | grep -iE "ya29\.|1//[A-Za-z0-9_-]{10}|AAAA[A-Za-z0-9_-]{10}" && echo "WARNING: possible token" || echo "CLEAN"
git diff --cached | grep "GOOGLE_ADS_.*=" | grep -v "=$\|=false\|=true\|=n8n_demo\|=google_ads\|=mock_fixture\|=15\|=graph" && echo "WARNING: possible value" || echo "CLEAN"
```

---

## 7. Proposed V4.5.1 Implementation Approach

The following code changes will be made in V4.5.1. **Not implemented yet.**

### Step 1 — Add `google-ads` library

```
agents/ads-agent/requirements.txt
```

Add:
```
google-ads>=23.1.0
```

Install into `.venv`:
```bash
~/kaiju/.venv/bin/pip install google-ads
```

### Step 2 — Google Ads client creation (`google_ads_adapter.py`)

```python
from google.ads.googleads.client import GoogleAdsClient

def _build_client(credentials: GoogleAdsCredentials) -> GoogleAdsClient:
    config = {
        "developer_token": credentials.developer_token,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "refresh_token": credentials.refresh_token,
        "use_proto_plus": True,
    }
    if credentials.login_customer_id:
        config["login_customer_id"] = credentials.login_customer_id
    return GoogleAdsClient.load_from_dict(config)
```

### Step 3 — GAQL query execution

Execute the query in §8 using the client's `GoogleAdsService`.

### Step 4 — Normalization

Map the GAQL rows to the canonical metrics schema (see §10).

### Step 5 — Error handling

Wrap all API calls in `try/except`. Map `GoogleAdsException` and `TransportError` to normalized error codes (see §11). Never surface raw exception messages that may contain account details.

### Step 6 — Guard

The live fetch block remains wrapped in `if is_google_ads_live_enabled()`. Smoke tests always run with `GOOGLE_ADS_LIVE_ENABLED=false` (default).

---

## 8. Initial GAQL Query

This read-only query fetches campaign-level metrics for the last 30 days. It will be the basis for V4.5.1's `fetch_google_ads_metrics()` implementation.

```sql
SELECT
  campaign.id,
  campaign.name,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
LIMIT 20
```

### Normalization notes

| GAQL field | Canonical field | Transformation |
|---|---|---|
| `metrics.cost_micros` | `spend` | Divide by 1,000,000 |
| `metrics.impressions` | `impressions` | Direct |
| `metrics.clicks` | `clicks` | Direct |
| `metrics.conversions` | `conversions` | Direct (float → int) |
| `campaign.name` | `campaign` | Use first row or join with `, ` for summary |

For account-level summary (`request_type=summary`), aggregate all rows: sum `spend`, `impressions`, `clicks`, `conversions`. Derive `cpa`, `ctr`, `cpc`, `conversion_rate` using the existing `normalize_metrics()` function from `integrations/schemas.py`.

For a future `request_type=campaigns` response, return per-campaign rows. This is out of scope for V4.5.

---

## 9. Manual Live Test Commands

**Run after V4.5.1 is implemented** (not yet available):

### Adapter demo
```bash
cd ~/kaiju/agents/ads-agent
ADS_DATA_SOURCE=google_ads \
GOOGLE_ADS_LIVE_ENABLED=true \
~/kaiju/.venv/bin/python3 run_google_ads_adapter_demo.py
```

Expected: `ok: true`, canonical metrics, no credential values in output.

### Integration resolver demo
```bash
ADS_DATA_SOURCE=google_ads \
GOOGLE_ADS_LIVE_ENABLED=true \
~/kaiju/.venv/bin/python3 run_integration_demo.py summary
```

### Full graph demo (via OpenClaw)
```bash
cd ~/kaiju
ADS_DATA_SOURCE=google_ads \
GOOGLE_ADS_LIVE_ENABLED=true \
~/kaiju/.venv/bin/python3 openclaw/run_openclaw_demo.py summary
```

### Credential-only validation (no fetch)
```bash
cd ~/kaiju/agents/ads-agent
GOOGLE_ADS_LIVE_ENABLED=true \
~/kaiju/.venv/bin/python3 run_google_ads_adapter_demo.py
# Expect: credentials pass validation, then google_ads_live_not_implemented until V4.5.1
```

---

## 10. Expected Success Response Shape

After V4.5.1 implementation, a successful live fetch should return:

```json
{
  "ok": true,
  "data_source": "google_ads",
  "data": {
    "source": "google_ads",
    "client": "your-client-id",
    "campaign": "Campaign Name (aggregated)",
    "date_range": {
      "start_date": null,
      "end_date": null
    },
    "currency": "ARS",
    "spend": 125000.0,
    "conversions": 62,
    "clicks": 3100,
    "impressions": 85000,
    "ctr": 0.0365,
    "cpc": 40.32,
    "cpa": 2016.13,
    "conversion_rate": 0.02,
    "raw_source": "google_ads"
  }
}
```

The `data` block matches the canonical metrics schema exactly. The graph's `normalize_metrics` node and all downstream analysis nodes receive this shape unchanged.

---

## 11. Expected Failure Modes

All errors are normalized before reaching the OpenClaw envelope. Raw Google Ads API exceptions are never surfaced.

| Error code | Trigger | Recoverable |
|---|---|---|
| `google_ads_live_disabled` | `GOOGLE_ADS_LIVE_ENABLED=false` (default) | Yes |
| `google_ads_live_not_implemented` | Live enabled, credentials valid, V4.5.1 not yet deployed | Yes |
| `credentials_missing` | One or more required env vars absent | Yes |
| `credentials_invalid` | OAuth token rejected or developer token denied | Yes |
| `google_ads_api_error` | Google Ads API returned a non-transient error | Yes |
| `customer_not_found` | `GOOGLE_ADS_CUSTOMER_ID` does not exist or is inaccessible | Yes |
| `no_data` | API returned zero rows for the requested date range | Yes |
| `integration_timeout` | Google Ads API request exceeded configured timeout | Yes |

All errors produce `ok: false` in the OpenClaw response envelope with the normalized code in `errors[0].code`. No Python tracebacks are exposed.

---

## 12. Testing Policy

| Test type | Approach |
|---|---|
| Automated smoke tests (V0–V4) | Always use `ADS_DATA_SOURCE=n8n_demo` (default) or `mock_fixture`; no credentials required |
| V4 integration smoke test (`smoke_test_v4_integration.sh`) | Uses `ADS_DATA_SOURCE=mock_fixture` only — no network, no credentials |
| Live Google Ads tests | Manual only; requires real credentials; not part of CI suite |
| Credential validation test | Can run with fake env vars; `google_ads_live_not_implemented` confirms validator passed |

The `n8n_demo` path remains the default for all automated suites. Live tests are gated behind `GOOGLE_ADS_LIVE_ENABLED=true` which must be set explicitly.

---

## 13. Production Implications

Before enabling live Google Ads calls in production:

| Requirement | Detail |
|---|---|
| GCP Secret Manager | All 6 credential vars must be stored as secrets, not env vars in container config |
| Tenant credential mapping | Each `client_id` / `tenant_id` must map to its own credential reference — not a single global set |
| Per-tenant customer ID | `GOOGLE_ADS_CUSTOMER_ID` must be resolved per request, not a static env var |
| Audit log safety | Audit JSONL entries may record `data_source: google_ads` and error codes, but never credential values or raw API responses |
| MemPalace safety | Snapshots store canonical metrics (normalized numbers), never raw API payloads |
| Rate limiting | Google Ads API has per-developer and per-account rate limits; implement retry with backoff before production |
| Access level | Basic access (test account data) is granted first; standard access requires Google review |
| Production smoke test | A synthetic read-only "canary" customer ID can validate the live path without touching real client data |

---

## 14. V4.5 Acceptance Criteria

### V4.5.0 (this runbook) — complete when:

- [x] `docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md` exists
- [x] Required credentials documented with field-level detail
- [x] OAuth2 refresh token acquisition steps documented
- [x] Secret safety rules explicitly stated
- [x] Proposed V4.5.1 implementation approach documented
- [x] Initial GAQL query documented
- [x] Manual live test commands documented
- [x] Expected success response shape documented
- [x] All normalized error codes documented
- [x] Testing policy (no live credentials in CI) documented
- [x] Production implications documented
- [x] No secrets committed
- [x] All existing smoke tests pass

### V4.5.1 (live fetch — not yet implemented) — complete when:

- [ ] `google-ads` library added to `agents/ads-agent/requirements.txt`
- [ ] `fetch_google_ads_metrics()` implements real GAQL query behind `GOOGLE_ADS_LIVE_ENABLED=true`
- [ ] Canonical metrics returned from live data
- [ ] All normalized error codes handled
- [ ] No credential values in logs, audit, or MemPalace
- [ ] Manual live test confirmed against real account
- [ ] All automated smoke tests still pass (still use `n8n_demo` / `mock_fixture`)

---

## Further Reading

| Document | Purpose |
|---|---|
| [docs/V4_REAL_INTEGRATIONS_DESIGN.md](V4_REAL_INTEGRATIONS_DESIGN.md) | V4 architecture design and phase status |
| [docs/ROADMAP.md](ROADMAP.md) | Full milestone history |
| [docs/ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) | All env var definitions including Google Ads vars |
| [.env.example](.env.example) | Local dev template |
| [docs/GCP_DEPLOYMENT_PLAN.md](GCP_DEPLOYMENT_PLAN.md) | Cloud Run deployment and Secret Manager plan |

# Environment Variables Reference

All Kaiju Command Center / OpenClaw configuration is read from environment variables. No config file is committed. Use `.env.example` as a local development template (copy to `.env`, never commit `.env`).

---

## OpenClaw Variables

### `OPENCLAW_ENV`

| Field | Value |
|---|---|
| Purpose | Runtime environment identifier |
| Default | `local` |
| Allowed values | `local`, `staging`, `production` |
| Invalid value | Falls back to `local` |
| Local example | `OPENCLAW_ENV=local` |
| Production | `OPENCLAW_ENV=production` |
| Secret | No |

---

### `PORT`

| Field | Value |
|---|---|
| Purpose | HTTP server listen port |
| Default | `8100` |
| Local example | `PORT=8100` |
| Production | Set automatically by Cloud Run; do not hardcode |
| Secret | No |

---

### `OPENCLAW_API_AUTH_ENABLED`

| Field | Value |
|---|---|
| Purpose | Enable API key enforcement on `POST /openclaw/process` |
| Default | `false` |
| Accepted true values | `true`, `1`, `yes`, `on` |
| Accepted false values | `false`, `0`, `no`, `off` |
| Invalid value | Falls back to `false` |
| Local example | `OPENCLAW_API_AUTH_ENABLED=false` |
| Production | `OPENCLAW_API_AUTH_ENABLED=true` |
| Secret | No |
| Notes | When enabled, `OPENCLAW_API_KEYS` must also be set |

---

### `OPENCLAW_API_KEYS`

| Field | Value |
|---|---|
| Purpose | Comma-separated valid Bearer tokens for API key auth |
| Default | Empty (no keys) |
| Local example | `OPENCLAW_API_KEYS=local-dev-key` |
| Production | Sourced from GCP Secret Manager — never hardcode |
| Secret | **Yes** |
| Notes | Keys are never printed by `run_config_demo.py`; shown as count only. If `OPENCLAW_API_AUTH_ENABLED=true` and this is empty, all requests return `auth_not_configured`. |

---

### `OPENCLAW_ALLOWED_ORIGINS`

| Field | Value |
|---|---|
| Purpose | CORS allowed origins (comma-separated) |
| Default | `*` |
| Local example | `OPENCLAW_ALLOWED_ORIGINS=*` |
| Production | `OPENCLAW_ALLOWED_ORIGINS=https://app.kaiju.digital,https://admin.kaiju.digital` |
| Secret | No |
| Notes | Wildcard (`*`) sets `allow_credentials=False`. Explicit origins set `allow_credentials=True`. Never use `*` with credentials in production. |

---

### `OPENCLAW_DEFAULT_TENANT`

| Field | Value |
|---|---|
| Purpose | Fallback tenant identifier when none is supplied in the request |
| Default | `demo-client` |
| Local example | `OPENCLAW_DEFAULT_TENANT=demo-client` |
| Production | Set to your primary tenant or organization slug |
| Secret | No |

---

### `OPENCLAW_REQUIRE_TENANT_HEADER`

| Field | Value |
|---|---|
| Purpose | Reject requests that do not include an `X-Tenant-Id` header |
| Default | `false` |
| Local example | `OPENCLAW_REQUIRE_TENANT_HEADER=false` |
| Production | `OPENCLAW_REQUIRE_TENANT_HEADER=true` when multi-tenant is active |
| Secret | No |
| Notes | Not enforced in code yet (V3.5 design only); flag is parsed and available |

---

### `OPENCLAW_AUDIT_ENABLED`

| Field | Value |
|---|---|
| Purpose | Enable append-only JSONL audit log writes |
| Default | `true` |
| Local example | `OPENCLAW_AUDIT_ENABLED=true` |
| Production | `OPENCLAW_AUDIT_ENABLED=true` (use Cloud Logging sink in future) |
| Secret | No |
| Notes | Audit failures are non-fatal — requests continue and return `ok: true` with a warning |

---

### `OPENCLAW_AUDIT_ROOT`

| Field | Value |
|---|---|
| Purpose | Directory for local JSONL audit files |
| Default | `openclaw/audit` (repo-relative) |
| Local example | `OPENCLAW_AUDIT_ROOT=openclaw/audit` |
| Production | Override to a GCS-mounted path or disable in favour of Cloud Logging |
| Secret | No |
| Notes | Runtime audit files are gitignored. In Cloud Run, container filesystem is ephemeral — audit files do not persist across restarts. |

---

## Memory Variables (MemPalace)

### `MEMORY_ENABLED`

| Field | Value |
|---|---|
| Purpose | Enable MemPalace client memory reads and writes |
| Default | `true` |
| Local example | `MEMORY_ENABLED=true` |
| Production | `MEMORY_ENABLED=false` until a durable storage backend is configured |
| Secret | No |
| Notes | When disabled, all memory operations return safe no-ops; graph continues normally |

---

### `MEMORY_ROOT`

| Field | Value |
|---|---|
| Purpose | Root directory for client memory files |
| Default | `memory/client-memory` (repo-relative) |
| Local example | `MEMORY_ROOT=memory/client-memory` |
| Production | Override to a GCS-mounted path or Firestore adapter path |
| Secret | No |
| Notes | Runtime memory files are gitignored |

---

### `MEMORY_MAX_RECENT_SNAPSHOTS`

| Field | Value |
|---|---|
| Purpose | Number of recent snapshots to load per run for historical comparison |
| Default | `5` |
| Local example | `MEMORY_MAX_RECENT_SNAPSHOTS=5` |
| Production | Tune based on storage cost and comparison window needed |
| Secret | No |

---

### `MEMORY_STORE_RAW_PAYLOADS`

| Field | Value |
|---|---|
| Purpose | Store raw n8n payload in snapshot (design-only, not yet implemented) |
| Default | `false` |
| Local example | `MEMORY_STORE_RAW_PAYLOADS=false` |
| Production | Keep `false`; raw payloads may contain sensitive data |
| Secret | No |
| Notes | V2.5 deferred feature — parsed by config module but not yet acted upon |

---

## n8n / Agent Variables

### `N8N_ADS_WEBHOOK_URL`

| Field | Value |
|---|---|
| Purpose | URL of the n8n webhook for Ads Agent data fetch |
| Default | `None` (empty) |
| Local example | `N8N_ADS_WEBHOOK_URL=https://flows.kaiju.digital/webhook/ads-agent-demo` |
| Production | Sourced from GCP Secret Manager |
| Secret | **Yes** (if webhook URL includes auth tokens or is not public) |
| Notes | Never use `/webhook-test/` paths in production |

---

### `N8N_WEBHOOK_TIMEOUT`

| Field | Value |
|---|---|
| Purpose | Timeout in seconds for n8n webhook HTTP requests |
| Default | `15.0` |
| Invalid value | Zero, negative, or non-numeric falls back to `15.0` |
| Local example | `N8N_WEBHOOK_TIMEOUT=15` |
| Production | Increase if n8n cold starts are observed (e.g. `30`) |
| Secret | No |

---

### `ADS_AGENT_EXECUTION_MODE`

| Field | Value |
|---|---|
| Purpose | Toggle between LangGraph execution and legacy direct mode |
| Default | `graph` |
| Allowed values | `graph`, `legacy` |
| Local example | `ADS_AGENT_EXECUTION_MODE=graph` |
| Production | `ADS_AGENT_EXECUTION_MODE=graph` |
| Secret | No |
| Notes | `legacy` mode uses the direct n8n client path without LangGraph nodes |

---

## Google Ads Integration Variables (V4.4+)

### `ADS_DATA_SOURCE`

| Field | Value |
|---|---|
| Purpose | Select data source adapter for the Ads Agent |
| Default | `n8n_demo` |
| Allowed values | `n8n_demo`, `mock_fixture`, `google_ads` |
| Invalid value | Falls back to `n8n_demo` |
| Local example | `ADS_DATA_SOURCE=n8n_demo` |
| Production | `ADS_DATA_SOURCE=google_ads` when real integration is active |
| Secret | No |
| Notes | `google_ads` requires `GOOGLE_ADS_LIVE_ENABLED=true` and all credential vars |

---

### `GOOGLE_ADS_LIVE_ENABLED`

| Field | Value |
|---|---|
| Purpose | Gate for live Google Ads API calls |
| Default | `false` |
| Accepted true values | `true`, `1`, `yes`, `on` |
| Accepted false values | anything else |
| Local example | `GOOGLE_ADS_LIVE_ENABLED=false` |
| Production | `GOOGLE_ADS_LIVE_ENABLED=true` when real integration is active |
| Secret | No |
| Notes | When `false`, `ADS_DATA_SOURCE=google_ads` returns `google_ads_live_disabled` error without loading credentials |

---

### `GOOGLE_ADS_CREDENTIAL_SOURCE`

| Field | Value |
|---|---|
| Purpose | Selects the credential loading strategy for the Google Ads adapter |
| Default | `env` |
| Accepted values | `env` — load credentials from environment variables (default); `provider` — load via CredentialProvider composition layer |
| Local example | `GOOGLE_ADS_CREDENTIAL_SOURCE=env` |
| Production | `GOOGLE_ADS_CREDENTIAL_SOURCE=provider` when tenant-level credentials are used |
| Secret | No |
| Notes | Any unrecognised value falls back to `env`. When set to `provider`, `tenant_id` must be supplied to the adapter call and a `SecretStore` must be reachable via the CredentialProvider. |

---

### `GOOGLE_ADS_DEVELOPER_TOKEN`

| Field | Value |
|---|---|
| Purpose | Google Ads API developer token |
| Default | Empty |
| Local example | Do not commit; set in local `.env` only |
| Production | Sourced from GCP Secret Manager |
| Secret | **Yes** |
| Notes | Required when `GOOGLE_ADS_LIVE_ENABLED=true` |

---

### `GOOGLE_ADS_CLIENT_ID`

| Field | Value |
|---|---|
| Purpose | OAuth2 client ID for Google Ads API access |
| Default | Empty |
| Local example | Do not commit; set in local `.env` only |
| Production | Sourced from GCP Secret Manager |
| Secret | **Yes** (treat as sensitive) |
| Notes | Required when `GOOGLE_ADS_LIVE_ENABLED=true` |

---

### `GOOGLE_ADS_CLIENT_SECRET`

| Field | Value |
|---|---|
| Purpose | OAuth2 client secret |
| Default | Empty |
| Local example | Do not commit; set in local `.env` only |
| Production | Sourced from GCP Secret Manager |
| Secret | **Yes** |
| Notes | Required when `GOOGLE_ADS_LIVE_ENABLED=true` |

---

### `GOOGLE_ADS_REFRESH_TOKEN`

| Field | Value |
|---|---|
| Purpose | Long-lived OAuth2 refresh token for Google Ads API |
| Default | Empty |
| Local example | Do not commit; set in local `.env` only |
| Production | Sourced from GCP Secret Manager |
| Secret | **Yes** |
| Notes | Required when `GOOGLE_ADS_LIVE_ENABLED=true` |

---

### `GOOGLE_ADS_LOGIN_CUSTOMER_ID`

| Field | Value |
|---|---|
| Purpose | MCC / manager account ID (used when accessing sub-accounts) |
| Default | Empty |
| Local example | `GOOGLE_ADS_LOGIN_CUSTOMER_ID=9876543210` |
| Production | Tenant-specific; not a secret but sensitive |
| Secret | No (but tenant-sensitive — do not log) |
| Notes | Optional — omit if not using an MCC hierarchy |

---

### `GOOGLE_ADS_CUSTOMER_ID`

| Field | Value |
|---|---|
| Purpose | Target Google Ads advertising account ID |
| Default | Empty |
| Local example | `GOOGLE_ADS_CUSTOMER_ID=1234567890` |
| Production | Tenant-specific; sourced from tenant config |
| Secret | No (but tenant-sensitive — do not log) |
| Notes | Required when `GOOGLE_ADS_LIVE_ENABLED=true` |

---

### `GOOGLE_ADS_CURRENCY`

| Field | Value |
|---|---|
| Purpose | Currency code for canonical metrics output from live Google Ads fetch |
| Default | `ARS` |
| Allowed values | Any ISO 4217 currency code (e.g. `ARS`, `USD`, `EUR`) |
| Local example | `GOOGLE_ADS_CURRENCY=ARS` |
| Production | Set per tenant to match their Google Ads account currency |
| Secret | No |
| Notes | Applies only when `ADS_DATA_SOURCE=google_ads` and `GOOGLE_ADS_LIVE_ENABLED=true` |

---

## GCP Secret Manager Variables (V5.12+)

### `GCP_SECRET_MANAGER_ENABLED`

| Field | Value |
|---|---|
| Purpose | Gate for all live GCP Secret Manager API calls |
| Default | `false` |
| Accepted true values | `true`, `1`, `yes`, `on` |
| Accepted false values | anything else |
| Local example | `GCP_SECRET_MANAGER_ENABLED=false` |
| Production | `GCP_SECRET_MANAGER_ENABLED=true` when GCPSecretManagerStore is active |
| Secret | No |
| Notes | When `false`, no GCP client is instantiated and no network calls are made. Default remains `false` through V5.12.2. |

---

### `GCP_PROJECT_ID`

| Field | Value |
|---|---|
| Purpose | GCP project for Secret Manager API calls |
| Default | Empty |
| Fallback | `GOOGLE_CLOUD_PROJECT` (standard GCP SDK env var) |
| Local example | `GCP_PROJECT_ID=my-gcp-project` |
| Production | Set to the project that owns the Secret Manager secrets |
| Secret | No |
| Notes | Required when `GCP_SECRET_MANAGER_ENABLED=true`. If empty, `GCPSecretManagerStore` records an init error and returns safe unavailable responses. |

---

### `GCP_SECRET_MANAGER_PREFIX`

| Field | Value |
|---|---|
| Purpose | Prefix segment in GCP secret names |
| Default | `kaiju` |
| Local example | `GCP_SECRET_MANAGER_PREFIX=kaiju` |
| Production | `GCP_SECRET_MANAGER_PREFIX=kaiju` (or org-specific slug) |
| Secret | No |
| Notes | Becomes the first segment of `{prefix}-{env}-{integration_type}-{credential_ref}`. |

---

### `GCP_SECRET_MANAGER_ENV`

| Field | Value |
|---|---|
| Purpose | Environment segment in GCP secret names |
| Default | `local` |
| Allowed values | `local`, `dev`, `staging`, `prod` |
| Invalid value | Falls back to `local` |
| Local example | `GCP_SECRET_MANAGER_ENV=local` |
| Production | `GCP_SECRET_MANAGER_ENV=prod` |
| Secret | No |
| Notes | Becomes the second segment of the secret name. Ensures prod secrets are never accessible in dev or staging by accident. |

---

## Summary Table

| Variable | Default | Secret | Required in Production |
|---|---|---|---|
| `OPENCLAW_ENV` | `local` | No | Yes |
| `PORT` | `8100` | No | Set by Cloud Run |
| `OPENCLAW_API_AUTH_ENABLED` | `false` | No | Yes (`true`) |
| `OPENCLAW_API_KEYS` | `` | **Yes** | Yes |
| `OPENCLAW_ALLOWED_ORIGINS` | `*` | No | Yes (explicit origins) |
| `OPENCLAW_DEFAULT_TENANT` | `demo-client` | No | Yes |
| `OPENCLAW_REQUIRE_TENANT_HEADER` | `false` | No | Future |
| `OPENCLAW_AUDIT_ENABLED` | `true` | No | Yes |
| `OPENCLAW_AUDIT_ROOT` | `openclaw/audit` | No | Override for durability |
| `MEMORY_ENABLED` | `true` | No | `false` until durable backend |
| `MEMORY_ROOT` | `memory/client-memory` | No | Override for durability |
| `MEMORY_MAX_RECENT_SNAPSHOTS` | `5` | No | No |
| `MEMORY_STORE_RAW_PAYLOADS` | `false` | No | No |
| `N8N_ADS_WEBHOOK_URL` | `None` | **Yes** | Yes |
| `N8N_WEBHOOK_TIMEOUT` | `15.0` | No | No |
| `ADS_AGENT_EXECUTION_MODE` | `graph` | No | No |
| `ADS_DATA_SOURCE` | `n8n_demo` | No | `google_ads` when live |
| `GOOGLE_ADS_LIVE_ENABLED` | `false` | No | `true` when live |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | `` | **Yes** | Yes (live only) |
| `GOOGLE_ADS_CLIENT_ID` | `` | **Yes** | Yes (live only) |
| `GOOGLE_ADS_CLIENT_SECRET` | `` | **Yes** | Yes (live only) |
| `GOOGLE_ADS_REFRESH_TOKEN` | `` | **Yes** | Yes (live only) |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | `` | No | Optional |
| `GOOGLE_ADS_CUSTOMER_ID` | `` | No | Yes (live only) |
| `GOOGLE_ADS_CURRENCY` | `ARS` | No | Set per tenant |
| `GCP_SECRET_MANAGER_ENABLED` | `false` | No | `true` when GCPSecretManagerStore is active |
| `GCP_PROJECT_ID` | `` | No | Yes (when Secret Manager enabled) |
| `GCP_SECRET_MANAGER_PREFIX` | `kaiju` | No | No |
| `GCP_SECRET_MANAGER_ENV` | `local` | No | `prod` in production |

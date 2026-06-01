# V5 — Tenant Credentials & Secure Onboarding — Design Document

**Status:** In progress — V5.2 complete  
**Milestone tag:** `v5.0.0` (target)  
**Depends on:** V4 beta (`v4.5.1-alpha`)

---

## 1. Purpose

V5 defines the secure onboarding layer for tenants and client credentials.

The long-term goal is to allow a new client or user to connect their Google Ads account through a front-end onboarding flow — without exposing secrets to the assistant, to logs, to audit files, to MemPalace, or to Git at any point in the flow.

Today, credentials reach the adapter through environment variables set on the host or container. This is acceptable for a single-tenant deployment but does not scale to a multi-tenant SaaS where each client owns their own Google Ads account and credentials must be stored, retrieved, and rotated independently.

V5 introduces:
- a credential data model that separates secret material from metadata
- a secret store abstraction (local dev → GCP Secret Manager production path)
- OpenClaw admin endpoints for credential submission and status checking
- two onboarding modes: manual credential entry (internal/beta) and OAuth connect flow (SaaS/professional)
- a credential resolver that the Integration Resolver and Google Ads adapter will use at runtime instead of reading environment variables directly
- audit and memory policies that guarantee secret values never appear in observable outputs

---

## 2. Current Baseline

| Area | Current State |
|---|---|
| Live Google Ads fetch | Implemented behind `GOOGLE_ADS_LIVE_ENABLED=true` gate |
| Credential delivery | Environment variables on host or container |
| Tenant credential store | Does not exist |
| Front-end onboarding | Does not exist |
| OAuth UI / connect flow | Does not exist |
| Secret Manager integration | Not implemented (documented as production target) |
| Admin credential endpoints | Does not exist |
| Credential resolver | Does not exist; adapter reads `os.getenv()` directly |
| Credential data model | Implicit in `GoogleAdsCredentials` dataclass; no persistence layer |

The `google_ads_adapter.py` module contains `load_google_ads_credentials()`, which reads five env vars directly. V5 will introduce a credential resolver so the adapter receives credentials from a secure runtime source rather than from the process environment or from request payloads.

---

## 3. Target Architecture

```
Front-end onboarding UI
    ↓
OpenClaw Admin API              (POST /openclaw/admin/.../credentials/google-ads)
    ↓
Credential Service              (validate shape · store secret ref · update status)
    ↓
Secret Backend                  (local: .env / ignored file · production: GCP Secret Manager)
    ↓
Credential Reference Store      (tenant_id + client_id → credential_ref · no secret values)
    ↓
Credential Resolver             (load_credentials_for_client(tenant_id, client_id))
    ↓
Integration Resolver            (resolve_ads_data → selects google_ads adapter)
    ↓
Google Ads Adapter              (receives credentials from resolver, not from env)
    ↓
Google Ads API
```

**Key invariant:** The adapter receives credential material only from the secure runtime credential resolver. Credentials must never travel through request payloads, graph state, audit records, or MemPalace.

---

## 4. Two Onboarding Modes

### Mode A — Manual Credential Entry (Internal / Beta)

Intended for internal teams and early-access clients who already hold a Google Ads developer token and OAuth credentials.

Flow:
1. Admin or authorized user opens the credential management UI.
2. User enters:
   - Developer token
   - OAuth client ID
   - OAuth client secret
   - Refresh token (already exchanged outside this UI)
   - Customer ID
   - Login customer ID (optional, for MCC accounts)
3. Front-end sends a single `POST` to the admin credentials endpoint over TLS.
4. Backend validates shape (all required fields present, customer ID format).
5. Backend writes secret values to the secret store; writes non-secret metadata to the credential reference store.
6. Backend runs optional live validation (GAQL test query — see Section 9).
7. Front-end receives a status response only: `{ "configured": true, "customer_id": "...", "status": "configured" }`. No secret values are returned.
8. On all subsequent reads, the UI shows `configured: true` and last validation date. Raw values are never shown again.

### Mode B — OAuth Connect Flow (SaaS / Professional)

Intended for self-serve clients who do not hold raw credentials.

Flow:
1. User clicks "Connect Google Ads" in the onboarding UI.
2. Front-end redirects the user to Google's OAuth authorization endpoint with the required scopes (`https://www.googleapis.com/auth/adwords`).
3. User grants consent in Google's UI.
4. Google redirects to `GET /openclaw/admin/oauth/google-ads/callback` with an authorization code.
5. Backend exchanges the authorization code for a refresh token and access token using the confidential OAuth client credentials.
6. Backend stores the refresh token in the secret store. The access token is never persisted.
7. Backend writes credential reference metadata (no secrets).
8. Front-end receives connection status only.

**Scope principle:** Request only the minimum required OAuth scope. For read-only campaign metrics, `https://www.googleapis.com/auth/adwords` in read-only mode is sufficient. Do not request write scopes.

---

## 5. Security Principles

These principles are non-negotiable and apply at every layer of V5.

| Principle | Rule |
|---|---|
| Git safety | Never store credentials in any committed file |
| MemPalace safety | Never store credentials or OAuth tokens in MemPalace |
| Audit safety | Never write secret values to audit JSONL files |
| Response safety | Never return secret values in API responses |
| Front-end safety | Never expose refresh tokens or client secrets to the browser after submission |
| Header safety | Never log Authorization headers or Bearer tokens |
| Clipboard safety | Never paste credentials into Claude, ChatGPT, or any chat interface |
| Redaction | All secret values must be redacted before appearing in logs or error messages |
| Encryption at rest | Credentials must be encrypted at rest in the secret store |
| Production secret store | GCP Secret Manager is the production target |
| Local dev secret store | Ignored `.env` or locally-encrypted file only; never committed |
| Principle of least privilege | OAuth scopes must be the minimum required for the integration |
| Tenant isolation | One client's credentials must never be accessible to another client |
| Rotation readiness | Credentials must be replaceable without code changes |

---

## 6. Credential Data Model

Design only. No implementation in V5.1.

### CredentialReference (metadata — safe to store in DB or config)

```
tenant_id          string    Tenant identifier
client_id          string    Client identifier within the tenant
integration_type   string    "google_ads"
credential_ref     string    Opaque reference to secret material in the secret store
customer_id        string    Google Ads advertising account ID (not a secret, but tenant-sensitive)
login_customer_id  string    MCC manager account ID (optional)
status             enum      configured | missing | invalid | validation_failed | active
last_validated_at  datetime  UTC timestamp of last successful or attempted validation
created_at         datetime  UTC timestamp
updated_at         datetime  UTC timestamp
```

### Secret Material (stored in secret backend only — never in CredentialReference)

```
developer_token    string    Google Ads API developer token
client_secret      string    OAuth2 client secret
refresh_token      string    Long-lived OAuth2 refresh token
```

The `credential_ref` field in `CredentialReference` is an opaque pointer (e.g. a GCP Secret Manager resource name or a local UUID). The secret backend resolves it to the actual material at runtime. No database row or config file ever contains the raw secret values.

---

## 7. API Design — Future

Design only. No implementation in V5.1.

All admin endpoints require authentication. In early versions, this may be a static admin API key. In later versions, full user auth is expected.

### Credential management endpoints

```
POST   /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads
       Body: { developer_token, client_id, client_secret, refresh_token, customer_id, login_customer_id? }
       Response: { configured: bool, customer_id: string, status: string }
       Note: secret values are never echoed back

GET    /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/status
       Response: { configured: bool, customer_id: string, status: string, last_validated_at: string }
       Note: no secret values returned

POST   /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/validate
       Triggers live GAQL validation; updates status and last_validated_at
       Response: { valid: bool, error_code: string?, status: string }

DELETE /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads
       Removes credential_ref and deletes secret from secret store
       Response: { deleted: bool }
```

### OAuth endpoints (Mode B)

```
POST   /openclaw/admin/oauth/google-ads/start
       Body: { tenant_id, client_id }
       Response: { authorization_url: string }
       Note: authorization_url is a Google OAuth URL, not a secret

GET    /openclaw/admin/oauth/google-ads/callback
       Query params: code, state
       Backend exchanges code for refresh token; stores securely
       Response: redirect to status page or JSON status
```

### Response redaction rule

All credential endpoint responses must be validated against a redaction schema before being sent. Any response that accidentally includes a field named `developer_token`, `client_secret`, `refresh_token`, `access_token`, or `authorization_code` must be rejected by the response formatter.

---

## 8. Front-End Onboarding UX

Design only.

### Screen flow

```
1. Integrations dashboard
   → Select integration: Google Ads

2. Choose onboarding method
   → [ Connect with Google ]  (Mode B — OAuth)
   → [ Manual setup ]         (Mode A — internal/beta)

3a. OAuth connect flow (Mode B)
   → Redirect to Google OAuth consent screen
   → Return to Kaiju with connection status

3b. Manual credential form (Mode A)
   → Developer token          [password input — masked]
   → OAuth client ID          [text input]
   → OAuth client secret      [password input — masked]
   → Refresh token            [password input — masked]
   → Customer ID              [text input]
   → Login customer ID        [text input, optional]
   → [ Save credentials ]

4. Validation result
   → Success: "Google Ads connected"
   → Failure: human-readable error code (credentials_invalid, customer_not_found, etc.)
   → No raw error messages from the API; no secret values in the error

5. Connected status page
   → Integration: Google Ads
   → Customer ID: 1234-5678-90   (shown)
   → Status: active
   → Last validated: 2026-05-30 21:00 UTC
   → [ Re-validate ] [ Disconnect ]
   → Developer token: ••••••••   (never shown)
   → Refresh token: ••••••••     (never shown)
```

The UI must never render raw secret values after initial submission. The "show value" affordance common in credential managers must not exist here — values are write-only from the front-end's perspective once submitted.

---

## 9. Credential Validation

### Validation stages

| Stage | Description | Required |
|---|---|---|
| Shape validation | All required fields present; customer ID numeric format | Always |
| Live API validation | Optional GAQL test query | On validate endpoint or post-submit |
| Customer access check | Verify the credentials can access the specified customer ID | On live validation |
| Read-only GAQL test | Execute `SELECT campaign.id FROM campaign LIMIT 1` for LAST_7_DAYS | On live validation |

### Error codes

| Code | Meaning |
|---|---|
| `credentials_missing` | One or more required fields absent |
| `credentials_invalid` | Shape valid but API rejected the credentials |
| `secret_store_write_failed` | Secret backend write error |
| `secret_store_read_failed` | Secret backend read error at runtime |
| `oauth_authorization_failed` | User denied consent or Google returned an error |
| `oauth_token_exchange_failed` | Authorization code exchange failed |
| `customer_not_found` | Customer ID not accessible with these credentials |
| `google_ads_api_error` | Generic Google Ads API error |
| `integration_timeout` | Google Ads API did not respond in time |

---

## 10. Secret Storage Strategy

### Local / development

| Option | Safety | Notes |
|---|---|---|
| `.env` file (gitignored) | Safe locally | Already established pattern; never commit |
| Local encrypted file (gitignored) | Safe locally | Adds encryption at rest for local dev |
| Mock secret store | Safe | Returns fixture values; for smoke tests only |

### Production target

**GCP Secret Manager** is the production secret store.

- Each credential field is a separate Secret Manager secret, versioned by tenant/client.
- A suggested naming convention: `kaiju/{env}/{tenant_id}/{client_id}/google_ads/{field_name}`
- The service account running OpenClaw/Cloud Run has `secretmanager.secretAccessor` IAM binding, scoped to the secrets it needs — not project-wide.
- `credential_ref` in the CredentialReference store contains the resource name of the secret (e.g. `projects/my-project/secrets/kaiju-prod-tenant-a-client-b-google_ads-refresh_token/versions/latest`).
- Secrets are retrieved at runtime per request, or cached with a short TTL.
- Secret rotation: new secret version is created; `credential_ref` is updated to the new version; old version is disabled.

### Secret store abstraction

Before any concrete backend is wired, a `CredentialStore` interface must be defined:

```
get(tenant_id, client_id, field) → string | None
set(tenant_id, client_id, field, value) → credential_ref
delete(tenant_id, client_id) → bool
```

Implementations:
- `EnvCredentialStore` — reads from environment variables (current behavior, transitional)
- `LocalFileCredentialStore` — reads/writes an ignored local encrypted file
- `GCPSecretManagerStore` — production implementation

The Google Ads adapter will call the credential resolver, which calls the credential store. It will never call `os.getenv()` directly in V5+.

---

## 11. Tenant Mapping

```
tenant_id
    └── client_id (one or more per tenant)
            └── CredentialReference
                    └── credential_ref → secret material (in secret backend)
                    └── customer_id
                    └── login_customer_id (optional)
```

Rules:
- `tenant_id` is resolved from the `X-Tenant-Id` request header or request body (existing OpenClaw behavior).
- `client_id` identifies the specific client within the tenant.
- The credential resolver uses `(tenant_id, client_id)` as the lookup key.
- Request context objects — `AdsAgentState`, audit records, MemPalace entries — must never contain secret values. They may contain `tenant_id`, `client_id`, `customer_id` (non-secret but tenant-sensitive), and `status`.
- Audit logs include integration status only, not credential material (see Section 12).

---

## 12. Audit and Memory Policy

### Audit JSONL — what is allowed

```
tenant_id              ✓ Allowed
client_id              ✓ Allowed
integration_type       ✓ Allowed  e.g. "google_ads"
credential_status      ✓ Allowed  e.g. "active", "validation_failed"
validation_result_code ✓ Allowed  e.g. "google_ads_api_error"
timestamp              ✓ Allowed
```

### Audit JSONL — what is forbidden

```
developer_token        ✗ Never
client_secret          ✗ Never
refresh_token          ✗ Never
oauth_authorization_code ✗ Never
access_token           ✗ Never
raw_request_body (if it contains credentials) ✗ Never
```

### MemPalace — what is allowed

MemPalace may store integration status metadata: `integration_type`, `status`, `last_validated_at`. It must never store credentials, OAuth tokens, or `credential_ref` values.

### Enforcement

The audit writer and the memory writer must validate their inputs against an allowlist before writing. Any field not on the allowlist is dropped silently and a warning is emitted to stderr.

---

## 13. Threat Model

| Threat | Risk | Mitigation |
|---|---|---|
| Credential leakage through logs | High | `_sanitize_message()` already exists; extend to credential resolver layer; never log raw config dicts |
| Credential leakage through audit JSONL | High | Audit writer allowlist (Section 12); audit tests in V5 smoke suite |
| Credential leakage through MemPalace | Medium | MemPalace writer allowlist; write_memory node never receives credential material |
| Front-end exposure after submission | Medium | Response redaction schema; write-only credential UI |
| Accidental commit of `.env` | High | `.gitignore` already covers `.env`; pre-commit hook recommended |
| Over-permissive OAuth scopes | Medium | Request only `adwords` read-only scope; document minimum required scope |
| Tenant credential mix-up | High | `(tenant_id, client_id)` compound key; strict isolation in credential resolver |
| Stale or rotated credentials | Medium | Credential validation endpoint; `last_validated_at` surfaced to UI; rotation plan in runbook |
| Unauthorized admin access | High | Admin endpoints require auth; admin API key or full user auth before endpoints are exposed |
| Secret Manager IAM over-permission | Medium | Least-privilege service account; secret names scoped to tenant/client |
| Credential material in graph state | High | Graph state schema (`AdsAgentState`) must not include credential fields; enforced in V5.7 |
| OAuth code interception | Medium | Authorization code is single-use and short-lived; HTTPS required; `state` parameter for CSRF protection |

---

## 14. Implementation Phases

| Phase | Scope |
|---|---|
| **V5.1** | Design doc + ROADMAP update (this document) |
| **V5.2** | Local credential status model: `CredentialReference` dataclass, status enum, metadata helpers — no secret storage yet |
| **V5.3** | `CredentialStore` abstraction interface: `get`, `set`, `delete`; `EnvCredentialStore` transitional implementation |
| **V5.4** | `LocalFileCredentialStore`: ignored local encrypted file; credential smoke test section for local dev path |
| **V5.5** | OpenClaw admin credential status endpoints: `GET .../status` only; no write yet; auth placeholder |
| **V5.6** | Manual credential upload endpoint: `POST .../credentials/google-ads`; shape validation; secret store write; redacted response only |
| **V5.7** | Google Ads adapter reads credentials through credential resolver instead of `os.getenv()`; `EnvCredentialStore` wired as default; existing env-var path still works |
| **V5.8** | OAuth flow skeleton: `POST /oauth/google-ads/start` returns authorization URL; `GET /oauth/google-ads/callback` stub; no live exchange yet |
| **V5.9** | `GCPSecretManagerStore`: production implementation; IAM notes; Cloud Run integration |
| **V5.10** | Front-end onboarding integration: wire UI screens to admin endpoints; status page; validation result display |

---

## 15. Non-Goals for Early V5

The following are explicitly out of scope until explicitly promoted:

- Billing or subscription management
- Full user account management (registration, login, password reset)
- Public self-serve onboarding without admin review
- Production Google OAuth consent screen submission to Google
- Multi-region secret replication
- Secret sharing between tenants
- Write access to Google Ads (all integrations remain read-only)
- Kubernetes or multi-region deployment changes
- Tenant database if in-memory or file-based config is sufficient for the first internal version

---

## 16. Acceptance Criteria for V5 Planning

The following must be true before V5.1 is considered complete:

- [x] This design document exists at `docs/V5_TENANT_CREDENTIALS_AND_ONBOARDING_DESIGN.md`
- [x] `docs/ROADMAP.md` includes V5 as a planned milestone
- [x] Security principles are documented explicitly (Section 5)
- [x] Both onboarding modes are documented (Section 4)
- [x] Secret Manager is identified as the production target (Section 10)
- [x] Audit and memory policies are explicit (Section 12)
- [x] Threat model is documented (Section 13)
- [x] No source code files are modified
- [x] No secrets are added to any file

---

## 17. V5.2 Implementation Notes

**Branch:** `v5-tenant-credentials`

**Files added:**

```
agents/ads-agent/credentials/
  __init__.py       — public re-exports
  models.py         — CredentialReference dataclass, enums, all helpers

agents/ads-agent/run_credentials_model_demo.py   — standalone demo, 10 assertions
```

**What was implemented:**

- `CredentialStatus` enum: `missing`, `configured`, `invalid`, `validation_failed`, `active`, `revoked`
- `IntegrationType` enum: `google_ads`
- `CredentialReference` dataclass: tenant/client/integration metadata only; no secret fields
- `now_utc_iso()` — UTC ISO timestamp ending with `Z`
- `sanitize_identifier()` — lowercase, strip, replace unsafe chars, collapse hyphens
- `make_credential_ref()` — deterministic SHA-256-based opaque reference (`cred_google_ads_<12hex>`)
- `filter_safe_metadata()` — drops keys matching 9 secret-related substrings (case-insensitive)
- `create_credential_reference()` — creates sanitized, timestamped CredentialReference; filters metadata
- `credential_reference_to_dict()` — safe full dict, no secrets possible
- `credential_reference_to_redacted_response()` — API-safe response with `configured: bool`
- `validate_credential_reference()` — checks required fields, valid status, valid integration type, safe metadata
- `update_credential_status()` — returns new CredentialReference with updated status + timestamps; raises `ValueError` for invalid status

**What was NOT implemented (deferred to V5.3+):**

- Secret storage of any kind
- Endpoint creation
- Adapter integration
- Google Ads adapter changes
- OpenClaw changes

**Security validation:**

- Secret-safety grep over all new files: no output (clean)
- Metadata filtering verified: `refresh_token`, `client_secret`, `authorization`, `oauth_code`, `access_level` all dropped
- Redacted response verified: no secret values present in any output
- All existing smoke tests (V0–V4, 7 suites) pass with no changes

The following must be true before V5 is considered feature-complete (end of V5.10):

- [ ] Credentials never appear in API responses
- [ ] Credentials never appear in audit JSONL or MemPalace
- [ ] `CredentialStore` abstraction exists and is the sole credential access path
- [ ] Google Ads adapter retrieves credentials through the credential resolver, not `os.getenv()`
- [ ] Local dev path remains safe and frictionless
- [ ] GCP Secret Manager production path is documented and implementable
- [ ] OAuth connect flow is functional for Mode B

---

## 18. V5.3 Implementation Notes

**Branch:** `v5-tenant-credentials`

**Files added or modified:**

```
agents/ads-agent/credentials/
  store.py          — CredentialStore ABC, InMemoryCredentialStore, helpers (new)
  __init__.py       — re-exports updated to include store symbols

agents/ads-agent/run_credentials_store_demo.py   — standalone demo, 15 sections, all assertions pass
```

**What was implemented:**

- `make_store_key(tenant_id, client_id, integration_type)` — deterministic composite key `"tenant/client/type"`
- `missing_credential_status(tenant_id, client_id, integration_type)` — redacted status shape with `credential_ref: null`, `configured: false`
- `assert_no_secret_material(payload)` — recursive key-name scanner; returns `(True, [])` or `(False, [offending paths])`; checks 7 forbidden substrings: `token`, `secret`, `password`, `authorization`, `oauth_code`, `refresh`, `access`
- `CredentialStore` — abstract base class with 6 methods: `put_reference`, `get_reference`, `get_status`, `update_status`, `delete_reference`, `list_references`
- `InMemoryCredentialStore` — in-memory dict-backed implementation; stores `CredentialReference` copies only; all returned objects are deep copies

**Naming note:**

The term `CredentialStore` in V5.3 refers to the **credential reference metadata store** — it holds `CredentialReference` objects (tenant/client metadata pointers). This is the "Credential Reference Store" layer from the Section 3 architecture diagram. The **secret store** (the layer that holds raw secret values and will be implemented as `GCPSecretManagerStore` in V5.9) is a separate interface not yet defined. The `EnvCredentialStore` and `LocalFileCredentialStore` mentioned in Sections 3 and 10 are implementations of the secret store abstraction, deferred to V5.4+.

**What was NOT implemented (deferred to V5.4+):**

- Secret store abstraction (`EnvCredentialStore`, `GCPSecretManagerStore`)
- Disk persistence of any kind
- OpenClaw admin endpoints
- Google Ads adapter integration
- Frontend or onboarding UI

**Security validation:**

- Secret-safety grep over all new files: no output (clean)
- `put_reference` rejects any `CredentialReference` whose `metadata` contains secret-like keys (validated by both `validate_credential_reference` and `assert_no_secret_material`)
- All returned objects are `copy.deepcopy` copies — callers cannot mutate store state through returned values
- `missing_credential_status` always returns `credential_ref: null` and `configured: false` — no accidental data leakage for unconfigured tenants
- All existing smoke tests (V0–V4, 7 suites) pass with no changes

---

## Related Documents

- [V4 Real Integrations Design](V4_REAL_INTEGRATIONS_DESIGN.md)
- [Google Ads Live Integration Runbook](GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md)
- [GCP Deployment Plan](GCP_DEPLOYMENT_PLAN.md)
- [Environment Variables Reference](ENVIRONMENT_VARIABLES.md)
- [Roadmap](ROADMAP.md)

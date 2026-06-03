# Kaiju Command Center V5 Beta Release Notes

**Release name:** Kaiju Command Center V5 beta — Tenant Credentials & Secure Onboarding Foundation

**Branch:** `v5-tenant-credentials`

**Recommended tag:** `v5.0.0-beta`

---

## Overview

V5 establishes the full credential management foundation required to support multi-tenant Google Ads integrations securely. No credentials are stored in Git, returned in API responses, written to audit logs, or surfaced in MemPalace. The adapter continues to work without any credential setup when `GOOGLE_ADS_LIVE_ENABLED=false` (the default).

---

## What Is Included

### CredentialReference model (V5.2)

`CredentialReference` is the metadata record that identifies a tenant/client credential without holding any secret values. It carries `customer_id`, `login_customer_id`, `status`, and an opaque `credential_ref` hash pointer to the secret backend. Secret values (developer token, client secret, refresh token) are never stored here.

### CredentialStore abstraction (V5.3)

`CredentialStore` ABC defines the `put_reference` / `get_reference` / `get_status` interface. `InMemoryCredentialStore` provides a dev/test implementation. The abstraction decouples callers from any particular persistence backend.

### LocalFileCredentialReferenceStore (V5.4)

A JSON-backed `CredentialStore` that reads from and writes to the path set by `CREDENTIAL_REFERENCE_STORE_PATH`. Atomic JSON writes prevent partial writes. The runtime file path is gitignored.

### Admin GET credential status endpoint (V5.5)

`GET /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/status`

Returns the redacted `CredentialReference` status envelope. Never returns secret values. Auth applies when `OPENCLAW_API_AUTH_ENABLED=true`.

### Admin POST credential reference endpoint (V5.6)

`POST /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads`

Accepts only safe metadata fields: `customer_id`, `login_customer_id`, `status`, `metadata`. Recursively rejects any payload key matching secret-like patterns (`token`, `secret`, `password`, `refresh`, `oauth_code`, etc.). Returns `secret_material_rejected` on forbidden payload. Never accepts or stores raw credentials.

### Credential Resolver bridge (V5.7)

`resolve_credential_reference(tenant_id, client_id, integration_type, store=None)` resolves safe metadata from the credential store. Returns a `ResolvedCredentialReference` with no secret fields. `assert_resolved_reference_has_no_secret_material()` enforces this at test time.

### SecretStore abstraction (V5.8)

`SecretStore` ABC defines the secret bundle interface: `put_secret_bundle` / `get_secret_bundle` / `get_secret_status`. `InMemorySecretStore` provides a dev/test implementation — no disk writes, no persistence across restarts. `GOOGLE_ADS_SECRET_FIELDS` defines the allowed field set. `redact_secret_status` returns field presence booleans only.

### Google Ads CredentialProvider (V5.9)

`compose_google_ads_credentials(tenant_id, client_id, secret_store)` composes a complete `GoogleAdsCredentials` by combining `CredentialReference` metadata (resolves `customer_id`, `login_customer_id`) with a secret bundle (resolves `developer_token`, `client_id`, `client_secret`, `refresh_token`). The `credentials` field uses `field(repr=False)` to prevent accidental logging via `repr()`. `google_ads_provider_result_to_redacted_dict()` is the only safe output path.

### Adapter credential source feature flag (V5.10)

`GOOGLE_ADS_CREDENTIAL_SOURCE` controls how the Google Ads adapter loads credentials:

| Value | Behaviour |
|---|---|
| `env` (default) | Load from environment variables — existing path, unchanged |
| `provider` | Load via `compose_google_ads_credentials()`; requires `tenant_id` at call time |

`fetch_google_ads_metrics(client_id, request_type, tenant_id=None, secret_store=None)` — the two new optional parameters maintain full backward compatibility with all existing callers.

### V5 credential chain smoke test (V5.11)

`scripts/smoke_test_v5_credentials.sh` — 8-section end-to-end test covering imports, all credential demos, adapter provider mode, OpenClaw admin endpoints (including auth), and secret-safety grep. Requires no real credentials, no live API calls, and no Google OAuth setup.

---

## What Is Not Included

| Feature | Reason / Planned path |
|---|---|
| Frontend onboarding UI | Deferred — plan as `v5.12-frontend-onboarding` |
| OAuth connect flow | Deferred — requires Google OAuth consent screen submission |
| GCP Secret Manager backend | Deferred — plan as `v5.12-gcp-secret-manager` |
| Real credential upload/storage in production | No production secret backend exists yet |
| Live Google Ads validation through provider path | Requires production `SecretStore` backend |
| Billing / user management | Out of scope for V5 |
| Multi-region secret replication | Out of scope for V5 |

---

## Security Model

- **No credentials in Git.** The `LocalFileCredentialReferenceStore` runtime path is gitignored. No secret values appear in any committed file.
- **No credentials in API responses.** All admin endpoints return only redacted status shapes. `credential_ref` is an opaque hash, not a secret.
- **No credentials in audit log.** The OpenClaw audit JSONL records request/response envelopes; these never include secret values.
- **No credentials in MemPalace.** Agent memory records are filtered before write.
- **No secrets printed.** `field(repr=False)` on `GoogleAdsCredentialProviderResult.credentials`. All demo/test output paths use `redacted_google_ads_credentials()` or `google_ads_provider_result_to_redacted_dict()`.
- **Provider output is always redacted.** Raw credential objects never leave the composition layer.
- **Secret-key rejection is recursive.** Admin POST rejects any payload key matching forbidden substrings at any nesting level.

---

## Feature Flags

| Flag | Default | Purpose |
|---|---|---|
| `GOOGLE_ADS_LIVE_ENABLED` | `false` | Gates live Google Ads API calls |
| `GOOGLE_ADS_CREDENTIAL_SOURCE` | `env` | Selects env-var or provider credential loading |
| `OPENCLAW_API_AUTH_ENABLED` | `false` | Enables Bearer token auth on all endpoints |

---

## Smoke Tests

| Script | Coverage |
|---|---|
| `scripts/smoke_test_v5_credentials.sh` | Full V5 credential chain (new) |
| `scripts/smoke_test_v4_integrations.sh` | Integration resolver, Google Ads safety gates |
| `scripts/smoke_test_v3_openclaw_http.sh` | OpenClaw HTTP server, all endpoints |
| `scripts/smoke_test_v3_openclaw_audit.sh` | Audit log |
| `scripts/smoke_test_v3_openclaw.sh` | OpenClaw process layer |
| `scripts/smoke_test_v2_memory.sh` | MemPalace |
| `scripts/smoke_test_v1_graph.sh` | LangGraph Ads Agent |
| `scripts/smoke_test_v0.sh` | Router + legacy path |

All 8 suites pass on the `v5-tenant-credentials` branch.

---

## Recommended Next Branch Options

| Branch | Focus |
|---|---|
| `v5.12-frontend-onboarding` | Frontend credential submission UI; status page |
| `v5.12-gcp-secret-manager` | `GCPSecretManagerStore` production backend; Cloud Run IAM |

Either branch can proceed independently. `v5.12-gcp-secret-manager` unlocks live credential validation through the provider path. `v5.12-frontend-onboarding` unlocks self-serve tenant onboarding.

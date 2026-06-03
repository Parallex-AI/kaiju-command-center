# V5.12 GCP Secret Manager Backend — Design Document

**Branch:** `v5.12-gcp-secret-manager`  
**Base:** `v5.0.0-beta` / `d60b7ae`  
**Status:** Design only — no code, no dependencies, no runtime changes.

---

## 1. Purpose

V5.12 introduces `GCPSecretManagerStore` — a production-ready implementation of the `SecretStore` interface backed by [GCP Secret Manager](https://cloud.google.com/secret-manager). It replaces `InMemorySecretStore` in production deployments while leaving the existing interface, provider layer, adapter, and all smoke tests unchanged.

The implementation must preserve every security invariant already in place:

| Invariant | How preserved |
|---|---|
| No secrets in Git | Secret values never touch any committed file |
| No secrets in logs | `SecretRecord` carries only field presence booleans; raw bundle is never serialized |
| No secrets in audit | OpenClaw audit JSONL records envelopes only; no bundle is ever in scope |
| No secrets in MemPalace | Agent memory writes are filtered before reaching MemPalace |
| No secrets in API responses | All admin endpoints return redacted status shapes only |
| No secrets in demos or smoke tests | Demos use `InMemorySecretStore`; smoke tests require no GCP access |

---

## 2. Current Baseline

| Component | State |
|---|---|
| `SecretStore` ABC | Exists — `credentials/secret_store.py` |
| `InMemorySecretStore` | Exists — dev/test only, no disk writes |
| `SecretRecord` | Exists — redacted shape (field presence booleans, no values) |
| `GOOGLE_ADS_SECRET_FIELDS` | Exists — allowed field set for Google Ads bundles |
| `redact_secret_status` | Exists — converts a raw record into a safe output dict |
| `assert_allowed_secret_fields` | Exists — enforces field allowlist on write |
| `assert_no_secret_values_in_payload` | Exists — detects value leakage in demo/test output |
| Google Ads `CredentialProvider` | Exists — composes `GoogleAdsCredentials` from `CredentialReference` + `SecretStore` |
| Adapter provider mode | Exists — opt-in via `GOOGLE_ADS_CREDENTIAL_SOURCE=provider` |
| Production secret backend | **Does not exist** |

The `CredentialProvider` already accepts any `SecretStore` implementation. Wiring `GCPSecretManagerStore` requires no changes to the provider or adapter interfaces.

---

## 3. Target Architecture

```
OpenClaw Admin POST
  → LocalFileCredentialReferenceStore (metadata: customer_id, status, credential_ref)
  → credential_ref (opaque hash)
  → GCPSecretManagerStore (secret bundle: developer_token, client_id, client_secret, refresh_token)

At request time:
  Google Ads Adapter
    → compose_google_ads_credentials(tenant_id, client_id, secret_store=GCPSecretManagerStore())
      → resolve_credential_reference()      # reads metadata store
      → secret_store.get_secret_bundle()    # reads GCP Secret Manager
      → GoogleAdsCredentials (internal)
    → _do_live_fetch()
    → Google Ads API
```

**Key separation:** Secret Manager stores only secret bundles, keyed by `credential_ref`. The `LocalFileCredentialReferenceStore` (or future DB store) holds only non-secret metadata. Neither store has visibility into the other's data.

---

## 4. Secret Naming Convention

### Format

```
{prefix}-{env}-{integration_type}-{credential_ref}
```

### Example

```
kaiju-prod-google-ads-cred_google_ads_abcd1234ef56
```

### Rules

| Rule | Rationale |
|---|---|
| All lowercase | GCP secret names are case-sensitive; lowercase prevents collision |
| Only `[a-z0-9_-]` characters | GCP allows letters, digits, underscores, hyphens |
| Prefix from `GCP_SECRET_MANAGER_PREFIX` (default: `kaiju`) | Namespace isolation; enables per-prefix IAM |
| Env segment from `GCP_SECRET_MANAGER_ENV` | Separates dev/staging/prod in the same GCP project |
| Integration type segment (`google-ads`) | Allows future multi-integration support |
| `credential_ref` is the trailing segment | Opaque deterministic hash from `make_credential_ref()` — already stable and unique per tenant/client/type |
| No raw `tenant_id` in secret name | Avoids exposing business identity in Secret Manager metadata; `credential_ref` is sufficient for lookup |
| No raw `client_id` in secret name | Same reason; already embedded in `credential_ref` hash |
| No raw `customer_id` in secret name | `customer_id` is non-secret metadata; it lives in `CredentialReference`, not the secret name |

### Configuration

`GCP_SECRET_MANAGER_PREFIX` and `GCP_SECRET_MANAGER_ENV` are set per-deployment. The full secret name is computed at runtime by `GCPSecretManagerStore` and never stored in any file.

---

## 5. Secret Payload Format

### Stored JSON shape

```json
{
  "developer_token": "...",
  "client_id": "...",
  "client_secret": "...",
  "refresh_token": "..."
}
```

### Field clarification: `client_id` naming ambiguity

The word `client_id` is used in two distinct contexts in this codebase:

| Context | Meaning | Location |
|---|---|---|
| Business `client_id` | Tenant's advertiser identifier (e.g. `"acme"`) | `CredentialReference`, URL path params, OpenClaw request payload |
| OAuth `client_id` | Google OAuth 2.0 application credential | Secret bundle — this field |

The secret bundle field `client_id` always refers to the **OAuth application credential**. It is a string like `1234567890-xxxxxxxxxxxx.apps.googleusercontent.com`. It is a secret because it is used together with `client_secret` and `refresh_token` to obtain access tokens.

The business `client_id` (tenant's advertiser name) is **never** stored in the secret bundle.

### Explicitly excluded fields

| Field | Reason for exclusion |
|---|---|
| `customer_id` | Non-secret; stored in `CredentialReference` metadata |
| `login_customer_id` | Non-secret; stored in `CredentialReference` metadata |
| `tenant_id` | Routing metadata; never in secret bundle |
| Business `client_id` | Routing metadata; never in secret bundle |
| `access_token` | Short-lived; obtained at runtime via OAuth refresh, never stored |
| `oauth_code` | Single-use authorization code; never persisted after exchange |

---

## 6. Required Environment Variables

### Core flags

| Variable | Default | Description |
|---|---|---|
| `GCP_PROJECT_ID` | *(required when enabled)* | GCP project ID where secrets are stored |
| `GCP_SECRET_MANAGER_ENABLED` | `false` | Gates all GCP Secret Manager calls; `false` returns `gcp_secret_manager_disabled` |
| `GCP_SECRET_MANAGER_PREFIX` | `kaiju` | Name prefix for all managed secrets |
| `GCP_SECRET_MANAGER_ENV` | `local` | Deployment environment segment (`local`, `dev`, `staging`, `prod`) |
| `GCP_SECRET_MANAGER_LOCATION` | `global` | Optional; GCP Secret Manager region override |

### Credential source

| Variable | Required value for provider mode | Description |
|---|---|---|
| `GOOGLE_ADS_CREDENTIAL_SOURCE` | `provider` | Opts the adapter into provider mode |

### Local development

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Path to service account JSON key for local dev. **Must be outside the repo root.** Never committed. |

### Cloud Run (production)

Service account is attached to the Cloud Run service revision directly. `GOOGLE_APPLICATION_CREDENTIALS` is not used in production. Application Default Credentials (ADC) resolve automatically.

### Minimal local dev set (with emulator or real GCP)

```
GCP_PROJECT_ID=kaiju-dev
GCP_SECRET_MANAGER_ENABLED=true
GCP_SECRET_MANAGER_ENV=dev
GOOGLE_ADS_CREDENTIAL_SOURCE=provider
GOOGLE_APPLICATION_CREDENTIALS=/home/user/.gcp/kaiju-dev-sa.json  # outside repo
```

### Minimal production set (Cloud Run)

```
GCP_PROJECT_ID=kaiju-prod
GCP_SECRET_MANAGER_ENABLED=true
GCP_SECRET_MANAGER_ENV=prod
GCP_SECRET_MANAGER_PREFIX=kaiju
GOOGLE_ADS_CREDENTIAL_SOURCE=provider
# GOOGLE_APPLICATION_CREDENTIALS not needed — ADC from attached service account
```

---

## 7. IAM Model

### Principle: least privilege per environment

| Role | Binding target | When needed |
|---|---|---|
| `roles/secretmanager.secretAccessor` | Per-secret or per-prefix condition | Read path (`get_secret_bundle`) |
| `roles/secretmanager.secretVersionAdder` | Per-secret or per-prefix condition | Write path (`put_secret_bundle` — adds new versions) |
| `roles/secretmanager.secretCreator` | Per-prefix condition | Initial secret creation on first `put_secret_bundle` |
| `roles/secretmanager.secretVersionDestroyer` | Per-secret or per-prefix condition | Delete/disable path |
| `roles/secretmanager.admin` | **Never in production** | Dev/manual only |

### Service account strategy

| Environment | Service account | Permissions |
|---|---|---|
| `local` | Developer key or emulator | `secretAccessor` + `secretVersionAdder` on dev secrets only |
| `dev` | `kaiju-dev@<project>.iam.gserviceaccount.com` | `secretAccessor` + `secretVersionAdder` on `kaiju-dev-*` |
| `staging` | `kaiju-staging@<project>.iam.gserviceaccount.com` | `secretAccessor` + `secretVersionAdder` on `kaiju-staging-*` |
| `prod` | `kaiju-prod@<project>.iam.gserviceaccount.com` | `secretAccessor` only on `kaiju-prod-*`; write via separate admin SA |

### IAM condition (recommended)

Restrict each service account to secrets matching a resource name prefix condition:

```
resource.name.startsWith("projects/<project>/secrets/kaiju-prod-")
```

This ensures a prod service account cannot read dev secrets and vice versa.

### Cloud Run binding

Attach the service account to the Cloud Run service revision at deploy time:

```bash
gcloud run deploy kaiju-openclaw \
  --service-account kaiju-prod@<project>.iam.gserviceaccount.com \
  ...
```

No JSON key file is used in production.

---

## 8. SecretStore Interface Mapping

`GCPSecretManagerStore` must implement all five methods of the `SecretStore` ABC:

| Method | GCP Secret Manager operation | Notes |
|---|---|---|
| `put_secret_bundle(credential_ref, integration_type, secrets, metadata)` | `create_secret` (if new) + `add_secret_version` | Adds a new version; previous versions remain accessible per retention policy |
| `get_secret_bundle(credential_ref, integration_type)` | `access_secret_version` (latest) | Returns raw dict internally; **never serialized or logged** |
| `get_secret_status(credential_ref, integration_type)` | `get_secret` (metadata only) or `access_secret_version` with immediate redaction | Returns `SecretRecord` with field presence booleans only; if `access_secret_version` is called, the raw bundle is discarded immediately after field presence check |
| `delete_secret_bundle(credential_ref, integration_type)` | `destroy_secret_version` (latest) or `delete_secret` | See rotation/deletion notes below |
| `list_secret_records(integration_type, prefix)` | `list_secrets` with filter | May be prefix-filtered; returns `SecretRecord` list — no values |

### Notes on `get_secret_status`

Two implementation options:

**Option A — metadata-only (preferred if feasible):** Call `get_secret` to retrieve secret metadata (labels, create time, replication). Infer `configured_fields` from labels stored at `put_secret_bundle` time. No access to secret payload needed.

**Option B — payload-check (fallback):** Call `access_secret_version`, immediately check for key presence, discard payload without logging. This is the approach used by `InMemorySecretStore`.

Option A is preferred as it avoids the `secretAccessor` role for status checks. If labels are used to store field names, no secret version access is needed to confirm configuration.

### Notes on deletion

Two deletion behaviors:

- **Soft delete (preferred):** Destroy the latest version. The secret resource persists; history is preserved for audit. A new `put_secret_bundle` call can re-enable.
- **Hard delete:** Delete the secret resource entirely. Cannot be undone. Reserve for compliance-driven purge operations.

Default implementation uses soft delete (destroy latest version). Hard delete is a separate explicit operation.

---

## 9. Local Development Strategy

### Disabled mode (default)

When `GCP_SECRET_MANAGER_ENABLED=false`, `GCPSecretManagerStore` returns `gcp_secret_manager_disabled` errors without making any network call. This is the default for all local development and CI.

### Test isolation

All existing smoke tests use `InMemorySecretStore` directly and are unaffected by this feature. The V5 smoke test (`smoke_test_v5_credentials.sh`) requires no GCP access and continues to pass without modification.

### Development options

| Option | When to use |
|---|---|
| `InMemorySecretStore` | Unit tests, smoke tests, all automated CI |
| Real GCP project with dev service account | Manual integration testing against real Secret Manager |
| GCP Secret Manager emulator (`gcloud beta emulators secretmanager`) | Optional; allows integration tests without real GCP billing |

### Service account key location

If using a local service account JSON key, it **must** reside outside the repository root:

```
~/.gcp/kaiju-dev-sa.json       ✓  outside repo
~/kaiju/.gcp/kaiju-dev-sa.json ✗  inside repo — gitignored but risky
```

The `.gitignore` already excludes `*.json` in sensitive paths. As an added safeguard, `GCPSecretManagerStore` should log a warning (not an error) if `GOOGLE_APPLICATION_CREDENTIALS` points to a path inside the repo root.

---

## 10. Error Handling

All errors must be returned as structured dicts matching the `make_integration_error` shape. Raw GCP exception messages must be sanitized before surfacing.

| Error code | Trigger |
|---|---|
| `gcp_secret_manager_disabled` | `GCP_SECRET_MANAGER_ENABLED` is not `true` |
| `gcp_project_id_missing` | `GCP_PROJECT_ID` is unset or empty when enabled |
| `gcp_secret_not_found` | Secret resource does not exist (`NOT_FOUND` from GCP) |
| `gcp_secret_access_denied` | IAM permission denied (`PERMISSION_DENIED` from GCP) |
| `gcp_secret_write_failed` | `create_secret` or `add_secret_version` call failed |
| `gcp_secret_read_failed` | `access_secret_version` call failed for non-permission reason |
| `gcp_secret_payload_invalid` | Retrieved payload is not valid JSON or missing required fields |
| `gcp_secret_delete_failed` | Version destroy or secret delete call failed |
| `gcp_dependency_missing` | `google-cloud-secret-manager` library not installed |

### Sanitization rule

The raw GCP gRPC status message may contain the secret resource name (which itself contains `credential_ref`). Since `credential_ref` is an opaque hash (not a human-readable identifier), this is acceptable in error messages. However, any substring matching the secret payload value markers (`ya29`, `sk-`, known token prefixes) must be stripped before surfacing.

---

## 11. Dependency Plan

### Library

```
google-cloud-secret-manager>=2.20.0
```

### Policy

- The dependency is **not added** in V5.12.1 (this design step).
- It is added to `requirements.txt` in **V5.12.2** (config helpers step), pinned to a minimum version.
- The library is imported lazily inside `GCPSecretManagerStore` methods, guarded by a try/except that returns `gcp_dependency_missing` if absent. This preserves the existing environment where the library is not installed.
- Lazy import pattern matches the existing pattern in `google_ads_adapter.py` for the `google-ads` library.

### Example lazy import guard

```python
def _get_client(self):
    try:
        from google.cloud import secretmanager
        return secretmanager.SecretManagerServiceClient()
    except ImportError:
        raise RuntimeError("google-cloud-secret-manager is not installed")
```

---

## 12. Testing Strategy

### Automated (no GCP required)

| Test | What it covers |
|---|---|
| Existing `InMemorySecretStore` demo | All existing `SecretStore` interface behavior |
| Existing provider demo | Full credential composition without GCP |
| V5 smoke test `[5/8]` | Provider + SecretStore chain |
| `GCPSecretManagerStore` unit tests (V5.12.3+) | Disabled mode, missing project ID, dependency missing |

### Manual / integration (GCP required)

| Test | What it covers |
|---|---|
| Create a secret via `put_secret_bundle` | Write path, IAM, naming convention |
| Read status via `get_secret_status` | Status path, redaction |
| Retrieve bundle internally via `get_secret_bundle` | Read path, payload parsing |
| Compose credentials via `compose_google_ads_credentials` | End-to-end provider chain with real GCP |
| Destroy/disable latest version | Soft delete path |
| Verify `secretAccessor`-denied case | IAM isolation verification |

These tests are documented in a manual GCP smoke script (`V5.12.6`). They require explicit operator action and real credentials; they never run in CI.

### Non-goal for automated testing

Live Google Ads API calls remain gated behind `GOOGLE_ADS_LIVE_ENABLED=true` and are never triggered by automated tests.

---

## 13. Security Rules

The following are invariants, not guidelines. Any implementation that violates these is incorrect.

| Rule | Detail |
|---|---|
| Never print the secret payload | No `print()`, `logging.*`, `json.dumps()`, or `repr()` of a raw bundle |
| Never serialize the raw bundle | `get_secret_bundle()` returns a dict for internal use only; it is consumed immediately and discarded |
| Never return the raw bundle from OpenClaw | All admin endpoints return `SecretRecord` (presence booleans) only |
| Never write the payload to audit | OpenClaw audit JSONL records request/response envelopes; bundle never enters scope |
| Never write the payload to MemPalace | Agent memory writes are filtered before reaching MemPalace |
| Never commit service account JSON | `GOOGLE_APPLICATION_CREDENTIALS` must point outside the repo; CI uses Workload Identity |
| Repo `.gitignore` must cover key files | `*.json` in sensitive paths, `service_account*.json`, `.gcp/` — already in place |
| Rotate by adding versions | `put_secret_bundle` creates a new secret version; it does not edit or overwrite in place |
| Prefer Workload Identity in CI/CD | Avoid JSON key files in automated pipelines entirely |
| Log only secret names, never values | Any log statement may include the secret resource name (opaque); never the payload |

---

## 14. Rotation Strategy

GCP Secret Manager's versioning model maps naturally to the rotation workflow:

1. **Write a new bundle** — `put_secret_bundle` creates a new secret version. The previous version remains in GCP under its version number but is no longer the `latest`.
2. **Stable `credential_ref`** — The `credential_ref` hash does not change on rotation. Existing `CredentialReference` records remain valid.
3. **`SecretRecord.updated_at` changes** — The `SecretRecord` timestamp reflects when the latest version was written.
4. **Previous versions** — Managed by GCP's automatic replication and optional destroy policy. A retention policy can be set at the secret level to auto-destroy versions older than N days.
5. **Future admin endpoint** — A `POST .../credentials/google-ads/rotate` endpoint (not in V5.12 scope) would call `put_secret_bundle` with new values. It would never return or accept raw values.
6. **Emergency revocation** — Calling `delete_secret_bundle` destroys the latest version, rendering the `credential_ref` unusable until a new version is written. The `CredentialReference` is left intact (status changes to `revoked`).

---

## 15. Implementation Phases

| Phase | Milestone | Description |
|---|---|---|
| **V5.12.1** | Design | Design doc and ROADMAP update *(this document)* |
| **V5.12.2** | Config | Add `google-cloud-secret-manager` dependency · `GCPSecretManagerConfig` dataclass · env var parsing · `is_gcp_secret_manager_enabled()` helper · no live GCP calls |
| **V5.12.3** | Read/status | Implement `get_secret_bundle` and `get_secret_status` · disabled fallback · missing project ID guard · dependency guard · `gcp_secret_not_found` / `gcp_secret_access_denied` error codes |
| **V5.12.4** | Write | Implement `put_secret_bundle` — create secret + add version · `gcp_secret_write_failed` error code · secret naming helper |
| **V5.12.5** | Delete | Implement `delete_secret_bundle` — soft delete (destroy latest version) · `gcp_secret_delete_failed` error code |
| **V5.12.6** | Manual smoke | `scripts/manual_gcp_secret_manager_smoke.sh` — operator-run only, requires real GCP credentials · not part of CI |
| **V5.12.7** | Wiring | Wire `CredentialProvider` to accept `GCPSecretManagerStore` when enabled · update `compose_google_ads_credentials` call site · integration test with `InMemorySecretStore` remains the primary automated path |
| **V5.12.8** | Closure | Docs, `docs/V5_12_GCP_SECRET_MANAGER_DESIGN.md` implementation notes · ROADMAP update · `V5_BETA_RELEASE_NOTES.md` update · all smoke tests pass |

---

## 16. Non-Goals

The following are explicitly out of scope for V5.12:

- Frontend credential submission UI — deferred to `v5.12-frontend-onboarding`
- OAuth connect flow — requires Google OAuth consent screen submission
- Billing or subscription management
- User management (registration, login, password reset)
- Google Ads write access (V5.12 is read-only from the API perspective)
- Live Google Ads validation in automated tests — requires real credentials provided manually
- Multi-region secret replication — future concern
- Secret sharing between tenants

---

## 17. Acceptance Criteria for Design (V5.12.1)

- [x] Design document exists at `docs/V5_12_GCP_SECRET_MANAGER_DESIGN.md`
- [x] IAM model documented with least-privilege roles and environment separation
- [x] Secret naming convention documented with rationale for each rule
- [x] Secret payload format documented with explicit field exclusions and naming ambiguity resolved
- [x] All required environment variables documented with defaults
- [x] Local development strategy documented (disabled mode, emulator option, key location rules)
- [x] Error codes enumerated with triggers
- [x] Dependency noted as not yet added
- [x] Testing strategy covers both automated (no GCP) and manual (GCP required) paths
- [x] Security invariants stated explicitly
- [x] Rotation strategy documented
- [x] Implementation phases enumerated
- [x] No code changes in this step
- [x] No dependencies added
- [x] No secrets added
- [x] ROADMAP updated with V5.12 section

---

## Related Documents

- [V5 Tenant Credentials and Onboarding Design](V5_TENANT_CREDENTIALS_AND_ONBOARDING_DESIGN.md)
- [V5 Beta Release Notes](V5_BETA_RELEASE_NOTES.md)
- [GCP Deployment Plan](GCP_DEPLOYMENT_PLAN.md)
- [Environment Variables Reference](ENVIRONMENT_VARIABLES.md)
- [Roadmap](ROADMAP.md)

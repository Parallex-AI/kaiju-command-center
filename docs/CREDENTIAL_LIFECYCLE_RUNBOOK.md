# Credential Lifecycle Runbook

**Kaiju Command Center — V5.14 / V5.15 / V5.16**

This runbook documents the operator-facing procedures for managing Google Ads credentials through the OpenClaw admin API. It covers token setup, credential onboarding, validation, rotation, deletion, and audit maintenance. All curl examples use placeholder values only.

---

## 1. Purpose and Scope

This runbook covers the complete Google Ads credential lifecycle managed through the OpenClaw admin endpoints introduced in V5.14 through V5.16:

- V5.14 — credential bundle write (metadata reference + secret bundle)
- V5.15 — structural validation and delete/revoke
- V5.16 — token-scoped RBAC, audit hardening, and credential rotation

**In scope:** token setup, credential onboarding (metadata and bundle), structural validation, rotation, deletion, audit JSONL verification, audit pruning, rollback scenarios.

**Out of scope:** live Google Ads API validation (requires `GOOGLE_ADS_LIVE_ENABLED=true` — see `docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md`), GCP IAM setup (see `docs/GCP_SECRET_MANAGER_RUNBOOK.md`), Cloud Run deployment.

---

## 2. Hard Safety Rules

These rules apply to every operation in this runbook. Read them before proceeding.

1. **Never paste real secrets into any terminal session that is being observed, recorded, or shared.** This includes Claude, ChatGPT, Slack, GitHub Issues, and Zoom screenshares.
2. **Never commit `.env` files, service account JSON, or any file containing real credential values.** The `.gitignore` prevents this, but verify manually before every commit.
3. **Never log or return raw secret values.** All admin endpoints return redacted envelopes. If a response contains `developer_token`, `client_secret`, or `refresh_token` as non-empty values, treat it as a security incident.
4. **Keep `GOOGLE_ADS_LIVE_ENABLED=false` during all credential management operations.** The validate, rotate, and delete endpoints do not call the Google Ads API regardless of this flag. Live API testing is a separate, gated procedure.
5. **Never call `get_secret_bundle()` to verify a write.** Use `get_secret_status()` (field-presence booleans only) or the `/validate` endpoint. The admin API enforces this — no endpoint reads back secret values.
6. **`OPENCLAW_ADMIN_DELETE_ENABLED=true` must be set explicitly and intentionally.** The delete endpoint is disabled by default. Do not set this flag in a shared environment without approval.
7. **Rotate credentials immediately if there is any suspicion of exposure**, regardless of confirmed evidence. The `/rotate` endpoint replaces the bundle in-place without reading the prior version.
8. **GCP Secret Manager version note:** the `/rotate` endpoint writes a new secret version under the current abstraction. The prior GCP Secret Manager version remains enabled. Version destruction is not automatic — see `docs/GCP_SECRET_MANAGER_RUNBOOK.md` Section 13 for manual version lifecycle management.

---

## 3. Required Environment Variables

These 12 variables control the V5.14–V5.16 credential lifecycle. All must be reviewed before any credential operation.

| Variable | Default | Secret | Purpose |
|---|---|---|---|
| `OPENCLAW_API_AUTH_ENABLED` | `false` | No | Enable Bearer token enforcement on all admin endpoints |
| `OPENCLAW_ADMIN_KEYS` | `` | **Yes** | Comma-separated admin-scope tokens — grants all operations (ADMIN scope) |
| `OPENCLAW_READ_KEYS` | `` | **Yes** | Comma-separated read-only tokens — grants status check only (READ scope) |
| `OPENCLAW_API_KEYS` | `` | **Yes** | Backward-compat API keys — treated as READ scope; cannot perform WRITE/VALIDATE/ROTATE/DELETE |
| `OPENCLAW_ADMIN_DELETE_ENABLED` | `false` | No | Enable the DELETE endpoint — disabled by default; must be set explicitly |
| `OPENCLAW_TENANT_KEYS` | `` | No | Per-token tenant allow-list: `token-a:tenant-a,token-a:tenant-b,token-b:tenant-c`. Unset = no restriction. See Section 3a. |
| `OPENCLAW_AUDIT_ENABLED` | `true` | No | Enable append-only JSONL audit log writes |
| `OPENCLAW_AUDIT_ROOT` | `openclaw/audit` | No | Directory for audit JSONL files |
| `OPENCLAW_AUDIT_RETAIN_DAYS` | `90` | No | Days to retain audit files before pruning |
| `GCP_SECRET_MANAGER_ENABLED` | `false` | No | Enable GCPSecretManagerStore; when false, InMemorySecretStore is used |
| `GCP_PROJECT_ID` | `` | No | GCP project for Secret Manager API calls; required when GCP_SECRET_MANAGER_ENABLED=true |
| `GCP_SECRET_MANAGER_ENV` | `local` | No | Environment segment in GCP secret names (`local`, `dev`, `staging`, `prod`) |
| `GOOGLE_ADS_LIVE_ENABLED` | `false` | No | Gate for live Google Ads API calls — keep false during all credential management |

**Local `.env` minimum for testing with InMemorySecretStore (no GCP required):**

```
OPENCLAW_API_AUTH_ENABLED=true
OPENCLAW_ADMIN_KEYS=<ADMIN_TOKEN>
OPENCLAW_READ_KEYS=<READ_TOKEN>
OPENCLAW_AUDIT_ENABLED=true
GCP_SECRET_MANAGER_ENABLED=false
GOOGLE_ADS_LIVE_ENABLED=false
```

Replace `<ADMIN_TOKEN>` and `<READ_TOKEN>` with long random strings generated locally. Never use these examples verbatim.

---

## 4. Token Setup

### Generating tokens

Admin and read tokens are arbitrary opaque strings. Generate them with sufficient entropy:

```bash
# 32-byte URL-safe random token (placeholder command)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

The output is the token value. Store it in your secret manager or `.env` file. Never commit it.

### Token scopes (V5.16)

| Token type | Env var | Scope | Permitted operations |
|---|---|---|---|
| Admin | `OPENCLAW_ADMIN_KEYS` | `ADMIN` | All: status, write, validate, rotate, delete |
| Read-only | `OPENCLAW_READ_KEYS` | `READ` | Status check only |
| API key (backward compat) | `OPENCLAW_API_KEYS` | `READ` | Status check only |

**Scope resolution priority:** `OPENCLAW_ADMIN_KEYS` → `OPENCLAW_READ_KEYS` → `OPENCLAW_API_KEYS`. The first match wins.

The `ADMIN` scope satisfies any minimum-scope requirement. The `READ` scope satisfies only `READ`-gated endpoints. Attempting a write, validate, rotate, or delete with a `READ`-scoped token returns `403 scope_not_granted`.

### Using tokens in requests

All admin endpoints expect an `Authorization: Bearer <token>` header:

```bash
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  http://localhost:8100/openclaw/admin/tenants/<TENANT_ID>/clients/<CLIENT_ID>/credentials/google-ads/status
```

### Section 3a. Tenant-scoped tokens (V5.17)

`OPENCLAW_TENANT_KEYS` restricts individual tokens to specific tenant IDs. Format:

```
OPENCLAW_TENANT_KEYS=<token-a>:<tenant-a>,<token-a>:<tenant-b>,<token-b>:<tenant-c>
```

**Rules:**

| Condition | Behavior |
|---|---|
| `OPENCLAW_TENANT_KEYS` unset or empty | No restriction — all tokens may access all tenants |
| Token not listed in the map | Global access (backward compatible) |
| Token listed, `tenant_id` in its set | Access allowed |
| Token listed, `tenant_id` not in its set | 403 `tenant_access_denied` |

Tenant access is always checked **after** scope succeeds. An invalid token returns 401
`unauthorized`; an insufficient-scope token returns 403 `scope_not_granted`. Neither
reaches the tenant check.

See `docs/V5_17_PER_TENANT_PERMISSION_DESIGN.md` for the full design, backward
compatibility rules, error model, and planned future IAM/OAuth path.

### Rotating tokens

To rotate a token:
1. Add the new value to `OPENCLAW_ADMIN_KEYS` or `OPENCLAW_READ_KEYS` alongside the old value (comma-separated).
2. Redeploy or restart the service.
3. Verify that requests using the new token succeed.
4. Remove the old value and redeploy.

Never log token values. Never include tokens in error messages, audit events, or response bodies.

---

## 5. Endpoint Summary

All admin endpoints follow the path pattern: `/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads[/suffix]`

| Method | Path suffix | Minimum scope | HTTP on success | Notes |
|---|---|---|---|---|
| `GET` | `/status` | `READ` | `200` | Read-only metadata; never returns secret values |
| `POST` | `` | `WRITE` | `200` | Metadata upsert or full bundle write (auto-detected by payload) |
| `POST` | `/validate` | `VALIDATE` | `200` | Structural validation — `get_secret_status()` only; no Google Ads API call |
| `POST` | `/rotate` | `ROTATE` | `200` | Replace secret bundle; status must not be REVOKED |
| `DELETE` | `` | `DELETE` | `200` | Revoke and delete; also requires `OPENCLAW_ADMIN_DELETE_ENABLED=true` |

Auth failures:
- Missing or invalid token → `401 unauthorized`
- Valid token with insufficient scope → `403 scope_not_granted`
- Auth enabled but no keys configured → `401 auth_not_configured`

---

## 6. Status Check

**Endpoint:** `GET /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/status`
**Minimum scope:** READ

Returns the redacted `CredentialReference` status. Never returns secret values.

```bash
curl -X GET \
  "http://localhost:8100/openclaw/admin/tenants/<TENANT_ID>/clients/<CLIENT_ID>/credentials/google-ads/status" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Example response (no credential exists yet):**

```json
{
  "ok": true,
  "tenant_id": "<TENANT_ID>",
  "client_id": "<CLIENT_ID>",
  "integration_type": "google_ads",
  "credential_status": {
    "exists": false,
    "status": null,
    "configured": false
  },
  "errors": []
}
```

**Example response (credential exists):**

```json
{
  "ok": true,
  "tenant_id": "<TENANT_ID>",
  "client_id": "<CLIENT_ID>",
  "integration_type": "google_ads",
  "credential_status": {
    "exists": true,
    "status": "active",
    "configured": true,
    "last_validated_at": "2026-01-01T00:00:00Z"
  },
  "errors": []
}
```

**Status values and meanings:**

| Status | Meaning |
|---|---|
| `configured` | CredentialReference created; bundle may or may not be written |
| `active` | All four secret fields present and structurally complete |
| `validation_failed` | CredentialReference exists but one or more secret fields are missing |
| `revoked` | Credential has been deleted; rotation is not permitted |

The response never includes `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, or any secret values.

---

## 7. Metadata Write (No Secrets)

**Endpoint:** `POST /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads`
**Minimum scope:** WRITE

Use this path to create or update a `CredentialReference` without providing secret material. Useful for recording `customer_id` before the secret bundle is available.

The endpoint routes automatically: if the payload contains any of the four secret field names (`developer_token`, `client_id` [OAuth], `client_secret`, `refresh_token`), it is treated as a bundle write (see Section 8). Otherwise it is a metadata-only upsert.

```bash
curl -X POST \
  "http://localhost:8100/openclaw/admin/tenants/<TENANT_ID>/clients/<CLIENT_ID>/credentials/google-ads" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "1234567890"}'
```

**Accepted metadata fields:** `customer_id`, `login_customer_id`, `status`, `metadata`

**Rejected fields:** any key name containing `token`, `secret`, `password`, `authorization`, `auth_header`, `oauth_code`, `refresh`, or `access` — rejected with `400 secret_material_rejected`.

If the `CredentialReference` already exists, the call updates only the provided fields and preserves all others (upsert semantics). `credential_ref` is never modified.

---

## 8. Bundle Write (All Four Secret Fields)

**Endpoint:** `POST /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads`
**Minimum scope:** WRITE

Submitting all four secret fields in the payload triggers the bundle write path. The endpoint writes metadata to `LocalFileCredentialReferenceStore` and secret material to the configured `SecretStore` (`InMemorySecretStore` locally, `GCPSecretManagerStore` in production).

**All four secret fields are required.** A partial bundle is rejected with `400 secret_bundle_incomplete` and no write occurs.

```bash
curl -X POST \
  "http://localhost:8100/openclaw/admin/tenants/<TENANT_ID>/clients/<CLIENT_ID>/credentials/google-ads" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_token": "<FAKE_DEVELOPER_TOKEN>",
    "client_id": "<FAKE_GOOGLE_CLIENT_ID>",
    "client_secret": "<FAKE_GOOGLE_CLIENT_SECRET>",
    "refresh_token": "<FAKE_REFRESH_TOKEN>",
    "customer_id": "1234567890"
  }'
```

Replace all `<FAKE_*>` placeholders with your actual credential values when working with real credentials in a secure terminal. Never paste real values into any shared session.

**Example success response:**

```json
{
  "ok": true,
  "tenant_id": "<TENANT_ID>",
  "client_id": "<CLIENT_ID>",
  "integration_type": "google_ads",
  "credential_status": {
    "exists": true,
    "status": "configured",
    "configured": true
  },
  "secret_status": {
    "configured": true,
    "configured_fields": {
      "developer_token": true,
      "client_id": true,
      "client_secret": true,
      "refresh_token": true
    }
  },
  "errors": []
}
```

The response contains field-presence booleans only — no secret values. After writing, run structural validation (Section 9) to confirm all fields are present.

---

## 9. Structural Validation

**Endpoint:** `POST /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/validate`
**Minimum scope:** VALIDATE

Checks whether all four required secret fields are configured in the `SecretStore`. Uses `get_secret_status()` (field-presence booleans) only. Does **not** call the Google Ads API. Does **not** read secret values (`get_secret_bundle()` is never called on this path).

Updates `CredentialReference` status to `active` (all fields present) or `validation_failed` (any missing). Emits an audit event with `operation="validate"`.

```bash
curl -X POST \
  "http://localhost:8100/openclaw/admin/tenants/<TENANT_ID>/clients/<CLIENT_ID>/credentials/google-ads/validate" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Example success response (structurally complete):**

```json
{
  "ok": true,
  "tenant_id": "<TENANT_ID>",
  "client_id": "<CLIENT_ID>",
  "integration_type": "google_ads",
  "validation_result": {
    "structurally_complete": true,
    "missing_fields": [],
    "last_validated_at": "2026-01-01T00:00:00Z",
    "live_api_tested": false
  },
  "credential_status": {
    "exists": true,
    "status": "active",
    "configured": true,
    "last_validated_at": "2026-01-01T00:00:00Z"
  },
  "secret_status": {
    "configured": true,
    "configured_fields": {
      "developer_token": true,
      "client_id": true,
      "client_secret": true,
      "refresh_token": true
    }
  },
  "errors": []
}
```

`live_api_tested` is always `false` for this endpoint. Live API validation is a separate procedure gated by `GOOGLE_ADS_LIVE_ENABLED=true`.

Returns `404` when no `CredentialReference` exists. Returns `200` in all other cases, even when `structurally_complete=false` — the operation ran; the result reflects the completeness check.

---

## 10. Credential Rotation

**Endpoint:** `POST /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/rotate`
**Minimum scope:** ROTATE

Replaces the stored secret bundle for an existing `CredentialReference`. Requires all four secret fields. Uses `put_secret_bundle()` only — `get_secret_bundle()` is never called on this path. Validates structurally via `get_secret_status()` after the write. Emits an audit event with `operation="rotate"`.

**Permitted current statuses:** `active`, `configured`, `validation_failed`
**Rejected status:** `revoked` → `409 invalid_status_for_rotation` (create a new credential instead)

```bash
curl -X POST \
  "http://localhost:8100/openclaw/admin/tenants/<TENANT_ID>/clients/<CLIENT_ID>/credentials/google-ads/rotate" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_token": "<FAKE_DEVELOPER_TOKEN>",
    "client_id": "<FAKE_GOOGLE_CLIENT_ID>",
    "client_secret": "<FAKE_GOOGLE_CLIENT_SECRET>",
    "refresh_token": "<FAKE_REFRESH_TOKEN>"
  }'
```

**Example success response:**

```json
{
  "ok": true,
  "tenant_id": "<TENANT_ID>",
  "client_id": "<CLIENT_ID>",
  "integration_type": "google_ads",
  "rotation_result": {
    "structurally_complete": true,
    "missing_fields": [],
    "last_validated_at": "2026-01-01T00:00:00Z"
  },
  "credential_status": {
    "exists": true,
    "status": "active",
    "configured": true,
    "last_validated_at": "2026-01-01T00:00:00Z"
  },
  "secret_status": {
    "configured": true,
    "configured_fields": {
      "developer_token": true,
      "client_id": true,
      "client_secret": true,
      "refresh_token": true
    }
  },
  "errors": []
}
```

**GCP Secret Manager version note:** rotation writes a new secret version via `put_secret_bundle()`. The prior GCP Secret Manager version remains enabled — it is not automatically disabled or destroyed. To enforce version lifecycle policies (e.g., disable prior version after rotation), use `gcloud secrets versions disable` manually after confirming the new version is active. A configurable version destruction policy is planned for a future milestone.

After rotation, run structural validation (Section 9) to confirm the new bundle is complete.

---

## 11. Delete and Revoke

**Endpoint:** `DELETE /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads`
**Minimum scope:** DELETE
**Additional gate:** `OPENCLAW_ADMIN_DELETE_ENABLED=true` must be set

Deletes the secret bundle and marks the `CredentialReference` as `revoked`. Idempotent on already-absent secrets (returns `200` with `warnings: ["secret_already_absent"]`). Once revoked, the credential cannot be rotated — a new bundle write must be performed instead. Emits an audit event with `operation="delete"`.

**This operation is irreversible within the current secret version.** If `GCPSecretManagerStore` is active and the prior secret version has not been disabled, the raw GCP secret version may still exist in Secret Manager until explicitly destroyed.

```bash
# Set the delete gate first (do not leave this enabled in shared environments)
export OPENCLAW_ADMIN_DELETE_ENABLED=true

curl -X DELETE \
  "http://localhost:8100/openclaw/admin/tenants/<TENANT_ID>/clients/<CLIENT_ID>/credentials/google-ads" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Example success response:**

```json
{
  "ok": true,
  "tenant_id": "<TENANT_ID>",
  "client_id": "<CLIENT_ID>",
  "integration_type": "google_ads",
  "credential_status": {
    "exists": true,
    "status": "revoked",
    "configured": false
  },
  "secret_status": {
    "configured": false,
    "configured_fields": {
      "developer_token": false,
      "client_id": false,
      "client_secret": false,
      "refresh_token": false
    }
  },
  "warnings": [],
  "errors": []
}
```

Returns `403 delete_not_enabled` if `OPENCLAW_ADMIN_DELETE_ENABLED` is not `true`. Returns `404 credential_not_found` if no `CredentialReference` exists.

---

## 12. Audit Verification

Audit events are written to append-only JSONL files under `OPENCLAW_AUDIT_ROOT` (default: `openclaw/audit/`). Each file is named `YYYY-MM-DD.jsonl`.

### Audit event fields (credential operations)

Every credential operation appends one event per action. Safe fields present in every event:

| Field | Description |
|---|---|
| `timestamp` | ISO 8601 UTC timestamp |
| `event_type` | `"credential_operation"` |
| `tenant_id` | Tenant identifier |
| `client_id` | Client identifier |
| `integration_type` | `"google_ads"` |
| `operation` | One of: `metadata_upsert`, `bundle_write`, `validate`, `rotate`, `delete` |
| `ok` | `true` if the operation completed successfully |
| `error_codes` | List of error code strings (empty on success) |
| `request_id` | Propagated from `X-Request-Id` header or generated |
| `trace_id` | Propagated from `X-Trace-Id` header or generated |
| `seq` | 1-based integer sequence number within the file |
| `file_digest` | SHA-256 hex digest of file bytes before this append |
| `source` | `"openclaw_admin"` |

### Fields deliberately excluded from audit events

The following fields are **never** included in any audit event, by design:

- `credential_ref` — internal opaque identifier
- `secret_id` — GCP Secret Manager secret name
- `customer_id` — tenant-sensitive metadata
- `login_customer_id` — tenant-sensitive metadata
- `developer_token` — secret value
- `client_secret` — secret value
- `refresh_token` — secret value
- `access_token` — ephemeral, never stored

### Verifying audit file integrity

`verify_audit_file()` in `openclaw/audit_maintenance.py` replays the `seq` sequence and `file_digest` chain to detect tampered or out-of-order events.

```python
from openclaw.audit_maintenance import verify_audit_file

result = verify_audit_file("openclaw/audit/2026-01-01.jsonl")
# result = {
#   "ok": True,
#   "events_checked": 12,
#   "errors": [],
#   "warnings": []
# }
```

Possible error strings:
- `"file_not_found"` — file does not exist
- `"invalid_json:lineN"` — line N is not valid JSON
- `"seq_mismatch:lineN:expectedE:gotA"` — sequence number mismatch
- `"digest_mismatch:lineN"` — digest does not match accumulated bytes

**Known limitation:** `seq` and `file_digest` are computed outside any file lock. In environments with concurrent audit writers (e.g., multiple server processes), sequence collisions are possible. This is a known gap targeted for V5.17 Phase 5.

---

## 13. Audit Pruning

`prune_audit_files()` in `openclaw/audit_maintenance.py` deletes `.jsonl` files in the audit root whose file modification time is older than `retain_days` days.

```python
from openclaw.audit_maintenance import prune_audit_files

result = prune_audit_files(root="openclaw/audit", retain_days=90)
# result = {
#   "ok": True,
#   "deleted_count": 3,
#   "kept_count": 87,
#   "errors": []
# }
```

`OPENCLAW_AUDIT_RETAIN_DAYS` (default `90`) controls the default retention period. Set it lower for shorter retention windows; set it higher for longer ones.

**Before pruning in production:**
- Verify that the audit files to be pruned have been archived or replicated to a durable store (e.g., Cloud Storage, BigQuery) if required for compliance.
- A future milestone will add a Cloud Logging or BigQuery sink. Until then, pruning permanently deletes local JSONL files.
- Cloud Run ephemeral filesystems mean audit files do not survive container restarts regardless of retention policy — plan accordingly.

---

## 14. Rollback and Recovery

### Scenario: Incorrect bundle written

**Situation:** bundle written with wrong credentials; need to correct.

**Recovery:** Run the `/rotate` endpoint with the correct credential values. The new bundle overwrites the prior version. Status updates to `active` after structural validation.

### Scenario: Credentials suspected exposed

**Situation:** a token value may have been logged, shared, or observed.

**Recovery:**
1. Immediately obtain new credentials from the Google Ads API console.
2. Run `/rotate` with the new bundle. Do this before disabling old credentials to avoid a service interruption.
3. Disable or destroy the prior GCP Secret Manager secret version manually (see GCP Secret Manager Runbook Section 13).
4. Rotate any `OPENCLAW_ADMIN_KEYS` tokens that may have been observed.

### Scenario: Credential in `validation_failed` state

**Situation:** structural validation returned `structurally_complete=false` with missing fields.

**Recovery:** Run the POST bundle write endpoint with all four required fields. Then re-run `/validate` to confirm `active` status. If using `GCPSecretManagerStore`, confirm the secret exists in GCP before re-validating.

### Scenario: Accidental delete (REVOKED status)

**Situation:** credential was deleted and marked REVOKED; rotation is now rejected.

**Recovery:** Create a new bundle write via the POST endpoint. This creates a new `CredentialReference` or re-uses the existing one depending on store behavior. Run `/validate` afterward to confirm.

### Scenario: Secret store unavailable (InMemorySecretStore cleared on restart)

**Situation:** the service restarted and `InMemorySecretStore` was cleared; all in-memory secrets are gone; `CredentialReference` metadata still exists in the local file store.

**Recovery:** Re-submit the bundle write. The `CredentialReference` metadata is preserved (upsert semantics). Run `/validate` to confirm `active` status.

### Scenario: Auth misconfiguration (`auth_not_configured`)

**Situation:** `OPENCLAW_API_AUTH_ENABLED=true` but no keys are configured.

**Recovery:** Set `OPENCLAW_ADMIN_KEYS` and restart. All requests fail with `auth_not_configured` until at least one key list is populated.

### Scenario: GCP Secret Manager unavailable

**Situation:** `GCPSecretManagerStore` is enabled but GCP returns errors.

**Recovery:**
1. Check GCP project ID and IAM bindings (see GCP Secret Manager Runbook Section 15).
2. If the issue cannot be resolved quickly, set `GCP_SECRET_MANAGER_ENABLED=false` to fall back to `InMemorySecretStore`. Secrets in GCP Secret Manager are unaffected and available for re-enablement.

---

## 15. Error Handling Guide

| Error code | HTTP status | Endpoint | Cause | Action |
|---|---|---|---|---|
| `unauthorized` | 401 | All | Missing or invalid Bearer token | Provide a valid token from `OPENCLAW_ADMIN_KEYS` or other key lists |
| `auth_not_configured` | 401 | All | Auth enabled but no keys configured | Set at least one of `OPENCLAW_ADMIN_KEYS`, `OPENCLAW_READ_KEYS`, or `OPENCLAW_API_KEYS` |
| `scope_not_granted` | 403 | All | Valid token but insufficient scope | Use a token from `OPENCLAW_ADMIN_KEYS` for WRITE/VALIDATE/ROTATE/DELETE operations |
| `delete_not_enabled` | 403 | DELETE | `OPENCLAW_ADMIN_DELETE_ENABLED` not `true` | Set `OPENCLAW_ADMIN_DELETE_ENABLED=true` and restart the service |
| `credential_not_found` | 404 | validate, rotate, delete | No `CredentialReference` for this tenant/client | Run the POST bundle write first |
| `invalid_request` | 400 | POST, rotate | Missing or empty request body | Include all required fields in the request body |
| `secret_bundle_incomplete` | 400 | POST, rotate | One or more of the four secret fields missing | Provide all four: `developer_token`, `client_id`, `client_secret`, `refresh_token` |
| `secret_material_rejected` | 400 | POST (metadata path) | Payload contains a forbidden secret-like key name | Remove keys containing `token`, `secret`, `password`, `authorization`, `refresh`, `access` |
| `invalid_status_for_rotation` | 409 | rotate | Credential status is `revoked` | Create a new bundle write instead of rotating |
| `invalid_json` | 400 | POST, rotate | Request body is not valid JSON | Validate JSON syntax before sending |
| `credential_store_failed` | 400/500 | All | LocalFileCredentialReferenceStore read/write failed | Check `CREDENTIAL_REFERENCE_STORE_PATH` configuration and file permissions |
| `secret_write_failed` | 400 | POST (bundle), rotate | `put_secret_bundle()` raised an exception | Check SecretStore configuration; check GCP IAM bindings if using GCPSecretManagerStore |
| `secret_delete_failed` | 400 | DELETE | `delete_secret_bundle()` raised an exception | Check SecretStore configuration; check GCP IAM bindings |
| `credential_status_failed` | 400 | GET status | Store read failed during status lookup | Check store configuration |
| `audit_append_failed` | warning only | All write paths | Audit JSONL write failed | Check `OPENCLAW_AUDIT_ROOT` path and file permissions; credential operation itself was not affected |

---

## 16. Fake-Secret Rehearsal Checklist

Run this checklist using fake placeholder values before working with real credentials. This exercises the full lifecycle against a running service with `InMemorySecretStore`.

```
Pre-conditions:
  [ ] Service is running locally (uvicorn or python -m openclaw.server)
  [ ] OPENCLAW_API_AUTH_ENABLED=true
  [ ] OPENCLAW_ADMIN_KEYS set to a local test token
  [ ] GCP_SECRET_MANAGER_ENABLED=false
  [ ] GOOGLE_ADS_LIVE_ENABLED=false

Rehearsal steps:
  [ ] 1. GET /status — confirms no credential exists (exists: false)
  [ ] 2. POST metadata-only — confirms CredentialReference created (status: configured)
  [ ] 3. GET /status — confirms credential exists (exists: true, status: configured)
  [ ] 4. POST /validate — expects validation_failed (bundle not yet written)
  [ ] 5. POST bundle write — all four FAKE fields, expects ok: true
  [ ] 6. GET /status — confirms configured: true
  [ ] 7. POST /validate — expects structurally_complete: true, status: active
  [ ] 8. POST /rotate — all four new FAKE fields, expects ok: true
  [ ] 9. POST /validate — confirms active status after rotation
  [ ] 10. POST /rotate with incomplete payload (omit one field) — expects 400 secret_bundle_incomplete
  [ ] 11. Enable OPENCLAW_ADMIN_DELETE_ENABLED=true
  [ ] 12. DELETE — expects ok: true, status: revoked
  [ ] 13. POST /rotate on revoked — expects 409 invalid_status_for_rotation
  [ ] 14. GET /status — confirms status: revoked
  [ ] 15. Check audit JSONL — confirm events present; run verify_audit_file(); expect ok: true
  [ ] 16. Disable OPENCLAW_ADMIN_DELETE_ENABLED

  All steps passed: rehearsal complete.
  No real credentials were used.
```

---

## 17. Pre-Real-Onboarding Checklist

This checklist is a **gate**, not an instruction set. Every item must be verified and confirmed before any real Google Ads OAuth credentials are submitted to any environment.

```
Security posture:
  [ ] All fake-secret rehearsal steps (Section 16) passed on the target environment
  [ ] GOOGLE_ADS_LIVE_ENABLED=false confirmed in target environment
  [ ] OPENCLAW_API_AUTH_ENABLED=true confirmed in target environment
  [ ] OPENCLAW_ADMIN_KEYS contains only long, randomly generated tokens
  [ ] No real credentials in any .env file tracked by Git
  [ ] No real credentials in any chat session, issue tracker, or PR description
  [ ] GCP Secret Manager (if active): IAM bindings scoped to kaiju-{env}- prefix
  [ ] GCP Secret Manager (if active): no Owner/Editor/Admin role on Cloud Run SA

Operational readiness:
  [ ] Credential rotation plan documented and understood by operating team
  [ ] OPENCLAW_AUDIT_ENABLED=true confirmed
  [ ] Audit file durability plan confirmed (ephemeral container filesystem risk acknowledged)
  [ ] OPENCLAW_ADMIN_DELETE_ENABLED default (false) confirmed in production

Approvals:
  [ ] Operator has reviewed GCP Secret Manager Runbook Section 7 (IAM Model)
  [ ] Operator has reviewed docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md
  [ ] Live credential submission will be performed from a secure, unobserved terminal
  [ ] A rollback plan is ready (Section 14 of this runbook)

Only proceed with real credential onboarding when all boxes above are checked.
```

---

## 18. Related Documents

| Document | Purpose |
|---|---|
| [docs/GCP_SECRET_MANAGER_RUNBOOK.md](GCP_SECRET_MANAGER_RUNBOOK.md) | IAM setup, secret naming convention, GCP configuration, secret rotation (version management), failure modes |
| [docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md](GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md) | OAuth2 credential setup, GAQL queries, live adapter test plan |
| [docs/ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) | Complete environment variable reference |
| [docs/V5_16_BRANCH_CLOSURE.md](V5_16_BRANCH_CLOSURE.md) | V5.16 implementation summary: RBAC, audit hardening, rotation endpoint |
| [docs/V5_15_BRANCH_CLOSURE.md](V5_15_BRANCH_CLOSURE.md) | V5.15 implementation summary: validate, delete, audit events |
| [docs/V5_12_GCP_SECRET_MANAGER_DESIGN.md](V5_12_GCP_SECRET_MANAGER_DESIGN.md) | Full design specification for GCPSecretManagerStore |
| [docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md](V5_17_LIVE_GCP_VALIDATION_PLAN.md) | Operator-run fake-secret lifecycle validation plan: write → validate → rotate → delete through GCPSecretManagerStore |
| [docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md](V5_17_LIVE_GCP_VALIDATION_RESULTS.md) | Results template for V5.17 live GCP validation — fill in after operator-run execution |
| [docs/ROADMAP.md](ROADMAP.md) | V5.17 and beyond: per-tenant isolation, audit locking, live GCP validation plan |
| [openclaw/audit_maintenance.py](../openclaw/audit_maintenance.py) | `verify_audit_file()` and `prune_audit_files()` implementation |
| [openclaw/admin.py](../openclaw/admin.py) | All credential lifecycle function implementations |
| [openclaw/auth.py](../openclaw/auth.py) | Token-scoped RBAC: `AdminScope`, `resolve_token_scope()`, `validate_api_auth()`, `validate_tenant_access()` |
| [docs/V5_17_PER_TENANT_PERMISSION_DESIGN.md](V5_17_PER_TENANT_PERMISSION_DESIGN.md) | V5.17 Phase 3 design: `OPENCLAW_TENANT_KEYS` format, request evaluation order, backward compat, future IAM path |

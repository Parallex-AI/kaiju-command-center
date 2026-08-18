# Credential Lifecycle Runbook

**Kaiju Command Center — V5.14 / V5.15 / V5.16 / V5.17 / V5.19**

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

These 14 variables control the V5.14–V5.17 credential lifecycle. All must be reviewed before any credential operation.

| Variable | Default | Secret | Purpose |
|---|---|---|---|
| `OPENCLAW_API_AUTH_ENABLED` | `false` | No | Enable Bearer token enforcement on all admin endpoints |
| `OPENCLAW_ADMIN_KEYS` | `` | **Yes** | Comma-separated admin-scope tokens — grants all operations (ADMIN scope) |
| `OPENCLAW_READ_KEYS` | `` | **Yes** | Comma-separated read-only tokens — grants status check only (READ scope) |
| `OPENCLAW_API_KEYS` | `` | **Yes** | Backward-compat API keys — treated as READ scope; cannot perform WRITE/VALIDATE/ROTATE/DELETE |
| `OPENCLAW_ADMIN_DELETE_ENABLED` | `false` | No | Enable the DELETE endpoint — disabled by default; must be set explicitly |
| `OPENCLAW_TENANT_KEYS` | `` | No | Per-token tenant allow-list: `token-a:tenant-a,token-a:tenant-b,token-b:tenant-c`. Unset = no restriction. See Section 3a. |
| `OPENCLAW_ADMIN_RATE_LIMIT_RPM` | `0` | No | Max requests/minute per token for STANDARD routes (status, write, validate). `0` = disabled. See Section 3b. |
| `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` | `0` | No | Max requests/minute per token for SENSITIVE routes (rotate, delete). `0` = disabled. See Section 3b. |
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

### Section 3b. Rate limiting (V5.17 Phase 4)

`OPENCLAW_ADMIN_RATE_LIMIT_RPM` and `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` enable
per-token sliding-window rate limiting on admin endpoints. Both default to `0` (disabled)
for backward compatibility.

**Route categories:**

| Category | Variable | Routes |
|---|---|---|
| STANDARD | `OPENCLAW_ADMIN_RATE_LIMIT_RPM` | GET /status, POST (write), POST /validate |
| SENSITIVE | `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` | POST /rotate, DELETE |

**Rules:**

- Each token has an independent budget per category. Exhausting one token's STANDARD budget
  does not affect another token or the SENSITIVE budget for the same token.
- Auth failures (401), scope failures (403 `scope_not_granted`), and tenant failures
  (403 `tenant_access_denied`) are rejected before the rate check runs and do not consume budget.
- Rate limit state is in-process only. State resets on service restart or Cloud Run
  instance recycling. Not suitable as a hard quota.
- When `OPENCLAW_API_AUTH_ENABLED=false`, all requests share a single anonymous bucket.

**Example configuration (modest protection, not a hard quota):**

```
OPENCLAW_ADMIN_RATE_LIMIT_RPM=60
OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM=10
```

**Rate limit exceeded response (HTTP 429):**

```json
{
  "ok": false,
  "errors": [
    {
      "code": "rate_limit_exceeded",
      "message": "Rate limit exceeded. Retry after 47 seconds.",
      "recoverable": true,
      "source": "openclaw",
      "retry_after_seconds": 47
    }
  ]
}
```

See `docs/V5_17_RATE_LIMITING_DESIGN.md` for the full design.

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

**V5.17 Phase 5 — File locking:** On Linux/Unix platforms (including Cloud Run), `seq` and `file_digest` are now computed and written under an exclusive `fcntl.flock(LOCK_EX)` advisory file lock. This prevents seq/digest races between concurrent writers in the same process group. The return value of `append_audit_event()` includes `"lock_used": true` when locking is applied, or `"lock_used": false` on non-Unix platforms (automatic fallback — no locking, existing behavior).

**Remaining limitations of local file audit:**
- The file lock is advisory; it does not protect against privileged direct filesystem writes outside the locking protocol.
- The seq/file_digest chain is tamper-evident, not cryptographically signed.
- Multiple Cloud Run instances writing to separate ephemeral container filesystems maintain separate audit chains; there is no cross-instance lock.
- Local audit files are lost on container restart. External archival is a future option (see `docs/V5_17_AUDIT_HARDENING_DECISION.md`).

See `docs/V5_17_AUDIT_HARDENING_DECISION.md` for the full options analysis and design rationale.

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
| `rate_limit_exceeded` | 429 | All admin routes | Token exceeded its per-minute request budget | Back off for `retry_after_seconds` before retrying; check `OPENCLAW_ADMIN_RATE_LIMIT_RPM` / `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` configuration |

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

## 18. V5.19 — Real Credential Readiness Gates

V5.19 builds the safety controls, approval workflow, preflight infrastructure, runtime guardrails, and audit requirements that gate any real Google Ads credential onboarding or live API validation. This section documents the components, approval workflow, live gate conditions, server preflight route, audit events, operator procedure, rollback path, and the current deferred boundary.

`GOOGLE_ADS_LIVE_ENABLED=false` throughout V5.19. No real credentials. No Google Ads API calls. No deploy.

### A. Purpose

The V5.19 gate system answers the question: "Is this system ready to onboard real Google Ads credentials and attempt live API validation?" Each gate is a structured, auditable, blocking condition. All gates must pass before any credential onboarding or live API call can proceed.

The system is designed to fail safely: any single gate failure returns a structured error with a specific denial code, emits an audit event, and does not proceed to any credential access or API call.

### B. Components

| Component | Module | Purpose |
|-----------|--------|---------|
| Live gate | `openclaw/live_gate.py` | Pure evaluation of 11 boolean readiness signals; no I/O; no env reads |
| Approval model | `openclaw/approval.py` | `ApprovalRecord` dataclass, `LocalFileApprovalStore`, validity checking |
| Preflight checker | `openclaw/preflight.py` | Composes approval validation and gate check into a single call |
| Live guard | `openclaw/live_guard.py` | HTTP-layer guard functions and safe response builders |
| Server preflight route | `openclaw/server.py` | `POST /openclaw/admin/live-google-ads/preflight` — operator-callable probe |
| Live guard audit events | `openclaw/audit.py` | `build_live_guard_audit_event()` — never includes forbidden identifiers |

### C. Approval Record Procedure

An `ApprovalRecord` must exist and be valid for any tenant/client pair before the live gate will pass. The approval record is created out-of-band by an operator — Claude Code does not self-approve.

**Fields required in an approval record:**

| Field | Description |
|-------|-------------|
| `approved_by` | Operator label (not a credential value) |
| `approved_at` | ISO 8601 timestamp |
| `scope` | One of: `google_ads_live_validation`, `google_ads_credential_onboarding`, `google_ads_credential_rotation`, `google_ads_credential_revoke` |
| `intended_operation` | Plain-text description of what will be called |
| `expiry` | ISO 8601 timestamp or `null` |
| `rollback_plan` | Non-empty text describing the rollback path |
| `revoked` | Boolean; `true` = approval is revoked and gate will fail |

**Fields that must never appear in an approval record:**

`approval_id`, `tenant_id`, `client_id`, `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, `refresh_token`, `access_token`, `developer_token`, `client_secret`

**Validation rules:**

- `revoked: true` → gate fails with `approval_invalid`
- `expiry` set and in the past → gate fails with `approval_invalid`
- `scope` does not match the required scope → gate fails with `approval_invalid`
- Approval absent → gate fails with `approval_missing`

Approval records are stored in `LocalFileApprovalStore` for local development and testing. Real operator approvals require a separate out-of-band process not implemented in V5.19.

### D. Live Gate Conditions

`check_live_gate()` in `openclaw/live_gate.py` evaluates 11 boolean signals in priority order. `live_disabled` is always checked first — if `GOOGLE_ADS_LIVE_ENABLED=false`, the gate returns immediately with `live_disabled` without evaluating other signals.

| Priority | Denial code | Signal evaluated | Required value |
|----------|-------------|-----------------|---------------|
| 1 | `live_disabled` | `live_enabled` | `true` |
| 2 | `approval_missing` | `approval_present` | `true` |
| 3 | `approval_invalid` | `approval_valid` | `true` |
| 4 | `preflight_missing` | `preflight_passed` | `true` |
| 5 | `audit_disabled` | `audit_enabled` | `true` |
| 6 | `credential_missing` | `credential_configured` | `true` |
| 7 | `credential_not_active` | `credential_status` | `"active"` |
| 8 | `tenant_not_allowed` | `tenant_allowed` | `true` |
| 9 | `client_not_allowed` | `client_allowed` | `true` |
| 10 | `rollback_plan_missing` | `rollback_plan_present` | `true` |
| 11 | `operator_confirmation_missing` | `operator_confirmed` | `true` |

`check_live_gate()` is pure Python: it reads no environment variables and makes no I/O calls. The caller is responsible for supplying pre-resolved boolean signals.

### E. Server Preflight Route

**Endpoint:** `POST /openclaw/admin/live-google-ads/preflight`
**Minimum scope:** `VALIDATE`
**Rate limit category:** `STANDARD`

This route is an operator-callable probe that checks whether the current server configuration would allow a live Google Ads operation. It does not perform a live Google Ads API call. `live_api_tested` is always `false` in the response.

`live_enabled` is always derived from `GOOGLE_ADS_LIVE_ENABLED` in the server environment — never from the request body. With the default `GOOGLE_ADS_LIVE_ENABLED=false`, the gate always returns `live_disabled`.

**Denied response (HTTP 403):**

```json
{
  "ok": false,
  "error": "live_preflight_failed",
  "live_api_tested": false,
  "live_gate_allowed": false,
  "error_code": "<denial_code>"
}
```

**Allowed response (HTTP 200 — only if `GOOGLE_ADS_LIVE_ENABLED=true` and all other gates pass):**

```json
{
  "ok": true,
  "error": null,
  "live_api_tested": false,
  "live_gate_allowed": true,
  "error_code": null
}
```

The response never includes `tenant_id`, `client_id`, `approval_id`, `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, `refresh_token`, `access_token`, `developer_token`, or `client_secret`.

### F. Audit Events

Two audit events are emitted per preflight route call. All live guard audit events use `source="server_live_guard"` and `integration_type="google_ads"`, and include `live_api_tested=false`.

**Event 1 — always emitted:**

| Field | Value |
|-------|-------|
| `event_type` | `"live_gate_check"` |
| `ok` | `true` if gate passed; `false` if denied |
| `live_enabled` | `false` until `GOOGLE_ADS_LIVE_ENABLED=true` is explicitly set |
| `approval_present` | Boolean — derived from request signals |
| `approval_valid` | Boolean |
| `credential_status` | String status value |
| `live_gate_allowed` | Boolean |
| `live_api_tested` | Always `false` |
| `error_codes` | List of denial codes, or `[]` on pass |

**Event 2 — outcome-specific:**

| Outcome | `event_type` | `ok` |
|---------|-------------|------|
| Gate denied | `"live_mode_denied"` | `false` |
| Gate allowed | `"live_preflight_allowed"` | `true` |

**Fields never included in live guard audit events:**

`tenant_id`, `client_id`, `approval_id`, `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, `refresh_token`, `access_token`, `developer_token`, `client_secret`

The audit chain (`seq` + `file_digest`) is maintained by `append_audit_event()` and verifiable by `verify_audit_file()` in `audit_maintenance.py`.

### G. Operator Procedure

To check live readiness using the preflight route:

```bash
curl -X POST \
  "http://localhost:8100/openclaw/admin/live-google-ads/preflight" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

With `GOOGLE_ADS_LIVE_ENABLED=false` (the default and required state for all V5.19 operations), the response is always:

```json
{
  "ok": false,
  "error": "live_preflight_failed",
  "live_api_tested": false,
  "live_gate_allowed": false,
  "error_code": "live_disabled"
}
```

**To verify the audit chain after a preflight call:**

```python
from openclaw.audit_maintenance import verify_audit_file
from datetime import datetime, timezone

date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
result = verify_audit_file(f"openclaw/audit/{date_str}.jsonl")
# result["ok"] must be True; result["events_checked"] increases by 2 per preflight call
```

**Enabling live mode (future, gated):**

`GOOGLE_ADS_LIVE_ENABLED=true` must never be set in any environment until all of the following apply:
1. All Pre-Real-Onboarding Checklist items (Section 17) are verified.
2. An operator-authored approval record with a valid scope, non-expired expiry, and non-empty rollback plan exists.
3. All other gate conditions pass via the preflight route.
4. The change is explicitly authorized per the GCP cost and authority rules for this project.

### H. Rollback and Emergency Revoke

For the full rollback and emergency revoke procedure, see Section 14 (Rollback and Recovery) of this runbook.

**V5.19 addition — revoke the approval record after credential revocation:**

After completing a credential delete/revoke via `DELETE /credentials/google-ads`, mark the corresponding approval record revoked:

```json
{ "revoked": true, "revoked_at": "<ISO8601_timestamp>", "notes": "<incident_description>" }
```

This prevents the approval from being reused for a subsequent live operation attempt. A new approval record must be authored by an operator before the live gate will pass again.

**V5.19 addition — verify preflight returns denied after revoke:**

```bash
curl -X POST \
  "http://localhost:8100/openclaw/admin/live-google-ads/preflight" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
# With GOOGLE_ADS_LIVE_ENABLED=false: expect ok=false, error_code=live_disabled
# If live mode were enabled: expect ok=false, error_code=approval_missing or approval_invalid
```

No credential values in any incident record. No GCP resource paths. No `approval_id` values that could correlate to operator identity.

### I. Current Deferred Boundary

V5.19 implements the gate infrastructure and operator tooling. The following actions require separate explicit authorization and are not performed in V5.19:

| Deferred action | Gate condition required first |
|----------------|------------------------------|
| Real Google Ads OAuth credential onboarding | All V5.19 gates PASS; `GOOGLE_ADS_LIVE_ENABLED=true` explicitly authorized |
| Real Google Ads live API validation | Real credentials onboarded; explicit operator approval per-prompt |
| Setting `GOOGLE_ADS_LIVE_ENABLED=true` | Section 17 checklist complete; preflight route returns `live_gate_allowed: true` |
| Secret Manager prior-version destruction | Separate implementation authorization; irreversible |
| Cloud Run deployment | IAM, billing, service account authorization |
| External approval UI | Separate frontend milestone |

`GOOGLE_ADS_LIVE_ENABLED=false` is the authoritative gate. Until it is explicitly set to `true` by an authorized operator action, no live Google Ads API call can occur regardless of any other configuration.

---

## 19. Related Documents

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
| [docs/V5_17_RATE_LIMITING_DESIGN.md](V5_17_RATE_LIMITING_DESIGN.md) | V5.17 Phase 4 design: sliding-window rate limiting, env vars, route categories, anonymous bucket, interaction with RBAC/tenant isolation |
| [docs/V5_17_AUDIT_HARDENING_DECISION.md](V5_17_AUDIT_HARDENING_DECISION.md) | V5.17 Phase 5 design decision: fcntl file locking for audit append, options evaluated, limitations, future paths |
| [docs/V5_19_IMPLEMENTATION_PLAN.md](V5_19_IMPLEMENTATION_PLAN.md) | V5.19 full implementation plan: live gate, approval workflow, preflight checker, server guardrails, audit events, runbook scope |
| [openclaw/live_gate.py](../openclaw/live_gate.py) | `check_live_gate()`, `LiveGateInput`, `LiveGateResult`, 11 denial codes — pure evaluation, no I/O |
| [openclaw/approval.py](../openclaw/approval.py) | `ApprovalRecord` dataclass, `LocalFileApprovalStore`, `is_approval_valid()`, `sanitize_approval_record()` |
| [openclaw/preflight.py](../openclaw/preflight.py) | `check_live_operation_preflight()`, `LiveOperationPreflightInput`, `LiveOperationPreflightResult` |
| [openclaw/live_guard.py](../openclaw/live_guard.py) | `guard_live_google_ads_from_signals()`, safe response builders, `LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS` |

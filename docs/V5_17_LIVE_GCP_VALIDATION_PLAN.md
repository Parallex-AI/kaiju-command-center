# V5.17 Live GCP Lifecycle Validation Plan — Fake Secrets Only

**Kaiju Command Center — V5.17**

> **IMPORTANT:** This plan is operator-run only. It must not be executed by automation or without explicit operator approval. It uses fake credential values only. It does not call the Google Ads API. `GOOGLE_ADS_LIVE_ENABLED` must remain `false` throughout.

---

## 1. Purpose

Validate the full HTTP → `openclaw/server.py` → `openclaw/admin.py` → `GCPSecretManagerStore` chain using fake Google Ads credential values only.

Prior V5.13 and V5.14 GCP validation confirmed `GCPSecretManagerStore` could write and read a secret bundle. This plan extends that scope to the V5.15 and V5.16 lifecycle endpoints — validate, rotate, delete — and adds post-delete status and audit JSONL verification.

**Validation focus:**

| Phase | Operation | Endpoint |
|-------|-----------|----------|
| A | Pre-flight | — |
| B | Write fake bundle | `POST /credentials/google-ads` |
| C | Status after write | `GET /credentials/google-ads/status` |
| D | Structural validate | `POST /credentials/google-ads/validate` |
| E | Rotate fake bundle | `POST /credentials/google-ads/rotate` |
| F | Delete/revoke | `DELETE /credentials/google-ads` |
| G | Post-delete status | `GET /credentials/google-ads/status` |
| H | Audit verification | `verify_audit_file()` |
| — | Cleanup | — |

This is the first end-to-end lifecycle test through `GCPSecretManagerStore` for all V5.15/V5.16 operations.

---

## 2. Non-Goals

This validation explicitly excludes:

- Real Google Ads credentials of any kind
- Google Ads API calls (`GOOGLE_ADS_LIVE_ENABLED` remains `false`)
- Production Cloud Run deployment
- Staging or production Cloud Run environments
- New GCP resources or secrets beyond the one rehearsal secret
- IAM changes of any kind
- Billing changes of any kind
- API enablement (Secret Manager API must already be enabled; this plan does not enable it)
- Fixed-cost infrastructure (no Compute Engine, GKE, Cloud SQL, Pub/Sub, Scheduler, Load Balancer, Redis, BigQuery, or NAT Gateway)
- Real OAuth credential onboarding
- BigQuery audit sink
- KMS or HSM audit signing
- GCP Secret Manager version destruction implementation (prior version behavior is observed only — no version destruction code)
- Frontend credential UI
- OAuth consent flow
- Per-tenant IAM RBAC (tested via token scope only)

---

## 3. Preconditions

All of the following must be confirmed before starting any phase.

**GCP access:**
- Operator has an existing local GCP profile (`gcloud auth application-default login` or equivalent) configured **outside the repo**
- GCP Secret Manager API is already enabled in the target project
- The local profile has sufficient IAM access: `roles/secretmanager.secretVersionAdder`, `roles/secretmanager.secretCreator`, `roles/secretmanager.secretAccessor`, `roles/secretmanager.secretDeleter` — scoped to the rehearsal prefix at minimum
- No key file is created or downloaded during this validation

**Local server configuration:**
- `GCP_SECRET_MANAGER_ENABLED=true` — for the local test server only, not committed
- `GOOGLE_ADS_LIVE_ENABLED=false`
- `OPENCLAW_API_AUTH_ENABLED=true`
- `OPENCLAW_ADMIN_KEYS` configured with a placeholder admin token (not a real credential)
- `OPENCLAW_READ_KEYS` optionally configured with a placeholder read token
- `OPENCLAW_ADMIN_DELETE_ENABLED=false` by default; enabled only for Phase F (delete)
- `CREDENTIAL_REFERENCE_STORE_PATH` points to a temp/operator-controlled path **outside the committed repo files** (e.g., a temp directory or a path not tracked by git)
- `OPENCLAW_AUDIT_ROOT` points to a temp/operator-controlled path **outside the committed repo files**

**Repo state:**
- No `.env` file committed to the repository
- No credential JSON files inside the repository
- No service account key files inside the repository
- `runtime/credential-references/` is gitignored and must not be staged

---

## 4. Required Fake Identifiers

All curl examples and recorded results must use these placeholder identifiers only.

| Placeholder | Role |
|---|---|
| `<TENANT_ID_REHEARSAL>` | Tenant namespace for the rehearsal run |
| `<CLIENT_ID_REHEARSAL>` | Client identifier for the rehearsal run |
| `<ADMIN_TOKEN>` | Admin-scope bearer token (from `OPENCLAW_ADMIN_KEYS`) |
| `<READ_TOKEN>` | Read-only bearer token (from `OPENCLAW_READ_KEYS`) |
| `<FAKE_DEVELOPER_TOKEN_V1>` | First fake developer token (bundle write) |
| `<FAKE_GOOGLE_CLIENT_ID_V1>` | First fake OAuth client ID (bundle write) |
| `<FAKE_GOOGLE_CLIENT_SECRET_V1>` | First fake OAuth client secret (bundle write) |
| `<FAKE_REFRESH_TOKEN_V1>` | First fake refresh token (bundle write) |
| `<FAKE_DEVELOPER_TOKEN_V2>` | Second fake developer token (rotation) |
| `<FAKE_GOOGLE_CLIENT_ID_V2>` | Second fake OAuth client ID (rotation) |
| `<FAKE_GOOGLE_CLIENT_SECRET_V2>` | Second fake OAuth client secret (rotation) |
| `<FAKE_REFRESH_TOKEN_V2>` | Second fake refresh token (rotation) |

**Fake value requirements:**

- Values must be obviously fake — they must not resemble real OAuth tokens, developer tokens, or refresh tokens
- Acceptable example patterns: `fake-dev-token-v1-rehearsal`, `fake-client-id-v1-rehearsal`, `fake-secret-v1-rehearsal`, `fake-refresh-v1-rehearsal`
- Patterns that must never be used: anything starting with `ya29.`, `1//`, real base64-encoded JWT-shaped strings, or values containing GCP project identifiers
- V1 and V2 values must be distinct so rotation can be distinguished if Secret Manager version metadata is inspected

---

## 5. Redaction Rules

These rules govern what may be recorded in `docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md` during execution.

**Record only:**
- `ok` (boolean)
- HTTP status code (integer)
- `credential_status` (status string and `configured` boolean)
- `secret_status.configured` (boolean)
- `configured_fields` map (field name → boolean only, no values)
- `missing_fields` (field names only, no values)
- `last_validated_at` (timestamp string)
- `warnings` and `error_codes` (code strings only)
- Audit verification result (`ok`, `events_checked`, `errors`)
- Number of GCP Secret Manager versions if inspected manually (count only, no names or values)

**Never record:**
- GCP project ID
- Service account email or display name
- `GOOGLE_APPLICATION_CREDENTIALS` file path or contents
- Raw token values (admin, read, or fake credential values)
- Raw fake secret payload JSON
- `credential_ref` value
- `secret_id` value (the GCP secret name)
- `customer_id` or `login_customer_id` values
- Full JSON response bodies if they contain any of the above

If a response accidentally surfaces any of the above, redact before recording and note "response redacted — contained non-recordable field."

---

## 6. Local Server Startup

> **All values below are placeholders. Do not use real values. Do not commit the startup configuration.**

Source an application-default credentials profile configured outside the repo (do not paste credentials or project details into any shared session):

```bash
# Source operator GCP profile — configured outside repo; not echoed here
# (e.g., gcloud auth application-default login was run previously)

export GOOGLE_ADS_LIVE_ENABLED=false
export GCP_SECRET_MANAGER_ENABLED=true
export GCP_SECRET_MANAGER_ENV=local
export GCP_SECRET_MANAGER_PREFIX=kaiju-rehearsal
export OPENCLAW_API_AUTH_ENABLED=true
export OPENCLAW_ADMIN_KEYS=<ADMIN_TOKEN>
export OPENCLAW_READ_KEYS=<READ_TOKEN>
export OPENCLAW_ADMIN_DELETE_ENABLED=false
export OPENCLAW_AUDIT_ENABLED=true
export OPENCLAW_AUDIT_ROOT=<TEMP_AUDIT_ROOT_OUTSIDE_REPO>
export CREDENTIAL_REFERENCE_STORE_PATH=<TEMP_REFERENCE_STORE_OUTSIDE_REPO>

# Start local server (adjust port if needed)
cd ~/kaiju
uvicorn openclaw.server:app --host 127.0.0.1 --port 8100
```

**Notes:**
- `GCP_SECRET_MANAGER_ENV=local` and `GCP_SECRET_MANAGER_PREFIX=kaiju-rehearsal` together scope the rehearsal secret to a name that is obviously not production
- `<TEMP_AUDIT_ROOT_OUTSIDE_REPO>` and `<TEMP_REFERENCE_STORE_OUTSIDE_REPO>` must resolve to paths not tracked by git — for example, a temp directory created by `mktemp -d`
- Do not set `GCP_PROJECT_ID` in a way that prints it to shared output; use `gcloud config get-value project` privately to confirm it is set in the profile
- Do not set `GOOGLE_ADS_LIVE_ENABLED=true` for any reason during this validation

---

## 7. Phase A — Pre-flight

Run this checklist before starting Phase B. Record PASS or FAIL for each item.

```
Pre-flight checklist:

  [ ] Branch is v5.17-production-readiness
  [ ] Latest commit hash matches expected (no uncommitted source changes)
  [ ] Working tree is clean (git status --short returns only untracked/ignored runtime files)
  [ ] GOOGLE_ADS_LIVE_ENABLED=false confirmed in active shell
  [ ] No credential JSON tracked by git (git ls-files | grep -i "credential.*json" returns empty)
  [ ] No .env file tracked by git
  [ ] Local smoke tests pass in InMemory mode (GCP_SECRET_MANAGER_ENABLED=false):
        scripts/smoke_test_v5_credentials.sh   → 17/17 PASS
        scripts/smoke_test_v5_12_gcp_secret_manager.sh → 8/8 PASS
  [ ] No prior rehearsal CredentialReference exists for <TENANT_ID_REHEARSAL>/<CLIENT_ID_REHEARSAL>
        (GET /status returns exists=false, or CREDENTIAL_REFERENCE_STORE_PATH is empty)
  [ ] GCP Secret Manager access confirmed (gcp_secret_manager_status() returns enabled=true,
        dependency_available=true, project_id_configured=true — no project ID printed)
  [ ] Local server is running and health check passes:
        curl http://127.0.0.1:8100/openclaw/health → {"ok": true}

Pre-flight result: PASS / FAIL
If any item is FAIL, stop and resolve before proceeding.
```

---

## 8. Phase B — Write Fake Bundle

**Endpoint:** `POST /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads`
**Required scope:** WRITE (satisfied by ADMIN token)

```bash
curl -X POST \
  "http://127.0.0.1:8100/openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_token": "<FAKE_DEVELOPER_TOKEN_V1>",
    "client_id": "<FAKE_GOOGLE_CLIENT_ID_V1>",
    "client_secret": "<FAKE_GOOGLE_CLIENT_SECRET_V1>",
    "refresh_token": "<FAKE_REFRESH_TOKEN_V1>"
  }'
```

**Expected result:**
- HTTP `200`
- `ok: true`
- `credential_status.configured: true` (status: `configured` or `active`)
- `secret_status.configured: true`
- `configured_fields`: all four fields `true` — `developer_token`, `client_id`, `client_secret`, `refresh_token`
- No secret values in response
- No `credential_ref` or `secret_id` in response body

**If write fails:**
- Stop. Do not proceed to Phase C.
- Inspect `errors[].code` only — do not inspect raw GCP error messages that may contain project identifiers
- Common causes: IAM binding missing (`gcp_secret_access_denied`), project ID not configured (`gcp_project_id_missing`), dependency not installed (`gcp_dependency_missing`)
- See Failure Handling (Section 16)

---

## 9. Phase C — Status After Write

**Endpoint:** `GET /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/status`
**Required scope:** READ (satisfied by ADMIN or READ token)

```bash
curl -X GET \
  "http://127.0.0.1:8100/openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/status" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Expected result:**
- HTTP `200`
- `ok: true`
- `credential_status.exists: true`
- `credential_status.status: configured` (or `active` if already validated)
- `secret_status.configured: true`
- `configured_fields`: all four fields `true`
- No secret values in response

---

## 10. Phase D — Structural Validate

**Endpoint:** `POST /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/validate`
**Required scope:** VALIDATE (satisfied by ADMIN token)

```bash
curl -X POST \
  "http://127.0.0.1:8100/openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/validate" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Expected result:**
- HTTP `200`
- `ok: true`
- `validation_result.structurally_complete: true`
- `validation_result.missing_fields: []`
- `validation_result.live_api_tested: false`
- `validation_result.last_validated_at`: timestamp set
- `credential_status.status: active`
- `secret_status.configured: true`
- No Google Ads API call made — `live_api_tested` confirms this

**Implementation note:** `validate_google_ads_credentials()` calls `get_secret_status()` only — it never calls `get_secret_bundle()`. This means it reads field presence from the GCP secret version (via `access_secret_version`) but does not return or log the field values.

---

## 11. Phase E — Rotate Fake Bundle

**Endpoint:** `POST /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/rotate`
**Required scope:** ROTATE (satisfied by ADMIN token only)

```bash
curl -X POST \
  "http://127.0.0.1:8100/openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/rotate" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_token": "<FAKE_DEVELOPER_TOKEN_V2>",
    "client_id": "<FAKE_GOOGLE_CLIENT_ID_V2>",
    "client_secret": "<FAKE_GOOGLE_CLIENT_SECRET_V2>",
    "refresh_token": "<FAKE_REFRESH_TOKEN_V2>"
  }'
```

**Expected result:**
- HTTP `200`
- `ok: true`
- `rotation_result.structurally_complete: true`
- `rotation_result.missing_fields: []`
- `rotation_result.last_validated_at`: timestamp updated
- `credential_status.status: active`
- `secret_status.configured: true`
- All four `configured_fields: true`
- No secret values in response

**Optional GCP Secret Manager version observation:**
If the operator manually inspects the GCP secret using `gcloud secrets versions list` (from a secure terminal, not echoed here), the expected behavior under the current implementation is:
- Version count increases by 1 (new version added; prior version remains ENABLED)
- Record only: version count (integer), not version names or resource paths
- The prior version (`V1` bundle) remains enabled — it is not automatically disabled or destroyed on rotation under the current `put_secret_bundle()` implementation
- This is a known documented limitation; GCP version lifecycle management is deferred to a future milestone

---

## 12. Phase F — Delete / Revoke

**Before this phase:** set `OPENCLAW_ADMIN_DELETE_ENABLED=true` for the local server. This may require restarting the server with the updated env var.

**Endpoint:** `DELETE /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads`
**Required scope:** DELETE (satisfied by ADMIN token) **and** `OPENCLAW_ADMIN_DELETE_ENABLED=true`

```bash
curl -X DELETE \
  "http://127.0.0.1:8100/openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Expected result:**
- HTTP `200`
- `ok: true`
- `credential_status.status: revoked`
- `secret_status.configured: false`
- `configured_fields`: all four fields `false`
- `warnings`: empty or `["secret_already_absent"]` only if idempotent scenario
- No secret values in response

**Implementation note:** `delete_google_ads_credentials()` calls `delete_secret_bundle()` only — which calls `client.delete_secret()` (deletes the secret resource entirely, not just a version). It never calls `get_secret_bundle()`.

**After this phase:** restore `OPENCLAW_ADMIN_DELETE_ENABLED=false` or stop the test server.

---

## 13. Phase G — Post-Delete Status

**Endpoint:** `GET /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/status`
**Required scope:** READ

```bash
curl -X GET \
  "http://127.0.0.1:8100/openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/status" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Expected result:**
- HTTP `200`
- `credential_status.status: revoked`
- `secret_status.configured: false`
- No secret values in response

---

## 14. Phase H — Audit Verification

Use `verify_audit_file()` from `openclaw/audit_maintenance.py` on the temp audit file created during the validation run. The audit root is `<TEMP_AUDIT_ROOT_OUTSIDE_REPO>`.

```python
from openclaw.audit_maintenance import verify_audit_file

result = verify_audit_file("<TEMP_AUDIT_ROOT_OUTSIDE_REPO>/YYYY-MM-DD.jsonl")
# Expected: {"ok": True, "events_checked": N, "errors": [], "warnings": []}
```

**Expected result:**
- `ok: true`
- `events_checked`: N > 0 (at least one event per credential write path executed)
- `errors`: `[]`
- `warnings`: `[]`
- Sequence chain valid — `seq` increments 1, 2, 3… without gaps
- Digest chain valid — `file_digest` matches accumulated bytes before each append

**Expected operations in audit events (field names only):**
At minimum, events with these `operation` values should be present:
- `bundle_write` (Phase B)
- `validate` (Phase D)
- `rotate` (Phase E)
- `delete` (Phase F)

**Forbidden fields confirmation:** Inspect one audit event line manually (not in any shared session). Confirm the following fields are absent:
- `credential_ref`
- `secret_id`
- `customer_id`
- `login_customer_id`
- `developer_token`, `client_secret`, `refresh_token`, `access_token`

Record only: audit verification `ok` status, `events_checked` count, and forbidden-fields absent confirmation.

---

## 15. Cleanup Verification

After all phases complete, verify the following before closing the validation session:

```
Cleanup checklist:

  [ ] Rehearsal GCP secret is absent:
        gcloud secrets list --filter="name~kaiju-rehearsal" returns no rehearsal secret
        (or the secret was deleted in Phase F and confirmed absent via list)
  [ ] Temp CredentialReference store (<TEMP_REFERENCE_STORE_OUTSIDE_REPO>) is removed
        or archived outside the repo — not committed
  [ ] Temp audit files (<TEMP_AUDIT_ROOT_OUTSIDE_REPO>) are archived outside the repo or deleted —
        not committed and not left inside ~/kaiju/
  [ ] No .env file created inside the repo during this session
  [ ] No credential JSON file created inside the repo during this session
  [ ] git status --short shows only gitignored runtime files (if any) — no new tracked files
  [ ] OPENCLAW_ADMIN_DELETE_ENABLED is restored to false or test server is stopped
  [ ] Shell history that may contain fake token values is cleared if required by operator policy
```

---

## 16. Failure Handling

**If Phase B (write) fails:**
- Stop. Do not proceed to Phase C or later phases.
- Inspect `errors[].code` only — do not log or share raw GCP error messages.
- Common error codes and likely causes:
  - `gcp_project_id_missing` — `GCP_PROJECT_ID` not set or empty; check the shell environment
  - `gcp_secret_access_denied` — IAM binding missing; check `secretVersionAdder` and `secretCreator` roles
  - `gcp_dependency_missing` — `google-cloud-secret-manager` not installed; run `pip install google-cloud-secret-manager>=2.20.0`
  - `gcp_secret_write_failed` — generic GCP API failure; check quota and API enablement

**If Phase D (validate) fails:**
- Inspect `configured_fields` map (field names only) to identify which fields are missing.
- Do not inspect the raw secret payload to diagnose.
- If `structurally_complete=false` but the write succeeded, the likely cause is that `get_secret_status()` read the secret version and found it incomplete — this should not occur when Phase B succeeded with all four fields.

**If Phase E (rotate) fails after Phase D passed:**
- Check `rotation_result.missing_fields` (field names only).
- If `invalid_status_for_rotation` (409), the credential was marked REVOKED unexpectedly — do not proceed; investigate the CredentialReference status.
- To retry: issue the rotate request again with a known-good fake bundle.

**If Phase F (delete) fails:**
- Check `errors[].code`. If `delete_not_enabled`, confirm `OPENCLAW_ADMIN_DELETE_ENABLED=true` is set and the server is running with that value.
- If `secret_delete_failed`, the GCP delete may have failed (IAM, not-found, etc.). Run cleanup verification manually.
- Do not leave the delete gate (`OPENCLAW_ADMIN_DELETE_ENABLED=true`) enabled after the session.

**If Phase H (audit verification) fails:**
- Preserve the audit JSONL file outside the repo.
- Do not commit the audit file.
- Record the `errors` list from `verify_audit_file()` in the results document.
- Stop validation and investigate before marking the phase as PASS.

**If any secret value is accidentally printed to a shared terminal or log:**
- Treat as a security incident.
- Discard any logs containing the value.
- Rotate affected fake credentials (they are fake, but the incident response practice applies).
- Do not post the exposed value anywhere.

---

## 17. Acceptance Criteria

This validation is PASS when all of the following are true:

- [ ] All phases A through H completed without a blocking failure
- [ ] No real Google Ads credentials used in any phase
- [ ] `GOOGLE_ADS_LIVE_ENABLED=false` throughout — confirmed at start and end
- [ ] No Google Ads API calls made
- [ ] No secret values (fake or real) recorded in any committed document
- [ ] `credential_ref` and `secret_id` not recorded in any committed document
- [ ] Cleanup verified: rehearsal GCP secret absent, no temp files in repo
- [ ] Audit verification: `verify_audit_file()` returned `ok=true`
- [ ] `docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md` completed and committed (redacted)
- [ ] No new IAM changes, billing changes, or fixed-cost infrastructure created

---

## 18. Related Documents

| Document | Purpose |
|---|---|
| [docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md](CREDENTIAL_LIFECYCLE_RUNBOOK.md) | Full operator credential lifecycle guide: token setup, endpoints, error codes, checklists |
| [docs/GCP_SECRET_MANAGER_RUNBOOK.md](GCP_SECRET_MANAGER_RUNBOOK.md) | GCP IAM setup, secret naming, rotation (version management), failure modes |
| [docs/V5_16_BRANCH_CLOSURE.md](V5_16_BRANCH_CLOSURE.md) | V5.16 implementation summary: RBAC, audit hardening, rotation endpoint |
| [docs/RELEASE_NOTES_V5_16_0_BETA.md](RELEASE_NOTES_V5_16_0_BETA.md) | V5.16 release notes: endpoint changes, security guarantees, operator notes |
| [openclaw/admin.py](../openclaw/admin.py) | All credential lifecycle function implementations |
| [openclaw/audit_maintenance.py](../openclaw/audit_maintenance.py) | `verify_audit_file()` and `prune_audit_files()` |
| [agents/ads-agent/credentials/gcp_secret_manager_store.py](../agents/ads-agent/credentials/gcp_secret_manager_store.py) | `GCPSecretManagerStore` implementation: `put_secret_bundle`, `get_secret_status`, `delete_secret_bundle` |
| [docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md](V5_17_LIVE_GCP_VALIDATION_RESULTS.md) | Results template — fill in after operator-run validation |

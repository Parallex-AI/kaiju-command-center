# V5.18 Live GCP Fake-Secret Validation Plan

**Branch:** `v5.18-live-gcp-fake-validation`
**Base release:** `v5.17.0-beta`
**Kaiju Command Center — V5.18**

> **IMPORTANT:** This plan is operator-run only. It must not be executed by automation or without explicit operator approval per-prompt. It uses fake credential values only. It does not call the Google Ads API. `GOOGLE_ADS_LIVE_ENABLED` must remain `false` throughout. No GCP commands may be executed until the operator explicitly authorizes each step.

---

## 1. Objective

Execute the controlled live GCP Secret Manager lifecycle validation that V5.17 planned but did not execute. Validate the full HTTP → `openclaw/server.py` → `openclaw/admin.py` → `GCPSecretManagerStore` chain using fake Google Ads credential values only, across all five V5.17 lifecycle operations: write, status, validate, rotate, and delete.

This is the first V5.18 milestone. It produces a filled `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md` confirming the full lifecycle through `GCPSecretManagerStore` on a real GCP Secret Manager backend.

---

## 2. Non-Goals

This validation explicitly excludes:

- Real Google Ads credentials of any kind
- Google Ads API calls (`GOOGLE_ADS_LIVE_ENABLED` remains `false`)
- Production Cloud Run deployment
- Staging or production Cloud Run environments
- New GCP resources or secrets beyond the one rehearsal secret created and deleted during this validation
- IAM changes of any kind
- Billing changes of any kind
- API enablement (Secret Manager API must already be enabled; this plan does not enable it)
- Fixed-cost infrastructure (no Compute Engine, GKE, Cloud SQL, Pub/Sub, Scheduler, Load Balancer, Redis/Memorystore, BigQuery, or NAT Gateway)
- Real OAuth credential onboarding
- BigQuery audit sink
- KMS or HSM audit signing
- GCP Secret Manager version destruction / disable policy (prior version behavior observed only — no version lifecycle management code changes)
- Frontend credential UI
- OAuth consent flow
- Per-tenant IAM RBAC (tested via token scope and `OPENCLAW_TENANT_KEYS` only)
- Real customer IDs, real developer tokens, real OAuth client secrets, real refresh tokens, real access tokens

---

## 3. Hard Safety Rules

These rules apply throughout the entire V5.18 cycle. No exception.

1. `GOOGLE_ADS_LIVE_ENABLED=false` at all times — in every shell, every server startup, every test
2. No real Google Ads credentials may be used, stored, referenced, or requested
3. No GCP commands may be executed without explicit operator approval per-prompt
4. No secret values (fake or real) may appear in committed docs, chat, shared logs, or stdout captured in tracked files
5. No GCP project ID, service account email, or `GOOGLE_APPLICATION_CREDENTIALS` path may appear in any tracked file
6. No `.env` file, credential JSON, or service account key file may be committed to the repo
7. Results must be recorded in redacted form only (see Section 9)
8. Claude Code does not decide cloud architecture, IAM, billing, or infrastructure — those decisions require explicit operator authorization

---

## 4. Required Operator Approvals

Each of the following requires explicit operator authorization before execution. Claude Code does not proceed without confirmation.

| Gate | Authorization required |
|------|------------------------|
| Execute any GCP CLI command (`gcloud`, `gsutil`, etc.) | Per-prompt explicit approval |
| Start local OpenClaw server with `GCP_SECRET_MANAGER_ENABLED=true` | Per-prompt explicit approval |
| Execute each validation phase (F through N) | Per-phase operator sign-off |
| Enable `OPENCLAW_ADMIN_DELETE_ENABLED=true` for Phase J | Per-prompt explicit approval |
| Commit any results document | Per-prompt explicit approval |

---

## 5. Required Local Prerequisites

All of the following must be confirmed before Phase A (preflight) can begin.

**Python and package environment:**
- Python 3.12+ available at `~/kaiju/.venv/bin/python3`
- `google-cloud-secret-manager>=2.20.0` installed in the venv: `pip show google-cloud-secret-manager`
- FastAPI, uvicorn, httpx installed (already confirmed by smoke suite)
- `openclaw/` importable from `~/kaiju/`

**Local smoke suite baseline:**
- `scripts/smoke_test_v5_credentials.sh` → 20/20 PASS (with `GCP_SECRET_MANAGER_ENABLED=false`)
- `scripts/smoke_test_v5_12_gcp_secret_manager.sh` → 8/8 PASS

**Git hygiene:**
- Branch: `v5.18-live-gcp-fake-validation`
- Working tree clean
- No credential JSON or `.env` files tracked

---

## 6. Required GCP Prerequisites

All of the following must be confirmed by the operator before Phase B (GCP preflight) can begin. None of these are created during this validation.

| Prerequisite | Confirmation method |
|---|---|
| GCP project exists and is active | `gcloud config get-value project` (do not echo output publicly) |
| Secret Manager API is enabled | `gcloud services list --enabled` — confirm `secretmanager.googleapis.com` |
| Application-default credentials configured | `gcloud auth application-default print-access-token` (do not record or share token) |
| IAM: `roles/secretmanager.secretVersionAdder` or equivalent on project or prefix | Review IAM policy privately |
| IAM: `roles/secretmanager.secretCreator` | Review IAM policy privately |
| IAM: `roles/secretmanager.secretAccessor` | Review IAM policy privately |
| IAM: `roles/secretmanager.secretDeleter` | Review IAM policy privately |
| No existing rehearsal secret with the `kaiju-rehearsal` prefix | `gcloud secrets list --filter="name~kaiju-rehearsal"` returns empty |

No key files are created or downloaded during this validation. The local `gcloud` application-default credentials profile is used.

---

## 7. Secrets Policy

| What | Rule |
|------|------|
| Real Google Ads credentials | Never used, never requested, never referenced |
| GCP project ID | Used in local shell env only — never written to any tracked file |
| Service account email | Referenced by the operator only — never written to any tracked file |
| `GOOGLE_APPLICATION_CREDENTIALS` path | Set in local shell only — never written to any tracked file |
| Admin/read token values | Used as local env vars only — never written to any tracked file |
| Fake credential values | Used in curl requests only — never written to any tracked file |
| `credential_ref` | Never recorded — internal GCP secret name derived value |
| `secret_id` | Never recorded — internal GCP secret resource identifier |

---

## 8. Fake Credential Policy

All curl request bodies and test identifiers must use the following placeholder patterns only.

| Placeholder | Role | Acceptable example pattern |
|---|---|---|
| `<TENANT_ID_REHEARSAL>` | Tenant namespace | `tenant-v518-rehearsal` |
| `<CLIENT_ID_REHEARSAL>` | Client identifier | `client-v518-rehearsal` |
| `<ADMIN_TOKEN>` | Admin-scope bearer token | Set from `OPENCLAW_ADMIN_KEYS` |
| `<READ_TOKEN>` | Read-only bearer token | Set from `OPENCLAW_READ_KEYS` |
| `<FAKE_DEVELOPER_TOKEN_V1>` | First fake developer token | `fake-dev-token-v1-v518` |
| `<FAKE_GOOGLE_CLIENT_ID_V1>` | First fake OAuth client ID | `fake-client-id-v1-v518` |
| `<FAKE_GOOGLE_CLIENT_SECRET_V1>` | First fake OAuth client secret | `fake-client-secret-v1-v518` |
| `<FAKE_REFRESH_TOKEN_V1>` | First fake refresh token | `fake-refresh-v1-v518` |
| `<FAKE_DEVELOPER_TOKEN_V2>` | Second fake developer token (rotation) | `fake-dev-token-v2-v518` |
| `<FAKE_GOOGLE_CLIENT_ID_V2>` | Second fake OAuth client ID (rotation) | `fake-client-id-v2-v518` |
| `<FAKE_GOOGLE_CLIENT_SECRET_V2>` | Second fake OAuth client secret (rotation) | `fake-client-secret-v2-v518` |
| `<FAKE_REFRESH_TOKEN_V2>` | Second fake refresh token (rotation) | `fake-refresh-v2-v518` |

**Rules:**
- V1 and V2 values must be distinct so rotation can be confirmed
- Values must be obviously fake — never resemble real OAuth tokens, developer tokens, or JWT-shaped strings
- Patterns prohibited: anything starting with `ya29.`, `1//`, real base64 JWT strings, or GCP project identifier substrings
- Fake values must not be written to any tracked doc, even in placeholder form

---

## 9. Redaction Rules

These rules govern what may be recorded in `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md`.

**Record only:**
- `ok` (boolean)
- HTTP status code (integer)
- `credential_status` status string and `configured` boolean
- `secret_status.configured` (boolean)
- `configured_fields` map (field name → boolean — no values)
- `missing_fields` (field names only)
- `last_validated_at` (timestamp string)
- `warnings` and error code strings
- Audit verification: `ok`, `events_checked`, `errors`
- GCP secret version count (integer only — no resource names, no secret IDs)

**Never record:**
- GCP project ID
- Service account email or display name
- `GOOGLE_APPLICATION_CREDENTIALS` file path or contents
- Raw token values (admin, read, or any credential value)
- Raw fake secret payload JSON
- `credential_ref` or `secret_id`
- `customer_id` or `login_customer_id`
- Full JSON response bodies containing any of the above

If a response accidentally surfaces any of the above, redact before recording and note "response redacted — contained non-recordable field."

---

## 10. Validation Phases

### Phase A — Local Repo and Tool Preflight

Run before any GCP operation.

```
Pre-flight checklist:

  [ ] Branch: v5.18-live-gcp-fake-validation
  [ ] Latest commit on branch confirmed (git log --oneline -1)
  [ ] Working tree clean (git status --short returns empty or only gitignored runtime)
  [ ] GOOGLE_ADS_LIVE_ENABLED=false confirmed in active shell
  [ ] GCP_SECRET_MANAGER_ENABLED=false confirmed (InMemory mode for preflight only)
  [ ] No credential JSON tracked (git ls-files | grep -i "credential.*json" returns empty)
  [ ] No .env file tracked (git ls-files | grep "\.env" returns .env.example only or empty)
  [ ] Python venv confirmed: ~/kaiju/.venv/bin/python3 --version
  [ ] google-cloud-secret-manager installed: pip show google-cloud-secret-manager
  [ ] Local smoke suite PASS in InMemory mode:
        scripts/smoke_test_v5_credentials.sh   → 20/20 PASS
        scripts/smoke_test_v5_12_gcp_secret_manager.sh → 8/8 PASS
```

Phase A result: PASS / FAIL (stop if FAIL)

---

### Phase B — GCP CLI and Auth Preflight

> Requires explicit operator approval before running any gcloud command.

```
GCP preflight checklist:

  [ ] gcloud installed and on PATH: gcloud --version
  [ ] Active GCP account confirmed (do not echo account email in shared output)
  [ ] Active GCP project confirmed (do not echo project ID in shared output)
  [ ] Secret Manager API confirmed enabled
  [ ] Application-default credentials valid (token fetch — do not share token)
  [ ] No existing kaiju-rehearsal secret:
        gcloud secrets list --filter="name~kaiju-rehearsal" returns empty
  [ ] IAM bindings sufficient for secretCreator, secretVersionAdder,
        secretAccessor, secretDeleter (review privately — do not share policy output)
```

Phase B result: PASS / FAIL (stop if FAIL)

---

### Phase C — Secret Manager API Availability Check

> Requires explicit operator approval.

Use `gcp_secret_manager_status()` from the Python layer to confirm dependency and project config without printing the project ID:

```python
import os
os.environ["GCP_SECRET_MANAGER_ENABLED"] = "true"
os.environ["GOOGLE_ADS_LIVE_ENABLED"] = "false"
# GCP_PROJECT_ID must be set in environment — do not print it here

import sys
sys.path.insert(0, os.path.expanduser("~/kaiju/agents/ads-agent"))
from credentials.gcp_secret_manager_store import gcp_secret_manager_status

status = gcp_secret_manager_status()
print({
    "enabled": status.get("enabled"),
    "dependency_available": status.get("dependency_available"),
    "project_id_configured": status.get("project_id_configured"),
    # do not print project_id value
})
```

Expected:
- `enabled: true`
- `dependency_available: true`
- `project_id_configured: true`

Phase C result: PASS / FAIL (stop if FAIL)

---

### Phase D — Local Environment Setup

> All values are placeholders. Do not use real values. Do not commit or echo the startup configuration.

Set environment variables in the local shell only. Do not paste into any shared session.

```bash
# GCP identity — configured in local gcloud profile, not set here
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
```

**Notes:**
- `GCP_SECRET_MANAGER_ENV=local` and `GCP_SECRET_MANAGER_PREFIX=kaiju-rehearsal` scope the rehearsal secret to an obviously non-production name
- `<TEMP_AUDIT_ROOT_OUTSIDE_REPO>` and `<TEMP_REFERENCE_STORE_OUTSIDE_REPO>` must resolve to paths not tracked by git (e.g., a temp directory from `mktemp -d`)
- `GCP_PROJECT_ID` must be set in the local shell from the operator's gcloud profile — do not echo or share the project ID value
- `OPENCLAW_TENANT_KEYS` may optionally be set to restrict the admin token to `<TENANT_ID_REHEARSAL>` for per-tenant isolation testing

Phase D result: PASS / FAIL (environment variables confirmed set before proceeding)

---

### Phase E — Start Local OpenClaw Server

> Requires explicit operator approval.

```bash
cd ~/kaiju
~/kaiju/.venv/bin/python3 -m uvicorn openclaw.server:app \
  --host 127.0.0.1 --port 8100
```

Confirm health check:
```bash
curl http://127.0.0.1:8100/openclaw/health
# Expected: {"ok": true}
```

Also confirm GCP backend is active:
```bash
curl http://127.0.0.1:8100/openclaw/health
```

Phase E result: PASS / FAIL (server healthy before proceeding to Phase F)

---

### Phase F — Write Fake Google Ads Credential Bundle

**Endpoint:** `POST /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads`
**Required scope:** WRITE (satisfied by ADMIN token)

```bash
curl -s -X POST \
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
- `credential_status.configured: true`
- `secret_status.configured: true`
- All four `configured_fields: true`
- No secret values in response
- No `credential_ref` or `secret_id` in response body

**If write fails:** stop — do not proceed to Phase G. See Section 12 (Failure Handling).

Phase F result: PASS / FAIL

---

### Phase G — Read Metadata / Status Only

**Endpoint:** `GET /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/status`
**Required scope:** READ

```bash
curl -s -X GET \
  "http://127.0.0.1:8100/openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/status" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Expected result:**
- HTTP `200`
- `ok: true`
- `credential_status.exists: true`
- `credential_status.status: configured`
- `secret_status.configured: true`
- All four `configured_fields: true`
- No secret values in response

Phase G result: PASS / FAIL

---

### Phase H — Structural Validate Endpoint

**Endpoint:** `POST /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/validate`
**Required scope:** VALIDATE (satisfied by ADMIN token)

```bash
curl -s -X POST \
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
- No Google Ads API call made — `live_api_tested: false` confirms this

Phase H result: PASS / FAIL

---

### Phase I — Rotate Fake Credential Bundle

**Endpoint:** `POST /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/rotate`
**Required scope:** ROTATE (satisfied by ADMIN token only)

```bash
curl -s -X POST \
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
- `credential_status.status: active`
- `secret_status.configured: true`
- All four `configured_fields: true`
- No secret values in response

**Optional GCP version observation (operator-controlled, private):**
If the operator inspects `gcloud secrets versions list` from a secure terminal (not echoed), record only: version count (integer). The prior V1 version remains enabled — this is a known limitation. Do not record version names, resource paths, or the secret ID.

Phase I result: PASS / FAIL

---

### Phase J — Delete / Revoke Fake Credential Bundle

> Requires explicit operator approval to enable `OPENCLAW_ADMIN_DELETE_ENABLED=true`.
> Restart the server with this env var set before executing this phase.

**Endpoint:** `DELETE /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads`
**Required scope:** DELETE (satisfied by ADMIN token) and `OPENCLAW_ADMIN_DELETE_ENABLED=true`

```bash
curl -s -X DELETE \
  "http://127.0.0.1:8100/openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Expected result:**
- HTTP `200`
- `ok: true`
- `credential_status.status: revoked`
- `secret_status.configured: false`
- All four `configured_fields: false`
- `warnings`: empty or `["secret_already_absent"]` only
- No secret values in response

**After this phase:** restore `OPENCLAW_ADMIN_DELETE_ENABLED=false` or stop the test server before proceeding.

Phase J result: PASS / FAIL

---

### Phase K — Post-Delete Status Check

**Endpoint:** `GET /openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/status`
**Required scope:** READ

```bash
curl -s -X GET \
  "http://127.0.0.1:8100/openclaw/admin/tenants/<TENANT_ID_REHEARSAL>/clients/<CLIENT_ID_REHEARSAL>/credentials/google-ads/status" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Expected result:**
- HTTP `200`
- `credential_status.status: revoked`
- `secret_status.configured: false`
- No secret values in response

Phase K result: PASS / FAIL

---

### Phase L — Audit Verification

Use `verify_audit_file()` on the temp audit JSONL created during this session. The audit root is `<TEMP_AUDIT_ROOT_OUTSIDE_REPO>`.

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/kaiju"))
from openclaw.audit import verify_audit_file

result = verify_audit_file("<TEMP_AUDIT_ROOT_OUTSIDE_REPO>/YYYY-MM-DD.jsonl")
# Expected: {"ok": True, "events_checked": N, "errors": [], "warnings": []}
print(result)
```

**Expected result:**
- `ok: true`
- `events_checked`: N ≥ 4 (at least one event for bundle_write, validate, rotate, delete)
- `errors: []`
- `warnings: []`
- Sequence chain valid — `seq` increments 1, 2, 3… without gaps
- Digest chain valid — each `file_digest` matches SHA-256 of bytes before that append
- `lock_used: true` on each event (Linux — fcntl locking active)

**Expected operations in audit events (field names only):**

| operation | expected present |
|---|---|
| `bundle_write` | yes |
| `validate` | yes |
| `rotate` | yes |
| `delete` | yes |

**Forbidden fields confirmation (inspect locally — do not share):**
Confirm none of the following appear in any audit event line:
- `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`
- `developer_token`, `client_secret`, `refresh_token`, `access_token`

Record only: `ok`, `events_checked`, `errors`, forbidden-fields-absent confirmation.

Phase L result: PASS / FAIL

---

### Phase M — Secret Manager Cleanup Verification

> Requires explicit operator approval before running gcloud cleanup commands.

```
Cleanup checklist:

  [ ] Rehearsal GCP secret is absent:
        gcloud secrets list --filter="name~kaiju-rehearsal" returns empty
  [ ] Temp CredentialReference store (<TEMP_REFERENCE_STORE_OUTSIDE_REPO>) removed
        or archived outside the repo — not committed
  [ ] Temp audit files (<TEMP_AUDIT_ROOT_OUTSIDE_REPO>) archived outside repo or deleted —
        not committed, not inside ~/kaiju/
  [ ] No new .env file created inside the repo during this session
  [ ] No credential JSON file created inside the repo during this session
  [ ] git status --short shows only gitignored runtime files (if any)
  [ ] OPENCLAW_ADMIN_DELETE_ENABLED restored to false or server stopped
  [ ] Shell history containing fake token values cleared per operator policy
```

Phase M result: PASS / FAIL

---

### Phase N — Results Redaction and Documentation

After all phases A–M complete:

1. Fill in `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md` using the redaction rules in Section 9
2. Confirm the results doc contains no project IDs, service account emails, credential paths, token values, fake secret values, `credential_ref`, or `secret_id`
3. Run final `git status` — confirm no unintended files staged
4. Request operator review of results doc before committing
5. Commit only: `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md` and any minimal code changes required by findings
6. Do not commit `.env`, credential JSON, audit JSONL, or runtime files

Phase N result: COMPLETE / INCOMPLETE

---

## 11. Cleanup Policy

- The rehearsal GCP secret must be deleted before the validation session closes (Phase J handles this)
- All temp files (`TEMP_AUDIT_ROOT_OUTSIDE_REPO`, `TEMP_REFERENCE_STORE_OUTSIDE_REPO`) must be removed or archived outside the repo
- No audit JSONL files from this session may be committed to the repo
- No runtime credential reference JSON may be committed to the repo
- `OPENCLAW_ADMIN_DELETE_ENABLED=true` must not persist in any running server after Phase J

---

## 12. Evidence Policy

| What to record | Where | Format |
|---|---|---|
| Phase pass/fail | `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md` | Table row — redacted |
| HTTP status codes | Results doc | Integer |
| `ok` booleans | Results doc | Boolean |
| `credential_status` values | Results doc | Status string + configured boolean |
| `configured_fields` map | Results doc | Field name → boolean only |
| Audit verification result | Results doc | `ok`, `events_checked`, `errors` |
| GCP version count (optional) | Results doc | Integer only |
| Failures or deviations | Results doc | Error code strings + description |

**Never record:** project ID, service account, credential paths, token values, fake secret values, `credential_ref`, `secret_id`, raw JSON bodies containing the above.

---

## 13. Failure Handling

**Phase F (write) fails:**
- Stop. Do not proceed to Phase G or later.
- Inspect `errors[].code` only — do not log or share raw GCP error messages.
- Common causes:
  - `gcp_project_id_missing` — `GCP_PROJECT_ID` not set
  - `gcp_secret_access_denied` — IAM `secretCreator` or `secretVersionAdder` missing
  - `gcp_dependency_missing` — `google-cloud-secret-manager` not installed
  - `gcp_secret_write_failed` — generic GCP API failure; check quota and API enablement

**Phase H (validate) fails:**
- Inspect `configured_fields` map (field names only) for missing fields
- Do not inspect the raw secret payload to diagnose
- If `structurally_complete: false` after a successful Phase F, something interrupted the secret write path — retry Phase F before proceeding

**Phase I (rotate) fails:**
- Check `rotation_result.missing_fields`
- If `invalid_status_for_rotation` (409), credential was unexpectedly REVOKED — investigate CredentialReference status
- Retry with a known-good fake bundle if appropriate

**Phase J (delete) fails:**
- Check `errors[].code`. If `delete_not_enabled`, confirm `OPENCLAW_ADMIN_DELETE_ENABLED=true` in the running server
- If `secret_delete_failed`, the GCP delete may have failed — run cleanup verification manually via `gcloud`
- Do not leave `OPENCLAW_ADMIN_DELETE_ENABLED=true` active after the session

**Phase L (audit verification) fails:**
- Preserve the audit JSONL file outside the repo — do not commit it
- Record `errors` list from `verify_audit_file()` in the results doc
- Stop and investigate before marking the phase PASS

**Any secret value accidentally printed to a shared terminal or log:**
- Treat as a security incident
- Discard logs containing the value
- Do not post the value anywhere
- Rotate the affected fake credential set (they are fake, but the incident response practice applies)

---

## 14. Cost Posture

| Item | Status |
|---|---|
| New GCP resources created | None beyond the one rehearsal secret (ephemeral — deleted in Phase J) |
| Fixed-cost infrastructure | None |
| Cloud Run | Not deployed |
| Compute Engine, GKE, Cloud SQL, Pub/Sub, BigQuery, Redis | Not created |
| GCP Secret Manager cost | One secret with two versions (V1 and V2) for the duration of the validation session only; deleted before session closes; minimal cost |
| API enablement | None — Secret Manager API must already be enabled |

---

## 15. Deferred Items

The following are explicitly out of scope for V5.18 and remain deferred:

- Real Google Ads OAuth credential onboarding (requires explicit operator approval and separate gating)
- Cloud Run deployment (requires service account, IAM, billing authorization)
- GCP Secret Manager version destruction / disable policy on rotate
- Redis/Memorystore distributed rate limiting
- BigQuery audit replication / Cloud Storage audit archival
- KMS/HSM cryptographic audit signing
- OAuth2 / admin identity provider integration
- Real Google Ads live API validation
- Multi-instance production rate limiting
- Frontend credential UI

---

## 16. Acceptance Criteria

This validation is PASS when all of the following are true:

- [ ] All phases A through M completed without a blocking failure
- [ ] Phase N (results documentation) complete and reviewed
- [ ] No real Google Ads credentials used in any phase
- [ ] `GOOGLE_ADS_LIVE_ENABLED=false` throughout — confirmed at start and end
- [ ] No Google Ads API calls made
- [ ] No secret values (fake or real) recorded in any committed document
- [ ] `credential_ref` and `secret_id` not recorded in any committed document
- [ ] Cleanup verified: rehearsal GCP secret absent, no temp files in repo
- [ ] Audit verification: `verify_audit_file()` returned `ok=true`
- [ ] `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md` completed, reviewed, and committed (redacted)
- [ ] No new IAM changes, billing changes, or fixed-cost infrastructure created

---

## 17. Related Documents

| Document | Purpose |
|---|---|
| [docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md](V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md) | Results template — fill in after operator-run validation |
| [docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md](V5_17_LIVE_GCP_VALIDATION_PLAN.md) | V5.17 validation plan (predecessor — phases A–H) |
| [docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md](V5_17_LIVE_GCP_VALIDATION_RESULTS.md) | V5.17 results template (unfilled — not executed) |
| [docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md](CREDENTIAL_LIFECYCLE_RUNBOOK.md) | Full operator credential lifecycle guide: token setup, endpoints, error codes, checklists |
| [docs/GCP_SECRET_MANAGER_RUNBOOK.md](GCP_SECRET_MANAGER_RUNBOOK.md) | GCP IAM setup, secret naming, rotation, failure modes |
| [docs/V5_17_BRANCH_CLOSURE.md](V5_17_BRANCH_CLOSURE.md) | V5.17 implementation summary and known limitations |
| [docs/RELEASE_NOTES_V5_17_0_BETA.md](RELEASE_NOTES_V5_17_0_BETA.md) | V5.17 release notes: endpoint changes, security guarantees, operator notes |
| [openclaw/admin.py](../openclaw/admin.py) | All credential lifecycle function implementations |
| [openclaw/audit.py](../openclaw/audit.py) | `append_audit_event()` with fcntl locking |
| [agents/ads-agent/credentials/gcp_secret_manager_store.py](../agents/ads-agent/credentials/gcp_secret_manager_store.py) | `GCPSecretManagerStore`: `put_secret_bundle`, `get_secret_status`, `delete_secret_bundle` |
| [docs/ROADMAP.md](ROADMAP.md) | Full project roadmap |

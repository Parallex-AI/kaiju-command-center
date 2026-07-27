# Release Notes — v5.15.0-beta

**Branch:** `v5.15-credential-lifecycle-hardening`
**Base:** `v5.14.0-beta`
**Tag candidate:** `v5.15.0-beta`
**Status:** Complete — ready for merge and tag

---

## Release Summary

v5.15.0-beta completes the credential lifecycle hardening cycle following V5.14's admin credential bundle write. Three phases were implemented: safe audit events on all credential write paths, a structural validation endpoint that confirms secret presence without ever fetching secret values, and a revoke/delete endpoint gated behind an explicit operator opt-in. All paths in the validate and delete routes use `get_secret_status()` or `delete_secret_bundle()` only — `get_secret_bundle()` is never called. Existing metadata-only and bundle write behavior is fully preserved. No real credentials were used. No fixed-cost infrastructure was created.

---

## Highlights

- **Credential audit events on all write paths** — `upsert_google_ads_credential_reference()` emits `operation="metadata_upsert"`; `write_google_ads_credential_bundle()` emits `operation="bundle_write"`; audit events never include `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, or any secret value
- **Structural validation endpoint** — `POST /credentials/google-ads/validate` checks that all required secret fields are present in `SecretStore` using `get_secret_status()` only; updates `CredentialReference` to `ACTIVE` or `VALIDATION_FAILED`; sets `last_validated_at`; `live_api_tested` always `false`
- **Revoke/delete endpoint** — `DELETE /credentials/google-ads` requires `OPENCLAW_ADMIN_DELETE_ENABLED=true`; disabled by default (403); calls `delete_secret_bundle()` only; marks status `REVOKED`; idempotent on already-absent secrets
- **No `get_secret_bundle()` in validate or delete paths** — confirmed by code review and smoke test section 14
- **All existing behavior preserved** — `POST /credentials/google-ads` metadata-only and bundle write paths unchanged; `GET /credentials/google-ads/status` unchanged
- **76/76 lifecycle demo assertions** — function-level demo covers sections A–K end-to-end
- **Zero real credentials used** — fake field values only; `GOOGLE_ADS_LIVE_ENABLED=false` throughout
- **Zero fixed-cost infrastructure** — no Cloud Run, GKE, Cloud SQL, Pub/Sub, or any fixed-cost service

---

## What Changed

### `openclaw/audit.py`

Added `build_credential_audit_event(tenant_id, client_id, integration_type, operation, ok, request_id, trace_id, error_codes)`:

- New function distinct from the existing `build_audit_event()` (which is for OpenClaw process responses)
- Returns: `timestamp`, `event_type="credential_operation"`, `tenant_id`, `client_id`, `integration_type`, `operation`, `ok`, `error_codes`, `request_id`, `trace_id`, `source="openclaw_admin"`
- Deliberately never includes: `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, or any secret value

### `openclaw/admin.py`

**Phase 1 additions:**
- `_emit_credential_audit_event()` — private helper; swallows all exceptions; never affects write outcome
- `upsert_google_ads_credential_reference()` wired to emit `operation="metadata_upsert"` on success and on error
- `write_google_ads_credential_bundle()` wired to emit `operation="bundle_write"` on success and on error

**Phase 2 addition:**
- `validate_google_ads_credentials(tenant_id, client_id, secret_store=None)`:
  - Loads `CredentialReference`; resolves `credential_ref` internally
  - Calls `secret_store.get_secret_status(credential_ref, integration_type)` — no raw values returned
  - Checks all required fields present; updates status to `ACTIVE` or `VALIDATION_FAILED`
  - Returns `validation_result` with `structurally_complete`, `missing_fields`, `last_validated_at`, `live_api_tested=false`
  - Emits `operation="validate"` audit event

**Phase 3 additions:**
- `_is_admin_delete_enabled()` — reads `OPENCLAW_ADMIN_DELETE_ENABLED` from `os.environ` at call time; `"false"` by default
- `delete_google_ads_credentials(tenant_id, client_id, secret_store=None)`:
  - Checks env gate first — exits immediately with `delete_not_enabled` if not enabled
  - Loads `CredentialReference`; resolves `credential_ref` internally
  - Calls `secret_store.delete_secret_bundle(credential_ref, integration_type)` only
  - `True` → deleted; `False` → idempotent (`warnings=["secret_already_absent"]`); exception → `secret_delete_failed`
  - Updates `CredentialReference` to `REVOKED`; calls `get_secret_status()` for redacted confirmation
  - Emits `operation="delete"` audit event

### `openclaw/server.py`

Added two new admin routes:

```
POST  /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/validate
DELETE /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads
```

HTTP response codes:
- Validate: 200 (ran), 404 (`credential_not_found`), 400 (other errors), 401 (auth)
- Delete: 200 (success or idempotent), 403 (`delete_not_enabled`), 404 (`credential_not_found`), 400 (other errors), 401 (auth)

### `scripts/smoke_test_v5_credentials.sh`

Extended from 10 to 14 sections:

| Section | Coverage |
|---------|---------|
| `[11/14]` | Lifecycle audit and validation events — function-level demo (A–K), delete markers H/I/J |
| `[12/14]` | Lifecycle API (TestClient) — Validate B/A/C + Delete E/A/B/C markers |
| `[13/14]` | Validate route server-level auth (401 without token, 404 with token but no ref) |
| `[14/14]` | Phase 3 forbidden behavior: no `.get_secret_bundle()` in admin.py, `GOOGLE_ADS_LIVE_ENABLED=true` absent from demo files, `GCP_SECRET_MANAGER_ENABLED=true` absent from lifecycle demos, delete gate reads `os.environ`, audit event shape excludes all four forbidden fields |

### New demo files

| File | Purpose |
|------|---------|
| `openclaw/run_admin_credentials_lifecycle_demo.py` | Function-level lifecycle demo — sections A–K · 76/76 assertions |
| `openclaw/run_admin_credentials_lifecycle_api_demo.py` | FastAPI TestClient lifecycle demo — Validate B/A/C + Delete E/A/D/B/C |

---

## Endpoint Changes

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| `GET` | `/credentials/google-ads/status` | Unchanged | Read-only metadata status |
| `POST` | `/credentials/google-ads` | Unchanged | Metadata upsert or full bundle write |
| `POST` | `/credentials/google-ads/validate` | **New** | Structural validation · `get_secret_status()` only |
| `DELETE` | `/credentials/google-ads` | **New** | Revoke/delete · `OPENCLAW_ADMIN_DELETE_ENABLED=true` required |

---

## Validation Completed

| Phase | What was validated | Result |
|-------|-------------------|--------|
| 1 — Audit emission | Lifecycle demo A–D: audit event shape, no forbidden fields in events, global leak assertion | **PASS** |
| 2 — Validate demo | `validate_google_ads_credentials()` function: complete → `ACTIVE`, missing ref → 404, incomplete → `VALIDATION_FAILED` | **PASS** |
| 2 — Validate API | TestClient Validate B (404), A (200, complete, `status=active`), C (200, incomplete, `status=validation_failed`) | **PASS** |
| 3 — Delete demo | `delete_google_ads_credentials()` function: gate disabled, gate enabled success, idempotent, missing credential | **PASS** |
| 3 — Delete API | TestClient Delete E (401), A (403), D (404), B (200 revoked), C (200 idempotent) | **PASS** |

---

## Security Guarantees

These invariants held throughout all validation phases and are enforced by design:

| Invariant | How enforced |
|-----------|--------------|
| Audit events never include secret values | `build_credential_audit_event()` takes only `operation`, `ok`, `error_codes` — no payload fields; confirmed by section 14 smoke check |
| Audit events never include `credential_ref`, `secret_id`, `customer_id`, `login_customer_id` | Same function design; forbidden fields not in the function signature |
| Validate path never fetches secrets | Only `get_secret_status()` called — returns boolean field presence; `get_secret_bundle()` not called |
| Delete path never reads secrets | Only `delete_secret_bundle()` and `get_secret_status()` called; no bundle fetch |
| Delete disabled by default | `_is_admin_delete_enabled()` returns `False` unless `OPENCLAW_ADMIN_DELETE_ENABLED` is exactly `"true"` |
| Idempotent delete is safe | `delete_secret_bundle()` returning `False` → `ok=true`, `warnings=["secret_already_absent"]`; status updated to `REVOKED` regardless |
| No real credentials committed | Secret-safety grep confirms clean; all test values are `fake-*` prefixed |
| Credential reference store in temp dir | All demos and TestClient tests use isolated temp paths |
| No live Google Ads API calls | `GOOGLE_ADS_LIVE_ENABLED=false` throughout; no `GoogleAdsClient` in any lifecycle path |

---

## Cost Guarantees

| Guarantee | Status |
|-----------|--------|
| Pay-per-use only | No standing GCP resources created |
| No fixed-cost infrastructure | No Cloud Run, GKE, Compute Engine, Cloud SQL, BigQuery, Pub/Sub, Scheduler, Load Balancer, NAT Gateway, Redis/Memorystore |
| No IAM changes | Confirmed |
| No billing changes | Confirmed |
| No API enablement | Confirmed |
| No production deployment | Confirmed |

---

## Smoke Tests

| Suite | Result |
|-------|--------|
| `scripts/smoke_test_v5_credentials.sh` | **14/14 PASS** — env/imports, model demo, stores, resolver, secret store + provider, adapter non-live, OpenClaw admin endpoints, secret-safety + git hygiene, mocked bundle demo, API write demo, lifecycle audit + delete events, lifecycle API validate + delete, validate auth, Phase 3 forbidden behavior |
| `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **8/8 PASS** — imports, disabled mode, read/status mock, write mock, delete/list mock, factory behavior, provider/factory integration, secret-safety + git hygiene |
| `openclaw/run_admin_credentials_lifecycle_demo.py` | **76/76 PASS** — sections A–K |
| `openclaw/run_admin_credentials_lifecycle_api_demo.py` | **PASS** — Validate B/A/C + Delete E/A/D/B/C |

---

## Operator Notes

No migration steps are required to upgrade from v5.14.0-beta. All new behavior is additive and env-gated.

**To validate stored credentials structurally:**

```bash
curl -X POST \
  http://localhost:<port>/openclaw/admin/tenants/<tenant_id>/clients/<client_id>/credentials/google-ads/validate
```

Returns `validation_result.structurally_complete=true` when all four secret fields are present in `SecretStore`. `live_api_tested` is always `false` — this endpoint does not call the Google Ads API.

**To revoke and delete a credential bundle:**

```bash
# Requires OPENCLAW_ADMIN_DELETE_ENABLED=true in the server environment
curl -X DELETE \
  http://localhost:<port>/openclaw/admin/tenants/<tenant_id>/clients/<client_id>/credentials/google-ads
```

Returns `credential_status.status=revoked` and `secret_status.configured=false` on success. Calling again when the secret is already absent returns `ok=true` with `warnings=["secret_already_absent"]`.

**Environment variables added in V5.15:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENCLAW_ADMIN_DELETE_ENABLED` | `false` | Enables `DELETE /credentials/google-ads`; must be `"true"` to allow destructive operation |

---

## Not Included in v5.15.0-beta

The following remain deferred:

- **Live API validation** — `validate` confirms structural completeness only; no Google Ads API call; `live_api_tested` always `false`
- **Live GCP delete path validation** — all delete tests used `InMemorySecretStore`; `GCPSecretManagerStore` delete path not validated in this branch
- **Real Google Ads credentials** — `GOOGLE_ADS_LIVE_ENABLED=false` throughout; no real credentials used or validated
- **RBAC hardening** — delete endpoint is env-gated only; no per-tenant IAM or role-based access control
- **Secret rotation UX** — no rotation endpoint; current write path overwrites in place
- **Audit log tamper-resistance** — audit JSONL is append-only; no cryptographic integrity protection
- **Rate limiting** — no per-tenant or global rate limiting on admin endpoints
- **Frontend credential UI** — deferred to a future branch
- **OAuth consent flow** — not in scope

---

## Recommended Next Steps

1. **Merge and tag** — merge `v5.15-credential-lifecycle-hardening` into `master`; tag `v5.15.0-beta`
2. **V5.16 credential lifecycle production hardening** — RBAC/IAM authorization on admin endpoints, audit persistence hardening, rotation workflow (`POST /credentials/google-ads/rotate`), operator runbook for real credential operations
3. **Live GCP lifecycle validation** — controlled validation of write → validate → delete through `GCPSecretManagerStore` with fake values only
4. **Controlled real credential onboarding** — once structural validation and rotation are hardened, controlled onboarding of real (non-production) Google Ads credentials under `GOOGLE_ADS_LIVE_ENABLED=false`
5. **Cloud Run deployment** — deploy OpenClaw to Cloud Run with `GCPSecretManagerStore`, IAM-scoped service account, and a tested credential operation runbook

All steps should maintain the established guardrails: pay-as-you-go only, no fixed-cost infrastructure, no secrets committed, explicit operator approval before any live Google Ads API call.

---

## Related Documents

- [V5.15 Branch Closure](V5_15_BRANCH_CLOSURE.md)
- [Release Notes — v5.14.0-beta](RELEASE_NOTES_V5_14_0_BETA.md)
- [V5.14 Branch Closure](V5_14_BRANCH_CLOSURE.md)
- [Release Notes — v5.13.0-beta](RELEASE_NOTES_V5_13_0_BETA.md)
- [V5.13 Branch Closure](V5_13_BRANCH_CLOSURE.md)
- [V5.12 GCP Secret Manager Release Notes](V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

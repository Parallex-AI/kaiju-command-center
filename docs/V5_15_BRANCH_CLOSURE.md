# V5.15 Branch Closure — Credential Lifecycle Hardening

**Branch:** `v5.15-credential-lifecycle-hardening`
**Base tag:** `v5.14.0-beta`
**Target release tag candidate:** `v5.15.0-beta`
**Status:** Complete — all phases PASS · closure docs complete · ready for merge and tag

---

## Summary

V5.15 completes the credential lifecycle story begun in V5.14. Three phases were implemented and committed: (1) safe credential audit events on all write paths, (2) a structural validation endpoint that confirms secret presence without fetching secret values, and (3) a revoke/delete endpoint gated behind an explicit environment variable. All paths use `get_secret_status()` or `delete_secret_bundle()` only — `get_secret_bundle()` is never called in the validate or delete paths. No Google Ads live API calls were made. No real credentials were used. No fixed-cost infrastructure was created. All six smoke suites pass.

---

## Scope

This branch covered three implementation phases for the OpenClaw admin credential lifecycle:

- **Phase 1** — Credential audit events: `build_credential_audit_event()` in `openclaw/audit.py`; audit emission wired into all credential write paths
- **Phase 2** — Structural validation endpoint: `POST /credentials/google-ads/validate`; confirms secret presence using `get_secret_status()` only; no live Google Ads API call
- **Phase 3** — Revoke/delete endpoint: `DELETE /credentials/google-ads`; gated behind `OPENCLAW_ADMIN_DELETE_ENABLED=true`; marks `CredentialReference` as `REVOKED`; idempotent

What was not in scope: production deployment, real Google Ads OAuth credential onboarding, live API validation, RBAC hardening, frontend UI, OAuth consent flow, secret rotation UX.

---

## Completed Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| Phase 1 | Credential audit events · `build_credential_audit_event()` · audit emission on upsert and bundle write | **Complete** |
| Phase 2 | Structural validation endpoint · `POST /credentials/google-ads/validate` · `get_secret_status()` only · updates status to `ACTIVE` or `VALIDATION_FAILED` | **Complete** |
| Phase 3 | Revoke/delete endpoint · `DELETE /credentials/google-ads` · `OPENCLAW_ADMIN_DELETE_ENABLED` gate · `delete_secret_bundle()` · status `REVOKED` · idempotent | **Complete** |
| Closure | Branch closure doc · release notes · ROADMAP update · README update · final smoke suites | **Complete** |

---

## Implementation Summary

### `openclaw/audit.py` — `build_credential_audit_event()`

Added `build_credential_audit_event(tenant_id, client_id, integration_type, operation, ok, request_id, trace_id, error_codes)`:

- Returns a structured audit event dict for credential operations
- Fields: `timestamp`, `event_type="credential_operation"`, `tenant_id`, `client_id`, `integration_type`, `operation`, `ok`, `error_codes`, `request_id`, `trace_id`, `source="openclaw_admin"`
- Deliberately excludes: `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, all secret values, all payload content
- Shape distinct from the existing `build_audit_event()` which is for OpenClaw process responses

### `openclaw/admin.py` — audit emission and new functions

**Audit emission (Phase 1):**
- Added `_emit_credential_audit_event()` helper — swallows all exceptions; never affects write outcome
- `upsert_google_ads_credential_reference()` emits `operation="metadata_upsert"` on success and on error
- `write_google_ads_credential_bundle()` emits `operation="bundle_write"` on success and on error

**Structural validation (Phase 2):**
- Added `validate_google_ads_credentials(tenant_id, client_id, secret_store=None)`:
  - Loads `CredentialReference` — returns `credential_not_found` if absent
  - Resolves `credential_ref` internally (never echoed)
  - Calls `get_secret_status()` — examines configured field booleans only
  - Updates `CredentialReference` to `ACTIVE` (all fields present) or `VALIDATION_FAILED` (any missing)
  - Sets `last_validated_at`
  - Returns `validation_result` with `structurally_complete`, `missing_fields`, `last_validated_at`, `live_api_tested=false`
  - Emits `operation="validate"` audit event

**Revoke/delete (Phase 3):**
- Added `_is_admin_delete_enabled()` — reads `OPENCLAW_ADMIN_DELETE_ENABLED` from `os.environ` at call time; default `"false"`
- Added `delete_google_ads_credentials(tenant_id, client_id, secret_store=None)`:
  - Checks env gate first — returns `delete_not_enabled` immediately if not enabled
  - Loads `CredentialReference` — returns `credential_not_found` if absent
  - Resolves `credential_ref` internally (never echoed)
  - Calls `delete_secret_bundle()` only — never calls `get_secret_bundle()`
  - `True` → secrets deleted; `False` → already absent (idempotent, `warnings=["secret_already_absent"]`); exception → `error_codes=["secret_delete_failed"]`
  - Updates `CredentialReference` to `REVOKED` via `update_credential_status()`
  - Calls `get_secret_status()` for redacted confirmation in response
  - Emits `operation="delete"` audit event
  - Returns `credential_status`, `secret_status`, `warnings`, `errors`

### `openclaw/server.py` — new routes

**Phase 2:**
```
POST /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/validate
```
- Calls `validate_google_ads_credentials()`
- Returns 404 on `credential_not_found`; 200 when validation ran; 400 on other errors
- Auth via `validate_api_auth` — 401 if auth enabled and token absent or invalid

**Phase 3:**
```
DELETE /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads
```
- Calls `delete_google_ads_credentials()`
- Returns 403 on `delete_not_enabled`; 404 on `credential_not_found`; 200 on success; 400 on other errors
- Auth via `validate_api_auth` — 401 if auth enabled and token absent or invalid

### Demo files added/extended

| File | Purpose |
|------|---------|
| `openclaw/run_admin_credentials_lifecycle_demo.py` | Function-level lifecycle demo — sections A–K (76/76 assertions): audit events on write paths, validate scenarios, delete gate, delete success, idempotent delete, missing delete |
| `openclaw/run_admin_credentials_lifecycle_api_demo.py` | FastAPI TestClient lifecycle demo — Validate B/A/C + Delete E/A/D/B/C: auth, 403 gate, 404 missing, 200 success, 200 idempotent, cross-response leak assertion |

### Smoke suite extended

| File | Change |
|------|--------|
| `scripts/smoke_test_v5_credentials.sh` | Extended from 10 to 14 sections: sections 11–14 cover lifecycle audit demo, lifecycle API demo (validate + delete markers), validate route server-level auth, Phase 3 forbidden behavior checks |

---

## Endpoint Summary

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/credentials/google-ads/status` | Read-only status (existing — unchanged) |
| `POST` | `/credentials/google-ads` | Metadata upsert or full bundle write (existing — unchanged) |
| `POST` | `/credentials/google-ads/validate` | Structural validation — `get_secret_status()` only · no live API call |
| `DELETE` | `/credentials/google-ads` | Revoke/delete — `OPENCLAW_ADMIN_DELETE_ENABLED=true` required |

---

## Validation Phases

| Phase | What was validated | Result |
|-------|-------------------|--------|
| 1 — Audit events | Lifecycle function demo sections A–D: audit emission on upsert and bundle write, forbidden field content in audit events confirmed absent, global leak assertion | **PASS** |
| 2 — Validation demo | Lifecycle function demo sections E–G: `validate_google_ads_credentials()` with complete bundle → `ACTIVE`, missing credential → `credential_not_found`, incomplete → `VALIDATION_FAILED` | **PASS** |
| 2 — Validation API | TestClient Validate B (404), Validate A (200, `structurally_complete=true`, `status=active`), Validate C (200, `structurally_complete=false`, `status=validation_failed`) | **PASS** |
| 3 — Delete demo | Lifecycle function demo sections H–K: delete gate disabled → `delete_not_enabled`, delete enabled → `status=revoked`, idempotent → `secret_already_absent`, missing credential → `credential_not_found` | **PASS** |
| 3 — Delete API | TestClient Delete E (401 auth), Delete A (403 disabled), Delete D (404 missing), Delete B (200 success, `status=revoked`), Delete C (200 idempotent, `warnings=["secret_already_absent"]`) | **PASS** |

---

## Smoke Test Results

| Suite | Script | Result |
|-------|--------|--------|
| V5 credentials | `scripts/smoke_test_v5_credentials.sh` | **14/14 PASS** |
| V5.12 GCP Secret Manager | `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **8/8 PASS** |
| GCP write helper demo | `openclaw/run_admin_credentials_gcp_write_demo.py` | **PASS** |
| API write demo | `openclaw/run_admin_credentials_api_write_demo.py` | **PASS** |
| Lifecycle function demo | `openclaw/run_admin_credentials_lifecycle_demo.py` | **76/76 PASS** |
| Lifecycle API demo | `openclaw/run_admin_credentials_lifecycle_api_demo.py` | **PASS** |

All suites run without real GCP credentials. No live GCP calls. No live Google Ads API calls.

---

## Security Posture

| Property | Status |
|----------|--------|
| Audit events exclude `credential_ref` | Confirmed |
| Audit events exclude `secret_id` | Confirmed |
| Audit events exclude `customer_id` | Confirmed |
| Audit events exclude `login_customer_id` | Confirmed |
| Audit events exclude all secret values (`developer_token`, `client_secret`, `refresh_token`, `access_token`) | Confirmed |
| Validate path never calls `get_secret_bundle()` | Confirmed |
| Delete path never calls `get_secret_bundle()` | Confirmed |
| Delete path never reads or returns secret values | Confirmed |
| `OPENCLAW_ADMIN_DELETE_ENABLED` required for destructive operation — disabled by default | Confirmed |
| `get_secret_status()` returns configured-field booleans only | Confirmed |
| API responses never return raw secret values | Confirmed |
| `GOOGLE_ADS_LIVE_ENABLED=false` throughout | Confirmed |
| No real credentials used in any test or demo | Confirmed |
| No `.env` committed | Confirmed |
| No credential JSON committed | Confirmed |
| No runtime files committed | Confirmed |
| Secret-safety grep clean | Confirmed |
| No runtime credential files tracked by Git | Confirmed |

---

## Cost Posture

| Property | Status |
|----------|--------|
| No fixed-cost infrastructure created | Confirmed |
| No Cloud Run, GKE, or Compute Engine | Confirmed |
| No Cloud SQL, BigQuery, Pub/Sub, or Scheduler | Confirmed |
| No Load Balancer, NAT Gateway, or Redis/Memorystore | Confirmed |
| No committed use discounts or reserved capacity | Confirmed |
| No paid Marketplace services | Confirmed |
| No production deployment | Confirmed |
| No IAM changes | Confirmed |
| No billing changes | Confirmed |
| No API enablement | Confirmed |

---

## What Was Explicitly Not Done

- No production deployment (Cloud Run or otherwise)
- No real Google Ads OAuth credentials used or validated
- No Google Ads live API calls
- No live GCP endpoint delete validation (all delete tests used `InMemorySecretStore`)
- No user-facing credential submission or management UI
- No per-tenant RBAC or IAM-based authorization
- No OAuth-based admin authentication
- No secret rotation UX or rotation endpoint
- No GCP Secret Manager secret version destruction policy
- No audit log tamper-resistance hardening

---

## Known Limitations

- Validation is structural only — confirms that secret fields are present in `SecretStore`, but does not attempt a live Google Ads API call; `live_api_tested` remains `false`
- The delete endpoint is environment-gated but not yet RBAC-gated — any authenticated caller can delete when `OPENCLAW_ADMIN_DELETE_ENABLED=true`
- Audit log is append-only JSONL and not cryptographically tamper-resistant
- Rate limiting is not implemented on any admin endpoint
- Secret rotation (replace a bundle with a new one and revoke the old) has no dedicated endpoint; the current write path overwrites in place
- `InMemorySecretStore` was used for all automated delete validation; live GCP delete path was not validated in this branch

---

## Next Recommended Milestone

**V5.16 — Credential Lifecycle Production Hardening:**

1. **Authorization/RBAC** — per-tenant IAM isolation; role-based access to credential admin endpoints; token scope enforcement
2. **Audit persistence hardening** — structured credential audit log with tamper-evident properties; log rotation; retention policy
3. **Rotation workflow** — `POST /credentials/google-ads/rotate` endpoint; atomic bundle replacement; old credential version disabled
4. **Operator runbook** — step-by-step credential onboarding, validation, rotation, and revoke guide for real Google Ads credentials
5. **Optional live GCP lifecycle validation** — controlled validation of the full write → validate → delete lifecycle through `GCPSecretManagerStore` using fake values only
6. **Controlled readiness for real Google Ads OAuth onboarding** — once structural validation and rotation are hardened, controlled onboarding of real (non-production) credentials under `GOOGLE_ADS_LIVE_ENABLED=false`

All future milestones should maintain the established guardrails: pay-as-you-go only, no fixed-cost infrastructure, no secrets committed, explicit operator approval before any live Google Ads API call.

---

## Merge and Tag Recommendation

Once final review is complete:

```bash
git checkout master
git merge --no-ff v5.15-credential-lifecycle-hardening
git tag v5.15.0-beta
```

Tag message: `v5.15.0-beta — Credential lifecycle hardening: audit events, structural validation, revoke/delete (Phases 1–3 PASS)`

**Prerequisites before merge:**
- Final smoke suite pass (complete — 14/14 and 8/8 above)
- Secret-safety grep clean (complete — confirmed)
- No credential JSON in repo (complete — confirmed)
- Working tree clean (complete — confirmed)

---

## Related Documents

- [V5.14 Branch Closure](V5_14_BRANCH_CLOSURE.md)
- [Release Notes — v5.14.0-beta](RELEASE_NOTES_V5_14_0_BETA.md)
- [Release Notes — v5.15.0-beta](RELEASE_NOTES_V5_15_0_BETA.md)
- [V5.13 Branch Closure](V5_13_BRANCH_CLOSURE.md)
- [Release Notes — v5.13.0-beta](RELEASE_NOTES_V5_13_0_BETA.md)
- [V5.12 GCP Secret Manager Release Notes](V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

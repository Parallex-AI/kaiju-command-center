# V5.16 Branch Closure — Admin RBAC and Audit Hardening

**Branch:** `v5.16-admin-rbac-audit-hardening`
**Base:** `v5.15.0-beta` / master after `f5d40ac`
**Target release tag candidate:** `v5.16.0-beta`
**Status:** Complete — all phases PASS · closure docs complete · ready for merge and tag

---

## Summary

V5.16 hardens the OpenClaw admin credential lifecycle on three axes following V5.15's audit events and lifecycle endpoints. Phase 1 introduces token-scoped RBAC: a six-value `AdminScope` enum gates each admin endpoint at the minimum required privilege level, while preserving backward compatibility for existing API key configurations. Phase 2 adds audit sequence numbering and per-append file digest to the credential audit JSONL, exposes audit warning visibility on all write paths, and adds maintenance utilities for verification and pruning. Phase 3 adds a credential rotation endpoint (`POST /credentials/google-ads/rotate`) that replaces the stored secret bundle without reading it back and without calling the Google Ads API. All three phases use `get_secret_status()` for structural validation only — `get_secret_bundle()` is never called on any validate, delete, or rotate path. No real credentials were used. No fixed-cost infrastructure was created. All six smoke suites pass.

---

## Scope

Three implementation phases for the OpenClaw admin credential system:

- **Phase 1** — Token-scoped RBAC: `AdminScope` enum; `OPENCLAW_ADMIN_KEYS` / `OPENCLAW_READ_KEYS` env vars; per-endpoint minimum-scope enforcement; 401/403 distinction; backward-compatible API key fallback
- **Phase 2** — Audit seq/digest hardening: `seq` and `file_digest` fields on every credential audit event; `verify_audit_file()` and `prune_audit_files()` maintenance utilities; `audit_append_failed` warning visibility on all write paths; `OPENCLAW_AUDIT_RETAIN_DAYS` config
- **Phase 3** — Credential rotation endpoint: `rotate_google_ads_credentials()` in `openclaw/admin.py`; `POST /credentials/google-ads/rotate` route; `AdminScope.ROTATE` required; writes new bundle via `put_secret_bundle()` only; validates structurally via `get_secret_status()` only; emits `operation="rotate"` audit event

What was not in scope: production deployment, real Google Ads OAuth credential onboarding, live API validation, per-tenant IAM RBAC, KMS/HSM audit signing, audit BigQuery replication, GCP Secret Manager version destruction, frontend UI, OAuth consent flow.

---

## Completed Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| Phase 1 | Token-scoped RBAC · `AdminScope` enum · `OPENCLAW_ADMIN_KEYS` · `OPENCLAW_READ_KEYS` · per-endpoint minimum scope · 401/403 distinction · backward-compatible fallback | **Complete** |
| Phase 2 | Audit seq/digest hardening · `seq` + `file_digest` on every event · `verify_audit_file()` · `prune_audit_files()` · `audit_append_failed` warning visibility · `OPENCLAW_AUDIT_RETAIN_DAYS` | **Complete** |
| Phase 3 | Credential rotation endpoint · `rotate_google_ads_credentials()` · `POST /credentials/google-ads/rotate` · `AdminScope.ROTATE` · `put_secret_bundle()` only · `get_secret_status()` structural validation · `operation="rotate"` audit | **Complete** |
| Closure | Branch closure doc · release notes · ROADMAP update · README update · final smoke suites | **Complete** |

---

## Implementation Summary

### Phase 1 — Token-Scoped RBAC (`openclaw/auth.py`)

Added `AdminScope` enum with six values: `READ`, `WRITE`, `VALIDATE`, `ROTATE`, `DELETE`, `ADMIN`.

Scope hierarchy (ADMIN grants all scopes; other scopes are discrete):
- `scope_allows(ADMIN, X)` → `True` for all X
- `scope_allows(X, X)` → `True` (identity)
- `scope_allows(READ, WRITE)` → `False` (no implicit promotion)

New env vars:
- `OPENCLAW_ADMIN_KEYS` — comma-separated admin-scope tokens; grant `AdminScope.ADMIN` (all operations)
- `OPENCLAW_READ_KEYS` — comma-separated read-only tokens; grant `AdminScope.READ`
- `OPENCLAW_API_KEYS` — preserved as backward-compatible `READ`-only fallback

Auth logic:
- Missing/invalid token → `401 unauthorized`
- Valid token with insufficient scope → `403 scope_not_granted`
- `validate_api_auth()` accepts optional `required_scope` param; existing call sites without `required_scope` are unchanged

Per-endpoint minimum scope:
| Endpoint | Minimum scope |
|----------|--------------|
| `GET /credentials/google-ads/status` | `READ` |
| `POST /credentials/google-ads` | `WRITE` |
| `POST /credentials/google-ads/validate` | `VALIDATE` |
| `POST /credentials/google-ads/rotate` | `ROTATE` |
| `DELETE /credentials/google-ads` | `DELETE` |

`DELETE` still also requires `OPENCLAW_ADMIN_DELETE_ENABLED=true`.

### Phase 2 — Audit Seq/Digest Hardening (`openclaw/audit.py`, `openclaw/audit_maintenance.py`)

`append_audit_event()` now stamps two new fields on every emitted event:
- `seq` — monotonically increasing integer (1-based) per JSONL file; first event is `seq=1`
- `file_digest` — SHA-256 hex digest of the audit file bytes **before** the current append; first event digest is `""` (empty string, no prior content)

Added `verify_audit_file(path)`:
- Replays each event in order; recomputes expected `file_digest` from the bytes preceding each event; returns `{ok, total_events, valid_events, tampered_events, errors}`

Added `prune_audit_files(audit_root, retain_days)`:
- Deletes JSONL files older than `retain_days` days by file modification time
- Returns `{pruned_count, retained_count, errors}`

Added `OPENCLAW_AUDIT_RETAIN_DAYS` env var (default `90`) consumed by `prune_audit_files()`.

Credential write paths (`upsert_google_ads_credential_reference`, `write_google_ads_credential_bundle`, `validate_google_ads_credentials`, `delete_google_ads_credentials`, `rotate_google_ads_credentials`) now surface `audit_append_failed` in the response `warnings` list if audit append fails. Credential operations do not fail solely because audit append failed.

### Phase 3 — Credential Rotation (`openclaw/admin.py`, `openclaw/server.py`)

Added `rotate_google_ads_credentials(tenant_id, client_id, payload, secret_store=None)`:

Steps:
- **A** — Load `CredentialReference`; return `credential_not_found` if absent
- **B** — Reject `REVOKED` status → `invalid_status_for_rotation` (HTTP 409); allowed: `ACTIVE`, `CONFIGURED`, `VALIDATION_FAILED`
- **C** — Pre-write payload validation: require all four secret fields (`developer_token`, `client_id`, `client_secret`, `refresh_token`); return `secret_bundle_incomplete` with `missing_fields` if any absent; emit audit `ok=false`; no write occurs
- **D** — Resolve `SecretStore` (factory if not injected)
- **E** — `put_secret_bundle()` — writes new bundle; does not call `get_secret_bundle()`
- **F** — `get_secret_status()` — verifies configured fields structurally; no secret values returned
- **G** — Update `CredentialReference` to `ACTIVE` (all fields present) or `VALIDATION_FAILED` (any missing); set `last_validated_at`
- **H** — Emit `operation="rotate"` audit event
- **I** — Return response with `rotation_result`, `credential_status`, `secret_status`

Response `rotation_result` shape:
```json
{
  "structurally_complete": true,
  "missing_fields": [],
  "last_validated_at": "2026-07-28T00:00:00Z"
}
```

No `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, or secret values appear in any response or audit event.

Added route `POST /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/rotate`:
- Requires `AdminScope.ROTATE`
- HTTP 200 on success, 400 on business logic failure, 404 on `credential_not_found`, 409 on `invalid_status_for_rotation`
- 401/403 on auth failure

### Demo files added/extended

| File | Change |
|------|--------|
| `openclaw/run_admin_credentials_lifecycle_demo.py` | Sections P–T added: rotate active, rotate CONFIGURED, incomplete payload, rotate REVOKED, missing credential |
| `openclaw/run_admin_credentials_lifecycle_api_demo.py` | Rotate scenarios A–F added: success, not-found (404), revoked (409), incomplete (400), read-token denied (403), admin-token ok (200); leak assertion extended to 20 responses |

### Smoke suite extended

| File | Change |
|------|--------|
| `scripts/smoke_test_v5_credentials.sh` | Extended from 14 to 17 sections; sections 15–17 cover RBAC scope matrix, audit seq/digest/tamper/prune/warning markers, and rotate endpoint (import, route, RBAC, forbidden behavior, TestClient 200/404/409/403, lifecycle markers) |

---

## Endpoint Summary

| Method | Path | Minimum scope | Notes |
|--------|------|---------------|-------|
| `GET` | `/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/status` | `READ` | Read-only metadata status |
| `POST` | `/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads` | `WRITE` | Metadata upsert or full bundle write |
| `POST` | `/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/validate` | `VALIDATE` | Structural validation — `get_secret_status()` only |
| `POST` | `/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/rotate` | `ROTATE` | Bundle rotation — `put_secret_bundle()` + `get_secret_status()` only |
| `DELETE` | `/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads` | `DELETE` | Revoke/delete — also requires `OPENCLAW_ADMIN_DELETE_ENABLED=true` |

---

## Validation Phases

| Phase | What was validated | Result |
|-------|-------------------|--------|
| 1 — RBAC scope matrix | `scope_allows()` for all combinations; `ADMIN` grants all; `READ` grants `READ` only; 401 on missing token; 403 on insufficient scope; backward-compatible `OPENCLAW_API_KEYS` fallback | **PASS** |
| 1 — RBAC API | TestClient: READ token on WRITE endpoint → 403; ADMIN token on WRITE endpoint → 200; no token when auth enabled → 401 | **PASS** |
| 2 — Audit seq/digest | Lifecycle demo: `seq=1` on first event; `seq` increments per append; `file_digest` matches pre-append SHA-256; `verify_audit_file()` detects tampered event; `prune_audit_files()` removes old files; `audit_append_failed` in warnings when append fails | **PASS** |
| 3 — Rotate function | `rotate_google_ads_credentials()`: active → ok=true, status=active; CONFIGURED → ok=true; incomplete payload → ok=false, missing_fields, no write; REVOKED → invalid_status_for_rotation; missing → credential_not_found | **PASS** |
| 3 — Rotate API | TestClient: full bundle → 200 ok=true; missing credential → 404; REVOKED → 409; incomplete payload → 400; READ token → 403; ADMIN token → 200 | **PASS** |

---

## Smoke Test Results

| Suite | Script | Result |
|-------|--------|--------|
| V5 credentials | `scripts/smoke_test_v5_credentials.sh` | **17/17 PASS** |
| V5.12 GCP Secret Manager | `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **8/8 PASS** |
| GCP write helper demo | `openclaw/run_admin_credentials_gcp_write_demo.py` | **PASS** |
| API write demo | `openclaw/run_admin_credentials_api_write_demo.py` | **PASS** |
| Lifecycle function demo | `openclaw/run_admin_credentials_lifecycle_demo.py` | **PASS** |
| Lifecycle API demo | `openclaw/run_admin_credentials_lifecycle_api_demo.py` | **PASS** |

All suites run without real GCP credentials. No live GCP calls. No live Google Ads API calls.

---

## Security Posture

| Property | Status |
|----------|--------|
| `OPENCLAW_API_KEYS` is `READ`-only fallback — no WRITE/VALIDATE/ROTATE/DELETE via old key | Confirmed |
| `WRITE`/`VALIDATE`/`ROTATE`/`DELETE` require explicit scope or `ADMIN` | Confirmed |
| Valid token with insufficient scope returns `403 scope_not_granted` — not `401` | Confirmed |
| Missing or invalid token returns `401 unauthorized` | Confirmed |
| `DELETE` requires RBAC scope **and** `OPENCLAW_ADMIN_DELETE_ENABLED=true` | Confirmed |
| Validate path never calls `get_secret_bundle()` | Confirmed |
| Delete path never calls `get_secret_bundle()` | Confirmed |
| Rotate path never calls `get_secret_bundle()` | Confirmed |
| Validate / delete / rotate paths never call Google Ads API | Confirmed |
| Audit events exclude `credential_ref` | Confirmed |
| Audit events exclude `secret_id` | Confirmed |
| Audit events exclude `customer_id` | Confirmed |
| Audit events exclude `login_customer_id` | Confirmed |
| Audit events exclude all secret values (`developer_token`, `client_secret`, `refresh_token`, `access_token`) | Confirmed |
| API responses never return raw secret values | Confirmed |
| `rotation_result.missing_fields` contains field names only — no values | Confirmed |
| `GOOGLE_ADS_LIVE_ENABLED=false` throughout | Confirmed |
| No real credentials used in any test or demo | Confirmed |
| No `.env` committed | Confirmed |
| No credential JSON committed | Confirmed |
| No runtime files committed | Confirmed |
| Secret-safety grep clean | Confirmed |

---

## Cost Posture

| Property | Status |
|----------|--------|
| No fixed-cost infrastructure created | Confirmed |
| No Cloud Run, GKE, or Compute Engine | Confirmed |
| No Cloud SQL, BigQuery, Pub/Sub, or Scheduler | Confirmed |
| No Load Balancer, NAT Gateway, or Redis/Memorystore | Confirmed |
| No committed use discounts or reserved capacity | Confirmed |
| No IAM changes | Confirmed |
| No billing changes | Confirmed |
| No API enablement | Confirmed |
| No production deployment | Confirmed |

---

## What Was Explicitly Not Done

- No production deployment (Cloud Run or otherwise)
- No real Google Ads OAuth credentials used, stored, or validated
- No Google Ads live API calls
- No live GCP lifecycle validation (all tests used `InMemorySecretStore`)
- No GCP IAM/RBAC integration (RBAC is token-scope based, not IAM or OAuth)
- No OAuth2 admin authentication
- No per-tenant permission model or row-level RBAC
- No KMS or HSM audit log signing
- No cryptographic tamper-evidence on audit JSONL
- No BigQuery audit log replication
- No GCP Secret Manager version destruction policy for rotated secrets
- No concurrent-writer safety on audit append
- No user-facing credential management UI

---

## Known Limitations

- RBAC is token-scope based only — not IAM-backed, OAuth-backed, or per-tenant; any caller with an `OPENCLAW_ADMIN_KEYS` token can act on any tenant
- Audit `seq`/`file_digest` is tamper-evident but not cryptographically signed; a filesystem actor with write access can modify or truncate the JSONL
- Audit append is not concurrent-writer safe; simultaneous appends from multiple processes may corrupt `seq` ordering
- Rotation replaces the bundle through the `SecretStore` abstraction; it does not destroy or disable the prior GCP Secret Manager secret version
- Structural validation confirms configured field presence only — `live_api_tested` remains `false`; no Google Ads API handshake is performed
- Rate limiting is not implemented on any admin endpoint

---

## Next Recommended Milestone

**V5.17 — Production Readiness Hardening:**

1. **Operator runbook** — step-by-step credential lifecycle guide: onboard, validate, rotate, revoke; fake-values-only rehearsal; real credential readiness checklist
2. **Controlled live GCP lifecycle validation** — write → validate → rotate → delete through `GCPSecretManagerStore` with fake secrets only; confirm rotation does not destroy prior version by default
3. **Optional GCP Secret Manager version policy** — disable prior secret version on rotate; version destruction policy configuration
4. **Per-tenant admin permission model** — scope tokens to specific tenant namespaces; prevent cross-tenant credential access
5. **Rate limiting and abuse protection** — per-IP or per-token rate limits on admin endpoints
6. **Audit persistence hardening** — concurrent-writer-safe append; optional cryptographic signing or HMAC chain; BigQuery sink option
7. **Production readiness checklist** — before any real Google Ads OAuth credential onboarding

All milestones should maintain the established guardrails: pay-as-you-go only, no fixed-cost infrastructure, no secrets committed, explicit operator approval before any live Google Ads API call.

---

## Merge and Tag Recommendation

Once final review is complete:

```bash
git checkout master
git merge --no-ff v5.16-admin-rbac-audit-hardening
git tag v5.16.0-beta
```

Tag message: `v5.16.0-beta — Admin RBAC + audit hardening + credential rotation endpoint (Phases 1–3 PASS)`

**Prerequisites before merge:**
- Final smoke suite pass (complete — 17/17 and 8/8 above)
- Secret-safety grep clean (complete — confirmed)
- No credential JSON in repo (complete — confirmed)
- Working tree clean (complete — confirmed)

---

## Related Documents

- [V5.15 Branch Closure](V5_15_BRANCH_CLOSURE.md)
- [Release Notes — v5.15.0-beta](RELEASE_NOTES_V5_15_0_BETA.md)
- [V5.14 Branch Closure](V5_14_BRANCH_CLOSURE.md)
- [Release Notes — v5.14.0-beta](RELEASE_NOTES_V5_14_0_BETA.md)
- [V5.13 Branch Closure](V5_13_BRANCH_CLOSURE.md)
- [Release Notes — v5.13.0-beta](RELEASE_NOTES_V5_13_0_BETA.md)
- [Release Notes — v5.16.0-beta](RELEASE_NOTES_V5_16_0_BETA.md)
- [V5.12 GCP Secret Manager Release Notes](V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

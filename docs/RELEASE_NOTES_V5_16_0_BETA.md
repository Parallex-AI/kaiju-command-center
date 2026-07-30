# Release Notes — v5.16.0-beta

**Branch:** `v5.16-admin-rbac-audit-hardening`
**Base:** `v5.15.0-beta` / master after `f5d40ac`
**Tag candidate:** `v5.16.0-beta`
**Status:** Complete — ready for merge and tag

---

## Release Summary

v5.16.0-beta hardens the OpenClaw admin credential lifecycle across three dimensions. Phase 1 introduces token-scoped RBAC with a six-value `AdminScope` enum: each admin endpoint now enforces a minimum required scope, with 401/403 distinction and full backward compatibility for existing `OPENCLAW_API_KEYS` configurations (now treated as `READ`-only). Phase 2 adds audit sequence numbering and per-append file digest to every credential audit event, adds `audit_append_failed` warning visibility on all write paths, and introduces audit verification and pruning utilities. Phase 3 adds `POST /credentials/google-ads/rotate` — a credential rotation endpoint that writes a new bundle without ever reading the existing one and without calling the Google Ads API. All validate, delete, and rotate paths continue to use `get_secret_status()` for structural checks only — `get_secret_bundle()` is never called. All existing metadata/bundle write/validate/delete behavior is fully preserved. No real credentials were used. No fixed-cost infrastructure was created.

---

## Highlights

- **Token-scoped RBAC** — six-scope `AdminScope` enum (`READ`, `WRITE`, `VALIDATE`, `ROTATE`, `DELETE`, `ADMIN`); valid token with insufficient scope returns `403 scope_not_granted`; missing/invalid token returns `401 unauthorized`; `OPENCLAW_ADMIN_KEYS` tokens grant `ADMIN`; `OPENCLAW_READ_KEYS` tokens grant `READ`; `OPENCLAW_API_KEYS` preserved as `READ`-only fallback
- **Audit seq/digest hardening** — every credential audit event now carries `seq` (1-based, monotonically increasing per file) and `file_digest` (SHA-256 of file bytes before append); tamper detection via `verify_audit_file()`; `prune_audit_files()` for retention management; `OPENCLAW_AUDIT_RETAIN_DAYS` (default 90)
- **Credential rotation endpoint** — `POST /credentials/google-ads/rotate` requires `AdminScope.ROTATE`; writes new bundle via `put_secret_bundle()` only; validates structurally via `get_secret_status()` only; updates status to `ACTIVE` or `VALIDATION_FAILED`; emits `operation="rotate"` audit event; `REVOKED` credentials return `409 invalid_status_for_rotation`
- **No `get_secret_bundle()` in any lifecycle path** — validate, delete, and rotate paths all confirmed by code review and smoke test section 17
- **401/403 distinction** — unauthorized (missing/invalid token) is `401`; forbidden (valid token, wrong scope) is `403 scope_not_granted`; responses include `errors[].code` for programmatic handling
- **`audit_append_failed` warning visibility** — all five write paths surface this warning if audit append fails; write operations never fail solely because audit append failed
- **Zero real credentials used** — fake field values only; `GOOGLE_ADS_LIVE_ENABLED=false` throughout
- **Zero fixed-cost infrastructure** — no Cloud Run, GKE, Cloud SQL, Pub/Sub, or any fixed-cost service

---

## What Changed

### `openclaw/auth.py`

Added `AdminScope` enum:
```python
class AdminScope(str, Enum):
    READ = "read"
    WRITE = "write"
    VALIDATE = "validate"
    ROTATE = "rotate"
    DELETE = "delete"
    ADMIN = "admin"
```

Added `scope_allows(granted_scope, required_scope)`:
- `ADMIN` grants all scopes
- All other scopes are discrete (no implicit promotion)
- Identity: `scope_allows(X, X)` → `True`

Extended `validate_api_auth(headers, required_scope=None)`:
- Accepts optional `required_scope: AdminScope`; existing callers without `required_scope` are unchanged
- Token lookup checks `OPENCLAW_ADMIN_KEYS` first (grants `ADMIN`), then `OPENCLAW_READ_KEYS` (grants `READ`), then `OPENCLAW_API_KEYS` (grants `READ`, backward compatible)
- Returns `(False, [{"code": "scope_not_granted", ...}])` when token is valid but scope is insufficient
- Returns `(False, [{"code": "unauthorized", ...}])` when token is missing or not found

### `openclaw/audit.py`

Extended `append_audit_event(event, audit_root)`:
- Stamps `seq` — reads existing event count from file to determine next integer (1-based); first event on a new file is `seq=1`
- Stamps `file_digest` — SHA-256 hex digest of file bytes before append; first event on a new file is `""`

Added `verify_audit_file(path)`:
- Replays events in order; recomputes expected `file_digest` for each event from prior bytes; returns `{ok, total_events, valid_events, tampered_events, errors}`

### `openclaw/audit_maintenance.py` (new)

Added `prune_audit_files(audit_root, retain_days)`:
- Scans JSONL files in `audit_root`; deletes files with `mtime` older than `retain_days` days
- Returns `{pruned_count, retained_count, errors}`
- `retain_days` defaults to `int(os.environ.get("OPENCLAW_AUDIT_RETAIN_DAYS", "90"))`

### `openclaw/admin.py`

**All five write paths updated (Phases 2 and 3):**
- `upsert_google_ads_credential_reference()` — surfaces `audit_append_failed` warning
- `write_google_ads_credential_bundle()` — surfaces `audit_append_failed` warning
- `validate_google_ads_credentials()` — surfaces `audit_append_failed` warning
- `delete_google_ads_credentials()` — surfaces `audit_append_failed` warning
- `rotate_google_ads_credentials()` — new function; full rotation lifecycle (steps A–I); no `get_secret_bundle()` call; emits `operation="rotate"` audit event

`rotate_google_ads_credentials()` response keys:
- `ok`, `tenant_id`, `client_id`, `integration_type`
- `rotation_result`: `{structurally_complete, missing_fields, last_validated_at}`
- `credential_status`: redacted `CredentialReference` snapshot (no `credential_ref`)
- `secret_status`: boolean field presence map (no values)
- `errors`, `warnings`

### `openclaw/server.py`

Per-endpoint `required_scope` added to all five admin routes.

Added new route:
```
POST /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/rotate
```

HTTP response codes for rotate:
- `200` — success or VALIDATION_FAILED after write
- `400` — `secret_bundle_incomplete` (pre-write) or other business logic error
- `404` — `credential_not_found`
- `409` — `invalid_status_for_rotation` (REVOKED credential)
- `401` / `403` — auth failure

### Demo files updated

| File | Change |
|------|--------|
| `openclaw/run_admin_credentials_lifecycle_demo.py` | Sections P–T: rotate active (ok=true), rotate CONFIGURED (ok=true), incomplete payload (ok=false, missing\_fields), rotate REVOKED (409), missing credential (404) |
| `openclaw/run_admin_credentials_lifecycle_api_demo.py` | Rotate scenarios A–F: 200 success, 404 not-found, 409 revoked, 400 incomplete, 403 READ token, 200 ADMIN token; leak assertion extended to 20 responses |

### Smoke suite extended

| Section | Coverage |
|---------|---------|
| `[15/17]` | RBAC scope matrix: `scope_allows()` for all combinations; 401 and 403 response shapes; ADMIN grants all; READ grants READ only; ROTATE requires ADMIN |
| `[16/17]` | Audit seq/digest: `seq` field present, first event `seq=1`; `file_digest` present; `verify_audit_file()` importable; tamper detection marker; prune marker; `audit_append_failed` warning marker |
| `[17/17]` | Rotate endpoint: import, route, RBAC; no `.get_secret_bundle()` in rotate path; TestClient 200/404/409/403; lifecycle demo P/Q/R/S/T markers; API demo A/B/C/E markers |

---

## Endpoint Changes

| Method | Path | Status | Minimum scope |
|--------|------|--------|---------------|
| `GET` | `/credentials/google-ads/status` | Scope-gated (was auth-gated) | `READ` |
| `POST` | `/credentials/google-ads` | Scope-gated (was auth-gated) | `WRITE` |
| `POST` | `/credentials/google-ads/validate` | Scope-gated (was auth-gated) | `VALIDATE` |
| `POST` | `/credentials/google-ads/rotate` | **New** | `ROTATE` |
| `DELETE` | `/credentials/google-ads` | Scope-gated (was auth-gated) + env gate | `DELETE` |

---

## Validation Completed

| Phase | What was validated | Result |
|-------|-------------------|--------|
| 1 — Scope matrix | `scope_allows()` for all 36 combinations; `ADMIN` grants all; identity; no implicit promotion | **PASS** |
| 1 — RBAC API | TestClient: READ token on WRITE → 403; ADMIN token on WRITE → 200; no token when auth enabled → 401 | **PASS** |
| 2 — Audit seq/digest | `seq=1` on first event; increments per append; `file_digest` matches pre-append SHA-256; `verify_audit_file()` detects tamper; `prune_audit_files()` removes old files | **PASS** |
| 2 — Audit warning | `audit_append_failed` surfaces in `warnings` list when append raises; write operation still returns `ok=true` | **PASS** |
| 3 — Rotate function | Sections P–T: active → ok=true, CONFIGURED → ok=true, incomplete → ok=false + missing\_fields, REVOKED → invalid\_status\_for\_rotation, missing → credential\_not\_found | **PASS** |
| 3 — Rotate API | Scenarios A–F: 200 success, 404, 409, 400, 403, 200 admin | **PASS** |

---

## Security Guarantees

| Invariant | How enforced |
|-----------|--------------|
| Validate/delete/rotate paths never call `get_secret_bundle()` | No `get_secret_bundle` method calls in those paths; confirmed by smoke test section 17 grep |
| Rotation never reads the existing secret bundle | `put_secret_bundle()` write-only; `get_secret_status()` status-only; no bundle fetch at any point |
| Rotation response never includes secret values | `rotation_result.missing_fields` contains field names only; `secret_status` contains booleans only |
| Audit events exclude `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, all secret values | `build_credential_audit_event()` function signature excludes all these fields; confirmed by audit safety grep |
| Valid token with wrong scope returns `403`, not `401` | `scope_allows()` check distinct from token lookup; `scope_not_granted` error code |
| `OPENCLAW_API_KEYS` can only READ — no implicit WRITE/ROTATE/DELETE | Token lookup assigns `READ` scope to `OPENCLAW_API_KEYS`; `scope_allows(READ, WRITE)` → `False` |
| `DELETE` requires both RBAC scope and env gate | Two independent guards in `delete_google_ads_credentials()` |
| `audit_append_failed` warning is non-fatal | `_emit_credential_audit_event()` swallows exceptions; write path continues to success |
| No real credentials in any test or demo | Secret-safety grep confirms all values are `fake-*` prefixed or placeholder strings |

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

## Operator Notes

No migration steps are required to upgrade from v5.15.0-beta. All new RBAC behavior is opt-in via the new env vars; existing `OPENCLAW_API_KEYS` configurations continue to work as `READ`-only.

**New environment variables in V5.16:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENCLAW_ADMIN_KEYS` | `` | Comma-separated admin-scope tokens; grant `AdminScope.ADMIN` (all operations) |
| `OPENCLAW_READ_KEYS` | `` | Comma-separated read-only tokens; grant `AdminScope.READ` |
| `OPENCLAW_AUDIT_RETAIN_DAYS` | `90` | Number of days to retain audit JSONL files; used by `prune_audit_files()` |

**Preserved environment variables:**

| Variable | Scope | Notes |
|----------|-------|-------|
| `OPENCLAW_API_KEYS` | `READ` | Backward-compatible fallback; checked after `OPENCLAW_ADMIN_KEYS` and `OPENCLAW_READ_KEYS` |
| `OPENCLAW_API_AUTH_ENABLED` | — | Still gates whether auth is enforced; default `false` |
| `OPENCLAW_ADMIN_DELETE_ENABLED` | — | Still required for `DELETE` in addition to `DELETE` scope |

**To rotate stored credentials:**

```bash
curl -X POST \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"developer_token":"...","client_id":"...","client_secret":"...","refresh_token":"..."}' \
  http://localhost:<port>/openclaw/admin/tenants/<tenant_id>/clients/<client_id>/credentials/google-ads/rotate
```

Returns `rotation_result.structurally_complete=true` and `credential_status.status=active` on success. Requires a token from `OPENCLAW_ADMIN_KEYS`. Use placeholder values only in runbook examples — never commit real tokens.

---

## Not Included in v5.16.0-beta

The following remain deferred:

- **Live API validation** — `validate` and `rotate` confirm structural completeness only; `live_api_tested` always `false`; no Google Ads API call
- **Real Google Ads credentials** — `GOOGLE_ADS_LIVE_ENABLED=false` throughout; no real credentials used or validated
- **Per-tenant RBAC** — token scope applies globally; no tenant-namespace token isolation
- **IAM or OAuth admin auth** — RBAC is token-scope based; no GCP IAM or OAuth2 integration
- **Cryptographic audit signing** — `seq`/`file_digest` is tamper-evident but not cryptographically signed
- **Concurrent-writer-safe audit append** — single-process assumption; no file locking
- **GCP Secret Manager version destruction on rotate** — prior secret version is not disabled or destroyed
- **Rate limiting** — no per-token or per-IP limits on admin endpoints
- **Frontend credential UI** — deferred to a future branch
- **OAuth consent flow** — not in scope

---

## Recommended Next Steps

1. **Merge and tag** — merge `v5.16-admin-rbac-audit-hardening` into `master`; tag `v5.16.0-beta`
2. **V5.17 production readiness hardening** — operator runbook, controlled live GCP lifecycle validation with fake secrets, optional secret version destruction policy, per-tenant permission model, rate limiting, audit persistence hardening, real credential onboarding readiness checklist
3. **Controlled live GCP lifecycle validation** — validate the full write → validate → rotate → delete lifecycle through `GCPSecretManagerStore` with fake values only; confirm rotate behavior with prior version
4. **Cloud Run deployment** — once operator runbook and per-tenant RBAC are in place, deploy OpenClaw to Cloud Run with `GCPSecretManagerStore` and IAM-scoped service account

All steps should maintain the established guardrails: pay-as-you-go only, no fixed-cost infrastructure, no secrets committed, explicit operator approval before any live Google Ads API call.

---

## Related Documents

- [V5.16 Branch Closure](V5_16_BRANCH_CLOSURE.md)
- [Release Notes — v5.15.0-beta](RELEASE_NOTES_V5_15_0_BETA.md)
- [V5.15 Branch Closure](V5_15_BRANCH_CLOSURE.md)
- [Release Notes — v5.14.0-beta](RELEASE_NOTES_V5_14_0_BETA.md)
- [V5.14 Branch Closure](V5_14_BRANCH_CLOSURE.md)
- [Release Notes — v5.13.0-beta](RELEASE_NOTES_V5_13_0_BETA.md)
- [V5.13 Branch Closure](V5_13_BRANCH_CLOSURE.md)
- [V5.12 GCP Secret Manager Release Notes](V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

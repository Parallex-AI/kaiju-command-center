# V5.17 Branch Closure — Production Readiness Hardening

**Branch:** `v5.17-production-readiness`
**Base:** `v5.16.0-beta` / master after `e4c65cc`
**Target release tag candidate:** `v5.17.0-beta`
**Status:** Complete — all phases PASS · closure docs complete · ready for merge and tag

---

## Summary

V5.17 hardens the OpenClaw admin credential lifecycle for controlled real-credential onboarding readiness. Five phases were implemented across the branch: Phase 1 delivers a step-by-step operator credential lifecycle runbook. Phase 2 provides a controlled live GCP lifecycle validation plan and results template for fake-secret operator rehearsal — this is a plan and template only; the live validation was not executed as part of this branch. Phase 3 adds per-tenant token isolation via `OPENCLAW_TENANT_KEYS`, restricting individual admin tokens to specific tenant namespaces. Phase 4 adds local admin endpoint rate limiting with per-token, per-category sliding windows via `OPENCLAW_ADMIN_RATE_LIMIT_RPM` and `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM`. Phase 5 hardens the audit JSONL append path with `fcntl.flock(LOCK_EX)` file locking to prevent seq/digest races between concurrent writers.

No real Google Ads credentials were used. No Google Ads live API calls were made. `GOOGLE_ADS_LIVE_ENABLED` remained `false` throughout. No production deployment was performed. No GCP resources were created. No fixed-cost infrastructure was introduced. All six smoke suites pass.

---

## Scope

Five implementation phases for the OpenClaw admin credential system:

- **Phase 1** — Operator credential lifecycle runbook: step-by-step onboard/validate/rotate/revoke guide; fake-values-only rehearsal; real credential readiness checklist; decision record for when each path is safe to execute
- **Phase 2** — Controlled live GCP lifecycle validation plan and results template: operator-run fake-secret plan (Phases A–H) covering write → validate → rotate → delete through `GCPSecretManagerStore`; results template for recording outcomes; not executed as part of this branch
- **Phase 3** — Per-tenant token isolation: `OPENCLAW_TENANT_KEYS` env var; `parse_tenant_keys()` parser; `validate_tenant_access()` function; all five admin routes check tenant access after scope check; unlisted tokens retain global access; listed tokens are restricted to their allowed tenant set
- **Phase 4** — Admin endpoint rate limiting: `openclaw/rate_limit.py` with `RateLimiter` (sliding 60s window, `collections.deque`), `RateLimitCategory` (STANDARD/SENSITIVE), `get_rate_limiter()` process singleton, `check_rate_limit()`; `OPENCLAW_ADMIN_RATE_LIMIT_RPM` and `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` env vars (default `0` = disabled); HTTP 429 with `retry_after_seconds` on exhaustion; denied requests do not consume rate budget
- **Phase 5** — Audit persistence hardening: `fcntl.flock(LOCK_EX)` exclusive lock around seq/digest computation and JSONL write in `append_audit_event()`; safe fallback for non-Unix platforms (`_HAS_FCNTL = False`); `lock_used` return field; backward-compatible with all existing callers

What was not in scope: production deployment, real Google Ads OAuth credential onboarding, live GCP lifecycle validation execution, GCP Secret Manager version destruction policy, Redis/Memorystore distributed rate limiting, OAuth2 admin authentication, IAM-backed RBAC, BigQuery audit replication, Cloud Storage audit archival, KMS/HSM audit signing, frontend UI.

---

## Completed Phases

| Phase | Commit | Description | Status |
|-------|--------|-------------|--------|
| Phase 1 | `17ce414` | Operator credential lifecycle runbook · `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` | **Complete** |
| Phase 2 | `961eaae` | Live GCP lifecycle validation plan and results template · `docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md` · `docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md` (template only) | **Complete** |
| Phase 3 | `4b7d8a2` | Per-tenant token isolation · `OPENCLAW_TENANT_KEYS` · `validate_tenant_access()` · all five admin routes | **Complete** |
| Phase 4 | `ac899df` | Admin endpoint rate limiting · `openclaw/rate_limit.py` · `OPENCLAW_ADMIN_RATE_LIMIT_RPM` · `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` | **Complete** |
| Phase 5 | `e6bebc0` | Audit persistence hardening · `fcntl.flock(LOCK_EX)` in `append_audit_event()` · `lock_used` return field | **Complete** |
| Closure | — | Branch closure doc · release notes · ROADMAP update · README update · final smoke suites | **Complete** |

---

## Files Added

| File | Phase | Description |
|------|-------|-------------|
| `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` | 1 | Step-by-step operator lifecycle guide |
| `docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md` | 2 | Controlled fake-secret lifecycle validation plan (Phases A–H) |
| `docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md` | 2 | Results template — not yet executed; must be filled by operator after approval |
| `openclaw/rate_limit.py` | 4 | `RateLimiter`, `RateLimitCategory`, `get_rate_limiter`, `check_rate_limit` |
| `docs/V5_17_RATE_LIMITING_DESIGN.md` | 4 | Rate limiting design decisions |
| `docs/V5_17_AUDIT_HARDENING_DECISION.md` | 5 | Audit persistence hardening design decision |
| `docs/V5_17_BRANCH_CLOSURE.md` | Closure | This document |
| `docs/RELEASE_NOTES_V5_17_0_BETA.md` | Closure | V5.17.0-beta release notes |

---

## Files Materially Modified

| File | Phases | Change |
|------|--------|--------|
| `openclaw/config.py` | 3, 4 | Added `parse_tenant_keys()`, `tenant_keys` field; added `admin_rate_limit_rpm`, `admin_rate_limit_sensitive_rpm` fields |
| `openclaw/auth.py` | 3 | Added `validate_tenant_access()` |
| `openclaw/server.py` | 3, 4 | Tenant access check after scope check on all five routes; `check_rate_limit()` call on all five routes |
| `openclaw/audit.py` | 5 | `fcntl` import guard; `append_audit_event()` locked path + fallback; `lock_used` in return dict |
| `openclaw/run_admin_credentials_lifecycle_demo.py` | 3, 5 | Section U added (audit locking); per-tenant isolation assertion markers added |
| `openclaw/run_admin_credentials_lifecycle_api_demo.py` | 3, 4 | Per-tenant isolation (Tenant A–F) and rate limiting (Rate A–G) scenario sections added |
| `scripts/smoke_test_v5_credentials.sh` | 3, 4, 5 | Extended from [17/17] to [20/20]; sections 18 (per-tenant isolation), 19 (rate limiting), 20 (audit file locking) |
| `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` | 1, 5 | Full lifecycle runbook; Section 12 updated with V5.17 Phase 5 file locking description |
| `docs/ROADMAP.md` | Closure | V5.17 marked complete |
| `README.md` | Closure | Current milestone updated to V5.17 |

---

## Security Posture

| Property | Status |
|----------|--------|
| All five admin routes check tenant access after scope check, before rate limit | Confirmed |
| `validate_tenant_access()` returns `tenant_access_denied` error for restricted tokens on disallowed tenants | Confirmed |
| Unlisted tokens (not in `OPENCLAW_TENANT_KEYS`) retain global access — backward compatible | Confirmed |
| Denied requests (401, 403 scope, 403 tenant) do not consume rate limit budget | Confirmed |
| Rate limit check occurs after auth, scope, and tenant checks | Confirmed |
| `fcntl.flock(LOCK_EX)` serializes seq/digest computation and write for concurrent writers | Confirmed |
| Audit event seq/digest chain remains tamper-evident via `verify_audit_file()` | Confirmed |
| `lock_used` return field allows callers and tests to confirm locking was applied | Confirmed |
| No `get_secret_bundle()` call on any lifecycle path | Confirmed |
| Validate/delete/rotate paths never call the Google Ads API | Confirmed |
| Audit events exclude `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, all secret values | Confirmed |
| API responses never return raw secret values | Confirmed |
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

## GCP Posture

No GCP resources were created or modified. No GCP APIs were enabled. No IAM changes were made. The Phase 2 results template (`docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md`) is an unfilled operator template — it records what to capture, not what was captured. It must be filled only after explicit operator approval and a separate operator-run rehearsal using fake secrets only.

All tests used `InMemorySecretStore` (`GCP_SECRET_MANAGER_ENABLED=false`). No live GCP calls were made.

---

## Google Ads Posture

No Google Ads API calls were made. `GOOGLE_ADS_LIVE_ENABLED=false` throughout. No real Google Ads credentials were used, stored, or validated. Live API testing remains deferred to a future explicitly authorized phase.

---

## Secret-Safety Posture

All credential values in demos, tests, and smoke scripts are explicitly labeled fake (`fake-dev-token-*`, `fake-client-secret-*`, `fake-refresh-token-*`, `fake-oauth-client-id-*`). The secret-safety grep confirmed: no `ya29.` OAuth token prefix, no `sk-` API key prefix, no real credential assignments, no real `GOOGLE_APPLICATION_CREDENTIALS` paths. Audit events confirmed to exclude all sensitive fields by design.

---

## RBAC / Tenant Isolation Posture

RBAC is token-scope based (inherited from V5.16). V5.17 adds tenant isolation via `OPENCLAW_TENANT_KEYS`. Each admin token can be restricted to one or more tenant IDs. Tokens not listed in `OPENCLAW_TENANT_KEYS` retain global access (backward-compatible default). The tenant check runs after scope check and before rate limit, ensuring denied-tenant requests never consume rate budget.

---

## Rate Limiting Posture

Rate limiting is local-only (process-in-memory, `collections.deque` sliding window). Default is `0` (disabled) for both STANDARD and SENSITIVE categories — existing deployments see no behavior change. When enabled, each (token, category) pair has an independent budget. HTTP 429 responses include `retry_after_seconds`. Rate limits do not apply cross-process or cross-instance; distributed rate limiting is a deferred item.

---

## Audit Persistence Posture

On Linux/Unix (including Cloud Run containers), `append_audit_event()` holds an exclusive `fcntl.flock(LOCK_EX)` advisory lock for the duration of seq computation, digest computation, and JSONL write. This prevents seq/digest races between cooperative writers in the same process group. The lock is advisory — it does not prevent privileged out-of-band filesystem writes. On non-Unix platforms (Windows), the fallback path (no locking) is used automatically. Audit files remain tamper-evident via the seq/file_digest chain but are not cryptographically signed and are not durable across container restarts.

---

## Live GCP Validation Status

**Not executed in this branch.**

The Phase 2 document (`docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md`) is a controlled fake-secret operator plan covering write → validate → rotate → delete through `GCPSecretManagerStore`. The results template (`docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md`) is an unfilled template. No live GCP lifecycle validation was performed. Execution requires explicit operator approval and must follow the plan in `docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md` — fake secrets only, no real Google Ads credentials, `GOOGLE_ADS_LIVE_ENABLED=false`.

---

## Implementation Summary

### Phase 1 — Operator Credential Lifecycle Runbook

`docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` provides a complete step-by-step guide for the full admin credential lifecycle:

- **Section 1–3** — Prerequisites, env vars, authentication
- **Section 4** — Metadata write (`POST /credentials/google-ads`)
- **Section 5** — Bundle write (all four secret fields)
- **Section 6** — Structural validation (`POST /credentials/google-ads/validate`)
- **Section 7** — Credential rotation (`POST /credentials/google-ads/rotate`)
- **Section 8** — Revoke/delete (`DELETE /credentials/google-ads`)
- **Section 9** — Error reference
- **Section 10** — Fake-value rehearsal safety checks
- **Section 11** — Real credential readiness checklist
- **Section 12** — Audit verification and pruning (updated in Phase 5 to include file locking)
- **Section 13** — Related documents

### Phase 2 — Live GCP Validation Plan and Results Template

`docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md` describes an eight-phase controlled validation:
- **Phase A** — Environment setup with fake values
- **Phase B** — Metadata write through `GCPSecretManagerStore`
- **Phase C** — Bundle write through `GCPSecretManagerStore`
- **Phase D** — Structural validation (`get_secret_status()` only)
- **Phase E** — Credential rotation (new bundle via `put_secret_bundle()`, prior version untouched by default)
- **Phase F** — Revoke/delete
- **Phase G** — Audit file verification
- **Phase H** — Cleanup and env restore

`docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md` is an unfilled template for recording operator-run results. It has not been filled because live validation was not executed.

### Phase 3 — Per-Tenant Token Isolation

`OPENCLAW_TENANT_KEYS=<token>:<tenant_id>,<token>:<tenant_id>,...`

**`openclaw/config.py`** — `parse_tenant_keys()` parses the env var into `Dict[str, Set[str]]`; malformed entries are silently skipped; stored in `OpenClawConfig.tenant_keys`.

**`openclaw/auth.py`** — `validate_tenant_access(token, tenant_id, config)`:
- If `tenant_keys` is empty: all tokens have global access (backward-compatible default)
- If `tenant_keys` is non-empty and token is listed: access allowed only for listed tenant IDs
- If `tenant_keys` is non-empty and token is not listed: global access (unlisted tokens are not restricted)
- Returns `(True, [])` on access or `(False, [{"code": "tenant_access_denied", ...}])` on denial

**`openclaw/server.py`** — All five admin routes check `validate_tenant_access()` after `validate_api_auth()` / `validate_tenant_access()` order: auth → scope → tenant → rate limit → operation.

Route check order:
1. `validate_api_auth()` (returns 401/403 scope_not_granted)
2. `validate_tenant_access()` (returns 403 tenant_access_denied)
3. `check_rate_limit()` (returns 429 rate_limit_exceeded)
4. Business logic (returns 200/400/404/409)

### Phase 4 — Admin Endpoint Rate Limiting

**`openclaw/rate_limit.py`** (new file):
- `RateLimitCategory(str, Enum)` — `STANDARD = "standard"`, `SENSITIVE = "sensitive"`
- `RateLimiter` — per-(token, category) `collections.deque`; window is 60 seconds; `check(token, category, limit)` removes expired timestamps, checks count, appends if allowed
- `get_rate_limiter()` — module-level singleton; shared across all requests in the same process
- `check_rate_limit(token, category, config)` — reads `admin_rate_limit_rpm` / `admin_rate_limit_sensitive_rpm` from config; `limit=0` always allows

**Route categories:**
- STANDARD (`OPENCLAW_ADMIN_RATE_LIMIT_RPM`): GET status, POST write, POST validate
- SENSITIVE (`OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM`): DELETE, POST rotate

**HTTP 429 response:**
```json
{
  "ok": false,
  "errors": [{"code": "rate_limit_exceeded", "recoverable": true, "retry_after_seconds": <N>}]
}
```

### Phase 5 — Audit Persistence Hardening

**`openclaw/audit.py`** — Module-level fcntl import guard:
```python
try:
    import fcntl as _fcntl
    _HAS_FCNTL = True
except ImportError:
    _fcntl = None
    _HAS_FCNTL = False
```

Modified `append_audit_event()` — locked path (Linux/Unix):
```
touch file to ensure it exists
open(file, "r+b")
flock(LOCK_EX)
read all current bytes
compute file_digest (SHA-256 or "" if empty)
compute seq (non-empty line count + 1)
stamp event["seq"] and event["file_digest"]
seek to end
write encoded JSONL line
flush
flock(LOCK_UN)
lock_used = True
```

Fallback path (non-Unix): existing behavior — `_compute_file_digest`, `_next_audit_seq`, open `"a"`, `lock_used = False`.

Return value: `{"ok": True, "path": ..., "seq": ..., "file_digest": ..., "lock_used": ...}` — backward-compatible.

---

## Smoke Test Results

| Suite | Script | Result |
|-------|--------|--------|
| V5 credentials | `scripts/smoke_test_v5_credentials.sh` | **20/20 PASS** |
| V5.12 GCP Secret Manager | `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **8/8 PASS** |
| GCP write helper demo | `openclaw/run_admin_credentials_gcp_write_demo.py` | **PASS** |
| API write demo | `openclaw/run_admin_credentials_api_write_demo.py` | **PASS** |
| Lifecycle function demo | `openclaw/run_admin_credentials_lifecycle_demo.py` | **PASS** (Sections A–U) |
| Lifecycle API demo | `openclaw/run_admin_credentials_lifecycle_api_demo.py` | **PASS** |

All suites run without real GCP credentials. No live GCP calls. No live Google Ads API calls. `GOOGLE_ADS_LIVE_ENABLED=false` throughout.

---

## Known Limitations

- **Rate limiter is process-local** — `RateLimiter` state lives in a single process. Multiple Cloud Run instances each maintain independent budgets. Distributed rate limiting (Redis/Memorystore) is deferred.
- **`fcntl` locking is process-host-local** — `fcntl.flock` serializes writers within one process. Multiple Cloud Run instances with separate local filesystems each maintain independent audit chains. Not a cross-instance lock.
- **Audit JSONL is tamper-evident, not cryptographically signed** — the `seq`/`file_digest` chain detects filesystem-level tampering but can be rewritten consistently by a privileged actor with write access. KMS/HSM signing is deferred.
- **Audit files are not durable across container restarts** — Cloud Run container filesystems are ephemeral. Cloud Storage archival or BigQuery replication would be required for durable long-term retention. Both are deferred.
- **GCP Secret Manager prior versions are not disabled on rotate** — `rotate_google_ads_credentials()` calls `put_secret_bundle()` (which calls `add_secret_version`) only. The prior secret version remains enabled unless the operator handles version lifecycle externally.
- **Tenant isolation is token-based, not IAM-backed** — `OPENCLAW_TENANT_KEYS` provides local token-to-tenant mapping only. No GCP IAM, OAuth2, or per-tenant service account is used.
- **Live GCP validation was not executed** — the Phase 2 results template is unfilled. Execution requires explicit operator approval.
- **`GOOGLE_ADS_LIVE_ENABLED=false` throughout** — no live Google Ads API handshake or real credential validation was performed.

---

## Deferred Items

| Item | Why deferred |
|------|-------------|
| Cloud Run deployment | Requires service account, IAM, billing authorization, explicit operator approval |
| BigQuery audit replication | Requires GCP dataset, IAM `roles/bigquery.dataEditor`, billing |
| Cloud Storage audit archival / object lock | Requires GCP bucket, IAM `roles/storage.objectAdmin`, billing |
| KMS/HSM audit signing | Requires GCP KMS key, IAM `roles/cloudkms.signerVerifier`, latency trade-off |
| GCP Secret Manager version destruction / disable policy | Requires explicit operator policy decision and GCP IAM |
| Redis/Memorystore distributed rate limiting | Requires standing infrastructure, billing; current local rate limiting is sufficient for single-instance deployments |
| OAuth2 / admin identity provider | Requires external IdP, IAM integration |
| Real Google Ads OAuth credential onboarding | Requires explicit operator approval, live credentials, `GOOGLE_ADS_LIVE_ENABLED=true` |
| Real Google Ads live API validation | Requires `GOOGLE_ADS_LIVE_ENABLED=true`, real credentials, explicit operator approval |
| Multi-instance production rate limiting | Requires distributed store; deferred pending Cloud Run deployment |
| Live GCP lifecycle validation execution | Must follow `docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md`; requires explicit operator approval |

---

## Release Readiness Decision

**Ready for merge and tag.**

All five implementation phases are committed and pass all smoke suites (20/20 and 8/8). All security, cost, GCP, Google Ads, and secret-safety postures are confirmed. No real credentials were used. No GCP resources were created. The working tree is clean.

---

## Merge and Tag Instructions

Once final review is complete:

```bash
git checkout master
git merge --no-ff v5.17-production-readiness
git tag v5.17.0-beta
```

Tag message: `v5.17.0-beta — Production readiness hardening: operator runbook + per-tenant isolation + rate limiting + audit file locking (Phases 1–5 PASS)`

**Prerequisites before merge:**
- Final smoke suite pass (complete — 20/20 and 8/8 above)
- Secret-safety grep clean (complete — confirmed)
- No credential JSON in repo (complete — confirmed)
- Working tree clean (complete — confirmed)

---

## Related Documents

- [V5.16 Branch Closure](V5_16_BRANCH_CLOSURE.md)
- [Release Notes — v5.16.0-beta](RELEASE_NOTES_V5_16_0_BETA.md)
- [Credential Lifecycle Runbook](CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [V5.17 Live GCP Validation Plan](V5_17_LIVE_GCP_VALIDATION_PLAN.md)
- [V5.17 Live GCP Validation Results](V5_17_LIVE_GCP_VALIDATION_RESULTS.md) (template — not yet executed)
- [V5.17 Per-Tenant Permission Design](V5_17_PER_TENANT_PERMISSION_DESIGN.md)
- [V5.17 Rate Limiting Design](V5_17_RATE_LIMITING_DESIGN.md)
- [V5.17 Audit Hardening Decision](V5_17_AUDIT_HARDENING_DECISION.md)
- [Release Notes — v5.17.0-beta](RELEASE_NOTES_V5_17_0_BETA.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

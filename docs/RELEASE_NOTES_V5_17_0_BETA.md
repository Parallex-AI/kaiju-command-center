# Release Notes — v5.17.0-beta

**Branch:** `v5.17-production-readiness`
**Base:** `v5.16.0-beta` / master after `e4c65cc`
**Tag candidate:** `v5.17.0-beta`
**Status:** Complete — ready for merge and tag

---

## Release Summary

v5.17.0-beta is the production readiness hardening release for the OpenClaw admin credential lifecycle. Building on V5.16's RBAC, audit seq/digest, and credential rotation, V5.17 delivers five phases: an operator credential lifecycle runbook, a controlled live GCP lifecycle validation plan and results template (not executed), per-tenant token isolation, local admin endpoint rate limiting, and audit append file locking.

No real Google Ads credentials were used. No Google Ads live API calls were made. `GOOGLE_ADS_LIVE_ENABLED=false` throughout. No production deployment was performed. No GCP resources were created. No fixed-cost infrastructure was introduced.

---

## Highlights

- **Operator credential lifecycle runbook** — `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md`: step-by-step guide for onboard, validate, rotate, revoke; fake-values-only rehearsal safety checks; real credential readiness checklist; full error reference; audit verification guidance
- **Per-tenant token isolation** — `OPENCLAW_TENANT_KEYS` env var restricts individual admin tokens to specific tenant namespaces; `403 tenant_access_denied` on denied tenant access; backward-compatible default (unlisted tokens retain global access)
- **Local admin endpoint rate limiting** — `openclaw/rate_limit.py`; `OPENCLAW_ADMIN_RATE_LIMIT_RPM` and `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` (default `0` = disabled); per-token, per-category sliding 60s window; STANDARD (status, write, validate) and SENSITIVE (rotate, delete) categories; `HTTP 429` with `retry_after_seconds`; denied requests do not consume budget
- **Audit append file locking** — `fcntl.flock(LOCK_EX)` on Linux/Unix; seq/digest computed and written atomically under lock; `lock_used` return field; safe fallback for non-Unix; prevents false seq/digest mismatches from concurrent writers
- **Controlled live GCP validation plan** — `docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md`: eight-phase fake-secret plan (A–H) from environment setup through cleanup; results template ready for operator-run rehearsal under explicit approval
- **Zero real credentials used** — fake field values only; all smoke suites pass without any live GCP or Google Ads calls
- **Zero fixed-cost infrastructure** — no Cloud Run, GKE, Cloud SQL, BigQuery, Pub/Sub, Redis/Memorystore, or any standing service

---

## What's New

### Phase 1 — Operator Credential Lifecycle Runbook (`docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md`)

Complete step-by-step guide covering the full admin credential lifecycle for operators:

- **Env var reference** — all required and optional variables for auth, audit, delete gate, rate limiting, tenant isolation
- **Metadata write** — `POST /credentials/google-ads` with `customer_id` and optional `login_customer_id`
- **Bundle write** — `POST /credentials/google-ads` with all four secret fields (`developer_token`, `client_id`, `client_secret`, `refresh_token`)
- **Structural validation** — `POST /credentials/google-ads/validate`; `get_secret_status()` only; `live_api_tested=false`
- **Credential rotation** — `POST /credentials/google-ads/rotate`; `put_secret_bundle()` only; prior version not destroyed by default
- **Revoke/delete** — `DELETE /credentials/google-ads`; requires `OPENCLAW_ADMIN_DELETE_ENABLED=true` and `DELETE` scope
- **Error code reference** — all error codes with cause and resolution
- **Fake-value rehearsal checklist** — confirms safe values before any runbook execution
- **Real credential readiness checklist** — gates for when real Google Ads credential onboarding may begin
- **Audit verification** — `verify_audit_file()` usage; file locking behavior (Phase 5 update)

### Phase 2 — Live GCP Lifecycle Validation Plan and Results Template

- `docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md` — eight-phase operator-run validation plan:
  - Phase A: environment setup (fake values, `GCPSecretManagerStore`)
  - Phase B: metadata write
  - Phase C: bundle write
  - Phase D: structural validation
  - Phase E: credential rotation (observe prior version behavior)
  - Phase F: revoke/delete
  - Phase G: audit file verification
  - Phase H: cleanup and environment restore
- `docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md` — operator results template; **not yet executed**; must be filled only after explicit operator approval and operator-run rehearsal using fake secrets; `GOOGLE_ADS_LIVE_ENABLED=false` required throughout

### Phase 3 — Per-Tenant Token Isolation

**`openclaw/config.py`** — `parse_tenant_keys(value)`:
- Parses `"token-a:tenant-1,token-a:tenant-2,token-b:tenant-3"` into `Dict[str, Set[str]]`
- Malformed entries (no `:`, empty token, empty tenant) are silently skipped
- Result stored in `OpenClawConfig.tenant_keys`

**`openclaw/auth.py`** — `validate_tenant_access(token, tenant_id, config)`:
- If `tenant_keys` is empty: all tokens have global access (backward-compatible default — no behavior change when `OPENCLAW_TENANT_KEYS` is unset)
- If `tenant_keys` is non-empty and token is listed: access allowed only for listed tenant IDs
- If `tenant_keys` is non-empty and token is not listed: global access (unlisted tokens are never restricted)

**`openclaw/server.py`** — all five admin routes execute checks in this order:
1. `validate_api_auth()` → `401 unauthorized` / `403 scope_not_granted`
2. `validate_tenant_access()` → `403 tenant_access_denied`
3. `check_rate_limit()` → `429 rate_limit_exceeded`
4. Business logic → `200` / `400` / `404` / `409`

**New env var:**

| Variable | Default | Purpose |
|---|---|---|
| `OPENCLAW_TENANT_KEYS` | `` | Comma-separated `token:tenant_id` pairs; restricts listed tokens to their allowed tenants |

### Phase 4 — Admin Endpoint Rate Limiting

**`openclaw/rate_limit.py`** (new file):

```python
class RateLimitCategory(str, Enum):
    STANDARD = "standard"   # GET status, POST write, POST validate
    SENSITIVE = "sensitive" # DELETE, POST rotate
```

`RateLimiter` uses a per-(token, category) `collections.deque` with a 60-second sliding window. `get_rate_limiter()` returns a process-level singleton.

`check_rate_limit(token, category, config)`:
- `limit=0` → always allowed (disabled)
- `limit>0` → allowed if count within window < limit; `(False, [rate_limit_exceeded error])` if exhausted

HTTP 429 response shape:
```json
{
  "ok": false,
  "errors": [{
    "code": "rate_limit_exceeded",
    "recoverable": true,
    "retry_after_seconds": 43
  }]
}
```

**New env vars:**

| Variable | Default | Description |
|---|---|---|
| `OPENCLAW_ADMIN_RATE_LIMIT_RPM` | `0` | Max requests/min for STANDARD routes per token; `0` = disabled |
| `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` | `0` | Max requests/min for SENSITIVE routes per token; `0` = disabled |

### Phase 5 — Audit Append File Locking

**`openclaw/audit.py`** — module-level fcntl guard:
```python
try:
    import fcntl as _fcntl
    _HAS_FCNTL = True
except ImportError:
    _fcntl = None
    _HAS_FCNTL = False
```

`append_audit_event()` locked path (when `_HAS_FCNTL = True`, Linux/Unix):
- `audit_file.touch(exist_ok=True)` to ensure file exists
- Open `r+b` (binary read-write, no truncation)
- `fcntl.flock(LOCK_EX)` — exclusive advisory lock
- Read all current bytes; compute `file_digest` (SHA-256 or `""`) and `seq` (non-empty line count + 1)
- Stamp `event["seq"]` and `event["file_digest"]`
- `fh.seek(0, 2)` — seek to end
- Write encoded JSONL line and flush
- `fcntl.flock(LOCK_UN)` — release lock
- `lock_used = True`

Return dict adds `lock_used` field. All existing callers that check only `ok` are unaffected.

---

## Security Hardening

| Invariant | How enforced |
|-----------|--------------|
| Tenant-restricted tokens cannot access disallowed tenant namespaces | `validate_tenant_access()` checked after scope, before rate limit and business logic |
| Denied requests (auth, scope, tenant) do not consume rate budget | Rate check is the fourth guard in the route; auth/scope/tenant denials return before reaching it |
| Audit seq/digest races between concurrent writers are prevented on Linux/Unix | `fcntl.flock(LOCK_EX)` holds for the duration of seq computation, digest computation, and write |
| No `get_secret_bundle()` call on any lifecycle path | Confirmed by code review and smoke test section 14 grep |
| Audit events exclude all sensitive fields and secret values | `build_credential_audit_event()` field set; confirmed by smoke test section 14 |
| API responses never return raw secret values | No endpoint serializes bundle contents |
| `GOOGLE_ADS_LIVE_ENABLED=false` throughout | Confirmed by smoke test section 14 forbidden-behavior grep |
| No real credentials used in any test or demo | Secret-safety grep confirms fake-prefixed values only |

---

## Operational Hardening

- **Tenant isolation without IAM** — `OPENCLAW_TENANT_KEYS` provides local token-to-tenant binding without external policy service
- **Gradual rate protection** — STANDARD and SENSITIVE budgets are independent; rotating a credential does not affect status-read budget
- **Concurrent-write protection** — `fcntl.flock` prevents false audit chain invalidation on single-instance Linux/Unix deployments
- **Operator rehearsal guidance** — V5.17 Phase 2 plan provides a staged, fake-secret validation sequence before any real credential onboarding

---

## Developer and Operator Docs Added

| Document | Purpose |
|---|---|
| `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` | Full operator lifecycle guide |
| `docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md` | Operator-run fake-secret lifecycle validation plan |
| `docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md` | Results template (unfilled — requires operator approval) |
| `docs/V5_17_PER_TENANT_PERMISSION_DESIGN.md` | Per-tenant isolation design decisions |
| `docs/V5_17_RATE_LIMITING_DESIGN.md` | Rate limiting design decisions |
| `docs/V5_17_AUDIT_HARDENING_DECISION.md` | Audit persistence hardening design decisions |

---

## Tests

| Suite | Result |
|-------|--------|
| `openclaw/run_admin_credentials_gcp_write_demo.py` | **PASS** |
| `openclaw/run_admin_credentials_api_write_demo.py` | **PASS** |
| `openclaw/run_admin_credentials_lifecycle_demo.py` | **PASS** (Sections A–U, 20+ assertions per section) |
| `openclaw/run_admin_credentials_lifecycle_api_demo.py` | **PASS** |
| `scripts/smoke_test_v5_credentials.sh` | **20/20 PASS** |
| `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **8/8 PASS** |

Smoke test sections added in V5.17:
- `[18/20]` — Per-tenant token isolation: `parse_tenant_keys`, `validate_tenant_access`, TestClient restricted/allowed/backward-compat; API demo Tenant A–F markers
- `[19/20]` — Rate limiting: `RateLimiter`, `RateLimitCategory`, `get_rate_limiter`, `check_rate_limit`; per-token isolation; STANDARD/SENSITIVE separation; API demo Rate A–G markers
- `[20/20]` — Audit file locking: `_HAS_FCNTL` importable; `LOCK_EX` in `audit.py` source; `append_audit_event` returns `lock_used` and `seq=1`; lifecycle demo Section U markers; no forbidden fields

---

## Compatibility

| Behavior | V5.16 | V5.17 |
|---|---|---|
| `OPENCLAW_TENANT_KEYS` unset | Global access (all tokens, all tenants) | Global access — unchanged |
| `OPENCLAW_ADMIN_RATE_LIMIT_RPM=0` (default) | No rate limiting | No rate limiting — unchanged |
| `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM=0` (default) | No rate limiting | No rate limiting — unchanged |
| `append_audit_event()` return dict | `{ok, path, seq, file_digest}` | Adds `lock_used` — backward-compatible |
| All existing `OPENCLAW_API_KEYS`, `OPENCLAW_ADMIN_KEYS`, `OPENCLAW_READ_KEYS` behavior | As specified | Unchanged |
| `GOOGLE_ADS_LIVE_ENABLED` behavior | `false` default | `false` default — unchanged |

No breaking changes. All existing configuration and callers are unaffected by default.

---

## Migration Notes

**No migration steps are required.** All V5.17 features are opt-in via new environment variables; defaults preserve V5.16 behavior exactly.

**To enable per-tenant token isolation:**

```bash
# Restrict token-a to tenant-1 and tenant-2; token-b to tenant-3 only
export OPENCLAW_TENANT_KEYS=token-a:tenant-1,token-a:tenant-2,token-b:tenant-3
```

**To enable rate limiting:**

```bash
# 60 req/min for standard routes, 10 req/min for sensitive routes, per token
export OPENCLAW_ADMIN_RATE_LIMIT_RPM=60
export OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM=10
```

**Before real credential onboarding:**
1. Read `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` in full — especially Sections 10–11 (rehearsal checklist and real credential readiness gates)
2. Complete the fake-value rehearsal documented in Section 10
3. Confirm all readiness gate conditions in Section 11 before using real values
4. Do not execute `docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md` without explicit operator approval

**Live GCP validation:**
- The results template `docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md` is unfilled
- Execution requires explicit operator approval
- `GOOGLE_ADS_LIVE_ENABLED` must remain `false` during execution (fake secrets only)

---

## Known Limitations

- **Rate limiter is process-local** — not effective across multiple Cloud Run instances; distributed rate limiting (Redis/Memorystore) is deferred
- **`fcntl` file locking is Unix-only and process-local** — Windows uses the fallback (no lock); multiple Cloud Run instances with separate ephemeral filesystems each maintain independent audit chains
- **Audit JSONL is not cryptographically signed** — tamper-evident via seq/digest chain; not signed with KMS/HSM; a privileged writer with filesystem access can rewrite the chain
- **Audit files are ephemeral** — Cloud Run container filesystems do not persist across instance restarts; Cloud Storage or BigQuery replication is required for durable audit history
- **GCP Secret Manager prior versions are not disabled on rotate** — the prior version remains enabled unless the operator handles version lifecycle externally
- **Live GCP validation not executed** — `docs/V5_17_LIVE_GCP_VALIDATION_RESULTS.md` is an unfilled template
- **No real Google Ads live API validation** — `live_api_tested=false` always; `GOOGLE_ADS_LIVE_ENABLED=false`

---

## Deferred Work

- Cloud Run deployment (requires service account, IAM, billing authorization)
- BigQuery audit replication
- Cloud Storage audit archival with optional object lock
- KMS/HSM cryptographic audit signing
- GCP Secret Manager version destruction / disable policy on rotate
- Redis/Memorystore distributed rate limiting
- OAuth2 / admin identity provider integration
- Real Google Ads OAuth credential onboarding
- Real Google Ads live API validation
- Multi-instance production rate limiting
- Live GCP lifecycle validation execution

---

## Upgrade and Merge Notes

No database migrations. No API changes. No client-side changes required.

Merge recommendation:
```bash
git checkout master
git merge --no-ff v5.17-production-readiness
git tag v5.17.0-beta
```

---

## Related Documents

- [V5.17 Branch Closure](V5_17_BRANCH_CLOSURE.md)
- [Credential Lifecycle Runbook](CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [V5.17 Live GCP Validation Plan](V5_17_LIVE_GCP_VALIDATION_PLAN.md)
- [V5.17 Live GCP Validation Results](V5_17_LIVE_GCP_VALIDATION_RESULTS.md) (template — not yet executed)
- [V5.17 Per-Tenant Permission Design](V5_17_PER_TENANT_PERMISSION_DESIGN.md)
- [V5.17 Rate Limiting Design](V5_17_RATE_LIMITING_DESIGN.md)
- [V5.17 Audit Hardening Decision](V5_17_AUDIT_HARDENING_DECISION.md)
- [V5.16 Branch Closure](V5_16_BRANCH_CLOSURE.md)
- [Release Notes — v5.16.0-beta](RELEASE_NOTES_V5_16_0_BETA.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

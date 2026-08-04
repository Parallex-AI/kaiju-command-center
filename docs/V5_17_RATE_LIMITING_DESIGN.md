# V5.17 Phase 4 — Rate Limiting Design

**Kaiju Command Center — OpenClaw**

---

## 1. Purpose

OpenClaw admin credential endpoints are authenticated and scoped, but a compromised or
misconfigured caller can still issue a high volume of requests per minute. This document
specifies the local-first, zero-infrastructure rate limiting design added in V5.17 Phase 4.

---

## 2. Design Principles

- **Local-only.** Rate limit state lives in the process. No Redis, no Memorystore, no
  external service, no fixed-cost infrastructure.
- **Backward-compatible default.** Both env vars default to `0` (disabled). Existing
  deployments see no change in behavior.
- **Per-token, per-category.** Each (token, category) pair has its own sliding window
  bucket. Exhausting one token or category does not affect others.
- **Denied requests never consume budget.** Auth failures (401), scope failures (403
  `scope_not_granted`), and tenant failures (403 `tenant_access_denied`) are rejected
  before the rate check runs. Only authenticated, scoped, tenant-allowed requests consume
  rate budget.
- **Recoverable error with retry guidance.** HTTP 429 responses include
  `retry_after_seconds` so callers can back off deterministically.
- **No token values in responses.** Rate limit error responses follow the same no-leak
  contract as all other OpenClaw responses.

---

## 3. New Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENCLAW_ADMIN_RATE_LIMIT_RPM` | `0` | Max requests per minute for STANDARD routes per token. `0` = disabled. |
| `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` | `0` | Max requests per minute for SENSITIVE routes per token. `0` = disabled. |

---

## 4. Route Categories

### STANDARD (governed by `OPENCLAW_ADMIN_RATE_LIMIT_RPM`)

- `GET  /openclaw/admin/tenants/{t}/clients/{c}/credentials/google-ads/status`
- `POST /openclaw/admin/tenants/{t}/clients/{c}/credentials/google-ads` (upsert/write)
- `POST /openclaw/admin/tenants/{t}/clients/{c}/credentials/google-ads/validate`

### SENSITIVE (governed by `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM`)

- `POST   /openclaw/admin/tenants/{t}/clients/{c}/credentials/google-ads/rotate`
- `DELETE /openclaw/admin/tenants/{t}/clients/{c}/credentials/google-ads`

---

## 5. Request Evaluation Order

```
1. config load (reads env vars on every request — no cache)
2. validate_api_auth   → 401 if auth fails
3. extract_bearer_token
4. validate_api_auth scope check → 403 scope_not_granted if scope fails
5. validate_tenant_access → 403 tenant_access_denied if tenant denied
6. check_rate_limit   → 429 rate_limit_exceeded if budget exhausted
7. admin.py function
```

Steps 1–5 do not consume rate budget. Only step 6 onward may consume budget.

---

## 6. Sliding-Window Algorithm

- Window: 60 seconds
- Per (token, category) bucket stored as a `collections.deque` of monotonic timestamps
- On each request:
  1. Drop timestamps older than `now - 60s`
  2. If `len(bucket) < limit`: append `now`, allow
  3. Else: compute `retry_after = oldest_timestamp + 60 - now + 1`, deny
- `retry_after_seconds` is always at least 1

---

## 7. Key Implementation Files

| File | Role |
|---|---|
| `openclaw/rate_limit.py` | `RateLimiter`, `RateLimitCategory`, `get_rate_limiter()`, `check_rate_limit()` |
| `openclaw/config.py` | Adds `admin_rate_limit_rpm`, `admin_rate_limit_sensitive_rpm` fields |
| `openclaw/server.py` | Calls `check_rate_limit()` after tenant check in all 5 admin routes |

---

## 8. Singleton Lifecycle

`get_rate_limiter()` uses double-checked locking to return a process-singleton
`RateLimiter`. State is in-memory and lost on process restart or Cloud Run instance
recycling. This is intentional — rate limiting provides abuse protection, not hard quotas.

For tests, `RateLimiter.reset_for_tests()` clears all bucket state so scenarios start
fresh without reimporting the module.

---

## 9. Anonymous Bucket

When `OPENCLAW_API_AUTH_ENABLED=false`, no token is extracted. The rate limiter uses
the sentinel key `"__anon__"` as the token for shared anonymous rate limiting. This
prevents a crash when auth is disabled and ensures the rate limit still applies if
configured.

---

## 10. Interaction with Other Controls

Rate limiting composes with, not replaces, RBAC and tenant isolation:

- A request must pass auth → scope → tenant before it consumes rate budget.
- If RBAC or tenant checks are tightened later, rate budget is unaffected.
- STANDARD and SENSITIVE limits are independent — exhausting one does not affect the other.

---

## 11. Related Documents

- `docs/V5_17_PER_TENANT_PERMISSION_DESIGN.md` — Phase 3 per-tenant token isolation
- `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` — Operational runbook including rate limit config

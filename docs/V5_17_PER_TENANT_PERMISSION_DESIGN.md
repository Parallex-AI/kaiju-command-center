# V5.17 Phase 3 — Per-Tenant Token Isolation Design

**Kaiju Command Center — OpenClaw**

---

## 1. Purpose

OpenClaw admin endpoints operate on tenant-scoped credential data. Prior to V5.17, any
authenticated token with the correct scope could access credentials for any tenant. This
document specifies the local-first design for restricting individual tokens to specific
tenant IDs via the `OPENCLAW_TENANT_KEYS` environment variable.

---

## 2. Current Gap

V5.16 RBAC controls *what operations* a token may perform (READ, WRITE, VALIDATE, ROTATE,
DELETE, ADMIN scopes) but does not control *which tenants* a token may access. A single
admin token with WRITE scope can write credentials for any tenant in the system.

This is acceptable for single-operator deployments but introduces risk when multiple
operators share a deployment, or when a token is rotated per-client.

---

## 3. V5.17 Local-First Implementation

Tenant restriction is implemented entirely via a new environment variable
`OPENCLAW_TENANT_KEYS`. No database, no external policy service, no per-tenant config
files. The restriction map is parsed at request time from the env var.

**Files changed:**

| File | Change |
|---|---|
| `openclaw/config.py` | Added `parse_tenant_keys()` parser; added `tenant_keys: Dict[str, Set[str]]` field to `OpenClawConfig`; updated `config_to_dict()` and `redacted_config_dict()` |
| `openclaw/auth.py` | Added `validate_tenant_access(token, tenant_id, config)` |
| `openclaw/server.py` | Config loaded once per request; tenant check added to all 5 admin routes after scope check |

---

## 4. OPENCLAW_TENANT_KEYS Format

```
OPENCLAW_TENANT_KEYS=<token-a>:<tenant-a>,<token-a>:<tenant-b>,<token-b>:<tenant-c>
```

- Comma-separated `token:tenant_id` pairs
- A token may appear multiple times to allow access to multiple tenants
- Whitespace around separators is stripped
- Malformed entries (no `:`, empty token, empty tenant) are silently skipped
- The env var may be set to any string that parses to a non-empty map

**Parsed result for example above:**

```python
{
    "token-a": {"tenant-a", "tenant-b"},
    "token-b": {"tenant-c"},
}
```

---

## 5. Request Evaluation Order

For every admin route:

1. **Parse config** — `get_config()` called once per request
2. **Authenticate token** — `validate_api_auth()` checks token presence and scope
   - Missing or invalid token → 401 `unauthorized`
   - Valid token but wrong scope → 403 `scope_not_granted`
3. **Check tenant access** — `validate_tenant_access(token, tenant_id, config)` called
   only after auth/scope succeeds
   - Token not listed or map empty → allowed
   - Token listed, tenant allowed → allowed
   - Token listed, tenant not in set → 403 `tenant_access_denied`
4. **Call admin function** — only reached if both auth and tenant checks pass

The ordering guarantees that:
- An invalid token always returns 401, never 403 `tenant_access_denied`
- A valid token with insufficient scope always returns 403 `scope_not_granted`,
  never `tenant_access_denied`

---

## 6. Backward Compatibility Rules

| Condition | Behavior |
|---|---|
| `OPENCLAW_TENANT_KEYS` unset or empty | No restriction — all tokens may access all tenants |
| Map is set, token not listed | Token has global access (backward compat) |
| Map is set, token listed, tenant in set | Access allowed |
| Map is set, token listed, tenant not in set | 403 `tenant_access_denied` |
| Auth disabled (`OPENCLAW_API_AUTH_ENABLED=false`) | Token is `None`; `validate_tenant_access(None, ...)` → global access |

**No breaking change:** deployments that do not set `OPENCLAW_TENANT_KEYS` behave
identically to V5.16.

---

## 7. Error Model

**HTTP 403** with body:

```json
{
  "ok": false,
  "request_id": "<uuid>",
  "trace_id": "<uuid>",
  "tenant_id": "<tenant_id>",
  "client_id": "<client_id>",
  "integration_type": "google_ads",
  "errors": [
    {
      "code": "tenant_access_denied",
      "message": "Token is not authorized to access this tenant.",
      "recoverable": false,
      "source": "openclaw"
    }
  ]
}
```

The response does not include the token value, the allow-list, or any other
token-permission metadata.

---

## 8. Security Posture

- Token values are never echoed in responses
- The tenant allow-list is never exposed in responses (only `restriction_enabled` and
  `restricted_token_count` are surfaced in `redacted_config_dict()`)
- Restriction is enforced server-side on every request — no client-supplied header can
  bypass it
- Auth and scope are checked before tenant access, so an unauthenticated request cannot
  probe tenant existence via `tenant_access_denied`
- `validate_tenant_access` is a pure function with no I/O; it can be unit-tested without
  a running server

---

## 9. Limitations

- **No per-request audit of tenant check.** The audit event records the operation but not
  whether a tenant check was evaluated. A future phase may add this.
- **Static map only.** `OPENCLAW_TENANT_KEYS` is read from the environment at request
  time. A process restart is required to change the map. No hot reload.
- **No expiry.** Token-to-tenant bindings have no TTL. Rotation requires updating the
  env var and restarting.
- **No per-tenant scope.** A listed token has the same scope (READ, ADMIN, etc.) for all
  of its allowed tenants. Fine-grained per-tenant scopes require the future `TenantPolicy`
  model (Section 10).
- **Single deployment.** This design is local-first. Multi-process or multi-replica
  deployments must ensure `OPENCLAW_TENANT_KEYS` is consistent across all instances.

---

## 10. Future TenantPolicy Shape

When per-tenant scope control is needed, a `TenantPolicy` model will replace the env var
map. Proposed shape:

```python
@dataclass
class TenantPolicy:
    tenant_id: str
    actor_id: str          # token hash or service account identifier
    scopes: set            # subset of AdminScope values
    allowed_clients: set   # client_id restrictions within tenant (empty = all)
    expires_at: Optional[str]  # ISO 8601 UTC; None = no expiry
    source: str            # "env", "config_file", "iam", "oauth"
```

Policies would be loaded from a config file or a policy service, with the env var path
remaining as a fallback for local deployments.

---

## 11. Future IAM / OAuth Path

For production multi-tenant deployments, token-to-tenant bindings should be managed via:

- **GCP IAM conditions** on service account bindings (per-tenant resource scoping)
- **OAuth 2.0 scopes** with tenant_id embedded in the token claim
- **A policy microservice** that evaluates `(actor, tenant, scope)` tuples

The `OPENCLAW_TENANT_KEYS` mechanism is intentionally designed to be replaced by one of
these without changing `validate_tenant_access`'s call signature.

---

## 12. Non-Goals

- This design does not implement per-client-id isolation within a tenant
- This design does not implement token revocation (use `OPENCLAW_ADMIN_KEYS` rotation)
- This design does not persist the allow-list to GCP Secret Manager
- This design does not log token values, even in redacted form
- This design does not change `admin.py` — all tenant enforcement is in the HTTP layer

---

## 13. Test Coverage

| Layer | Coverage |
|---|---|
| `parse_tenant_keys()` unit tests | Empty, single pair, multi-tenant same token, malformed entries |
| `validate_tenant_access()` unit tests | No map, token not listed, allowed, denied, None token |
| FastAPI TestClient integration | Allowed tenant → 200; denied tenant → 403; invalid token → 401 |
| API demo scenarios | Tenant A–G covering all backward-compat and denial paths |
| Smoke test section | `[18/18]` — imports, parse, unit, TestClient, API demo |

See `scripts/smoke_test_v5_credentials.sh` section `[18/18]` and
`openclaw/run_admin_credentials_lifecycle_api_demo.py` Tenant A–G scenarios.

---

## Related Documents

| Document | Purpose |
|---|---|
| `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` | Operator runbook for the full credential lifecycle |
| `docs/GCP_SECRET_MANAGER_RUNBOOK.md` | GCP Secret Manager integration reference |
| `docs/V5_17_LIVE_GCP_VALIDATION_PLAN.md` | Fake-secret live GCP validation plan |

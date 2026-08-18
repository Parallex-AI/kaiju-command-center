# V5.19 Implementation Plan — Real Credential Readiness Gates

**Branch:** `v5.19-real-credential-readiness-gates`
**Base:** `v5.18.0-beta` / master after `da2796e`
**Working title:** Real Credential Readiness Gates
**Status:** Phase 6 in progress — audit event additions for live guard/preflight underway; Phases 1–5 committed

---

## Purpose

V5.19 builds the safety controls, approval workflow, preflight infrastructure, runtime guardrails, audit requirements, and operator documentation needed before any real Google Ads credential onboarding or live API validation can occur. It does not perform real onboarding or live API calls. All work is gate-building, policy design, and safety infrastructure.

The goal is that after V5.19, the question "can we now safely onboard real credentials?" has a clear, auditable, structured answer — either "yes, all gates pass" or "no, gate X is not satisfied."

---

## Starting Point

| Property | State |
|----------|-------|
| V5.18.0-beta | Shipped |
| Fake live GCP Secret Manager credential lifecycle | All 14 phases A–N PASS |
| Cleanup | Complete |
| Credential final state | REVOKED |
| Real Google Ads credentials | Not used |
| `GOOGLE_ADS_LIVE_ENABLED` | `false` — unchanged |
| Deploy | None |
| IAM changes | None |
| API enablement | None |
| Billing changes | None |
| Fixed-cost infrastructure | None |

---

## Non-Goals for V5.19

V5.19 explicitly does not:

- Use real Google Ads credentials
- Call the Google Ads API
- Execute an OAuth consent flow with real credentials
- Set `GOOGLE_ADS_LIVE_ENABLED=true` in any committed or deployed configuration
- Deploy to Cloud Run or any production environment
- Modify IAM policies
- Enable additional GCP APIs
- Touch billing
- Create fixed-cost infrastructure
- Onboard real production clients
- Implement an external approval UI

These items remain deferred to a separately authorized milestone.

---

## Design Areas

### A. `GOOGLE_ADS_LIVE_ENABLED` Safety Gate

**Current state:** `false` by default; no enforcement beyond the default.

**V5.19 design:**

Define a `_check_live_gate(config, tenant_id, client_id)` function in `openclaw/admin.py` (or a new `openclaw/live_gate.py` module) that enforces the following conditions before any live Google Ads API call is permitted:

| Condition | Check | Error code on failure |
|-----------|-------|-----------------------|
| `GOOGLE_ADS_LIVE_ENABLED=true` | Config value | `live_mode_disabled` |
| Approval record present for this tenant/client | Approval store check | `approval_missing` |
| Preflight check passed (see Section F) | Runtime preflight | `preflight_failed` |
| Credential status is ACTIVE | `LocalFileCredentialReferenceStore` | `credential_not_ready` |
| Structural completeness confirmed | `get_secret_status()` | `credential_incomplete` |
| Tenant token boundary enforced | `validate_tenant_access()` | `tenant_gate_failed` |
| Audit enabled | Config check | `audit_not_enabled` |

**Gate behavior:**
- All conditions must pass. Any single failure blocks the gate and returns a structured error.
- Audit event emitted on both gate pass and gate fail.
- Gate failure returns `ok=false` with structured `errors[]` — no raw secret data in error body.
- `GOOGLE_ADS_LIVE_ENABLED=false` always passes the gate check with `live_mode_disabled` — the check is short-circuit safe.

**Default must remain `false`.** No V5.19 code or test should set it to `true`.

---

### B. Real Credential Approval Workflow — Phase 3 implementation note

**Phase 3 adds `openclaw/approval.py`** with a local `ApprovalRecord` dataclass, `LocalFileApprovalStore`, `validate_approval_record()`, `is_approval_valid()`, and `sanitize_approval_record()`. Approval records contain no secrets, no credential values, no credential references, and no GCP resource paths. This local store is for development and testing only. Real operator approvals require a separate out-of-band process not implemented in V5.19.

**This does not authorize real Google Ads API usage.** No real Google Ads credential onboarding is performed. `GOOGLE_ADS_LIVE_ENABLED` remains `false` throughout V5.19.

**Phase 5 adds `openclaw/live_guard.py`** with `guard_live_google_ads_operation()` (for future adapter code with a real `ApprovalRecord`), `guard_live_google_ads_from_signals()` (for HTTP routes using pre-resolved boolean signals), and safe response builders `build_live_guard_denied_response()` / `build_live_guard_allowed_response()`. A new server route `POST /openclaw/admin/live-google-ads/preflight` is added to `server.py` as a preflight-only probe: `live_enabled` is always derived from `GOOGLE_ADS_LIVE_ENABLED` (server-side env var, default false), never from the request body. All responses include `live_api_tested=false` and exclude `tenant_id`, `client_id`, `approval_id`, and all credential/secret fields. This does not authorize real Google Ads API usage. No GCP, Secret Manager, or Google Ads API calls. `GOOGLE_ADS_LIVE_ENABLED` remains `false`.

**Phase 6 adds `build_live_guard_audit_event()` to `openclaw/audit.py`** and wires audit emission into the `POST /openclaw/admin/live-google-ads/preflight` route. Every route call emits two events: `live_gate_check` (always) and either `live_mode_denied` (if denied) or `live_preflight_allowed` (if allowed). Live guard audit events never include `tenant_id`, `client_id`, `approval_id`, `credential_ref`, `secret_id`, `customer_id`, `login_customer_id`, `refresh_token`, `access_token`, `developer_token`, or `client_secret`. `verify_audit_file()` passes on emitted events. Smoke test extended to 25/25.

**Phase 4 adds `openclaw/preflight.py`** with `LiveOperationPreflightInput`, `LiveOperationPreflightResult`, and `check_live_operation_preflight()`. The checker composes `is_approval_valid()` (Phase 3) and `check_live_gate()` (Phase 2) into a single call. The sanitized summary omits tenant/client identifiers and approval IDs, containing only boolean readiness signals and status strings safe for logging. This does not authorize real Google Ads API usage. No real credentials used. No GCP, Secret Manager, or Google Ads API calls. `GOOGLE_ADS_LIVE_ENABLED` remains `false`.

---

### B. Real Credential Approval Workflow

**Purpose:** Require an explicit, auditable, operator-authored approval record before live mode is permitted for any tenant/client pair.

**Approval record format (JSON):**

```json
{
  "approval_id": "<uuid>",
  "approved_by": "<operator_label>",
  "approved_at": "<ISO8601_timestamp>",
  "scope": "google_ads_live_validation",
  "tenant_id": "<redacted_or_labeled>",
  "client_id": "<redacted_or_labeled>",
  "intended_operation": "<description_of_what_will_be_called>",
  "expiry": "<ISO8601_timestamp_or_null>",
  "rollback_plan": "<brief_description>",
  "revoked": false,
  "revoked_at": null,
  "notes": ""
}
```

**Rules:**
- No secrets, tokens, credential values, refresh tokens, or developer tokens in the approval record.
- No `credential_ref`, `secret_id`, or GCP resource paths.
- Approval is stored separately from code commits (local file outside repo, or future operator system).
- Approval must be revocable (`revoked: true`). A revoked approval fails the gate.
- Approval is scoped to a specific tenant/client pair — not global.
- Approval expires if `expiry` is set and current time exceeds it.
- Approval is separate from credential write or live enablement — it is a preceding record only.
- Generating an approval record is an operator action; Claude Code does not self-approve.

**`ApprovalStore` interface (V5.19 design, not full implementation):**
- `get_approval(tenant_id, client_id) → ApprovalRecord | None`
- `is_approval_valid(record) → bool` — checks not revoked, not expired, scope matches
- Storage backend: local file (initial), future: GCP Secret Manager or operator system

---

### C. Tenant/Client Readiness Gate

Before any live operation, the following must be confirmed for the target tenant/client:

| Check | Source | Required state |
|-------|--------|---------------|
| Credential reference exists | `LocalFileCredentialReferenceStore` | Entry present |
| Credential status | `CredentialReference.status` | `ACTIVE` |
| Structural completeness | `get_secret_status()` | `configured=true`, all 4 fields present |
| Tenant token boundary | `validate_tenant_access()` | Access granted |
| Customer ID present | `CredentialReference.customer_id` | Non-null |
| Credential not revoked | `CredentialReference.status` | Not `REVOKED` |

**Customer ID handling:** `customer_id` and `login_customer_id` are sensitive metadata. They must not appear in audit events, logs, or API responses beyond confirmation of presence. Pass as redacted references only.

**Failure behavior:** Any failed readiness check returns a specific error code (see Section G) and does not proceed to any credential access or API call.

---

### D. OAuth Onboarding Readiness Design

**Status:** Design-only in V5.19. No implementation of live OAuth execution.

**Intended future flow (do not implement without separate authorization):**

```
Operator → OAuth2 authorization URL
    ↓ User/operator grants consent
Authorization code → Token exchange endpoint
    ↓
Refresh token + client credentials
    ↓ Write to GCP Secret Manager via put_secret_bundle()
Credential reference created or updated
    ↓
Structural validation confirms all 4 fields present
    ↓
Approval record created for live gate
```

**Key design decisions for V5.19 documentation:**
- Where does the OAuth authorization URL come from? (Google Ads OAuth2 endpoint; client_id + scope + redirect_uri)
- Where is the authorization code exchanged? (Server-side endpoint, not client-side)
- How is the refresh token written? (`put_secret_bundle()` via admin endpoint — same path as fake-secret rehearsal)
- What happens if token exchange fails? (No partial write; error logged without secrets)
- What is the revocation flow? (`DELETE /credentials/google-ads` → `delete_secret_bundle()` → REVOKED — same path as Phase J)
- What is the refresh token rotation strategy? (On expiry: detect `UNAUTHENTICATED` from Google Ads API, trigger rotate flow)

**V5.19 deliverable:** Design document (`docs/V5_19_OAUTH_ONBOARDING_DESIGN.md` — optional if time permits; otherwise inline in this plan).

---

### E. Secret Manager Version Lifecycle Policy

**Current state (from V5.18):** `put_secret_bundle()` calls `add_secret_version`. The prior version remains enabled. Both V1 and V2 were deleted together in Phase J via `delete_secret_bundle()`.

**Problem:** If rotation is performed without deleting old versions, prior versions accumulate and remain accessible to any IAM principal with `secretAccessor`. This is a security hygiene concern for real credentials.

**Policy options:**

| Option | Description | Trade-off |
|--------|-------------|-----------|
| A. Disable prior version on rotate | After `add_secret_version`, call `disable_secret_version` on the previous version | Prevents prior-version access; requires additional IAM (`secretVersionManager`); version still exists |
| B. Destroy prior version on rotate after grace period | After `add_secret_version`, call `destroy_secret_version` on version N-1 after a configurable delay | Irreversible; prevents any recovery of prior version; simplest long-term hygiene |
| C. Keep all versions enabled | Current behavior — no additional action | Simplest code; accumulates versions; prior versions accessible |
| D. Operator-managed lifecycle | Don't touch versions in code; document that operators must manage version lifecycle externally | Zero code change; operational burden on operator |

**V5.19 decision:** Document the options and select a policy. **Do not implement destructive version lifecycle (Option B) in V5.19 unless explicitly authorized as a separate implementation phase.** Option A (disable) is the recommended starting point — it prevents prior-version access without being irreversible.

**Implementation scope if authorized:**
- `_disable_prior_secret_version(secret_id, current_version)` in `GCPSecretManagerStore`
- Called after successful `add_secret_version` in `put_secret_bundle()`
- Error on disable is non-fatal (log warning, do not fail rotation)
- New IAM permission required: `secretmanager.versions.disable` (part of `roles/secretmanager.secretVersionManager`)

---

### F. Preflight Checklist Before Real Google Ads API Validation

A `run_live_preflight(config, tenant_id, client_id)` function that validates all conditions before any live-mode operation is attempted. Returns `(ok: bool, failures: list[str])`.

| # | Check | Pass condition | Failure code |
|---|-------|---------------|-------------|
| 1 | ADC / cloud auth available | `gcp_secret_manager_status()` init_errors empty | `adc_not_available` |
| 2 | `GCP_PROJECT_ID` set | Config non-empty | `project_id_missing` |
| 3 | `GCP_SECRET_MANAGER_ENABLED=true` | Config true | `secret_manager_disabled` |
| 4 | `GOOGLE_ADS_LIVE_ENABLED=false` (pre-gate) | Still false until gate passes | `live_mode_not_controlled` |
| 5 | Tenant/client credential reference exists | Store lookup | `credential_reference_missing` |
| 6 | Credential status is ACTIVE | Reference status | `credential_not_active` |
| 7 | Structural completeness | `get_secret_status()` → all 4 fields | `credential_incomplete` |
| 8 | `OPENCLAW_AUDIT_ENABLED=true` | Config true | `audit_not_enabled` |
| 9 | Delete/revoke path tested | V5.18 Phase J PASS (documented) | N/A — documentation check |
| 10 | Rollback plan present | Approval record `rollback_plan` non-empty | `rollback_plan_missing` |
| 11 | No secrets in environment logs | Grep check on runtime env (not `GOOGLE_ADS_*` raw values in logs) | `secrets_in_logs` |
| 12 | Approval record valid | `is_approval_valid()` | `approval_missing_or_invalid` |

**Preflight output:** Structured result with pass/fail per check — no credential values, no raw secrets.

---

### G. Runtime Guardrails

**Live adapter call guard:**

Before any code path that would call `fetch_google_ads_metrics()` with a real credential source:

```python
gate_result = check_live_gate(config, tenant_id, client_id)
if not gate_result.ok:
    emit_live_gate_denied_audit_event(tenant_id, client_id, gate_result.failures)
    return {"ok": False, "errors": gate_result.errors}
```

**Error codes to define:**

| Code | Meaning |
|------|---------|
| `live_mode_disabled` | `GOOGLE_ADS_LIVE_ENABLED=false` |
| `approval_missing` | No valid approval record for this tenant/client |
| `approval_expired` | Approval record past expiry |
| `approval_revoked` | Approval record marked revoked |
| `preflight_failed` | One or more preflight checks failed |
| `credential_not_ready` | Credential reference missing, REVOKED, or incomplete |
| `tenant_gate_failed` | Token not authorized for this tenant |
| `audit_not_enabled` | `OPENCLAW_AUDIT_ENABLED` is false |
| `rollback_plan_missing` | Approval record has no rollback plan |

**Principle:** Gate errors must never expose credential values, customer IDs, secret resource paths, or project identifiers. Error bodies contain only error codes, human-readable messages, and boolean flags.

**Raw credential fetch guard:** `get_secret_bundle()` must never be called outside the adapter boundary. Validate/rotate/delete paths already enforce this (confirmed V5.18). Live adapter path must enforce the same.

---

### H. Audit Requirements

**New audit operation types for V5.19:**

| `operation` | `ok` meaning | When emitted |
|-------------|-------------|-------------|
| `live_gate_check` | `true` = gate passed | Every live-gate evaluation (pass or fail) |
| `live_mode_denied` | `false` always | Gate evaluation failed |
| `preflight_check` | `true` = all checks pass | Before live adapter invocation |
| `adapter_invoked` | `true` = call initiated | At live adapter invocation boundary |

**Audit field rules (all existing rules apply plus):**
- No `customer_id` or `login_customer_id` values — presence boolean only
- No approval record secrets
- No `approval_id` if it could correlate to operator identity
- `tenant_id` and `client_id` — OK to include (non-secret metadata)
- `gate_failures: [list_of_error_codes]` — OK (no values)
- No GCP resource paths

---

### I. Rollback and Emergency Revoke Procedure

Formal procedure for revoking a live credential after onboarding:

**Step 1 — Disable live mode**
```bash
# Remove GOOGLE_ADS_LIVE_ENABLED=true from server environment
# Stop and restart server without the flag
```

**Step 2 — Revoke credential via API**
```bash
DELETE /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads
# Requires OPENCLAW_ADMIN_DELETE_ENABLED=true in server env (temporary)
# Requires ADMIN scope token
```

**Step 3 — Confirm post-revoke status**
```bash
GET /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/status
# Expect: credential_status.status=revoked, secret_status.configured=false
```

**Step 4 — Verify audit trail**
```python
verify_audit_file(path)
# Expect: op=delete ok=True present; seq/digest chain valid
```

**Step 5 — Revoke approval record**
```json
{ "revoked": true, "revoked_at": "<timestamp>", "notes": "<incident_description>" }
```

**Step 6 — Document incident**
- Record what operation was attempted, what failed or required revocation, timestamp, operator identity, resolution.
- No credential values in incident record.

**Step 7 — Restore delete gate**
```bash
# Remove OPENCLAW_ADMIN_DELETE_ENABLED=true from server env
# Restart server
```

---

### J. Documentation and Runbook Updates

| Document | Update scope |
|----------|-------------|
| `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` | Section 11 (real credential readiness gates) — fill in gate checklist; add approval record procedure; add rollback procedure |
| `docs/GCP_SECRET_MANAGER_RUNBOOK.md` | Version lifecycle policy decision; prior-version disable procedure (if authorized) |
| `docs/V5_19_IMPLEMENTATION_PLAN.md` | This document — filled with implementation details as phases complete |
| `docs/ROADMAP.md` | V5.19 phases updated as they complete |
| `README.md` | V5.19 current milestone entry |
| `docs/V5_19_BRANCH_CLOSURE.md` | Created at closure (Phase 9) |
| `docs/RELEASE_NOTES_V5_19_0_BETA.md` | Created at closure (Phase 9) |

---

### K. Test Strategy

**Unit tests (no live GCP, no Google Ads API):**
- `test_live_gate_disabled` — `GOOGLE_ADS_LIVE_ENABLED=false` → `live_mode_disabled` error
- `test_live_gate_no_approval` — no approval record → `approval_missing` error
- `test_live_gate_expired_approval` — expired approval → `approval_expired` error
- `test_live_gate_revoked_approval` — revoked approval → `approval_revoked` error
- `test_live_gate_revoked_credential` — credential status REVOKED → `credential_not_ready` error
- `test_live_gate_incomplete_credential` — missing fields → `credential_incomplete` error
- `test_live_gate_all_pass` — all conditions met with mocked store → gate passes
- `test_preflight_missing_project` — `GCP_PROJECT_ID` not set → `project_id_missing`
- `test_preflight_audit_disabled` — `OPENCLAW_AUDIT_ENABLED=false` → `audit_not_enabled`
- `test_approval_record_valid` — non-expired, non-revoked → `is_approval_valid()` true
- `test_approval_record_expired` — expiry in past → false
- `test_approval_record_revoked` — `revoked: true` → false

**FastAPI TestClient tests:**
- Denied live-mode request → `ok=false`, correct error code, no secrets in response body
- Gate audit event emitted on denial — `op=live_mode_denied` present
- Gate audit event emitted on pass — `op=live_gate_check ok=True` present

**Smoke tests:**
- All gate logic must be exercisable with `GOOGLE_ADS_LIVE_ENABLED=false`
- Smoke test extension: `[21/21]` — live gate denial path; approval record validation
- No live Google Ads calls in any smoke test

**Explicitly excluded from V5.19 test scope:**
- Real Google Ads API calls
- Real OAuth token exchange
- Live GCP Secret Manager calls in tests (mocked only via `InMemorySecretStore`)
- `GOOGLE_ADS_LIVE_ENABLED=true` in any test

---

### L. Release Criteria

V5.19 is ready to merge and tag when:

| Criterion | Requirement |
|-----------|-------------|
| Live gate implemented | `check_live_gate()` returns structured pass/fail |
| Approval record model defined | `ApprovalRecord` dataclass + `ApprovalStore` interface |
| Preflight checker implemented | `run_live_preflight()` returns per-check result |
| Runtime guardrails in place | Adapter call guarded by gate check |
| Audit events defined and emitted | `live_gate_check`, `live_mode_denied`, `preflight_check` |
| All tests pass | 20/20 + 8/8 smoke suites + new unit/API tests |
| `GOOGLE_ADS_LIVE_ENABLED=false` by default | Confirmed in all configs and tests |
| No secrets exposed | Safety grep clean |
| No cloud changes | No GCP, IAM, billing, or deploy operations |
| Credential lifecycle runbook Section 11 updated | Gates and approval procedure documented |
| Deferred real API validation clearly stated | Release notes and closure doc explicit |

---

### M. Phase Breakdown

| Phase | Description | Deliverables |
|-------|-------------|-------------|
| 1 | Planning and branch setup | `docs/V5_19_IMPLEMENTATION_PLAN.md`; `docs/ROADMAP.md` update; `README.md` update; branch `v5.19-real-credential-readiness-gates` |
| 2 | Live-mode gate design | `openclaw/live_gate.py` (or `openclaw/admin.py` extension); `check_live_gate()` function; error codes; unit tests |
| 3 | Approval record model | `ApprovalRecord` dataclass; `ApprovalStore` interface; `LocalFileApprovalStore` initial implementation; `is_approval_valid()`; unit tests |
| 4 | Preflight checker | `run_live_preflight()` function; per-check result structure; integration with gate; unit tests |
| 5 | API/server guardrails | Server route guard for any live-mode path; `live_mode_disabled` short-circuit; FastAPI TestClient tests |
| 6 | Audit event additions | `op=live_gate_check`, `op=live_mode_denied`, `op=preflight_check`, `op=adapter_invoked` events; forbidden field check; smoke test extension |
| 7 | Runbook updates | `CREDENTIAL_LIFECYCLE_RUNBOOK.md` Section 11 gates + approval procedure; `GCP_SECRET_MANAGER_RUNBOOK.md` version lifecycle policy |
| 8 | Test coverage | New smoke test section `[21/N]` for gate denial paths; full test pass before closure |
| 9 | Closure docs and release notes | `docs/V5_19_BRANCH_CLOSURE.md`; `docs/RELEASE_NOTES_V5_19_0_BETA.md`; `docs/ROADMAP.md` V5.19 complete; `README.md` V5.19 complete |
| 10 | Merge, tag, release | `git merge --no-ff`; `git tag v5.19.0-beta`; `gh release create` |

---

### N. Risks

| Risk | Mitigation |
|------|-----------|
| Accidental live enablement during development | Default `GOOGLE_ADS_LIVE_ENABLED=false`; gate short-circuits immediately when false; no test sets it to true |
| Real credential leakage | Gate blocks before any credential fetch; `get_secret_bundle()` not called unless gate passes; approval record contains no credential values |
| Overclaiming production readiness | Release notes and closure doc explicitly state V5.19 validates gates only; real API validation remains deferred |
| Stale ADC / cloud auth | Preflight check `adc_not_available` fails early; no silent fallback |
| Tenant boundary mistakes | `validate_tenant_access()` remains in gate chain; tenant gate failure blocks before credential access |
| Secret Manager old-version exposure | Version lifecycle policy decision documented in V5.19; implementation only if authorized |
| Audit incompleteness | New audit events for gate/preflight added in Phase 6; smoke test asserts presence |
| Approval record tampering | Approval store read is first gate check; invalid/revoked/expired approval fails immediately |

---

### O. Explicit Deferred Work

The following items are **not** in V5.19 scope and require separate explicit authorization:

| Deferred item | Notes |
|---------------|-------|
| Real Google Ads OAuth credential onboarding | Requires `GOOGLE_ADS_LIVE_ENABLED=true`, real refresh token, explicit operator approval, V5.19 gate PASS |
| Real Google Ads live API validation | Requires all gates PASS, real credentials, explicit operator approval per-prompt |
| Cloud Run deployment | Requires service account, IAM, billing authorization |
| IAM hardening beyond current posture | `secretVersionManager` for version disable, if version lifecycle policy is implemented |
| Secret Manager prior-version destruction (Option B) | Irreversible; requires separate explicit authorization |
| External approval UI | Requires frontend; separate milestone |
| Multi-instance / distributed approval store | Redis or GCP-backed; separate milestone |
| OAuth2 / admin identity provider | Requires external IdP integration |
| BigQuery audit replication / Cloud Storage archival | Requires GCP dataset or bucket, IAM, billing |
| KMS/HSM cryptographic audit signing | Requires GCP KMS key |

---

## Related Documents

- [V5.18 Branch Closure](V5_18_BRANCH_CLOSURE.md)
- [Release Notes — v5.18.0-beta](RELEASE_NOTES_V5_18_0_BETA.md)
- [V5.18 Live GCP Fake Validation Results](V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md)
- [Credential Lifecycle Runbook](CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

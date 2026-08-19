# Release Notes — v5.19.0-beta

**Branch:** `v5.19-real-credential-readiness-gates`
**Base:** `v5.18.0-beta` / master after `da2796e`
**Tag candidate:** `v5.19.0-beta`
**Status:** Complete — Phases 1–8 PASS · closure docs complete · ready for merge and tag

---

## Release Summary

v5.19.0-beta implements the local and server-side readiness gates required before any future real Google Ads credential or live API validation. Building on V5.18's confirmed fake-secret GCP lifecycle, V5.19 adds `check_live_gate()`, `ApprovalRecord`, `LocalFileApprovalStore`, `check_live_operation_preflight()`, a server preflight route, live guard audit events, runbook documentation, and hardened test coverage across eight phases.

V5.19 implements real credential readiness gates only. V5.19 does not authorize real Google Ads usage. V5.19 does not validate real Google Ads credentials. V5.19 does not call the Google Ads API. V5.19 does not execute OAuth onboarding. V5.19 does not deploy to production. V5.19 does not change IAM, billing, APIs, or cloud architecture. `GOOGLE_ADS_LIVE_ENABLED` remains false by default. No GCP operations were performed.

---

## Highlights

- **`check_live_gate()` — 11-condition gate** — all 11 conditions must pass for live mode; no single flag can bypass the gate; structured denial codes and required-actions list on every denial
- **`ApprovalRecord` + `LocalFileApprovalStore`** — structured approval record model with status validation, expiry checking, forbidden-field/value detection in metadata, and local file store for operator testing
- **`check_live_operation_preflight()`** — composes approval validation and live gate check into a single preflight decision; sanitized summary excludes all tenant, client, and secret identifiers
- **Server preflight route** — `POST /openclaw/admin/live-google-ads/preflight`; `AdminScope.VALIDATE` required; `live_enabled` always derived server-side; `live_api_tested=false` on all responses
- **Two-event audit model** — every preflight route call emits `live_gate_check` + `live_mode_denied` or `live_preflight_allowed`; all 11 forbidden credential/secret/resource field names excluded
- **Phase 8 test hardening** — 18 live gate tests, 24 approval tests, 20 preflight tests, 14 server guard sections; auth (401) and scope (403) enforcement verified
- **Both smoke suites PASS throughout** — 26/26 and 8/8

---

## What's New

### Phase 2 — Live-mode gate (`check_live_gate()`)

`openclaw/live_gate.py` implements `check_live_gate()`, a pure Python function that evaluates 11 gate conditions in sequence and returns a structured `LiveGateResult`. All 11 conditions must pass for `allowed=True`. Denial returns a single `error_code`, human-readable `reasons`, and a non-empty `required_actions` list.

**11 denial codes:**

| Error code | Triggered when |
|---|---|
| `live_disabled` | `GOOGLE_ADS_LIVE_ENABLED` is not true |
| `approval_missing` | No approval record provided |
| `approval_invalid` | Approval record fails validation |
| `preflight_missing` | Preflight not completed |
| `audit_disabled` | Audit is not enabled |
| `credential_missing` | No credential reference provided |
| `credential_not_active` | Credential status is not exactly `ACTIVE` |
| `tenant_not_allowed` | Tenant not in the allowed set |
| `client_not_allowed` | Client not in the allowed set |
| `rollback_plan_missing` | No rollback plan documented |
| `operator_confirmation_missing` | No operator confirmation on record |

### Phase 3 — Approval record model

`openclaw/approval.py` provides `ApprovalRecord` (dataclass), `ApprovalStore` (abstract interface), `LocalFileApprovalStore`, `validate_approval_record()`, `is_approval_valid()`, and `sanitize_approval_record()`. Key properties:

- No secrets, credential values, or GCP resource paths in `ApprovalRecord`
- Forbidden field names and forbidden value patterns detected in `metadata` and denied
- Non-APPROVED status (PENDING, REJECTED, REVOKED, EXPIRED) triggers `approval_not_approved:<status>` error codes in `ApprovalValidationResult`
- `LocalFileApprovalStore` requires an explicit path argument — no default inside the repo; for local operator testing only

### Phase 4 — Preflight checker

`openclaw/preflight.py` implements `check_live_operation_preflight()`, which composes `validate_approval_record()` and `check_live_gate()` into a single preflight decision. The sanitized summary excludes `tenant_id`, `client_id`, `approval_id`, and all secret fields.

### Phase 5 — Server guardrails and preflight route

`openclaw/live_guard.py` implements `guard_live_google_ads_operation()` and `guard_live_google_ads_from_signals()`. The server preflight route `POST /openclaw/admin/live-google-ads/preflight` is added to `openclaw/server.py`. Key invariants:

- `live_enabled` derived server-side from `GOOGLE_ADS_LIVE_ENABLED` at request time; never read from request body
- All preflight responses include `live_api_tested=false`
- `LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS` absent from all live guard response shapes
- `AdminScope.VALIDATE` required; 401 without token, 403 for READ-scope token

### Phase 6 — Live guard audit events

`build_live_guard_audit_event()` added to `openclaw/audit.py`. Every preflight route call emits two audit events: `live_gate_check` followed by `live_mode_denied` (if denied) or `live_preflight_allowed` (if allowed). Audit events exclude all 11 forbidden credential/secret/resource field names. `verify_audit_file()` passes on emitted events.

### Phase 7 — Runbook updates

`docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` Section 18: V5.19 real credential readiness gate procedure, approval record format, all 11 gate conditions, preflight route shape, two-event audit model, rollback/revoke procedure.

`docs/GCP_SECRET_MANAGER_RUNBOOK.md` Section 18: Secret Manager prior-version lifecycle policy; four evaluated options; manual operator procedure; implementation deferred.

### Phase 8 — Test coverage hardening

- `run_live_gate_demo.py` Tests 15–18: empty and unknown `credential_status` denial; `required_actions` non-empty for all 11 denial codes; no forbidden field names in `LiveGateResult` serialization
- `run_approval_demo.py` Tests 17–24: PENDING/REJECTED/EXPIRED status denials; missing reason; future `expires_at` allows; wrong `integration_type`; forbidden metadata field name; forbidden metadata value pattern
- `run_preflight_demo.py` Tests 18–20: wrong integration type; `CONFIGURED` credential status denial; `VALIDATION_FAILED` credential status denial
- `run_server_live_guard_demo.py` Phase 8A/8B: 401 without token; 403 for READ-scope token on VALIDATE route
- Smoke test extended from 25/25 to 26/26; new [26/26] section covers 14 Phase 8 marker strings

---

## Confirmed Behaviors

| Behavior | Confirmed by |
|---|---|
| All 11 gate conditions evaluated; no single flag bypasses the gate | Phase 2 demo |
| `credential_not_active` fires on empty string, `UNKNOWN`, `CONFIGURED`, `VALIDATION_FAILED` | Phase 8 demo (Tests 15–16, 19–20) |
| All 11 denial codes produce non-empty `required_actions` | Phase 8 demo (Test 17) |
| `ApprovalRecord` contains no secret values or GCP resource paths | Phase 3 demo; safety grep |
| `LocalFileApprovalStore` requires explicit path; no default inside repo | Phase 3 demo |
| Non-APPROVED approval status (PENDING, REJECTED, EXPIRED) denied with `approval_not_approved:<status>` | Phase 8 demo (Tests 17–19) |
| Wrong `integration_type` triggers `approval_invalid` at gate | Phase 8 demo (approval Test 22; preflight Test 18) |
| Forbidden field names in `metadata` detected and denied | Phase 8 demo (Tests 23–24) |
| `check_live_operation_preflight()` sanitized summary excludes `tenant_id`, `client_id`, `approval_id`, secret fields | Phase 4 demo |
| `live_enabled` always derived server-side from `GOOGLE_ADS_LIVE_ENABLED`; never from request body | Phase 5 demo |
| All preflight responses include `live_api_tested=false` | Phase 5 demo + smoke |
| Forbidden response keys absent from all live guard response shapes | Phase 5, 6 demo + smoke |
| `AdminScope.VALIDATE` enforced: 401 without token, 403 for READ-scope token | Phase 8 demo (8A/8B) |
| Two audit events per route call: `live_gate_check` + `live_mode_denied` or `live_preflight_allowed` | Phase 6 demo + smoke |
| Audit events exclude all 11 forbidden credential/secret/resource field names | Phase 6 demo + smoke |
| `verify_audit_file()` passes on live guard emitted events | Phase 6 demo + smoke |

---

## Operational Notes

| Note | Detail |
|---|---|
| `live_enabled` source | Always read from `GOOGLE_ADS_LIVE_ENABLED` env var via `get_config()` at request time; never from request body; no request can override this signal |
| `LocalFileApprovalStore` scope | For local development and operator testing only; not a production approval authority; real approvals require a separate out-of-band process |
| Auth test pattern | `get_config()` reads `os.environ` on every request; env var changes take effect immediately on the same `TestClient` without module restart; Phase 8A/8B use this pattern |
| `live_api_tested=false` | Present on all preflight responses; the gate does not call the Google Ads API under any condition |

---

## Files Added

| File | Purpose |
|---|---|
| `openclaw/live_gate.py` | `check_live_gate()` — 11-condition gate with structured denial codes |
| `openclaw/approval.py` | `ApprovalRecord`; `LocalFileApprovalStore`; `validate_approval_record()`; `is_approval_valid()`; `sanitize_approval_record()` |
| `openclaw/preflight.py` | `check_live_operation_preflight()` — composes approval validation and live gate check |
| `openclaw/live_guard.py` | `guard_live_google_ads_operation()`; `guard_live_google_ads_from_signals()`; `LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS` |
| `openclaw/run_live_gate_demo.py` | 18-test demo: all 11 denial codes, allow path, credential status edge cases, required_actions, no forbidden keys |
| `openclaw/run_approval_demo.py` | 24-test demo: all approval status paths, store round-trip, forbidden field/value detection, metadata coverage |
| `openclaw/run_preflight_demo.py` | 20-test demo: all preflight denial paths, allow path, sanitized summary, wrong integration type, credential status |
| `openclaw/run_server_live_guard_demo.py` | 14-section demo: route behavior, helper behavior, audit emission, auth/scope enforcement |
| `docs/V5_19_IMPLEMENTATION_PLAN.md` | V5.19 full design specification and implementation notes |
| `docs/V5_19_BRANCH_CLOSURE.md` | Branch closure documentation |
| `docs/RELEASE_NOTES_V5_19_0_BETA.md` | This document |

---

## Files Modified

| File | Change |
|---|---|
| `openclaw/server.py` | Added `POST /openclaw/admin/live-google-ads/preflight`; live guard import; two-event audit emission |
| `openclaw/audit.py` | Added `build_live_guard_audit_event()` |
| `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` | Section 18: V5.19 real credential readiness gates and approval procedure |
| `docs/GCP_SECRET_MANAGER_RUNBOOK.md` | Section 18: Secret Manager version lifecycle policy |
| `docs/ROADMAP.md` | V5.19 Phases 1–9 marked complete; Phase 10 remains |
| `README.md` | V5.19 milestone updated; closure doc and release notes links added |
| `scripts/smoke_test_v5_credentials.sh` | Extended from 25/25 to 26/26; new [26/26] Phase 8 section |

---

## Tests

| Suite / Demo | Result |
|---|---|
| `scripts/smoke_test_v5_credentials.sh` | **26/26 PASS** |
| `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **8/8 PASS** |
| `openclaw/run_live_gate_demo.py` | **PASS** — 18 tests |
| `openclaw/run_approval_demo.py` | **PASS** — 24 tests |
| `openclaw/run_preflight_demo.py` | **PASS** — 20 tests |
| `openclaw/run_server_live_guard_demo.py` | **PASS** — Phases 1–6 + 8A/8B |
| Safety grep (Phase 9 changed files) | **CLEAN** |

---

## Security Summary

| Property | Status |
|---|---|
| No real Google Ads credentials used | Confirmed |
| No secret values in approval records | Confirmed |
| No GCP resource paths in approval records, live gate results, or audit events | Confirmed |
| No GCP operations performed | Confirmed |
| Google Ads API never called | Confirmed |
| `live_api_tested=false` on all preflight responses | Confirmed |
| Live guard response shapes exclude all forbidden field names | Confirmed |
| Audit events exclude all 11 forbidden credential/secret/resource field names | Confirmed |
| `GOOGLE_ADS_LIVE_ENABLED` remains `false` by default | Confirmed |
| No `.env` committed | Confirmed |
| No credential JSON committed | Confirmed |
| Safety grep CLEAN on all Phase 9 changed files | Confirmed |

---

## Deferred Work

- Real Google Ads OAuth credential onboarding (requires explicit operator approval gate; separate milestone)
- Real Google Ads live API validation (requires `GOOGLE_ADS_LIVE_ENABLED=true`; explicit operator approval)
- OAuth consent flow execution
- Production Cloud Run deployment (requires service account, IAM, billing authorization)
- GCP API enablement
- IAM changes
- Billing changes
- Secret Manager prior-version destruction policy (operator manual procedure documented in `docs/GCP_SECRET_MANAGER_RUNBOOK.md` Section 18)
- External approval UI (`LocalFileApprovalStore` for local operator testing only)
- Real production client onboarding

---

## Compatibility

No breaking changes. All existing routes and behaviors from V5.18 are preserved. The new `POST /openclaw/admin/live-google-ads/preflight` route is additive and admin-scoped (`AdminScope.VALIDATE`). V5.12 GCP Secret Manager smoke suite (8/8) confirms no regressions in the credential lifecycle stack. V5.18 smoke suite extended from 25/25 to 26/26 with no regressions in existing tests.

---

## Upgrade and Merge Notes

No database migrations. No API changes to existing endpoints. No client-side changes required. No environment variable changes required for existing deployments; `GOOGLE_ADS_LIVE_ENABLED` remains `false` by default.

Merge recommendation:

```bash
git checkout master
git merge --no-ff v5.19-real-credential-readiness-gates
git tag v5.19.0-beta
```

Tag message: `v5.19.0-beta — Real credential readiness gates: live gate · approval records · preflight checker · server guard · audit events · runbooks · test hardening (Phases 1–8 PASS)`

---

## Related Documents

- [V5.19 Branch Closure](V5_19_BRANCH_CLOSURE.md)
- [V5.19 Implementation Plan](V5_19_IMPLEMENTATION_PLAN.md)
- [V5.18 Branch Closure](V5_18_BRANCH_CLOSURE.md)
- [Release Notes — v5.18.0-beta](RELEASE_NOTES_V5_18_0_BETA.md)
- [Credential Lifecycle Runbook](CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

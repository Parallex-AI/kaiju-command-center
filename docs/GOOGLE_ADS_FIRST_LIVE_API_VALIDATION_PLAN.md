# Google Ads First Live API Validation Plan — V5.20

**Kaiju Command Center — V5.20 Phase 5**

**Branch:** `v5.20-controlled-real-google-ads-onboarding-readiness`

---

> **THIS IS A PLAN ONLY — READ BEFORE USING THIS DOCUMENT**
>
> - This document does **not** authorize real Google Ads API usage.
> - This document does **not** authorize real credential onboarding.
> - This document does **not** authorize OAuth execution.
> - This document does **not** authorize setting `GOOGLE_ADS_LIVE_ENABLED=true`.
> - This document does **not** constitute an approval record.
> - Any future execution of this plan requires a **separate, explicit, named-operator approval** recorded outside the repository in `LocalFileApprovalStore` and validated by `validate_approval_record()`.
> - No part of this document may be used to justify bypassing the V5.19/V5.20 gate infrastructure.

---

## A. Purpose

This document defines the controlled first live Google Ads API validation procedure for a future separately authorized phase. The objective is to prove that one approved credential can perform one read-only, non-mutating, time-boxed Google Ads API call under V5.19/V5.20 gates, with full audit coverage and an immediately ready rollback path.

This plan exists to make the future execution window as short, controlled, and recoverable as possible — not to expand scope, enable production usage, or bypass any gate.

---

## B. Preconditions

All items below must be confirmed by the authorizing operator **before** any live flag is set or any live call is attempted. This checklist must be completed in order.

| # | Item | Status |
|---|---|---|
| B1 | V5.19.0-beta shipped and tagged on master | [ ] |
| B2 | V5.20 `GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md` reviewed in full — all sections A–M complete | [ ] |
| B3 | `validate_onboarding_ceremony()` passes with current input | [ ] |
| B4 | `validate_credential_intake_dry_run()` passes with current input | [ ] |
| B5 | Valid `ApprovalRecord` exists in `LocalFileApprovalStore` at operator-specified path outside repo | [ ] |
| B6 | `approval_scope` matches `GOOGLE_ADS_LIVE_VALIDATION` | [ ] |
| B7 | Approval record is not expired | [ ] |
| B8 | Credential status is exactly `ACTIVE` in credential store | [ ] |
| B9 | Tenant and client are explicitly listed in the approval record and are the same as the live call target | [ ] |
| B10 | Audit is enabled (`OPENCLAW_AUDIT_ENABLED=true`) | [ ] |
| B11 | Rollback plan is documented in `ApprovalRecord.evidence` with named operator and steps | [ ] |
| B12 | Emergency revoke plan is documented | [ ] |
| B13 | Server preflight route (`POST /openclaw/admin/live-google-ads/preflight`) confirms `allowed=true` | [ ] |
| B14 | `check_live_gate()` returns `allowed=true` with real approval record | [ ] |
| B15 | Safety grep is clean on all changed files | [ ] |
| B16 | `smoke_test_v5_credentials.sh` passes (28/28) | [ ] |
| B17 | `smoke_test_v5_12_gcp_secret_manager.sh` passes (8/8) | [ ] |
| B18 | Final named-operator authorization recorded separately for this specific call | [ ] |
| B19 | `GOOGLE_ADS_LIVE_ENABLED` remains `false` until the final authorized execution window opens | [ ] |

**Precondition result:** [ ] ALL COMPLETE — proceed to execution window  /  [ ] BLOCKED — do not proceed

---

## C. Explicit Non-Goals

The following are explicitly out of scope for the first live validation and must not occur under this plan, even if technically possible with the credential:

- No campaign creation, modification, or deletion
- No ad group creation, modification, or deletion
- No keyword creation, modification, or deletion
- No bid or bidding strategy changes
- No budget creation, modification, or deletion
- No conversion action creation or modification
- No remarketing list or user-list access or changes
- No account linking or client relationship changes
- No background or scheduled jobs
- No bulk API operations or batch calls
- No write or mutate endpoints of any kind
- No multi-client or multi-tenant validation in a single window
- No persistent live mode — live flag must be reverted immediately after validation
- No production deployment or infrastructure changes
- No additional credential onboarding in the same window

---

## D. Candidate First API Call

The future call must be the most minimal read available — sufficient to confirm credential validity and account accessibility without exposing sensitive campaign, budget, keyword, or user data.

**Operation type:** Read-only account or customer accessibility check.

**Preferred future API surface:** A minimal customer or account metadata read — for example, a call that returns whether the credential has any accessible accounts, without returning campaign hierarchy, spend, bid data, conversion data, or keyword data. The Google Ads API `CustomerService` accessible-customer listing or equivalent minimal identity read is the preferred candidate; the exact method must be confirmed by the operator at execution time against the API version in use.

**Query constraints:**

| Constraint | Requirement |
|---|---|
| Endpoint type | Read-only only |
| Data exposed | Account-level identity or accessibility only |
| Campaign data | Must not be requested |
| Budget data | Must not be requested |
| Keyword data | Must not be requested |
| Conversion data | Must not be requested |
| User-list data | Must not be requested |
| Response size | Minimum possible; no pagination |
| Response handling | Must be redacted before any logging or documentation |
| Raw response | Must not be committed to the repository |
| Account/customer identifiers | Must be redacted in all evidence |

**Excluded:** Executable code, curl commands, real customer IDs, real developer token, real client secrets, real account identifiers. This section is design-only.

---

## E. Execution Window Constraints

The future authorized execution window must satisfy all of the following. Any deviation is a stop condition (see Section H).

| Constraint | Requirement |
|---|---|
| Tenant/client scope | Single explicitly approved tenant and client only |
| Operator | Single named authorizing operator present for the entire window |
| Time window | Single explicitly stated and bounded window; no open-ended live mode |
| Credential reference | Single credential reference matching the approval record |
| Call count | Single read-only call; one retry permitted only if explicitly authorized in the approval record |
| Background execution | Not permitted |
| Scheduled execution | Not permitted |
| Concurrent calls | Not permitted |
| Post-validation live flag | Live mode disabled immediately after validation result is captured |
| Output handling | All outputs must be redacted before capture; no raw API response committed |

---

## F. Required Runtime Flags (Future Execution Template)

The following describes the future flag state for the authorized execution window. No executable commands are included here. These settings are a documentation template only and do not authorize execution.

| Flag | Pre-window state | During authorized window | After window |
|---|---|---|---|
| `GOOGLE_ADS_LIVE_ENABLED` | `false` | May be `true` only if explicitly authorized for this window | Must be `false` — revert immediately |
| `OPENCLAW_AUDIT_ENABLED` | `true` | `true` — must remain enabled | `true` |
| `GCP_SECRET_MANAGER_ENABLED` | Operator-controlled | Operator-controlled | Operator-controlled |
| `OPENCLAW_API_AUTH_ENABLED` | `true` | `true` | `true` |

Constraints:
- `GOOGLE_ADS_LIVE_ENABLED=true` must not be set before the authorization window opens.
- The authorization window must be manually and immediately reverted after the call completes or if any stop condition fires.
- The request body for the preflight route must never be used to force `live_enabled=true` — the flag is read from the server environment only.
- The server preflight route must still return `live_api_tested=false` before the actual first live call is attempted, since that field reflects historical live API usage, not a pre-authorization state.

---

## G. Audit Sequence

The following events must appear in the audit chain before, during, and after the live validation window. All events must pass `verify_audit_file()` with `ok=true` after the window closes.

| Step | Event | Source |
|---|---|---|
| 1 | Approval record created and validated | `validate_approval_record()` |
| 2 | Onboarding ceremony PASS evidence recorded | `validate_onboarding_ceremony()` result |
| 3 | Credential intake dry-run PASS evidence recorded | `validate_credential_intake_dry_run()` result |
| 4 | Server preflight checked — `live_gate_check` event emitted | `build_live_guard_audit_event()` |
| 5 | Live gate evaluated — `live_preflight_allowed` or `live_mode_denied` event emitted | `build_live_guard_audit_event()` |
| 6 | Live validation window opens — operator records timestamp | Operator written record |
| 7 | Live call attempted — result captured as redacted structural summary only | Operator or server |
| 8 | Live flag disabled — operator confirms and records | Operator written record |
| 9 | Post-validation credential status confirmed | `GET /credentials/google-ads/status` |
| 10 | Audit chain verified with `verify_audit_file()` | `audit_maintenance.verify_audit_file()` |

**Forbidden audit fields** — none of the following may appear in any audit event, log line, evidence file, or documentation output:

| Forbidden field |
|---|
| `credential_ref` |
| `secret_id` |
| `customer_id` |
| `login_customer_id` |
| `developer_token` |
| `client_secret` |
| `refresh_token` |
| `access_token` |
| `project_id` |
| `project_number` |
| `service_account_email` |
| Raw response payload |
| Unredacted account identifiers |

---

## H. Stop Conditions

Any of the following must trigger an immediate halt and transition to the rollback sequence (Section I):

| # | Stop condition |
|---|---|
| H1 | Approval record missing, expired, revoked, or covering the wrong scope |
| H2 | `validate_onboarding_ceremony()` returns any failure code |
| H3 | `validate_credential_intake_dry_run()` returns any failure code |
| H4 | Server preflight route returns `allowed=false` for any reason |
| H5 | `check_live_gate()` returns `allowed=false` for any reason |
| H6 | Audit is disabled or `verify_audit_file()` returns `ok=false` |
| H7 | Rollback plan missing from `ApprovalRecord.evidence` |
| H8 | Emergency revoke path unavailable or untested |
| H9 | Any smoke test fails |
| H10 | Any secret, token, or credential value appears in terminal output, log, or audit file |
| H11 | Any account or customer identifier appears in any committed document |
| H12 | Unexpected Google Ads permission scope or permission error returned |
| H13 | API response contains sensitive campaign, budget, keyword, or conversion data not expected from the call |
| H14 | API call attempts or succeeds in any mutation |
| H15 | More than the approved number of retries is needed |
| H16 | `GOOGLE_ADS_LIVE_ENABLED` cannot be immediately reverted after the window closes |
| H17 | Any behavior not explicitly covered by the approval record |

---

## I. Rollback Sequence

Execute in order. Do not skip steps. Document each step result.

| Step | Action | Verify |
|---|---|---|
| 1 | Set `GOOGLE_ADS_LIVE_ENABLED=false` in server environment and restart or drain | Server returns `live_disabled` on next preflight call |
| 2 | Revoke the `ApprovalRecord` in `LocalFileApprovalStore` using `revoke_approval()` | `is_approval_valid()` returns `False` |
| 3 | If credential exposure or misuse is suspected: mark credential `REVOKED` via `POST /credentials/google-ads/revoke` or equivalent | `GET /credentials/google-ads/status` returns `status=revoked` |
| 4 | If full removal is required: call `DELETE /credentials/google-ads` (requires `OPENCLAW_ADMIN_DELETE_ENABLED=true`) | `GET /credentials/google-ads/status` returns `credential_not_found` |
| 5 | Confirm `check_live_gate()` now denies live use | `check_live_gate()` returns `allowed=false` |
| 6 | Run `smoke_test_v5_credentials.sh` — confirm suite passes | 28/28 PASS |
| 7 | Run safety grep on all changed files | No sensitive hits |
| 8 | Run `verify_audit_file()` on all audit files produced during window | `ok=true` on all files |
| 9 | Confirm GCP Secret Manager state out-of-band (operator, terminal, no screen recording) | Secret disabled or destroyed as required |
| 10 | Archive audit log to operator-controlled storage outside repo | Operator confirms |
| 11 | Document final state: timestamp, operator name, trigger, all steps taken, final credential status | Written record stored outside repo |

---

## J. Evidence Package

The following evidence must be assembled and stored at an operator-controlled path outside the repository before the live validation window is considered closed.

**Required evidence:**

| Item | Source |
|---|---|
| Sanitized `ApprovalRecord` (no secrets) | `sanitize_approval_record()` output |
| `validate_onboarding_ceremony()` PASS result | Demo output or inline check |
| `validate_credential_intake_dry_run()` PASS result | Demo output or inline check |
| Server preflight PASS result | Preflight route response |
| `check_live_gate()` PASS result | Gate check result |
| Exact approved operation name | From approval record |
| Authorized time window | From approval record |
| Redacted live result summary (ok/error, HTTP status only) | Operator-redacted |
| `GOOGLE_ADS_LIVE_ENABLED=false` confirmation post-window | Operator written record |
| Rollback readiness confirmation | Pre-execution checklist |
| Smoke test result (28/28) | `smoke_test_v5_credentials.sh` output |
| Safety grep result (clean) | Grep output |
| `verify_audit_file()` result (ok=true on all files) | `audit_maintenance.verify_audit_file()` |

**Forbidden evidence fields** — must not appear in any evidence file stored inside or outside the repo:

| Forbidden |
|---|
| Real customer IDs |
| Real login customer IDs |
| Raw `credential_ref` values |
| GCP Secret Manager resource paths |
| GCP project IDs or project numbers |
| Account emails |
| Raw API response payload |
| Tokens, client secrets, refresh tokens, access tokens, developer tokens |

---

## K. Operator Authorization Template

The following template must be completed and signed by a named operator before any live validation window opens. This template does **not** constitute authorization — it is a structural template only.

A completed, signed record must be stored in `LocalFileApprovalStore` at an operator-controlled path outside the repository, and must pass `validate_approval_record()` before any gate will allow live execution.

---

> "I explicitly authorize one controlled read-only Google Ads live validation for **\<redacted tenant/client\>** during **\<approved time window\>**, using V5.19/V5.20 gates, a valid and signed `ApprovalRecord`, audit enabled, rollback plan documented and present in `ApprovalRecord.evidence`, emergency revoke path available and tested, no mutation operations, and `GOOGLE_ADS_LIVE_ENABLED=true` set only for the authorized execution window.
>
> I understand this authorization is limited to **one read-only validation attempt** (plus at most one authorized retry) and does not authorize campaign management, production usage, multi-client validation, or any write/mutate operation.
>
> Operator: **\<redacted/operator-label\>**
> Date: **\<ISO 8601 UTC\>**
> Scope: `GOOGLE_ADS_LIVE_VALIDATION`
> Tenant/Client: **\<redacted\>**
> Expires: **\<ISO 8601 UTC\>**"

---

This template is **not an executed approval**. A completed, signed authorization must be stored outside the repository in `LocalFileApprovalStore` and must pass `validate_approval_record()`.

---

## L. Phase 5 Conclusion

This document concludes V5.20 Phase 5.

| Item | Status |
|---|---|
| First live API validation plan created | **Complete** — `docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md` |
| Real execution performed | **No** — this is documentation only |
| Real credentials used | **No** — no real credential values in this document |
| OAuth consent flow executed | **No** — Phase 5 does not execute OAuth |
| Google Ads API called | **No** — no API call made in Phase 5 |
| GCP commands run | **No** — no `gcloud` or GCP API calls in Phase 5 |
| `GOOGLE_ADS_LIVE_ENABLED=true` set | **No** — flag remains `false` |
| Deploy, IAM, API, or billing changes | **No** — no infrastructure or configuration changes |
| Next phase | Phase 6 — Rollback/emergency revoke drill (`openclaw/run_revoke_drill_demo.py`) |

---

## M. Phase 6 Prerequisite — Rollback Drill

The rollback and emergency revoke drill (`openclaw/rollback_drill.py`, `validate_rollback_drill()`) must return `ok=True` (PASS) before any future live validation window may open.

| Drill prerequisite | Gate |
|---|---|
| Live flag confirmed disabled post-window | `live_flag_disabled=True` |
| Approval record confirmed revoked | `approval_revoked=True` |
| Credential marked REVOKED | `credential_marked_revoked=True` |
| Credential bundle deleted or revoked | `credential_bundle_deleted_or_revoked=True` |
| Post-revoke status verified | `post_revoke_status_verified=True` |
| Secret state verified out-of-band | `secret_status_verified=True` |
| Live gate denies after revocation | `live_gate_denied_after_revoke=True` |
| Smoke tests pass post-drill | `smoke_tests_passed=True` |
| Safety grep clean post-drill | `safety_grep_clean=True` |
| Audit chain verified | `audit_chain_verified=True` |
| Final state documented | `final_state_documented=True` |

The drill is fake/local only. It does not revoke real credentials, call Secret Manager, or call the Google Ads API. No execution is authorized by this document.

---

## N. Phase 7 Prerequisite — Version Lifecycle Policy

If any credential rotation or new credential onboarding occurs before or during the first live validation window, the Secret Manager version lifecycle policy decision must be validated before the rotation proceeds.

| Prerequisite | Gate |
|---|---|
| Lifecycle mode decided | `lifecycle_mode = DISABLE_PREVIOUS_WITH_GRACE_PERIOD` |
| Grace period defined | `grace_period_hours` is a positive integer ≤ 168 |
| Prior version disable confirmed | `disable_previous_version_required=True` |
| Destroy separately authorized | `destroy_previous_requires_separate_approval=True` |
| Rollback window documented | `rollback_window_present=True` |
| Audit enabled | `audit_requirement_present=True` |
| Evidence documented | `evidence_requirement_present=True` |
| Operator confirmation obtained | `operator_confirmation_present=True` |
| Validator PASS | `validate_secret_version_policy()` returns `ok=True` |

**Important constraints:**
- No Secret Manager version disable or destroy operation is authorized by this plan.
- `validate_secret_version_policy()` is a local-only check; it does not call Secret Manager.
- A PASS result from the validator does not authorize any version lifecycle operation — a separate named-operator approval and execution authorization is required.
- If no rotation occurs before or during the first live validation window, this prerequisite does not gate the validation window.

---

## Related Documents

- [V5.20 Implementation Plan](V5_20_IMPLEMENTATION_PLAN.md)
- [Google Ads Real Onboarding Checklist](GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md)
- [Credential Lifecycle Runbook](CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [V5.19 Branch Closure](V5_19_BRANCH_CLOSURE.md)
- [Roadmap](ROADMAP.md)

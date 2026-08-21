# Google Ads Real Onboarding Checklist — V5.20

**Kaiju Command Center — V5.20 Phase 2**

**Branch:** `v5.20-controlled-real-google-ads-onboarding-readiness`

---

> **WARNING — READ BEFORE USING THIS DOCUMENT**
>
> - This checklist is **not** an approval to use real credentials.
> - **Do not paste credentials into chat** (Claude, ChatGPT, Slack, GitHub, or any observed session).
> - **Do not commit credentials** to this repository or any tracked file.
> - **Do not print credentials** to any terminal with screen recording or shared access.
> - **Do not store credentials in docs.** No token values, refresh tokens, client secrets, or developer tokens belong in any `.md` file.
> - **Do not call the Google Ads API** until a separate explicit operator approval is recorded, signed, and not expired.
> - **`GOOGLE_ADS_LIVE_ENABLED` must remain `false`** until final separately authorized execution. Setting it to `true` without a completed, signed approval is a protocol violation.
> - **Any real onboarding must stop immediately** if secret leakage, unexpected API behavior, or missing rollback evidence is detected.

---

## A. Readiness State

Verify all items before proceeding to the approval ceremony. All items must be checked by the authorizing operator.

| # | Item | Verified |
|---|---|---|
| A1 | V5.19.0-beta shipped and tagged on master | [ ] |
| A2 | V5.20 Phase 1 plan (`docs/V5_20_IMPLEMENTATION_PLAN.md`) reviewed by operator | [ ] |
| A3 | V5.19 live gate (`check_live_gate()`) available and imported correctly | [ ] |
| A4 | `ApprovalRecord` model and `LocalFileApprovalStore` available and functional | [ ] |
| A5 | `check_live_operation_preflight()` available and functional | [ ] |
| A6 | Server preflight route (`POST /openclaw/admin/live-google-ads/preflight`) registered | [ ] |
| A7 | Credential lifecycle audit events (`build_credential_audit_event()`, `verify_audit_file()`) available | [ ] |
| A8 | `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` reviewed by operator | [ ] |
| A9 | `docs/GCP_SECRET_MANAGER_RUNBOOK.md` reviewed by operator | [ ] |
| A10 | `scripts/smoke_test_v5_credentials.sh` passing — 26/26 PASS | [ ] |
| A11 | `scripts/smoke_test_v5_12_gcp_secret_manager.sh` passing — 8/8 PASS | [ ] |
| A12 | No outstanding uncommitted code changes on active branch | [ ] |
| A13 | Operator confirms that real Google Ads API execution remains deferred and unauthorized until a separate explicit approval is recorded | [ ] |

**Readiness state result:** [ ] PASS — proceed to Section B  /  [ ] BLOCKED — do not proceed

---

## B. Operator Approval Ceremony

The approval ceremony must be completed by a named operator before any credential intake, OAuth flow, or live API call. The resulting `ApprovalRecord` must be stored in `LocalFileApprovalStore` at an operator-specified path **outside the repository**. The approval record must **not** be committed.

### B.1 Approval Record Fields

Fill all fields using placeholders only in this document. Real values go only into the `ApprovalRecord` object stored locally.

| Field | Placeholder |
|---|---|
| `operator_label` | `<redacted/operator-label>` |
| `tenant_id` | `<redacted-tenant>` |
| `client_id` | `<redacted-client>` |
| `integration_type` | `google_ads` |
| `intended_operation` | `<credential_onboarding \| live_validation \| rotation \| revoke>` |
| `approval_scope` | `<scope — e.g. read-only validation for single tenant/client>` |
| `risk_acknowledgement` | `<summary only — no credential values>` |
| `rollback_plan_present` | `yes / no` |
| `emergency_revoke_plan_present` | `yes / no` |
| `evidence_location` | `<redacted-local-path-or-ticket-id>` |
| `approved_at` | `<ISO 8601 UTC timestamp>` |
| `expires_at` | `<ISO 8601 UTC timestamp>` |
| `approval_status` | `APPROVED` |

### B.2 Approval Record Invariants

| # | Rule | Verified |
|---|---|---|
| B1 | Approval record **must not** contain any secret, token, or credential value | [ ] |
| B2 | Approval record **must not** contain customer IDs or login customer IDs | [ ] |
| B3 | Approval record **must not** contain GCP project IDs or project numbers | [ ] |
| B4 | Approval record **must not** contain raw Secret Manager resource paths | [ ] |
| B5 | Approval record **must not** contain any email addresses | [ ] |
| B6 | Approval must be scoped to a single tenant and client | [ ] |
| B7 | Approval must have a valid `expires_at` timestamp in the future | [ ] |
| B8 | Approval must be revocable — `ApprovalStore.revoke_approval()` path confirmed available | [ ] |
| B9 | Approval record path is **not** committed, logged, or printed | [ ] |
| B10 | `validate_approval_record()` passes on the completed record | [ ] |

**Approval ceremony result:** [ ] COMPLETE  /  [ ] INCOMPLETE — do not proceed

---

## C. Credential Intake Boundary

This section defines the exact boundary for how real credential intake must occur. **No intake is executed in Phase 2.** This is a checklist for when intake is separately authorized.

| # | Rule | Verified |
|---|---|---|
| C1 | Real credential transfer path approved outside any chat interface | [ ] |
| C2 | No credential values enter Claude, ChatGPT, or any AI assistant prompt | [ ] |
| C3 | No credential values written to this repository (tracked or untracked) | [ ] |
| C4 | No credential values written to any doc file | [ ] |
| C5 | No credential values printed to any terminal with screen recording or shared access | [ ] |
| C6 | No credential values stored in shell history (use `set +o history` or equivalent before intake) | [ ] |
| C7 | No `.env` file created inside the repository | [ ] |
| C8 | No service account JSON key file committed or staged | [ ] |
| C9 | Immediate write to the approved secret backend (GCP Secret Manager) is planned and confirmed | [ ] |
| C10 | Local temporary credential material handling is documented in `ApprovalRecord.evidence` | [ ] |
| C11 | Cleanup of all local temporary credential material after Secret Manager write is documented | [ ] |
| C12 | Redaction grep is planned and will be run after intake completes — checking for OAuth token prefixes, API key prefixes, and credential file path patterns in all changed docs and source files | [ ] |

**Credential intake boundary result:** [ ] CONFIRMED  /  [ ] INCOMPLETE — do not proceed

---

## D. OAuth Onboarding Boundary

This section documents the planned OAuth flow boundaries. **Phase 2 does not execute OAuth.** This is design-only documentation of what future authorized execution must follow.

| Step | Description | Authorized by |
|---|---|---|
| D1 — Consent initiation | Operator opens OAuth consent URL in a browser on a controlled workstation; not via Claude Code or any AI assistant | Future separate approval |
| D2 — Token exchange | Handled by Google OAuth infrastructure; result is a refresh token | Future separate approval |
| D3 — Refresh token capture | Operator receives refresh token in browser redirect or out-of-band channel; never via Claude Code | Future separate approval |
| D4 — Immediate Secret Manager write | Operator writes refresh token to GCP Secret Manager directly using `gcloud` or GCP Console; not via Claude Code | Future separate approval |
| D5 — Local temporary cleanup | All local copies of the refresh token removed immediately after Secret Manager write; shell history cleared | Future separate approval |
| D6 — Status metadata update | `CredentialReference` metadata updated via `POST /credentials/google-ads` (metadata-only payload) | Future separate approval |
| D7 — Validation preflight | `POST /credentials/google-ads/validate` confirms `structurally_complete: true`, `live_api_tested: false` | Future separate approval |
| D8 — Revoke path | If OAuth revoke is needed, operator follows `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` Section 18 | Future separate approval |

> **Phase 2 conclusion on OAuth:** No OAuth consent flow is initiated, no token exchange is performed, no refresh token is captured, and no secret backend write is triggered in this phase. All steps above are design documentation only.

---

## E. Preflight Checklist Before First Live API Call

All items below must be verified before `GOOGLE_ADS_LIVE_ENABLED` is set to `true` in any environment. Setting the flag before all items are checked is a protocol violation.

| # | Item | Verified |
|---|---|---|
| E1 | Valid `ApprovalRecord` exists in `LocalFileApprovalStore` (not expired, not revoked) | [ ] |
| E2 | `approval_status` is exactly `APPROVED` | [ ] |
| E3 | `approval_scope` matches the intended operation | [ ] |
| E4 | `tenant_id` and `client_id` in the approval record match the target tenant and client | [ ] |
| E5 | `expires_at` is in the future at the time of the first call | [ ] |
| E6 | `OPENCLAW_AUDIT_ENABLED=true` confirmed in server environment | [ ] |
| E7 | Rollback plan is present and documented in `ApprovalRecord.evidence` | [ ] |
| E8 | Named-operator confirmation of rollback plan is present | [ ] |
| E9 | Credential `status` is exactly `ACTIVE` in `CredentialReference` store | [ ] |
| E10 | Tenant and client are in the allowed set (`check_live_gate()` condition 6 passes) | [ ] |
| E11 | Client is in the allowed set (`check_live_gate()` condition 7 passes) | [ ] |
| E12 | Server preflight route (`POST /openclaw/admin/live-google-ads/preflight`) returns `allowed: true` for this tenant/client | [ ] |
| E13 | Live gate (`check_live_gate()`) returns `allowed: true` with the real approval record | [ ] |
| E14 | `live_api_tested: false` confirmed before the first live call (`/validate` endpoint result) | [ ] |
| E15 | Logs redaction spot-checked: no real values in server stdout, request/response logs, or audit JSONL | [ ] |
| E16 | Emergency revoke path tested with fake-only credential flow (Section G below) | [ ] |
| E17 | Final named-operator authorization obtained for the first API call (separate from onboarding approval) | [ ] |

**Preflight result:** [ ] ALL PASS — may proceed to first live call (with separately authorized `GOOGLE_ADS_LIVE_ENABLED=true`)  /  [ ] BLOCKED

---

## F. First Live API Validation Constraints

This section documents the constraints that apply to the first real Google Ads API call. **No execution occurs in Phase 2.** These constraints must be honored at the time of separately authorized execution.

| Constraint | Requirement |
|---|---|
| Endpoint | Read-only endpoint only (e.g. `CustomerService.listAccessibleCustomers` or equivalent minimal read) |
| OAuth scope | Minimal scope required for the read operation only |
| Target | Single tenant, single client, single operator-approved time window — no batch |
| No mutations | No campaign, ad group, ad, keyword, budget, or bidding write operations |
| No bulk operations | No batch API calls; no background jobs |
| No retries | No automatic retries beyond the approved limit (operator must specify limit in approval record) |
| No raw response committed | Raw API response payload must not be committed to the repo |
| Response redaction | Only structural metadata (ok/error, HTTP status code) logged; no account data logged |
| Audit events (before) | `op=live_gate_check` audit event emitted before the first call | 
| Audit events (after) | `op=live_preflight_allowed` or `op=live_mode_denied` audit event emitted after the first call |
| Rollback trigger | Any unexpected error code, HTTP 5xx, or field from `LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS` triggers immediate rollback |
| Post-call audit verification | `verify_audit_file()` run immediately after the first call |
| Immediate stop | Operator must be present and ready to disable live mode instantly if any anomaly appears |

---

## G. Rollback and Emergency Revoke Checklist

This sequence must be documented in the approval record and rehearsed with a fake credential before the first real call. Steps must be executable in order without additional authorization.

| Step | Action | Verified |
|---|---|---|
| G1 | Confirm `GOOGLE_ADS_LIVE_ENABLED=false` in server environment, or disable it and restart/drain | [ ] |
| G2 | Revoke the `ApprovalRecord` via `ApprovalStore.revoke_approval()` | [ ] |
| G3 | Mark credential `status=REVOKED` via `DELETE /credentials/google-ads` (or `revoke_google_ads_credentials()` directly) | [ ] |
| G4 | Delete credential bundle through approved lifecycle path (`DELETE /credentials/google-ads` with `OPENCLAW_ADMIN_DELETE_ENABLED=true`) | [ ] |
| G5 | Verify post-delete credential status returns `credential_not_found` via `GET /credentials/google-ads/status` | [ ] |
| G6 | Verify GCP Secret Manager secret status out-of-band (operator-run only; no Claude Code GCP commands) | [ ] |
| G7 | Run `verify_audit_file()` on all audit files; confirm seq/digest chain is intact | [ ] |
| G8 | Run safety grep: `grep -R "ya29\." -n docs/ openclaw/audit/` (or equivalent redaction check) | [ ] |
| G9 | Document final state: timestamp, operator name, trigger, steps taken, audit event count | [ ] |
| G10 | Do not resume or re-authorize without a new `ApprovalRecord` and a new explicit operator sign-off | [ ] |

**Rollback drill result (rehearsal with fake credential):** [ ] COMPLETE  /  [ ] NOT YET RUN

---

## H. Audit Evidence Checklist

All evidence items below are required before any future real credential activation is considered closed. Evidence must be sanitized — no secrets, no raw resource paths, no customer IDs.

| # | Required Evidence | Present |
|---|---|---|
| H1 | Sanitized `ApprovalRecord` summary (output of `sanitize_approval_record()`) — no secrets | [ ] |
| H2 | Preflight result (`check_live_operation_preflight()` output) | [ ] |
| H3 | Live gate result (`check_live_gate()` output with `allowed: true`) | [ ] |
| H4 | Audit file verification result (`verify_audit_file()` output) | [ ] |
| H5 | Smoke test result (`smoke_test_v5_credentials.sh` — 26/26 PASS) | [ ] |
| H6 | Rollback/revoke dry-run result (fake credential revoke sequence completed) | [ ] |
| H7 | Safety grep result — CLEAN on all changed docs and source files | [ ] |
| H8 | Final operator sign-off (named operator, timestamp, scope of authorization) | [ ] |
| H9 | Confirmation: no secrets in any evidence item | [ ] |
| H10 | Confirmation: no raw Secret Manager resource paths in any evidence item | [ ] |
| H11 | Confirmation: no customer IDs in any evidence item | [ ] |

**Audit evidence result:** [ ] COMPLETE  /  [ ] INCOMPLETE

---

## I. Secret Manager Version Lifecycle Decision

A policy decision is required before real credentials are written to GCP Secret Manager. The current implementation retains all versions after rotation. This must be resolved before any real credential write.

| # | Item | Status |
|---|---|---|
| I1 | Current operative policy documented: prior GCP Secret Manager versions remain enabled after rotation (no automatic disable or destroy) | Documented |
| I2 | Prior version handling reviewed against `docs/GCP_SECRET_MANAGER_RUNBOOK.md` Section 13 | [ ] |
| I3 | Policy decision recorded — choose one: | [ ] |
| | Option A: Destroy prior version immediately after rotation (irreversible; requires separate authorization) | [ ] Accepted / [ ] Deferred |
| | Option B: Disable prior version immediately; destroy after defined grace period (preferred design; requires implementation in V5.20 Phase 7) | [ ] Accepted / [ ] Deferred |
| I4 | Destructive destroy **not** performed unless separately approved (distinct from onboarding approval) | [ ] Confirmed |
| I5 | Rotation path documented in `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` | Documented |
| I6 | Revoke/delete path documented in `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` | Documented |
| I7 | Version lifecycle implementation status: **pending (V5.20 Phase 7 deliverable)** | Pending |

---

## J. Stop Conditions

Immediately stop all onboarding or validation activity if any of the following are detected. Document the stop condition and do not resume without a new approval.

| # | Condition |
|---|---|
| J1 | Any credential value appears in terminal output |
| J2 | Any credential value appears in any doc file |
| J3 | Any credential value appears in `git diff` or `git status` output |
| J4 | Any customer ID appears in committed docs |
| J5 | Any raw GCP Secret Manager resource path appears in committed docs |
| J6 | Approval record is missing, expired, or revoked |
| J7 | Preflight check denied (`check_live_operation_preflight()` returns `allowed: false`) |
| J8 | Live gate denied (`check_live_gate()` returns `allowed: false`) |
| J9 | Audit is disabled (`OPENCLAW_AUDIT_ENABLED` is not `true`) |
| J10 | Rollback plan is missing or not documented in `ApprovalRecord.evidence` |
| J11 | Smoke tests fail (any test from `smoke_test_v5_credentials.sh` or `smoke_test_v5_12_gcp_secret_manager.sh`) |
| J12 | Unexpected Google Ads API permission error or unexpected response field appears |
| J13 | Operator approval is ambiguous, unsigned, or covers a broader scope than the specific operation |

**If a stop condition is triggered:** disable live mode immediately, execute Section G (Rollback), document the incident, and obtain new authorization before any retry.

---

## K. Final Authorization Statement Template

The following template must be completed and signed by a named operator before any real credential intake or live API call is authorized. This document does not constitute that authorization — it is only a template.

---

> "I explicitly authorize a controlled real Google Ads **\<operation\>** for **\<redacted tenant/client\>** during **\<time window\>**, using the V5.20 checklist, V5.19 gates, a valid and signed `ApprovalRecord`, audit enabled, rollback plan documented and rehearsed, and `GOOGLE_ADS_LIVE_ENABLED=true` set only for the authorized execution window.
>
> Operator: **\<redacted/operator-label\>**
> Date: **\<ISO 8601 UTC\>**
> Scope: **\<specific scope\>**
> Expires: **\<ISO 8601 UTC\>**"

---

This template is **not an executed approval**. A completed, signed authorization must be stored outside the repository in `LocalFileApprovalStore` and must pass `validate_approval_record()`.

---

## M. Phase 4 — Credential Intake Dry-Run Validator

`openclaw/credential_intake.py` (`validate_credential_intake_dry_run()`) enforces the intake boundary rules defined in Section C of this checklist. It is a pure local validator with no network calls, no GCP access, and no real credential handling.

| Boundary rule | Enforced by |
|---|---|
| No credentials via chat or Claude Code | `transfer_path_forbidden_confirmed` check |
| No real credential values in input | `credential_values_absent` check |
| `GOOGLE_ADS_LIVE_ENABLED=false` throughout | `live_flag_false_confirmed` check |
| GCP write is operator-only | `gcp_write_operator_only_confirmed` check |
| Screen recording prohibited during entry | `screen_recording_prohibited_confirmed` check |
| No credential committed to repo | `repo_commit_prohibited_confirmed` check |
| Immediate redaction check after write | `immediate_redaction_confirmed` check |
| Rollback plan documented | `rollback_plan_present` check |
| Emergency revoke plan documented | `emergency_revoke_plan_present` check |
| Operator confirmation obtained | `operator_confirmation_present` check |
| Audit enabled | `audit_enabled` check |
| Checklist reference present | `checklist_reference_present` check |
| Intake boundary doc accepted | `intake_boundary_doc_confirmed` check |
| Operator identity recorded | `operator_identity_present` check |
| Approval ceremony completed | `approval_ceremony_reference_present` check |
| Hard stop: real secret material | `real_secret_material_present` detection |
| Hard stop: OAuth execution | `oauth_execution_detected` detection |
| Hard stop: Google Ads API call | `google_ads_api_call_detected` detection |
| Hard stop: GCP command | `gcp_command_detected` detection |
| Hard stop: filesystem write | `filesystem_write_detected` detection |
| Hard stop: network call | `network_call_detected` detection |
| Forbidden fields in evidence/metadata | `_FORBIDDEN_FIELD_NAMES` check (18 names) |
| Forbidden values in evidence/metadata | `_FORBIDDEN_VALUE_PATTERNS` check (10 patterns) |

The validator returns `ok=True` (PASS) only when all 25 conditions are satisfied. `GOOGLE_ADS_LIVE_ENABLED` must remain `false` throughout. No real credential intake is executed in V5.20.

---

## N. Phase 5 — First Live API Validation Plan

`docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md` defines the controlled first live Google Ads API validation procedure for a future separately authorized phase. It is documentation only — no execution, no real credentials, no API calls.

| Plan section | Validates |
|---|---|
| Section B (Preconditions) | 19 items including: V5.19 shipped, checklist complete, ceremony PASS, intake PASS, approval record valid, audit enabled, rollback documented, live gate PASS, smoke tests PASS |
| Section C (Non-goals) | No mutations, no bulk ops, no multi-client validation, no persistent live mode |
| Section D (Candidate call) | Read-only accessible-customers style check; no campaign, budget, keyword, or conversion data |
| Section E (Execution window) | Single tenant/client/operator/credential/call; no background or scheduled execution |
| Section F (Runtime flags) | `GOOGLE_ADS_LIVE_ENABLED=false` pre/post window; must be reverted immediately after validation |
| Section G (Audit sequence) | 10 steps: approval created → ceremony PASS → intake PASS → preflight → live gate → window opens → call → flag disabled → status confirmed → audit verified |
| Section H (Stop conditions) | 17 items: approval issues, validator failures, gate denials, secret leakage, unexpected scopes, mutations, unrevertable live flag |
| Section I (Rollback sequence) | 11 ordered steps: disable flag → revoke approval → revoke credential → delete bundle → verify gate → smoke tests → safety grep → audit chain → GCP out-of-band → archive → document |
| Section J (Evidence package) | Required: sanitized approval, ceremony/intake/preflight/gate PASS, operation name, time window, redacted result, flag disabled confirmation, smoke, grep, audit; Forbidden: real IDs, tokens, raw payloads |
| Section K (Authorization template) | Structural template only — not an executed approval |

The plan does **not** authorize execution. Any future live validation requires a separate explicit named-operator approval in `LocalFileApprovalStore`, not expired, passing `validate_approval_record()`.

---

## O. Phase 6 — Rollback and Emergency Revoke Drill Validator

`openclaw/rollback_drill.py` (`validate_rollback_drill()`) models and validates a fake/local rollback and emergency revoke drill. It confirms that the full rollback sequence can be rehearsed before any future real Google Ads live validation window opens.

Key properties:
- Pure local validator; no network calls, no GCP access, no Secret Manager calls, no real credentials.
- Validates 11 rollback step confirmations (live flag disabled, approval revoked, credential revoked, bundle deleted, status verified, secret state verified, live gate denied, smoke tests passed, safety grep clean, audit chain verified, final state documented).
- Hard-stops if real credentials are present, Google Ads API was called, GCP commands were used, Secret Manager was called, OAuth was executed, network calls were detected, or filesystem writes occurred.
- Forbidden field/value detection in evidence and metadata (19 forbidden field names; 12 forbidden value patterns).
- Sanitized summary excludes evidence, metadata, and all raw credential values.
- Returns `ok=True` (PASS) only when all 18 conditions are satisfied.

This validator does **not** revoke real credentials. It does **not** call Secret Manager. It does **not** call the Google Ads API. A PASS result from this drill is a prerequisite before any future real live validation execution.

---

## L. Phase 2 Conclusion

This document concludes V5.20 Phase 2.

| Item | Status |
|---|---|
| Checklist document created | **Complete** — `docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md` |
| Real onboarding executed | **No** — this is documentation only |
| Real credentials used | **No** — no real credential values in this document |
| OAuth consent flow executed | **No** — Phase 2 does not execute OAuth |
| Google Ads API called | **No** — no API call made in Phase 2 |
| GCP commands run | **No** — no `gcloud` or GCP API calls in Phase 2 |
| `GOOGLE_ADS_LIVE_ENABLED=true` set | **No** — flag remains `false` |
| Deploy, IAM, API, or billing changes | **No** — no infrastructure or configuration changes |
| Next phase | Phase 3 — Onboarding approval ceremony model (`openclaw/onboarding_ceremony.py`) |

---

## Related Documents

- [V5.20 Implementation Plan](V5_20_IMPLEMENTATION_PLAN.md)
- [Credential Lifecycle Runbook](CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [V5.19 Branch Closure](V5_19_BRANCH_CLOSURE.md)
- [v5.19.0-beta Release Notes](RELEASE_NOTES_V5_19_0_BETA.md)
- [Roadmap](ROADMAP.md)

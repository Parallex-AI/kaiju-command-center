# V5.20 Implementation Plan — Controlled Real Google Ads Onboarding Readiness

**Branch:** `v5.20-controlled-real-google-ads-onboarding-readiness`
**Base:** `v5.19.0-beta` / master at `631abbd`
**Status:** Phase 1 — Planning

---

## Purpose

V5.20 defines the final operator-controlled readiness process required before any real Google Ads credential onboarding or live API validation can occur. It does not perform real credential intake, does not execute OAuth flows, does not call the Google Ads API, and does not set `GOOGLE_ADS_LIVE_ENABLED=true` at runtime.

V5.20 builds on the readiness gate infrastructure from V5.19 (live gate, approval records, preflight checker, server guard, audit events, runbooks) by establishing the ceremony, checklist, intake boundary design, first-call plan, and rollback drill required to safely execute real onboarding in a future authorized milestone.

---

## Starting Point

| Milestone | What was delivered |
|---|---|
| V5.18 | Fake live GCP Secret Manager credential lifecycle confirmed (write → validate → rotate → delete → audit) |
| V5.19 | `check_live_gate()` (11 conditions); `ApprovalRecord` + `LocalFileApprovalStore`; `check_live_operation_preflight()`; server preflight route; two-event audit model; runbooks; hardened tests |

Real Google Ads credentials and live API validation remain explicitly deferred. `GOOGLE_ADS_LIVE_ENABLED` remains `false` by default. No real credentials have ever been used or committed.

---

## Non-Goals for Phase 1 (and for V5.20 overall unless separately authorized)

- No real credentials
- No Google Ads API calls
- No `GOOGLE_ADS_LIVE_ENABLED=true` at runtime
- No OAuth consent flow execution
- No GCP commands
- No GCP API enablement
- No IAM changes
- No billing changes
- No production deployment
- No production onboarding of any tenant or client
- No cloud resource creation

---

## Design Areas

### A. Real Onboarding Approval Ceremony

Define a formal, documented operator ceremony that must be completed before real credentials are accepted into the system. The ceremony produces a signed `ApprovalRecord` (using the V5.19 model) and a completed checklist before any credential intake begins.

Required ceremony elements:

| Field | Description |
|---|---|
| Named operator | Full name of the authorizing operator; not a team name |
| Tenant scope | Exact `tenant_id` being onboarded |
| Client scope | Exact `client_id` being onboarded |
| Integration type | `google_ads` only for V5.20 scope |
| Intended operation | Description of the first authorized operation (e.g. read-only API validation) |
| Risk acknowledgement | Explicit operator acknowledgement that real credentials are entering the system |
| Rollback plan | Named operator, exact steps, and estimated time to full credential revocation |
| Emergency revoke plan | Documented emergency path if anomalous behavior is observed during first API call |
| Evidence checklist | All items in Section D completed and verified |
| Timestamp | ISO 8601 UTC |
| Approval record stored | In `LocalFileApprovalStore` at an operator-specified path outside the repo |

Invariants:
- No secrets in the `ApprovalRecord` (enforced by V5.19 `validate_approval_record()`)
- Approval record must not be committed to the repo
- Approval record path must not be logged or printed

---

### B. Credential Intake Boundary

Define the exact boundary for how real credential intake must happen in a future authorized milestone. No intake is executed in V5.20.

Design principles:

| Principle | Detail |
|---|---|
| Never via chat | Real credential values must never be typed, pasted, or transmitted through Claude Code, any chat interface, or any log sink |
| Never committed to repo | No `.env`, no JSON file, no Python literal, no YAML — no real credential value may appear in any tracked file |
| Never written to docs | No reference to actual token values, client IDs, developer tokens, or secret names in any documentation file |
| Never printed in logs | Server startup, request handling, and audit event paths must not emit any real credential value or Secret Manager resource path |
| Approved intake path | Operator writes credential values directly to GCP Secret Manager using `gcloud` (or GCP Console) on a terminal with no screen recording. Claude Code does not participate in the write |
| Immediate redaction check | After any credential write, operator verifies that the value does not appear in any log, audit file, or git-tracked file |
| No raw persistence outside Secret Manager | After the GCP Secret Manager write, the raw value must not be stored anywhere else — not in a local file, not in memory-mapped storage, not in a shell history |

---

### C. OAuth Onboarding Readiness

Document the future OAuth flow boundaries. No OAuth execution occurs in V5.20.

| Boundary | Design |
|---|---|
| Consent initiation | Operator opens consent URL in a browser on a controlled workstation; not via Claude Code |
| Token exchange | Handled by Google OAuth infrastructure; result is a refresh token |
| Refresh token capture | Operator receives refresh token in browser redirect or out-of-band; never via Claude Code |
| Secret Manager write | Operator writes refresh token to Secret Manager directly; not via Claude Code |
| Failure handling | If consent fails, no credential record is written; existing `credential_status=CONFIGURED` path applies |
| Revoke handling | If OAuth revoke is needed, operator follows `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` Section 18 |
| V5.20 constraint | All of the above is design-only; no execution in V5.20 |

---

### D. Preflight Checklist Before First Real API Call

All items below must be verified by the operator before `GOOGLE_ADS_LIVE_ENABLED` is set to `true` in any environment. This checklist will be formalized as `docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md` in Phase 2.

| # | Item | Verified by |
|---|---|---|
| 1 | V5.19 live gate installed and smoke-tested (26/26 PASS) | Smoke suite |
| 2 | Approval record created, valid, and loaded in `LocalFileApprovalStore` | `validate_approval_record()` |
| 3 | `check_live_gate()` returns `allowed=True` with real approval record | `check_live_operation_preflight()` |
| 4 | Audit enabled and `verify_audit_file()` passes on empty audit log | `verify_audit_file()` |
| 5 | Rollback plan documented with named operator and time estimate | In `ApprovalRecord.evidence` |
| 6 | Emergency revoke plan documented and reviewed | In `ApprovalRecord.evidence` |
| 7 | Credential status is exactly `ACTIVE` in credential store | `get_credential_status()` |
| 8 | Tenant and client in allowed set | `check_live_gate()` condition |
| 9 | Server preflight route returns `allowed=True` for this tenant/client | `POST /openclaw/admin/live-google-ads/preflight` |
| 10 | Delete/revoke path tested with fake credential before first real call | `DELETE /credentials/google-ads` dry run |
| 11 | Logs redaction spot-checked: no real values in server stdout or audit JSONL | Operator manual check |
| 12 | `GOOGLE_ADS_LIVE_ENABLED` still `false` until all above complete | Environment check |
| 13 | Final named-operator approval for first API call, separate from onboarding approval | Written sign-off |

---

### E. Live API Validation Boundary

Define the constraints for the first real Google Ads API call. No execution in V5.20.

| Constraint | Detail |
|---|---|
| Endpoint | Read-only endpoint only (e.g. `CustomerService.listAccessibleCustomers` or equivalent minimal read) |
| Scope | Minimal OAuth scope required for the read |
| Target | Single tenant, single client, single operator-approved time window |
| No mutations | No campaign, ad group, ad, keyword, or budget write operations |
| No bulk operations | No batch API calls |
| Request redaction | Operator verifies request payload contains no raw credential values before sending |
| Response handling | Response must not be printed in full to any log; only structural metadata (ok/error, HTTP status) logged |
| Audit events | Two audit events emitted via `build_live_guard_audit_event()`: one before (`live_gate_check`) and one after (`live_preflight_allowed` or `live_mode_denied`) |
| Rollback trigger | Any unexpected error code, any HTTP 5xx, or any response containing a field from `LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS` triggers immediate rollback |
| Post-call verification | Operator verifies audit chain with `verify_audit_file()` immediately after first call |

---

### F. Rollback and Emergency Revoke Sequence

Define the exact ordered steps for full credential revocation after a live call. This sequence must be documented in the checklist and rehearsed with a fake credential before first real use.

| Step | Action |
|---|---|
| 1 | Set `GOOGLE_ADS_LIVE_ENABLED=false` in the server environment and restart (or drain) |
| 2 | Call `POST /credentials/google-ads/revoke` or equivalent to mark credential `REVOKED` |
| 3 | Verify credential status returns `REVOKED` via `GET /credentials/google-ads/status` |
| 4 | Call `DELETE /credentials/google-ads` (requires `OPENCLAW_ADMIN_DELETE_ENABLED=true`) to delete GCP Secret Manager bundle |
| 5 | Verify `GET /credentials/google-ads/status` returns `credential_not_found` |
| 6 | Check GCP Secret Manager (operator, out-of-band) to confirm secret is disabled or destroyed |
| 7 | Run `verify_audit_file()` on the audit log and confirm chain is intact |
| 8 | Document incident: timestamp, operator name, trigger, steps taken, final state |
| 9 | Revoke `ApprovalRecord` in `LocalFileApprovalStore` |
| 10 | Archive audit log to operator-controlled storage outside repo |

---

### G. Audit and Evidence Requirements

Required evidence before any future real credential activation is considered closed:

| Evidence item | Source |
|---|---|
| Sanitized `ApprovalRecord` (no secrets) | `sanitize_approval_record()` output |
| Preflight PASS result | `check_live_operation_preflight()` result |
| Live gate PASS result | `check_live_gate()` result |
| First-call authorization sign-off | Named operator written approval |
| Audit log with no secret values | `verify_audit_file()` + `grep` redaction check |
| No raw IDs in docs | Safety grep CLEAN on all changed docs |
| Rollback drill result | Fake credential revoke sequence completed and verified |
| Final state documentation | Post-call or post-rollback state recorded |

---

### H. Secret Manager Version Lifecycle Decision

A policy decision is required before real credentials are written to GCP Secret Manager. Prior versions cannot remain indefinitely active after rotation. Options evaluated in `docs/GCP_SECRET_MANAGER_RUNBOOK.md` Section 18:

| Option | Description | Status |
|---|---|---|
| A | Destroy prior version immediately after rotation | Deferred — irreversible, requires separate authorization |
| B | Disable prior version immediately, destroy after defined grace period | Preferred design — requires operator policy decision and implementation |
| C | Keep all versions active indefinitely | Not acceptable for production use |
| D | Manual operator destroy, no automation | Current interim state |

V5.20 must produce a final policy decision on Option A or B before real credential rotation is authorized. Implementation of the chosen option is a V5.20 deliverable.

---

### I. Operator Checklist Document

Phase 2 will produce:

**`docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md`**

Contents:
- Pre-ceremony requirements
- Approval ceremony template
- Credential intake boundary rules
- Preflight checklist (Section D above, as a fillable operator checklist)
- First real API call constraints
- Post-call verification steps
- Rollback and emergency revoke sequence
- Audit evidence requirements
- Sign-off block (named operator, date, result)

---

### J. Test Strategy

V5.20 test scope:

| Test type | What is tested | Phase |
|---|---|---|
| Checklist validator unit tests | `validate_onboarding_checklist()` function accepts valid checklist, rejects missing/invalid fields | Phase 3 |
| Ceremony model unit tests | `OnboardingApprovalCeremony` dataclass validation; forbidden field detection | Phase 3 |
| Fake credential intake dry-run tests | Intake boundary enforcement with fake values; no real credentials | Phase 4 |
| Rollback drill tests | Full fake revoke sequence using V5.19 delete/revoke path; audit chain verified | Phase 6 |
| Smoke test extensions | No `GOOGLE_ADS_LIVE_ENABLED=true` in V5.20 files; no real credential patterns | Each phase |
| Safety greps | All changed docs and source files clean on each commit | Each phase |

No real Google Ads API calls in any V5.20 test. All tests use fake credentials, mock stores, or structural checks only.

---

## Phase Breakdown

| Phase | Description | Deliverables |
|---|---|---|
| 1 | Planning and branch setup | `V5_20_IMPLEMENTATION_PLAN.md`; ROADMAP update; README update; branch `v5.20-controlled-real-google-ads-onboarding-readiness` |
| 2 | Real onboarding checklist document | `docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md`; all sections A–H above represented as operator-fillable checklist |
| 3 | Onboarding approval ceremony model | `openclaw/onboarding_ceremony.py`; `OnboardingApprovalCeremony` dataclass; `validate_onboarding_checklist()`; unit tests |
| 4 | Credential intake dry-run design | `openclaw/credential_intake.py`; intake boundary validation (no real values); fake intake dry-run demo; unit tests |
| 5 | First live API validation plan | `docs/GOOGLE_ADS_FIRST_LIVE_CALL_PLAN.md`; exact endpoint, scope, constraints, audit sequence, rollback trigger — design only, no execution |
| 6 | Rollback/emergency revoke drill | `openclaw/run_revoke_drill_demo.py`; full fake credential revoke sequence; audit chain verification; smoke test extension |
| 7 | Secret Manager version lifecycle implementation | Implement chosen option (A or B from Section H); `openclaw/secret_lifecycle.py`; operator policy decision recorded |
| 8 | Final readiness review | All checklist items from Section D verified in test context; gap analysis; no open blockers |
| 9 | Closure docs and release notes | `docs/V5_20_BRANCH_CLOSURE.md`; `docs/RELEASE_NOTES_V5_20_0_BETA.md`; ROADMAP/README updates |
| 10 | Merge, tag, release | Merge to master; `v5.20.0-beta` tag; GitHub Release |

---

## Explicit Deferred Work

| Item | Deferred to |
|---|---|
| Actual real credential intake | Separate authorized milestone after V5.20 closure |
| Real OAuth consent flow execution | Requires explicit per-call operator authorization |
| Setting `GOOGLE_ADS_LIVE_ENABLED=true` | Requires V5.20 closure + explicit operator authorization |
| First real Google Ads API call | Requires `GOOGLE_ADS_LIVE_ENABLED=true` + completed ceremony + checklist |
| Production Cloud Run deployment | Requires service account, IAM, billing authorization |
| IAM hardening | Separate milestone |
| Destructive Secret Manager version lifecycle | Policy decision in Phase 7; irreversible destroy requires separate authorization |
| External approval UI | `LocalFileApprovalStore` only in V5.20 |
| Real production client or tenant onboarding | Deferred |
| BigQuery audit replication or Cloud Storage archival | Deferred |

---

## Release Criteria

V5.20 is releasable as `v5.20.0-beta` when all of the following are true:

- [ ] Checklist document complete and operator-reviewed
- [ ] Ceremony model implemented and tested
- [ ] Intake boundary enforcement tested with fake credentials
- [ ] First live API call plan documented (design only, no execution)
- [ ] Rollback drill completed with fake credential and audit verified
- [ ] Secret Manager version lifecycle policy decided and implemented (or deferred with explicit risk acceptance)
- [ ] Final readiness review complete, no open blockers
- [ ] Both smoke suites pass
- [ ] Safety greps clean on all changed files
- [ ] No real credentials used
- [ ] No `GOOGLE_ADS_LIVE_ENABLED=true` at runtime
- [ ] No Google Ads API calls
- [ ] No GCP commands
- [ ] Closure docs complete

---

## Related Documents

- [V5.19 Implementation Plan](V5_19_IMPLEMENTATION_PLAN.md)
- [V5.19 Branch Closure](V5_19_BRANCH_CLOSURE.md)
- [Credential Lifecycle Runbook](CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

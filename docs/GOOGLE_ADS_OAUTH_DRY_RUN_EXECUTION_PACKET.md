# Google Ads OAuth Dry-Run Execution Packet — V5.22 Controlled Ceremony

**Version:** V5.22
**Branch:** `v5.22-controlled-real-oauth-ceremony-dry-run`
**Baseline:** `v5.21.0-beta` / master `dd67c4f`
**Type:** Redacted dry-run template — not a live execution record

---

> **WARNING: THIS PACKET IS A REDACTED DRY-RUN TEMPLATE ONLY.**
>
> It does **not** authorize real OAuth execution.
> It does **not** authorize real credential handoff.
> It does **not** authorize authorization URL generation.
> It does **not** authorize browser opening.
> It does **not** authorize callback URL handling.
> It does **not** authorize auth code receipt.
> It does **not** authorize token exchange.
> It does **not** authorize Secret Manager writes.
> It does **not** authorize Google Ads API calls.
> It does **not** authorize GCP operations.
> It does **not** authorize deployment.
> It does **not** authorize `GOOGLE_ADS_LIVE_ENABLED=true` activation.
>
> **All fields must use placeholder labels only.**
> Real credentials, IDs, account identifiers, resource paths, emails, tokens, auth codes,
> approval payloads, OAuth URLs, callback URLs, or Secret Manager paths must never be entered.

---

## A. Packet Purpose

This packet is the structured artifact operators will complete during the V5.22 dry-run execution. It collects redacted role readiness, timed-window, validator, evidence, stop-condition, rollback, and final-state confirmations in a single, auditable document.

It is **not** a live execution record. No real OAuth ceremony is performed by filling in this packet. All fields that would reference real participants, real credentials, real accounts, or real execution state use `<placeholder_label>` form only.

When the V5.22 dry-run is executed (Phase 4), operators will work through this packet sequentially, completing each section in order, using redacted placeholder values throughout. The completed packet becomes the dry-run evidence artifact.

---

## B. Packet Identity

| Field | Value |
|---|---|
| Packet ID | `<packet_ref>` |
| Milestone | `V5.22` |
| Branch | `v5.22-controlled-real-oauth-ceremony-dry-run` |
| Baseline release | `v5.21.0-beta` |
| Baseline merge commit | `dd67c4f` |
| Dry-run date | `<timestamp_redacted>` |
| Dry-run status | `PENDING` |
| Decision owner | `<operator_label>` |
| Evidence reference | `<evidence_ref>` |

Allowed status values: `PENDING` · `PASS` · `FAIL` · `STOPPED`

---

## C. Participant Placeholder Table

All roles must be confirmed before the dry-run window opens. Real names, emails, account IDs, tenant IDs, customer IDs, project IDs, or resource paths are **forbidden** in this table and in any committed evidence document.

| Role | Label | Confirmed | Notes |
|---|---|---|---|
| Primary operator | `<operator_label>` | [ ] | Leads ceremony sequencing throughout |
| Secondary reviewer | `<reviewer_label>` | [ ] | Reviews each gate output; provides independent confirmation |
| Approval owner | `<approval_owner_label>` | [ ] | Holds approval record; confirms expiry and scope |
| OAuth execution operator | `<oauth_operator_label>` | [ ] | Would execute browser step in a future real ceremony |
| Credential handling owner | `<credential_owner_label>` | [ ] | Would manage acceptable handoff channel in a future real ceremony |
| Secret storage owner | `<storage_owner_label>` | [ ] | Would execute Secret Manager write in a future real ceremony |
| Rollback owner | `<rollback_owner_label>` | [ ] | Holds rollback and revoke path; must be reachable throughout window |
| Emergency revoke owner | `<emergency_revoke_owner_label>` | [ ] | Can initiate emergency revocation immediately; must be reachable throughout |
| Evidence owner | `<evidence_owner_label>` | [ ] | Assembles and stores redacted evidence package |
| Final verifier | `<verifier_label>` | [ ] | Confirms dry-run result and signs off |
| Stop authority | `<stop_authority_label>` | [ ] | Can halt ceremony at any point; must be reachable throughout |

**Readiness rule:** All roles must be confirmed before proceeding past Section D. Any unconfirmed role is a stop condition (see Section K).

---

## D. Redacted Target Context

These fields identify the ceremony context using placeholder labels only. They must not contain real tenant IDs, client IDs, account IDs, customer IDs, project IDs, service account emails, resource paths, credential refs, or Secret Manager paths.

| Field | Value |
|---|---|
| Tenant reference | `<tenant_ref>` |
| Client reference | `<client_ref>` |
| Approval reference | `<approval_ref>` |
| Ceremony reference | `<ceremony_ref>` |
| Handoff reference | `<handoff_ref>` |
| Rollback reference | `<rollback_ref>` |
| Evidence reference | `<evidence_ref>` |

All values are placeholders. No real identifiers are permitted in this section.

---

## E. Timed Execution Window Fields

The timed execution window defines the boundary within which ceremony actions occur. All steps must occur within this window. No action may start before the window opens. No action may continue after the window closes.

| Window parameter | Value | Confirmed |
|---|---|---|
| Planned window start | `<timestamp_redacted>` | [ ] |
| Planned window end | `<timestamp_redacted>` | [ ] |
| Maximum duration | `<duration_redacted>` | [ ] |
| Pre-window checklist lock | `YES` — all preconditions confirmed before window opens | [ ] |
| Window opened by | `<operator_label>` | [ ] |
| Window close confirmed by | `<verifier_label>` | [ ] |
| Extension requested | `NO` | [ ] |
| Extension approved | `NO` | [ ] |
| Stop authority reachable throughout | `YES` | [ ] |
| Rollback owner reachable throughout | `YES` | [ ] |
| Emergency revoke owner reachable throughout | `YES` | [ ] |
| Final live flag reset confirmation required | `YES` | [ ] |

**Window rules:**

| Rule | Requirement |
|---|---|
| D1 — No action before window opens | Any pre-window execution is unauthorized and a stop condition |
| D2 — No action after window closes | Window closure freezes all ceremony activity immediately |
| D3 — Unresolved ambiguity triggers stop | Any ambiguity not resolved before window closes halts ceremony |
| D4 — Extension requires re-approval | Extending the window requires a new explicit approval from the approval owner |
| D5 — Missing live flag reset is stop | If `GOOGLE_ADS_LIVE_ENABLED` reset is not confirmed before window closes, halt and escalate |
| D6 — Dry-run window does not activate live mode | Running this dry-run timed window is not authorization to activate `GOOGLE_ADS_LIVE_ENABLED=true` |
| D7 — Missing rollback owner is stop | Rollback owner must be reachable at all times during the window |
| D8 — Missing stop authority is stop | Stop authority must be reachable at all times during the window |

---

## F. Required Pre-Flight Gates

All gates must reach `PASS` before the dry-run sequence begins. Any `FAIL` or `STOPPED` is a stop condition.

| Gate | Status | Notes |
|---|---|---|
| V5.21 final readiness review reviewed | `PENDING` | `docs/V5_21_FINAL_READINESS_REVIEW.md` — 534 assertions PASS |
| V5.22 implementation plan reviewed | `PENDING` | `docs/V5_22_IMPLEMENTATION_PLAN.md` |
| OAuth ceremony checklist reviewed | `PENDING` | `docs/GOOGLE_ADS_OAUTH_CEREMONY_CHECKLIST.md` |
| Credential handoff protocol reviewed | `PENDING` | `docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md` |
| OAuth dry-run runbook reviewed | `PENDING` | `docs/GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md` |
| OAuth approval packet validator | `PENDING` | `openclaw/run_oauth_approval_packet_demo.py` — expected `PASS` — 110 assertions |
| OAuth auth URL design validator | `PENDING` | `openclaw/run_oauth_auth_url_demo.py` — expected `PASS` — 82 assertions |
| OAuth callback/token-exchange boundary validator | `PENDING` | `openclaw/run_oauth_callback_demo.py` — expected `PASS` — 98 assertions |
| Credential intake dry-run validator | `PENDING` | `openclaw/run_credential_intake_demo.py` — expected `PASS` — 70 assertions |
| Secret Manager version policy validator | `PENDING` | `openclaw/run_secret_version_policy_demo.py` — expected `PASS` — 71 assertions |
| Rollback drill validator | `PENDING` | `openclaw/run_rollback_drill_demo.py` — expected `PASS` — 67 assertions |
| Onboarding ceremony validator | `PENDING` | `openclaw/run_onboarding_ceremony_demo.py` — expected `PASS` |
| `smoke_test_v5_credentials.sh` | `PENDING` | expected `PASS` — 34/34 |
| `smoke_test_v5_12_gcp_secret_manager.sh` | `PENDING` | expected `PASS` — 8/8 |
| Safety grep | `PENDING` | expected `CLEAN` — all 9 patterns |

Allowed gate status values: `PENDING` · `PASS` · `FAIL` · `STOPPED`

---

## G. Dry-Run Sequence Checklist

Complete each step in order. Steps must not be skipped. Any `FAIL` halts the dry-run immediately.

| Step | Action | Status | Confirmed by |
|---|---|---|---|
| G-01 | Confirm branch is `v5.22-controlled-real-oauth-ceremony-dry-run` and base is `dd67c4f` | `[ ]` | `<operator_label>` |
| G-02 | Confirm working tree is clean | `[ ]` | `<operator_label>` |
| G-03 | Confirm no real credentials are present in any file | `[ ]` | `<operator_label>` |
| G-04 | Confirm no real approval has been created | `[ ]` | `<approval_owner_label>` |
| G-05 | Confirm all participant placeholders are populated in Section C | `[ ]` | `<reviewer_label>` |
| G-06 | Confirm timed window placeholders are populated in Section E | `[ ]` | `<operator_label>` |
| G-07 | Confirm all pre-flight gates reviewed (Section F) | `[ ]` | `<reviewer_label>` |
| G-08 | Confirm approval packet validator PASS | `[ ]` | `<operator_label>` |
| G-09 | Confirm auth URL design validator PASS | `[ ]` | `<operator_label>` |
| G-10 | Confirm callback boundary validator PASS | `[ ]` | `<operator_label>` |
| G-11 | Walk through ceremony checklist (`docs/GOOGLE_ADS_OAUTH_CEREMONY_CHECKLIST.md`) | `[ ]` | `<operator_label>` + `<reviewer_label>` |
| G-12 | Walk through credential handoff protocol (`docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md`) | `[ ]` | `<credential_owner_label>` + `<reviewer_label>` |
| G-13 | Walk through dry-run runbook (`docs/GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md`) | `[ ]` | `<operator_label>` + `<reviewer_label>` |
| G-14 | Walk through stop conditions (Section K of this packet) | `[ ]` | `<stop_authority_label>` |
| G-15 | Walk through rollback and emergency revoke sequence (Section L of this packet) | `[ ]` | `<rollback_owner_label>` + `<emergency_revoke_owner_label>` |
| G-16 | Record validator evidence in Section H | `[ ]` | `<evidence_owner_label>` |
| G-17 | Record smoke test evidence in Section H | `[ ]` | `<evidence_owner_label>` |
| G-18 | Record safety grep evidence in Section H | `[ ]` | `<evidence_owner_label>` |
| G-19 | Confirm no OAuth execution occurred during dry-run | `[ ]` | `<operator_label>` + `<reviewer_label>` |
| G-20 | Confirm no token exchange occurred | `[ ]` | `<operator_label>` |
| G-21 | Confirm no GCP, Secret Manager, or Google Ads API call occurred | `[ ]` | `<operator_label>` |
| G-22 | Confirm `GOOGLE_ADS_LIVE_ENABLED` remains `false` | `[ ]` | `<verifier_label>` |
| G-23 | Close dry-run window | `[ ]` | `<operator_label>` + `<verifier_label>` |
| G-24 | Assign final result: `PASS` / `FAIL` / `STOPPED` | `[ ]` | `<reviewer_label>` + `<verifier_label>` |

---

## H. Validator Evidence Fields

Record the result of each validator run during the dry-run. Do not include raw output containing secrets, real identifiers, or sensitive values. PASS/FAIL status only.

| Validator / Suite | Result | Expected | Notes |
|---|---|---|---|
| OAuth approval packet validator (`run_oauth_approval_packet_demo.py`) | `PENDING` | `PASS` | 110 assertions |
| OAuth auth URL design validator (`run_oauth_auth_url_demo.py`) | `PENDING` | `PASS` | 82 assertions |
| OAuth callback boundary validator (`run_oauth_callback_demo.py`) | `PENDING` | `PASS` | 98 assertions |
| Credential intake dry-run validator (`run_credential_intake_demo.py`) | `PENDING` | `PASS` | 70 assertions |
| Secret version policy validator (`run_secret_version_policy_demo.py`) | `PENDING` | `PASS` | 71 assertions |
| Rollback drill validator (`run_rollback_drill_demo.py`) | `PENDING` | `PASS` | 67 assertions |
| Onboarding ceremony validator (`run_onboarding_ceremony_demo.py`) | `PENDING` | `PASS` | |
| `smoke_test_v5_credentials.sh` | `PENDING` | `PASS` | 34/34 sections |
| `smoke_test_v5_12_gcp_secret_manager.sh` | `PENDING` | `PASS` | 8/8 sections |
| Safety grep (all 9 patterns) | `PENDING` | `CLEAN` | No sensitive hits |

Allowed result values: `PENDING` · `PASS` · `FAIL` · `NOT_RUN`

---

## I. No-Execution Confirmations

To be completed by `<operator_label>` and countersigned by `<reviewer_label>` at the close of the dry-run.

| Confirmation | Value |
|---|---|
| Real OAuth executed | `NO` |
| Browser opened | `NO` |
| Authorization URL generated | `NO` |
| Callback URL received | `NO` |
| Auth code received | `NO` |
| Token exchange attempted | `NO` |
| Token response received | `NO` |
| Real credentials requested | `NO` |
| Real credentials used | `NO` |
| Real approval created | `NO` |
| Secret Manager called | `NO` |
| Google Ads API called | `NO` |
| GCP commands / API calls used | `NO` |
| Deploy performed | `NO` |
| IAM / API / billing changes made | `NO` |
| `GOOGLE_ADS_LIVE_ENABLED=true` activated | `NO` |

These fields are pre-filled `NO` for the template. They must be verified and re-confirmed by operators at dry-run close. Any deviation is a stop condition and must be escalated immediately.

---

## J. Evidence Package Checklist

### Allowed evidence (may be recorded in completed packet)

- Redacted packet ID (`<packet_ref>` form)
- Branch name
- Baseline tag and commit hash
- Placeholder role labels (no real identities)
- Validator PASS / FAIL result only (no raw output with identifiers)
- Smoke suite PASS / FAIL result only
- Safety grep PASS / FAIL / CLEAN result only
- Timed window placeholder values (no real timestamps unless pre-approved for dry-run logging)
- Stop-condition and rollback walkthrough status (e.g. "rehearsed", "not triggered")
- Final no-execution confirmations from Section I

### Forbidden evidence (must never appear in any committed file)

- Real secret, token, or key value of any kind
- OAuth authorization URL (real or constructed)
- Callback URL or redirect URI
- Authorization code
- Access token or refresh token
- Client ID (real)
- Client secret (real)
- Developer token (real)
- Customer ID (real numeric)
- Login customer ID (real numeric)
- GCP project ID or project number
- Service account email
- Secret Manager resource path (`projects/...`)
- Credential reference path
- Real approval payload with identities
- Screenshots, logs, or outputs containing any of the above

---

## K. Stop-Condition Checklist

Any of the following conditions requires an immediate stop, window closure, and escalation to stop authority.

| Code | Condition |
|---|---|
| K-01 | Any real credential value (token, secret, key, password) appears in any file, log, or output |
| K-02 | Any OAuth authorization URL appears in any file, log, or output |
| K-03 | A browser is opened as part of any step |
| K-04 | A real callback URL appears in any file, log, or output |
| K-05 | A real auth code appears in any file, log, or output |
| K-06 | A real token (access or refresh) appears in any file, log, or output |
| K-07 | Token exchange is attempted against any endpoint |
| K-08 | Secret Manager is called (read or write) |
| K-09 | Google Ads API is called |
| K-10 | Any GCP command or API is invoked |
| K-11 | `GOOGLE_ADS_LIVE_ENABLED` is set to `true` at runtime |
| K-12 | A real approval record is created with real participant identities |
| K-13 | Any participant placeholder in Section C is missing or unconfirmed |
| K-14 | Timed window fields in Section E are missing |
| K-15 | Any pre-flight gate in Section F is `FAIL` |
| K-16 | Any smoke suite fails (`FAIL`) |
| K-17 | Safety grep produces a sensitive hit |
| K-18 | Rollback owner is unreachable during the window |
| K-19 | Emergency revoke owner is unreachable during the window |
| K-20 | Evidence owner is unreachable |
| K-21 | Stop authority is unreachable during the window |

**Stop procedure:** Declare stop → halt all actions → notify stop authority → execute rollback rehearsal (Section L) → document stop reason in Section M.

---

## L. Rollback and Emergency Revoke Rehearsal Fields

To be completed during the rollback rehearsal walkthrough (dry-run step G-15). All values are placeholders or confirmations only — no real revoke actions are taken in the dry-run.

| Field | Value |
|---|---|
| Stop declared | `YES` / `NO` |
| Stop reason | `<redacted_reason>` |
| Rollback owner confirmed | `YES` / `NO` |
| Emergency revoke owner confirmed | `YES` / `NO` |
| No real OAuth to revoke | `YES` — no real OAuth was executed |
| No auth code / token to revoke | `YES` — no real auth code or token was received |
| No Secret Manager write to delete | `YES` — no Secret Manager write was performed |
| No Google Ads API live state to reverse | `YES` — no Google Ads API was called |
| `GOOGLE_ADS_LIVE_ENABLED` final state `false` | `YES` / `NO` |
| Safety grep after stop | `PENDING` |
| Smoke suite after stop | `PENDING` |
| Final rollback rehearsal result | `PENDING` |

Allowed final rehearsal result values: `PASS` · `FAIL` · `STOPPED`

**Rehearsal reminder:** In this dry-run, there is nothing real to revoke. The rehearsal validates that the rollback sequence is understood and can be executed correctly in a future real ceremony. No actual revocation, deletion, or API call occurs.

---

## M. Final Dry-Run Decision

To be completed at the close of the dry-run window by `<reviewer_label>` and countersigned by `<verifier_label>`.

| Field | Value |
|---|---|
| Dry-run packet complete | `YES` / `NO` |
| All pre-flight gates `PASS` | `YES` / `NO` |
| All validators `PASS` | `YES` / `NO` |
| Dry-run sequence complete (G-01–G-24) | `YES` / `NO` |
| No-execution confirmations all `NO` | `YES` / `NO` |
| Stop conditions avoided | `YES` / `NO` |
| Rollback rehearsal complete | `YES` / `NO` |
| Evidence package redacted | `YES` / `NO` |
| Final decision | `PENDING` |
| Reviewer sign-off | `<reviewer_label>` |
| Final verifier sign-off | `<verifier_label>` |
| Notes | `<redacted_notes>` |

Allowed final decision values: `PASS` · `FAIL` · `STOPPED`

---

## N. Phase 2 Conclusion

This dry-run execution packet template is complete.

- Documentation-only. No dry-run has been executed.
- No real approval was created.
- No credentials were used or requested.
- No OAuth was executed.
- No authorization URL was generated.
- No browser was opened.
- No callback URL was received.
- No auth code was received.
- No token exchange was attempted.
- No Secret Manager was called.
- No Google Ads API was called.
- No GCP commands or APIs were used.
- No deployment was performed.
- `GOOGLE_ADS_LIVE_ENABLED` remains false.

Phase 3 (dry-run execution validator — `openclaw/oauth_dry_run_execution.py`) remains pending.

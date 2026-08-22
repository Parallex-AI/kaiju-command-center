# Google Ads OAuth Dry-Run Runbook — V5.21 Controlled Onboarding

**Kaiju Command Center — V5.21 Phase 7**

**Branch:** `v5.21-controlled-real-google-ads-oauth-onboarding`

---

> **WARNING — READ BEFORE USING THIS DOCUMENT**
>
> - This runbook is **documentation-only**. It does not authorize real OAuth execution.
> - This runbook does not authorize real credential handoff.
> - This runbook does not authorize token exchange.
> - This runbook does not authorize Secret Manager writes.
> - This runbook does not authorize Google Ads API calls.
> - This runbook does not authorize GCP operations.
> - This runbook does not authorize `GOOGLE_ADS_LIVE_ENABLED=true`.
> - This runbook does not create a real approval.
> - **This runbook must not be used as permission to perform live onboarding.**
> - **All real execution requires separate explicit operator approval.**
> - **Do not paste credentials, OAuth URLs, auth codes, refresh tokens, or access tokens into chat.**
> - **Do not commit any real credential value, token, resource path, customer ID, project ID, or account email.**
> - **Any dry-run step must stop immediately** if a real credential, real URL, real auth code, or real token is detected.

---

## A. Purpose

This dry-run runbook defines how operators rehearse a future Google Ads OAuth onboarding ceremony without touching real credentials, URLs, auth codes, tokens, Google APIs, Secret Manager, or cloud resources. The runbook is a rehearsal reference only. It does not perform real onboarding.

The objective of the dry-run is to validate the following before any future real execution:

- **Sequencing:** all ceremony steps occur in the correct order and no step is skipped.
- **Timing:** the execution window model is correctly defined and all participants understand the timebox.
- **Role readiness:** every named role is confirmed and reachable before the window opens.
- **Stop authority:** the stop authority is confirmed, understands their mandate, and is reachable throughout the window.
- **Evidence collection:** the evidence package rehearsal confirms what is collected and what remains redacted.
- **Rollback readiness:** the rollback and emergency revoke sequences are reviewed and understood before the window opens.
- **Validator coverage:** all V5.21 validators are confirmed PASS before the dry-run proceeds.
- **Smoke and safety-grep coverage:** both smoke suites and all safety greps are CLEAN before the dry-run proceeds.
- **Final live flag reset:** the procedure for confirming `GOOGLE_ADS_LIVE_ENABLED` remains false is reviewed and rehearsed.

V5.21 Phase 7 creates this runbook. It does not execute the ceremony. No OAuth URL was generated. No browser flow was opened. No real credentials were requested or used. No Secret Manager write was performed. No Google Ads API was called. No GCP operation was performed.

---

## B. Dry-Run Scope

### In scope for the dry-run

| Item | Description |
|---|---|
| Approval packet dry-run | Walk through `validate_oauth_approval_packet()` with dry-run inputs; confirm PASS |
| Ceremony checklist walkthrough | Walk through all sections of `docs/GOOGLE_ADS_OAUTH_CEREMONY_CHECKLIST.md` |
| Credential handoff protocol walkthrough | Walk through all sections of `docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md` |
| Authorization URL design gate review | Walk through `validate_oauth_auth_url_design()` validator requirements |
| Callback/token-exchange boundary gate review | Walk through `validate_oauth_callback_design()` validator requirements |
| Rollback and emergency revoke walkthrough | Walk through Section I (Rollback and Revocation Integration) of credential handoff protocol |
| Evidence package rehearsal | Walk through Section J (Evidence Package) of ceremony checklist and Section J of dry-run result template |
| Smoke and safety-grep verification | Confirm both smoke suites PASS and all safety greps CLEAN |
| Final live flag reset confirmation | Confirm `GOOGLE_ADS_LIVE_ENABLED` remains false; rehearse reset procedure |
| Timed window walkthrough | Walk through the timed execution window model in Section D of this runbook |

### Explicitly out of scope for the dry-run

| Item | Reason |
|---|---|
| Real OAuth browser execution | Requires separate explicit operator authorization beyond V5.21 |
| Real browser consent screen interaction | Requires separate explicit authorization |
| Real OAuth authorization URL generation | Requires separate explicit authorization |
| Real callback URL receipt | Requires separate explicit authorization |
| Real auth code receipt or handling | Requires separate explicit authorization |
| Real token exchange | Requires separate explicit authorization |
| Real credential handoff | Requires separate explicit authorization |
| Real Secret Manager write | Requires separate explicit authorization |
| Real Google Ads API call | Requires separate explicit authorization |
| Real GCP operation | Requires separate explicit authorization |
| Production deployment | Requires separate explicit authorization |
| `GOOGLE_ADS_LIVE_ENABLED=true` runtime activation | Requires separate explicit authorization |

---

## C. Participants and Role Readiness

All roles must be confirmed before the dry-run window opens. Use redacted labels only in all committed documents. Real operator names, emails, tenant IDs, customer IDs, or account IDs must never appear in any committed file.

| Role | Label | Dry-run confirmed | Notes |
|---|---|---|---|
| Primary operator | `<operator_label>` | [ ] | Leads ceremony sequencing |
| Secondary reviewer | `<reviewer_label>` | [ ] | Reviews each gate output |
| Approval owner | `<approval_owner_label>` | [ ] | Holds approval record; confirms expiry |
| OAuth execution operator | `<oauth_operator_label>` | [ ] | Executes browser step (future real ceremony only) |
| Credential handling owner | `<credential_handler_label>` | [ ] | Manages acceptable channel for credential transfer |
| Secret storage owner | `<storage_owner_label>` | [ ] | Executes Secret Manager write (future real ceremony only) |
| Rollback owner | `<rollback_owner_label>` | [ ] | Holds rollback and revoke path |
| Emergency revoke owner | `<revoke_owner_label>` | [ ] | Can initiate emergency revocation immediately |
| Evidence owner | `<evidence_owner_label>` | [ ] | Assembles and stores redacted evidence package |
| Final verifier | `<verifier_label>` | [ ] | Confirms dry-run result and signs off |
| Stop authority | `<stop_authority_label>` | [ ] | Can halt the ceremony at any point; must be reachable throughout |

**Role readiness check:** all roles must be confirmed confirmed before proceeding past Section D. Any unconfirmed role is a stop condition.

**Placeholder reminder:** no real name, email, tenant ID, customer ID, login customer ID, project ID, or account email may appear in this table or any committed evidence document. All identifiers use the `<label>` form above.

---

## D. Timed Execution Window Model

The timed execution window defines the boundary within which a future real OAuth ceremony may proceed. All ceremony actions must occur within this window. No action may start before the window opens. No action may continue after the window closes.

| Window parameter | Value | Confirmed |
|---|---|---|
| Planned window start | `<timestamp_redacted>` | [ ] |
| Planned window end | `<timestamp_redacted>` | [ ] |
| Maximum duration | Must be explicitly defined before real execution | [ ] |
| Pre-window checklist lock | All preconditions confirmed before window opens | [ ] |
| Live-action boundary | Only actions listed in Section E may occur during window | [ ] |
| Rollback decision point | Defined pause point at Section E step 16 | [ ] |
| Post-window cleanup | Final live flag reset and evidence package assembly | [ ] |
| Final live flag reset confirmation | `GOOGLE_ADS_LIVE_ENABLED` confirmed false before window closes | [ ] |

### Window rules

| Rule | Rationale |
|---|---|
| D1 — No action before window opens | Any pre-window execution is unauthorized and a stop condition |
| D2 — No action after window closes | Window closure freezes all ceremony activity immediately |
| D3 — Unresolved ambiguity triggers stop | Any ambiguity not resolved before window closes halts ceremony |
| D4 — Window extension requires re-approval | Extending the window requires a new explicit approval from the approval owner |
| D5 — Missing live flag reset confirmation is stop | If `GOOGLE_ADS_LIVE_ENABLED` reset is not confirmed before window closes, halt and escalate |
| D6 — Timed window rehearsal does not activate live mode | Running the dry-run timed window model is not authorization to activate `GOOGLE_ADS_LIVE_ENABLED=true` |
| D7 — Missing rollback owner during window is stop | Rollback owner must be reachable at all times during the execution window |
| D8 — Missing stop authority during window is stop | Stop authority must be reachable at all times during the execution window |

### Mandatory pause points

| Pause point | After step | Purpose |
|---|---|---|
| P1 — Pre-window gate review | Step 13 (Section E) | Final confirmation all validators PASS, smoke PASS, grep CLEAN |
| P2 — Authorization URL design review | After URL design review gate | Secondary reviewer confirms URL design before any browser step |
| P3 — Callback boundary review | After callback gate | Secondary reviewer confirms callback handling design before any token step |
| P4 — Credential handoff approval | Before handoff sequence step E1 | Approval owner confirms handoff packet is ready |
| P5 — Rollback decision checkpoint | After any unexpected outcome | Rollback owner and stop authority confirm proceed vs. halt |
| P6 — Final live flag review | Before window closes | All participants confirm `GOOGLE_ADS_LIVE_ENABLED` final state |

---

## E. Dry-Run Sequence

The following sequence defines the full dry-run rehearsal. Each step must be confirmed in order. Steps must not be skipped. Any FAIL at any step halts the dry-run immediately.

| Step | Action | Gate | Confirmed |
|---|---|---|---|
| E1 | Confirm current branch/ref and working tree state | Branch matches approved plan; tree clean | [ ] |
| E2 | Confirm V5.20 readiness docs reviewed (`docs/V5_20_FINAL_READINESS_REVIEW.md`) | V5.20 PASS confirmed in readiness review | [ ] |
| E3 | Confirm V5.21 implementation plan reviewed (`docs/V5_21_IMPLEMENTATION_PLAN.md`) | All phase notes reviewed | [ ] |
| E4 | Confirm OAuth ceremony checklist reviewed (`docs/GOOGLE_ADS_OAUTH_CEREMONY_CHECKLIST.md`) | All 14 sections reviewed by operator and reviewer | [ ] |
| E5 | Confirm credential handoff protocol reviewed (`docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md`) | All 14 sections reviewed by operator and reviewer | [ ] |
| E6 | Confirm approval packet validator PASS — `validate_oauth_approval_packet()` | Demo passes with dry-run inputs; no real approval values | [ ] |
| E7 | Confirm OAuth auth URL design validator PASS — `validate_oauth_auth_url_design()` | Demo passes; no real URL generated | [ ] |
| E8 | Confirm OAuth callback boundary validator PASS — `validate_oauth_callback_design()` | Demo passes; no real callback processed | [ ] |
| E9 | Confirm credential intake dry-run validator PASS — `validate_credential_intake()` | Demo passes; no real credentials used | [ ] |
| E10 | Confirm Secret Manager version policy validator PASS — `validate_secret_version_policy()` | Demo passes; `DISABLE_PREVIOUS_WITH_GRACE_PERIOD` confirmed | [ ] |
| E11 | Confirm rollback drill validator PASS — `validate_rollback_drill()` | Demo passes; revoke path confirmed | [ ] |
| E12 | Confirm `smoke_test_v5_credentials.sh` PASS (current count) | All sections PASS | [ ] |
| E13 | Confirm `smoke_test_v5_12_gcp_secret_manager.sh` PASS (8/8) | All sections PASS | [ ] |
| E14 | Confirm all safety greps CLEAN on ceremony-modified files | No real tokens, IDs, URLs, or resource paths found | [ ] |
| **P1 PAUSE** | Pre-window gate review — all participants confirm before window opens | All E1–E14 confirmed PASS/CLEAN | [ ] |
| E15 | Walk through timed execution window model (Section D) | All window parameters reviewed and understood | [ ] |
| E16 | Walk through stop conditions (Section H) | All participants can identify and act on stop conditions | [ ] |
| **P5 PAUSE** | Rollback decision checkpoint rehearsal | Rollback owner and stop authority confirm escalation path | [ ] |
| E17 | Walk through rollback and emergency revoke sequence (Section I) | All participants understand revoke path | [ ] |
| E18 | Walk through evidence package (Section G) | Evidence owner confirms what is collected and what stays redacted | [ ] |
| E19 | Confirm no real execution occurred during dry-run | All roles confirm; operator confirms no OAuth flow was initiated | [ ] |
| **P6 PAUSE** | Final live flag review — all participants confirm | `GOOGLE_ADS_LIVE_ENABLED` confirmed false | [ ] |
| E20 | Document dry-run result using template in Section J | Evidence owner records result; all roles sign in redacted form | [ ] |

**Dry-run result:** [ ] ALL STEPS PASS — dry-run complete  /  [ ] STOP — halt; do not proceed to real ceremony

---

## F. Gate Checklist

All gates must be confirmed before the dry-run window closes. Each gate must have a confirmed PASS status. Any gate failure is a stop condition.

| Gate | Validator / Document | Required result | Confirmed |
|---|---|---|---|
| F1 — Approval packet | `validate_oauth_approval_packet()` | PASS | [ ] |
| F2 — OAuth auth URL design | `validate_oauth_auth_url_design()` | PASS | [ ] |
| F3 — OAuth callback boundary | `validate_oauth_callback_design()` | PASS | [ ] |
| F4 — Credential handoff protocol | `docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md` | All 14 sections reviewed | [ ] |
| F5 — Credential intake dry-run | `validate_credential_intake()` | PASS | [ ] |
| F6 — Secret Manager version policy | `validate_secret_version_policy()` | PASS | [ ] |
| F7 — Rollback drill | `validate_rollback_drill()` | PASS | [ ] |
| F8 — Live gate requirement | `check_live_gate()` with approval conditions | PASS | [ ] |
| F9 — Audit requirement | Audit logging enabled and path writable confirmed | CONFIRMED | [ ] |
| F10 — Safety grep | All greps on ceremony-modified files | CLEAN | [ ] |
| F11 — Smoke tests | `smoke_test_v5_credentials.sh` + `smoke_test_v5_12_gcp_secret_manager.sh` | Both PASS | [ ] |
| F12 — Final live flag reset | `GOOGLE_ADS_LIVE_ENABLED` reset procedure confirmed | CONFIRMED | [ ] |

---

## G. Evidence Rehearsal

### Allowed dry-run evidence (may be committed in redacted form)

| Evidence item | Allowed committed form |
|---|---|
| Role readiness summary | `<operator_label>` confirmed; `<reviewer_label>` confirmed; etc. |
| Checklist walkthrough status | PASS/FAIL per checklist section |
| Validator names and result | `validate_oauth_approval_packet()`: PASS/FAIL |
| Smoke test result | `smoke_test_v5_credentials.sh` — PASS/FAIL · `smoke_test_v5_12_gcp_secret_manager.sh` — PASS/FAIL |
| Safety grep result | CLEAN or FAIL |
| Timed window start/end | `<timestamp_redacted>` |
| Rollback owner confirmation | `<rollback_owner_label>` confirmed |
| Emergency revoke owner confirmation | `<revoke_owner_label>` confirmed |
| Final no-execution statement | "No real OAuth was executed during this dry-run" |
| Final live flag false statement | "`GOOGLE_ADS_LIVE_ENABLED` confirmed false at dry-run close" |

### Forbidden dry-run evidence (must never appear in any committed file)

| Forbidden item | Why |
|---|---|
| Real secret, token, or key value | Permanent credential leakage risk |
| Real OAuth authorization URL | Contains client ID and redirect URI |
| Real callback URL | Contains auth code in some flows |
| Real auth code | One-time credential — immediate leakage risk |
| Real refresh token | Long-lived credential — immediate leakage risk |
| Real access token | Live credential — immediate leakage risk |
| Real OAuth client ID | Identifies the OAuth application |
| Real OAuth client secret | Authenticates the OAuth application |
| Real developer token | Identifies the Google Ads developer account |
| Real customer ID | Identifies a Google Ads account |
| Real login customer ID | Identifies a Google Ads manager account |
| Real Secret Manager resource path | Exposes GCP project structure |
| Real credential reference or secret ID | Exposes Secret Manager naming |
| Real GCP project ID or project number | Exposes GCP project identity |
| Real GCP account email or service account | Exposes GCP identity |
| Screenshots with sensitive material | Screen content may contain credentials |

If any forbidden item is detected in any committed or chat-visible evidence, halt immediately and treat as a credential leakage incident.

---

## H. Stop Conditions

Any of the following conditions during the dry-run must cause immediate halt. No dry-run step may continue after a stop condition is detected.

| # | Stop condition |
|---|---|
| H1 | Approval packet validator fails or is missing |
| H2 | Checklist walkthrough mismatch — any section status is ambiguous |
| H3 | Role ambiguity — any role is unconfirmed or unavailable |
| H4 | Stop authority is missing or unreachable at any point during the window |
| H5 | Timed execution window is not defined before dry-run begins |
| H6 | Rollback owner is unavailable at any point during the window |
| H7 | Emergency revoke owner is unavailable at any point during the window |
| H8 | Evidence owner is unavailable at any point during the window |
| H9 | Any validator returns FAIL during dry-run gate review |
| H10 | Smoke test failure — either suite fails |
| H11 | Safety grep failure — any real token, ID, URL, or resource path found |
| H12 | Live flag state ambiguity — `GOOGLE_ADS_LIVE_ENABLED` state cannot be confirmed |
| H13 | Any real secret, token, credential, or key value appears in chat, log, repo, or docs |
| H14 | Any real account ID, customer ID, resource path, or project ID appears in any committed file |
| H15 | Operator attempts to execute real OAuth during dry-run |
| H16 | Browser is opened with any OAuth-related URL during dry-run |
| H17 | Real OAuth authorization URL is generated at any point |
| H18 | Real auth code is received at any point |
| H19 | Token exchange is attempted at any point |
| H20 | GCP command is run at any point |
| H21 | Secret Manager is called at any point |
| H22 | Google Ads API is called at any point |
| H23 | Any window rule (Section D rules D1–D8) is violated |
| H24 | Evidence package contains any forbidden item (Section G) |
| H25 | Rollback decision checkpoint is skipped at pause point P5 |

**On stop:** halt all dry-run activity; notify stop authority and rollback owner; document the stop condition in the dry-run result template (Section J); do not proceed to real ceremony without a new separate dry-run PASS.

---

## I. Rollback and Emergency Revoke Rehearsal

This section rehearses the rollback and revoke sequence. It is documentation-only. No real revocation action is taken during the dry-run.

| Step | Dry-run action | Confirmed |
|---|---|---|
| R1 | Declare stop — operator announces halt to all participants | [ ] |
| R2 | Freeze further ceremony actions — no new actions after halt | [ ] |
| R3 | Confirm no real OAuth was executed — operator and reviewer confirm | [ ] |
| R4 | Confirm no real auth code or token exists — credential handling owner confirms | [ ] |
| R5 | Confirm no Secret Manager write occurred — storage owner confirms | [ ] |
| R6 | Confirm no Google Ads API call occurred — OAuth execution operator confirms | [ ] |
| R7 | Confirm `GOOGLE_ADS_LIVE_ENABLED` remains false — primary operator confirms | [ ] |
| R8 | Review revoke path if future credential exists — emergency revoke owner walks through `DELETE /credentials/google-ads` (V5.15 endpoint, ADMIN scope) | [ ] |
| R9 | Review delete/revoke bundle path if future storage occurs — storage owner walks through Secret Manager version disable sequence | [ ] |
| R10 | Verify smoke tests — primary operator confirms both suites PASS | [ ] |
| R11 | Verify safety grep — secondary reviewer confirms all greps CLEAN | [ ] |
| R12 | Document final dry-run state — evidence owner records redacted result in Section J template | [ ] |

**Rollback rehearsal result (future ceremony only):** [ ] REHEARSED — participants understand revoke path  /  [ ] NOT REHEARSED — stop; re-rehearse before real ceremony

---

## J. Dry-Run Result Template

Complete this template after each dry-run. All fields must use redacted placeholders. No real credential values, resource paths, customer IDs, project IDs, or account emails may appear in any committed instance of this template.

| Field | Value |
|---|---|
| Dry-run date | `<timestamp_redacted>` |
| Branch / ref | `<branch_ref>` |
| Primary operator | `<operator_label>` |
| Secondary reviewer | `<reviewer_label>` |
| Tenant ref | `<tenant_ref>` |
| Client ref | `<client_ref>` |
| Approval packet validator | PASS / FAIL |
| OAuth auth URL design validator | PASS / FAIL |
| OAuth callback boundary validator | PASS / FAIL |
| Credential handoff protocol reviewed | YES / NO |
| Credential intake dry-run validator | PASS / FAIL |
| Secret version policy validator | PASS / FAIL |
| Rollback drill validator | PASS / FAIL |
| Smoke test result (`smoke_test_v5_credentials.sh`) | PASS / FAIL |
| Smoke test result (`smoke_test_v5_12_gcp_secret_manager.sh`) | PASS / FAIL |
| Safety grep result | CLEAN / FAIL |
| Real OAuth executed | NO |
| Real credentials used | NO |
| Real auth code received | NO |
| Token exchange attempted | NO |
| GCP / Secret Manager / Google Ads API called | NO |
| `GOOGLE_ADS_LIVE_ENABLED` final state | `false` |
| Overall dry-run decision | PASS / FAIL |
| Notes | `<redacted_notes>` |

**Sign-off (future ceremony only — redacted labels only):**

| Role | Label | Timestamp | Sign-off |
|---|---|---|---|
| Primary operator | `<operator_label>` | `<timestamp_redacted>` | [ ] Confirmed |
| Secondary reviewer | `<reviewer_label>` | `<timestamp_redacted>` | [ ] Confirmed |
| Evidence owner | `<evidence_owner_label>` | `<timestamp_redacted>` | [ ] Confirmed |
| Stop authority | `<stop_authority_label>` | `<timestamp_redacted>` | [ ] Confirmed |

---

## K. Phase 7 Conclusion

This document was produced in V5.21 Phase 7 as a dry-run onboarding runbook for a future authorized Google Ads OAuth ceremony event.

**Dry-run onboarding runbook created.** Documentation-only.

**No real approval was created.** All approval references use redacted placeholders only.
**No credentials were requested or used.** All credential class references are illustrative or redacted.
**No OAuth was executed.** No browser flow was opened. No authorization URL was generated.
**No auth code was received.** No real callback was processed.
**No token exchange was attempted.**
**No Secret Manager call was made.**
**No Google Ads API call was made.**
**No GCP operation was performed.**
**`GOOGLE_ADS_LIVE_ENABLED` remains false.**

This runbook is prerequisite documentation only. A future ceremony operator must use this runbook in conjunction with a separately issued, non-expired, explicitly scoped operator approval before initiating any real OAuth onboarding event. Completion of this dry-run runbook is not authorization to execute the ceremony.

**Phase 7 implementation:** `docs/GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md` created. Documentation-only. No Python module. No real credentials. No real approval. No OAuth executed. No auth URL generated. No auth code received. No token exchange. No Secret Manager call. No Google Ads API call. No GCP operation. No live flag activation. `GOOGLE_ADS_LIVE_ENABLED` remains false.

**Phase 8 note:** `docs/V5_21_FINAL_READINESS_REVIEW.md` (V5.21 Phase 8) is the pre-execution final readiness review and gap analysis that confirms this dry-run runbook exists and has been reviewed as part of the V5.21 readiness assessment (Section A, Section C). The review confirms: dry-run runbook readiness controls PASS locally; completion of a dry-run using this runbook is a mandatory gate (G5) before any real ceremony execution window opens. The review states NOT APPROVED for real OAuth execution. This runbook remains a rehearsal reference only.

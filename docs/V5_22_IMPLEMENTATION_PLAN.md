# V5.22 Implementation Plan — Controlled Real OAuth Ceremony Dry Run Execution

**Branch:** `v5.22-controlled-real-oauth-ceremony-dry-run`
**Base:** `v5.21.0-beta` / master at `dd67c4f`
**Status:** Phase 7 — Branch closure docs and release notes
**Purpose:** Execute a full dry-run rehearsal of the controlled Google Ads OAuth onboarding ceremony using V5.21 controls, validators, runbooks, and redacted placeholders only.

---

**This plan does not authorize execution.**
**This plan does not request real credentials.**
**This plan does not execute OAuth.**
**This plan does not call Google Ads API.**
**This plan does not call GCP or Secret Manager.**
**`GOOGLE_ADS_LIVE_ENABLED` remains false throughout.**

---

## A. Objective

V5.22 executes a full dry-run rehearsal of the controlled Google Ads OAuth onboarding ceremony using V5.21 controls, validators, runbooks, checklists, and redacted placeholders only.

V5.22 validates whether the ceremony can be operated safely before any future real credential or OAuth work. Every step of the ceremony is rehearsed using placeholder labels (e.g. `[OPERATOR]`, `[REVIEWER]`, `[TENANT_REF]`) — no real participant identities, no real credentials, no real auth codes, no real tokens.

The critical distinction: V5.22 rehearses how real OAuth onboarding would be performed. It does not perform real OAuth onboarding. Any real execution requires a separate explicit operator authorization that is outside the scope of this branch and cannot be inferred from V5.22's PASS status.

---

## B. Non-Authorization Statement

V5.22 Phase 1 is not authorization to execute any of the following:

- **Real OAuth execution** — No real OAuth consent flow is initiated.
- **Real credential handoff** — No real refresh token, access token, client secret, or developer token is produced, stored, or transmitted.
- **Real authorization URL generation** — No URL pointing to Google OAuth endpoints is generated.
- **Real browser opening** — No browser interaction occurs.
- **Real callback URL handling** — No redirect URI receives a real OAuth callback.
- **Real auth code receipt** — No authorization code from Google OAuth is received, logged, stored, or committed.
- **Real token exchange** — No call to the Google OAuth token endpoint is made.
- **Real Secret Manager writes** — No credentials are written to GCP Secret Manager.
- **Real Google Ads API calls** — No Google Ads API endpoint is invoked.
- **Real GCP operations** — No GCP commands, APIs, or resources are used.
- **Real deployment** — No Cloud Run, App Engine, or other compute deployment is executed.
- **`GOOGLE_ADS_LIVE_ENABLED=true` activation** — The live flag is not set to `true` at runtime in any context.

---

## C. Baseline

**Baseline release:** `v5.21.0-beta`
**Baseline branch:** `master`
**Baseline merge commit:** `dd67c4f`

**Existing controls available from V5.21:**

| Control | File | Description |
|---|---|---|
| OAuth ceremony checklist | `docs/GOOGLE_ADS_OAUTH_CEREMONY_CHECKLIST.md` | 15-section operator ceremony template; 25 stop conditions; 13-step rollback |
| OAuth auth URL design validator | `openclaw/oauth_auth_url.py` | 26 fields; 26 failure codes; `validate_oauth_auth_url_design()` |
| OAuth callback/token-exchange boundary validator | `openclaw/oauth_callback.py` | 32 fields; 32 failure codes; `validate_oauth_callback_design()` |
| OAuth approval packet validator | `openclaw/oauth_approval_packet.py` | 33 fields; 33 failure codes; `validate_oauth_approval_packet()` |
| Credential handoff protocol | `docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md` | 14 sections; 15 stop conditions; 7-step revocation path |
| OAuth dry-run runbook | `docs/GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md` | 11 sections; 20-step dry-run sequence; 12-gate checklist |
| V5.21 final readiness review | `docs/V5_21_FINAL_READINESS_REVIEW.md` | 534 assertions PASS; NOT APPROVED for real execution |
| Credential intake dry-run validator | `openclaw/credential_intake.py` | V5.20; `validate_credential_intake_dry_run()` |
| Rollback drill validator | `openclaw/rollback_drill.py` | V5.20; `validate_rollback_drill()` |
| Secret Manager version policy validator | `openclaw/secret_version_policy.py` | V5.20; `validate_secret_version_policy()` |
| V5.19 live / preflight gate | `openclaw/live_gate.py`, `openclaw/preflight.py` | Live-disabled gate; preflight denial chain |

---

## D. V5.22 Phase Plan

### Phase 1 — Branch setup and dry-run execution plan
**Deliverables:** `docs/V5_22_IMPLEMENTATION_PLAN.md`; README and ROADMAP updates.
**No-real-execution constraint:** Planning only. No validator run. No dry-run execution. No real credentials. No OAuth. No GCP.
**Validation:** Document review. Safety grep clean. Smoke tests pass (no regressions from base).

### Phase 2 — Dry-run execution packet template
**Deliverables:** `docs/GOOGLE_ADS_OAUTH_DRY_RUN_EXECUTION_PACKET.md`
**Contents:**
- Redacted participant placeholder table (8 roles: operator, reviewer, tenant ref, client ref, rollback owner, emergency revoke owner, evidence owner, stop authority — all as `[PLACEHOLDER]` labels).
- Dry-run execution summary fields (date, window start, window duration, window state).
- Pre-ceremony gate checklist (validators, smoke, approval packet, stop authority confirmed).
- Authorization URL design gate (dry-run — redacted input fields, no real URL).
- Browser execution gate (dry-run — placeholder confirmation, no real browser).
- Callback/token-exchange boundary gate (dry-run — placeholder confirmations, no real callback or auth code).
- Credential handoff protocol gate (dry-run — placeholder confirmations, no real credentials).
- Evidence package (redacted fields only).
- Stop-condition rehearsal table (all H1–H25 conditions from dry-run runbook, each marked simulated or not triggered).
- Rollback/emergency revoke rehearsal table (R1–R12 steps, each marked rehearsed).
- Dry-run sign-off block (redacted placeholder labels, not real names/signatures).
- No-execution confirmation (14 items).
**No-real-execution constraint:** Documentation-only template. No Python module. No real credentials. No real participants. No OAuth. No GCP.
**Validation:** Document review. Safety grep clean.

**Phase 2 Implementation Note:** `docs/GOOGLE_ADS_OAUTH_DRY_RUN_EXECUTION_PACKET.md` created. Documentation-only. 14 sections (A–N): packet purpose; packet identity (9 fields); participant placeholder table (11 roles, all as `<label>` placeholders); redacted target context (7 reference fields); timed execution window fields (12 fields, 8 window rules D1–D8); required pre-flight gates (15 gates); dry-run sequence checklist (24 steps G-01–G-24); validator evidence fields (10 validators/suites); no-execution confirmations (16 items, all pre-filled `NO`); evidence package checklist (allowed and forbidden evidence tables); stop-condition checklist (21 conditions K-01–K-21); rollback and emergency revoke rehearsal fields (12 fields); final dry-run decision (12 fields, sign-off block); Phase 2 conclusion. No Python module created. No dry-run executed. No real approval. No credentials. No OAuth. No auth URL. No browser. No callback URL. No auth code. No token exchange. No Secret Manager. No Google Ads API. No GCP. `GOOGLE_ADS_LIVE_ENABLED` remains false. Phase 3 (dry-run execution validator) remains pending.

### Phase 3 — Dry-run execution validator
**Deliverables:** `openclaw/oauth_dry_run_execution.py` · `openclaw/run_oauth_dry_run_execution_demo.py`
**Validator responsibilities:**
- Validate `OAuthDryRunExecutionInput` completeness.
- Enforce that all participant fields contain placeholder labels, not real identities.
- Enforce that all credential fields are absent or explicitly set to `False`.
- Enforce that execution window is timeboxed and within policy bounds.
- Enforce that all 7 validator gates are confirmed present and PASS.
- Enforce that all 12 pre-ceremony checklist items are confirmed.
- Enforce that stop-condition rehearsal is recorded.
- Enforce that rollback rehearsal is recorded.
- Enforce that evidence package contains only placeholder/redacted content.
- Hard-stop detection: real credential present, OAuth execution detected, auth code present, token exchange attempted, GCP/Secret Manager called, browser opened.
- Forbidden-field and forbidden-value detection.
- Pure stdlib only — no GCP, no network, no subprocess, no socket, no requests.
**Demo:** Scenarios covering PASS path, each failure code, hard-stop triggers.
**No-real-execution constraint:** Local-only. No real credentials. No OAuth. No GCP. `GOOGLE_ADS_LIVE_ENABLED` remains false.
**Validation:** All demo assertions PASS. Smoke section added to `smoke_test_v5_credentials.sh`.

**Phase 3 Implementation Note:** `openclaw/oauth_dry_run_execution.py` and `openclaw/run_oauth_dry_run_execution_demo.py` created. Local-only dry-run execution packet validator. `OAuthDryRunExecutionInput` (45 boolean fields: 12 packet completeness, 11 pre-flight/gate, 7 dry-run sequence/evidence, 15 hard-stop detections; plus evidence and metadata dicts). 47 failure codes. `validate_oauth_dry_run_execution()` validates packet completeness, gate PASS confirmation, no-execution confirmations, evidence package redaction, stop-condition and rollback rehearsal presence, and final decision presence; enforces all 15 hard-stop fields are False; detects forbidden field names and value patterns in evidence/metadata. Pure stdlib. No GCP. No network. No subprocess. No socket. No real credentials. No real approval. No OAuth. No auth URL. No browser. No callback URL. No auth code. No token exchange. No Secret Manager. No Google Ads API. No GCP. No deploy. `GOOGLE_ADS_LIVE_ENABLED` remains false. Demo: 55 scenarios, 112 assertions, all PASS. Smoke suite updated to [35/35] PASS. Phase 4 remains pending.

### Phase 4 — Execute dry-run packet locally
**Deliverables:** `docs/V5_22_DRY_RUN_EXECUTION_RESULTS.md`
**Contents:**
- Dry-run execution summary (date, branch, base commit, all participants as placeholders).
- Pre-ceremony gate results (all 7 validators confirmed PASS).
- Authorization URL design gate dry-run result (validator output, redacted input).
- Callback/token-exchange boundary gate dry-run result.
- Credential handoff protocol walkthrough result.
- Approval packet dry-run result.
- Evidence package (placeholder/redacted only).
- Aggregate assertion count.
- Dry-run verdict (PASS or FAIL).
- Explicit NOT APPROVED statements.
**No-real-execution constraint:** Documentation-only execution results. All inputs are placeholder labels. No real credentials. No OAuth. No GCP. No actual ceremony executed.
**Validation:** Document review. Safety grep clean. Dry-run execution validator PASS.

**Phase 4 Implementation Note:** `docs/V5_22_DRY_RUN_EXECUTION_RESULTS.md` created. Local dry-run execution result: PASS. 14 sections (A–N): scope; packet identity (9 redacted fields); participant placeholder results (11 roles, all PASS); target context results (7 placeholder references, all PASS); timed execution window results (12 fields, all PASS); pre-flight gate results (15 gates, all PASS); local validator evidence (610 assertions across 8 explicit-count demos, plus onboarding ceremony PASS and smoke suites 35/35 and 8/8 PASS); dry-run sequence results (24 steps G-01–G-24, all PASS); no-execution confirmations (16 items, all NO); evidence package result (10 allowed categories recorded, 17 forbidden categories absent); stop-condition review (21 conditions reviewed, none triggered); rollback rehearsal readiness (12 fields, all PASS); final dry-run decision (12 fields, PASS); Phase 4 conclusion. No real approval. No credentials. No OAuth. No auth URL. No browser. No callback URL. No auth code. No token exchange. No Secret Manager. No Google Ads API. No GCP. No deploy. `GOOGLE_ADS_LIVE_ENABLED` remains false. Phase 5 remains pending.

### Phase 5 — Stop-condition and rollback rehearsal results
**Deliverables:** `docs/V5_22_STOP_AND_ROLLBACK_REHEARSAL_RESULTS.md`
**Contents:**
- Stop-condition walkthrough for all H1–H25 conditions from the dry-run runbook.
- Each condition: description, simulated trigger (or "not triggered — condition clear"), expected system response, rehearsal outcome (PASS / NOT APPLICABLE).
- Rollback/emergency revoke rehearsal for all R1–R12 steps.
- Each step: description, rehearsal action, rehearsal outcome.
- Rehearsal verdict.
- Explicit confirmations: no real revoke, no real Secret Manager, no real credentials, no real approval revocation.
**No-real-execution constraint:** Documentation-only rehearsal results. No real revoke. No real Secret Manager. No real credentials.
**Validation:** Document review. Safety grep clean.

**Phase 5 Implementation Note:** `docs/V5_22_STOP_AND_ROLLBACK_REHEARSAL_RESULTS.md` created. Documentation-only local rehearsal. 10 sections (A–J): rehearsal scope; source artifacts reviewed (9 artifacts, all PASS); stop-condition walkthrough (26 conditions H-01–H-26, all rehearsal result PASS, no condition triggered, no real action performed); stop procedure rehearsal (12 steps D-01–D-12, all PASS); rollback rehearsal results (16 fields R-01–R-16, all confirmed PASS or YES); emergency revoke rehearsal (10 checklist items, all PASS, no-real-state walkthrough only); post-stop safety validation (safety grep CLEAN, smoke 35/35 and 8/8 PASS, dry-run execution demo 112 PASS, rollback drill demo 67 PASS, secret version policy demo 71 PASS); no-real-state confirmation (15 items, all NO); rehearsal decision (PASS, `<reviewer_label>` / `<verifier_label>` sign-off, not approved for real OAuth); Phase 5 conclusion. Rehearsal result PASS. No real stop triggered. No real rollback/revoke performed. No real approval, credentials, OAuth, auth URL, browser, callback URL, auth code, token exchange, Secret Manager, Google Ads API, GCP, deploy, or live flag activation. Phase 6 remains pending.

### Phase 6 — Final dry-run review and gap analysis
**Deliverables:** `docs/V5_22_FINAL_DRY_RUN_REVIEW.md`
**Contents:**
- Overall dry-run verdict (PASS or FAIL with gap analysis if FAIL).
- Review of each V5.22 phase result.
- Gap analysis: any ceremony step that could not be rehearsed with placeholder-only inputs.
- Aggregate assertion count across all validators and demos.
- Smoke suite results.
- Pre-execution checklist status (G1–G21 from V5.21).
- Explicit NOT APPROVED statements.
- Conditions required before a real ceremony could be authorized (deferred to future branch).
**No-real-execution constraint:** Documentation-only final review. Not an approval for real OAuth.
**Validation:** Document review. Safety grep clean. All smoke suites PASS.

**Phase 6 Implementation Note:** `docs/V5_22_FINAL_DRY_RUN_REVIEW.md` created. Documentation-only final review. 12 sections (A–L): review scope; phase-by-phase review (Phases 1–6, all PASS, all NOT PERFORMED); artifact inventory (10 artifacts); validation evidence summary (610 explicit assertions across 7 counted demos, onboarding ceremony PASS, smoke suites 35/35 and 8/8 PASS, safety grep CLEAN); dry-run completeness review (14 elements all PASS); no-execution boundary review (17 confirmations all NO); security and redaction review (14 sensitive categories all absent); gap analysis (16 gaps G-01–G-16 documented); required conditions before real ceremony (13 conditions required); NOT APPROVED statements (16 explicitly NOT APPROVED actions); final Phase 6 decision (dry-run readiness PASS, local controls PASS, documentation package PASS, no-execution boundary PASS, real ceremony authorization NOT GRANTED, final decision PASS dry-run only); Phase 6 conclusion. Final dry-run verdict PASS. Aggregate validation evidence 610 explicit assertions. NOT APPROVED statements recorded. Remaining gaps listed. No real approval, credentials, OAuth, auth URL, browser, callback URL, auth code, token exchange, Secret Manager, Google Ads API, GCP, deploy, rollback/revoke, or live flag. Commit `d42d6e2`.

**Phase 7 Implementation Note:** `docs/V5_22_BRANCH_CLOSURE.md` and `docs/RELEASE_NOTES_V5_22_0_BETA.md` created. Branch closure document: 12 sections (A–L); closure status READY FOR PHASE 8 AUTHORIZATION; phase completion matrix (Phases 1–6 PASS with commits, Phase 7 pending commit, Phase 8 pending authorization); 9 files added; 7 files modified; validation evidence (610 aggregate assertions, smoke 35/35 and 8/8 PASS, safety grep PASS); 7 dry-run artifacts summary; 21 security confirmations; 16 NOT APPROVED boundaries; 16 remaining gaps (G-01–G-16); Phase 8 requirements; closure decision READY FOR MERGE/TAG/RELEASE AUTHORIZATION ONLY. Release notes: 10 sections (A–J); release candidate `v5.22.0-beta`; READY FOR RELEASE (Phase 8 authorization required); real ceremony NOT GRANTED. README and ROADMAP updated. No merge performed. No tag created. No push. No GitHub Release. No real credentials. No OAuth. No GCP. No deploy. `GOOGLE_ADS_LIVE_ENABLED` remains false. Phase 8 remains pending explicit authorization.

### Phase 7 — Branch closure docs and release notes
**Deliverables:** `docs/V5_22_BRANCH_CLOSURE.md` · `docs/RELEASE_NOTES_V5_22_0_BETA.md`
**Contents:** Standard closure format (phase matrix, files added/modified, validator evidence, security confirmations, release decision, deferred items, Phase 8 requirements).
**No-real-execution constraint:** Documentation-only. No merge/tag/release in this phase.
**Validation:** Document review. Safety grep clean. Smoke tests PASS.

### Phase 8 — Merge, tag, release
**Requires explicit operator authorization before execution.**
**Actions:** Merge to master. Tag `v5.22.0-beta`. Push master and tag. Publish GitHub Release.
**Constraints:** No deploy. No GCP. No OAuth. No credentials. No API. No live flag.

---

## E. Acceptance Criteria

| Criterion | Phase |
|---|---|
| V5.22 implementation plan exists | 1 |
| Dry-run packet template exists | 2 |
| Dry-run execution validator exists and all demos PASS | 3 |
| Dry-run packet execution results exist | 4 |
| Stop/rollback rehearsal results exist | 5 |
| Final dry-run review exists and verdict is PASS | 6 |
| Branch closure and release notes exist | 7 |
| Smoke tests PASS (34/34 and 8/8) | 1–7 |
| Safety greps CLEAN throughout | 1–7 |
| No real credentials at any phase | 1–8 |
| No OAuth executed at any phase | 1–8 |
| No real auth URL generated at any phase | 1–8 |
| No browser opened at any phase | 1–8 |
| No real callback URL received at any phase | 1–8 |
| No real auth code received at any phase | 1–8 |
| No token exchange attempted at any phase | 1–8 |
| No Secret Manager called at any phase | 1–8 |
| No Google Ads API called at any phase | 1–8 |
| No GCP command or API used at any phase | 1–8 |
| No deploy at any phase | 1–8 |
| `GOOGLE_ADS_LIVE_ENABLED` not activated at any phase | 1–8 |

---

## F. Required Safety Checks

The following safety checks are performed at each phase:

| Check | Tool | Expected result |
|---|---|---|
| `ya29.` OAuth token prefix | `grep` | No hits with real token values |
| `sk-` API key prefix | `grep` | No hits |
| `GOOGLE_APPLICATION_CREDENTIALS=/` | `grep` | No hits |
| `credential_ref.*projects/` | `grep` | No hits |
| `secret_id.*projects/` | `grep` | No hits |
| `customer_id.*[0-9]` | `grep` | No hits |
| `login_customer_id.*[0-9]` | `grep` | No hits |
| `auth code.*[A-Za-z0-9_-]{10,}` | `grep` | No hits with real values |
| `https://accounts.google.com/o/oauth2` | `grep` | No hits |
| `GOOGLE_ADS_LIVE_ENABLED=true` | `grep` | Prohibition text only, not runtime setting |
| Forbidden imports in new validators | `grep` | `google.cloud`, `google.ads`, `requests`, `urllib`, `httpx`, `webbrowser`, `subprocess`, `socket` all absent |
| Smoke suite — credentials | `smoke_test_v5_credentials.sh` | 34/34 PASS (or higher after Phase 3 adds a section) |
| Smoke suite — GCP | `smoke_test_v5_12_gcp_secret_manager.sh` | 8/8 PASS |
| Untracked secret-bearing files | `git status` | No `.env`, no credential JSON, no token files |

---

## G. Stop Conditions

The following conditions require an immediate stop:

| Code | Condition |
|---|---|
| G-01 | Any real credential value (token, secret, key) appears in any file |
| G-02 | Any real OAuth authorization URL appears in any file or output |
| G-03 | A browser is opened as part of any step |
| G-04 | Any real auth code appears in any file, output, or log |
| G-05 | Token exchange is attempted against any endpoint |
| G-06 | Secret Manager is called (read or write) |
| G-07 | Google Ads API is called |
| G-08 | Any GCP command or API is invoked |
| G-09 | A real participant identity (name, email, ID) appears in an approval or packet |
| G-10 | Any real tenant ID, client ID, customer ID, or project ID appears |
| G-11 | Safety grep produces a sensitive hit |
| G-12 | Any smoke suite section fails (after retry for known WSL2 transient) |
| G-13 | Dry-run execution packet is structurally incomplete |
| G-14 | Timed execution window parameters are missing |
| G-15 | Rollback owner is missing from packet |
| G-16 | Emergency revoke owner is missing from packet |
| G-17 | Evidence owner is missing from packet |
| G-18 | Stop authority is missing from packet |

---

## H. Deferred Beyond V5.22

The following items are explicitly outside V5.22 scope:

1. Real OAuth approval (written by a human operator with real identity)
2. Real OAuth browser ceremony (live consent flow)
3. Real credential handoff (actual refresh token, access token, client secret)
4. Real auth code handling (live redirect URI callback)
5. Real token exchange (calling Google OAuth token endpoint)
6. Real Secret Manager write with OAuth output credentials
7. Real Google Ads API read-only validation
8. `GOOGLE_ADS_LIVE_ENABLED=true` runtime activation
9. Production Cloud Run or other deployment
10. IAM hardening or Service Account key rotation
11. External approval UI or ticketing integration
12. Multi-client or multi-tenant onboarding
13. Billing account validation or budget alert configuration
14. GCP project resource path configuration for production secrets

---

## I. Phase 1 Conclusion

Phase 1 is complete with the creation of this document and the associated README and ROADMAP updates.

- Branch `v5.22-controlled-real-oauth-ceremony-dry-run` created from `master` at `dd67c4f`.
- V5.22 dry-run execution plan created in this file.
- No dry-run executed yet.
- No real OAuth, credentials, GCP, or API work performed.
- Phase 2 (dry-run execution packet template) remains pending.

**`GOOGLE_ADS_LIVE_ENABLED` remains false. No real OAuth was executed. No real credentials were used.**

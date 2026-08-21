# Google Ads OAuth Ceremony Checklist — V5.21 Controlled Onboarding

**Kaiju Command Center — V5.21 Phase 2**

**Branch:** `v5.21-controlled-real-google-ads-oauth-onboarding`

---

> **WARNING — READ BEFORE USING THIS DOCUMENT**
>
> - This checklist is **documentation-only**. It does not authorize real OAuth execution.
> - This checklist does not authorize real credential intake.
> - This checklist does not authorize Google Ads API calls.
> - This checklist does not authorize Secret Manager writes.
> - This checklist does not authorize GCP operations.
> - This checklist does not authorize `GOOGLE_ADS_LIVE_ENABLED=true`.
> - **All real execution requires separate explicit operator approval.**
> - **Do not paste credentials, OAuth URLs, auth codes, or tokens into chat** (Claude, ChatGPT, Slack, GitHub, or any observed session).
> - **Do not commit any real credential value, OAuth code, token, resource path, customer ID, project ID, or account email** to this repository.
> - **Do not print tokens, refresh tokens, or client secrets** to any terminal with screen recording or shared access.
> - **Do not call the Google Ads API** until a separate explicit operator approval is recorded, signed, and not expired.
> - **`GOOGLE_ADS_LIVE_ENABLED` must remain `false`** until final separately authorized execution.
> - **Any ceremony step must stop immediately** if secret leakage, unexpected OAuth behavior, or missing rollback evidence is detected.

---

## A. Ceremony Purpose

This checklist defines the operator-controlled ceremony required before any future Google Ads OAuth onboarding can occur. It converts V5.20's readiness controls into an execution-safe ceremony structure — but does not execute the ceremony.

The checklist serves as a prerequisite template. An authorized future execution operator must complete each section in sequence, confirm all items, and capture all evidence in a redacted evidence package stored outside the repository. No field in this document may be populated with a real credential, token, OAuth code, resource path, or account identifier.

V5.21 Phase 2 creates this checklist. It does not execute the ceremony. No OAuth URL was generated. No browser flow was opened. No real credentials were requested or used.

---

## B. Ceremony Participants and Roles

All role assignments must be confirmed before the ceremony window opens. Use redacted labels only in this document; real operator names belong in the approval record stored outside the repository.

| Role | Label | Confirmed |
|------|-------|-----------|
| Primary operator | `<operator_label>` | [ ] |
| Secondary reviewer | `<reviewer_label>` | [ ] |
| Approval owner | `<approval_owner_label>` | [ ] |
| OAuth execution operator | `<oauth_operator_label>` | [ ] |
| Credential handling owner | `<credential_handler_label>` | [ ] |
| Secret storage owner | `<storage_owner_label>` | [ ] |
| Rollback owner | `<rollback_owner_label>` | [ ] |
| Emergency revoke owner | `<revoke_owner_label>` | [ ] |
| Evidence owner | `<evidence_owner_label>` | [ ] |
| Post-ceremony verifier | `<verifier_label>` | [ ] |
| Stop authority | `<stop_authority_label>` | [ ] |

All roles identified and confirmed before ceremony window opens: [ ] YES — proceed to Section C  /  [ ] NO — do not proceed

---

## C. Preconditions

All preconditions must be confirmed before the ceremony window opens. All items must be checked by the authorizing operator.

| # | Item | Verified |
|---|---|---|
| C1 | V5.20 onboarding checklist (`docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md`) reviewed | [ ] |
| C2 | V5.20 final readiness review (`docs/V5_20_FINAL_READINESS_REVIEW.md`) reviewed | [ ] |
| C3 | V5.21 implementation plan (`docs/V5_21_IMPLEMENTATION_PLAN.md`) reviewed | [ ] |
| C4 | V5.21 OAuth ceremony checklist (this document) reviewed | [ ] |
| C5 | Approval record exists and is stored outside the repository | [ ] |
| C6 | Approval scope matches OAuth onboarding operation | [ ] |
| C7 | Approval status is APPROVED and not expired | [ ] |
| C8 | Approval countersignatures are complete | [ ] |
| C9 | Tenant ref and client ref are redacted in all committed docs | [ ] |
| C10 | OAuth app/client configuration reviewed out-of-band | [ ] |
| C11 | Required OAuth scopes defined out-of-band and on record | [ ] |
| C12 | Redirect URI reviewed out-of-band | [ ] |
| C13 | Credential intake boundary reviewed (`openclaw/credential_intake.py` PASS) | [ ] |
| C14 | Rollback drill validator PASS (`openclaw/rollback_drill.py`) | [ ] |
| C15 | Secret version lifecycle policy validator PASS (`openclaw/secret_version_policy.py`) | [ ] |
| C16 | `scripts/smoke_test_v5_credentials.sh` PASS immediately before ceremony window | [ ] |
| C17 | `scripts/smoke_test_v5_12_gcp_secret_manager.sh` PASS immediately before ceremony window | [ ] |
| C18 | Safety grep CLEAN on all ceremony-modified files | [ ] |
| C19 | Audit enabled and audit file writable confirmed | [ ] |
| C20 | Emergency revoke path confirmed and tested dry | [ ] |
| C21 | Execution window start and end time defined | [ ] |
| C22 | Stop authority confirmed and reachable | [ ] |
| C23 | Rollback owner confirmed and reachable | [ ] |
| C24 | Evidence package storage path defined outside repository | [ ] |

**Preconditions result:** [ ] ALL PASS — proceed to Section D  /  [ ] BLOCKED — do not proceed

---

## D. Authorization URL Review Gate

**Phase 2 status: Authorization URL generation is not performed in this phase.**

**Phase 3 note:** `openclaw/oauth_auth_url.py` implements a local-only design validator (`validate_oauth_auth_url_design()`) that checks all preconditions for this gate — redirect URI approval, scope approval, state parameter safety, OAuth param design (prompt=consent, access_type=offline, include_granted_scopes=false), ceremony controls, and evidence/metadata cleanliness — without generating any real authorization URL. No real URL was generated. No browser was opened. No real credentials were used. Phase 3 validator passes all 34 demo test scenarios (82 assertions).

The following items define the review gate that must be satisfied before any future authorization URL is generated or opened. This gate must be completed immediately before the OAuth browser step in any future authorized ceremony.

| # | Item | Verified |
|---|---|---|
| D1 | Authorization URL generation is **not** performed in Phase 2 | [x] |
| D2 | Future authorization URL must be reviewed by secondary reviewer before opening | [ ] |
| D3 | URL must use the approved OAuth client (reviewed out-of-band; not committed) | [ ] |
| D4 | URL must use the approved redirect URI (reviewed out-of-band; not committed) | [ ] |
| D5 | URL must request only the approved scopes — no additions | [ ] |
| D6 | URL must not be committed to repository | [ ] |
| D7 | URL must not be pasted into chat | [ ] |
| D8 | URL must not appear in logs, terminal history, or screen recordings | [ ] |
| D9 | URL must not contain unexpected query parameters | [ ] |
| D10 | URL must be discarded after ceremony — not stored in docs or files | [ ] |
| D11 | URL review ambiguity is a stop condition | [ ] |

**Authorization URL gate result (future ceremony only):** [ ] PASS — proceed to Section E  /  [ ] STOP — do not open URL

---

## E. OAuth Scope Confirmation Gate

**Phase 2 status: No real scopes are requested in this phase.**

The following items define scope confirmation that must occur before any real authorization URL is opened.

| # | Item | Verified |
|---|---|---|
| E1 | Required scopes are documented out-of-band and on record | [ ] |
| E2 | Requested scopes in authorization URL match approved scope list exactly | [ ] |
| E3 | No broad or extra scopes included beyond approved list | [ ] |
| E4 | Scope mismatch of any kind is a stop condition | [ ] |
| E5 | Scope list must not include account identifiers | [ ] |
| E6 | Scope approval evidence must be redacted before any commit | [ ] |
| E7 | Scope confirmation is repeated after browser consent screen is shown | [ ] |

**Scope gate result (future ceremony only):** [ ] PASS — proceed to Section F  /  [ ] STOP — halt ceremony

---

## F. Browser Execution Gate

**Phase 2 status: Browser OAuth execution is not performed in this phase.**

The following items define the browser execution gate for any future authorized ceremony.

| # | Item | Verified |
|---|---|---|
| F1 | Browser OAuth execution is **not** performed in Phase 2 | [x] |
| F2 | Future browser execution requires separate explicit operator approval | [ ] |
| F3 | Browser execution must occur only within the approved execution window | [ ] |
| F4 | Operator must verify the active Google account before proceeding past consent screen | [ ] |
| F5 | Operator must stop on unexpected Google account shown in browser | [ ] |
| F6 | Operator must stop on unexpected OAuth app name shown by Google | [ ] |
| F7 | Operator must stop on unexpected scopes shown on consent screen | [ ] |
| F8 | Operator must stop on any Google warning screen not previously reviewed | [ ] |
| F9 | No screenshots containing credentials, emails, or account data may be committed | [ ] |
| F10 | No OAuth result (auth code, redirect URL) may be pasted into chat | [ ] |
| F11 | Secondary reviewer must be present or reachable during browser execution | [ ] |

**Browser execution gate result (future ceremony only):** [ ] PASS — proceed to Section G  /  [ ] STOP — halt ceremony

---

## G. Callback and Auth-Code Handling Gate

**Phase 2 status: Callback and token exchange are not performed in this phase.**

The following items define auth-code handling requirements for any future authorized ceremony.

| # | Item | Verified |
|---|---|---|
| G1 | Callback and token exchange are **not** performed in Phase 2 | [x] |
| G2 | Future auth code must be handled only through approved secure channel | [ ] |
| G3 | Auth code must not be committed to repository | [ ] |
| G4 | Auth code must not be logged to file or terminal | [ ] |
| G5 | Auth code must not be pasted into chat | [ ] |
| G6 | Auth code must not be stored in shell history | [ ] |
| G7 | Auth code must not appear in any committed document | [ ] |
| G8 | Auth code must not be transmitted via unapproved channel (email, Slack, SMS) | [ ] |
| G9 | Auth code handling ambiguity of any kind is a stop condition | [ ] |
| G10 | Auth code must be consumed immediately — no storage for later use | [ ] |

**Callback/auth-code gate result (future ceremony only):** [ ] PASS — proceed to Section H  /  [ ] STOP — halt ceremony

---

## H. Token Exchange Boundary Gate

**Phase 2 status: Token exchange is not performed in this phase.**

The following items define token exchange boundary requirements for any future authorized ceremony.

| # | Item | Verified |
|---|---|---|
| H1 | Token exchange is **not** performed in Phase 2 | [x] |
| H2 | Future token exchange requires separate explicit operator approval | [ ] |
| H3 | Refresh token must never be printed to terminal, log, or doc | [ ] |
| H4 | Access token must never be printed to terminal, log, or doc | [ ] |
| H5 | Client secret must never be printed to terminal, log, or doc | [ ] |
| H6 | Token response payload must not be committed to repository | [ ] |
| H7 | Token response payload must not be pasted into chat | [ ] |
| H8 | Token exchange must be immediately followed by redacted status verification only | [ ] |
| H9 | Token exchange failure of any kind is a stop condition | [ ] |
| H10 | Unexpected token response fields are a stop condition | [ ] |
| H11 | Credential handling owner must be present at token exchange step | [ ] |

**Token exchange gate result (future ceremony only):** [ ] PASS — proceed to Section I  /  [ ] STOP — halt ceremony

---

## I. Credential Storage Gate

**Phase 2 status: Real Secret Manager write is not performed in this phase.**

The following items define credential storage requirements for any future authorized ceremony.

| # | Item | Verified |
|---|---|---|
| I1 | Real Secret Manager write is **not** performed in Phase 2 | [x] |
| I2 | Future storage requires separate explicit operator approval | [ ] |
| I3 | Storage target (secret name/path) must be approved before ceremony opens | [ ] |
| I4 | Secret version lifecycle policy validator PASS confirmed immediately before storage step | [ ] |
| I5 | Previous version handling must follow V5.20 `DISABLE_PREVIOUS_WITH_GRACE_PERIOD` policy | [ ] |
| I6 | Storage response must be verified by field count only — no raw response committed | [ ] |
| I7 | Raw resource paths must not be committed to repository | [ ] |
| I8 | Credential ref and resource path must not be pasted into chat | [ ] |
| I9 | Storage ambiguity of any kind is a stop condition | [ ] |
| I10 | Storage owner must verify response status before ceremony continues | [ ] |
| I11 | Audit event must be emitted and verified after storage step | [ ] |

**Credential storage gate result (future ceremony only):** [ ] PASS — proceed to Section J  /  [ ] STOP — halt ceremony

---

## J. Google Ads API Boundary Gate

**Phase 2 status: Google Ads API is not called in this phase.**

The following items define the API boundary for any future authorized ceremony.

| # | Item | Verified |
|---|---|---|
| J1 | Google Ads API is **not** called in Phase 2 | [x] |
| J2 | Future API validation requires separate explicit operator approval beyond OAuth ceremony | [ ] |
| J3 | OAuth success does not imply approval to call the Google Ads API | [ ] |
| J4 | First API call must be read-only | [ ] |
| J5 | First API call must follow V5.20 first live API validation plan (`docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md`) | [ ] |
| J6 | Unexpected API response of any kind is a stop condition | [ ] |
| J7 | API response payload must be redacted before any commit or log | [ ] |
| J8 | Customer IDs and login customer IDs must not be committed to repository | [ ] |
| J9 | API error codes must be reviewed by secondary reviewer before any retry | [ ] |

**Google Ads API gate result (future ceremony only):** [ ] PASS — ceremony complete  /  [ ] STOP — halt ceremony

---

## K. Evidence Package

The evidence package must be assembled by the evidence owner and stored outside the repository. All fields must be redacted. No real credential values, resource paths, customer IDs, project IDs, or account emails may appear in any committed evidence document.

| Evidence item | Required content | Committed form |
|---|---|---|
| Approval status summary | Approval ref, status, expiry | Redacted ref only (`<approval_ref>`) |
| Checklist completion summary | All sections A–N status | PASS/FAIL per section |
| Ceremony start and end time | Actual times | Redacted (`<timestamp_redacted>`) |
| Operators present | All role labels | `<operator_label>` etc. |
| Tenant and client refs | Actual refs | Redacted (`<tenant_ref>`, `<client_ref>`) |
| Authorization URL review | URL reviewed — PASS/FAIL | PASS or FAIL only — no URL |
| Scope review | Scopes confirmed — PASS/FAIL | PASS or FAIL only — no scope list with account data |
| Callback handling | Auth code handled — PASS/FAIL | PASS or FAIL only — no auth code |
| Token exchange | Exchange result — PASS/FAIL | PASS or FAIL only — no token payload |
| Credential storage | Storage result — PASS/FAIL | PASS or FAIL only — no resource path |
| Smoke test results | Both suites result | 31/31 PASS · 8/8 PASS (or current) |
| Safety grep result | Grep status | CLEAN or FAIL |
| Rollback readiness | Rollback path confirmed | CONFIRMED or NOT CONFIRMED |
| Live flag final state | `GOOGLE_ADS_LIVE_ENABLED` state | `false` (or actual if authorized) |

---

## L. Stop Conditions

Any of the following conditions require an immediate halt. Do not continue to the next ceremony step. Initiate Section M rollback sequence immediately.

| # | Stop condition |
|---|---|
| L1 | Real secret, token, credential value, or GCP resource path appears in chat, repo, logs, or any committed doc |
| L2 | OAuth authorization URL appears in any committed document |
| L3 | Auth code appears anywhere outside the approved secure channel |
| L4 | Refresh token appears anywhere |
| L5 | Access token appears anywhere |
| L6 | Client secret appears anywhere |
| L7 | Customer ID or login customer ID appears in any committed document |
| L8 | GCP project ID, project number, or resource path appears in any committed document |
| L9 | Approval record missing, expired, revoked, or incorrect scope |
| L10 | Tenant or client identifier mismatch |
| L11 | Unexpected Google account shown in browser |
| L12 | Unexpected OAuth app name shown by Google |
| L13 | Unexpected or extra scopes shown on consent screen |
| L14 | Any Google warning screen not previously reviewed |
| L15 | Token exchange ambiguity or unexpected response |
| L16 | Secret Manager storage ambiguity or unexpected response |
| L17 | `GOOGLE_ADS_LIVE_ENABLED` cannot be confirmed as reverted to `false` |
| L18 | Smoke test fails |
| L19 | Safety grep fails |
| L20 | Audit disabled or audit chain verification fails |
| L21 | Rollback owner unreachable |
| L22 | Emergency revoke owner unreachable |
| L23 | Evidence capture fails for any ceremony step |
| L24 | Any ceremony step exceeds its allotted time without operator approval to continue |
| L25 | Stop authority declares halt for any reason |

---

## M. Rollback and Emergency Revoke Sequence

**Phase 2 status: No rollback action is executed in this phase. This sequence is documentation-only.**

In any future authorized ceremony where a stop condition is triggered, execute the following sequence in order:

| Step | Action | Owner |
|------|--------|-------|
| M1 | Stop ceremony — do not continue to next step | Stop authority |
| M2 | Do not continue OAuth, API, or storage steps | All operators |
| M3 | If live flag was activated: immediately set `GOOGLE_ADS_LIVE_ENABLED=false` | Rollback owner |
| M4 | Revoke approval record — set status to REVOKED in `LocalFileApprovalStore` | Approval owner |
| M5 | If credential reference was created: mark status REVOKED in credential store | Credential handling owner |
| M6 | If secret bundle was written: execute `DELETE /credentials/google-ads` (requires `OPENCLAW_ADMIN_DELETE_ENABLED=true`) | Storage owner |
| M7 | Run `validate_rollback_drill()` and confirm PASS | Rollback owner |
| M8 | Run `check_live_gate()` and confirm denial | Post-ceremony verifier |
| M9 | Run safety grep — confirm CLEAN | Evidence owner |
| M10 | Run both smoke suites — confirm PASS | Evidence owner |
| M11 | Verify audit chain with `verify_audit_file()` | Evidence owner |
| M12 | Document final state in redacted evidence package | Evidence owner |
| M13 | Notify stop authority that rollback is complete | Rollback owner |

All rollback actions must be logged in the evidence package with timestamps and operator labels (redacted). No credential values or resource paths may appear in the rollback evidence.

---

## N. Sign-Off Block

**Phase 2 status: No sign-off is collected in this phase. This block is a documentation template for future authorized ceremonies.**

All sign-offs must use redacted labels only. Real operator names belong in the approval record stored outside the repository.

| Role | Label | Timestamp | Status |
|------|-------|-----------|--------|
| Primary operator | `<operator_label>` | `<timestamp_redacted>` | [ ] Signed |
| Secondary reviewer | `<reviewer_label>` | `<timestamp_redacted>` | [ ] Signed |
| Approval owner | `<approval_owner_label>` | `<timestamp_redacted>` | [ ] Signed |
| Rollback owner | `<rollback_owner_label>` | `<timestamp_redacted>` | [ ] Signed |
| Emergency revoke owner | `<revoke_owner_label>` | `<timestamp_redacted>` | [ ] Signed |
| Evidence owner | `<evidence_owner_label>` | `<timestamp_redacted>` | [ ] Signed |
| Final verifier | `<verifier_label>` | `<timestamp_redacted>` | [ ] Signed |

Evidence package reference: `<evidence_ref>`
Approval record reference: `<approval_ref>`

---

## O. Phase 2 Conclusion

**V5.21 Phase 2 result:**

- [x] OAuth ceremony checklist created.
- [x] No OAuth authorization URL generated.
- [x] No browser OAuth flow opened.
- [x] No real credentials requested or used.
- [x] No Google Ads API calls.
- [x] No GCP or Secret Manager calls.
- [x] No live flag activation.
- [x] No real auth codes, tokens, client secrets, resource paths, customer IDs, or project IDs in this document.
- [x] Checklist is prerequisite documentation only.
- [x] All real execution requires separate explicit operator approval.

This checklist must be reviewed and all items checked before any future authorized OAuth ceremony can proceed. Completion of this document does not constitute authorization for any real execution path.

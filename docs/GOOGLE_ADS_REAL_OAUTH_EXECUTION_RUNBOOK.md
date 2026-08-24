# Google Ads Real OAuth Execution Runbook — V5.23 Controlled Ceremony

**Kaiju Command Center — V5.23 Phase 4**

**Branch:** `v5.23-controlled-real-oauth-execution-planning`
**Base:** `v5.22.0-beta` / master merge commit `4217652`

---

> **WARNING — READ BEFORE USING THIS DOCUMENT**
>
> - This is a **runbook template only**.
> - This document **does not authorize real OAuth execution.**
> - This document **does not create a real approval.**
> - **No real credential value** (developer token, client ID, client secret, access token, refresh token, auth code, callback URL, OAuth URL) may be entered in this file.
> - **No real OAuth authorization URL** may be entered in this file.
> - **No callback URL** may be entered in this file.
> - **No auth code** may be entered in this file.
> - **No token** (access or refresh) may be entered in this file.
> - **No Secret Manager path** (`projects/.../secrets/.../versions/...`) may be entered in this file.
> - **No Google Ads customer ID or login customer ID** may be entered in this file.
> - **No GCP project ID, project number, or service account email** may be entered in this file.
> - **No real operator name, email, or account identifier** may be entered in this file.
> - **All fields must remain placeholder-only** in the committed form.
> - Real values (if any are needed for a future authorized live ceremony) belong in the out-of-repository approval record and the out-of-repository evidence store — never in this file, never in git, never in chat, never in logs.

---

## A. Runbook Purpose

This runbook converts the V5.22 dry-run procedure (`docs/GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md`, `docs/GOOGLE_ADS_OAUTH_DRY_RUN_EXECUTION_PACKET.md`) into a future real-execution operator runbook for V5.23.

It defines:

- Ceremony windows and pause points.
- Per-step approval requirements (bound to the V5.23 Phase 2 A1–A10 authorization packet).
- Stop conditions that halt the ceremony at any point.
- Rollback and emergency-revoke ownership.
- Post-execution verification with redacted evidence only.
- Final go/no-go criteria that must be PASS immediately before any live activity.

It **does not** authorize execution. A live step is authorized only when the corresponding exact Section E phrase from `docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md` is captured verbatim through the approved out-of-repository channel, the Section F pre-execution gate checklist here is PASS in full, and no Section I stop condition is triggered.

**Purpose in one sentence:** provide the future authorized operator an unambiguous, step-by-step, verify-then-act runbook that treats every real value in transit as radioactive, treats every pause point as a fresh authorization surface, and treats every stop condition as absolute.

---

## B. Non-Authorization Statement

V5.23 Phase 4 does **not** authorize any of the following:

- Real OAuth execution.
- Real credential handoff.
- Real approval creation.
- Real OAuth authorization URL generation.
- Browser OAuth flow.
- Callback URL receipt.
- Auth code receipt.
- Token exchange.
- Token response receipt.
- Credential storage.
- Secret Manager write.
- Google Ads API call.
- GCP command or GCP API call.
- Deploy.
- IAM changes, API enablement, or billing changes.
- `GOOGLE_ADS_LIVE_ENABLED=true` runtime activation.
- Real rollback or real credential revocation.

None of the above may occur in Phase 4. Writing or committing this runbook is not authorization. Reviewing or approving this runbook is not authorization for any live step.

---

## C. Ceremony Identity

The following fields identify the ceremony instance. All values in committed form must remain placeholders. Real values belong in the out-of-repository approval record.

| Field | Committed value | Real value stored |
|---|---|---|
| Ceremony reference | `<ceremony_ref>` | Out-of-repo approval record |
| Packet reference | `<packet_ref>` | Out-of-repo approval record |
| Intake protocol reference | `<intake_protocol_ref>` | Out-of-repo approval record |
| Tenant reference | `<tenant_ref>` | Out-of-repo approval record |
| Client reference | `<client_ref>` | Out-of-repo approval record |
| Target integration | `google_ads` | — (literal) |
| Milestone | `V5.23` | — (literal) |
| Branch | `v5.23-controlled-real-oauth-execution-planning` | — (literal) |
| Baseline release | `v5.22.0-beta` | — (literal) |
| Baseline merge commit | `4217652` | — (literal) |
| Runbook status | `DRAFT` | Out-of-repo approval record |
| Evidence reference | `<evidence_ref>` | Out-of-repo evidence store |

### C.1 — Runbook status values

| Value | Meaning | Committable |
|---|---|---|
| `DRAFT` | Template state; no ceremony instance references this runbook | YES |
| `REVIEWED` | Reviewer has read the runbook, does not authorize execution | YES |
| `READY_TO_PROPOSE` | Phase 5 review completed; the runbook is a candidate for a future proposal | NO in this Phase 4 commit — reserved for a Phase 5 status transition after separate authorization |
| `REJECTED` | Runbook has been rejected; ceremony may not proceed | NO in this Phase 4 commit — reserved for a future post-review decision |

**Default committed status: `DRAFT`.** A commit that sets any other status is prohibited in Phase 4.

---

## D. Operator Roles

Every role below is filled by a specific human named only in the out-of-repository approval record. This document uses placeholder labels only.

| Role label | Required? | May see secrets? | May execute command? | May approve? | May stop? | Evidence responsibility |
|---|---|---|---|---|---|---|
| `<operator_label>` | YES | ONLY APPROVED CHANNEL | YES (per approved step) | NO | YES | Records each executed action in redacted form |
| `<reviewer_label>` | YES | ONLY APPROVED CHANNEL | NO | NO (may confirm continuation past pause; may not grant A1–A10) | YES | Countersigns every executed action |
| `<credential_owner_label>` | YES | YES (owns source; must not display) | NO (participates in transfer only) | NO | YES | Records channel-open and channel-close events in redacted form |
| `<secure_channel_owner_label>` | YES | ONLY APPROVED CHANNEL METADATA | NO | NO | YES | Records channel state (open/closed/preconditions met) in redacted form |
| `<secret_writer_label>` | YES (for A7) | ONLY APPROVED CHANNEL | YES (for A7 only, under exact phrase) | NO | YES | Records A7 write metadata (field-count-only, status boolean, redacted resource ref) |
| `<oauth_operator_label>` | YES (for A3, A4, A5) | ONLY APPROVED CHANNEL | YES (for A3–A5 only, under exact phrases) | NO | YES | Records OAuth step outcomes (PASS/FAIL/STOPPED) in redacted form |
| `<stop_authority_label>` | YES | NO (works from redacted status only) | NO | NO for A1–A10 grants; YES for halt/continue decisions | YES (supreme; may halt unilaterally) | Records halt decisions and rationale in redacted form |
| `<rollback_owner_label>` | YES (for A5–A9) | NO (works from redacted status only) | YES (for A10 rollback only, under exact phrase or documented emergency policy) | NO for A1–A9 grants; YES for A10 rollback under emergency policy | YES | Records rollback execution metadata in redacted form |
| `<emergency_revoke_owner_label>` | YES (for A6–A9) | NO (works from redacted status only) | YES (for A10 emergency revoke only) | NO for A1–A9 grants; YES for A10 emergency revoke under out-of-repo emergency policy | YES | Records revoke execution metadata in redacted form |
| `<evidence_owner_label>` | YES | ONLY APPROVED CHANNEL METADATA | NO | NO | YES (on evidence integrity failure) | Assembles the redacted evidence package; runs final safety grep |

### D.1 — Cross-cutting role rules

- Stop authority may halt without countersignature.
- No role may see a raw secret except through an approved channel and only when required by the specific step.
- No role may authorize its own step (self-authorization prohibited).
- Roles may be doubled by one human only if the approval record explicitly enumerates the doubling.
- Role attendance must be re-confirmed at each pause point in the G-sequence (Section G).

---

## E. Time-Boxed Execution Window

| Field | Committed value | Notes |
|---|---|---|
| Window reference | `<timebox_ref>` | Placeholder only. Real start/end times live in the out-of-repo approval record. |
| Proposed start | `<start_placeholder>` | Placeholder only. |
| Proposed end | `<end_placeholder>` | Placeholder only. |
| Max duration | `<duration_placeholder>` | Placeholder only. Recommended: bounded to the shortest window that fits the full G-sequence. |
| Freeze window before start | `<freeze_window_placeholder>` | Placeholder only. Recommended: no repo changes, no test runs against production dependencies, no team merges during the freeze. |
| Required pause points | `<pause_points_ref>` | References Section G pause points (after every executed A-step). |

### E.1 — Window rules

| Rule | Statement |
|---|---|
| E-R1 | **Expiry rule** — all approvals expire at window end. No authorized action may begin after the end timestamp; if it began before the end and is in flight when the end arrives, it must complete or STOP within the window. |
| E-R2 | **Extension rule** — no extension is permitted without explicit authorization captured through the approved out-of-repo channel. A new packet may be required if the extension crosses a policy threshold. |
| E-R3 | **Abort rule** — any STOP condition (Section I) aborts the window immediately. Post-abort, no A-step may proceed under the same packet. |
| E-R4 | **Restart rule** — restart requires a new authorization packet with fresh Section E phrases and a fresh dry-run PASS within the last 30 days per V5.23 Phase 2 Section G-C23. |
| E-R5 | **Freeze rule** — the freeze window before start must be observed; unexpected repo activity during the freeze is a stop condition. |
| E-R6 | **Attention rule** — the stop authority and reviewer must remain reachable throughout the window; interruption is a stop condition. |
| E-R7 | **No overlap rule** — two ceremony windows for the same tenant/client may not overlap; a fresh packet is required after any prior window closes. |
| E-R8 | **Post-window cool-down** — after any A-step completes, a mandatory cool-down (per pause point in Section G) applies before the next A-step may be requested. |

---

## F. Pre-Execution Gate Checklist

All items must be PASS in full **immediately before** any A-step is requested. Verification is at execution time; no item carries forward from a prior ceremony window.

| # | Check | Verified |
|---|---|---|
| F-01 | Branch confirmed (`v5.23-controlled-real-oauth-execution-planning` or the currently authorized ceremony branch) | [ ] |
| F-02 | Working tree clean (`git status --short` empty) | [ ] |
| F-03 | Latest baseline confirmed (`v5.22.0-beta` / merge `4217652` or later authorized baseline) | [ ] |
| F-04 | V5.23 Phase 1 complete (`docs/V5_23_IMPLEMENTATION_PLAN.md` present) | [ ] |
| F-05 | V5.23 Phase 2 complete (`docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md` present) | [ ] |
| F-06 | V5.23 Phase 3 complete (`docs/GOOGLE_ADS_REAL_CREDENTIAL_INTAKE_PROTOCOL.md` present) | [ ] |
| F-07 | Authorization packet present (out-of-repo reference resolves to a real packet instance) | [ ] |
| F-08 | Intake protocol reviewed and present | [ ] |
| F-09 | Packet status valid (`APPROVED_FOR_SPECIFIC_STEP` in out-of-repo store; committed status remains `DRAFT`) | [ ] |
| F-10 | Runbook status valid (`DRAFT` or `REVIEWED` for committed file; execution proceeds under out-of-repo `READY_TO_PROPOSE` status if Phase 5 has authorized it) | [ ] |
| F-11 | Target step named (exactly one from A1–A10) | [ ] |
| F-12 | Tenant/client placeholder scope confirmed via secure channel resolution | [ ] |
| F-13 | `<operator_label>` present | [ ] |
| F-14 | `<reviewer_label>` present | [ ] |
| F-15 | `<credential_owner_label>` present (for A2–A7) | [ ] |
| F-16 | `<secure_channel_owner_label>` present | [ ] |
| F-17 | `<oauth_operator_label>` present (for A3–A5) | [ ] |
| F-18 | `<stop_authority_label>` present and reachable | [ ] |
| F-19 | `<rollback_owner_label>` present and reachable (for A5–A9) | [ ] |
| F-20 | `<emergency_revoke_owner_label>` present and reachable (for A6–A9) | [ ] |
| F-21 | `<evidence_owner_label>` present | [ ] |
| F-22 | Exact authorization phrase captured for the requested step (verbatim per Section E of the Phase 2 packet) | [ ] |
| F-23 | Authorization unexpired (packet `<timebox_ref>` window end not reached) | [ ] |
| F-24 | Timebox open (Section E window rules E-R1–E-R8 verified) | [ ] |
| F-25 | Safety grep CLEAN across all 9 patterns on all files touched this window | [ ] |
| F-26 | All 8 demos PASS (dry-run execution, rollback drill, secret version policy, OAuth approval packet, OAuth callback, OAuth auth URL, credential intake, onboarding ceremony) | [ ] |
| F-27 | `smoke_test_v5_credentials.sh` PASS — 35/35 | [ ] |
| F-28 | `smoke_test_v5_12_gcp_secret_manager.sh` PASS — 8/8 | [ ] |
| F-29 | No `.env` file exists anywhere in the repository | [ ] |
| F-30 | No credential JSON file exists anywhere in the repository | [ ] |
| F-31 | No real secrets appear in docs, logs, or chat at execution time | [ ] |
| F-32 | Screen recording disabled on the operator's machine | [ ] |
| F-33 | Screenshots prohibited (operator agreement) | [ ] |
| F-34 | Clipboard controls confirmed (no clipboard-history sync; no cross-device clipboard during credential handling) | [ ] |
| F-35 | Shell history protection considered (history suppression enabled or terminal in secure mode) | [ ] |
| F-36 | Incident protocol visible or ready to invoke (Phase 3 Section M) | [ ] |
| F-37 | Rollback/revoke path owner reachable at execution time | [ ] |
| F-38 | `GOOGLE_ADS_LIVE_ENABLED` default is `false` (may only be `true` if A9 approved and window active) | [ ] |

Any `[ ]` left unchecked at execution time invalidates the pre-execution gate and blocks the A-step until the gate is re-verified.

---

## G. Execution Sequence Overview

The following sequence defines a future ceremony execution. **It is documentation only; no step is executed by writing or reviewing this runbook.** Each A-step is bracketed by an approval confirmation, an execution, and a mandatory pause point.

| Step | Action | Depends on |
|---|---|---|
| G1 | Open ceremony window (start timestamp reached; freeze window observed; roles confirmed) | Section E E-R5, Section F F-13–F-21 |
| G2 | Confirm packet status (`APPROVED_FOR_SPECIFIC_STEP`) and runbook status (`DRAFT`/`REVIEWED`/`READY_TO_PROPOSE`) | Section C C.1 |
| G3 | Confirm scope (tenant/client resolvable through secure channel) and timebox (window open) | Section F F-12, F-23, F-24 |
| G4 | Run safety grep (all 9 patterns CLEAN on files touched this window) | Section F F-25 |
| G5 | Run tests (all 8 demos PASS; smoke 35/35 PASS; smoke 8/8 PASS) | Section F F-26, F-27, F-28 |
| G6 | Confirm secure channel readiness (Phase 3 Section D preconditions met) | Section F F-16 |
| G7 | Confirm exact approval for A1 (Phase 2 Section E.1 phrase captured verbatim through out-of-repo channel) | Section F F-22 |
| G8 | Execute A1 (create real approval packet artifact in out-of-repo store) — **only if G7 authorized** | H.A1 card |
| G9 | Pause; capture G8 evidence in redacted form; countersign; verify no forbidden content committed | Section H.A1, Section M |
| G10 | Confirm exact approval for A2 (Phase 2 Section E.2 phrase captured verbatim) | Section F F-22 |
| G11 | Execute A2 (prepare secure credential handoff channel) — **only if G10 authorized** | H.A2 card |
| G12 | Pause; capture G11 evidence; countersign; verify | H.A2 |
| G13 | Confirm exact approval for A3 (Phase 2 Section E.3 phrase captured verbatim) | Section F F-22 |
| G14 | Execute A3 (generate real OAuth authorization URL) — **only if G13 authorized** | H.A3 card |
| G15 | Pause; capture G14 evidence; countersign; verify | H.A3 |
| G16 | Confirm exact approval for A4 (Phase 2 Section E.4 phrase captured verbatim) | Section F F-22 |
| G17 | Execute A4 (open browser OAuth flow) — **only if G16 authorized** | H.A4 card |
| G18 | Pause; capture G17 evidence; countersign; verify | H.A4 |
| G19 | Confirm exact approval for A5 (Phase 2 Section E.5 phrase captured verbatim) | Section F F-22 |
| G20 | Execute A5 (receive callback and handle auth code through approved secure channel) — **only if G19 authorized** | H.A5 card |
| G21 | Pause; capture G20 evidence; countersign; verify | H.A5 |
| G22 | Confirm exact approval for A6 (Phase 2 Section E.6 phrase captured verbatim) | Section F F-22 |
| G23 | Execute A6 (exchange auth code for tokens) — **only if G22 authorized** | H.A6 card |
| G24 | Pause; capture G23 evidence; countersign; verify | H.A6 |
| G25 | Confirm exact approval for A7 (Phase 2 Section E.7 phrase captured verbatim) | Section F F-22 |
| G26 | Execute A7 (store credential bundle in Secret Manager via V5.15 admin path) — **only if G25 authorized** | H.A7 card |
| G27 | Pause; capture G26 evidence; countersign; verify | H.A7 |
| G28 | Confirm exact approval for A8 (Phase 2 Section E.8 phrase captured verbatim) | Section F F-22 |
| G29 | Execute A8 (run first read-only Google Ads API validation) — **only if G28 authorized** | H.A8 card |
| G30 | Pause; capture G29 evidence; countersign; verify | H.A8 |
| G31 | Confirm exact approval for A9 (Phase 2 Section E.9 phrase captured verbatim) — **only if a decision has been made to activate a live flag** | Section F F-22 |
| G32 | Execute A9 (activate the explicitly named live flag) — **only if G31 authorized** | H.A9 card |
| G33 | Pause; capture G32 evidence; countersign; verify | H.A9 |
| G34 | Confirm exact approval for A10 if rollback/revoke needed (Phase 2 Section E.10 phrase captured verbatim, or documented emergency policy applies) | Section F F-22, Phase 3 Section I |
| G35 | Execute A10 (perform explicitly named rollback/revoke action) — **only if G34 authorized** | H.A10 card |
| G36 | Final safety grep (all 9 patterns CLEAN on all files touched during window) | Section F F-25 |
| G37 | Final evidence redaction review (Phase 3 Section J.3 procedure) | Phase 3 J.3 |
| G38 | Close ceremony window (record window-close timestamp; verify audit chain intact; hand off evidence to evidence owner) | Section E E-R1 |

### G.1 — Sequence rules

| Rule | Statement |
|---|---|
| G-R1 | **No step implies the next.** Each G-step gated by an approval confirmation must have its own captured Section E phrase before execution. |
| G-R2 | **No approval carries across steps** unless multiple steps are separately enumerated with individual phrases in the same authorization packet. |
| G-R3 | **No paused state may continue after window expiry.** If the window ends during a pause, the ceremony must abort; a new packet is required to resume. |
| G-R4 | **No step may be skipped without explicit authorization.** Skipping A1–A2 in favor of A3 is not permitted; the packet must sequence steps or provide justification in the out-of-repo record. |
| G-R5 | **Non-sequential steps (e.g., A10 rollback during A6)** may be authorized independently but must not be inserted silently; a pause + explicit approval capture is required. |
| G-R6 | **Every pause point requires an active countersignature** from the reviewer before the next G-step may be requested. Silent continuation is a stop condition. |

---

## H. Per-Step Execution Cards A1–A10

Each card below is a mini-runbook for one authorized step. Every card follows the same structure. **No card authorizes its step; each step requires its own Section E phrase from the Phase 2 packet.**

### H.A1 — Create Real Approval Packet

| Field | Value |
|---|---|
| Step ID | A1 |
| Purpose | Create a real approval packet artifact in the out-of-repository approval store, filled with real operator identities, real tenant/client scope, and named execution window. |
| Required exact authorization phrase | Phase 2 Section E.1 (`I authorize V5.23 step A1 only: create a real approval packet for <tenant_ref>/<client_ref> during <timebox_ref>. This does not authorize OAuth, credentials, token exchange, Secret Manager, Google Ads API, GCP, deploy, live flag, or rollback/revoke.`) |
| Required preconditions | F-01–F-14; approval owner present; approval record store writable out-of-repo. |
| Allowed action | Create packet instance in the out-of-repo approval store; fill real fields there; keep the committed repo template at status `DRAFT`. |
| Forbidden actions | Committing the filled packet to git; setting the committed status to `APPROVED_FOR_SPECIFIC_STEP`; naming real operators in any repo file. |
| Evidence allowed | `<packet_ref>` (redacted); status confirmation; timestamp placeholder. |
| Evidence forbidden | Real approval payload; real operator identities; real tenant/client IDs. |
| Stop if | Approval owner absent; out-of-repo store unavailable; any repo commit attempts to include real values. |
| Pause after step? | YES (G9). |
| Next step requires separate authorization? | YES. |

### H.A2 — Prepare Secure Credential Handoff Channel

| Field | Value |
|---|---|
| Step ID | A2 |
| Purpose | Prepare an approved secure channel (Phase 3 Section D.1–D.4) for future credential handoff. |
| Required exact authorization phrase | Phase 2 Section E.2 |
| Required preconditions | F-15–F-16; A1 completed; channel type selected from Phase 3 D.1–D.4. |
| Allowed action | Provision the channel with correct preconditions (password manager access grants, encrypted-transfer setup, terminal preparation) — no credentials transit yet. |
| Forbidden actions | Transferring credentials through the channel; testing the channel with a real credential; using a Phase 3 forbidden channel. |
| Evidence allowed | Channel-type label (`<pw_manager_item_ref>` / `<archive_ref>` / terminal-setup confirmation); readiness status. |
| Evidence forbidden | Any credential value; the channel's access credentials themselves; screenshots of the channel setup. |
| Stop if | Channel type not on D.1–D.4 approved list; preconditions not met; secure-channel owner absent. |
| Pause after step? | YES (G12). |
| Next step requires separate authorization? | YES. |

### H.A3 — Generate Real OAuth Authorization URL

| Field | Value |
|---|---|
| Step ID | A3 |
| Purpose | Generate the real OAuth authorization URL for the target tenant/client OAuth client. |
| Required exact authorization phrase | Phase 2 Section E.3 |
| Required preconditions | F-17; A1, A2 completed; `openclaw/oauth_auth_url.py` validator PASS on inputs; OAuth client (client_id, redirect_uri, scopes) pre-approved out-of-repo. |
| Allowed action | Invoke the URL construction using out-of-repo OAuth client parameters; capture the URL in a transient buffer only. |
| Forbidden actions | Committing the URL to git; pasting the URL into chat, log, or doc; opening the URL in a browser (that is A4); persisting the URL beyond A4 consumption. |
| Evidence allowed | URL generation status (PASS/FAIL); redacted URL reference (`<oauth_url_redacted>`); scope-match confirmation (booleans). |
| Evidence forbidden | The URL itself; the client_id; the redirect_uri; the scope list with account identifiers. |
| Stop if | Validator FAIL; client parameters unresolved; URL leaked to any forbidden channel; unexpected query parameters detected. |
| Pause after step? | YES (G15). |
| Next step requires separate authorization? | YES. |

### H.A4 — Open Browser OAuth Flow

| Field | Value |
|---|---|
| Step ID | A4 |
| Purpose | Open the browser to the A3-generated URL and complete the Google OAuth consent screen. |
| Required exact authorization phrase | Phase 2 Section E.4 |
| Required preconditions | F-17, F-32, F-33; A3 completed; browser prepared (private window, no extensions with credential access); active Google account verified out-of-band. |
| Allowed action | Open browser to A3 URL; verify Google account on screen; complete consent; observe redirect to the approved callback URI. |
| Forbidden actions | Screen recording; screen sharing; screenshotting any page; committing the browser URL bar contents; taking notes with real values. |
| Evidence allowed | Consent completion status (PASS/FAIL/STOPPED); Google account confirmation (boolean); scope match confirmation (boolean); redirect completion (boolean). |
| Evidence forbidden | The auth code visible in the redirect URL; the callback URL itself; any browser screenshot; any browser URL bar copy. |
| Stop if | Wrong Google account shown; unexpected OAuth app name; unexpected scopes on consent; any Google warning screen not previously reviewed; screen recording on. |
| Pause after step? | YES (G18). |
| Next step requires separate authorization? | YES. |

### H.A5 — Receive Callback and Handle Auth Code

| Field | Value |
|---|---|
| Step ID | A5 |
| Purpose | Receive the OAuth callback from A4 and route the auth code into the approved secure channel for A6 consumption. |
| Required exact authorization phrase | Phase 2 Section E.5 |
| Required preconditions | F-19; A4 completed; secure channel from A2 open; `openclaw/oauth_callback.py` validator PASS on inputs; auth code handling path pre-approved. |
| Allowed action | Route the auth code from the callback into the approved secure channel; consume the callback URL immediately without persistence. |
| Forbidden actions | Committing the auth code or callback URL; pasting either into chat/log/doc; storing the auth code for later; logging the callback URL. |
| Evidence allowed | Callback received (boolean); auth code routed to secure channel (boolean); channel receipt confirmation. |
| Evidence forbidden | The auth code; the callback URL; the redirect target; any URL bar screenshot. |
| Stop if | Auth code appears in any forbidden channel; callback URL logged; secure channel not open; validator FAIL; auth code not consumed within window. |
| Pause after step? | YES (G21). |
| Next step requires separate authorization? | YES. |

### H.A6 — Exchange Auth Code for Tokens

| Field | Value |
|---|---|
| Step ID | A6 |
| Purpose | Exchange the A5-received auth code with the Google OAuth token endpoint for refresh and access tokens. |
| Required exact authorization phrase | Phase 2 Section E.6 |
| Required preconditions | F-20; A5 completed; auth code still valid (not expired, single-use not yet consumed); rollback owner present; emergency revoke owner present. |
| Allowed action | Invoke the token endpoint with the auth code and client credentials (from A2 channel); receive the token response into a transient buffer; hand the token bundle to A7 immediately without persistence. |
| Forbidden actions | Committing the token response; pasting the token bundle into chat/log/doc; storing the token bundle in any local file; retrying the exchange without rollback owner confirmation. |
| Evidence allowed | Exchange status (PASS/FAIL); token field presence booleans (refresh token present, access token present, expiry present); redacted token references. |
| Evidence forbidden | The token values; the raw response body; the token expiry timestamp with real time; any diff of before/after. |
| Stop if | Exchange failure; unexpected response fields; token response visible on screen longer than the immediate hand-off; auth code re-use attempted. |
| Pause after step? | YES (G24). |
| Next step requires separate authorization? | YES. |

### H.A7 — Store Credentials in Secret Manager

| Field | Value |
|---|---|
| Step ID | A7 |
| Purpose | Store the A6-produced credential bundle in Secret Manager via the V5.15 admin write path (`POST /credentials/google-ads`). |
| Required exact authorization phrase | Phase 2 Section E.7 |
| Required preconditions | F-25–F-28 re-verified immediately before; A6 completed; secret path pre-approved (Phase 2 packet); version lifecycle policy `DISABLE_PREVIOUS_WITH_GRACE_PERIOD` confirmed (V5.20); `GCP_SECRET_MANAGER_ENABLED=true`; audit path writable. |
| Allowed action | Invoke `write_google_ads_credential_bundle()` via the V5.15 admin path in a single atomic call; receive and verify metadata-only response; emit and verify audit event. |
| Forbidden actions | Committing the bundle payload; committing the raw response body; committing the real Secret Manager path; retrying a partial write without rollback owner confirmation. |
| Evidence allowed | Write status boolean; field presence booleans (4 expected fields); version index placeholder (`<version_ref>`); audit `seq`/`digest`; redacted `<credential_ref_placeholder>`. |
| Evidence forbidden | The bundle values; the raw response body; the actual resource path with real project number; the actual secret name; the audit JSON with raw fields. |
| Stop if | Write ambiguity; response body error; audit chain broken; version lifecycle policy not confirmed; secret path not pre-approved; wrong project. |
| Pause after step? | YES (G27). |
| Next step requires separate authorization? | YES. |

### H.A8 — First Read-Only Google Ads API Validation

| Field | Value |
|---|---|
| Step ID | A8 |
| Purpose | Run the first read-only Google Ads API validation call to confirm the stored credentials work end-to-end. |
| Required exact authorization phrase | Phase 2 Section E.8 |
| Required preconditions | A7 completed; V5.20 first live API validation plan (`docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md`) reviewed; V5.19 preflight PASS; API operation is read-only (GAQL SELECT or metadata query only). |
| Allowed action | Invoke a single read-only GAQL query against the target customer (pre-approved in packet); capture the response into a transient buffer; verify expected shape without printing values. |
| Forbidden actions | Any mutation call; any campaign change; any budget change; committing the response payload; committing customer IDs in the response. |
| Evidence allowed | API status (PASS/FAIL); response shape confirmation (booleans); error code if any; latency placeholder. |
| Evidence forbidden | The response payload; the customer ID; the login customer ID; the developer token; the account name or account email. |
| Stop if | Non-read-only API attempted; unexpected response shape; error code indicates auth/token problem; V5.19 preflight FAIL. |
| Pause after step? | YES (G30). |
| Next step requires separate authorization? | YES. |

### H.A9 — Activate Live Flag

| Field | Value |
|---|---|
| Step ID | A9 |
| Purpose | Set `GOOGLE_ADS_LIVE_ENABLED=true` for the explicitly authorized runtime scope. |
| Required exact authorization phrase | Phase 2 Section E.9 |
| Required preconditions | A8 completed successfully; live-mode gate override authorized in writing; scope and duration of activation explicitly named in the out-of-repo record. |
| Allowed action | Set the flag in the specifically authorized runtime environment for the specifically authorized duration; verify via `check_live_gate()` that the flag is active only in the intended scope. |
| Forbidden actions | Activating the flag in a scope wider than named; extending the activation beyond named duration; committing any `.env` or config file containing `GOOGLE_ADS_LIVE_ENABLED=true`. |
| Evidence allowed | Activation status (PASS/FAIL); scope reference (redacted); activation timestamp placeholder; deactivation timestamp placeholder. |
| Evidence forbidden | The runtime environment identifier if it discloses infrastructure detail; any config file diff. |
| Stop if | Activation attempted in wrong scope; activation exceeds duration; `.env` or config file with `GOOGLE_ADS_LIVE_ENABLED=true` created in repo. |
| Pause after step? | YES (G33). |
| Next step requires separate authorization? | YES. |

### H.A10 — Rollback or Revoke

| Field | Value |
|---|---|
| Step ID | A10 |
| Purpose | Perform the explicitly named rollback/revoke action (revoke a credential; delete a Secret Manager version; deactivate live flag; roll back approval status). |
| Required exact authorization phrase | Phase 2 Section E.10 (or documented emergency policy from Phase 3 Section I) |
| Required preconditions | Rollback owner or emergency revoke owner present; V5.15 delete/revoke endpoint or V5.16 rotate endpoint identified as target; V5.20 rollback drill PASS confirmed. |
| Allowed action | Invoke the identified endpoint via the V5.15/V5.16 admin path; verify metadata-only response; emit and verify audit event. |
| Forbidden actions | Fetching the credential before deletion; printing the credential during rollback; committing rollback response body; retrying without rollback owner confirmation. |
| Evidence allowed | Rollback status (PASS/FAIL); secret version state (`ENABLED`/`DISABLED`/`DESTROYED`); audit event `seq`/`digest`; redacted `<credential_ref_placeholder>`. |
| Evidence forbidden | The credential value; the raw response body; the actual resource path; project number. |
| Stop if | Rollback ambiguity; response body error; audit chain broken; wrong resource targeted. |
| Pause after step? | YES (G effectively closes the sequence). |
| Next step requires separate authorization? | Any subsequent activity is a new ceremony; a new authorization packet is required. |

---

## I. Stop Conditions

Any of the following conditions immediately halts the ceremony, voids any in-flight authorization, and triggers the Phase 3 Section M incident protocol.

| # | Stop condition |
|---|---|
| I-01 | Any real credential value appears in chat (Claude Code, ChatGPT, Slack, GitHub, or any observed session) |
| I-02 | Any real credential value appears in git (any file, any branch, any repo) |
| I-03 | Any real credential value appears in a committed documentation file |
| I-04 | Any real credential value appears in logs (application, structured, cloud, CI, or downstream aggregator) |
| I-05 | Any real credential value appears in shell history |
| I-06 | An unauthorized channel (any not in Phase 3 Section D.1–D.4) is used for credential transit |
| I-07 | A screenshot containing a real credential is created |
| I-08 | Screen recording is active during any credential handling step |
| I-09 | A credential class is transmitted or accessed outside the current step's authorization scope |
| I-10 | Approval packet missing, expired, revoked, or scope-mismatched at execution time |
| I-11 | Runbook status invalid (committed status is not `DRAFT` or `REVIEWED`; execution attempted without out-of-repo `READY_TO_PROPOSE` status) |
| I-12 | A1 attempted before exact Section E.1 phrase captured verbatim |
| I-13 | A2 attempted before exact Section E.2 phrase captured verbatim |
| I-14 | A3 attempted before exact Section E.3 phrase captured verbatim |
| I-15 | A4 attempted before exact Section E.4 phrase captured verbatim |
| I-16 | A5 attempted before exact Section E.5 phrase captured verbatim |
| I-17 | A6 attempted before exact Section E.6 phrase captured verbatim |
| I-18 | A7 attempted before exact Section E.7 phrase captured verbatim |
| I-19 | A8 attempted before exact Section E.8 phrase captured verbatim |
| I-20 | A9 attempted before exact Section E.9 phrase captured verbatim |
| I-21 | A10 attempted before exact Section E.10 phrase captured verbatim (and no documented emergency policy applies) |
| I-22 | Authorization expired (timebox window end reached) |
| I-23 | Authorization paraphrased (Section E phrase substituted with a summary or reworded version) |
| I-24 | Authorization scope ambiguous (phrase mixes multiple steps or covers unnamed tenant/client) |
| I-25 | Tenant/client scope unclear (no named `<tenant_ref>`/`<client_ref>` resolvable through secure channel) |
| I-26 | Operator (`<operator_label>`) unavailable at execution time |
| I-27 | Reviewer (`<reviewer_label>`) unavailable at execution time |
| I-28 | Stop authority (`<stop_authority_label>`) unavailable at any point during window |
| I-29 | Rollback owner (`<rollback_owner_label>`) unavailable at any point during A5–A9 window |
| I-30 | Emergency revoke owner (`<emergency_revoke_owner_label>`) unavailable at any point during A6–A9 window |
| I-31 | Safety grep fails (a sensitive hit that is not documentation, prohibition, or table-label text) |
| I-32 | Any of the 10 required tests fails (8 demos + 2 smoke suites) |
| I-33 | Any V5.19–V5.22 validator fails |
| I-34 | Working tree dirty at execution time |
| I-35 | `.env` file created inside repository at any point during window |
| I-36 | Credential JSON file created inside repository at any point during window |
| I-37 | Token response visible on screen longer than the immediate consumption step allows |
| I-38 | Clipboard used outside approved procedure (e.g., without clipboard-history suppression) |
| I-39 | Local temporary secret file created outside approved procedure |
| I-40 | OAuth URL copied into any repository documentation file |
| I-41 | Callback URL copied into any repository documentation file |
| I-42 | Auth code copied into any repository documentation file |
| I-43 | Token exchange attempted outside A6 (before authorization or after window close) |
| I-44 | Secret Manager write attempted outside A7 |
| I-45 | Google Ads API call attempted outside A8 |
| I-46 | Live flag activation attempted outside A9 |
| I-47 | Rollback/revoke attempted outside A10 unless documented emergency policy explicitly applies |
| I-48 | Silent continuation past a mandatory pause point (no reviewer countersignature captured) |
| I-49 | Ceremony window overlap detected (a prior window for the same tenant/client has not closed) |
| I-50 | Freeze window before start violated (repo activity during freeze period) |

---

## J. Rollback and Revoke Readiness

Rollback/revoke is **not authorized by this runbook**. A10 is the only normal authorization path. Emergency policy must exist out-of-repository if A10 needs to bypass the standard Section E.10 phrase. **No secret values may be logged during rollback/revoke.**

### J.1 — Rollback readiness checklist

| # | Item | Verified |
|---|---|---|
| J-01 | Rollback owner (`<rollback_owner_label>`) reachable | [ ] |
| J-02 | Emergency revoke owner (`<emergency_revoke_owner_label>`) reachable | [ ] |
| J-03 | A10 phrase template available (Phase 2 Section E.10) | [ ] |
| J-04 | V5.15 revoke/delete path understood (`DELETE /credentials/google-ads`; `AdminScope.DELETE`; `OPENCLAW_ADMIN_DELETE_ENABLED=true`) | [ ] |
| J-05 | V5.16 rotate path understood (`POST /credentials/google-ads/rotate`; `AdminScope.ROTATE`) | [ ] |
| J-06 | V5.20 rollback drill reviewed (`openclaw/rollback_drill.py` PASS confirmed) | [ ] |
| J-07 | Secret Manager version lifecycle policy reviewed (`DISABLE_PREVIOUS_WITH_GRACE_PERIOD` per `openclaw/secret_version_policy.py`) | [ ] |
| J-08 | Evidence redaction ready (Phase 3 Section J procedure understood) | [ ] |
| J-09 | Audit verification ready (`verify_audit_file()` accessible; audit path known) | [ ] |
| J-10 | Final safety grep ready (all 9 patterns; expected acceptable hits catalog understood) | [ ] |

### J.2 — Rollback boundary rules

- Rollback/revoke does not authorize new intake, new OAuth, new token exchange, new Secret Manager write, or new API calls.
- After rollback/revoke, all subsequent activity is a **new ceremony**: a new authorization packet is required; no in-flight authorizations carry over.
- Rollback via V5.15 delete endpoint returns metadata only; use that path. Do not fetch the credential before deletion.
- Emergency revoke path skips the fresh Section E.10 phrase only if the documented emergency policy in the out-of-repo record explicitly authorizes it for the observed incident class.

---

## K. Post-Execution Verification

After each authorized A-step completes, the following template records the outcome. **Real values may never appear in the post-execution record.**

| Field | Content | Real value permitted? |
|---|---|---|
| Step ID | `A1` \| `A2` \| ... \| `A10` | Literal — YES |
| Authorization ref | `<packet_ref>` / `<phrase_capture_ref>` | Placeholder — NO real value |
| Status | `PASS` \| `FAIL` \| `STOPPED` | Literal — YES |
| Evidence ref | `<evidence_ref>` | Placeholder — NO real value |
| Safety grep result | `CLEAN` \| `FAIL` | Literal — YES |
| Smoke result (if applicable) | `smoke_test_v5_credentials.sh: 35/35 PASS` \| `smoke_test_v5_12_gcp_secret_manager.sh: 8/8 PASS` | Literal — YES |
| Redaction review result | `PASS` \| `FAIL` | Literal — YES |
| Follow-up required | Free text (redacted) | Redacted — NO real value |
| Next step authorization status | `NOT_REQUESTED` \| `REQUESTED` \| `APPROVED` \| `REJECTED` | Literal — YES |

**Rules:**
- Post-execution verification is written to the out-of-repo evidence store, not to git.
- If any field would require a real value to be meaningful, replace the value with a redacted reference.
- The reviewer countersigns each post-execution record.
- Missing post-execution record = ceremony not closed = new packet required for any future activity.

---

## L. Final Go/No-Go Checklist

Before the first authorized A-step of any ceremony window, all items below must be PASS in full. If any is FAIL, the ceremony does not proceed; no A-step is executed.

| # | Item | Verified |
|---|---|---|
| L-01 | All prior phases (V5.23 Phase 1, 2, 3) complete and committed | [ ] |
| L-02 | Authorization packet (Phase 2) reviewed by both operator and reviewer | [ ] |
| L-03 | Intake protocol (Phase 3) reviewed | [ ] |
| L-04 | This runbook (Phase 4) reviewed | [ ] |
| L-05 | Role coverage complete (all 10 roles from Section D filled or explicitly exempted per packet) | [ ] |
| L-06 | Timebox `<timebox_ref>` defined with start, end, and freeze window | [ ] |
| L-07 | Tenant/client scope defined through placeholder ref, resolvable through secure channel | [ ] |
| L-08 | Exact step requested (exactly one of A1–A10 named in the current ceremony proposal) | [ ] |
| L-09 | Exact phrase captured verbatim for the requested step (Phase 2 Section E) | [ ] |
| L-10 | Safety grep CLEAN across all 9 patterns on all files touched this window | [ ] |
| L-11 | All 8 demos PASS | [ ] |
| L-12 | `smoke_test_v5_credentials.sh` — 35/35 PASS | [ ] |
| L-13 | `smoke_test_v5_12_gcp_secret_manager.sh` — 8/8 PASS | [ ] |
| L-14 | No `.env` file exists anywhere in the repository | [ ] |
| L-15 | No credential JSON file exists anywhere in the repository | [ ] |
| L-16 | No real secrets in repo (verified via safety grep and manual inspection) | [ ] |
| L-17 | No uncommitted unrelated changes in working tree | [ ] |
| L-18 | Stop authority (`<stop_authority_label>`) online and reachable | [ ] |
| L-19 | Rollback owner (`<rollback_owner_label>`) online and reachable (for A5–A9) | [ ] |
| L-20 | Emergency revoke owner (`<emergency_revoke_owner_label>`) online and reachable (for A6–A9) | [ ] |
| L-21 | Secure channel (Phase 3 D.1–D.4) ready with preconditions met | [ ] |
| L-22 | Evidence owner (`<evidence_owner_label>`) ready with out-of-repo evidence store writable | [ ] |
| L-23 | Incident protocol (Phase 3 Section M) visible or ready to invoke | [ ] |
| L-24 | Redaction workflow (Phase 3 Section J.3) ready | [ ] |
| L-25 | `GOOGLE_ADS_LIVE_ENABLED` default is `false` (may only be `true` if A9 approved and window active) | [ ] |
| L-26 | Secret Manager boundary understood (before-A7 hard prohibitions; after-A7 reportable-only fields) | [ ] |
| L-27 | Google Ads API boundary understood (A8 read-only; no mutation calls) | [ ] |
| L-28 | Token exchange boundary understood (A6 only; single-use auth code; no retry without rollback confirmation) | [ ] |
| L-29 | No broad authorization has been provided (no "approve the ceremony", no "run everything", no umbrella language) | [ ] |
| L-30 | No paraphrased authorization has been provided (only verbatim Section E phrases counted) | [ ] |
| L-31 | No expired authorization is in use (all Section E phrases within their timebox windows) | [ ] |
| L-32 | No window ambiguity (start and end explicitly recorded in out-of-repo approval) | [ ] |
| L-33 | Final human go/no-go recorded outside the repository (with named human authorizer, timestamp, and explicit `GO` or `NO_GO` decision) | [ ] |

**Any `[ ]` unchecked → NO_GO. The ceremony does not proceed. A remediation cycle is required before re-attempting L-01–L-33.**

---

## M. Evidence Package Template

Evidence recorded in this repository must be **redacted at commit time**. Real values live only in the out-of-repository evidence store.

### M.1 — Allowed evidence (may appear in committed files)

| Category | Example |
|---|---|
| Role labels | `<operator_label>`, `<reviewer_label>`, `<stop_authority_label>` |
| Step IDs | `A1`, `A7`, `G26` |
| Authorization references | `<phrase_capture_ref>` |
| Packet references | `<packet_ref>` |
| Ceremony references | `<ceremony_ref>` |
| PASS/FAIL statuses | `A3: PASS`, `A6: STOPPED (reason: I-37)` |
| Redacted timestamps | `<timestamp_redacted>` |
| Safety grep statuses | `safety grep: CLEAN` |
| Smoke statuses | `smoke_test_v5_credentials.sh: 35/35 PASS` |
| Validator statuses | `oauth_callback validator: PASS` |
| Redacted evidence references | `<evidence_ref>` |

### M.2 — Forbidden evidence (must never appear in committed files)

| Category | Absolute rule |
|---|---|
| Real OAuth URL | **Never committed** |
| Callback URL | **Never committed** |
| Auth code | **Never committed** |
| Access token | **Never committed** |
| Refresh token | **Never committed** |
| Token response body | **Never committed** |
| Developer token | **Never committed** |
| Client ID | **Never committed** |
| Client secret | **Never committed** |
| Customer ID | **Never committed** |
| Login customer ID | **Never committed** |
| Secret Manager path (`projects/N/secrets/S/versions/V`) | **Never committed** |
| Project ID or project number | **Never committed** |
| Service account email | **Never committed** |
| `credential_ref` path | **Never committed** |
| Real approval payload | **Never committed** |
| Screenshots containing any of the above | **Never committed** |

---

## N. Relationship to Previous Controls

| Control | Milestone | Role |
|---|---|---|
| V5.22 dry-run runbook (`docs/GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md`) and dry-run execution packet (`docs/GOOGLE_ADS_OAUTH_DRY_RUN_EXECUTION_PACKET.md`) | V5.22 | Rehearsal basis — provides the ceremony structure this Phase 4 runbook adapts to real execution. |
| V5.23 Phase 2 authorization packet (`docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md`) | V5.23 | Defines the step-specific approval surface (A1–A10 with verbatim phrases). |
| V5.23 Phase 3 credential intake protocol (`docs/GOOGLE_ADS_REAL_CREDENTIAL_INTAKE_PROTOCOL.md`) | V5.23 | Defines the secure channel and incident handling for real credential intake. |
| V5.23 Phase 1 implementation plan (`docs/V5_23_IMPLEMENTATION_PLAN.md`) | V5.23 | Defines the 10-phase roadmap, boundary rules, and safety envelope. |
| V5.19 live-mode gate, approval workflow, preflight | V5.19 | Runtime gate; A9 authorization required to open. |
| V5.20 first live API validation plan (`docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md`) | V5.20 | A8 execution structure. |
| V5.20 rollback drill and secret version lifecycle policy | V5.20 | Prerequisite validators for A7/A10. |
| V5.15/V5.16 credential lifecycle endpoints | V5.15/V5.16 | Write/rotate/delete surfaces used by A7 and A10. |
| V5.12 Secret Manager backend (`GCPSecretManagerStore`) | V5.12 | Underlying storage backend for A7 writes. |

**None of the above authorize execution.** Phase 5 (`docs/V5_23_PRE_EXECUTION_AUTHORIZATION_REVIEW.md`) must decide whether the system is READY_TO_PROPOSE real execution. Even a READY_TO_PROPOSE verdict is not authorization; it is a precondition for a future authorization request.

---

## O. Phase 4 Conclusion

**V5.23 Phase 4 result:**

- [x] Real OAuth execution runbook created at `docs/GOOGLE_ADS_REAL_OAUTH_EXECUTION_RUNBOOK.md`.
- [x] Documentation-only.
- [x] All fields are placeholder-only in the committed form.
- [x] Runbook committed status is `DRAFT`.
- [x] No real approval created.
- [x] No real credentials requested or handled.
- [x] No OAuth executed.
- [x] No real OAuth authorization URL generated.
- [x] No browser opened.
- [x] No callback URL received.
- [x] No auth code received, logged, stored, pasted, or committed.
- [x] No token exchange attempted.
- [x] No Google OAuth token endpoint called.
- [x] No Secret Manager called.
- [x] No Google Ads API called.
- [x] No GCP commands or GCP API calls.
- [x] No deploy performed.
- [x] No IAM/API/billing changes made.
- [x] No cloud resources created.
- [x] No `GOOGLE_ADS_LIVE_ENABLED=true` runtime activation.
- [x] No real rollback or revocation performed.
- [x] No real operator identities recorded in-repo.
- [x] No real tenant/client/customer identifiers recorded in-repo.
- [x] No `.env` file created.
- [x] No credential JSON file created.

**Phase 5 (pre-execution final authorization review — `docs/V5_23_PRE_EXECUTION_AUTHORIZATION_REVIEW.md`) remains pending.** Phases 6–10 also remain pending as described in `docs/V5_23_IMPLEMENTATION_PLAN.md`.

**This document does not authorize any live step.** A live step is authorized only when the corresponding A*n* exact phrase from `docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md` Section E is captured verbatim through an approved out-of-repository channel, the Section L final go/no-go checklist here is PASS in full, the Phase 3 pre-intake checklist is PASS in full, and no Section I stop condition is triggered.

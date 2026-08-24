# V5.23 Implementation Plan — Controlled Real OAuth Execution Planning

**Branch:** `v5.23-controlled-real-oauth-execution-planning`
**Base:** `v5.22.0-beta` / master merge commit `4217652`
**Status:** Phase 4 — OAuth execution runbook final go/no-go checklist
**Purpose:** Design the authorization architecture, per-step gating model, and safety envelope required before any first controlled real OAuth execution can be proposed.

---

**This plan does not authorize execution.**
**This plan does not request real credentials.**
**This plan does not execute OAuth.**
**This plan does not generate a real OAuth authorization URL.**
**This plan does not open a browser OAuth flow.**
**This plan does not receive an auth code.**
**This plan does not exchange tokens.**
**This plan does not call Google Ads API.**
**This plan does not call GCP or Secret Manager.**
**`GOOGLE_ADS_LIVE_ENABLED` remains false throughout Phase 1.**

---

## A. Objective

V5.23 is the planning and authorization-design milestone for the first controlled real OAuth execution.

V5.20 delivered readiness controls. V5.21 designed the ceremony structure (checklist, auth-URL validator, callback validator, credential handoff protocol, approval packet validator, dry-run runbook). V5.22 successfully executed a full dry-run rehearsal with redacted placeholders only, producing a PASS verdict without touching a single real credential, OAuth endpoint, token, or GCP resource.

V5.23 Phase 1 defines the authorization architecture that governs any future real execution. It specifies:

- The per-step approval model (each live step requires separate explicit approval).
- The chain of ceremony gates that must be PASS immediately before each step.
- The secret and credential handling boundary applicable to real values.
- The stop conditions that override all in-flight authorization.
- The safety-check envelope that must be re-run before, during, and after execution.
- The deferred/optional-phase model (Phases 6–8 remain pending separate authorization).

**Critical distinction:** V5.23 defines *how* real OAuth would be executed safely if authorized. It does not authorize execution. It does not schedule a ceremony window. It does not name real operators. It does not commit any real value. A future real ceremony requires a separate explicit operator authorization that is outside the scope of V5.23 Phase 1 and cannot be inferred from V5.23's PASS status.

---

## B. Non-Authorization Statement

V5.23 Phase 1 does **not** authorize any of the following. Each item is explicitly out of scope until a later phase receives separate explicit operator approval.

- Real OAuth execution.
- Real credential handoff.
- Real OAuth authorization URL generation.
- Browser OAuth flow.
- Callback URL receipt.
- Auth code receipt.
- Token exchange.
- Token response receipt.
- Storing real credentials.
- Writing to Secret Manager.
- Google Ads API call.
- GCP command or GCP API call.
- Deploy.
- IAM changes, API enablement, or billing changes.
- `GOOGLE_ADS_LIVE_ENABLED=true` runtime activation.
- Real rollback or real credential revocation.

**None of the above may occur in Phase 1. No exception. If the plan itself creates ambiguity about whether an action is permitted, treat it as forbidden and ask before proceeding.**

---

## C. Baseline

**Baseline release:** `v5.22.0-beta`
**Baseline branch:** `master`
**Baseline merge commit:** `4217652`
**Baseline dry-run verdict:** PASS (dry-run only).
**Baseline real ceremony authorization:** NOT GRANTED.

**Existing controls carried forward from prior versions:**

| Version | Control set | Status |
|---|---|---|
| V5.12–V5.18 | Secret Manager backend, admin credential lifecycle, live GCP fake-secret validation | Preserved |
| V5.19 | Live-mode gate; approval workflow; preflight infrastructure; runtime guardrails | Preserved |
| V5.20 | Onboarding ceremony validator; credential intake dry-run; rollback drill; secret version lifecycle policy; first live API validation plan; final readiness review | Preserved |
| V5.21 | OAuth ceremony checklist; auth URL validator; callback boundary validator; credential handoff protocol; approval packet validator; dry-run runbook | Preserved |
| V5.22 | Dry-run execution packet template; dry-run execution validator; local dry-run results (PASS); stop/rollback rehearsal (PASS); final dry-run review (PASS); 610 aggregate assertions | Preserved |

**Validation evidence carried forward:** 610 explicit assertions across 7 counted demos, plus onboarding ceremony PASS, plus smoke suites 35/35 and 8/8 PASS, plus safety grep CLEAN across all 9 patterns.

V5.23 does not modify or weaken any prior control. V5.23 adds a top-level authorization layer above them.

---

## D. Risk Classification

**V5.23 risk class: HIGH.**

V5.23 is high-risk because — although Phase 1 is planning only — the phases it plans for approach:

- Real OAuth consent and browser execution.
- Real credential material (developer token, client secret, refresh token, access token).
- Real auth code receipt (single-use, high-value, short-lived).
- Real token exchange with the Google OAuth token endpoint.
- Real Secret Manager write (irreversible per-version, tenant-scoped).
- First live Google Ads API validation call.
- Possible `GOOGLE_ADS_LIVE_ENABLED=true` runtime activation.

**Operating discipline for V5.23:**

- **Use Opus / high analysis for planning and authorization boundary design.** Boundary decisions, gate composition, and stop-condition wording all require the higher-analysis mode.
- **Return to Sonnet / medium only after the plan is approved and tasks become mechanical** (e.g., stubbing a Python validator scaffold, running a smoke suite, formatting a table).
- **Treat every ambiguity as a stop condition.** If a step is not explicitly authorized and its safety envelope is not fully specified, halt and ask.
- **Never elevate a smaller approval to imply a larger one.** Approval to draft a plan is not approval to execute the plan. Approval to run a validator is not approval to generate an authorization URL.

---

## E. Phase Plan

Only Phase 1 is executed now. Phases 2–5 are documentation-only design work that may be authorized incrementally. Phases 6–8 involve real execution and remain pending separate explicit authorization at each step. Phases 9–10 are release-lifecycle steps.

### Phase 1 — Branch setup and real OAuth execution planning
**Status:** In progress (this document).
**Deliverables:** `docs/V5_23_IMPLEMENTATION_PLAN.md`; README and ROADMAP updates.
**No-real-execution constraint:** Planning only. No validator run. No dry-run execution. No real credentials. No OAuth. No GCP.
**Validation:** Document review. Safety grep clean. Smoke tests pass (no regressions from base).

### Phase 2 — Real ceremony authorization packet template
**Status:** In progress (this phase).

**Phase 2 Implementation Note:** `docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md` created. Documentation-only. 11 sections (A–K): packet purpose; packet identity (13 fields, all placeholders; default status `DRAFT`); scope boundary (9 fields + 8 scope rules C-R1–C-R8, prohibiting real values and cross-scope inference); live step authorization table (10 rows A1–A10; default status `NOT_REQUESTED`; 5 status enum values `NOT_REQUESTED | REQUESTED | APPROVED | REJECTED | STOPPED`; explicit rule that `APPROVED` may never be committed); exact authorization phrase templates (10 verbatim phrases E.1–E.10, one per step, plus 7 phrase rules E-R1–E-R7 including "only" and trailing "does not authorize" clauses invariant); approval validity rules (20 rules F-R1–F-R20 including per-step, per-tenant, per-window uniqueness and non-inference from V5.22 PASS); pre-authorization checklist (23 items G-C1–G-C23 including 30-day dry-run refresh); evidence rules (10 allowed categories + 15 forbidden categories + 5-step redaction procedure); stop conditions (29 conditions I-L1–I-L29); relationship to V5.22 (V5.22 PASS ≠ V5.23 approval; requires fresh step-specific authorization); Phase 2 conclusion. All fields placeholder-only. No real approval created. No real credentials. No real values recorded anywhere. No OAuth executed. No auth URL generated. No browser opened. No callback URL. No auth code. No token exchange. No Secret Manager. No Google Ads API. No GCP. No deploy. `GOOGLE_ADS_LIVE_ENABLED` remains false. Phase 3 (secure real credential intake protocol finalization) remains pending.

**Deliverables:** `docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md`.
**Purpose:** Formal operator authorization template for the first real OAuth execution. Extends V5.21's `oauth_approval_packet.py` schema with real-ceremony fields (named execution window, named participants, named tenant scope) — all as **placeholder labels** in the committed template, with the note that real values live only in an out-of-repository approval record.
**Contents:**
- Real approval record schema (approval ref placeholder, approval scope literal, approval expiry timestamp placeholder, countersignatures required list).
- Named participant slots (all as `<placeholder_label>` in committed doc; real names go into the out-of-repo approval only).
- Named tenant/client scope slots (placeholder in committed doc).
- Named execution window slots (placeholder timestamps; window rules literal).
- Per-step approval sub-fields (auth URL generation, browser execution, callback receipt, token exchange, Secret Manager write, API call, live flag activation — each with independent `authorized_by`, `authorized_at`, `expires_at` slots).
- Pre-flight gate checklist (all existing V5.19–V5.22 validators PASS required immediately before authorization is granted).
- Explicit non-authorization statement.
- Rehearsal-first requirement (dry-run PASS must be completed within the last 30 days before real execution).
**No-real-execution constraint:** Documentation-only template. No real approval created. No real values. No credentials. No OAuth. No GCP.
**Validation:** Document review. Safety grep clean.

### Phase 3 — Secure real credential intake protocol finalization
**Status:** In progress (this phase).

**Phase 3 Implementation Note:** `docs/GOOGLE_ADS_REAL_CREDENTIAL_INTAKE_PROTOCOL.md` created. Documentation-only. 15 sections (A–O): protocol purpose; non-authorization statement (17 items); credential class matrix (16 credential classes × 10 handling attributes each — every class marked `Stop if exposed = YES`, all approved-channel-required, all forbidden in chat/git/docs/logs); approved channels (4 classes D.1–D.4 with 7 attributes each — password manager secure item; encrypted file transfer with out-of-band passphrase; operator-local terminal entry without echo; cloud secret write after A7 only; plus D.5 explicit not-approved list); forbidden channels (17 items E-F1–E-F17); intake roles and responsibilities (9 role placeholders with 5 attributes each — operator, reviewer, credential owner, secure channel owner, secret writer, stop authority, rollback owner, emergency revoke owner, evidence owner; no self-authorization; stop authority supreme); intake sequence (18 steps G1–G18 extending V5.21 handoff E1–E12 and V5.23 A1–A10; 6 non-implication rules; time-slot rules); Secret Manager handoff boundary (before-A7 hard prohibitions; after-A7 reportable-only fields; violation → stop condition); rotation and revocation boundary (references V5.15/V5.16/V5.20/V5.23 A10; emergency policy exception with mandatory redaction); redaction and evidence rules (13 allowed categories + 16 forbidden categories + 5-step pre-commit redaction procedure); stop conditions (35 conditions K-01–K-35); pre-intake checklist (31 items L-01–L-31); incident protocol (13 steps M1–M13 with post-incident new-ceremony rule); relationship to previous controls (V5.21 handoff, V5.22 dry-run PASS, V5.23 Phase 1/2, V5.19/V5.20/V5.15/V5.16/V5.12 layered controls); Phase 3 conclusion. All fields placeholder-only. No real credentials requested or received. No real approval created. No real values recorded anywhere. No OAuth executed. No auth URL generated. No browser opened. No callback URL. No auth code. No token exchange. No Secret Manager. No Google Ads API. No GCP. No deploy. `GOOGLE_ADS_LIVE_ENABLED` remains false. Phase 4 (OAuth execution runbook final go/no-go checklist) remains pending.

**Deliverables:** `docs/GOOGLE_ADS_REAL_CREDENTIAL_INTAKE_PROTOCOL.md`.
**Purpose:** Convert V5.21's `GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md` into a real-credential-ready operating protocol. Defines exact secure-channel rules, forbidden channels, participant confirmation, and evidence-redaction rules — all reused from V5.21 with real-ceremony hardening.
**Contents:**
- Approved secure channels for real values (encrypted operator tooling; direct Secret Manager write path via V5.15 admin endpoint; encrypted local file with delete-after-write requirement; verbal read-aloud in secure room for short values only). Reuses V5.21 Section D.
- Explicit forbidden channels list (chat sessions of any kind — Claude Code, ChatGPT, Slack, GitHub, email, SMS, unencrypted files, clipboard on shared screens). Reuses V5.21 Section C.
- Credential class matrix (refresh token, access token, client ID, client secret, developer token, customer ID, login customer ID) — all as `<label_redacted>` in committed doc.
- Real ceremony operator responsibilities (credential handling owner, storage owner, evidence owner, secondary reviewer confirmations).
- Real handoff sequence with per-step gates (extends V5.21 handoff sequence E1–E12).
- Evidence redaction rules (all evidence committed to repo must be redacted; raw resource paths, real refs, real IDs forbidden).
- Real credential rotation and revocation integration (V5.15 `DELETE /credentials/google-ads` endpoint; V5.16 rotate endpoint; V5.20 secret version lifecycle policy).
- Stop conditions specific to real intake.
**No-real-execution constraint:** Documentation-only protocol. No credentials requested. No handoff performed. No Secret Manager call. No OAuth.
**Validation:** Document review. Safety grep clean.

### Phase 4 — OAuth execution runbook final go/no-go checklist
**Status:** In progress (this phase).

**Phase 4 Implementation Note:** `docs/GOOGLE_ADS_REAL_OAUTH_EXECUTION_RUNBOOK.md` created. Documentation-only. 15 sections (A–O): runbook purpose; non-authorization statement (17 items); ceremony identity (12 fields; 4 status enum values `DRAFT|REVIEWED|READY_TO_PROPOSE|REJECTED`; default committed status `DRAFT`; `READY_TO_PROPOSE`/`REJECTED` prohibited in Phase 4 commits); operator roles (10 role placeholders — operator, reviewer, credential owner, secure channel owner, secret writer, OAuth operator, stop authority, rollback owner, emergency revoke owner, evidence owner — each with 6 attributes and cross-cutting rules); time-boxed execution window (6 fields + 8 window rules E-R1–E-R8: expiry, extension, abort, restart, freeze, attention, no-overlap, cool-down); pre-execution gate checklist (38 items F-01–F-38; verification at execution time only, no carry-forward); execution sequence overview (38 steps G1–G38 with approval-confirmation and pause-point structure + 6 sequence rules G-R1–G-R6 including no-implication, no-carry-forward, no-continuation-past-expiry, no-skip-without-authorization, non-sequential-pause-requirement, silent-continuation-prohibited); per-step execution cards A1–A10 (each with step ID, purpose, required phrase reference, required preconditions, allowed action, forbidden actions, evidence allowed, evidence forbidden, stop-if triggers, pause-after=YES, next-step-separate-authorization=YES); stop conditions (50 conditions I-01–I-50); rollback/revoke readiness (10-item checklist J-01–J-10; 4 boundary rules; new-ceremony-after-rollback rule); post-execution verification template (9 fields; real-values-permitted flags; out-of-repo storage rule); final go/no-go checklist (33 items L-01–L-33; NO_GO on any unchecked item); evidence package template (11 allowed categories + 17 forbidden categories); relationship to previous controls (V5.22 runbook basis, V5.23 Phase 2/3, V5.19/V5.20/V5.15/V5.16/V5.12 layered controls; Phase 5 review required); Phase 4 conclusion. All fields placeholder-only. No real approval created. No real credentials. No real values recorded anywhere. No OAuth executed. No auth URL generated. No browser opened. No callback URL. No auth code. No token exchange. No Secret Manager. No Google Ads API. No GCP. No deploy. `GOOGLE_ADS_LIVE_ENABLED` remains false. Phase 5 (pre-execution final authorization review) remains pending.

**Deliverables:** `docs/GOOGLE_ADS_REAL_OAUTH_EXECUTION_RUNBOOK.md`.
**Purpose:** Convert V5.21's `GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md` from rehearsal form into real-execution operator runbook. Adds time-boxed operator steps, per-step stop conditions, rollback owner assignments, per-step approvals, and final go/no-go checklist. Every gate remains placeholder-labeled in the committed doc.
**Contents:**
- Timed execution window model (window start placeholder, window end placeholder, mandatory pause points P1–Pn, single-window rule).
- Named operator role slots (all `<placeholder_label>`).
- Real execution sequence (extends V5.22's 24-step dry-run sequence into 30+ real-execution steps with per-step approvals).
- Per-step stop conditions (`stop_if_*` triggers for every step).
- Rollback owner + emergency revoke owner assignment (placeholders; real assignments in approval record only).
- Post-execution verification steps (audit chain verification, safety grep, smoke suites, `check_live_gate()` denial confirmation).
- Final go/no-go checklist (must be PASS immediately before any live step; must be re-verified if any pause point is exceeded).
- Explicit non-authorization statement.
**No-real-execution constraint:** Documentation-only runbook. No OAuth executed. No browser opened. No credentials used.
**Validation:** Document review. Safety grep clean.

### Phase 5 — Pre-execution final authorization review
**Status:** Pending.
**Deliverables:** `docs/V5_23_PRE_EXECUTION_AUTHORIZATION_REVIEW.md`.
**Purpose:** Consolidate Phases 1–4 into a single review document that determines whether a real execution can even be *proposed* — not whether it is authorized. The review outputs a verdict (READY-TO-PROPOSE / NOT-READY) with gap analysis. A READY verdict is a precondition for any Phase 6 authorization request; it is not itself authorization.
**Contents:**
- Phase-by-phase review of Phases 1–4.
- Gap analysis (any missing control, missing approval slot, missing stop condition, missing rollback owner).
- Full validator inventory PASS confirmation.
- Aggregate assertion count.
- Smoke suite result.
- Safety grep result.
- Explicit NOT APPROVED statements (mirroring V5.22 final review structure).
- Explicit READY-TO-PROPOSE-OR-NOT verdict.
- Explicit statement that READY-TO-PROPOSE ≠ authorized to execute.
- Recommended conditions for a future authorization request.
**No-real-execution constraint:** Documentation-only review. No execution. No decision to execute.
**Validation:** Document review. Safety grep clean.

### Phase 6 — Optional real OAuth execution ceremony
**Status:** PENDING SEPARATE EXPLICIT AUTHORIZATION.
**May not be executed by default.** Phase 6 is listed here as a future possibility only. It is not activated by completing Phase 5. It is not activated by a READY-TO-PROPOSE verdict.
**Required conditions before Phase 6 may be authorized:**
1. Phase 5 review PASS with READY-TO-PROPOSE verdict.
2. Real approval packet (Phase 2 template) filled in **out-of-repository** with real operator identities, real tenant scope, and named execution window.
3. Approval countersigned by every required countersignatory.
4. Approval scope explicitly names OAuth-ceremony-only actions (auth URL generation, browser execution, callback receipt).
5. Dry-run (V5.22 or refreshed) PASS within the last 30 days.
6. `check_live_gate()` denial confirmed for all non-authorized live paths.
7. Explicit user authorization message naming every action Phase 6 will take, with each action listed line-by-line.
**Phase 6 does not automatically include:** token exchange (that is Phase 7), Secret Manager write (Phase 7), Google Ads API call (Phase 8), or `GOOGLE_ADS_LIVE_ENABLED=true` activation (Phase 8).
**Stop authority remains supreme.** Any stop condition (Section H) halts Phase 6 immediately.

### Phase 7 — Optional token exchange and Secret Manager write
**Status:** PENDING SEPARATE EXPLICIT AUTHORIZATION.
**Must be separately approved after Phase 6.** Auth-code receipt (end of Phase 6) does not authorize token exchange. Approval to exchange the auth code must be explicit and must arrive after the auth code is in hand.
**Required conditions before Phase 7 may be authorized:**
1. Phase 6 completed successfully with auth code in the approved secure channel.
2. Auth code has not been logged, committed, or transmitted through a forbidden channel.
3. Explicit user authorization message naming: (a) token exchange, (b) Secret Manager write, (c) target secret path (pre-approved in Phase 2 packet).
4. Version lifecycle policy validator PASS immediately before write.
5. Rollback owner and emergency revoke owner both present and reachable.
**Phase 7 does not include:** Google Ads API call, live flag activation.
**Failure at any Phase 7 step invokes rollback and revocation flow.**

### Phase 8 — Optional first Google Ads read-only API validation
**Status:** PENDING SEPARATE EXPLICIT AUTHORIZATION.
**Must keep `GOOGLE_ADS_LIVE_ENABLED=false` unless explicitly authorized otherwise.** A separate approval is required to set the live flag true, and a further separate approval is required to make the first API call.
**Required conditions before Phase 8 may be authorized:**
1. Phase 7 completed successfully with secret bundle written and verified.
2. `openclaw/onboarding_ceremony.py` and V5.20 `GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md` fully reviewed and PASS.
3. Explicit user authorization message naming: (a) live flag activation intent, (b) first API call, (c) API operation (must be read-only), (d) target customer scope.
4. Preflight validator PASS.
5. Live-mode gate override authorized in writing.
**Phase 8 API call must be read-only.** No mutation. No writes to Google Ads. No campaign changes.
**After Phase 8:** `GOOGLE_ADS_LIVE_ENABLED` must be returned to `false` unless a separate longer-term authorization is granted.

### Phase 9 — Branch closure docs and release notes
**Status:** Documentation phase; occurs only after prior phases complete (in whatever mix has been authorized).
**Deliverables:** `docs/V5_23_BRANCH_CLOSURE.md`; `docs/RELEASE_NOTES_V5_23_0_BETA.md`; README/ROADMAP updates.
**No-real-execution constraint:** Documentation-only. No merge/tag/release in this phase.

### Phase 10 — Merge, tag, release
**Status:** PENDING SEPARATE EXPLICIT AUTHORIZATION.
**Actions:** Merge to master. Tag `v5.23.0-beta`. Push master and tag. Publish GitHub Release.
**Authorization for Phase 10 does not imply Phase 6/7/8 authorization** and vice versa. The two authorization axes are orthogonal: Phase 10 releases whatever documentation/validator work has been completed in Phases 1–5 (and possibly 9); it does not commit the project to executing Phase 6/7/8.

---

## F. Authorization Model

**Core principle:** Every live step requires a separate explicit approval. Approval to complete step *N* is not approval to start step *N+1*.

**Live steps requiring separate explicit approval:**

| # | Live step | Approval must explicitly name |
|---|---|---|
| A1 | Create real approval packet (with real operator identity, real scope) | The exact approval scope, expiry, and countersignatories |
| A2 | Prepare secure credential handoff channel | The specific channel to use (from V5.21 Section D acceptable list) |
| A3 | Generate real OAuth authorization URL | The exact OAuth client, redirect URI, scope list, and window |
| A4 | Open browser OAuth flow | The specific operator, browser, Google account, and window |
| A5 | Receive callback and handle auth code | The secure channel receiving the code; the consumer that will use it |
| A6 | Exchange auth code for tokens | The token endpoint call; the immediate storage step to follow |
| A7 | Store credentials in Secret Manager | The exact secret path (from Phase 2 packet); the version lifecycle policy |
| A8 | Run first read-only Google Ads API validation | The specific GAQL/read operation, target customer, expected response shape |
| A9 | Activate any live flag (`GOOGLE_ADS_LIVE_ENABLED=true`) | The exact scope and duration of the activation |
| A10 | Rollback or revoke real credentials | The credential ref to revoke; the revoke endpoint; the audit event to emit |

**Cross-cutting rules for all A1–A10:**
- No approval may be inferred from an earlier approval.
- No approval may cover more than one live step unless the approval explicitly enumerates each covered step.
- No approval may extend beyond the approval expiry timestamp.
- No approval survives a stop condition; a new approval must be issued after any halt.
- Authorization messages must be verbatim in scope; paraphrase is not authorization.

**Anti-pattern examples (explicitly forbidden):**
- "Please execute the full ceremony" → not authorization; each step must be named.
- "Approved to test OAuth" → not authorization; test scope must be named (dry-run vs real, browser vs no-browser, etc.).
- "Go ahead" → not authorization; must reference the exact prior message that named the actions.

---

## G. Secret and Credential Handling Boundary

**Absolute rules — no exception permitted in Phase 1 or any subsequent phase without a separately authorized channel:**

| Rule | Statement |
|---|---|
| G1 | Chat sessions of any kind (Claude Code, ChatGPT, Slack, GitHub, any observed session) are **forbidden channels** for real secrets. |
| G2 | Git commits, PR descriptions, issue comments, and commit messages are **forbidden channels** for real secrets. |
| G3 | Log files, terminal history, shell recording, and screen recording are **forbidden channels** for real secrets. |
| G4 | Repository documentation files are **forbidden channels** for real secrets, including any file under `docs/`, `openclaw/`, `scripts/`, or root. |
| G5 | Screenshots containing real credential values, real customer IDs, real project IDs, real emails, real OAuth URLs, real callback URLs, real auth codes, real tokens, real client secrets, or real resource paths are **forbidden**. |
| G6 | Real credential values must **never be printed** to any terminal that could be recorded, screen-shared, or observed by a non-authorized party. |
| G7 | Any real credential intake must use an **approved secure channel** from the V5.21 credential handoff protocol Section D acceptable list, subject to the conditions in that section. |
| G8 | Any Secret Manager write must be reported in metadata-only form: field count, status boolean, secret name presence — never raw payload, never resource path. |
| G9 | Report only statuses (`configured=true`), never values. |
| G10 | If a real value is inadvertently produced (e.g., an auth code appears in a redirect URI shown in a browser), the immediate action is: do not copy, do not paste, close the tab or window, invoke Section H stop conditions, and initiate rollback/revoke. |

**Forbidden token/pattern committed anywhere in this repo:**
- Any string matching `ya29\.[A-Za-z0-9_-]{10,}` (OAuth access token)
- Any string matching `1//[A-Za-z0-9_-]{20,}` (Google refresh token pattern)
- Any string matching `4/0A[A-Za-z0-9_-]{20,}` (Google auth code pattern)
- Any string matching `sk-[A-Za-z0-9_-]{10,}` (API key pattern)
- Any string matching `projects/[0-9]+/secrets/[^/]+/versions/[0-9]+` (Secret Manager resource path with real project number)
- Any string matching `[0-9]{3}-[0-9]{3}-[0-9]{4}` in a customer_id context (Google Ads customer ID pattern)
- Any real developer token, client secret, or service account email
- Any real Google Ads OAuth URL beyond the schema `https://accounts.google.com/o/oauth2/` in documentation-only contexts

---

## H. Stop Conditions

Any of the following conditions require an immediate halt of any V5.23 activity. No exception. On stop, do not continue; invoke the applicable rollback flow; notify the user; document the stop condition in an out-of-repo evidence record.

| # | Stop condition |
|---|---|
| H-01 | A real secret value (token, refresh token, access token, client secret, developer token, customer ID, login customer ID, project ID, resource path, service account email, credential ref, secret name for real project) appears in chat, log, terminal output, or any file in the repository. |
| H-02 | An OAuth authorization URL is generated without a matching explicit approval that names the URL generation step. |
| H-03 | A browser is opened for an OAuth flow without a matching explicit approval that names the browser step. |
| H-04 | A callback URL appears in any location outside the approved secure channel. |
| H-05 | An auth code appears in chat, log, or any committed file. |
| H-06 | A token (access or refresh) appears in chat, log, or any committed file. |
| H-07 | Token exchange is attempted without a matching explicit approval that names the token exchange step. |
| H-08 | A Secret Manager write is attempted without a matching explicit approval that names the write step and the target secret path. |
| H-09 | A Google Ads API call is attempted without a matching explicit approval that names the API call, the operation (read-only), and the target customer. |
| H-10 | A GCP command or GCP API call is attempted without a matching explicit approval that names the operation and the target project. |
| H-11 | `GOOGLE_ADS_LIVE_ENABLED=true` appears in a runtime environment without a matching explicit approval that names the activation. |
| H-12 | Any V5.19–V5.22 validator returns FAIL. |
| H-13 | Either smoke suite (`smoke_test_v5_credentials.sh`, `smoke_test_v5_12_gcp_secret_manager.sh`) fails. |
| H-14 | Safety grep produces a sensitive hit (a match that is not documentation-only, prohibition text, or a Section F/G table label). |
| H-15 | The working tree is not clean at the start of a phase; unexpected files are present; staging or diff shows content not part of the phase scope. |
| H-16 | Operator identity is unclear (e.g., a message references "the team" without naming a specific human authorizer). |
| H-17 | Tenant or client scope is unclear (e.g., no named tenant ref in an authorization request). |
| H-18 | Rollback owner or emergency revoke owner is unavailable at the time of any live step. |
| H-19 | Approval record is missing, expired, revoked, or has scope that does not match the requested action. |
| H-20 | Any authorization message is a paraphrase or summary of a prior message rather than a verbatim, explicit statement of the actions to take. |
| H-21 | Any action exceeds its allotted time window without an explicit continue-approval. |
| H-22 | Screen recording, screen sharing, or observed session is active at any credential handling step. |
| H-23 | Any V5.23 planning or validator produces output that references a real credential value, a real resource path, or a real account identifier. |
| H-24 | Any V5.23 committed file introduces an import of `google.cloud`, `google.ads`, `requests`, `urllib`, `httpx`, `webbrowser`, `subprocess`, or `socket` outside the pre-existing V5.12–V5.22 infrastructure. |
| H-25 | Any phase-scope creep is detected (e.g., an "innocent" edit to a validator that widens a permission or removes a stop condition). |

---

## I. Required Safety Checks

The following safety checks must be run at every V5.23 phase — before, during, and after any work. Each phase must confirm all of these PASS before commit.

**Safety greps (all 9 patterns must be CLEAN, or hits must be documentation/prohibition/table-label text only):**

| # | Pattern | Purpose |
|---|---|---|
| I-01 | `ya29\.[A-Za-z0-9_-]{10,}` | OAuth access token |
| I-02 | `sk-[A-Za-z0-9_-]{10,}` | API key |
| I-03 | `GOOGLE_APPLICATION_CREDENTIALS=/` | Credential file path |
| I-04 | `credential_ref.*projects/` | Real GCP credential ref |
| I-05 | `secret_id.*projects/` | Real Secret Manager path |
| I-06 | `customer_id.*[0-9]` | Real Google Ads customer ID |
| I-07 | `login_customer_id.*[0-9]` | Real Google Ads manager ID |
| I-08 | `auth code.*[A-Za-z0-9_-]{10,}` | Real auth code (case-insensitive) |
| I-09 | `https://accounts.google.com/o/oauth2` | Generated OAuth URL |

**Forbidden imports (in any new V5.23 module, if any):**
- `google.cloud` (any submodule)
- `google.ads` (any submodule)
- `requests`
- `urllib` (any submodule)
- `httpx`
- `webbrowser`
- `subprocess`
- `socket`

Exception: modules already present in the V5.12–V5.22 baseline may retain their existing imports. V5.23 must not add new modules that import from the forbidden list.

**Suite runs (all must PASS at every phase):**

| # | Suite | Expected |
|---|---|---|
| I-10 | `openclaw/run_oauth_dry_run_execution_demo.py` | 112 PASS |
| I-11 | `openclaw/run_oauth_approval_packet_demo.py` | 110 PASS |
| I-12 | `openclaw/run_oauth_callback_demo.py` | 98 PASS |
| I-13 | `openclaw/run_oauth_auth_url_demo.py` | 82 PASS |
| I-14 | `openclaw/run_secret_version_policy_demo.py` | 71 PASS |
| I-15 | `openclaw/run_credential_intake_demo.py` | 70 PASS |
| I-16 | `openclaw/run_rollback_drill_demo.py` | 67 PASS |
| I-17 | `openclaw/run_onboarding_ceremony_demo.py` | PASS |
| I-18 | `scripts/smoke_test_v5_credentials.sh` | 35/35 PASS |
| I-19 | `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | 8/8 PASS |

**Repository hygiene checks:**

| # | Check | Expected |
|---|---|---|
| I-20 | `git status` clean at phase start (or shows only phase-scope files) | PASS |
| I-21 | `git branch --show-current` returns `v5.23-controlled-real-oauth-execution-planning` | PASS |
| I-22 | No `.env` file anywhere in the repository | PASS |
| I-23 | No credential JSON file anywhere in the repository | PASS |
| I-24 | No `GOOGLE_APPLICATION_CREDENTIALS` value pointing to a real credential file appears in any committed file | PASS |
| I-25 | No real GCP resource path (`projects/<real>/secrets/<real>/versions/<n>`) appears in any committed file | PASS |
| I-26 | No `.venv/`, secret files, or runtime artifacts staged for commit | PASS |

**Aggregate assertion count carried from V5.22 baseline:** 610 explicit assertions. Any V5.23 phase must not reduce this count without explicit user approval.

---

## J. Deferred Beyond V5.23 Phase 1

The following items are explicitly deferred beyond V5.23 Phase 1. Each requires separate explicit authorization at the time it becomes relevant. No item may be inferred as authorized by completion of Phase 1.

1. Real OAuth execution.
2. Real approval creation (with real operator identity, real tenant scope, real execution window).
3. Real credential handoff.
4. Real authorization URL generation.
5. Browser execution and OAuth consent.
6. Callback and auth-code handling.
7. Token exchange with Google OAuth token endpoint.
8. Token storage in Secret Manager.
9. Secret Manager write with real credentials.
10. Google Ads API call (read-only or otherwise).
11. `GOOGLE_ADS_LIVE_ENABLED=true` runtime activation.
12. Deploy (Cloud Run, App Engine, any compute).
13. GCP command or GCP API call.
14. IAM changes, API enablement, billing account modifications.
15. Rollback or revocation of real credentials.
16. GitHub Release publication for V5.23.
17. Merge to master for V5.23.
18. Tag `v5.23.0-beta` creation.

---

## K. Phase 1 Acceptance Criteria

Phase 1 is complete only if **all** of the following are true:

| # | Criterion | Status |
|---|---|---|
| K-01 | Branch `v5.23-controlled-real-oauth-execution-planning` created from master at `4217652` | [ ] |
| K-02 | `docs/V5_23_IMPLEMENTATION_PLAN.md` created with Sections A–L | [ ] |
| K-03 | `README.md` updated with V5.23 current-milestone bullet and `docs/V5_23_IMPLEMENTATION_PLAN.md` link | [ ] |
| K-04 | `docs/ROADMAP.md` updated: V5.22 marked shipped; V5.23 section added with Phase 1 `[x]` and Phases 2–10 `[ ]` | [ ] |
| K-05 | Latest shipped release in README remains `v5.22.0-beta` | [ ] |
| K-06 | V5.23 not marked shipped in README | [ ] |
| K-07 | V5.23 not marked shipped in ROADMAP | [ ] |
| K-08 | All 9 safety greps clean or documentation-only hits | [ ] |
| K-09 | All 8 demos PASS | [ ] |
| K-10 | `smoke_test_v5_credentials.sh` 35/35 PASS | [ ] |
| K-11 | `smoke_test_v5_12_gcp_secret_manager.sh` 8/8 PASS | [ ] |
| K-12 | Working tree contains only Phase 1 scope files | [ ] |
| K-13 | No real credentials, OAuth, tokens, auth codes, GCP calls, or Secret Manager calls occurred | [ ] |
| K-14 | `GOOGLE_ADS_LIVE_ENABLED` was not activated at any point | [ ] |
| K-15 | No merge, tag, push, or release performed | [ ] |

---

## L. Phase 1 Conclusion

V5.23 Phase 1 creates the planning foundation for the first controlled real OAuth execution. It defines the authorization architecture, per-step approval model, secret and credential handling boundary, stop conditions, safety-check envelope, and deferred-execution phases.

**V5.23 Phase 1 does not authorize any real execution.** It does not authorize a real approval packet, a real OAuth URL, a browser OAuth flow, a callback receipt, an auth code, a token exchange, a Secret Manager write, a Google Ads API call, a GCP command, an IAM change, an API enablement, a billing change, a deploy, or `GOOGLE_ADS_LIVE_ENABLED=true` activation. It does not authorize real rollback or revocation.

**Phase 2 (real ceremony authorization packet template) remains pending.** Phases 3–5 (protocol finalization, execution runbook, pre-execution review) also remain pending. Phases 6–8 (real execution) remain pending separate explicit authorization at each live step. Phases 9–10 (closure and release) remain pending completion of prior authorized work.

**`GOOGLE_ADS_LIVE_ENABLED` remains false. No real OAuth was executed. No real credentials were used. No Google Ads API was called. No GCP commands were run. No Secret Manager was accessed.**

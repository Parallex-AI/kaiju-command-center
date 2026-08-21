# V5.21 Implementation Plan — Controlled Real Google Ads OAuth Onboarding Ceremony

**Branch:** `v5.21-controlled-real-google-ads-oauth-onboarding`
**Base:** `v5.20.0-beta` / master at `5a4c692`
**Status:** Phase 1 — planning
**Purpose:** Prepare a controlled real Google Ads OAuth onboarding ceremony design.

---

**This plan does not authorize execution.**
**This plan does not request real credentials.**
**This plan does not execute OAuth.**
**This plan does not call Google Ads API.**
**This plan does not call GCP or Secret Manager.**
**`GOOGLE_ADS_LIVE_ENABLED` remains false throughout.**

---

## A. Objective

V5.21 converts V5.20's readiness controls into an operator-safe ceremony design for a future real Google Ads OAuth onboarding event. The purpose of early V5.21 phases is to produce ceremony documents, local validators, a dry-run runbook, and an approval packet model — all without executing any real onboarding, OAuth flow, or API call.

V5.20 established the local readiness layer: ceremony checklist, intake dry-run validator, rollback drill validator, version lifecycle policy validator, and final readiness review. V5.21 extends this by designing the ceremony control structures, authorization URL boundary, token-exchange boundary, credential handoff protocol, and operator approval packet that an authorized future execution would need to follow.

The critical distinction: V5.21 designs how real OAuth onboarding would be controlled. It does not perform real OAuth onboarding. Any real execution requires a separate explicit operator authorization that is outside the scope of this branch and cannot be inferred from V5.21's PASS status.

---

## B. Non-Authorization Statement

V5.21 Phase 1 is not approval to onboard a real client.
V5.21 Phase 1 is not approval to receive real secrets.
V5.21 Phase 1 is not approval to execute OAuth.
V5.21 Phase 1 is not approval to open an OAuth browser flow.
V5.21 Phase 1 is not approval to call Google Ads API.
V5.21 Phase 1 is not approval to write real credentials to Secret Manager.
V5.21 Phase 1 is not approval to activate `GOOGLE_ADS_LIVE_ENABLED=true`.
V5.21 Phase 1 is not approval to deploy.
V5.21 Phase 1 is not approval to run GCP commands.
V5.21 Phase 1 is not approval to call IAM, billing, or GCP APIs.

This non-authorization statement applies to every V5.21 phase unless a later phase receives explicit operator authorization. Each execution phase requires its own separate per-phase operator authorization.

---

## C. V5.20 Dependencies

V5.21 builds on V5.20's completed readiness infrastructure. All of the following must be available and PASS before any future V5.21 real execution ceremony can proceed:

| Dependency | Source |
|---|---|
| Real onboarding checklist | `docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md` |
| Onboarding ceremony validator | `openclaw/onboarding_ceremony.py` · `validate_onboarding_ceremony()` |
| Credential intake dry-run validator | `openclaw/credential_intake.py` · `validate_credential_intake_dry_run()` |
| First live API validation plan | `docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md` |
| Rollback and emergency revoke drill validator | `openclaw/rollback_drill.py` · `validate_rollback_drill()` |
| Secret Manager version lifecycle policy validator | `openclaw/secret_version_policy.py` · `validate_secret_version_policy()` |
| Final readiness review | `docs/V5_20_FINAL_READINESS_REVIEW.md` |
| Live gate and preflight checker | `openclaw/live_gate.py` · `openclaw/preflight.py` (V5.19) |
| Approval record model and local store | `openclaw/approval.py` (V5.19) |
| Server preflight route | `openclaw/server.py` (V5.19) |
| Live guard audit events | `openclaw/audit.py` (V5.19) |
| Credential lifecycle and audit chain | `openclaw/admin.py` · `openclaw/audit.py` (V5.15–V5.16) |
| Admin RBAC and token scopes | `openclaw/auth.py` · `AdminScope` (V5.16) |
| Tenant isolation | `openclaw/config.py` · `OPENCLAW_TENANT_KEYS` (V5.17) |
| Rate limiting | `openclaw/rate_limit.py` (V5.17) |
| Audit persistence hardening | `fcntl.flock` audit append (V5.17) |

---

## D. Proposed V5.21 Phases

### Phase 1 — Planning and branch setup
**Purpose:** Establish branch, implementation plan, ROADMAP entry, README entry.
**Deliverables:** `docs/V5_21_IMPLEMENTATION_PLAN.md`; ROADMAP update; README update; branch `v5.21-controlled-real-google-ads-oauth-onboarding`.
**No-real-execution constraint:** No OAuth. No credentials. No GCP. No API calls. No deployment.
**Validation:** Safety grep clean. Existing smoke suites pass (31/31 · 8/8).

### Phase 2 — OAuth ceremony checklist document
**Purpose:** Produce a structured operator-controlled OAuth ceremony checklist covering pre-ceremony gate verification, authorization URL review, scope confirmation, callback validation confirmation, and token-exchange boundary confirmation.
**Deliverables:** `docs/GOOGLE_ADS_OAUTH_CEREMONY_CHECKLIST.md`; operator ceremony template; stop conditions specific to OAuth; rollback sequence for OAuth-specific failure modes; sign-off block.
**No-real-execution constraint:** Checklist is a prerequisite template only. It does not authorize execution. No real URL generation. No real scopes requested.
**Validation:** Document review. Safety grep clean. Existing smoke suites pass.

### Phase 3 — OAuth authorization URL design validator (local-only)
**Purpose:** Implement a local-only validator that checks an `OAuthAuthorizationURLInput` against all ceremony boundary rules before any real authorization URL could be generated. The validator evaluates structure, scope list, redirect URI format, state parameter presence, and operator confirmation — it does not generate or open a real URL.
**Deliverables:** `openclaw/oauth_auth_url.py`; `OAuthAuthorizationURLInput` dataclass; `validate_oauth_auth_url_design()`; failure codes; demo script; smoke section.
**No-real-execution constraint:** Pure stdlib Python. No network. No browser. No Google OAuth client. No real client ID or secret values in inputs. Does not call `google.oauth2`, `requests`, or `httpx`.
**Validation:** Demo script runs and passes. Smoke section added. Safety grep clean.

### Phase 4 — OAuth callback and token-exchange boundary design (local-only)
**Purpose:** Implement a local-only validator that checks an `OAuthCallbackInput` against all boundary rules for the callback and token-exchange step: presence of authorization code, absence of error parameter, redirect URI match, state parameter match, operator-present confirmation, and forbidden-value detection. Does not perform a real token exchange.
**Deliverables:** `openclaw/oauth_callback.py`; `OAuthCallbackInput` dataclass; `validate_oauth_callback_design()`; failure codes; demo script; smoke section.
**No-real-execution constraint:** Pure stdlib Python. No network. No real authorization codes. No real token exchange. Does not call `google.auth`, `requests`, or `httpx`. Forbidden value patterns include authorization code shape, token shape, and secret resource paths.
**Validation:** Demo script runs and passes. Smoke section added. Safety grep clean.

### Phase 5 — Secure credential handoff protocol design (no real secrets)
**Purpose:** Design the protocol by which OAuth output (refresh token, access token, client ID, client secret, developer token, customer IDs) would be securely handed off to the Secret Manager write path under V5.15–V5.17 infrastructure. Design only — no real secrets, no real write, no real Secret Manager call.
**Deliverables:** `docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md`; handoff sequence; forbidden transmission channels; acceptable transmission channels; Secret Manager write path reference; audit requirements for handoff; revocation path.
**No-real-execution constraint:** Design document only. No credential values. No resource paths. No GCP commands. No Secret Manager calls.
**Validation:** Document review. Safety grep clean.

### Phase 6 — Operator approval packet model for real onboarding
**Purpose:** Define the structure of an operator approval packet required before any real Google Ads OAuth ceremony can be authorized. The packet model covers: named operator identity, tenant/client identifier (redacted in docs), approval scope, approval expiry, rollback plan reference, evidence package path, required countersignatures, and stop authority.
**Deliverables:** `openclaw/oauth_approval_packet.py`; `OAuthApprovalPacketInput` dataclass; `validate_oauth_approval_packet()`; failure codes; demo script; smoke section.
**No-real-execution constraint:** Pure stdlib Python. No real operator identities. No real tenant/client IDs in demo inputs. No GCP. No network.
**Validation:** Demo script runs and passes. Smoke section added. Safety grep clean.

### Phase 7 — Dry-run onboarding runbook and timed execution window model
**Purpose:** Produce a detailed dry-run operator runbook for the full OAuth onboarding ceremony, including a timed execution window model that defines maximum ceremony duration, mandatory pause points, rollback decision checkpoints, and evidence capture requirements. The runbook is a rehearsal reference only.
**Deliverables:** `docs/GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md`; step-by-step runbook; timed execution window model; pause points and checkpoints; rollback trigger conditions; post-ceremony evidence checklist.
**No-real-execution constraint:** Design document only. No credential values. No resource paths. No GCP commands.
**Validation:** Document review. Safety grep clean.

### Phase 8 — Pre-execution final review and gap analysis
**Purpose:** Assess all V5.21 deliverables against the V5.20 readiness infrastructure and produce a final pre-execution readiness review documenting: all validators PASS, all ceremony docs present, gap analysis, remaining blockers (if any), and explicit NOT APPROVED statement for real execution.
**Deliverables:** `docs/V5_21_FINAL_READINESS_REVIEW.md`; 10-section local readiness assessment; validator assertion counts; gap analysis; mandatory pre-execution checklist; stop conditions; NOT APPROVED statement.
**No-real-execution constraint:** Local assessment only. No OAuth. No GCP. No API calls.
**Validation:** All validators PASS. Smoke suites pass. Safety grep clean. Final review states NOT APPROVED for real execution.

### Phase 9 — Branch closure docs and release notes
**Purpose:** Produce branch closure documentation and v5.21.0-beta release notes.
**Deliverables:** `docs/V5_21_BRANCH_CLOSURE.md`; `docs/RELEASE_NOTES_V5_21_0_BETA.md`; ROADMAP/README updates.
**No-real-execution constraint:** Documentation only. No OAuth. No GCP. No API calls. No deployment.
**Validation:** Smoke suites pass. Safety grep clean. Working tree clean.

### Phase 10 — Merge, tag, release
**Purpose:** Merge `v5.21-controlled-real-google-ads-oauth-onboarding` to master, create annotated tag `v5.21.0-beta`, push, and publish GitHub Release.
**Deliverables:** Merge commit on master; tag `v5.21.0-beta`; GitHub Release.
**No-real-execution constraint:** No OAuth. No GCP. No API calls. No deployment.
**Validation:** Smoke suites pass on master. Tag verified. Release published.

---

## E. Explicitly Deferred Beyond Phase 1

The following items are explicitly deferred beyond V5.21 Phase 1. Each requires its own separate operator authorization before any work can proceed:

| Item | Deferred to |
|---|---|
| Real OAuth browser execution | Separate explicit authorization beyond V5.21 |
| Real Google OAuth consent screen interaction | Separate explicit authorization |
| Real refresh token acquisition | Separate explicit authorization |
| Real access token use | Separate explicit authorization |
| Real developer token usage | Separate explicit authorization |
| Real customer ID or login customer ID verification | Separate explicit authorization |
| Real Secret Manager write with OAuth output | Separate explicit authorization |
| Real Google Ads API call | Separate explicit authorization |
| `GOOGLE_ADS_LIVE_ENABLED=true` runtime activation | Separate explicit authorization |
| Production Cloud Run deployment | Requires service account, IAM, billing authorization |
| IAM changes | Separate explicit authorization |
| Billing changes | Separate explicit authorization |
| GCP API enablement | Separate explicit authorization |
| Real client onboarding to production | Separate explicit authorization |
| External approval UI | Deferred |

---

## F. Security Model

All V5.21 phases must adhere to the following security constraints:

| Constraint | Rule |
|---|---|
| Secrets in chat | Never — no real token, credential, or secret value in any Claude Code session |
| Secrets in repo | Never — no `.env`, no credential JSON, no `GOOGLE_APPLICATION_CREDENTIALS` file |
| Secrets in docs | Never — all docs use redacted placeholders only; no real project IDs, account emails, customer IDs, or resource paths |
| Secrets in logs | Never — local demo scripts must not log real credential values |
| OAuth code in docs | Never — no real authorization codes, no real redirect URIs containing live parameters |
| Token/resource paths in docs | Never — no GCP resource paths, no `projects/*/secrets/*` paths |
| Screenshots | Never — no screenshots containing credentials or sensitive session data |
| Real execution channel | All real OAuth execution, if ever authorized, must use an operator-controlled secure channel outside this repo and chat session |
| Forbidden imports | All local validators: no `network`, `requests`, `urllib`, `httpx`, `google.cloud`, `google.ads`, `google.oauth2`, or `google.auth` imports |
| Forbidden field names | All validators must reject credential-shaped field names in evidence/metadata inputs |
| Forbidden value patterns | All validators must reject token-shaped, secret-path-shaped, and customer-ID-shaped values in inputs |

---

## G. Ceremony Control Model

Any future real Google Ads OAuth onboarding ceremony must define the following roles and controls before it can be authorized:

| Component | Requirement |
|---|---|
| Named operator | Identified person responsible for ceremony execution; must be present throughout |
| Tenant/client identifier | Identified in approval record; redacted in all committed docs |
| Approval record | Valid `ApprovalRecord` (V5.19); APPROVED status; not expired; countersigned |
| Explicit time window | Start time; end time; maximum ceremony duration; hard stop if exceeded |
| Preflight | `check_live_operation_preflight()` must PASS before any step proceeds |
| V5.20 validators | All 4 validators must PASS: ceremony, intake dry-run, rollback drill, version policy |
| OAuth ceremony checklist | All items checked (V5.21 Phase 2 checklist) |
| Rollback owner | Named person responsible for executing rollback if triggered |
| Emergency revoke owner | Named person with authority to immediately revoke credentials |
| Evidence owner | Named person responsible for capturing and storing evidence package |
| Post-execution verifier | Named person who confirms post-ceremony state independently of executor |
| Stop authority | Named person with authority to call an immediate halt at any step |
| Audit enabled | `OPENCLAW_AUDIT_ENABLED=true` confirmed before ceremony begins |
| Smoke suites | Both smoke suites must PASS immediately before ceremony window opens |

---

## H. Stop Conditions

Any of the following conditions require an immediate halt and rollback during a future ceremony:

1. Any secret, token, credential value, or GCP resource path appears in chat, logs, repo, or docs.
2. Approval record missing, expired, or revoked at any point during ceremony.
3. Wrong tenant or client identifier confirmed in any ceremony step.
4. OAuth scope list does not match approved scope list exactly.
5. Token exchange returns unexpected response shape or error code.
6. Authorization code cannot be confirmed as single-use.
7. `GOOGLE_ADS_LIVE_ENABLED` cannot be reverted to false after ceremony.
8. Google Ads API response contains unexpected customer data or error.
9. Secret Manager write response does not confirm expected field count.
10. Audit chain cannot be verified after any write step.
11. Audit disabled or audit file unwritable during ceremony.
12. Rollback path is missing or has not been rehearsed since last version policy change.
13. Any smoke test fails immediately before ceremony window opens.
14. Safety grep finds real credential or resource path in any committed file.
15. Operator leaves ceremony window without named substitute on record.
16. Emergency revoke owner unreachable.
17. Evidence capture fails for any ceremony step.
18. Any ceremony step exceeds its allotted time without operator approval to continue.

---

## I. Success Criteria for V5.21 Beta

V5.21.0-beta is successful only if all of the following are true:

| Criterion | Requirement |
|---|---|
| OAuth ceremony checklist exists | `docs/GOOGLE_ADS_OAUTH_CEREMONY_CHECKLIST.md` present |
| Authorization URL design validator exists and passes | `openclaw/oauth_auth_url.py` · demo PASS |
| Callback/token-exchange boundary validator exists and passes | `openclaw/oauth_callback.py` · demo PASS |
| Credential handoff protocol design exists | `docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md` present |
| Operator approval packet validator exists and passes | `openclaw/oauth_approval_packet.py` · demo PASS |
| Dry-run onboarding runbook exists | `docs/GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md` present |
| Pre-execution final review exists and states NOT APPROVED | `docs/V5_21_FINAL_READINESS_REVIEW.md` present; NOT APPROVED for real execution |
| All smoke suites pass | 31/31 · 8/8 (or extended) |
| No real OAuth executed | Confirmed |
| No real credentials used | Confirmed |
| No Google Ads API called | Confirmed |
| No GCP or Secret Manager called | Confirmed |
| No deployment | Confirmed |
| `GOOGLE_ADS_LIVE_ENABLED` remains false | Confirmed |
| Safety grep clean | Confirmed on all changed files |

---

## J. Phase 1 Acceptance Criteria

- [x] New branch `v5.21-controlled-real-google-ads-oauth-onboarding` created from master at `5a4c692`.
- [x] `docs/V5_21_IMPLEMENTATION_PLAN.md` created with all required sections A–J.
- [x] `README.md` references V5.21 in progress with explicit non-authorization statement.
- [x] `docs/ROADMAP.md` references V5.21 phases.
- [x] Safety grep clean on all Phase 1 changed files.
- [x] `scripts/smoke_test_v5_credentials.sh` PASS (31/31).
- [x] `scripts/smoke_test_v5_12_gcp_secret_manager.sh` PASS (8/8).
- [x] No runtime or cloud changes of any kind.
- [x] `GOOGLE_ADS_LIVE_ENABLED` remains false by default.

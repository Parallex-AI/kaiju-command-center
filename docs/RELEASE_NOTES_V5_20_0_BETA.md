# Release Notes — v5.20.0-beta

**Branch:** `v5.20-controlled-real-google-ads-onboarding-readiness`
**Base:** `v5.19.0-beta` / master after `631abbd`
**Tag candidate:** `v5.20.0-beta`
**Status:** Complete — Phases 1–8 PASS · closure docs complete · ready for merge and tag

---

## Release Summary

v5.20.0-beta adds the local readiness layer required before any future real Google Ads credential onboarding or first live API validation. Building on V5.19's live gate, approval records, preflight infrastructure, and audit model, V5.20 provides operator checklists, onboarding ceremony validation, credential intake dry-run validation, a first live API validation plan, rollback and emergency revoke drill validation, Secret Manager version lifecycle policy validation, and a final readiness review across eight phases.

V5.20 implements controlled real Google Ads onboarding readiness only. V5.20 does not authorize real Google Ads credential onboarding. V5.20 does not validate real Google Ads credentials. V5.20 does not call the Google Ads API. V5.20 does not execute OAuth onboarding. V5.20 does not deploy to production. V5.20 does not change IAM, billing, APIs, or cloud architecture. `GOOGLE_ADS_LIVE_ENABLED` remains false by default. No GCP operations were performed.

---

## Highlights

- **`validate_onboarding_ceremony()` — onboarding ceremony model validator** — enforces all readiness, approval, boundary, and forbidden-field/value conditions before any ceremony can proceed; 36-assertion demo; local-only; no network or GCP imports
- **`validate_credential_intake_dry_run()` — credential intake dry-run validator** — enforces 7 intake boundary rules, 4 plan requirements, 4 reference confirmations, and 6 hard-stop detection conditions; 25 failure codes; 70-assertion demo; local-only; does not ingest real credentials
- **Google Ads First Live API Validation Plan** — design document; 19-item precondition checklist; 17 stop conditions; 11-step rollback sequence; evidence package; no execution, no real credentials, no API calls
- **`validate_rollback_drill()` — rollback and emergency revoke drill validator** — validates full rollback sequence including live flag confirmation, approval revocation, credential revocation, bundle deletion, audit chain verification, and live gate denial; 20 failure codes; 67-assertion demo; local-only
- **`validate_secret_version_policy()` — Secret Manager version lifecycle policy validator** — enforces `DISABLE_PREVIOUS_WITH_GRACE_PERIOD` as V5.20 authorized policy; rejects all 3 unauthorized modes; 19 failure codes; 4 lifecycle modes; 20 forbidden field names; 13 forbidden value patterns; 71-assertion demo; local-only
- **Final readiness review** — 10-section local assessment (Sections A–J); all V5.20 validators PASS; 244 total assertions; gap analysis; 0 open blockers; 15-item mandatory pre-execution checklist; 18 stop conditions; NOT approved for real execution
- **Smoke suite extended from 26/26 to 31/31** — five new V5.20 sections; no regressions in existing tests

---

## What's New

### Phase 2 — Real onboarding checklist document

`docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md` provides a structured operator-controlled ceremony checklist covering pre-ceremony gate verification, approval record confirmation, execution window and team confirmation, step-by-step ceremony procedure, stop conditions, rollback sequence, and post-ceremony audit. The checklist does not authorize execution; it is a prerequisite template for operator use under future separate authorization.

### Phase 3 — Onboarding ceremony model and checklist validator

`openclaw/onboarding_ceremony.py` implements `validate_onboarding_ceremony()`, a pure local Python function that evaluates an `OnboardingCeremonyInput` dataclass against all ceremony readiness, approval, boundary, and forbidden-field/value conditions. It returns a structured `OnboardingCeremonyResult` with pass/fail status, failure codes, failure messages, and a sanitized summary. It does not execute real onboarding, call OAuth, call GCP, or make any network calls.

**Key conditions enforced:**
- Live mode must not be pre-enabled
- Approval record must be present, APPROVED, and not expired
- All V5.19 gate conditions must be satisfied
- Credential reference must not carry forbidden fields (customer IDs, secret resource paths, token values)
- Operator confirmation and rollback plan must be on record
- Evidence package path must be declared
- Metadata must contain no forbidden field names or forbidden value patterns

### Phase 4 — Credential intake dry-run validator

`openclaw/credential_intake.py` implements `validate_credential_intake_dry_run()`, a pure local Python function evaluating a `CredentialIntakeDryRunInput` against all boundary rules before any credential intake ceremony can proceed. It returns a structured `CredentialIntakeDryRunResult` with 25 discrete failure codes.

**Key boundary rules enforced:**
- 7 intake boundary rules: live mode pre-activation blocked; operator confirmation required; rollback plan required; OAuth pre-execution blocked; direct API calls blocked; GOOGLE_ADS_LIVE_ENABLED pre-setting blocked; intake limited to one credential bundle
- 4 plan requirements: valid target environment; valid integration type; evidence package path declared; audit path declared
- 4 reference confirmations: credential store path declared; credential store valid identifier; no active credential present without explicit replacement flag; audit file writable confirmed
- 6 hard-stop detection conditions: access token pattern in any field; refresh token pattern; client secret pattern; forbidden secret resource path; forbidden customer ID pattern; forbidden credential value pattern

### Phase 5 — First live API validation plan

`docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md` provides a design-only plan for the first controlled read-only Google Ads API validation. Key elements:

| Element | Detail |
|---|---|
| Precondition checklist | 19 items — all must be satisfied before any execution |
| Execution window constraints | Defined working hours; operator present throughout |
| Audit sequence | 10 steps emitting audit events at each stage |
| Stop conditions | 17 conditions requiring immediate halt and rollback |
| Rollback sequence | 11 steps: live flag revert → approval revocation → credential revocation → bundle deletion → audit verification → gate denial confirmation |
| Evidence package | Required before, during, and after execution |

The plan does not authorize execution. Execution requires separate explicit operator approval.

### Phase 6 — Rollback and emergency revoke drill validator

`openclaw/rollback_drill.py` implements `validate_rollback_drill()`, a pure local Python function that validates the complete rollback sequence including live flag confirmation, approval revocation, credential revocation, bundle deletion, audit chain verification, and live gate denial confirmation. It provides 20 failure codes, 19 forbidden field names, and 12 forbidden value patterns.

**Key sequence steps validated:**
- `live_enabled_confirmed`: live flag was confirmed active before rollback
- `live_flag_reverted`: live flag reverted to false
- `approval_revoked`: approval record set to REVOKED status
- `credential_revoked`: credential reference marked REVOKED
- `bundle_deleted`: secret bundle deleted from secret store
- `audit_chain_verified`: audit event chain verified post-rollback
- `live_gate_denial_confirmed`: live gate correctly denies after rollback
- `rollback_evidence_saved`: rollback evidence package saved

### Phase 7 — Secret Manager version lifecycle policy validator

`openclaw/secret_version_policy.py` implements `validate_secret_version_policy()`, a pure local Python function that enforces the V5.20 authorized Secret Manager version lifecycle policy. The V5.20 authorized mode is `DISABLE_PREVIOUS_WITH_GRACE_PERIOD`.

**4 lifecycle modes evaluated:**
| Mode | V5.20 status |
|---|---|
| `DISABLE_PREVIOUS_WITH_GRACE_PERIOD` | Authorized — requires grace period 1–168 hours |
| `KEEP_ALL_VERSIONS` | Rejected — forbidden; accumulates live versions |
| `DESTROY_PREVIOUS_IMMEDIATELY` | Rejected — forbidden; irreversible without grace period |
| `MANUAL_OPERATOR_ONLY` | Rejected — blocked; requires explicit override |

**19 failure codes** across 5 lifecycle, 6 policy, 6 detection, and 2 forbidden categories.

### Phase 8 — Final readiness review

`docs/V5_20_FINAL_READINESS_REVIEW.md` is a 10-section local-only readiness assessment.

| Section | Content |
|---|---|
| A — Scope and constraints | 12 confirmed constraints |
| B — Phase matrix | All 10 phases: 8 PASS, 9 complete, 10 pending |
| C — Readiness gates | 6 gates + V5.19 dependency + audit + stop conditions |
| D — Evidence package | 4 demos + 2 smoke suites; 244 total assertions |
| E — Security properties | 22 confirmed properties |
| F — Gap analysis | 0 open blockers; 13 deferred items |
| G — Pre-execution checklist | 15-item mandatory checklist (G1–G15) |
| H — Stop conditions | 18 stop conditions |
| I — Release readiness decision | PASS for V5.20.0-beta after Phase 9; NOT approved for real execution |
| J — Next steps | Phase 9 closure and Phase 10 merge/tag/release |

---

## Confirmed Behaviors

| Behavior | Confirmed by |
|---|---|
| All 4 validators are pure stdlib Python — no GCP, Secret Manager, Google Ads, or network imports | Safety grep CLEAN; all demo runs |
| `validate_onboarding_ceremony()` returns structured result with sanitized summary; no forbidden fields in output | Phase 3 demo |
| `validate_credential_intake_dry_run()` enforces all 25 failure codes; hard-stop detection catches token/secret patterns | Phase 4 demo |
| `validate_rollback_drill()` correctly denies incomplete rollback sequences and detects forbidden fields/values | Phase 6 demo |
| `validate_secret_version_policy()` authorizes only `DISABLE_PREVIOUS_WITH_GRACE_PERIOD`; rejects 3 other modes | Phase 7 demo |
| All 4 validators reject forbidden credential/secret/resource field names in evidence/metadata inputs | All demos PASS |
| All 4 validators reject forbidden credential value patterns (token strings, resource paths, customer ID patterns) | All demos PASS |
| Smoke suite extended from 26/26 to 31/31 with no regressions in existing 26 sections | Phases 3–8; smoke final PASS |
| V5.12 GCP Secret Manager mocked smoke 8/8 passes throughout | Phase 8 confirmed |
| Final readiness review PASS applies only to local readiness controls | Section I, Phase 8 review |
| Final readiness review NOT APPROVED for real onboarding, API calls, OAuth, live flag activation | Section I, Phase 8 review |

---

## Operational Notes

| Note | Detail |
|---|---|
| Validator scope | All 4 validators evaluate local data structures only; no validator executes, simulates, or initiates any real external operation |
| First live API plan status | Design-only; existence does not authorize execution; all 19 preconditions must be satisfied independently before any execution |
| Version lifecycle policy | `DISABLE_PREVIOUS_WITH_GRACE_PERIOD` is the V5.20 authorized policy decision; applying it to a real secret requires separate explicit operator authorization |
| Final readiness review PASS | PASS for local readiness controls only; NOT a determination that real execution is authorized or safe to proceed |
| Real execution authorization | Any real Google Ads credential onboarding, OAuth execution, or live API call requires a separate future initiative with explicit operator approval |

---

## Files Added

| File | Purpose |
|---|---|
| `openclaw/onboarding_ceremony.py` | `validate_onboarding_ceremony()` — ceremony model validator; local-only |
| `openclaw/run_onboarding_ceremony_demo.py` | 36-assertion demo: all ceremony conditions, forbidden field/value detection |
| `openclaw/credential_intake.py` | `validate_credential_intake_dry_run()` — intake boundary validator; 25 failure codes; local-only |
| `openclaw/run_credential_intake_demo.py` | 33-scenario demo: all boundary rules, plan requirements, reference confirmations, hard-stop conditions |
| `openclaw/rollback_drill.py` | `validate_rollback_drill()` — rollback sequence validator; 20 failure codes; local-only |
| `openclaw/run_rollback_drill_demo.py` | 28-scenario demo: full rollback sequence validation, forbidden field/value detection |
| `openclaw/secret_version_policy.py` | `validate_secret_version_policy()` — version lifecycle policy validator; 19 failure codes; local-only |
| `openclaw/run_secret_version_policy_demo.py` | 30-scenario demo: all 4 lifecycle modes, grace period bounds, forbidden fields/values |
| `docs/V5_20_IMPLEMENTATION_PLAN.md` | V5.20 full design specification and implementation notes |
| `docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md` | Operator onboarding ceremony checklist; prerequisite only; does not authorize execution |
| `docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md` | First live API validation plan; design only; does not authorize execution |
| `docs/V5_20_FINAL_READINESS_REVIEW.md` | 10-section final readiness review; PASS for local readiness; NOT approved for real execution |
| `docs/V5_20_BRANCH_CLOSURE.md` | Branch closure documentation |
| `docs/RELEASE_NOTES_V5_20_0_BETA.md` | This document |

---

## Files Modified

| File | Change |
|---|---|
| `scripts/smoke_test_v5_credentials.sh` | Extended from 26/26 to 31/31; five new V5.20 sections [27–31] |
| `docs/ROADMAP.md` | V5.20 Phases 1–9 marked complete; Phase 10 remains |
| `README.md` | V5.20 milestone updated; Phase 9 bullet and closure doc and release notes links added |

---

## Tests

| Suite / Demo | Result |
|---|---|
| `scripts/smoke_test_v5_credentials.sh` | **31/31 PASS** |
| `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **8/8 PASS** |
| `openclaw/run_onboarding_ceremony_demo.py` | **PASS** — 36 assertions |
| `openclaw/run_credential_intake_demo.py` | **PASS** — 70 assertions (33 scenarios) |
| `openclaw/run_rollback_drill_demo.py` | **PASS** — 67 assertions (28 scenarios) |
| `openclaw/run_secret_version_policy_demo.py` | **PASS** — 71 assertions (30 scenarios) |
| Combined validator assertion total | **244 assertions, 0 failures** |
| Safety grep (Phase 9 changed files) | **CLEAN** |

---

## Security Summary

| Property | Status |
|---|---|
| No real Google Ads credentials used | Confirmed |
| No OAuth consent or token exchange executed | Confirmed |
| No Google Ads API called | Confirmed |
| No GCP operations performed | Confirmed |
| No Secret Manager called | Confirmed |
| No production deployment | Confirmed |
| No IAM changes | Confirmed |
| No billing changes | Confirmed |
| `GOOGLE_ADS_LIVE_ENABLED` remains `false` by default | Confirmed |
| All validators reject forbidden credential/secret/resource field names | Confirmed — all demos PASS |
| All validators reject forbidden credential value patterns | Confirmed — all demos PASS |
| No GCP resource paths in any committed document | Confirmed — safety grep CLEAN |
| No project IDs, account emails, or customer IDs documented | Confirmed |
| No `.env` committed | Confirmed |
| No credential JSON committed | Confirmed |
| Safety grep CLEAN on all Phase 9 changed files | Confirmed |

---

## Deferred Work

- Real Google Ads OAuth credential onboarding (requires explicit operator approval gate; separate future initiative)
- Real Google Ads live API validation (requires `GOOGLE_ADS_LIVE_ENABLED=true`; explicit operator approval; all 19 preconditions from validation plan must be satisfied)
- OAuth consent flow execution
- Production Cloud Run deployment (requires service account, IAM, billing authorization)
- GCP API enablement
- IAM changes
- Billing changes
- Real Secret Manager version disable under `DISABLE_PREVIOUS_WITH_GRACE_PERIOD` policy (policy decided; execution requires separate authorization; irreversible)
- External approval UI (`LocalFileApprovalStore` for local operator testing only)
- Multi-client live validation
- Background or scheduled live validation
- Real production client onboarding

---

## Compatibility

No breaking changes. All existing routes and behaviors from V5.19 are preserved. New V5.20 validators are additive local-only modules with no effect on cloud behavior or existing API endpoints. The V5.12 GCP Secret Manager smoke suite (8/8) confirms no regressions in the credential lifecycle stack. V5.19 smoke suite extended from 26/26 to 31/31 with no regressions in the existing 26 sections.

---

## Upgrade and Merge Notes

No database migrations. No API changes to existing endpoints. No client-side changes required. No environment variable changes required for existing deployments; `GOOGLE_ADS_LIVE_ENABLED` remains `false` by default. New validator modules may be imported independently — they carry no runtime dependencies beyond the Python standard library.

Merge recommendation:

```bash
git checkout master
git merge --no-ff v5.20-controlled-real-google-ads-onboarding-readiness
git tag v5.20.0-beta
```

Tag message: `v5.20.0-beta — Controlled real Google Ads onboarding readiness: ceremony validator · intake dry-run · first API validation plan · rollback drill · version lifecycle policy · final readiness review (Phases 1–8 PASS)`

---

## Related Documents

- [V5.20 Branch Closure](V5_20_BRANCH_CLOSURE.md)
- [V5.20 Implementation Plan](V5_20_IMPLEMENTATION_PLAN.md)
- [V5.20 Final Readiness Review](V5_20_FINAL_READINESS_REVIEW.md)
- [Google Ads Real Onboarding Checklist](GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md)
- [Google Ads First Live API Validation Plan](GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md)
- [V5.19 Branch Closure](V5_19_BRANCH_CLOSURE.md)
- [Release Notes — v5.19.0-beta](RELEASE_NOTES_V5_19_0_BETA.md)
- [Credential Lifecycle Runbook](CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

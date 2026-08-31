# V5.24 Implementation Plan — Documentation and Planning Hardening

**Kaiju Command Center — V5.24**

**Branch:** `v5.24-documentation-planning-hardening`
**Base release:** `v5.23.0-beta`
**Base merge commit:** `3963f9d`
**Risk classification:** MEDIUM (documentation-only; no execution risk)
**Date:** 2026-08-31

---

> **SCOPE BOUNDARY — READ BEFORE USING THIS DOCUMENT**
>
> V5.24 is **documentation and planning hardening only**.
>
> V5.24 does **not** authorize and will **not** perform:
> - Deploy, GCP commands, Secret Manager calls, IAM/API/billing changes, cloud resource creation.
> - Real credentials, OAuth, OAuth authorization URL generation, browser OAuth flow.
> - Callback URL receipt, auth code receipt, token exchange.
> - Google Ads API calls, rollback/revoke real.
> - `GOOGLE_ADS_LIVE_ENABLED=true` activation.
> - A1, A2, A3, A4, A5, A6, A7, A8, A9, or A10 from V5.23.
>
> V5.24 produces documentation artifacts only. Real OAuth execution remains
> at `READY_TO_PROPOSE` status and requires future per-step explicit authorization.

---

## A. Purpose

V5.24 hardens the planning and control documentation produced in V5.18–V5.23.

V5.23 produced a `READY_TO_PROPOSE` verdict for real OAuth execution with 17 open gaps
(H-01–H-17), all requiring human/out-of-repository action. V5.23 also produced a
comprehensive authorization and control framework across five phases.

V5.24 asks: **given the existing framework, where are the documentation and planning
controls weakest?** It fills those gaps with purpose-built hardening artifacts that
tighten the control envelope without crossing into execution territory.

**V5.24 hardening targets (identified by analysis of V5.23 gap set):**

| Target | Rationale |
|---|---|
| Authorization phrase validation | V5.23 defines verbatim phrases E.1–E.10 but does not specify how Claude Code distinguishes valid from invalid/partial/ambiguous authorization attempts |
| Gap closure evidence requirements | H-01–H-17 identify what humans must do but do not specify what evidence Claude Code must observe before acknowledging a gap as closed |
| Ceremony window integrity | Window rules E-R1–E-R8 exist but a standalone, operator-facing protocol for window planning and staleness management is absent |
| Control document navigation | Five V5.23 artifacts total >400 rules, assertions, and checklist items; a cross-reference index reduces operator navigation error |

---

## B. V5.23 Baseline Summary

| Field | Value |
|---|---|
| Baseline release | `v5.23.0-beta` |
| Baseline merge commit | `3963f9d` |
| Baseline verdict | `READY_TO_PROPOSE` |
| Baseline aggregate assertions | 610 (7 demo validators) |
| Baseline smoke suites | 35/35 + 8/8 |
| Baseline safety grep | CLEAN (9 patterns) |
| Open gaps at baseline | 17 (H-01–H-17; all block execution) |
| Control coverage | 22/22 controls PASS |
| Security categories absent | 18/18 PASS |

V5.24 must not decrease any of these baseline metrics.

---

## C. Phase Plan

| Phase | Description | Deliverable | Status |
|---|---|---|---|
| 1 | Implementation plan | `docs/V5_24_IMPLEMENTATION_PLAN.md` | **PASS** |
| 2 | Authorization phrase validation protocol | `docs/GOOGLE_ADS_AUTHORIZATION_PHRASE_VALIDATION_PROTOCOL.md` | **PASS** |
| 3 | Gap closure evidence requirements | `docs/GOOGLE_ADS_GAP_CLOSURE_EVIDENCE_REQUIREMENTS.md` | **PASS** |
| 4 | Ceremony window integrity protocol | `docs/GOOGLE_ADS_CEREMONY_WINDOW_INTEGRITY_PROTOCOL.md` | **PASS** |
| 5 | Hardening cross-reference review | `docs/V5_24_HARDENING_REVIEW.md` | **PASS** |
| 6 | Branch closure and release notes | `docs/V5_24_BRANCH_CLOSURE.md` + `docs/RELEASE_NOTES_V5_24_0_BETA.md` | **PASS** |
| 7 | Merge, tag, release | Merge to master, tag `v5.24.0-beta`, GitHub Release | `[ ]` — **PENDING EXPLICIT AUTHORIZATION** |

Phase 7 (merge, tag, release) requires separate explicit user authorization naming each action.
No phase authorizes any execution operation (deploy, GCP, OAuth, credentials, API).

---

## D. Phase 2 — Authorization Phrase Validation Protocol

**Deliverable:** `docs/GOOGLE_ADS_AUTHORIZATION_PHRASE_VALIDATION_PROTOCOL.md`

**Problem being solved:**

V5.23 Phase 2 (`docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md`) defines 10 verbatim
authorization phrase templates (E.1–E.10) and 7 phrase rules (E-R1–E-R7). However, the
existing framework does not specify:

- How Claude Code determines whether an authorization attempt contains the required exact phrase.
- What responses are required for partial, paraphrased, or umbrella authorization attempts.
- What constitutes an authorization attempt that must be rejected vs. ignored vs. escalated.
- How to handle authorization phrases that reference the wrong step, the wrong branch, or the wrong version.
- What to do when authorization is claimed verbally rather than through an approved channel.

**Phase 2 deliverable contents:**

| Section | Content |
|---|---|
| A | Purpose and non-authorization statement |
| B | Phrase anatomy — required elements of a valid authorization phrase |
| C | Validity criteria — 15+ rules for accepting a phrase as valid |
| D | Rejection criteria — 20+ patterns that invalidate an authorization attempt |
| E | Response protocol — prescribed Claude Code responses to invalid attempts |
| F | Channel validation — how to verify an approved out-of-repo channel was used |
| G | Version and step binding — how to confirm the phrase references the correct version and step |
| H | Ambiguity resolution — how to handle unclear or compound phrases |
| I | Escalation protocol — when to stop and escalate vs. when to simply reject |
| J | Logging and evidence — what Claude Code records about an authorization attempt (redacted) |
| K | Stop conditions — conditions that halt processing before phrase evaluation |
| L | Acceptance criteria |

---

## E. Phase 3 — Gap Closure Evidence Requirements

**Deliverable:** `docs/GOOGLE_ADS_GAP_CLOSURE_EVIDENCE_REQUIREMENTS.md`

**Problem being solved:**

V5.23 Section H documents 17 gaps (H-01–H-17) that block execution. Each gap states the
required closure condition in general terms. However, the existing framework does not specify:

- What specific evidence Claude Code must observe in the conversation before it can
  acknowledge a gap as closed.
- What evidence is insufficient (e.g., an assertion without supporting reference).
- What evidence must come from an approved out-of-repo channel vs. what can be asserted
  in-conversation.
- Whether gaps can be partially closed, and if so, how partial closure is tracked.
- How gap closure expires (e.g., role attendance confirmations lose validity over time).

**Phase 3 deliverable contents:**

| Section | Content |
|---|---|
| A | Purpose and non-authorization statement |
| B | Evidence classification — required vs. supporting vs. inadmissible |
| C | Per-gap evidence specifications — H-01 through H-17, each with: required evidence type, minimum specificity, admissibility rules, expiry conditions |
| D | Evidence sufficiency matrix — what combination of evidence closes each gap |
| E | Partial closure rules — when a gap is "partially addressed" vs. "closed" vs. "open" |
| F | Evidence expiry — which evidence classes have temporal validity limits |
| G | Evidence assertion vs. verification — what Claude Code can verify locally vs. what it must take on authority |
| H | Gap clustering — which gaps can be addressed in a single evidence submission |
| I | Minimum gap set for A1 proposal — which gaps (subset of H-01–H-17) must be closed before Claude Code may propose A1 |
| J | Stop conditions |
| K | Acceptance criteria |

---

## F. Phase 4 — Ceremony Window Integrity Protocol

**Deliverable:** `docs/GOOGLE_ADS_CEREMONY_WINDOW_INTEGRITY_PROTOCOL.md`

**Problem being solved:**

V5.23 Phase 4 (`docs/GOOGLE_ADS_REAL_OAUTH_EXECUTION_RUNBOOK.md`) Section E defines
8 window rules (E-R1–E-R8: expiry, extension, abort, restart, freeze, attention, no-overlap,
cool-down). V5.23 Phase 2 Checklist item G-C23 requires the dry-run be refreshed within 30
days. However, the existing framework does not provide:

- A standalone operator-facing protocol for planning a ceremony window before any
  authorization request is made.
- Explicit staleness rules for each prerequisite (dry-run currency, smoke suite currency,
  safety grep currency, gap closure evidence currency).
- A structured pre-window planning checklist that operators complete before requesting
  a timebox.
- Restart and cool-down procedures written at the operator level rather than buried in
  runbook sequence steps.
- Overlap detection — how to confirm no concurrent ceremony is in progress for the
  same tenant or another tenant sharing secrets.

**Phase 4 deliverable contents:**

| Section | Content |
|---|---|
| A | Purpose and non-authorization statement |
| B | Window planning prerequisites — what must be true before a window can be proposed |
| C | Dry-run currency — staleness rules (30-day hard limit + soft warning at 21 days) and refresh protocol |
| D | Smoke suite currency — staleness rules and re-run protocol |
| E | Safety grep currency — staleness rules and re-run protocol |
| F | Gap closure evidence currency — which evidence types expire and when |
| G | Window sizing guide — minimum/maximum duration, per-step time budgets |
| H | Overlap detection — how to confirm no concurrent ceremony for same or related tenant |
| I | Abort and restart protocol — step-by-step abort, cool-down, and restart checklist |
| J | Extension prohibition and emergency extension policy |
| K | Window integrity verification — checks at window open, mid-window, and window close |
| L | Stop conditions |
| M | Acceptance criteria |

---

## G. Phase 5 — Hardening Cross-Reference Review

**Deliverable:** `docs/V5_24_HARDENING_REVIEW.md`

**Purpose:** Consolidate Phases 2–4 into a unified review. Verify that:

1. V5.24 artifacts do not contradict any V5.18–V5.23 control clause.
2. V5.24 artifacts do not introduce new execution paths or weaken existing stop conditions.
3. The aggregate control assertion count meets or exceeds the V5.23 baseline (610).
4. All 22 V5.23 controls remain PASS after V5.24 additions.
5. Safety grep remains CLEAN.
6. Smoke suites remain PASS.
7. The `READY_TO_PROPOSE` verdict from V5.23 is unaffected by V5.24 additions.

**Review sections:**

| Section | Content |
|---|---|
| A | Purpose and non-authorization statement |
| B | V5.23 baseline reconfirmation |
| C | V5.24 artifact review (3 artifacts, Phases 2–4) |
| D | Contradiction analysis — V5.24 vs. V5.18–V5.23 control clauses |
| E | Control coverage matrix — 22 V5.23 controls re-evaluated with V5.24 additions |
| F | Aggregate assertion count — V5.24 additions counted and added to baseline |
| G | Security and redaction review |
| H | Gap analysis update — H-01–H-17 status unchanged (all still open; V5.24 does not close any gap) |
| I | Hardening verdict |
| J | Acceptance criteria |

---

## H. Credential and Execution Boundary

The following rules apply to all V5.24 phases without exception:

| Rule | Constraint |
|---|---|
| H-01 | No real credentials may appear in any V5.24 file |
| H-02 | No real OAuth authorization URL may be generated or referenced with real values |
| H-03 | No real callback URL, auth code, token, or Secret Manager path may appear |
| H-04 | No GCP command, GCP API call, Secret Manager call, or Google Ads API call may be made |
| H-05 | No deploy, IAM change, API enablement, or billing change may be made |
| H-06 | `GOOGLE_ADS_LIVE_ENABLED=true` must not be activated |
| H-07 | A1–A10 authorization phrases may not be executed, captured, or simulated as real |
| H-08 | All placeholder values must remain clearly labeled as placeholders |
| H-09 | Safety grep must remain CLEAN across all 9 patterns at every commit |
| H-10 | Smoke suites must remain PASS at every commit |

---

## I. Safety Envelope (V5.24)

The following checks apply at every commit. All must PASS before a phase is committed.

| Check | ID | Rule |
|---|---|---|
| No live credentials | I-01 | `grep -r "developer_token\|client_secret\|refresh_token\|access_token"` returns only documentation labels |
| No real OAuth URL | I-02 | `grep -r "accounts.google.com/o/oauth2"` returns only documentation references |
| No real callback URL | I-03 | `grep -r "redirect_uri.*http"` returns only placeholder examples |
| No Secret Manager path | I-04 | `grep -r "projects/.*/secrets/.*/versions"` returns only documentation labels |
| No Google Ads customer ID | I-05 | `grep -r "customer_id.*[0-9]\{10\}"` returns zero real IDs |
| No `.env` file | I-06 | `find . -name ".env" -not -path "./.git/*"` returns empty |
| No credential JSON | I-07 | `find . -name "*.json" -not -path "./.git/*" -not -path "./.venv/*"` returns no credential files |
| Smoke suite PASS | I-08 | `scripts/smoke_test_v5_credentials.sh` exits 0 (35/35) |
| Smoke suite PASS | I-09 | `scripts/smoke_test_v5_12_gcp_secret_manager.sh` exits 0 (8/8) |
| No GOOGLE_ADS_LIVE_ENABLED=true | I-10 | `grep -r "GOOGLE_ADS_LIVE_ENABLED=true"` returns zero results |

---

## J. Deferred Items

The following are explicitly deferred beyond V5.24:

| Item | Deferral reason |
|---|---|
| Real OAuth execution (A1–A10) | Requires future per-step explicit authorization |
| Secret Manager write | Requires A7 authorization (not granted) |
| Google Ads API call | Requires A8 authorization (not granted) |
| Live flag activation | Requires A9 authorization (not granted) |
| Deploy | Pending separate planning and authorization |
| GCP commands / IAM / billing | Pending separate explicit authorization |
| Closing gaps H-01–H-17 | Requires human/out-of-repo actions; not closeable by documentation |
| Multi-tenant ceremony sequencing | Deferred beyond V5.24 |
| Post-ceremony evidence chain design | Deferred beyond V5.24 |

---

## K. Phase 7 Authorization Requirements

Phase 7 (merge, tag, GitHub Release) requires separate explicit user authorization.

Required authorization must explicitly name:

- Merge branch `v5.24-documentation-planning-hardening` to master.
- Create annotated tag `v5.24.0-beta`.
- Push master.
- Push tag.
- Publish GitHub Release using `docs/RELEASE_NOTES_V5_24_0_BETA.md`.

Phase 7 authorization does **not** authorize:

- Deploy, GCP commands, Secret Manager calls, IAM/API/billing changes.
- Real credentials, OAuth, token exchange.
- Google Ads API calls, live flag activation.
- A1–A10 from V5.23.

---

## L. Phase 1 Acceptance Criteria

- [x] V5.24 branch created from `master` at `3963f9d` (`v5.23.0-beta`).
- [x] Implementation plan committed.
- [x] Scope boundary clearly stated.
- [x] V5.23 baseline recorded.
- [x] All 7 phases defined.
- [x] Phases 2–4 deliverable contents specified.
- [x] Phase 5 review structure defined.
- [x] Credential and execution boundary (H-01–H-10) stated.
- [x] Safety envelope (I-01–I-10) stated.
- [x] Deferred items listed.
- [x] Phase 7 authorization requirements stated.
- [x] No real credentials.
- [x] No OAuth, GCP, Secret Manager, Google Ads API.
- [x] No A1–A10 execution.
- [x] `GOOGLE_ADS_LIVE_ENABLED` remains `false`.

---

**Phases 1–6 complete. Phase 7 pending explicit user authorization.**

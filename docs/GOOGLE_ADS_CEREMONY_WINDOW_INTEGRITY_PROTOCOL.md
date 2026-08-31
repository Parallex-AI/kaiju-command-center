# Google Ads Ceremony Window Integrity Protocol

**Kaiju Command Center — V5.24 Phase 4**

**Branch:** `v5.24-documentation-planning-hardening`
**Base:** `v5.23.0-beta` / master merge commit `3963f9d`
**Date:** 2026-08-31

---

> **WARNING — READ BEFORE USING THIS DOCUMENT**
>
> - This document is **documentation and planning hardening only**.
> - This document **does not authorize real execution.**
> - Nothing in this document authorizes A1–A10.
> - No real ceremony window dates, operator identities, or account identifiers may
>   appear in this file.
> - All examples are placeholder-only.

---

## A. Purpose

V5.23 Phase 4 (`docs/GOOGLE_ADS_REAL_OAUTH_EXECUTION_RUNBOOK.md`) Section E defines
8 ceremony window rules (E-R1–E-R8). V5.23 Phase 2 Checklist item G-C23 requires
the dry-run PASS to be within 30 days. These controls exist but are embedded within
longer artifacts that operators consult during execution — not before.

This protocol provides a **standalone, operator-facing ceremony window planning and
integrity guide** for use before any authorization request is made. It covers:

- What must be true before a window can be proposed (Section B).
- Prerequisite staleness rules for dry-run, smoke suites, safety grep, and gap evidence (Sections C–F).
- Window sizing guide (Section G).
- Overlap detection (Section H).
- Abort and restart protocol (Section I).
- Extension prohibition and emergency extension policy (Section J).
- Window integrity verification at open, mid-window, and close (Section K).

**This protocol does not authorize a ceremony window.** Only a human operator can
select and authorize a ceremony window. This document specifies what operators must
prepare and what Claude Code checks before acknowledging a window as valid.

---

## B. Window Planning Prerequisites

Before an operator may propose a ceremony window, ALL of the following must hold:

| ID | Prerequisite | Basis |
|---|---|---|
| B-01 | V5.22-style dry-run PASS within 30 days | Phase 2 G-C23 |
| B-02 | Smoke suite `smoke_test_v5_credentials.sh` 35/35 PASS | Phase 4 F-27 |
| B-03 | Smoke suite `smoke_test_v5_12_gcp_secret_manager.sh` 8/8 PASS | Phase 4 F-28 |
| B-04 | Safety grep CLEAN (9 patterns) | Phase 1 I-01–I-09 |
| B-05 | All 9 minimum gaps ADDRESSED (per Section D.1 of gap closure evidence requirements) | V5.24 Phase 3 |
| B-06 | Stop authority named and availability confirmed for proposed window | Phase 4 D |
| B-07 | Credential owner named and availability confirmed for proposed window | Phase 4 D |
| B-08 | No active stop condition from Phase 4 Section I | Phase 4 Section I |
| B-09 | No concurrent ceremony in progress for same or related tenant | Section H of this document |
| B-10 | Working tree clean | Standard hygiene |

**Failure of any single B-01 through B-10 prerequisite prevents window proposal.**
Claude Code will not proceed with ceremony planning if any prerequisite is unmet.

---

## C. Dry-Run Currency

### C.1 — Currency rule

The V5.22-style dry-run PASS is **stale** if the PASS was recorded more than 30 days ago.
A stale dry-run blocks window proposal (B-01).

### C.2 — Warning threshold

| Days since dry-run PASS | Status | Action |
|---|---|---|
| 0–21 days | FRESH | No action required |
| 22–29 days | WARNING | Operator should schedule a refresh run |
| 30+ days | STALE — blocks window proposal | Refresh run required before proposing a window |

### C.3 — Dry-run refresh protocol

To refresh the dry-run currency:

1. Run `openclaw/run_oauth_dry_run_execution_demo.py` in the current session.
2. Confirm output shows "PASS" with assertion count ≥ 112.
3. Note the date of the PASS run.
4. Record the PASS as the new dry-run currency baseline.
5. The 30-day clock resets from the date of this PASS run.

### C.4 — What the dry-run does NOT do

Running the dry-run refresh does NOT:
- Authorize real OAuth execution.
- Close any V5.23 gap.
- Constitute an authorization attempt.
- Restart a paused ceremony.

---

## D. Smoke Suite Currency

### D.1 — Currency rule

Smoke suite results are valid only when run **in the current ceremony window session**.
Smoke suite results from a prior session are inadmissible (E-TYPE-06 per
`docs/GOOGLE_ADS_GAP_CLOSURE_EVIDENCE_REQUIREMENTS.md` Section B).

### D.2 — Required suites

| Suite | Target | PASS threshold |
|---|---|---|
| `scripts/smoke_test_v5_credentials.sh` | 35/35 | Exactly 35 tests must pass |
| `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | 8/8 | Exactly 8 tests must pass |

### D.3 — Smoke suite refresh protocol

1. Run each suite in-session.
2. Confirm output shows PASS at the required threshold.
3. If either suite fails: STOP. Investigate and fix before proceeding.
4. Record results as in-session PASS evidence.

---

## E. Safety Grep Currency

### E.1 — Currency rule

Safety grep results are valid only when run **in the current ceremony window session**.

### E.2 — Required patterns (9)

| Pattern | Checks for |
|---|---|
| `developer_token` | Real developer tokens |
| `client_secret` | Real OAuth client secrets |
| `refresh_token` | Real refresh tokens |
| `access_token` | Real access tokens |
| `accounts.google.com/o/oauth2` | Real OAuth authorization URLs |
| `redirect_uri.*http` | Real redirect/callback URIs |
| `projects/.*/secrets/.*/versions` | Real Secret Manager resource paths |
| `customer_id.*[0-9]{10}` | Real Google Ads customer IDs |
| `GOOGLE_ADS_LIVE_ENABLED=true` | Live flag activation |

### E.3 — Safety grep refresh protocol

1. Run each of the 9 patterns against the repository.
2. Any hit that is not a documentation label, prohibition text, or placeholder must halt processing immediately.
3. Record results as CLEAN or note hits with classification.
4. CLEAN means: all hits are documentation labels or prohibition text, not real values.

---

## F. Gap Closure Evidence Currency

Per `docs/GOOGLE_ADS_GAP_CLOSURE_EVIDENCE_REQUIREMENTS.md` Section F:

| Evidence class | Maximum validity |
|---|---|
| Role attendance confirmations | 24 hours; re-confirm if window shifts |
| Window selection | Valid only for the named window |
| Approval packet reference | Valid for the named ceremony instance |
| Account scope confirmation | Valid for the named ceremony instance |

**Before window proposal:** All 9 minimum gap evidence items must be within their
validity window. If any has expired, fresh evidence is required before window proposal.

---

## G. Window Sizing Guide

### G.1 — Window rules from Phase 4 Section E (E-R1–E-R8)

| Rule | Requirement |
|---|---|
| E-R1 (Expiry) | Every ceremony window has an explicit end time; execution beyond end time is prohibited |
| E-R2 (Extension prohibition) | No ceremony window may be extended once set |
| E-R3 (Abort) | Any operator may abort at any point; abort is immediate and unilateral |
| E-R4 (Restart) | A new window must be established after any abort; the original window is voided |
| E-R5 (Freeze) | If window closes with steps incomplete, all remaining steps are frozen; no continuation in a future window |
| E-R6 (Attention) | All roles must maintain active presence throughout the window |
| E-R7 (No-overlap) | No two ceremonies may share a window period for the same tenant or for tenants sharing secrets |
| E-R8 (Cool-down) | A minimum cool-down period (defined in out-of-repo policy) must elapse between ceremonies |

### G.2 — Minimum per-step time budgets

The following are planning estimates only. Real execution windows are set by the human operator.

| Step | Minimum time budget (planning estimate) |
|---|---|
| A1 | 20 minutes (approval packet verification + authorization capture) |
| A2 | 15 minutes (secure channel preparation and verification) |
| A3 | 10 minutes (OAuth URL generation — operator review required) |
| A4 | 20 minutes (browser OAuth flow — human-driven; variable) |
| A5 | 15 minutes (callback + auth code receipt and verification) |
| A6 | 15 minutes (token exchange) |
| A7 | 20 minutes (Secret Manager write + verification) |
| A8 | 30 minutes (first read-only Google Ads API validation) |
| A9 | 20 minutes (live flag activation + verification) |
| A10 (if triggered) | 30 minutes minimum (rollback/revoke + verification) |
| Buffer | ≥ 30 minutes |

**These are planning minimums only.** Real window duration is set by the human operator
based on actual ceremony complexity, role availability, and out-of-repo policy.

### G.3 — Window sizing rules

| Rule | Requirement |
|---|---|
| G-R1 | The window must be long enough to cover all planned steps plus buffer |
| G-R2 | If A10 (rollback/revoke) may be needed, time budget must include A10 |
| G-R3 | The window must end while all roles are still available |
| G-R4 | No window may be set to terminate "at completion" — an explicit end time is mandatory |

---

## H. Overlap Detection

### H.1 — Purpose

Rule E-R7 prohibits two ceremonies sharing a window for the same tenant or for tenants
sharing secrets. Before proposing a window, Claude Code must confirm no overlap exists.

### H.2 — Overlap detection check

Before acknowledging a window proposal, Claude Code asks the operator to confirm:

| Check | Required operator assertion |
|---|---|
| H-C1 | No other ceremony is currently in progress for the same tenant |
| H-C2 | No other ceremony is currently in progress for any tenant sharing the same secret or Secret Manager project |
| H-C3 | The last ceremony for this tenant completed its cool-down period (E-R8) |
| H-C4 | No concurrent ceremony is planned to start within the cool-down period after this window ends |

### H.3 — Overlap evidence

Operator must assert each of H-C1 through H-C4 explicitly. "No conflicts" alone is inadmissible.
Each assertion must reference the tenant scope.

### H.4 — If overlap is detected

If any H-C1 through H-C4 check fails:

1. Stop. Do not proceed with window proposal.
2. State the conflict clearly.
3. Do not proceed until the conflicting ceremony is complete and cool-down has elapsed.

---

## I. Abort and Restart Protocol

### I.1 — Abort triggers

Abort is triggered by:
- Any stop condition from Phase 4 Section I (I-01–I-50).
- Any stop authority invocation (unilateral; no countersignature required).
- Any credential exposure event.
- Any unauthorized action detection.
- Ceremony window expiry during execution.

### I.2 — Abort procedure

When an abort is triggered:

| Step | Action |
|---|---|
| I-A1 | STOP immediately. No further OAuth execution actions. |
| I-A2 | State the abort trigger clearly. |
| I-A3 | Close any open credential surfaces (per Phase 3 M1–M13 incident protocol). |
| I-A4 | Capture the abort state: last completed step, abort trigger, timestamp. |
| I-A5 | Notify stop authority and rollback owner. |
| I-A6 | Determine if A10 (rollback/revoke) is required. |
| I-A7 | If A10 is required: execute only with explicit A10 authorization phrase per `docs/GOOGLE_ADS_AUTHORIZATION_PHRASE_VALIDATION_PROTOCOL.md`. |
| I-A8 | Store abort evidence in out-of-repo evidence store. |
| I-A9 | Do NOT attempt to continue in the current window. The window is voided. |

### I.3 — Cool-down after abort

After any abort:

- No restart attempt may be made until:
  - The abort root cause has been documented in the out-of-repo evidence store.
  - All roles have confirmed they reviewed the abort evidence.
  - The cool-down period (E-R8) has elapsed from the abort time.
  - A new ceremony window has been proposed and confirmed through fresh evidence (all B-01–B-10).

### I.4 — Restart procedure

A restart is a new ceremony, not a continuation. The following apply:

| Rule | Requirement |
|---|---|
| I-R1 | All prerequisites (B-01–B-10) must be re-satisfied. |
| I-R2 | All prior-window evidence is invalid (E-TYPE-06). |
| I-R3 | Steps completed before abort do NOT carry forward. The full ceremony sequence starts at A1. |
| I-R4 | The abort evidence must be referenced in the new ceremony's approval packet. |
| I-R5 | The stop authority must provide explicit GO for the new ceremony independently of any prior GO. |

---

## J. Extension Prohibition and Emergency Extension Policy

### J.1 — Extension prohibition

Per E-R2: No ceremony window may be extended once set. An "extension" is any attempt to:
- Move the window end time later.
- Add time after the window start.
- Resume a ceremony after the window end time has passed.

All of the above are prohibited without exception under E-R2.

### J.2 — Emergency extension policy

An emergency extension policy is the only exception to E-R2 and must:

1. Be documented in the out-of-repo emergency revoke policy artifact (H-13).
2. Name the conditions under which an extension is permitted (e.g., system outage during A6).
3. Name who may authorize an emergency extension (stop authority + one additional named role).
4. State the maximum extension duration.
5. Require both authorizers to provide separate explicit authorizations for the extension.

**Absence of a documented emergency extension policy means no extension is possible.** Claude Code
may not grant or acknowledge an extension without a reference to the out-of-repo emergency extension policy artifact.

---

## K. Window Integrity Verification

### K.1 — At window open (before A1)

Before A1 execution may begin, Claude Code confirms:

| Check | Requirement |
|---|---|
| K-O1 | All B-01–B-10 prerequisites are satisfied |
| K-O2 | Window start/end times are confirmed |
| K-O3 | Current time is within the window |
| K-O4 | No overlap detected (H-C1–H-C4 confirmed) |
| K-O5 | All roles are live-attending at window open |
| K-O6 | Smoke suites PASS in-session |
| K-O7 | Safety grep CLEAN in-session |
| K-O8 | Working tree clean |

### K.2 — Mid-window (after each A-step completion)

After each A-step completion and before proposing the next A-step authorization:

| Check | Requirement |
|---|---|
| K-M1 | Current time is still within the window |
| K-M2 | All roles are still attending |
| K-M3 | No stop condition from Phase 4 Section I has been triggered |
| K-M4 | Evidence from the completed step has been recorded in out-of-repo evidence store |
| K-M5 | No credential exposure detected |

### K.3 — At window close (natural or forced)

When the window end time is reached:

| Check | Requirement |
|---|---|
| K-C1 | Any incomplete steps are immediately frozen — no continuation |
| K-C2 | Post-execution evidence is stored in the designated out-of-repo evidence store |
| K-C3 | Rollback/revoke state (A10 needed or not) is documented |
| K-C4 | All role attendance is released |
| K-C5 | Cool-down clock starts from window close time |

---

## L. Stop Conditions

Processing under this protocol halts immediately if:

| ID | Condition |
|---|---|
| L-01 | Any stop condition from Phase 4 Section I (I-01–I-50) is active |
| L-02 | Any stop condition from Phase 3 Section K (K-01–K-35) is active |
| L-03 | Window end time is reached during execution |
| L-04 | Overlap detected during or after window proposal |
| L-05 | Extension is requested without documented emergency extension policy |
| L-06 | An operator claims cool-down has elapsed without providing dated abort evidence |
| L-07 | Restart is attempted without re-satisfying all B-01–B-10 prerequisites |
| L-08 | Any role loses attendance during the window without stop authority notification |
| L-09 | Dry-run staleness is detected after window open (window must be voided; fresh dry-run required) |
| L-10 | Safety grep hit (non-documentation) is found during mid-window check |

---

## M. Acceptance Criteria

- [x] Protocol created at `docs/GOOGLE_ADS_CEREMONY_WINDOW_INTEGRITY_PROTOCOL.md`.
- [x] Documentation-only.
- [x] Non-authorization statement present.
- [x] Window planning prerequisites defined (10 items B-01–B-10).
- [x] Dry-run currency defined (30-day rule; 21-day warning; refresh protocol).
- [x] Smoke suite currency defined (in-session requirement; refresh protocol).
- [x] Safety grep currency defined (9 patterns; in-session requirement; refresh protocol).
- [x] Gap closure evidence currency cross-referenced.
- [x] Window sizing guide defined (E-R1–E-R8 + per-step budgets + 4 sizing rules).
- [x] Overlap detection defined (4 checks H-C1–H-C4 + conflict protocol).
- [x] Abort procedure defined (9 steps I-A1–I-A9).
- [x] Cool-down protocol defined.
- [x] Restart procedure defined (5 rules I-R1–I-R5).
- [x] Extension prohibition defined; emergency extension policy requirements defined.
- [x] Window integrity verification defined (open: 8 checks; mid: 5 checks; close: 5 checks).
- [x] Stop conditions defined (10 conditions L-01–L-10).
- [x] No real credentials, operator identities, account identifiers, or ceremony dates.
- [x] No OAuth, GCP, Secret Manager, Google Ads API.
- [x] No A1–A10 execution.
- [x] `GOOGLE_ADS_LIVE_ENABLED` remains `false`.

---

**Phase 4 complete. Proceed to Phase 5.**

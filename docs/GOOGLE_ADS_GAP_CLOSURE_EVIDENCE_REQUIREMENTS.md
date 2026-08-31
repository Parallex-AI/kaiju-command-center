# Google Ads Gap Closure Evidence Requirements

**Kaiju Command Center — V5.24 Phase 3**

**Branch:** `v5.24-documentation-planning-hardening`
**Base:** `v5.23.0-beta` / master merge commit `3963f9d`
**Date:** 2026-08-31

---

> **WARNING — READ BEFORE USING THIS DOCUMENT**
>
> - This document is **documentation and planning hardening only**.
> - This document **does not authorize real execution.**
> - Nothing in this document closes any V5.23 gap (H-01–H-17).
> - Nothing in this document authorizes A1–A10.
> - No real credential value, operator identity, tenant identifier, or Secret Manager path
>   may be entered in this file.
> - All examples are placeholder-only.

---

## A. Purpose

V5.23 Phase 5 (`docs/V5_23_PRE_EXECUTION_AUTHORIZATION_REVIEW.md`) Section H identifies
17 gaps (H-01–H-17), all of which block real OAuth execution. Each gap describes what
a human operator must do to close it. However, the existing framework does not specify
what evidence Claude Code must receive and assess before it can acknowledge a gap as closed.

This document defines:

- Evidence classification — what types of evidence are admissible (Section B).
- Per-gap evidence specifications — for each of H-01–H-17, what specific evidence is
  required, at what specificity, and with what expiry (Section C).
- Evidence sufficiency matrix — what combination closes each gap (Section D).
- Partial closure rules (Section E).
- Evidence expiry (Section F).
- Assertion vs. verification distinction (Section G).
- Gap clustering — which gaps can be addressed together (Section H).
- Minimum gap set for A1 proposal (Section I).
- Stop conditions (Section J).

**This document does not close any gap.** It specifies the requirements that must be
met for a gap to be considered closed. All 17 gaps (H-01–H-17) remain OPEN after V5.24.
Closing a gap requires human/out-of-repository action that Claude Code cannot perform.

---

## B. Evidence Classification

### B.1 — Evidence types

| Type | Definition | Admissibility |
|---|---|---|
| E-TYPE-01 | Out-of-repo record — artifact in an approved out-of-repo store (e.g., password manager entry, encrypted file, approval document) | Admissible when operator asserts its existence with specific reference |
| E-TYPE-02 | In-conversation operator assertion — operator states a fact in the Claude Code conversation | Admissible for low-sensitivity confirmations (e.g., role attendance) with named individual and timestamp |
| E-TYPE-03 | In-conversation document reference — operator provides a reference to an out-of-repo artifact without quoting content | Admissible; Claude Code cannot verify content but records the reference |
| E-TYPE-04 | System-generated artifact — e.g., smoke suite PASS output, safety grep output | Admissible when Claude Code ran the check in-session |
| E-TYPE-05 | Implicit assumption — "it should be fine" / "we already discussed" | **Inadmissible** |
| E-TYPE-06 | Past-session evidence — evidence provided in a prior conversation session without re-confirmation | **Inadmissible**; each ceremony window requires fresh evidence |

### B.2 — Sensitivity tiers

| Tier | Definition | Storage restriction |
|---|---|---|
| TIER-1 | Non-sensitive: role names, timestamp, channel class, window duration | May be noted in-conversation |
| TIER-2 | Semi-sensitive: named individuals, channel identifiers, ceremony references | Reference only in-conversation; content stays out-of-repo |
| TIER-3 | Sensitive: real credentials, approval payload, account identifiers, secret paths | **Never** in-conversation, **never** in-repo |

---

## C. Per-Gap Evidence Specifications

For each gap, the following columns apply:

- **Required evidence type** — which E-TYPE must be provided
- **Required specificity** — minimum detail required
- **Tier** — sensitivity tier
- **Expiry** — how long the evidence remains valid for the current ceremony window
- **Blocks A1 proposal?** — whether this gap must be closed before Claude Code may propose A1

---

### C.H-01 — No real human operator authorization captured

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-01 (out-of-repo record) |
| Required specificity | Operator asserts that an out-of-repo approval packet instance exists in a named artifact store; artifact store is one of Phase 3 D.1–D.4; packet contains: authorizer name, ceremony window reference, step A1 target; packet status is `NOT_YET_SUBMITTED` or equivalent (not `APPROVED`) |
| Tier | TIER-2 (reference only; no real payload in-conversation) |
| Expiry | Valid only for the named ceremony window; expires when window closes |
| Blocks A1 proposal | YES |
| Inadmissible forms | "I've authorized it"; "I'll authorize it when needed"; any assertion without artifact store reference |

---

### C.H-02 — No real out-of-repo approval packet

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-01 |
| Required specificity | Operator provides: (a) artifact store identifier (which D.1–D.4 class + tool name), (b) packet identifier or reference, (c) confirmation that packet fields for A1 (authorizer, tenant/client, window) are filled (no content in-conversation) |
| Tier | TIER-2 |
| Expiry | Expires when ceremony window closes |
| Blocks A1 proposal | YES |
| Inadmissible forms | "It exists somewhere"; "I'll create it before we start"; reference without store class |

---

### C.H-03 — No real tenant/client secure-channel reference

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-01 + E-TYPE-02 |
| Required specificity | Operator states: (a) the real tenant name or code (TIER-2; reference only, no account identifiers), (b) that a secure-channel reference for that tenant exists in the approval packet, (c) the channel class (D.1–D.4) used for the tenant credential handoff |
| Tier | TIER-2 |
| Expiry | Expires when ceremony window closes |
| Blocks A1 proposal | YES |
| Inadmissible forms | Tenant named without channel reference; channel named without tenant association |

---

### C.H-04 — No approved secure channel selected or configured

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-01 + E-TYPE-02 |
| Required specificity | Operator states: (a) which specific D.1–D.4 class is selected, (b) the specific tool or system name (e.g., "1Password"), (c) confirmation that storage owner and stop authority jointly selected it, (d) reference to the out-of-repo record documenting the selection |
| Tier | TIER-2 |
| Expiry | Expires when ceremony window closes |
| Blocks A1 proposal | YES |
| Inadmissible forms | "A secure channel"; "we'll figure it out"; naming only the class without the specific tool |

---

### C.H-05 — No real credential owner availability confirmation

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-02 |
| Required specificity | Operator states: (a) the role name "credential owner", (b) the named individual filling that role (TIER-2; name in-conversation is acceptable for attendance confirmation), (c) that they have confirmed availability during the entire proposed ceremony window |
| Tier | TIER-2 |
| Expiry | 24 hours maximum; re-confirmation required if window shifts |
| Blocks A1 proposal | YES |
| Inadmissible forms | "They'll be available"; "I am also the credential owner" without naming the individual; role confirmed without window reference |

---

### C.H-06 — No stop authority live attendance confirmation

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-02 |
| Required specificity | Operator states: (a) role name "stop authority", (b) named individual, (c) confirmation of live attendance throughout the window, (d) that they have stop authority understood as unilateral halt power |
| Tier | TIER-2 |
| Expiry | 24 hours maximum; re-confirmation required if window shifts |
| Blocks A1 proposal | YES |
| Inadmissible forms | "Someone can stop it if needed"; unnamed "stop authority"; stop authority who is the same person as the sole operator |

---

### C.H-07 — No rollback owner live attendance confirmation

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-02 |
| Required specificity | Operator states: (a) role name "rollback owner", (b) named individual, (c) confirmation of live attendance throughout A5–A9 |
| Tier | TIER-2 |
| Expiry | 24 hours maximum |
| Blocks A1 proposal | NO — required before A5; must be stated before window opens |
| Note | Not required for A1 proposal itself, but must be named before window opens |

---

### C.H-08 — No emergency revoke owner live attendance confirmation

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-02 |
| Required specificity | Operator states: (a) role name "emergency revoke owner", (b) named individual, (c) confirmation of live attendance throughout A6–A9 |
| Tier | TIER-2 |
| Expiry | 24 hours maximum |
| Blocks A1 proposal | NO — required before A6; must be named before window opens |
| Note | Not required for A1 proposal itself, but must be named before window opens |

---

### C.H-09 — No final timebox selected

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-01 + E-TYPE-02 |
| Required specificity | Operator states: (a) ceremony start date+time (timezone-explicit), (b) ceremony end date+time, (c) total duration, (d) confirmation that duration complies with Phase 4 Section E window rules (E-R1–E-R8) |
| Tier | TIER-1 |
| Expiry | Immediately superseded if window is shifted; original window is invalid after any shift |
| Blocks A1 proposal | YES |
| Inadmissible forms | "A couple of hours"; "sometime this week"; start without end |

---

### C.H-10 — No final human go/no-go recorded

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-01 |
| Required specificity | Operator states: (a) that the Phase 4 Section L L-33 go/no-go checklist is complete in the out-of-repo evidence store, (b) the named authorizer who recorded it, (c) the timestamp of recording, (d) the decision (`GO`); must be recorded for the specific ceremony window |
| Tier | TIER-2 (reference; no checklist content in-conversation) |
| Expiry | Expires when ceremony window closes or if any condition changes that would trigger a re-check |
| Blocks A1 proposal | YES |
| Inadmissible forms | "We're good to go"; no named authorizer; no timestamp; verbal GO without out-of-repo record reference |

---

### C.H-11 — No real Google Ads account scope confirmed

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-01 |
| Required specificity | Operator states that account scope (customer ID, login customer ID) is recorded in the out-of-repo approval packet; must confirm the account scope field is filled; no real account identifiers may appear in-conversation |
| Tier | TIER-3 (identifiers themselves must not appear in-conversation) |
| Expiry | Expires when ceremony window closes |
| Blocks A1 proposal | YES |
| Inadmissible forms | Account identifiers stated in-conversation; "the same account as before"; account scope without approval packet reference |

---

### C.H-12 — No post-execution evidence storage location selected

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-02 |
| Required specificity | Operator states: (a) the specific out-of-repo evidence store that will hold post-execution artifacts, (b) that the storage owner has confirmed it is writable, (c) the channel class (D.1–D.4) of the evidence store |
| Tier | TIER-2 |
| Expiry | Expires when ceremony window closes |
| Blocks A1 proposal | NO — required before A9; but must be named before window opens |

---

### C.H-13 — No emergency revocation policy artifact confirmed

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-01 |
| Required specificity | Operator states: (a) that an emergency revoke policy document exists in the out-of-repo evidence store, (b) the incident classes it covers are enumerated (confirmed by operator assertion; classes not quoted in-conversation), (c) the emergency revoke owner has confirmed knowledge of it |
| Tier | TIER-2 |
| Expiry | Expires when ceremony window closes or when incident classes change |
| Blocks A1 proposal | NO — required before A6; but policy existence must be confirmed before window opens |

---

### C.H-14 — No Phase 6 execution authorization

| Field | Requirement |
|---|---|
| Evidence type | E-TYPE-01 + valid Phase 2 / V5.24 authorization phrases for A2–A5 |
| Required specificity | Each of A2, A3, A4, A5 requires its own separate authorization per the phrase validation protocol (`docs/GOOGLE_ADS_AUTHORIZATION_PHRASE_VALIDATION_PROTOCOL.md`) |
| Tier | TIER-3 |
| Expiry | Per-step; each authorization valid only within the active ceremony window |
| Blocks A1 proposal | NO (H-14 gates Phase 6, not the A1 proposal itself) |

---

### C.H-15 — No Phase 7 token exchange / Secret Manager authorization

| Field | Requirement |
|---|---|
| Evidence type | Valid phrase for A6 and A7 per authorization phrase validation protocol |
| Required specificity | A6 and A7 must be separately authorized; A7 requires additional confirmation that Secret Manager is accessible (storage owner confirmation) |
| Tier | TIER-3 |
| Expiry | Per-step |
| Blocks A1 proposal | NO |

---

### C.H-16 — No Phase 8 Google Ads API authorization

| Field | Requirement |
|---|---|
| Evidence type | Valid phrase for A8 per authorization phrase validation protocol |
| Required specificity | A8 authorization; read-only GAQL SELECT scope confirmed in approval packet |
| Tier | TIER-3 |
| Expiry | Per-step |
| Blocks A1 proposal | NO |

---

### C.H-17 — No A9 live flag authorization

| Field | Requirement |
|---|---|
| Evidence type | Valid phrase for A9 per authorization phrase validation protocol |
| Required specificity | A9 authorization; scope (tenant, account) and duration (start/end) explicitly named |
| Tier | TIER-3 |
| Expiry | Per-step; duration explicitly bounded |
| Blocks A1 proposal | NO |

---

## D. Evidence Sufficiency Matrix

### D.1 — Gaps required before Claude Code may propose A1

The following gaps must be addressed with sufficient evidence before Claude Code
may propose A1 to the human operator:

| Gap | Minimum evidence required | Type |
|---|---|---|
| H-01 | Out-of-repo approval packet artifact asserted with store class + reference | E-TYPE-01 |
| H-02 | Packet fields filled (authorizer, tenant, window) — reference only | E-TYPE-01 |
| H-03 | Tenant reference + channel class asserted | E-TYPE-01 + E-TYPE-02 |
| H-04 | Specific channel tool named; storage owner + stop authority selection documented | E-TYPE-01 + E-TYPE-02 |
| H-05 | Credential owner named + availability confirmed for window | E-TYPE-02 |
| H-06 | Stop authority named + live attendance confirmed for window | E-TYPE-02 |
| H-09 | Window start, end, timezone asserted | E-TYPE-02 |
| H-10 | Go/no-go record referenced (named authorizer + timestamp + GO) | E-TYPE-01 |
| H-11 | Account scope recorded in approval packet (no identifiers in-conversation) | E-TYPE-01 |

**H-07, H-08, H-12, H-13 must be named before window opens but do not block the A1 proposal request.**

**H-14, H-15, H-16, H-17 are step-gating; they block the respective steps, not the A1 proposal.**

### D.2 — Sufficiency definition

Evidence is **sufficient** when:
- The required E-TYPE(s) are provided.
- The required specificity is met.
- The evidence is within its expiry window.
- No conflicting assertion undermines the evidence.

Evidence is **insufficient** when any required field is missing, vague, or inadmissible (E-TYPE-05 or E-TYPE-06).

---

## E. Partial Closure Rules

| Status | Definition |
|---|---|
| OPEN | No admissible evidence provided |
| PARTIALLY_ADDRESSED | Some required evidence provided but not sufficient for full closure |
| ADDRESSED | All required evidence provided and sufficient |

Claude Code does not treat `PARTIALLY_ADDRESSED` as `ADDRESSED`. A gap at `PARTIALLY_ADDRESSED`
still blocks the actions it guards. Claude Code states which specific evidence element is
missing when a gap is `PARTIALLY_ADDRESSED`.

---

## F. Evidence Expiry

| Evidence class | Maximum validity |
|---|---|
| Role attendance confirmations (H-05, H-06, H-07, H-08) | 24 hours; re-confirmation required if window shifts |
| Window selection (H-09) | Valid only for the named window; invalid if window changes |
| Go/no-go record (H-10) | Valid only for the named window |
| Approval packet reference (H-01, H-02) | Valid only for the named ceremony instance |
| Channel selection (H-04) | Valid for the named ceremony instance |
| Account scope confirmation (H-11) | Valid for the named ceremony instance |
| Emergency revoke policy (H-13) | Valid until policy is superseded or incident classes change |

**All evidence expires at ceremony window close.** A new ceremony window requires fresh evidence
for all gaps. Prior-window evidence is inadmissible in a subsequent window (E-TYPE-06).

---

## G. Assertion vs. Verification

Claude Code distinguishes between what it can verify locally and what it must accept
on operator assertion:

| Evidence element | Can Claude Code verify? | Basis |
|---|---|---|
| Smoke suite PASS | YES — runs in-session | E-TYPE-04 |
| Safety grep CLEAN | YES — runs in-session | E-TYPE-04 |
| Dry-run currency | YES — if run in-session; NO if asserted from prior session | E-TYPE-04 / E-TYPE-06 |
| Approval packet existence | NO — must accept assertion | E-TYPE-01 |
| Channel class selection | NO — must accept assertion | E-TYPE-02 |
| Role attendance | NO — must accept assertion | E-TYPE-02 |
| Window timing | NO — must accept assertion | E-TYPE-02 |
| Account scope in packet | NO — must not request content; accept reference | E-TYPE-01 |
| Go/no-go record | NO — must accept assertion with named authorizer + timestamp | E-TYPE-01 |

For items Claude Code cannot verify, it records the operator assertion and flags if the
assertion is internally inconsistent or contradicts other asserted evidence.

---

## H. Gap Clustering

Some gaps may be addressed in a single operator assertion that covers multiple gaps.
The following clusters are permitted:

| Cluster | Gaps covered | What the cluster assertion must include |
|---|---|---|
| CLUSTER-01 | H-01 + H-02 | Approval packet reference that confirms: artifact store class + tool + packet ID + packet contains authorizer, tenant, window |
| CLUSTER-02 | H-05 + H-06 | Single role-attendance statement covering both roles; each named individually |
| CLUSTER-03 | H-07 + H-08 | Single role-attendance statement covering rollback owner (A5–A9) and emergency revoke owner (A6–A9); each named individually |
| CLUSTER-04 | H-12 + H-13 | Evidence store + emergency revoke policy may be in same out-of-repo artifact; both must be explicitly confirmed |

**Gaps not listed in a cluster must be addressed individually.**

---

## I. Minimum Gap Set for A1 Proposal

Claude Code may propose A1 to the human operator only when the following are all ADDRESSED:

| Gap | Status required |
|---|---|
| H-01 | ADDRESSED |
| H-02 | ADDRESSED |
| H-03 | ADDRESSED |
| H-04 | ADDRESSED |
| H-05 | ADDRESSED |
| H-06 | ADDRESSED |
| H-09 | ADDRESSED |
| H-10 | ADDRESSED |
| H-11 | ADDRESSED |

Additionally, before any proposal:

| Pre-proposal requirement | Basis |
|---|---|
| Dry-run PASS within 30 days | Phase 2 Section G-C23 |
| Smoke suites PASS in current session | Phase 4 Section F-27/F-28 |
| Safety grep CLEAN in current session | Phase 1 Section I |
| Working tree clean | Standard hygiene |

If any of the above is not met, Claude Code states which item is missing before proposing A1.

---

## J. Stop Conditions

Processing under this document halts immediately if:

| ID | Condition |
|---|---|
| J-01 | An operator claims a gap is closed without providing admissible evidence |
| J-02 | An operator provides TIER-3 content (real credentials, account identifiers) in-conversation |
| J-03 | An operator asserts evidence from a prior ceremony window (E-TYPE-06) as current |
| J-04 | An operator asserts that this document closes any gap (it does not) |
| J-05 | Any active stop condition from Phase 4 Section I or Phase 3 Section K is triggered |
| J-06 | Conflicting evidence is asserted for the same gap without resolution |
| J-07 | Evidence is provided for H-14–H-17 without the corresponding authorization phrase |

---

## K. Acceptance Criteria

- [x] Document created at `docs/GOOGLE_ADS_GAP_CLOSURE_EVIDENCE_REQUIREMENTS.md`.
- [x] Documentation-only.
- [x] Non-authorization statement present.
- [x] Evidence classification defined (6 E-TYPEs; 3 sensitivity tiers).
- [x] Per-gap evidence specs defined for H-01–H-17.
- [x] Evidence sufficiency matrix defined (D.1–D.2).
- [x] Partial closure rules defined (3 states).
- [x] Evidence expiry defined for all evidence classes.
- [x] Assertion vs. verification distinction defined.
- [x] Gap clustering defined (4 clusters).
- [x] Minimum gap set for A1 proposal defined (9 gaps + 4 pre-proposal requirements).
- [x] Stop conditions defined (7 conditions J-01–J-07).
- [x] All 17 gaps (H-01–H-17) remain OPEN — this document does not close any gap.
- [x] No real credentials, operator identities, account identifiers, or Secret Manager paths.
- [x] No OAuth, GCP, Secret Manager, Google Ads API.
- [x] No A1–A10 execution.
- [x] `GOOGLE_ADS_LIVE_ENABLED` remains `false`.

---

**Phase 3 complete. Proceed to Phase 4.**

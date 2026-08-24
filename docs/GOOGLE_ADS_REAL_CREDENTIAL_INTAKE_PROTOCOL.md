# Google Ads Real Credential Intake Protocol — V5.23 Controlled Ceremony

**Kaiju Command Center — V5.23 Phase 3**

**Branch:** `v5.23-controlled-real-oauth-execution-planning`
**Base:** `v5.22.0-beta` / master merge commit `4217652`

---

> **WARNING — READ BEFORE USING THIS DOCUMENT**
>
> - This is a **protocol document only**.
> - This document **does not authorize real credential intake.**
> - This document **does not request** real credentials from any party.
> - **No real credential value** (developer token, client ID, client secret, access token, refresh token, auth code, callback URL, OAuth URL) may be entered in this file.
> - **No real client ID, client secret, developer token, customer ID, login customer ID** may be entered in this file.
> - **No real Secret Manager path** (`projects/.../secrets/.../versions/...`) may be entered in this file.
> - **No real `credential_ref` path** may be entered in this file.
> - **No real service account email** may be entered in this file.
> - **No real GCP project ID or project number** may be entered in this file.
> - **No real approval payload** may be entered in this file.
> - **All examples must use placeholders** in the form `<label_redacted>` — never real values.
> - Real values that must exist for a future authorized live ceremony belong in the **out-of-repository** approval record and the **out-of-repository** approved secure channel — never in this file, never in git, never in chat, never in logs.

---

## A. Protocol Purpose

This document finalizes the future real credential intake protocol for V5.23 controlled Google Ads OAuth execution.

It translates the V5.21 credential handoff protocol (`docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md`) — a design baseline that was purely rehearsal-grade — into a **real-credential-ready operating protocol**. Where V5.21 said "if a real ceremony were ever authorized, this is how it would look," V5.23 Phase 3 says "when a real ceremony is authorized under the A1–A10 model (Phase 2 packet), these are the exact intake safety rules that govern every real value in flight."

**But it still does not authorize intake or execution.** Real credential handoff remains NOT APPROVED. Every A*n* step from the V5.23 authorization packet still requires its own separate explicit approval captured verbatim through an approved out-of-repository channel. This protocol defines the safety envelope inside which those authorized operations must occur — it does not create authorizations.

Purpose in one sentence: **give the future authorized operator an unambiguous, per-credential-class, per-role, per-step safety contract that treats every real value in transit as radioactive until proven otherwise.**

---

## B. Non-Authorization Statement

V5.23 Phase 3 does **not** authorize any of the following. Each item is explicitly out of scope until a later phase receives separate explicit operator approval matching the exact Section E phrase from `docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md`.

- Real credential handoff.
- Real OAuth execution.
- Real approval creation.
- Real OAuth authorization URL generation.
- Browser OAuth flow.
- Callback URL receipt.
- Auth code receipt.
- Token exchange.
- Token response receipt.
- Storing real credentials.
- Secret Manager write.
- Google Ads API call.
- GCP command or GCP API call.
- Deploy.
- IAM changes, API enablement, or billing changes.
- `GOOGLE_ADS_LIVE_ENABLED=true` runtime activation.
- Real rollback or real credential revocation.

None of the above may occur in Phase 3. If this protocol itself creates ambiguity about whether an action is permitted, treat the action as forbidden and ask before proceeding.

---

## C. Credential Class Matrix

Every real value that may exist during a controlled real OAuth ceremony belongs to exactly one credential class. Each class has a mandatory handling profile. **No real value from any class may appear in this document, in git, in chat, in logs, or in any committed file** — only the redacted placeholder form.

| Class | Is secret? | May appear in chat? | May appear in git? | May appear in docs? | May appear in logs? | Approved channel required? | Storage target | Redacted report format | Stop if exposed? |
|---|---|---|---|---|---|---|---|---|---|
| OAuth authorization URL | YES | NO | NO | NO (placeholder only: `<oauth_url_redacted>`) | NO | YES | Ephemeral — consumed by browser and discarded | `<oauth_url_redacted>` | YES |
| OAuth callback URL | YES | NO | NO | NO (placeholder only: `<callback_url_redacted>`) | NO | YES | Ephemeral — consumed by handoff and discarded | `<callback_url_redacted>` | YES |
| OAuth auth code | YES | NO | NO | NO (placeholder only: `<auth_code_redacted>`) | NO | YES (single-use, short-lived) | Consumed by A6 token exchange, then discarded | `<auth_code_redacted>` | YES |
| OAuth access token | YES | NO | NO | NO (placeholder only: `<access_token_redacted>`) | NO | YES | Secret Manager after A7 authorization only | `<access_token_redacted>` | YES |
| OAuth refresh token | YES | NO | NO | NO (placeholder only: `<refresh_token_redacted>`) | NO | YES | Secret Manager after A7 authorization only | `<refresh_token_redacted>` | YES |
| OAuth token response | YES | NO | NO | NO (placeholder only: `<token_response_redacted>`) | NO | YES | Consumed by A7; never persisted as raw JSON | `<token_response_redacted>` | YES |
| Google Ads developer token | YES | NO | NO | NO (placeholder only: `<developer_token_redacted>`) | NO | YES | Secret Manager after A7 authorization only | `<developer_token_redacted>` | YES |
| OAuth client ID | YES (high-sensitivity when paired with client secret) | NO | NO | NO (placeholder only: `<client_id_redacted>`) | NO | YES | Secret Manager after A7 authorization only | `<client_id_redacted>` | YES |
| OAuth client secret | YES | NO | NO | NO (placeholder only: `<client_secret_redacted>`) | NO | YES | Secret Manager after A7 authorization only | `<client_secret_redacted>` | YES |
| Google Ads customer ID | YES (account-identifying) | NO | NO | NO (placeholder only: `<customer_ref>`) | NO | YES | Out-of-repo approval record | `<customer_ref>` | YES |
| Google Ads login customer ID | YES (manager-account-identifying) | NO | NO | NO (placeholder only: `<login_customer_ref>`) | NO | YES | Out-of-repo approval record | `<login_customer_ref>` | YES |
| Secret Manager resource reference (e.g. `projects/N/secrets/S/versions/V`) | YES (infrastructure-identifying) | NO | NO | NO (placeholder only: `<secret_manager_ref_redacted>`) | NO | YES (metadata-only reporting after A7) | Runtime resolution only — never committed | `<secret_manager_ref_redacted>` | YES |
| `credential_ref` (V5.15 internal reference) | YES (indirection identifying) | NO | NO | NO (placeholder only: `<credential_ref_placeholder>`) | NO | YES | Runtime resolution only — never committed | `<credential_ref_placeholder>` | YES |
| Service account email | YES (identity-identifying) | NO | NO | NO (placeholder only: `<service_account_email_redacted>`) | NO | YES | Out-of-repo IAM record | `<service_account_email_redacted>` | YES |
| GCP project reference (ID or number) | YES (project-identifying) | NO | NO | NO (placeholder only: `<gcp_project_ref>`) | NO | YES | Out-of-repo approval record | `<gcp_project_ref>` | YES |
| Approval packet reference (real, filled) | YES (approval-identifying) | NO | NO | NO (placeholder only: `<packet_ref>`) | NO | YES | Out-of-repo approval record | `<packet_ref>` | YES |

**Interpretation notes:**
- "May appear in docs" `NO` means the raw value must never be committed. The placeholder label (e.g., `<refresh_token_redacted>`) may appear anywhere — it is the redacted stand-in and carries no real information.
- "Stop if exposed" `YES` for every row means the incident protocol (Section M) triggers immediately upon any exposure of a real value in that class.
- "Approved channel required" `YES` for every row means transit of the real value must occur only through a Section D approved channel with all preconditions met.
- No class is exempt. Even fields that operators may think of as "less sensitive" (e.g., service account email) are treated as YES because pairing partial identifiers can enable targeted attacks.

---

## D. Approved Channels

An approved channel is any transit medium that satisfies **all** its preconditions at the moment of use. The channel classes below are defined in the abstract; concrete tool selection remains an out-of-repository configuration decision made by the storage owner and stop authority together — Claude Code does not decide tools.

### D.1 — Approved password manager secure item

**Purpose:** Long-term or short-term storage of a real credential value at rest, encrypted, access-controlled.

| Attribute | Requirement |
|---|---|
| Preconditions | Password manager is enterprise-grade, uses zero-knowledge encryption, has a documented access policy, and is under active audit. |
| Who may access | Only the specific `<operator_label>`, `<credential_owner_label>`, and `<secret_writer_label>` named in the packet. |
| What may transit | Any credential class from Section C, encrypted at rest and in transit. |
| What must never be displayed | The raw value on any screen that is shared, recorded, or observed. |
| Evidence allowed | Item reference (`<pw_manager_item_ref>`), access timestamp placeholder, access-actor label. |
| Evidence forbidden | The item value; any screenshot of the item view; any URL of the item that includes the value. |
| Stop conditions | Screen recording active; screen sharing active; unauthorized viewer in the room; access log gap; wrong actor accessed the item. |

### D.2 — Approved encrypted file transfer with out-of-band passphrase

**Purpose:** One-time transfer of a credential bundle between two authorized parties.

| Attribute | Requirement |
|---|---|
| Preconditions | Encrypted archive (AES-256 or stronger); passphrase transmitted through a completely separate channel from the archive; archive filename does not identify contents; archive is deleted from both endpoints within the ceremony window. |
| Who may access | Only the sending party (`<credential_owner_label>`) and receiving party (`<secret_writer_label>`) both named in the packet. |
| What may transit | Any credential class from Section C, inside the encrypted archive. |
| What must never be displayed | The passphrase in a channel where the archive is also visible; the archive contents outside a Section D.3 terminal-entry-without-echo procedure. |
| Evidence allowed | Archive filename placeholder (`<archive_ref>`); passphrase channel reference (`<passphrase_channel_ref>`); delivery timestamp placeholder. |
| Evidence forbidden | The passphrase itself; the archive contents; the actual filename if it discloses class; any screenshot of the delivery. |
| Stop conditions | Same-channel passphrase transmission; unencrypted archive; missing deletion confirmation from either endpoint; interception evidence. |

### D.3 — Approved operator-local terminal entry without echo where available

**Purpose:** Entry of a real credential into the receiving system (e.g., piping to a Secret Manager write via a stdin-only path) without displaying the value on screen.

| Attribute | Requirement |
|---|---|
| Preconditions | Terminal has echo disabled for the input; no screen recording is active; no screen sharing is active; shell history is disabled or the command is prefixed to suppress history; the receiving process reads from stdin (or an approved analog) and never re-prints the value. |
| Who may access | Only the `<operator_label>` performing the entry, physically alone at the terminal (or with the reviewer present in-room but not viewing the screen). |
| What may transit | A single credential class per entry from Section C. |
| What must never be displayed | The credential on the terminal; the credential in a subsequent `history` command; the credential in a subsequent `env` command; the credential in any process listing. |
| Evidence allowed | Entry timestamp placeholder; operator label; command outcome (PASS/FAIL); redacted field-count report. |
| Evidence forbidden | The credential; the raw command line; the receiving process's raw stdout; any process-listing output containing the credential. |
| Stop conditions | Echo not disabled; shell history not disabled; screen recording on; screen sharing on; the receiving process echoes the value back; the value appears in any log written during the entry. |

### D.4 — Approved cloud secret write path only after A7 authorization

**Purpose:** Write the credential bundle into Secret Manager as the durable storage of record.

| Attribute | Requirement |
|---|---|
| Preconditions | V5.23 A7 phrase captured verbatim through out-of-repo channel; V5.15/V5.16 write path (`POST /credentials/google-ads`) is the invoked route; `GCP_SECRET_MANAGER_ENABLED=true`; secret path is the pre-approved path from the out-of-repo record; audit path writable; rollback/emergency-revoke owners present; version lifecycle policy set to `DISABLE_PREVIOUS_WITH_GRACE_PERIOD`. |
| Who may access | Only the `<secret_writer_label>` invokes the write; reviewer confirms preconditions. |
| What may transit | The complete credential bundle from Section C token/secret classes, atomically, through the V5.15 admin path. |
| What must never be displayed | The bundle payload before, during, or after the write; the Secret Manager response body raw JSON; the resolved resource path with real project number. |
| Evidence allowed | Write status boolean; field presence booleans; version index placeholder; audit event `seq`/`digest` (V5.16 chain); redacted `<secret_manager_ref_redacted>`. |
| Evidence forbidden | The bundle values; the raw response body; the actual resource path; the actual project number/ID; the actual secret name; the audit JSON with raw fields. |
| Stop conditions | Missing A7 phrase; wrong secret path; write ambiguity; response body error; audit chain broken; version lifecycle policy not confirmed; rollback owner absent. |

### D.5 — What is not an approved channel

| Channel | Reason |
|---|---|
| Chat sessions (Claude Code, ChatGPT, Slack, GitHub) | Conversation logs may be retained; observed sessions. |
| Git commits, PR bodies, issue comments, commit messages | Permanent public/semi-public record; unpurgeable. |
| Repository documentation files | Committed docs are a permanent record. |
| Screenshots | Anything visible is disclosed. |
| Screen recordings | Same. |
| Plain email | Unless explicitly designated and encrypted end-to-end via a future authorization, email is forbidden. |
| Any medium not enumerated in Sections D.1–D.4 | If a channel is not on the approved list, it is not approved. Ambiguity is a stop condition. |

---

## E. Forbidden Channels

The following are **absolutely forbidden** for transit or storage of any credential class from Section C. Use of a forbidden channel at any point is an immediate stop condition and triggers the incident protocol (Section M).

| # | Channel |
|---|---|
| E-F1 | ChatGPT chat (any variant, any deployment) |
| E-F2 | Claude chat (any variant, any deployment) |
| E-F3 | Terminal with visible transcript (screen sharing, recording, or observed session) |
| E-F4 | Shell history (bash, zsh, fish, PowerShell, or any shell without history suppression) |
| E-F5 | Git commits (any branch, any repo) |
| E-F6 | Repository files (any file under the working tree) |
| E-F7 | `.env` files inside the repository |
| E-F8 | Credential JSON files inside the repository |
| E-F9 | Screenshots of any kind |
| E-F10 | Screen recordings |
| E-F11 | Plain (unencrypted) email |
| E-F12 | Slack, Microsoft Teams, WhatsApp, Telegram, iMessage, SMS, or any other messaging platform not explicitly on the D.1–D.4 approved list |
| E-F13 | Public GitHub issue or PR comments; issue titles; PR titles |
| E-F14 | Application logs (application logger, structured logger, cloud logger, or any downstream aggregator) |
| E-F15 | CI/CD job output (GitHub Actions logs, Cloud Build logs, or any other build system output) |
| E-F16 | Browser history copied into documentation or commits |
| E-F17 | Clipboard shared across untrusted applications (clipboard managers with history retention, cross-device sync services) |

**Rule:** if a channel is not listed as approved (Sections D.1–D.4) and it can retain, log, transmit, or display data, treat it as forbidden.

---

## F. Intake Roles and Responsibilities

Every role below is filled by a specific human named only in the out-of-repository approval record. **This document uses placeholder labels only.** Real names, emails, phone numbers, or other identifying information must never appear in git.

| Role label | Responsibility | May see secrets? | May write evidence? | May authorize? | May stop ceremony? |
|---|---|---|---|---|---|
| `<operator_label>` | Executes the intake step under the authorization phrase captured for that step; performs the physical action (terminal entry, secret write invocation, etc.). | ONLY THROUGH APPROVED CHANNEL | YES (redacted only) | NO (may request authorization; may not grant it) | YES |
| `<reviewer_label>` | Confirms preconditions, validates the exact authorization phrase, verifies redaction at each step, countersigns evidence. | ONLY THROUGH APPROVED CHANNEL | YES (redacted only) | Depends on packet (typically NO for A1–A10 grant; YES for continue-past-pause) | YES |
| `<credential_owner_label>` | Owns the source credential material and controls the sending endpoint (password manager item, encrypted archive origin). | YES (owns the source; must never display) | YES (redacted only) | NO | YES |
| `<secure_channel_owner_label>` | Owns and operates the approved secure channel infrastructure (password manager access grants, encrypted-transfer setup, terminal preparation). | ONLY THROUGH APPROVED CHANNEL METADATA | YES (redacted only) | NO | YES |
| `<secret_writer_label>` | Invokes the Secret Manager write path under A7 authorization; receives the credential via the approved channel; performs the atomic write. | ONLY THROUGH APPROVED CHANNEL | YES (redacted only — status booleans, field counts) | NO | YES |
| `<stop_authority_label>` | Holds the halt authority for the ceremony; declares STOP on any Section K condition; final arbiter of incident-versus-continue. | NO (works from redacted status only) | YES (halt decisions, redacted only) | NO for A1–A10 grants; YES for halt/continue decisions | YES (supreme) |
| `<rollback_owner_label>` | Prepares and executes rollback flow if any step from A5–A9 fails or needs reversal; reachable throughout the ceremony window. | NO (works from redacted status only) | YES (rollback execution records, redacted only) | NO for A1–A9 grants; YES for A10 rollback under approved emergency policy | YES |
| `<emergency_revoke_owner_label>` | Executes emergency revocation of a credential that has been leaked or compromised; reachable throughout A6–A9 windows. | NO (works from redacted status only) | YES (revoke execution records, redacted only) | NO for A1–A9 grants; YES for A10 emergency revoke only under out-of-repo emergency policy | YES |
| `<evidence_owner_label>` | Assembles the redacted evidence package; verifies no forbidden content is present before commit; performs final safety grep review. | ONLY THROUGH APPROVED CHANNEL METADATA | YES (assembles the record) | NO | YES (on evidence integrity failure) |

**Overrides and cross-cutting rules:**
- The stop authority may halt the ceremony at any point without countersignature.
- No role may see a raw secret except through an approved channel and only when required by the specific step.
- No role may authorize its own step (self-authorization prohibited).
- Roles may be doubled by one human only if the approval record explicitly enumerates the doubling; otherwise each role is a distinct human.
- Role attendance must be re-confirmed at each mandatory pause point (P1–P*n* in the execution runbook once Phase 4 is written).

---

## G. Intake Sequence

The following sequence extends the V5.21 handoff protocol (E1–E12) and the V5.23 A1–A10 authorization model. Every step is guarded by explicit authorization; **no step implies the next**.

| Step | Action | Authorization required |
|---|---|---|
| G1 | Confirm A1 and A2 authorization status from the approval packet (Section D of `docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md`) | A1 and A2 phrases captured verbatim (out-of-repo) |
| G2 | Confirm approved secure channel readiness (Section D.1–D.4 preconditions all met) | Secure-channel owner countersigns readiness |
| G3 | Confirm attendance of all required roles from Section F (operator, reviewer, credential owner, secure channel owner, secret writer for later steps, stop authority, rollback owner, emergency revoke owner, evidence owner) | Reviewer countersigns attendance |
| G4 | Confirm stop authority is present and reachable throughout window | Stop authority confirms |
| G5 | Confirm rollback and emergency revoke owners are present and reachable for A5–A9 window | Rollback owner and emergency revoke owner both confirm |
| G6 | Confirm safety grep baseline is CLEAN across all 9 patterns on all modified files | Evidence owner verifies |
| G7 | Confirm smoke baseline: `smoke_test_v5_credentials.sh` 35/35 PASS and `smoke_test_v5_12_gcp_secret_manager.sh` 8/8 PASS immediately before window | Evidence owner verifies |
| G8 | Confirm working tree is clean (`git status --short` empty) and branch matches expected V5.23 branch | Reviewer confirms |
| G9 | Confirm no `.env` file and no credential JSON file exist anywhere in the repository | Evidence owner verifies (grep + find) |
| G10 | Open approved secure channel per Section D | Secure-channel owner + credential owner |
| G11 | Transfer only the credential class authorized for the current step; do not transfer any class not covered by the current authorization | Credential owner (send); operator/secret writer (receive per step) |
| G12 | Confirm receipt without displaying the credential value; use field-count-only verification or redacted-status verification | Receiving role + reviewer countersign |
| G13 | Record redacted evidence reference only; commit no raw value; commit no derivative that could be reverse-engineered | Evidence owner |
| G14 | Close secure channel per Section D (archive deleted, item access revoked, terminal input finalized) | Secure-channel owner |
| G15 | Run immediate safety grep across all files touched in the ceremony window; run `git diff` review; confirm no forbidden pattern is present | Evidence owner + reviewer |
| G16 | Decide whether to proceed to A3/A4/A5/A6/A7 **only if separately authorized** for the next step; do not chain from prior authorization | Requires new Section E phrase for the next step |
| G17 | If exposure occurs at any point, STOP and execute the incident protocol in Section M immediately | Stop authority (supreme); incident protocol M1 (halt) is unilateral |
| G18 | After ceremony closes, confirm no credential material entered chat, git, docs, logs, shell history, or any other forbidden channel; run final safety grep; verify audit chain intact | Evidence owner + reviewer countersign closure |

**Non-implication rules (asymmetric authorization chains):**
- Credential intake (G-series) does not imply OAuth execution (A3/A4).
- OAuth execution does not imply token exchange (A6).
- Token exchange does not imply Secret Manager write (A7).
- Secret Manager write does not imply Google Ads API validation (A8).
- Google Ads API validation does not imply live flag activation (A9).
- Live flag activation does not imply future re-activation.
- Rollback (A10) does not authorize new intake — a fresh authorization packet is required.

**Time-slot rules:**
- Each step in the G-series must be completed within its allotted slot inside the timebox window from the approval packet.
- Exceeding a slot without an explicit continue-approval from the stop authority is a stop condition.
- The full G1–G18 sequence must complete within the packet's `<timebox_ref>` window end. If the window closes mid-sequence, all in-flight state is treated as suspect and rollback preconditions apply.

---

## H. Secret Manager Handoff Boundary

Secret Manager write is not authorized by this protocol.

Secret Manager write requires **A7 explicit authorization** — the exact Section E.7 phrase from the V5.23 authorization packet, captured verbatim through the approved out-of-repository channel.

### H.1 — Before A7

Before A7 is authorized:

- No Secret Manager call may be made from Claude Code or from any operator script.
- No GCP command (any `gcloud` invocation, any `gsutil` invocation, any `bq` invocation, any GCP API call) may be issued.
- No secret write attempt may be made — even to a test path.
- No secret path containing a real project ID, real project number, real secret name for a real project, or real version index may be committed to any file.
- No credential payload may be printed to any terminal.
- No local durable file containing credentials may be created inside the repository — no `.env`, no credential JSON, no cache file.
- No token or bundle may be staged for a later automated write; automation is not authorized.

### H.2 — After A7 (only within the authorized window)

Once A7 has been authorized under the exact Section E.7 phrase and the timebox window is open, the write may proceed subject to Section D.4 preconditions.

The A7 step may report **only** the following:

| Reportable | Form |
|---|---|
| Operation status | `PASS` \| `FAIL` |
| Field presence booleans | Presence of each expected field (developer token present, client ID present, client secret present, refresh token present) — booleans, not values |
| Secret version status | Version index placeholder (`<version_ref>`); version state (`ENABLED` \| `DISABLED`); version count if V5.20 lifecycle policy has been applied |
| Redacted credential reference placeholder | `<credential_ref_placeholder>` — never the real path |
| Audit event status | `seq` value; `digest` value; audit chain unbroken confirmation |

The A7 step **must not** report:

| Non-reportable | Why |
|---|---|
| Token values (access or refresh) | Section C — YES to `Stop if exposed` |
| Client secret | Section C — YES to `Stop if exposed` |
| Developer token | Section C — YES to `Stop if exposed` |
| Customer ID | Section C — account-identifying |
| Login customer ID | Section C — manager-account-identifying |
| Actual Secret Manager path | Infrastructure-identifying |
| Project ID or project number | Project-identifying |
| Service account email | Identity-identifying |
| Raw response body | Would contain path and metadata |
| Any diff of before/after payloads | Would reveal delta |

### H.3 — If A7 reporting rules are violated

Immediate stop condition. Section M incident protocol applies. Rollback flow (A10) may be required.

---

## I. Rotation and Revocation Boundary

Existing lifecycle controls (referenced only — no execution authorized by this protocol):

| Control | Reference | Purpose |
|---|---|---|
| V5.15 delete/revoke endpoint | `DELETE /credentials/google-ads` (requires `OPENCLAW_ADMIN_DELETE_ENABLED=true`; `AdminScope.DELETE` scope) | Deletes the secret and all versions; marks CredentialReference as `REVOKED` |
| V5.16 rotate endpoint | `POST /credentials/google-ads/rotate` (requires `AdminScope.ROTATE`) | Rotates via `put_secret_bundle()`; new version replaces existing; prior version handled per V5.20 lifecycle policy |
| V5.20 rollback drill | `openclaw/rollback_drill.py` (`validate_rollback_drill()`) | Local-only dry-run of rollback readiness; must PASS as a prerequisite gate |
| V5.20 Secret Manager version lifecycle policy | `openclaw/secret_version_policy.py` (`validate_secret_version_policy()`) | Enforces `DISABLE_PREVIOUS_WITH_GRACE_PERIOD` policy for version transitions |
| V5.23 A10 rollback/revoke step | Section E.10 of `docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md` | The explicit authorization step for real rollback/revoke |

### I.1 — Boundary rules

- **No rollback or revoke is authorized by this protocol.** A10 is the sole authorization surface for real rollback/revoke actions.
- **Emergency policy exception:** if a documented emergency policy exists in the out-of-repository approval record and it explicitly authorizes emergency revoke without a fresh A10 phrase, the emergency revoke owner may proceed under that policy — but must record the invocation in redacted form and immediately notify stop authority.
- **Even under emergency policy**, revocation must avoid logging secret values. The V5.15 delete endpoint returns metadata only; use that. Do not fetch, print, or paste the credential before deletion.
- After any rollback or revoke, all subsequent activity is a **new ceremony**: a new authorization packet is required; no in-flight authorizations carry over.

---

## J. Redaction and Evidence Rules

### J.1 — Allowed evidence (may appear in committed files)

| Category | Example |
|---|---|
| Role label | `<operator_label>`, `<reviewer_label>` |
| Step ID | `G11`, `A3`, `A7` |
| Packet reference | `<packet_ref>` |
| Ceremony reference | `<ceremony_ref>` |
| Secure-channel reference | `<pw_manager_item_ref>`, `<archive_ref>` |
| PASS/FAIL status | `G11: PASS`, `A7: FAIL (reason: K-9)` |
| Timestamp placeholder | `<timestamp_redacted>` |
| Safety grep status | `safety grep: CLEAN` |
| Smoke suite status | `smoke_test_v5_credentials.sh: 35/35 PASS` |
| Redacted credential class label | `<refresh_token_redacted>`, `<customer_ref>` |
| Redacted evidence reference | `<evidence_ref>` |
| Version index placeholder | `<version_ref>` |
| Audit chain metadata | `seq=N`, `digest=<hash_prefix_redacted>` |

### J.2 — Forbidden evidence (must never appear in committed files)

| Category | Absolute rule |
|---|---|
| Secret values (any Section C class) | **Never committed** |
| Auth code | **Never committed** |
| Token response body | **Never committed** |
| OAuth URL | **Never committed** |
| Callback URL | **Never committed** |
| Client ID | **Never committed** |
| Client secret | **Never committed** |
| Developer token | **Never committed** |
| Customer ID | **Never committed** |
| Login customer ID | **Never committed** |
| Secret Manager path (`projects/N/secrets/S/versions/V`) | **Never committed** |
| Project ID or project number | **Never committed** |
| Service account email | **Never committed** |
| Real approval raw payload | **Never committed** |
| Screenshots containing any of the above | **Never committed** |
| Real operator name, email, or phone | **Never committed** |

### J.3 — Pre-commit redaction procedure

Before any commit that touches a ceremony artifact:

1. Scan the file for any of the J.2 forbidden patterns.
2. Run all 9 safety greps from Section I of `docs/V5_23_IMPLEMENTATION_PLAN.md`.
3. If any hit is not a documentation label, prohibition text, or template placeholder, halt and redact.
4. Only after redaction is confirmed complete may the file be staged.
5. `git diff --cached` must be visually inspected line-by-line before commit.

---

## K. Stop Conditions

Any of the following conditions immediately halts the ceremony, voids any in-flight authorization, and triggers the incident protocol (Section M).

| # | Stop condition |
|---|---|
| K-01 | Any real credential value appears in chat (Claude Code, ChatGPT, Slack, GitHub, or any observed session) |
| K-02 | Any real credential value appears in git (any file, any branch, any repo) |
| K-03 | Any real credential value appears in a committed documentation file |
| K-04 | Any real credential value appears in logs (application, structured, cloud, CI, or any downstream aggregator) |
| K-05 | Any real credential value appears in shell history (bash, zsh, fish, PowerShell, or any shell) |
| K-06 | An unauthorized channel (any not in Section D.1–D.4) is used for credential transit |
| K-07 | A screenshot containing a real credential is created (even if not committed) |
| K-08 | Screen recording is active during any credential handling step |
| K-09 | A credential class is transmitted or accessed outside the authorization scope for the current step (e.g., transferring a refresh token while only A5 auth code handling is authorized) |
| K-10 | Approval packet is missing, expired, revoked, or scope-mismatched at execution time |
| K-11 | A1 (create real approval packet) attempted without the exact Section E.1 phrase |
| K-12 | A2 (prepare secure credential handoff channel) attempted without the exact Section E.2 phrase |
| K-13 | A3 (generate real OAuth authorization URL) attempted without the exact Section E.3 phrase |
| K-14 | A4 (open browser OAuth flow) attempted without the exact Section E.4 phrase |
| K-15 | A5 (receive callback and handle auth code) attempted without the exact Section E.5 phrase |
| K-16 | A6 (exchange auth code for tokens) attempted without the exact Section E.6 phrase |
| K-17 | A7 (store credentials in Secret Manager) attempted without the exact Section E.7 phrase |
| K-18 | A8 (first read-only Google Ads API validation) attempted without the exact Section E.8 phrase |
| K-19 | A9 (activate live flag) attempted without the exact Section E.9 phrase |
| K-20 | A10 (rollback/revoke) attempted without the exact Section E.10 phrase and without documented emergency policy |
| K-21 | Safety grep produces a sensitive hit (not documentation, prohibition, or table-label text) |
| K-22 | Any of the 10 required tests fails (8 demos + 2 smoke suites) |
| K-23 | Working tree is dirty at execution time |
| K-24 | Tenant/client scope is unclear (no named `<tenant_ref>` / `<client_ref>` resolvable through the secure channel) |
| K-25 | Credential owner is unavailable at time of intake |
| K-26 | Stop authority is unavailable at any point during the window |
| K-27 | Rollback owner is unavailable at any point during A5–A9 window |
| K-28 | Emergency revoke owner is unavailable at any point during A6–A9 window |
| K-29 | Token response is visible on screen longer than the immediate consumption step allows |
| K-30 | Secret is copied to clipboard without the approved procedure (e.g., without immediate `pbcopy`-then-clear equivalent, without clipboard-history-suppression) |
| K-31 | A local temporary file containing credentials is created outside the approved procedure |
| K-32 | A `.env` or credential JSON file is created inside the repository at any point during the ceremony |
| K-33 | Paraphrased authorization is accepted (the exact Section E phrase is not captured; a summary or reworded version is used) |
| K-34 | Audit chain verification fails at any point (broken `seq` or `digest`) |
| K-35 | Any role in Section F is doubled by one human without explicit approval enumeration |

---

## L. Pre-Intake Checklist

The following checklist must be PASS in full **immediately before** any intake step. Every item must be verified by the reviewer at the time of execution, not at any earlier draft time.

| # | Check | Verified |
|---|---|---|
| L-01 | Branch confirmed (`v5.23-controlled-real-oauth-execution-planning` or the currently authorized ceremony branch) | [ ] |
| L-02 | Working tree clean (`git status --short` shows no unexpected changes) | [ ] |
| L-03 | Current V5.23 phase confirmed | [ ] |
| L-04 | Target step ID confirmed (exactly one from A1–A10) | [ ] |
| L-05 | Authorization packet reference is present and resolves to a valid out-of-repo record | [ ] |
| L-06 | A1 status confirmed (approval packet artifact exists in the out-of-repo store, if the current step depends on it) | [ ] |
| L-07 | A2 status confirmed (secure channel prepared, if the current step depends on it) | [ ] |
| L-08 | Tenant/client placeholder scope confirmed via secure channel resolution | [ ] |
| L-09 | `<operator_label>` present and identified in-room or on secure video | [ ] |
| L-10 | `<reviewer_label>` present and identified | [ ] |
| L-11 | `<credential_owner_label>` present and identified (for intake steps) | [ ] |
| L-12 | `<secure_channel_owner_label>` present and identified | [ ] |
| L-13 | `<stop_authority_label>` present and reachable | [ ] |
| L-14 | `<rollback_owner_label>` present and reachable (for A5–A9) | [ ] |
| L-15 | `<emergency_revoke_owner_label>` present and reachable (for A6–A9) | [ ] |
| L-16 | `<evidence_owner_label>` present and identified | [ ] |
| L-17 | Safety grep CLEAN across all 9 patterns on all files touched this window | [ ] |
| L-18 | `smoke_test_v5_credentials.sh` PASS — 35/35 | [ ] |
| L-19 | `smoke_test_v5_12_gcp_secret_manager.sh` PASS — 8/8 | [ ] |
| L-20 | All 8 demos PASS (dry-run execution, rollback drill, secret version policy, OAuth approval packet, OAuth callback, OAuth auth URL, credential intake, onboarding ceremony) | [ ] |
| L-21 | No `.env` file exists anywhere in the repository | [ ] |
| L-22 | No credential JSON file exists anywhere in the repository | [ ] |
| L-23 | Shell history protection considered (history suppression enabled or terminal in secure mode) | [ ] |
| L-24 | Screen recording is disabled on the operator's machine | [ ] |
| L-25 | Screen sharing is disabled during any credential handling step | [ ] |
| L-26 | Screenshots are prohibited (operator agreement) | [ ] |
| L-27 | Approved secure channel (per Section D) is open and preconditions met | [ ] |
| L-28 | Evidence reference (`<evidence_ref>`) prepared and out-of-repo location confirmed writable | [ ] |
| L-29 | Section M incident stop procedure visible or ready to invoke | [ ] |
| L-30 | Clipboard is not shared across untrusted apps (no clipboard-history sync, no cross-device clipboard) | [ ] |
| L-31 | Timebox window is currently open (start time reached, end time not reached) | [ ] |

**Any [ ] left unchecked at execution time invalidates the intake and requires a full pre-authorization cycle restart.**

---

## M. Incident Protocol

If a real value leaks through any channel — approved or forbidden — execute the following sequence immediately. No item may be skipped.

| Step | Action |
|---|---|
| M1 | **STOP.** Halt all in-flight ceremony steps. Do not proceed with any next step. |
| M2 | **Do not copy further.** Do not re-paste the exposed value into any location. |
| M3 | **Do not paste into chat.** The value that leaked must not be discussed in any chat channel, including this one. |
| M4 | **Do not commit.** If a commit is in progress, `git reset` the changes; if a commit already happened, do not push — proceed to M8/M10 for rotation before any further git operation. |
| M5 | **Close the exposed surface.** Close the chat window, close the browser tab, close the terminal, revoke the shared screen, delete the file — whichever surface exposed the value. |
| M6 | **Capture only redacted incident metadata.** Time of detection (placeholder); role who detected (label); credential class exposed (label, not value); exposure surface class (chat/log/file/screen/etc.); duration of exposure (approximate window). No raw value in the incident metadata. |
| M7 | **Notify the stop authority.** Use an approved channel (Section D.1–D.4). Do not notify via a forbidden channel that would compound the exposure. |
| M8 | **Determine whether A10 rollback/revoke is required.** For any credential exposed from Section C classes (developer token, client secret, refresh token, access token, auth code), rollback/revoke is mandatory. For account identifiers (customer ID, login customer ID), consult stop authority for scope. |
| M9 | **If A10 is required, request explicit emergency authorization** through the approved secure channel, unless a documented emergency policy in the out-of-repo record already explicitly authorizes emergency revoke for this class. |
| M10 | **Rotate/revoke only through the approved path** — V5.15 `DELETE /credentials/google-ads` for revoke; V5.16 `POST /credentials/google-ads/rotate` for rotation. Do not fetch the credential before deletion; work from metadata only. |
| M11 | **Run safety grep** across the repository to confirm no residual exposure exists in committed files. |
| M12 | **Verify working tree is clean** and no forbidden pattern remains anywhere in the repo. |
| M13 | **Record redacted incident closure** in the out-of-repo evidence store: incident reference (placeholder), rotation/revoke reference (placeholder), post-incident safety grep status, closing timestamp placeholder, closing role label. |

**Post-incident:** all subsequent activity is a **new ceremony**. A new authorization packet is required. No in-flight authorizations carry over. The exposed credential is treated as compromised regardless of the response speed.

---

## N. Relationship to Previous Controls

| Control | Milestone | Role |
|---|---|---|
| V5.21 credential handoff protocol (`docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md`) | V5.21 | Design baseline — this Phase 3 document is its real-credential-ready operating counterpart. |
| V5.22 dry-run PASS (`docs/V5_22_FINAL_DRY_RUN_REVIEW.md`, tag `v5.22.0-beta`) | V5.22 | Rehearsal readiness proof — does not authorize live credential use. |
| V5.23 Phase 2 packet (`docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md`) | V5.23 | Defines explicit A1–A10 authorization surface — this Phase 3 protocol defines intake safety inside that surface. |
| V5.23 Phase 1 plan (`docs/V5_23_IMPLEMENTATION_PLAN.md`) | V5.23 | Defines the 10-phase roadmap, boundary rules, stop conditions, and safety envelope. |
| V5.19 live-mode gate, approval workflow, preflight (`openclaw/live_gate.py`, `openclaw/preflight.py`) | V5.19 | Runtime gate — must deny by default; A9 authorization is required to open. |
| V5.20 rollback drill and secret version lifecycle policy (`openclaw/rollback_drill.py`, `openclaw/secret_version_policy.py`) | V5.20 | Validators that must PASS as prerequisite gates before A7/A10 execution. |
| V5.15/V5.16 credential lifecycle endpoints | V5.15/V5.16 | The write/rotate/delete surfaces used by A7 and A10 under authorization. |
| V5.12 Secret Manager backend (`GCPSecretManagerStore`) | V5.12 | The underlying storage backend for A7 writes. |

**Cumulative rule:** None of the controls above, individually or in combination, authorize live credential use. Live credential intake is authorized only when the V5.23 A1–A10 phrase is captured verbatim for the specific step through an approved out-of-repository channel, and this Phase 3 protocol's Section L pre-intake checklist is PASS in full.

---

## O. Phase 3 Conclusion

**V5.23 Phase 3 result:**

- [x] Real credential intake protocol created at `docs/GOOGLE_ADS_REAL_CREDENTIAL_INTAKE_PROTOCOL.md`.
- [x] Documentation-only.
- [x] All examples use `<label_redacted>` placeholder form.
- [x] No real credentials requested.
- [x] No real credentials received or handled in any form.
- [x] No real approval created.
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
- [x] Working tree remains ready for commit.

**Phase 4 (OAuth execution runbook final go/no-go checklist — `docs/GOOGLE_ADS_REAL_OAUTH_EXECUTION_RUNBOOK.md`) remains pending.** Phases 5–10 also remain pending as described in `docs/V5_23_IMPLEMENTATION_PLAN.md`.

**This document does not authorize any live credential intake, OAuth execution, Secret Manager write, Google Ads API call, GCP command, IAM change, deploy, or live flag activation.** A live step is authorized only when the corresponding A*n* exact phrase from `docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md` Section E is captured verbatim through an approved out-of-repository channel, the Section L pre-intake checklist here is PASS in full, and no Section K stop condition is triggered.

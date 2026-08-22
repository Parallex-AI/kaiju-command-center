# Google Ads Credential Handoff Protocol — V5.21 Controlled OAuth Onboarding

**Kaiju Command Center — V5.21 Phase 5**

**Branch:** `v5.21-controlled-real-google-ads-oauth-onboarding`

---

> **WARNING — READ BEFORE USING THIS DOCUMENT**
>
> - This protocol is **documentation-only**. It does not authorize real credential handoff.
> - This protocol does not authorize Secret Manager writes.
> - This protocol does not authorize OAuth execution.
> - This protocol does not authorize Google Ads API calls.
> - This protocol does not authorize GCP operations.
> - This protocol does not authorize `GOOGLE_ADS_LIVE_ENABLED=true`.
> - **All real execution requires separate explicit operator approval.**
> - **Do not paste credentials, OAuth URLs, auth codes, refresh tokens, or access tokens into chat.**
> - **Do not commit any real credential value, token, resource path, customer ID, project ID, or account email.**
> - **No real Secret Manager write is performed by this document.**
> - **Any handoff step must stop immediately** if credential leakage, unexpected Secret Manager behavior, or missing rollback evidence is detected.

---

## A. Protocol Purpose

This document defines the secure handoff sequence by which OAuth ceremony output — refresh token, access token, client ID, client secret, developer token, and customer IDs — would be transferred to the Secret Manager write path under V5.15–V5.17 infrastructure. This is a design protocol only. No credentials are present in this document. No Secret Manager write is performed. No GCP call is made.

V5.21 Phase 5 creates this protocol as a reference for a future authorized ceremony execution operator. The protocol must be read and confirmed in full by all required participants before any real handoff step is initiated. The protocol gates every handoff action behind explicit operator confirmation.

**This document does not authorize execution.** An authorized future execution operator must receive a separate, explicit, non-expired approval record before using this protocol to perform any real handoff.

**Phase 6 cross-reference:** `openclaw/oauth_approval_packet.py` (`validate_oauth_approval_packet()`) must return PASS before any credential handoff step can begin. The approval packet validator confirms that the credential handoff protocol (this document) has been reviewed (`credential_handoff_protocol_present=True`) as a prerequisite gate. Credential handoff cannot proceed without approval packet PASS. Phase 6 does not create a real approval record, does not perform a real handoff, and does not authorize execution.

---

## B. Credential Classes Covered by This Protocol

The following credential classes are produced by a completed Google Ads OAuth ceremony and are covered by this protocol. No real values for any class may appear in this document or any committed file.

| Class | Source | Sensitivity | Committed form |
|---|---|---|---|
| OAuth refresh token | Token exchange response | **CRITICAL** | Redacted (`<refresh_token_redacted>`) |
| OAuth access token | Token exchange response | **CRITICAL** | Redacted (`<access_token_redacted>`) |
| OAuth client ID | OAuth ceremony setup | **HIGH** | Redacted (`<client_id_redacted>`) |
| OAuth client secret | OAuth ceremony setup | **CRITICAL** | Redacted (`<client_secret_redacted>`) |
| Developer token | Google Ads developer account | **HIGH** | Redacted (`<developer_token_redacted>`) |
| Customer ID | Google Ads account | **HIGH** | Redacted (`<customer_id_redacted>`) |
| Login customer ID | Google Ads manager account | **HIGH** | Redacted (`<login_customer_id_redacted>`) |

No raw value for any credential class above may be:
- Pasted into any chat session (Claude, ChatGPT, Slack, GitHub, or any observed session)
- Committed to this repository
- Written to a terminal with screen recording or shared access active
- Printed to any log file without immediate redaction

---

## C. Forbidden Transmission Channels

The following channels are **prohibited** for transmitting any credential produced by the OAuth ceremony. Use of a forbidden channel at any handoff step is an immediate stop condition.

| Channel | Reason | Action if detected |
|---|---|---|
| Chat session (Claude Code, ChatGPT, or similar) | Observed session risk; conversation logs may be retained | STOP immediately; treat as credential leakage incident |
| Slack DM or public channel | Not encrypted at rest to required standard; not access-controlled for credential data | STOP; revoke exposed credential |
| GitHub issue, PR comment, or commit message | Permanent public or semi-public record; cannot be fully purged | STOP; assume credential compromised |
| Email (any provider) | Transmission logs; inbox access not controlled; replay risk | STOP; revoke and rotate |
| SMS or messaging app | No access control; device backup risk | STOP; revoke and rotate |
| Clipboard paste into shared screen or recording | Screen recording may capture credential | STOP; treat as leakage |
| Unencrypted local file (e.g., `.env`, `.json` in repo) | Accidental commit risk; not rotation-safe | STOP; do not write; use Secret Manager path only |
| Plaintext terminal output with logging active | Logging system may retain; shared terminal risk | STOP; verify logging is off before any display |
| Documentation file in repository | Committed doc is permanent record | STOP; redact before any commit |

---

## D. Acceptable Transmission Channels

The following channels are **acceptable** for credential handoff, subject to the conditions listed. Each condition must be confirmed before use.

| Channel | Conditions required | Confirmed by |
|---|---|---|
| Direct Secret Manager write path (V5.15+ `write_credential_bundle()`) | Storage boundary confirmed; approval record present; audit event enabled; version lifecycle policy confirmed | `<storage_owner_label>` |
| Local encrypted credential file (operator workstation only, outside repo) | AES-256 or equivalent; no repo path; deleted after Secret Manager write confirmed | `<credential_handler_label>` |
| Encrypted out-of-band channel (approved operator tooling only) | End-to-end encryption confirmed; no log retention; limited to ceremony participants | `<approval_owner_label>` |
| Read-aloud to second operator in private secure room (for short values only) | No screen recording active; no shared display; second operator confirms receipt | `<operator_label>` + `<reviewer_label>` |

No channel outside this table may be used. Any ambiguity about channel acceptability is a stop condition.

---

## E. Handoff Sequence

The following sequence defines the order of handoff operations after a successful OAuth token exchange. Each step must be confirmed in order. Steps must not be skipped. Any FAIL at any step halts the handoff immediately.

| Step | Action | Gate | Confirmed |
|---|---|---|---|
| E1 | Confirm token exchange result is PASS — `validate_oauth_callback_design()` PASS | Token exchange gate PASS required | [ ] |
| E2 | Confirm approval record is present and not expired | Approval ref and expiry confirmed | [ ] |
| E3 | Confirm storage owner is present | `<storage_owner_label>` role confirmed | [ ] |
| E4 | Confirm audit event logging is active | Audit event write verified against V5.15–V5.16 audit path | [ ] |
| E5 | Confirm secret name / path is approved in approval record | Pre-approved path only — no improvised naming | [ ] |
| E6 | Confirm version lifecycle policy is set to `DISABLE_PREVIOUS_WITH_GRACE_PERIOD` | V5.20 policy validator PASS confirmed | [ ] |
| E7 | Confirm rollback path is ready before write | Revocation path in Section M confirmed; rollback owner present | [ ] |
| E8 | Transfer credential bundle to Secret Manager write path using acceptable channel only | Forbidden channels in Section C confirmed absent | [ ] |
| E9 | Confirm Secret Manager write response — field count only, no raw payload commit | Storage owner verifies response; redacted status only committed | [ ] |
| E10 | Confirm audit event emitted and logged | Audit event seq/digest verified | [ ] |
| E11 | Confirm no raw credential value appears in any log, terminal output, or committed file | Secondary reviewer confirms | [ ] |
| E12 | Mark handoff complete in evidence package — redacted form only | Evidence owner assembles redacted record | [ ] |

---

## F. Secret Manager Write Path Reference

The V5.15–V5.17 Secret Manager write path uses the `write_credential_bundle()` infrastructure. This section describes the structural write path design. No real project IDs, secret names, resource paths, or service account identities appear in this document.

### F.1 — Write infrastructure components

| Component | Role | V5.x ref |
|---|---|---|
| `GCPSecretManagerStore` | Backend store for write operations | V5.12 |
| `write_credential_bundle()` | Admin endpoint for credential write | V5.14 |
| `POST /credentials/google-ads` | HTTP endpoint for credential bundle write | V5.14 |
| Audit event on write | `credential_written` event with seq/digest | V5.16 |
| Version lifecycle policy | `DISABLE_PREVIOUS_WITH_GRACE_PERIOD` | V5.20 |
| Admin RBAC scope | `ADMIN` scope required for write path | V5.16 |
| Tenant isolation | Token-to-tenant binding required | V5.17 |
| Rate limiting | Sensitive route rate limit enforced | V5.17 |

### F.2 — Required pre-write validations

Before any real Secret Manager write, all of the following validators must confirm PASS:

| Validator | Module | Result required |
|---|---|---|
| Credential intake boundary | `openclaw/credential_intake.py` | PASS |
| Version lifecycle policy | `openclaw/version_lifecycle_policy.py` | PASS |
| OAuth authorization URL design | `openclaw/oauth_auth_url.py` | PASS |
| OAuth callback/token-exchange boundary | `openclaw/oauth_callback.py` | PASS |
| Credential handoff protocol review | This document | All sections confirmed |

### F.3 — Write path constraints

- Secret Manager write must use the pre-approved secret name only.
- Secret name must not be improvised during ceremony.
- Write must be performed in a single atomic call — no partial writes.
- If write fails, no retry is permitted without rollback owner confirmation.
- If write produces an unexpected response, halt immediately and invoke Section M.

---

## G. Audit Requirements for Handoff

All handoff actions must produce a verifiable audit trail. Audit records must be stored outside the repository in redacted form. No raw credential value, resource path, customer ID, project ID, or account email may appear in any audit record committed to the repository.

| Audit requirement | Required form | Confirmed |
|---|---|---|
| G1 — Pre-write audit event | `handoff_initiated` event logged with timestamp and operator label | [ ] |
| G2 — Write audit event | `credential_written` event with seq/digest (V5.16 format) logged | [ ] |
| G3 — Post-write verification audit | `write_verified` event confirming field-count-only status check | [ ] |
| G4 — Redaction confirmation | Audit reviewer confirms no raw value in any committed file | [ ] |
| G5 — Audit seq/digest chain | seq/digest chain unbroken from ceremony start through handoff complete | [ ] |
| G6 — Evidence package entry | Redacted handoff summary added to evidence package | [ ] |
| G7 — JSONL audit file | Audit JSONL file stored under V5.16 path; not committed to repository | [ ] |

**Audit gap of any kind is a stop condition.** Missing seq/digest, broken chain, or unverified write event halts the ceremony.

---

## H. Forbidden Content in Handoff Documentation

No handoff documentation committed to this repository may contain any of the following:

| Forbidden content | Examples (illustrative only — do not include in docs) |
|---|---|
| Real refresh token | Any value matching `1//...` pattern |
| Real access token | Any value matching `ya29....` pattern |
| Real auth code | Any value matching `4/0A...` pattern |
| Real client secret | Any string labeled or shaped as an OAuth client secret |
| Real client ID | Any string labeled as a Google OAuth client ID |
| Real developer token | Any string labeled or structured as a Google Ads developer token |
| Real customer ID | Any numeric string labeled or structured as a Google Ads customer ID |
| Real login customer ID | Any numeric string labeled as a Google Ads manager account ID |
| Real GCP resource path | Any string matching `projects/...`, `secrets/...`, `versions/...` pattern |
| Real service account email | Any email-like string associated with a GCP service account |
| Real project ID or number | Any string labeled as a GCP project ID or project number |
| Real secret name | Any string labeled as a Secret Manager secret name for a real project |

All placeholder values in this document use the form `<placeholder_label>`. No placeholder may contain a real value.

---

## I. Boundary Between OAuth Ceremony and Secret Manager Write

The credential handoff is the boundary between the OAuth ceremony (authorization URL → callback → token exchange) and the Secret Manager write path. This boundary must be treated as a hard control point.

| Boundary rule | Rationale |
|---|---|
| I1 — OAuth success does not imply write authorization | Token exchange PASS does not automatically permit Secret Manager write; separate step-gate required |
| I2 — Handoff must not begin until all prior ceremony gates are PASS | Sections E–H of the ceremony checklist must each be PASS before handoff sequence begins |
| I3 — Write must occur in the approved execution window only | Approval expiry must not have elapsed; confirm before write |
| I4 — Credential must not leave the acceptable channel set between exchange and write | No detour through forbidden channels at any intermediate step |
| I5 — Handoff failure does not retry automatically | Any write failure halts; rollback sequence initiates before any retry decision |
| I6 — Partial write is not a valid state | If write response is ambiguous, halt and invoke revocation path |

---

## J. Rollback and Revocation Integration

The handoff protocol integrates with the V5.20 rollback drill and the V5.15 revoke/delete endpoint. This section describes the integration points. No real resource paths, credential refs, or GCP identifiers appear in this document.

### J.1 — Pre-write rollback readiness confirmation

Before the handoff sequence begins, rollback readiness must be confirmed:

| Rollback readiness item | Confirmed |
|---|---|
| Revoke endpoint tested and PASS (`DELETE /credentials/google-ads`) | [ ] |
| Rollback owner is present and confirmed | [ ] |
| Revocation target (credential ref) is pre-approved in approval record | [ ] |
| V5.20 rollback drill PASS confirmed for this tenant | [ ] |
| Emergency revoke path (direct Secret Manager disable) known to rollback owner | [ ] |

### J.2 — Post-write revocation path

If a write succeeds but a credential leakage or ceremony failure is detected immediately after:

| Step | Action |
|---|---|
| R1 | Immediately halt all further ceremony steps |
| R2 | Notify emergency revoke owner (`<revoke_owner_label>`) |
| R3 | Initiate `DELETE /credentials/google-ads` via V5.15 endpoint under ADMIN scope |
| R4 | Confirm Secret Manager version is disabled — field count only, no raw response committed |
| R5 | Emit and verify `credential_revoked` audit event with seq/digest |
| R6 | Escalate to approval owner for post-incident review |
| R7 | Do not retry ceremony without new approval record |

---

## K. Participant Confirmation Requirements

All participants listed in Section B of the OAuth Ceremony Checklist must confirm readiness before the handoff sequence opens. Use redacted labels only.

| Participant | Confirmation required | Confirmed |
|---|---|---|
| Primary operator (`<operator_label>`) | Present; has read this protocol in full | [ ] |
| Secondary reviewer (`<reviewer_label>`) | Present; will confirm redaction at each handoff step | [ ] |
| Approval owner (`<approval_owner_label>`) | Approval record valid and not expired | [ ] |
| Credential handling owner (`<credential_handler_label>`) | Acceptable channel confirmed; no screen sharing active | [ ] |
| Secret storage owner (`<storage_owner_label>`) | Write path confirmed; audit logging active | [ ] |
| Rollback owner (`<rollback_owner_label>`) | Rollback path confirmed; revoke endpoint tested | [ ] |
| Emergency revoke owner (`<revoke_owner_label>`) | Emergency path confirmed; able to act immediately | [ ] |

---

## L. Stop Conditions

Any of the following conditions during handoff must cause immediate ceremony halt. No handoff step may continue after a stop condition is detected.

| # | Stop condition |
|---|---|
| L1 | Real credential value appears in chat, terminal, log, or committed file |
| L2 | Forbidden transmission channel used at any handoff step |
| L3 | Approval record expired or absent at time of handoff |
| L4 | Storage owner not present at write step |
| L5 | Secret Manager write produces unexpected response or error |
| L6 | Audit event seq/digest chain is broken |
| L7 | Partial write state detected — write response ambiguous |
| L8 | Rollback owner not reachable at time of write |
| L9 | Any handoff participant is not confirmed before handoff opens |
| L10 | Version lifecycle policy validator is not PASS before write |
| L11 | Pre-approved secret name not confirmed before write |
| L12 | Any OAuth callback validator (Phase 4) not PASS before handoff |
| L13 | Screen recording active during any credential handling step |
| L14 | Unexpected network error during write — do not retry without rollback owner |
| L15 | Evidence package incomplete at end of handoff |

**On stop:** halt all handoff steps; notify rollback owner and approval owner; initiate post-stop review before any restart.

---

## M. Revocation Path Summary

The revocation path for handoff-phase credentials:

1. Revoke via `DELETE /credentials/google-ads` (V5.15 endpoint, ADMIN scope required).
2. Confirm Secret Manager version disabled — status only, no raw resource path committed.
3. Emit `credential_revoked` audit event.
4. Verify audit seq/digest chain is intact after revocation.
5. Notify approval owner of revocation event.
6. Record revocation in evidence package (redacted form only).
7. Do not re-issue credentials without a new separate explicit operator approval.

**This path does not apply in Phase 5.** No Secret Manager write is performed in Phase 5. Revocation path is documented here for future authorized ceremony operators only.

---

## N. Protocol Compliance Statement

This document was produced in V5.21 Phase 5. It defines a secure credential handoff protocol for a future authorized Google Ads OAuth ceremony onboarding event.

**This document does not authorize real credential handoff.**
**This document does not perform a Secret Manager write.**
**This document does not execute OAuth.**
**This document does not call Google Ads API.**
**This document does not call GCP or Secret Manager.**
**No real credential values appear in this document.**
**`GOOGLE_ADS_LIVE_ENABLED` remains false.**

All placeholders in this document use the form `<label_redacted>`. Any future ceremony operator who uses this document must replace placeholder labels with real confirmed values in an out-of-repository approval record only — never in any committed file.

**Phase 5 implementation:** `docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md` created. Documentation-only. No Python module. No real credentials. No Secret Manager write. No OAuth. No GCP. No Google Ads API. No network calls. `GOOGLE_ADS_LIVE_ENABLED` remains false.

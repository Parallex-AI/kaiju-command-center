# Release Notes — v5.18.0-beta

**Branch:** `v5.18-live-gcp-fake-validation`
**Base:** `v5.17.0-beta` / master after `34bf81f`
**Tag candidate:** `v5.18.0-beta`
**Status:** Complete — all phases A–N PASS · ready for merge and tag

---

## Release Summary

v5.18.0-beta is the live GCP fake-secret credential lifecycle validation release for OpenClaw. Building on V5.17's operator runbook, per-tenant isolation, rate limiting, and audit locking, V5.18 executes the controlled live GCP Secret Manager validation that V5.17 planned but did not run. Fourteen phases (A–N) confirm the full HTTP → `admin.py` → `GCPSecretManagerStore` chain: write, metadata/status read, structural validate, rotate, delete/revoke cleanup, post-delete status, audit verification, and final redaction review.

No code changes were made. No real Google Ads credentials were used. No Google Ads live API calls were made. `GOOGLE_ADS_LIVE_ENABLED=false` throughout. No production deployment was performed. No IAM changes. No billing changes. No APIs enabled. No fixed-cost infrastructure. The rehearsal secret was created and deleted within the same session. Cleanup is complete.

---

## Highlights

- **Phases A–N all PASS** — full HTTP → `server.py` → `admin.py` → `GCPSecretManagerStore` lifecycle confirmed with fake values only
- **Fake credential write confirmed** — `put_secret_bundle()` writes to live GCP Secret Manager; `get_secret_status()` confirms all 4 fields present
- **Structural validate confirmed** — `structurally_complete=true`, `live_api_tested=false`, `get_secret_bundle()` never called
- **Rotation confirmed** — new fake version written; structurally complete after rotate; prior version retained until delete
- **Delete/revoke confirmed** — `delete_secret_bundle()` removes secret and all versions; credential marked REVOKED; genuine delete (no `secret_already_absent` warning)
- **Audit chain confirmed** — 15 events across 3 audit files; all expected operations present; seq/digest chain valid; forbidden fields absent
- **Cleanup confirmed** — rehearsal secret deleted; credential REVOKED; temp files outside repo; delete gate restored; results doc redacted and safety-grep clean
- **Final validation decision: PASS** — validated fake live GCP Secret Manager credential lifecycle only; real credential onboarding requires separate approval gate

---

## What's New

### Validation Execution (Phases A–N)

V5.18 is documentation-only. All work consists of executing the Phase A–N validation plan defined in `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_PLAN.md` and recording results in `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md`.

**Phase A — Local repo and tool preflight:** Branch, commit, working tree, Python deps (`fastapi`, `uvicorn`, `google.cloud.secretmanager`, `requests`), and smoke baselines (20/20 + 8/8) confirmed.

**Phase B — GCP CLI/auth preflight:** `gcloud` 579.0.0 installed, active account and project confirmed, ADC token available, Secret Manager CLI surface confirmed. IAM deferred — `gcloud projects test-iam-permissions` unsupported in SDK 579.0.0; validated implicitly by Phase F write and Phase J delete.

**Phase C — Secret Manager API availability:** API enabled, secret count 0, no existing rehearsal secret.

**Phases D–E — Local env setup and server readiness:** Fake tokens only, temp paths outside repo, `OPENCLAW_ADMIN_DELETE_ENABLED=false`, `GCP_SECRET_MANAGER_ENABLED=true`, `GOOGLE_ADS_LIVE_ENABLED=false`. Server startup: uvicorn complete, `/openclaw/health` ok=true, 9 routes registered.

**Phase F — Fake credential write (attempt 3 PASS):**
- Attempt 1 blocked: `GCP_PROJECT_ID` / `GOOGLE_CLOUD_PROJECT` not in server env; `GCPSecretManagerStore._check_ready()` blocked before any GCP network call.
- Attempt 2 blocked: ADC expired on first GCP network contact; `gcloud auth application-default login` required.
- Attempt 3 PASS: `POST /credentials/google-ads` → `put_secret_bundle()` → fake bundle written to GCP Secret Manager; `get_secret_status()` confirmed all 4 fields present (`developer_token`, `client_id`, `client_secret`, `refresh_token`); `credential_status.configured=true`.

**Phase G — Metadata/status read:** `GET /credentials/google-ads/status` → metadata only via `LocalFileCredentialReferenceStore`; no GCP call made; `credential_status.configured=true`; no payload access.

**Phase H — Structural validate (retry PASS after ADC re-expired):**
- Attempt 1 blocked: ADC re-expired after 3 days since Phase F; endpoint returned `ok=true`, `structurally_complete=false`, `live_api_tested=false` as designed; `_fetch_secret_bundle()` caught auth exception and returned `(None, error_code)`.
- Retry PASS: ADC refreshed; `POST /credentials/google-ads/validate` → `structurally_complete=true`, all 4 fields present, `live_api_tested=false`, `get_secret_bundle()` not called, no payload values returned.

**Phase I — Rotate (PASS):** `POST /credentials/google-ads/rotate` → `put_secret_bundle()` writes new fake version (V2) to GCP Secret Manager; `get_secret_status()` confirms all 4 fields present; `structurally_complete=true`; `get_secret_bundle()` not called; no payload values returned.

**Phase J — Delete/revoke (PASS):** `DELETE /credentials/google-ads` (with `OPENCLAW_ADMIN_DELETE_ENABLED=true` in server env only) → `delete_secret_bundle()` removes secret and all versions (V1 + V2); `credential_status.status=revoked`; `secret_status.configured=false`; `warnings=[]` confirms genuine delete.

**Phase K — Post-delete status (PASS):** `GET /credentials/google-ads/status` → `credential_status.status=revoked`; no GCP call; `LocalFileCredentialReferenceStore` only.

**Phase L — Full audit verification (PASS):** `verify_audit_file()` on all 3 audit files (2026-08-10, 2026-08-13, 2026-08-14); 15 total events; seq/digest chain valid; all 5 expected operations present; all 9 forbidden field names absent.

**Phase M — Cleanup verification (PASS):** Documentation-only; confirmed by Phase J/K/L evidence — no additional GCP command executed.

**Phase N — Final results redaction and documentation (PASS):** Safety grep clean (10 patterns); redaction checklist complete (16 items); consistency review PASS; final decision PASS.

---

## Confirmed Behaviors

| Behavior | Confirmed by |
|----------|-------------|
| `GCPSecretManagerStore` selected by factory when `GCP_SECRET_MANAGER_ENABLED=true` | Phase F |
| `put_secret_bundle()` creates secret and adds version; `AlreadyExists` handled safely | Phase F, I |
| `get_secret_status()` returns boolean field map only; no payload values returned | Phase F, H, I |
| Metadata GET uses `LocalFileCredentialReferenceStore` only; zero GCP calls | Phase G, K |
| Validate path: `get_secret_status()` only; `get_secret_bundle()` never called | Phase H |
| Validate response: `live_api_tested=false` always; no Google Ads API call | Phase H |
| ADC expiry causes `_fetch_secret_bundle()` to return `(None, error_code)`; endpoint returns `ok=true`, `structurally_complete=false` | Phase H attempt 1 |
| Rotate path: `put_secret_bundle()` then `get_secret_status()`; `get_secret_bundle()` never called | Phase I |
| Delete path: `delete_secret_bundle()` only; no payload read; marks REVOKED | Phase J |
| Delete idempotency: `secret_already_absent` warning absent confirms genuine delete (not already-absent hit) | Phase J |
| Audit events emitted for all 5 expected operations; seq/digest chain valid across date-boundary files | Phase L |
| Cleanup complete: secret deleted, credential REVOKED, no residual fake bundle | Phase J, K, L, M |

---

## Operational Notes

| Note | Detail |
|------|--------|
| ADC expiry | Application Default Credentials expire within ~1 hour; `gcloud auth application-default login` required before any phase that makes a live GCP call after a break |
| Project env var required | `GCP_PROJECT_ID` or `GOOGLE_CLOUD_PROJECT` must be in the server startup environment when `GCP_SECRET_MANAGER_ENABLED=true` |
| Delete gate | `OPENCLAW_ADMIN_DELETE_ENABLED=true` must be set only in the server startup env for the delete phase; never committed; remove by stopping the server |
| IAM implicit validation | Phase F write PASS and Phase J delete PASS serve as implicit IAM validation — write and delete roles confirmed sufficient |
| Audit files cross date boundaries | Audit files are named by date; seq resets per file; `verify_audit_file()` must be called separately on each file |

---

## Documents Added

| Document | Purpose |
|---|---|
| `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_PLAN.md` | Controlled fake-secret lifecycle validation plan (Phases A–N) |
| `docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md` | Filled operator results — all phases PASS; final decision PASS |
| `docs/V5_18_BRANCH_CLOSURE.md` | Branch closure documentation |
| `docs/RELEASE_NOTES_V5_18_0_BETA.md` | This document |

No code files were added or modified.

---

## Tests

| Suite | Result |
|-------|--------|
| `scripts/smoke_test_v5_credentials.sh` | **20/20 PASS** |
| `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **8/8 PASS** |
| V5.18 Phase L `verify_audit_file()` | **PASS** — 3 files, 15 events, seq/digest valid |
| V5.18 Phase N safety grep | **CLEAN** — 10 patterns, zero matches |

---

## Security Summary

| Property | Status |
|----------|--------|
| Fake values only — no real Google Ads credentials | Confirmed |
| Secret payload values never printed, recorded, or returned | Confirmed |
| `get_secret_bundle()` never called on any lifecycle path | Confirmed |
| Google Ads API never called | Confirmed |
| Audit events exclude all sensitive fields and identifiers | Confirmed |
| Redaction checklist: 16 items | PASS |
| Safety grep: 10 patterns | CLEAN |
| Rehearsal secret deleted; cleanup complete | Confirmed |
| Credential lifecycle final state: REVOKED | Confirmed |
| No `.env` committed | Confirmed |
| No credential JSON committed | Confirmed |
| `GOOGLE_ADS_LIVE_ENABLED=false` throughout | Confirmed |

---

## Deferred Work

- Real Google Ads OAuth credential onboarding (requires explicit operator approval, live credentials, `GOOGLE_ADS_LIVE_ENABLED=true`, separate pre-real-onboarding checklist in `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md`)
- Real Google Ads live API validation
- Cloud Run deployment (requires service account, IAM, billing authorization)
- GCP Secret Manager version destruction / disable policy on rotate
- Redis/Memorystore distributed rate limiting
- BigQuery audit replication / Cloud Storage audit archival
- KMS/HSM cryptographic audit signing
- OAuth2 / admin identity provider integration
- Production onboarding approval process

---

## Compatibility

No code changes. All V5.17 behavior is preserved exactly. No environment variable changes. No API changes. No configuration changes.

---

## Upgrade and Merge Notes

No database migrations. No API changes. No client-side changes required.

Merge recommendation:

```bash
git checkout master
git merge --no-ff v5.18-live-gcp-fake-validation
git tag v5.18.0-beta
```

---

## Related Documents

- [V5.18 Branch Closure](V5_18_BRANCH_CLOSURE.md)
- [V5.18 Live GCP Fake Validation Plan](V5_18_LIVE_GCP_FAKE_VALIDATION_PLAN.md)
- [V5.18 Live GCP Fake Validation Results](V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md)
- [V5.17 Branch Closure](V5_17_BRANCH_CLOSURE.md)
- [Release Notes — v5.17.0-beta](RELEASE_NOTES_V5_17_0_BETA.md)
- [Credential Lifecycle Runbook](CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

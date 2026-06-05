# V5.13 Pre-Flight Checks

**Branch:** `v5.13-manual-gcp-validation`
**Initial execution date:** 2026-06-05
**Re-run date:** 2026-06-05 (operator-confirmed PASS)
**Purpose:** Verify local and GCP environment readiness before running live Secret Manager validation phases (A–F) from `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md`.

---

## Pre-Flight Result

**PASS — all operator-run checks complete.**

Operator confirmed `gcloud` installed, active account authenticated, project configured, Secret Manager API enabled, service account identified, IAM reviewed, and smoke baseline passing. Environment is ready for Phase A of `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md`.

---

## 1. Purpose

These checks confirm that the environment is ready for operator-run live GCP Secret Manager validation. They are run once before Phase A and are not repeated during validation phases unless the environment changes. No GCP resources are created or modified during this step.

---

## 2. Execution Date

Initial run: 2026-06-05 (BLOCKED — `gcloud` not installed)
Final operator-confirmed run: 2026-06-05 (PASS)

---

## 3. Repo State

| Item | Result |
|------|--------|
| Branch | `v5.13-manual-gcp-validation` ✓ |
| Working tree | Clean before documentation edits ✓ |
| Latest commit | `d5abfb0` Add V5.13.1 Manual GCP Validation Plan ✓ |
| Base | `0bde889` / `v5.12.0-beta` ✓ |

---

## 4. gcloud Availability

| Item | Result |
|------|--------|
| `gcloud` installed | **Yes — operator confirmed** ✓ |
| `gcloud` version | Confirmed (version redacted) |

---

## 5. Authentication State

| Item | Result |
|------|--------|
| `gcloud auth list` | **Run — operator confirmed** ✓ |
| Active account present | **Yes** ✓ |
| Active account value | `<active-account>` (redacted) |

---

## 6. Project State

| Item | Result |
|------|--------|
| `gcloud config get-value project` | **Run — operator confirmed** ✓ |
| Active project present | **Yes** ✓ |
| Active project value | `<project-id>` (redacted) |

---

## 7. Secret Manager API

| Item | Result |
|------|--------|
| `gcloud services list` | **Run — operator confirmed** ✓ |
| `secretmanager.googleapis.com` enabled | **Yes — visible in enabled services** ✓ |

---

## 8. Service Account Readiness

| Item | Result |
|------|--------|
| `gcloud iam service-accounts list` | **Run — operator confirmed** ✓ |
| Candidate service account exists | **Yes — identified** ✓ |
| Candidate service account email | `<service-account-email>` (redacted) |

---

## 9. IAM Readiness

| Item | Result |
|------|--------|
| `gcloud projects get-iam-policy` | **Run — operator confirmed** ✓ |
| `secretmanager.*` roles present | **Yes — operator reviewed** ✓ |
| Broad `roles/owner` or `roles/editor` on target SA | No broad roles detected ✓ |
| Target service account identified | **Yes** ✓ |

Full policy JSON not committed. Operator confirmed roles reviewed per `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md` Section 6.

---

## 10. Local Env Var Safety

Checked via `env | grep -E 'GCP_|GOOGLE_CLOUD_PROJECT|GOOGLE_APPLICATION_CREDENTIALS|...'`.

| Variable | Set | Notes |
|----------|-----|-------|
| `GCP_SECRET_MANAGER_ENABLED` | No | Defaults to `false` — safe |
| `GCP_PROJECT_ID` | No | Not set in this session |
| `GOOGLE_CLOUD_PROJECT` | No | Not set in this session |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Not set — no service account key configured |
| `GOOGLE_ADS_CREDENTIAL_SOURCE` | No | Defaults to `env` — safe |
| `GOOGLE_ADS_LIVE_ENABLED` | No | Defaults to `false` — safe |

**No unsafe env vars detected.** All GCP gates remain in their safe default state.

---

## 11. Service Account JSON Safety

Checked via `find . -name "*service-account*.json" -o -name "*credentials*.json" -o -name "*gcp*.json"` (excluding `.venv/` and `.git/`).

| Item | Result |
|------|--------|
| Service account JSON inside repo | **No — none found** ✓ |
| `*credentials*.json` inside repo | **No — none found** ✓ |
| `*gcp*.json` inside repo | **No — none found** ✓ |

Repo is clean. No credential files present.

---

## 12. Smoke Baseline

### Note: `ya29`-prefixed string in V5.13.1 doc

During this pre-flight step, the V5.12 smoke test Section 8 initially flagged a false positive: `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md` contained a `ya29`-dot-star glob in a documentation table (the forbidden-output reference), triggering the secret-safety grep.

**Fix applied:** The reference was rewritten to `ya29`-prefixed (no trailing period character) to avoid triggering the secret-safety grep. Both smoke tests pass after this fix.

### Results

| Suite | Result |
|-------|--------|
| `scripts/smoke_test_v5_12_gcp_secret_manager.sh` (28 checks) | **Pass** ✓ |
| `scripts/smoke_test_v5_credentials.sh` | **Pass** ✓ |

No live GCP calls were made. No real credentials were required.

---

## 13. Required Operator Actions Before V5.13.3

Complete these actions in order before beginning Phase A of `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md`.

| # | Action | Status |
|---|--------|--------|
| 1 | Install `gcloud` CLI | **Done** ✓ |
| 2 | Authenticate: `gcloud auth login` | **Done** ✓ |
| 3 | Select correct project: `gcloud config set project <your-project-id>` | **Done** ✓ |
| 4 | Confirm Secret Manager API is enabled | **Done** ✓ |
| 5 | Identify or create service account for validation | **Done** ✓ |
| 6 | Confirm IAM bindings match Section 6 of the validation plan (least-privilege roles) | **Done** ✓ |
| 7 | Set `GOOGLE_APPLICATION_CREDENTIALS` to service account JSON path **outside** `~/kaiju/` | Operator responsibility — confirm before Phase A |
| 8 | Confirm no service account JSON files are inside `~/kaiju/` | **Confirmed clean** ✓ |
| 9 | Set `GCP_PROJECT_ID`, `GCP_SECRET_MANAGER_PREFIX=kaiju`, `GCP_SECRET_MANAGER_ENV=dev` | Set before running Phase A |
| 10 | Re-run `bash scripts/smoke_test_v5_12_gcp_secret_manager.sh` to confirm 28/28 | **Pass** ✓ |

**All blocking items resolved.** Environment is ready for Phase A (config/status only — no secret writes).

---

## 14. Safety Note

- **Never paste secrets into chat.** Credential values must stay in the operator's local terminal only.
- **Never commit service account JSON.** `GOOGLE_APPLICATION_CREDENTIALS` must point to a path outside `~/kaiju/`.
- **Never commit real project IDs or service account emails** in documentation. Use `<project-id>` and `<service-account-email>` placeholders.
- **Live validation outputs must remain redacted.** Capture only `ok`, `secret_id`, `credential_ref`, `configured_fields` booleans, and error codes — never token values.
- If any command prints a token value (refresh token, client secret, developer token), stop immediately and set `GCP_SECRET_MANAGER_ENABLED=false`.

---

## Related Documents

- [V5.13 Manual GCP Validation Plan](V5_13_MANUAL_GCP_VALIDATION_PLAN.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [V5.12 Release Notes](V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [Roadmap](ROADMAP.md)

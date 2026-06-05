# V5.13 Pre-Flight Checks

**Branch:** `v5.13-manual-gcp-validation`
**Execution date:** 2026-06-05
**Purpose:** Verify local and GCP environment readiness before running live Secret Manager validation phases (A–F) from `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md`.

---

## Pre-Flight Result

**BLOCKED — `gcloud` CLI not installed on this machine.**

Live GCP validation (Phases A–G) cannot proceed until `gcloud` is installed and authenticated. All local checks that do not require `gcloud` passed. See Section 13 (Required Operator Actions) for the complete unblock list.

---

## 1. Purpose

These checks confirm that the environment is ready for operator-run live GCP Secret Manager validation. They are run once before Phase A and are not repeated during validation phases unless the environment changes. No GCP resources are created or modified during this step.

---

## 2. Execution Date

2026-06-05

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
| `gcloud` installed | **No — command not found** |
| `gcloud` version | Not available |

**Action required:** Install the Google Cloud CLI before proceeding to Phase A. See Section 13.

---

## 5. Authentication State

| Item | Result |
|------|--------|
| `gcloud auth list` | Not run — `gcloud` not installed |
| Active account present | Unknown |
| Active account value | `<active-account>` (redacted) |

**Action required:** Run `gcloud auth login` after installing `gcloud`.

---

## 6. Project State

| Item | Result |
|------|--------|
| `gcloud config get-value project` | Not run — `gcloud` not installed |
| Active project present | Unknown |
| Active project value | `<project-id>` (redacted) |

**Action required:** Set correct GCP project with `gcloud config set project <your-project-id>` after installing `gcloud`.

---

## 7. Secret Manager API

| Item | Result |
|------|--------|
| `gcloud services list` | Not run — `gcloud` not installed |
| `secretmanager.googleapis.com` enabled | Unknown |

**Action required:** Confirm or enable Secret Manager API after `gcloud` is available.

---

## 8. Service Account Readiness

| Item | Result |
|------|--------|
| `gcloud iam service-accounts list` | Not run — `gcloud` not installed |
| Candidate service account exists | Unknown |
| Candidate service account email | `<service-account-email>` (redacted) |

**Action required:** Identify or create a suitable service account after `gcloud` is available. See Section 6 of `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md` for required IAM roles.

---

## 9. IAM Readiness

| Item | Result |
|------|--------|
| `gcloud projects get-iam-policy` | Not run — `gcloud` not installed |
| `secretmanager.*` roles present | Unknown |
| Broad `roles/owner` or `roles/editor` on target SA | Unknown |
| Target service account identified | Unknown |

**Action required:** Review project IAM policy after `gcloud` is available. Confirm least-privilege bindings per `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md` Section 6 before writing any secrets.

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

During this pre-flight step, the V5.12 smoke test Section 8 initially flagged a false positive: `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md` contained the literal string `` `ya29.*` `` in a documentation table (the forbidden-output reference). This triggered the `grep "ya29\."` secret-safety check.

**Fix applied:** The reference was rewritten to `ya29`-prefixed to avoid containing the literal dot pattern `ya29.` while preserving the meaning. Both smoke tests pass after this fix.

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
| 1 | Install `gcloud` CLI — see [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install) | **Required** |
| 2 | Authenticate: `gcloud auth login` | **Required** |
| 3 | Select correct project: `gcloud config set project <your-project-id>` | **Required** |
| 4 | Confirm Secret Manager API is enabled: `gcloud services list --enabled \| grep secretmanager` | **Required** |
| 5 | Identify or create service account for validation | **Required** |
| 6 | Confirm IAM bindings match Section 6 of the validation plan (least-privilege roles) | **Required** |
| 7 | Set `GOOGLE_APPLICATION_CREDENTIALS` to service account JSON path **outside** `~/kaiju/` | **Required** |
| 8 | Confirm no service account JSON files are inside `~/kaiju/` | Confirmed clean ✓ |
| 9 | Set `GCP_PROJECT_ID`, `GCP_SECRET_MANAGER_PREFIX=kaiju`, `GCP_SECRET_MANAGER_ENV=dev` | **Required** |
| 10 | Re-run `bash scripts/smoke_test_v5_12_gcp_secret_manager.sh` after `gcloud` install to confirm 28/28 | **Required** |

Once all 10 items are complete, the environment is ready for Phase A (config/status only — no secret writes).

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

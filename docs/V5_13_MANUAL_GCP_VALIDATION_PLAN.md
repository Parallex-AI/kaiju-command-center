# V5.13 Manual GCP Validation Plan

**Branch:** `v5.13-manual-gcp-validation`
**Base:** `v5.12.0-beta` / `master` at `0bde889`
**Status:** Complete — Phases A–F PASS. Results documented in `docs/V5_13_LIVE_GCP_VALIDATION_RESULTS.md`. No raw secrets committed. No live Google Ads API calls. No fixed-cost infrastructure.

---

## 1. Purpose

V5.13 validates the V5.12 GCP Secret Manager backend against a real GCP project using operator-controlled credentials. The goal is to confirm that `GCPSecretManagerStore` behaves correctly against live Secret Manager APIs: creating, reading, listing, and deleting secrets using the naming convention and payload format established in the V5.12 design.

All validation is performed manually by the operator using a local terminal with GCP credentials already configured outside the repo. No credentials are committed, pasted into docs, shared in chat, or stored in the repository at any point.

---

## 2. Current Baseline

| Item | Status |
|------|--------|
| V5.12 mocked smoke test (`scripts/smoke_test_v5_12_gcp_secret_manager.sh`) | **Passed** — 28/28 checks |
| `GCPSecretManagerStore` — read/status/write/delete/list | **Implemented** |
| `SecretStoreFactory` — backend selection via `GCP_SECRET_MANAGER_ENABLED` | **Implemented** |
| `compose_google_ads_credentials` factory wiring | **Implemented** |
| Cloud Run / IAM runbook (`docs/GCP_SECRET_MANAGER_RUNBOOK.md`) | **Exists** |
| Live GCP validation against real project | **Pending — this branch** |

The V5.12 implementation was fully validated using injected mock clients. This branch validates the same code paths against a real GCP Secret Manager instance.

---

## 3. Validation Principles

These rules apply throughout all phases of V5.13:

- **No real secrets in Git** — no token, key, or credential value is ever committed
- **No real secrets in chat** — credential values must not be pasted into any conversation
- **No real secrets in docs** — all documentation uses placeholders only
- **No service account JSON inside repo** — `GOOGLE_APPLICATION_CREDENTIALS` must point to a path outside the repo
- **No live Google Ads API call unless explicitly enabled** — `GOOGLE_ADS_LIVE_ENABLED=false` throughout all phases except Phase G
- **GCP validation starts with Google Ads live disabled** — Secret Manager access does not require Google Ads credentials
- **All output must be redacted** — any command output captured in docs uses `[REDACTED]` for token values; only boolean fields, `ok`, `secret_id`, `credential_ref`, and `configured_fields` are safe to include

---

## 4. Required Operator Inputs

The following values must be set by the operator in their local terminal before beginning validation. These are placeholders — substitute your real values at runtime only, never commit them.

```bash
# Operator configures these in their local terminal only:
GCP_PROJECT_ID=<your-project-id>
GCP_REGION=<your-region>                        # e.g. us-central1
CLOUD_RUN_SERVICE=<your-cloud-run-service>      # e.g. kaiju-openclaw
SERVICE_ACCOUNT=<your-service-account>          # e.g. kaiju-openclaw@<project>.iam.gserviceaccount.com
GCP_SECRET_MANAGER_PREFIX=kaiju
GCP_SECRET_MANAGER_ENV=dev                      # or: staging | prod
```

No real values for these variables appear anywhere in this document or in the repository.

---

## 5. Pre-Flight Checklist

Complete all items before beginning Phase A.

### Environment
- [ ] Currently on branch `v5.13-manual-gcp-validation`
- [ ] Working tree is clean (`git status` shows nothing to commit)
- [ ] `gcloud` CLI is installed and on PATH
- [ ] `gcloud auth login` has been completed in the operator's local session
- [ ] `gcloud config get-value project` returns the intended GCP project — not a personal or shared project
- [ ] `gcloud services list --enabled | grep secretmanager` confirms Secret Manager API is enabled

### GCP access
- [ ] Service account exists and its email is known
- [ ] IAM roles have been reviewed (see Section 6)
- [ ] `GOOGLE_APPLICATION_CREDENTIALS` points to a service account JSON **outside the repo**
- [ ] No service account JSON file exists inside `~/kaiju/` or any subdirectory

### Local baseline
- [ ] `bash scripts/smoke_test_v5_12_gcp_secret_manager.sh` passes with 28/28 checks
- [ ] `bash scripts/smoke_test_v5_credentials.sh` passes
- [ ] Docker validation is optional (already performed in V5.12.9)

---

## 6. IAM Validation Plan

Before writing or reading any secrets, confirm the service account has exactly the permissions needed and no more.

### Required permissions

| Permission | Purpose |
|------------|---------|
| `secretmanager.secrets.create` | Phase B — create test secret |
| `secretmanager.secrets.get` | Phase C — get secret metadata |
| `secretmanager.versions.add` | Phase B — add secret version |
| `secretmanager.versions.access` | Phase C — read secret version payload |
| `secretmanager.secrets.list` | Phase D — list secrets by prefix |
| `secretmanager.secrets.delete` | Phase E — delete test secret (only if delete validation is intended) |

### Recommended roles

| Role | Scope | Notes |
|------|-------|-------|
| `roles/secretmanager.secretAccessor` | Project or prefix condition | Read access to secret versions |
| `roles/secretmanager.secretVersionAdder` | Project or prefix condition | Add new versions only |
| `roles/secretmanager.secretCreator` | Project or prefix condition | Create secrets (not auto-granted by accessor) |
| `roles/secretmanager.secretDeleter` | Project or prefix condition | Only if Phase E is intended |

### Conditions

Where possible, bind roles with a resource condition scoped to the `kaiju-<env>-` prefix:

```
resource.name.startsWith("projects/<PROJECT_NUMBER>/secrets/kaiju-<env>-")
```

This prevents the service account from accessing secrets outside the intended prefix.

### Avoid

- `roles/owner` — too broad
- `roles/editor` — too broad
- Bare project-level `roles/secretmanager.admin` unless this is a temporary manual validation and will be narrowed afterward

---

## 7. Manual Command Plan

These commands are listed as a reference plan. **Do not run them yet** — they are executed during Phase A by the operator in their local terminal. No output from these commands is committed to the repo.

```bash
# Confirm active project
gcloud config get-value project

# Confirm Secret Manager API is enabled
gcloud services list --enabled | grep secretmanager

# List service accounts
gcloud iam service-accounts list

# Review project-level IAM policy
gcloud projects get-iam-policy <PROJECT_ID>

# Review service account IAM bindings on a specific secret (after Phase B)
gcloud secrets get-iam-policy <SECRET_ID> --project=<PROJECT_ID>
```

All `<PLACEHOLDER>` values must be substituted by the operator at runtime. No real project ID, secret ID, or service account email appears in this document.

---

## 8. Environment Variable Plan

Set these in the operator's local terminal before beginning Phase A. Do not export them in any script or commit them to any file.

```bash
# Master GCP gate — set to true only for live validation phases
export GCP_SECRET_MANAGER_ENABLED=true

# GCP project — substitute your real project ID at runtime only
export GCP_PROJECT_ID="<your-project-id>"

# Secret naming config
export GCP_SECRET_MANAGER_PREFIX="kaiju"
export GCP_SECRET_MANAGER_ENV="dev"           # use dev or a dedicated validation env

# Credential source — use provider path for Phase F
export GOOGLE_ADS_CREDENTIAL_SOURCE="provider"

# Keep Google Ads live calls disabled unless Phase G
export GOOGLE_ADS_LIVE_ENABLED=false

# Service account credentials — path must be OUTSIDE the repo
export GOOGLE_APPLICATION_CREDENTIALS="/path/outside/repo/service-account.json"
```

After validation, restore:

```bash
export GCP_SECRET_MANAGER_ENABLED=false
unset GCP_PROJECT_ID
unset GOOGLE_APPLICATION_CREDENTIALS
export GOOGLE_ADS_CREDENTIAL_SOURCE=env
export GOOGLE_ADS_LIVE_ENABLED=false
```

---

## 9. Validation Phases

### Phase A — Config and Status Only

**Goal:** Confirm the Python module reads env vars and reports correct config without making any GCP API calls.

**Steps:**
1. Set env vars per Section 8 (except leave `GCP_SECRET_MANAGER_ENABLED=false` for this phase)
2. Run the status helper from `agents/ads-agent/`:
   ```bash
   cd ~/kaiju/agents/ads-agent
   python3 -c "
   from credentials import gcp_secret_manager_status
   import json; print(json.dumps(gcp_secret_manager_status(), indent=2))
   "
   ```
3. Confirm: `enabled: false`, `project_id_configured: true`, no network call made

**Allowed output:** `enabled`, `project_id_configured`, `prefix`, `env`, `location` — all config-level fields. No secret values.

---

### Phase B — Write Test Secret Bundle

**Goal:** Create a real secret in GCP Secret Manager using `GCPSecretManagerStore.put_secret_bundle()`.

**Steps:**
1. Set `GCP_SECRET_MANAGER_ENABLED=true` and all env vars per Section 8
2. Use controlled test credential values — not real Google Ads credentials — or real credentials stored outside the repo and never printed:
   ```bash
   cd ~/kaiju/agents/ads-agent
   python3 -c "
   import os
   os.environ['GCP_SECRET_MANAGER_ENABLED'] = 'true'
   from credentials import create_secret_store
   store = create_secret_store()
   result = store.put_secret_bundle(
       credential_ref='cred_validation_test_001',
       integration_type='google_ads',
       bundle={
           'developer_token': '<test-value>',
           'client_id': '<test-value>',
           'client_secret': '<test-value>',
           'refresh_token': '<test-value>',
       }
   )
   print('result:', result)
   "
   ```
3. Capture: `result` (should be `'created'` or `'updated'`)
4. Verify in GCP console or via `gcloud secrets list` that the secret ID `kaiju-dev-google_ads-cred_validation_test_001` was created

**Allowed output:** `result` enum value only. No credential values printed.

---

### Phase C — Read and Status Test

**Goal:** Read the secret version created in Phase B and confirm the status response is correctly redacted.

**Steps:**
1. Env vars as Phase B
2. Run:
   ```bash
   cd ~/kaiju/agents/ads-agent
   python3 -c "
   import os, json
   os.environ['GCP_SECRET_MANAGER_ENABLED'] = 'true'
   from credentials import create_secret_store
   store = create_secret_store()
   status = store.get_secret_status(
       credential_ref='cred_validation_test_001',
       integration_type='google_ads'
   )
   print(json.dumps(status, indent=2))
   "
   ```
3. Confirm: `configured_fields` contains `true`/`false` booleans only — no raw values

**Allowed output:** `credential_ref`, `integration_type`, `configured_fields` (boolean list), `metadata`, `backend`, `enabled`. No token values.

---

### Phase D — List Test

**Goal:** List secrets filtered by the `kaiju-dev-` prefix and confirm no payload access occurs.

**Steps:**
1. Env vars as Phase B
2. Run:
   ```bash
   cd ~/kaiju/agents/ads-agent
   python3 -c "
   import os, json
   os.environ['GCP_SECRET_MANAGER_ENABLED'] = 'true'
   from credentials import create_secret_store
   store = create_secret_store()
   records = store.list_secret_records(integration_type='google_ads')
   for r in records:
       print({'credential_ref': r.credential_ref, 'integration_type': r.integration_type, 'listed': r.metadata.get('listed')})
   "
   ```
3. Confirm: `cred_validation_test_001` appears in results; `configured_fields` is empty list (list does not access payload)

**Allowed output:** `credential_ref`, `integration_type`, `listed: True`. No secret values.

---

### Phase E — Delete Test

**Goal:** Delete the test secret created in Phase B and confirm it is gone.

**Steps:**
1. Env vars as Phase B
2. Run:
   ```bash
   cd ~/kaiju/agents/ads-agent
   python3 -c "
   import os
   os.environ['GCP_SECRET_MANAGER_ENABLED'] = 'true'
   from credentials import create_secret_store
   store = create_secret_store()
   deleted = store.delete_secret_bundle(
       credential_ref='cred_validation_test_001',
       integration_type='google_ads'
   )
   print('deleted:', deleted)
   "
   ```
3. Confirm: `deleted: True`
4. Re-run Phase C status check — confirm `NotFound` is returned (result: `error_code: not_found` or equivalent)

**Allowed output:** `deleted: True/False`, error code. No credential values.

---

### Phase F — Provider Composition

**Goal:** Confirm `compose_google_ads_credentials()` uses the `GCPSecretManagerStore` backend when configured, and returns a redacted status view only.

**Note:** For this phase, the test secret from Phase B should exist (re-create if Phase E was run, or use a fresh `credential_ref`).

**Steps:**
1. Set `GOOGLE_ADS_CREDENTIAL_SOURCE=provider` and `GOOGLE_ADS_LIVE_ENABLED=false`
2. Run:
   ```bash
   cd ~/kaiju/agents/ads-agent
   python3 -c "
   import os, json
   os.environ['GCP_SECRET_MANAGER_ENABLED'] = 'true'
   os.environ['GOOGLE_ADS_CREDENTIAL_SOURCE'] = 'provider'
   os.environ['GOOGLE_ADS_LIVE_ENABLED'] = 'false'
   from credentials.google_ads_provider import compose_google_ads_credentials
   result = compose_google_ads_credentials(tenant_id='cred_validation_test_001')
   print('ok:', result.ok)
   print('redacted_status:', result.redacted_status())
   "
   ```
3. Confirm: `ok: True`, status shows `configured_fields` booleans only, no raw credential values in output

**Allowed output:** `ok`, `redacted_status` fields — `configured_fields`, `backend`, `enabled`. No token values.

---

### Phase G — Optional: Google Ads Live Validation

**Goal:** Confirm the full credential chain from Secret Manager to a real Google Ads API call.

**Only proceed if:**
- Real Google Ads credentials are available and stored outside the repo
- The test GCP project and service account are approved for Google Ads API access
- The operator explicitly chooses to proceed

**Steps:**
1. Re-create test secret (Phase B) with **real** credentials (values never printed or committed)
2. Set `GOOGLE_ADS_LIVE_ENABLED=true`
3. Run the minimal validation — a `get_campaign_details` or equivalent call that returns metadata only
4. Capture only: `ok: True`, `data_source: google_ads`, non-sensitive campaign name or count
5. Immediately set `GOOGLE_ADS_LIVE_ENABLED=false` after

**Allowed output:** `ok`, `data_source: google_ads`, non-PII campaign metadata. No token or key values.

---

## 10. Safety Stop Conditions

**Stop all validation immediately and set `GCP_SECRET_MANAGER_ENABLED=false`** if any of the following occur:

| Condition | Action |
|-----------|--------|
| A command prints a refresh token value | Stop, clear terminal, set `GCP_SECRET_MANAGER_ENABLED=false` |
| A command prints `client_secret` value | Stop, clear terminal |
| A command prints `developer_token` value | Stop, clear terminal |
| `gcloud config get-value project` returns wrong project | Stop, switch to correct project before continuing |
| Service account has `roles/owner` or `roles/editor` unexpectedly | Stop, review IAM before proceeding |
| `git status` shows modified or untracked secret-related files | Stop, investigate before continuing |
| Any `*.json` file appears inside the repo directory | Stop, confirm it is not a service account key |
| Any validation output would be recorded containing raw credential values | Do not record — use `[REDACTED]` placeholder only |

---

## 11. Expected Output Rules

### Allowed in docs, logs, and captured output

- `ok: true` / `ok: false`
- `secret_id` (the GCP resource name, without embedded token values)
- `credential_ref` (the opaque hash/reference, not a token value)
- `configured_fields: ["developer_token", "client_id", "client_secret", "refresh_token"]` (field names, not values)
- `error_code` strings (e.g. `not_found`, `permission_denied`)
- `backend: gcp_secret_manager`
- `enabled: true/false`
- `listed: true`
- `deleted: true/false`

### Forbidden in docs, logs, and captured output

| Field | Reason |
|-------|--------|
| `developer_token` value | Google Ads API credential |
| `client_secret` value | OAuth2 client secret |
| `refresh_token` value | OAuth2 long-lived token |
| `access_token` (OAuth2 short-lived token, `ya29`-prefixed) | OAuth2 short-lived token |
| Service account private key | GCP authentication |
| OAuth authorization code | One-time exchange token |

---

## 12. Manual Validation Result Template

Fill this table during operator-run validation. Use `[REDACTED]` for any sensitive output fields.

| Phase | Status | Date | Notes | Evidence / Redacted Output |
|-------|--------|------|-------|---------------------------|
| A — Config/status | Pending | | | |
| B — Write test secret | Pending | | | |
| C — Read/status | Pending | | | |
| D — List | Pending | | | |
| E — Delete | Pending | | | |
| F — Provider composition | Pending | | | |
| G — Google Ads live (optional) | Pending | | | |

**Overall result:** Pending

---

## 13. Rollback Plan

If any phase produces unexpected results, roll back immediately:

```bash
# Step 1 — disable GCP backend
export GCP_SECRET_MANAGER_ENABLED=false
unset GCP_PROJECT_ID
unset GOOGLE_APPLICATION_CREDENTIALS

# Step 2 — revert credential source
export GOOGLE_ADS_CREDENTIAL_SOURCE=env
export GOOGLE_ADS_LIVE_ENABLED=false

# Step 3 — delete only test secrets created for validation
# (run manually in GCP console or via gcloud — do not automate)
# gcloud secrets delete kaiju-dev-google_ads-cred_validation_test_001 --project=<PROJECT_ID>

# Step 4 — if Cloud Run env vars were modified, revert via GCP console or:
# gcloud run services update <SERVICE> --update-env-vars GCP_SECRET_MANAGER_ENABLED=false
```

The in-memory fallback is always available — setting `GCP_SECRET_MANAGER_ENABLED=false` immediately returns the system to its V5.12 default safe state with no further action required.

---

## 14. Acceptance Criteria

- [x] Plan document exists at `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md`
- [x] No GCP commands executed
- [x] No real GCP project ID, service account, or credential values committed
- [x] No code changes — runtime source files untouched
- [x] No dependencies added
- [x] Roadmap updated with V5.13 section
- [x] Pre-flight checks executed and documented in `docs/V5_13_PREFLIGHT_CHECKS.md` (V5.13.2)
- [x] No resources created, no secrets touched during pre-flight
- [x] Operator has installed `gcloud` and authenticated — confirmed PASS in `docs/V5_13_PREFLIGHT_CHECKS.md`
- [x] Operator has confirmed IAM bindings (Section 6) — confirmed PASS in `docs/V5_13_PREFLIGHT_CHECKS.md`
- [ ] Phases A–F completed and result table filled — tracked in `docs/V5_13_LIVE_GCP_VALIDATION_RESULTS.md` (V5.13.3)

---

## Related Documents

- [V5.13 Pre-Flight Checks](V5_13_PREFLIGHT_CHECKS.md)
- [V5.13 Live GCP Validation Results](V5_13_LIVE_GCP_VALIDATION_RESULTS.md)
- [V5.12 Design Document](V5_12_GCP_SECRET_MANAGER_DESIGN.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [V5.12 Release Notes](V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [Roadmap](ROADMAP.md)

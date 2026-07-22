# V5.13 Live GCP Validation Results

**Branch:** `v5.13-manual-gcp-validation`
**Date:** 2026-06-08
**Status:** In progress — Phase A PASS, Phase B PASS, Phase C PASS, Phase D PASS, Phases E–F pending operator execution

---

## 1. Purpose

Document the operator-run live validation of the V5.12 GCP Secret Manager backend against a real GCP project. All sensitive values are redacted. Only status booleans, `secret_id`, `credential_ref`, `configured_fields` field names, `backend`, and error codes may be recorded here.

This document is the live counterpart to `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md`, which contains the full phase-by-phase instructions. Results from each phase are recorded here after the operator runs them locally.

---

## 2. Safety Rules

These rules apply to every entry in this document:

- **No real secrets in docs** — credential values, tokens, keys must never appear here
- **No real secrets in Git** — nothing sensitive committed
- **No real secrets in chat** — do not paste token values into the conversation
- **No service account JSON in repo** — `GOOGLE_APPLICATION_CREDENTIALS` points outside `~/kaiju/`
- **No live Google Ads API calls** — `GOOGLE_ADS_LIVE_ENABLED=false` throughout Phases A–F
- **All output must be redacted** — only the fields listed in Section 1 above are safe to record
- **Stop immediately** if any command prints a refresh token, client secret, developer token, or access token value

---

## 3. Operator Environment

All sensitive values are placeholders. No real values are committed.

| Variable | Value |
|----------|-------|
| `GCP_PROJECT_ID` | `<project-id>` (redacted) |
| `GCP_SECRET_MANAGER_PREFIX` | `kaiju` |
| `GCP_SECRET_MANAGER_ENV` | `dev` |
| `GCP_SECRET_MANAGER_ENABLED` | `true` (during validation phases only) |
| `GOOGLE_ADS_CREDENTIAL_SOURCE` | `provider` |
| `GOOGLE_ADS_LIVE_ENABLED` | `false` |
| `GOOGLE_APPLICATION_CREDENTIALS` | `<path-outside-repo>` (redacted) |
| Active GCP account | `<active-account>` (redacted) |
| Service account | `<service-account-email>` (redacted) |

---

## 4. Phase A — Config/Status Only

**Goal:** Confirm `GCPSecretManagerStore` initialises correctly with live env vars. No secret read or write.

**Operator runs locally (no output to paste here):**

```bash
cd ~/kaiju/agents/ads-agent

export GCP_SECRET_MANAGER_ENABLED=true
export GCP_PROJECT_ID="<project-id>"
export GCP_SECRET_MANAGER_PREFIX="kaiju"
export GCP_SECRET_MANAGER_ENV="dev"
export GOOGLE_ADS_CREDENTIAL_SOURCE="provider"
export GOOGLE_ADS_LIVE_ENABLED=false
export GOOGLE_APPLICATION_CREDENTIALS="<path-outside-repo>"

~/kaiju/.venv/bin/python3 -c "
import os, json
from credentials import gcp_secret_manager_status, secret_store_factory_status, create_secret_store

status = gcp_secret_manager_status()
factory = secret_store_factory_status()
store = create_secret_store()

print('gcp_status:', json.dumps({k: v for k, v in status.items() if k != 'project_id'}, indent=2))
print('factory_backend:', factory['selected_backend'])
print('store_type:', type(store).__name__)
"
```

**Expected (safe to record):**

- `enabled: true`
- `project_id_configured: true`
- `selected_backend: gcp_secret_manager`
- `store_type: GCPSecretManagerStore`
- No secret values printed

**Result:** PASS

| Field | Value |
|-------|-------|
| `enabled` | `true` |
| `project_id_configured` | `true` |
| `selected_backend` | `gcp_secret_manager` |
| `created_store_class` | `GCPSecretManagerStore` |
| `google_ads_live_enabled` | `false` |
| `error_code` | `none` |

**Notes:** Config/status loaded cleanly. No secrets written, read, printed, or deleted.

> **Caveat:** Phase A was run with placeholder values for `GCP_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`. This is acceptable for Phase A because it performs local config/factory validation only and makes no live GCP API calls. Before Phase B, the operator must replace both placeholders with real local values in the terminal only — do not paste real values into chat or docs.

---

## 5. Phase B — Write Test Secret Bundle

**Goal:** Create a real secret in GCP Secret Manager using `put_secret_bundle()`.

**Operator runs locally:**

```bash
cd ~/kaiju/agents/ads-agent

~/kaiju/.venv/bin/python3 -c "
import os, json
os.environ['GCP_SECRET_MANAGER_ENABLED'] = 'true'
from credentials import create_secret_store

store = create_secret_store()
result = store.put_secret_bundle(
    credential_ref='cred_google_ads_manual_validation_v5130',
    integration_type='google_ads',
    bundle={
        'developer_token': '<operator-test-value>',
        'client_id': '<operator-test-value>',
        'client_secret': '<operator-test-value>',
        'refresh_token': '<operator-test-value>',
    }
)
print('write_result:', result)
print('credential_ref: cred_google_ads_manual_validation_v5130')
print('secret_id: kaiju-dev-google_ads-cred_google_ads_manual_validation_v5130')
"
```

**Important:** Substitute `<operator-test-value>` with controlled test values in the operator's local terminal only. Do not paste values here.

**Expected (safe to record):**

- `write_result: created` or `write_result: updated`
- `credential_ref: cred_google_ads_manual_validation_v5130`
- `secret_id: kaiju-dev-google_ads-cred_google_ads_manual_validation_v5130`
- No credential values printed

**Result:** PASS

| Field | Value |
|-------|-------|
| `ok` | `true` |
| `credential_ref` | `<redacted>` |
| `secret_id` | `<redacted>` |
| `backend` | `gcp_secret_manager` |
| `configured_fields` | `client_id, client_secret, developer_token, refresh_token` |
| `google_ads_live_enabled` | `false` |
| `error_code` | `none` |

**Notes:** Test secret bundle written to GCP Secret Manager using fake validation values only. No real Google Ads credentials used. No secret payload printed. No fixed-cost infrastructure created. SDK (`google-cloud-secret-manager`) installed into project venv; package was already declared in `requirements.txt:4`.

---

## 6. Phase C — Read/Status Test

**Goal:** Read the secret created in Phase B and confirm the status response is redacted.

**Operator runs locally:**

```bash
cd ~/kaiju/agents/ads-agent

~/kaiju/.venv/bin/python3 -c "
import os, json
os.environ['GCP_SECRET_MANAGER_ENABLED'] = 'true'
from credentials import create_secret_store

store = create_secret_store()
status = store.get_secret_status(
    credential_ref='cred_google_ads_manual_validation_v5130',
    integration_type='google_ads'
)
# Print only safe fields — never print bundle
safe = {k: v for k, v in status.items() if k not in ('bundle', 'raw')}
print(json.dumps(safe, indent=2))
"
```

**Expected (safe to record):**

- `configured: true`
- `configured_fields` — list of field names, all `true`
- `backend: gcp_secret_manager`
- No raw token values in output

**Result:** PASS

| Field | Value |
|-------|-------|
| `configured` | `true` |
| `available` | `true` |
| `credential_ref` | `<redacted>` |
| `backend` | `gcp_secret_manager` |
| `configured_fields` | `developer_token, client_id, client_secret, refresh_token` (all `true`) |
| `google_ads_live_enabled` | `false` |
| `payload_printed` | `false` |
| `error_code` | `none` |

**Notes:** Secret status verified through safe metadata/status only. `list_secret_records()` located the Phase B credential_ref without accessing payload. `get_secret_status()` confirmed all four fields configured and available. No raw credential values printed. No Google Ads live call. No fixed-cost infrastructure created.

---

## 7. Phase D — List Test

**Goal:** List secrets by prefix/env and confirm the test secret appears. No payload access.

**Operator runs locally:**

```bash
cd ~/kaiju/agents/ads-agent

~/kaiju/.venv/bin/python3 -c "
import os
os.environ['GCP_SECRET_MANAGER_ENABLED'] = 'true'
from credentials import create_secret_store

store = create_secret_store()
records = store.list_secret_records(integration_type='google_ads')
for r in records:
    print({
        'credential_ref': r.credential_ref,
        'integration_type': r.integration_type,
        'configured_fields': r.configured_fields,
        'listed': r.metadata.get('listed'),
    })
print('total:', len(records))
"
```

**Expected (safe to record):**

- `cred_google_ads_manual_validation_v5130` appears in list
- `configured_fields: []` (list operation does not access payload)
- `listed: True`
- `total` count — safe integer
- No secret values printed

**Result:** PASS

| Field | Value |
|-------|-------|
| `listed` | `true` |
| `credential_ref_found` | `true` |
| `manual_validation_records_count` | `1` |
| `payload_accessed` | `false` |
| `backend` | `gcp_secret_manager` |
| `configured_fields` | `[]` (expected — descriptor-only listing, no payload access) |
| `google_ads_live_enabled` | `false` |
| `error_code` | `none` |

**Notes:** Secret descriptors listed safely. Phase B manual validation record found. `configured_fields=[]` is expected because `list_secret_records` calls `list_secrets` (GCP descriptor API only) and never calls `access_secret_version`. No secret payload accessed or printed. No actual `credential_ref` or `secret_id` printed. No Google Ads live call. No fixed-cost infrastructure created.

---

## 8. Phase E — Delete Test

**Goal:** Delete the test secret and confirm it is gone.

**Operator runs locally:**

```bash
cd ~/kaiju/agents/ads-agent

~/kaiju/.venv/bin/python3 -c "
import os, json
os.environ['GCP_SECRET_MANAGER_ENABLED'] = 'true'
from credentials import create_secret_store

store = create_secret_store()

# Delete
deleted = store.delete_secret_bundle(
    credential_ref='cred_google_ads_manual_validation_v5130',
    integration_type='google_ads'
)
print('deleted:', deleted)

# Verify gone
status = store.get_secret_status(
    credential_ref='cred_google_ads_manual_validation_v5130',
    integration_type='google_ads'
)
safe = {k: v for k, v in status.items() if k not in ('bundle', 'raw')}
print('post_delete_status:', json.dumps(safe, indent=2))
"
```

**Expected (safe to record):**

- `deleted: True`
- Post-delete status: `configured: false` or error code `not_found` / `gcp_secret_not_found`
- No secret values printed

**Result:** Pending

---

## 9. Phase F — Provider Composition Test

**Goal:** Confirm `compose_google_ads_credentials()` uses `GCPSecretManagerStore` and returns a correctly redacted result with `GOOGLE_ADS_LIVE_ENABLED=false`.

**Note:** The test secret must exist for this phase. If Phase E was run first, recreate it with Phase B before running Phase F.

**Operator runs locally:**

```bash
cd ~/kaiju/agents/ads-agent

~/kaiju/.venv/bin/python3 -c "
import os, json
os.environ['GCP_SECRET_MANAGER_ENABLED'] = 'true'
os.environ['GOOGLE_ADS_CREDENTIAL_SOURCE'] = 'provider'
os.environ['GOOGLE_ADS_LIVE_ENABLED'] = 'false'

from credentials.google_ads_provider import compose_google_ads_credentials

result = compose_google_ads_credentials(
    tenant_id='cred_google_ads_manual_validation_v5130'
)
print('ok:', result.ok)
print('redacted_status:', json.dumps(result.redacted_status(), indent=2))
"
```

**Expected (safe to record):**

- `ok: True`
- `configured_fields` all `true` in redacted status
- `backend: gcp_secret_manager`
- `google_ads_live_enabled: false` — no Google Ads API call made
- No raw credential values in output

**Result:** Pending

---

## 10. Result Table

| Phase | Status | Redacted Evidence | Notes |
|-------|--------|-------------------|-------|
| A — Config/status | **PASS** | enabled=true, project_id_configured=true, selected_backend=gcp_secret_manager, created_store_class=GCPSecretManagerStore, google_ads_live_enabled=false, error_code=none | Placeholder env vars used; acceptable for config-only phase. Real values required before Phase B. |
| B — Write test secret | **PASS** | ok=true, credential_ref=&lt;redacted&gt;, secret_id=&lt;redacted&gt;, backend=gcp_secret_manager, configured_fields=client_id,client_secret,developer_token,refresh_token, google_ads_live_enabled=false, error_code=none | Fake validation values only. No real credentials. No payload printed. |
| C — Read/status | **PASS** | configured=true, available=true, credential_ref=&lt;redacted&gt;, backend=gcp_secret_manager, configured_fields=developer_token,client_id,client_secret,refresh_token (all true), google_ads_live_enabled=false, payload_printed=false, error_code=none | Status verified via list+status only. No payload printed. |
| D — List | **PASS** | listed=true, credential_ref_found=true, manual_validation_records_count=1, payload_accessed=false, backend=gcp_secret_manager, configured_fields=[] (descriptor-only), google_ads_live_enabled=false, error_code=none | list_secret_records descriptor API only. No payload access. |
| E — Delete | Pending | | |
| F — Provider composition | Pending | | |

**Overall:** In progress (4/6 phases complete)

---

## 11. Failure Handling

| Failure | Action |
|---------|--------|
| `permission_denied` / `gcp_secret_access_denied` | Stop. Record `permission_denied`. Check IAM bindings per `docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md` Section 6. Do not retry until IAM is corrected. |
| Payload validation error | Stop. Inspect local test values in operator's terminal only. Do not paste payload into chat or docs. |
| `not_found` on read/delete | Verify `credential_ref` matches what was written in Phase B. Check `GCP_SECRET_MANAGER_PREFIX` and `GCP_SECRET_MANAGER_ENV` match. |
| Service account JSON appears inside repo | Stop immediately. Remove file. Do not commit. Re-run `find . -name "*service-account*.json"`. |
| Any token value printed to terminal | Stop. Do not copy output anywhere. Set `GCP_SECRET_MANAGER_ENABLED=false`. Clear terminal history if needed. |
| `gcloud` auth expired | Run `gcloud auth login` or `gcloud auth application-default login` to refresh. |

---

## 12. Cleanup

After Phases A–F are complete:

```bash
# Step 1 — confirm test secret deleted (Phase E should have done this)
# If not yet deleted, run:
# store.delete_secret_bundle('cred_google_ads_manual_validation_v5130', 'google_ads')

# Step 2 — unset validation env vars
export GCP_SECRET_MANAGER_ENABLED=false
unset GCP_PROJECT_ID
unset GOOGLE_APPLICATION_CREDENTIALS
export GOOGLE_ADS_CREDENTIAL_SOURCE=env
export GOOGLE_ADS_LIVE_ENABLED=false

# Step 3 — confirm no service account JSON in repo
find ~/kaiju -name "*service-account*.json" -o -name "*credentials*.json" -o -name "*gcp*.json" | grep -v ".venv" | grep -v ".git"

# Step 4 — re-run smoke baseline
cd ~/kaiju
bash scripts/smoke_test_v5_12_gcp_secret_manager.sh
bash scripts/smoke_test_v5_credentials.sh
```

---

## 13. Acceptance Criteria

- [x] Phase A — config/status passes with live env vars
- [x] Phase B — test secret created in real GCP Secret Manager
- [x] Phase C — redacted status returns correct `configured_fields`
- [x] Phase D — list returns test secret with `configured_fields: []`
- [ ] Phase E — delete returns `True`; post-delete status confirms `not_found`
- [ ] Phase F — provider composition returns `ok: True` with `GOOGLE_ADS_LIVE_ENABLED=false`
- [ ] Test secret cleaned up (deleted from GCP)
- [ ] No real secrets in this document
- [ ] No live Google Ads API calls made
- [ ] Smoke baseline passes after cleanup

---

## Related Documents

- [V5.13 Manual GCP Validation Plan](V5_13_MANUAL_GCP_VALIDATION_PLAN.md)
- [V5.13 Pre-Flight Checks](V5_13_PREFLIGHT_CHECKS.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [V5.12 Release Notes](V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [Roadmap](ROADMAP.md)

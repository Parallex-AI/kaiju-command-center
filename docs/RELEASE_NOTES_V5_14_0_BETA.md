# Release Notes — v5.14.0-beta

**Branch:** `v5.14-admin-gcp-wiring`
**Base:** `v5.13.0-beta`
**Tag candidate:** `v5.14.0-beta`
**Status:** Complete — ready for merge and tag

---

## Release Summary

v5.14.0-beta completes the admin credential bundle write path deferred from V5.12.6. `POST /credentials/google-ads` can now accept a full Google Ads credential bundle: metadata fields are written to `LocalFileCredentialReferenceStore`; secret fields are written to `SecretStore` (factory-selected: `InMemorySecretStore` by default, `GCPSecretManagerStore` when `GCP_SECRET_MANAGER_ENABLED=true`). The metadata-only path is preserved exactly as before. The live GCP endpoint path was validated in Phase 4 through FastAPI TestClient with fake values only. No real Google Ads credentials were used. No fixed-cost infrastructure was created. Temporary GCP test secrets were deleted.

---

## Highlights

- **Admin endpoint now accepts full credential bundles** — `POST /credentials/google-ads` with `developer_token`, `client_id`, `client_secret`, and `refresh_token` writes secrets to `SecretStore` and metadata to `CredentialReference`
- **Backward-compatible metadata-only path preserved** — payloads without secret fields continue to use `upsert_google_ads_credential_reference()` exactly as before
- **Factory auto-selection** — `InMemorySecretStore` remains the default; `GCPSecretManagerStore` activates only when `GCP_SECRET_MANAGER_ENABLED=true`
- **Response never contains secret values** — `secret_status` returns configured fields as booleans only; no field values in any response path
- **Forbidden field and incomplete bundle rejection** — `access_token` and other disallowed fields rejected with `secret_material_rejected`; partial bundles rejected with `secret_bundle_incomplete`
- **Live GCP endpoint validated** — Phase 4 confirmed the full POST → `GCPSecretManagerStore` → write → status → delete → post-delete confirm cycle using fake values only
- **API-level smoke added** — `run_admin_credentials_api_write_demo.py` covers five TestClient scenarios; smoke suite extended to 10 sections
- **Zero real credentials used** — fake Google Ads field values only; `GOOGLE_ADS_LIVE_ENABLED=false` throughout
- **Zero fixed-cost infrastructure** — no Cloud Run, GKE, Cloud SQL, Pub/Sub, or any fixed-cost service

---

## What Changed

### `openclaw/admin.py`

Added `write_google_ads_credential_bundle(tenant_id, client_id, payload, secret_store=None)`:

- Partitions payload: secret fields → `SecretStore`; metadata fields → `LocalFileCredentialReferenceStore`
- Forbidden-field guard applied to non-secret fields (rejects `access_token`, `oauth_code`, etc.)
- All four secret fields required (`secret_bundle_incomplete` if any missing)
- `assert_allowed_secret_fields` validates the secret partition (`secret_material_rejected` if unexpected fields)
- `upsert_google_ads_credential_reference()` called with metadata only — secrets never pass through this path
- `credential_ref` resolved from upsert result; used as the secret bundle key
- `create_secret_store()` factory called when `secret_store=None`
- Returns: `{"ok": true, "credential_status": {...}, "secret_status": {...}, "errors": []}`
- `secret_status.configured_fields` contains booleans only — no values

Exported: `GOOGLE_ADS_SECRET_FIELDS` (re-exported from `credentials.secret_store`)

### `openclaw/server.py`

POST `/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads`:

```
if payload contains any key in GOOGLE_ADS_SECRET_FIELDS:
    → write_google_ads_credential_bundle()   # new path
else:
    → upsert_google_ads_credential_reference()  # existing path
```

Both paths return a redacted envelope; error responses return HTTP 400.

### `scripts/smoke_test_v5_credentials.sh`

- Section `[9/10]` — mocked bundle demo (`run_admin_credentials_gcp_write_demo.py`) with `GCP_SECRET_MANAGER_ENABLED=false` and factory default check
- Section `[10/10]` — API TestClient demo (`run_admin_credentials_api_write_demo.py`) with scenario-level pass checks and fake-value stdout guard

### New files

| File | Purpose |
|------|---------|
| `openclaw/run_admin_credentials_gcp_write_demo.py` | Function-level demo with injected `InMemorySecretStore` — 7 sections |
| `openclaw/run_admin_credentials_api_write_demo.py` | FastAPI TestClient demo — scenarios A–E |

---

## Validation Completed

| Phase | What was validated | Result |
|-------|-------------------|--------|
| 2 — Helper demo | `write_google_ads_credential_bundle()` with injected `InMemorySecretStore` · full bundle write · GET status · metadata-only path unchanged · incomplete bundle rejection · forbidden field rejection · factory default · comprehensive leak assertion | **PASS** |
| 3 — API TestClient | POST metadata-only (scenario A) · POST full bundle → `secret_status.configured=true` (scenario B) · POST incomplete bundle → `secret_bundle_incomplete` (scenario C) · POST forbidden field `access_token` → `secret_material_rejected` (scenario D) · cross-response leak assertion (scenario E) | **PASS** |
| 4 — Live GCP endpoint | POST full bundle via FastAPI TestClient → `GCPSecretManagerStore` · `status_code=200` · `ok=true` · `secret_status.configured=true` · all 4 fields confirmed · temporary secret deleted · `post_delete_configured=false` confirmed | **PASS** |

---

## Security Guarantees

These invariants held throughout all validation phases and are enforced by design:

| Invariant | How enforced |
|-----------|--------------|
| Secret values never in API responses | `secret_status` returns only boolean `configured_fields`; no raw values anywhere in response path |
| Forbidden extra fields rejected | `assert_allowed_secret_fields` rejects `access_token`, `oauth_code`, and any non-bundle field in secret position |
| Incomplete bundles rejected before any write | Missing-field check before `SecretStore.put_secret_bundle()` is called |
| No real Google Ads credentials used | Only `fake-*-v5-14-phase-4` values in Phase 4; `GOOGLE_ADS_LIVE_ENABLED=false` throughout |
| No credential payload printed | Phase 4 inline script; all `credential_ref` and `secret_id` values recorded as `<redacted>` |
| No real secrets committed to Git | Secret-safety grep confirms clean; runtime files not tracked |
| Credential reference store redirected outside repo | `CREDENTIAL_REFERENCE_STORE_PATH` set to `/tmp/` path in all demos and Phase 4 |
| Temporary GCP test secret deleted | `delete_secret_bundle()` called in Phase 4 `finally` block; `post_delete_configured=false` confirmed |
| Service account JSON outside repo | `GOOGLE_APPLICATION_CREDENTIALS` points to path outside `~/kaiju/` |
| Operator profile outside repo | `~/.kaiju/gcp-v513.env` — never committed |

---

## Cost Guarantees

| Guarantee | Status |
|-----------|--------|
| Pay-per-use only | GCP Secret Manager API: charged per operation, no standing cost |
| No fixed-cost infrastructure | No Cloud Run, GKE, Compute Engine, Cloud SQL, BigQuery, Pub/Sub, Scheduler, Load Balancer, NAT Gateway, Redis/Memorystore |
| No IAM changes | Confirmed |
| No billing changes | Confirmed |
| No API enablement | Confirmed |
| No production deployment | Confirmed |

---

## Smoke Tests

| Suite | Result |
|-------|--------|
| `scripts/smoke_test_v5_credentials.sh` | **10/10 PASS** — env/imports, model demo, stores, resolver, secret store + provider, adapter non-live, OpenClaw admin endpoints (POST/GET/forbidden/malformed/auth), secret-safety + git hygiene, mocked bundle demo, API TestClient demo |
| `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **8/8 PASS** — imports, disabled mode, read/status mock, write mock, delete/list mock, factory behavior, provider/factory integration, secret-safety + git hygiene |

---

## Operator Notes

No migration steps are required to upgrade from v5.13.0-beta. All new behavior is additive and factory-gated.

**To enable GCP Secret Manager as the credential backend:**

```bash
GCP_SECRET_MANAGER_ENABLED=true
GCP_PROJECT_ID=<your-project-id>
GCP_SECRET_MANAGER_PREFIX=kaiju
GCP_SECRET_MANAGER_ENV=dev        # or: staging, prod
GOOGLE_APPLICATION_CREDENTIALS=<path-to-service-account.json>   # outside repo
GOOGLE_ADS_CREDENTIAL_SOURCE=provider
GOOGLE_ADS_LIVE_ENABLED=false     # keep false until real credentials are validated
```

**To write a credential bundle via the admin endpoint:**

```bash
curl -X POST \
  http://localhost:<port>/openclaw/admin/tenants/<tenant_id>/clients/<client_id>/credentials/google-ads \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "<customer_id>",
    "login_customer_id": "<login_customer_id>",
    "developer_token": "<developer_token>",
    "client_id": "<oauth_client_id>",
    "client_secret": "<oauth_client_secret>",
    "refresh_token": "<refresh_token>"
  }'
```

The response includes `credential_status` and `secret_status` with configured fields as booleans only. No secret values are returned.

**To write metadata only (existing behavior):**

Omit all four secret fields. The request routes to the existing `upsert_google_ads_credential_reference()` path. Response includes `credential_status` only; `secret_status` is absent.

See [`docs/GCP_SECRET_MANAGER_RUNBOOK.md`](GCP_SECRET_MANAGER_RUNBOOK.md) for IAM setup, secret naming, and Cloud Run deployment instructions.

---

## Not Included in v5.14.0-beta

The following remain deferred:

- **Real Google Ads credentials** — OAuth credentials (`developer_token`, `client_secret`, `refresh_token`) not validated against the Google Ads API; `GOOGLE_ADS_LIVE_ENABLED=false` throughout
- **Google Ads live API execution** — no live API calls made in any validation phase
- **Production deployment** — no Cloud Run deployment performed
- **Credential validation endpoint** — no `POST .../validate` to test a stored credential against the live Google Ads API
- **Credential delete/revoke endpoint** — credential delete through the admin API is not yet productized
- **Secret rotation UX** — no rotation endpoint or rotation runbook wired through the admin API
- **Admin authorization hardening** — auth is currently an API key placeholder; per-tenant RBAC and audit trail for credential writes are future work
- **Frontend credential onboarding UI** — deferred to a future branch
- **OAuth connect flow** — requires Google OAuth consent screen; not in scope

---

## Recommended Next Steps

1. **Merge and tag** — merge `v5.14-admin-gcp-wiring` into `master`; tag `v5.14.0-beta`
2. **Controlled real credential onboarding** — run a controlled test with real (non-production) Google Ads OAuth credentials, `GOOGLE_ADS_LIVE_ENABLED=false`, validating the full bundle write + provider composition chain end-to-end through the admin endpoint
3. **V5.15 credential lifecycle hardening** — validation UX, audit log integration for credential writes, rotation/revoke endpoint, authorization controls, operator runbook
4. **Cloud Run deployment** — deploy OpenClaw to Cloud Run with `GCPSecretManagerStore`, following [`docs/GCP_SECRET_MANAGER_RUNBOOK.md`](GCP_SECRET_MANAGER_RUNBOOK.md)
5. **Controlled live Google Ads fetch** — single scoped test call with explicit operator approval and known-safe account

All steps should maintain the established guardrails: pay-as-you-go only, no fixed-cost infrastructure, no secrets committed, explicit operator approval before any live Google Ads API call.

---

## Related Documents

- [V5.14 Branch Closure](V5_14_BRANCH_CLOSURE.md)
- [Release Notes — v5.13.0-beta](RELEASE_NOTES_V5_13_0_BETA.md)
- [V5.13 Branch Closure](V5_13_BRANCH_CLOSURE.md)
- [V5.12 GCP Secret Manager Release Notes](V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

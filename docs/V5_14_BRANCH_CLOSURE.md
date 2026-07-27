# V5.14 Branch Closure — Admin Credential Bundle GCP Wiring

**Branch:** `v5.14-admin-gcp-wiring`
**Base tag:** `v5.13.0-beta`
**Target release tag candidate:** `v5.14.0-beta`
**Status:** Complete — all phases PASS · closure docs complete · ready for merge and tag

---

## Summary

V5.14 wired the OpenClaw admin credential write endpoint to `SecretStore` — completing the deferred V5.12.6 item. `POST /credentials/google-ads` can now write a full Google Ads credential bundle: metadata fields go to `LocalFileCredentialReferenceStore`; secret fields go to `SecretStore` (auto-selected by factory: `InMemorySecretStore` by default, `GCPSecretManagerStore` when `GCP_SECRET_MANAGER_ENABLED=true`). The metadata-only path is fully preserved. The live GCP endpoint path was validated in Phase 4 using fake values only. All smoke suites pass. No real credentials were used. No fixed-cost infrastructure was created. Temporary GCP test secrets were deleted.

---

## Scope

This branch covered one task: **wire the admin credential bundle write endpoint to `SecretStore`, validate all paths, and close the branch.**

What was implemented:
- `write_google_ads_credential_bundle()` in `openclaw/admin.py`
- Server routing in `openclaw/server.py` — secret-bearing payloads take the new bundle write path; metadata-only payloads keep the existing path
- Local helper demo: `openclaw/run_admin_credentials_gcp_write_demo.py`
- API-level FastAPI TestClient demo: `openclaw/run_admin_credentials_api_write_demo.py`
- Extended smoke suite: `scripts/smoke_test_v5_credentials.sh` — sections 9 and 10

What was not in scope: frontend credential UI, OAuth consent flow, secret rotation UX, production deployment, real Google Ads API calls, IAM changes.

---

## Completed Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| Phase 2 | `write_google_ads_credential_bundle()` helper + server routing + local demo | **Complete** |
| Phase 3 | API-level FastAPI TestClient smoke — scenarios A–E | **Complete** |
| Phase 4 | Live GCP endpoint validation — fake bundle via `GCPSecretManagerStore` through the POST route | **Complete** |
| Closure | Branch closure doc · release notes · ROADMAP · README · final smoke suites | **Complete** |

---

## Implementation Summary

### `openclaw/admin.py` — `write_google_ads_credential_bundle()`

- Partitions payload into secret fields (`developer_token`, `client_id`, `client_secret`, `refresh_token`) and metadata fields (`customer_id`, `login_customer_id`, `status`, `metadata`)
- Runs forbidden-field guard on non-secret fields only
- Requires all four secret fields — partial bundles rejected with `secret_bundle_incomplete`
- Validates secret fields via `assert_allowed_secret_fields` — unknown/globally-forbidden fields (e.g. `access_token`) rejected with `secret_material_rejected`
- Upserts `CredentialReference` via existing `upsert_google_ads_credential_reference()` (metadata only — no secrets passed)
- Resolves `credential_ref` from upsert result
- Writes secret bundle to `SecretStore` via `put_secret_bundle(credential_ref, integration_type, secrets)`
- Returns combined redacted response: `credential_status` + `secret_status` (configured fields as booleans only) — no secret values anywhere

### `openclaw/server.py` — routing

POST `/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads`:

- If payload contains any known Google Ads secret field → `write_google_ads_credential_bundle()`
- Otherwise → `upsert_google_ads_credential_reference()` (existing path, backward-compatible)
- Error responses: 400 on `ok=false`; 200 on `ok=true`

### Secret store factory

When `secret_store=None` (production path), `create_secret_store()` auto-selects:
- `InMemorySecretStore` — when `GCP_SECRET_MANAGER_ENABLED` is unset or `false`
- `GCPSecretManagerStore` — when `GCP_SECRET_MANAGER_ENABLED=true`

`secret_store=` injection (test path) bypasses the factory and is used in Phase 3 TestClient demos.

### Files added

| File | Purpose |
|------|---------|
| `openclaw/run_admin_credentials_gcp_write_demo.py` | Function-level demo with injected `InMemorySecretStore` — 7 sections including factory default and comprehensive leak assertion |
| `openclaw/run_admin_credentials_api_write_demo.py` | FastAPI TestClient demo — 5 scenarios (A–E): metadata-only, full bundle, incomplete bundle, forbidden field, cross-response leak assertion |

### Files modified

| File | Change |
|------|--------|
| `openclaw/admin.py` | Added `write_google_ads_credential_bundle()` |
| `openclaw/server.py` | Added bundle-write routing; imports `write_google_ads_credential_bundle`, `GOOGLE_ADS_SECRET_FIELDS` |
| `scripts/smoke_test_v5_credentials.sh` | Extended to sections 9 and 10 (mocked bundle demo + API TestClient demo) |

---

## Validation Phases

| Phase | Description | Result |
|-------|-------------|--------|
| 2 | Local helper/demo — `write_google_ads_credential_bundle()` with `InMemorySecretStore` · 7 scenarios · factory default · leak assertions | **PASS** |
| 3 | API-level FastAPI TestClient — scenarios A–E: metadata-only POST, full bundle POST, incomplete bundle rejection, forbidden field rejection, cross-response leak assertion | **PASS** |
| 4 | Live GCP endpoint — full bundle via `POST /credentials/google-ads` through `GCPSecretManagerStore` · temporary secret deleted · post-delete `configured=false` confirmed | **PASS** |

### Phase 4 evidence (all output redacted)

| Field | Value |
|-------|-------|
| `endpoint_post_ok` | `true` |
| `status_code` | `200` |
| `secret_status_configured` | `true` |
| `configured_fields` | `developer_token, client_id, client_secret, refresh_token` |
| `credential_ref` | `<redacted>` |
| `secret_id` | `<redacted>` |
| `backend` | `gcp_secret_manager` |
| `google_ads_live_enabled` | `false` |
| `google_ads_api_called` | `false` |
| `output_redacted` | `true` |
| `temporary_secret_deleted` | `true` |
| `post_delete_configured` | `false` |
| `payload_printed` | `false` |
| `error_code` | `none` |

---

## Smoke Test Results

| Suite | Script | Result |
|-------|--------|--------|
| V5 credentials | `scripts/smoke_test_v5_credentials.sh` | **10/10 PASS** |
| V5.12 GCP Secret Manager | `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **8/8 PASS** |
| Helper/function demo | `openclaw/run_admin_credentials_gcp_write_demo.py` | **PASS** |
| API TestClient demo | `openclaw/run_admin_credentials_api_write_demo.py` | **PASS** |

All suites run without real GCP credentials in default mode. Live GCP path validated in Phase 4.

---

## Security Posture

| Property | Status |
|----------|--------|
| Secret values never returned by any API response | Confirmed |
| Secret values never printed or logged | Confirmed |
| Forbidden extra field `access_token` rejected with `secret_material_rejected` | Confirmed |
| Incomplete secret bundle rejected with `secret_bundle_incomplete` | Confirmed |
| Fake values only in tests and demos | Confirmed |
| `GOOGLE_ADS_LIVE_ENABLED=false` throughout | Confirmed |
| No Google Ads live API calls | Confirmed |
| No real secrets committed to Git | Confirmed |
| No credential JSON in repo | Confirmed |
| No `.env` committed | Confirmed |
| Credential reference store created in temp dir outside repo during tests | Confirmed |
| Temporary GCP Secret Manager secret deleted after Phase 4 | Confirmed |
| Post-delete `configured=false` confirmed | Confirmed |
| Actual `credential_ref` and `secret_id` never printed or recorded | Confirmed |
| Local operator profile (`~/.kaiju/gcp-v513.env`) outside repo | Confirmed |
| `GOOGLE_APPLICATION_CREDENTIALS` path outside repo | Confirmed |
| Secret-safety grep clean | Confirmed |
| No runtime credential files tracked by Git | Confirmed |

---

## Cost Posture

| Property | Status |
|----------|--------|
| No fixed-cost infrastructure created | Confirmed |
| No Cloud Run, GKE, or Compute Engine | Confirmed |
| No Cloud SQL, BigQuery, Pub/Sub, or Scheduler | Confirmed |
| No Load Balancer, NAT Gateway, or Redis/Memorystore | Confirmed |
| No committed use discounts or reserved capacity | Confirmed |
| No paid Marketplace services | Confirmed |
| No production deployment | Confirmed |
| No IAM changes | Confirmed |
| No billing changes | Confirmed |
| No API enablement | Confirmed |
| GCP Secret Manager API calls: pay-per-use · temporary · deleted after Phase 4 | Confirmed |

---

## What Was Explicitly Not Done

- No production deployment (Cloud Run or otherwise)
- No real Google Ads OAuth credentials used or validated
- No Google Ads live API calls
- No user-facing credential submission UI
- No multi-tenant production onboarding flow
- No secret rotation UX
- No admin authorization hardening beyond existing auth placeholder
- No audit trail hardening specific to credential writes
- No IAM changes or service account updates

---

## Known Limitations

- Phase 4 validated one controlled fake bundle through the endpoint — not a full production load test
- Real Google Ads OAuth credentials (`developer_token`, `client_secret`, `refresh_token`) have not been validated against the live Google Ads API; `GOOGLE_ADS_LIVE_ENABLED=false` throughout
- Production deployment is deferred; no Cloud Run wiring to `GCPSecretManagerStore` in a live environment
- Admin authorization is currently an API key placeholder — per-tenant IAM isolation and RBAC are future work
- Secret rotation and credential delete/revoke flows through the admin endpoint are not yet end-to-end productized
- Audit trail for credential write events is not yet integrated with the OpenClaw audit log

---

## Next Recommended Milestone

After merge and tag:

1. **V5.15 — Admin credential lifecycle hardening**: validation UX (test live credential against Google Ads), audit log integration for credential write/delete events, credential rotation/revoke endpoint, authorization controls hardening, operator runbook for credential operations
2. **Controlled real credential onboarding**: run a controlled test with real (non-production) Google Ads OAuth credentials, still with `GOOGLE_ADS_LIVE_ENABLED=false` — validate the full bundle write and provider composition chain end-to-end
3. **Cloud Run deployment**: deploy OpenClaw to Cloud Run with `GCPSecretManagerStore`, IAM-scoped service account, and a tested secret rotation runbook

All future milestones should maintain the established guardrails: pay-as-you-go only, no fixed-cost infrastructure, no secrets committed, explicit operator approval before any live Google Ads API call.

---

## Merge and Tag Recommendation

Once final review is complete:

```bash
git checkout master
git merge --no-ff v5.14-admin-gcp-wiring
git tag v5.14.0-beta
```

Tag message: `v5.14.0-beta — Admin credential bundle GCP wiring (Phases 2–4 PASS)`

**Prerequisites before merge:**
- Final smoke suite pass (complete — see above)
- Secret-safety grep clean (complete — confirmed)
- No credential JSON in repo (complete — confirmed)
- Working tree clean (complete — confirmed)

---

## Related Documents

- [V5.13 Branch Closure](V5_13_BRANCH_CLOSURE.md)
- [Release Notes — v5.13.0-beta](RELEASE_NOTES_V5_13_0_BETA.md)
- [Release Notes — v5.14.0-beta](RELEASE_NOTES_V5_14_0_BETA.md)
- [V5.12 GCP Secret Manager Release Notes](V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

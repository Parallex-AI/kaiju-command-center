# Release Notes — v5.13.0-beta

**Branch:** `v5.13-manual-gcp-validation`
**Base:** `v5.12.0-beta`
**Tag candidate:** `v5.13.0-beta`
**Status:** Complete — ready for merge and tag

---

## Release Summary

v5.13.0-beta completes the live GCP validation of the `GCPSecretManagerStore` backend introduced in V5.12. The implementation was validated against a real GCP project through six manual phases covering write, read, list, delete, and full credential provider composition. All phases passed. No source code changes were made in V5.13. This release is documentation and validation only.

---

## Highlights

- **GCP Secret Manager backend confirmed live** — `GCPSecretManagerStore` write, read, list, delete, and provider composition all validated against a real GCP project
- **Provider composition verified end-to-end** — `compose_google_ads_credentials` successfully resolved a `CredentialReference`, fetched the secret bundle from live GCP Secret Manager, and composed a `GoogleAdsCredentials` object
- **Zero real credentials used** — all validation used fake Google Ads field values; `GOOGLE_ADS_LIVE_ENABLED=false` throughout
- **Zero fixed-cost infrastructure** — no Cloud Run, GKE, Cloud SQL, Pub/Sub, or any fixed-cost service was created; GCP Secret Manager API is pay-per-use
- **Temporary test secrets deleted** — all secrets created during validation were deleted from GCP after each phase; no persistent test secrets remain
- **Smoke suite green** — `smoke_test_v5_12_gcp_secret_manager.sh` 28/28 PASS; `smoke_test_v5_credentials.sh` all sections PASS

---

## Validation Completed

| Phase | What was validated | Result |
|-------|-------------------|--------|
| A — Config | Env vars present; `GCPSecretManagerStore` init success; disabled-mode guard works | **PASS** |
| B — Write | `put_secret_bundle` with fake Google Ads fields via live GCP Secret Manager | **PASS** |
| C — Read/status | `get_secret_status` returns `configured=true`; 4 fields present; no payload value printed | **PASS** |
| D — List | `list_secret_records` returns descriptor-only; no `access_secret_version` called; `configured_fields=[]` | **PASS** |
| E — Delete | `delete_secret_bundle` returns `True`; post-delete status `configured=false` confirmed | **PASS** |
| F — Provider | `compose_google_ads_credentials` resolved reference → fetched live bundle → composed credentials; redacted output verified; no secret values in output; temp secret deleted; repo clean | **PASS** |

Full results: [`docs/V5_13_LIVE_GCP_VALIDATION_RESULTS.md`](V5_13_LIVE_GCP_VALIDATION_RESULTS.md)

---

## Security Guarantees

These invariants held throughout all validation phases and are enforced by design:

| Invariant | How enforced |
|-----------|--------------|
| No real Google Ads credentials used | Only fake field values in all Phase B–F secret bundles |
| `GOOGLE_ADS_LIVE_ENABLED=false` | Set in operator profile; never overridden |
| No credential payload printed | `repr=False` on `credentials` field; `google_ads_provider_result_to_redacted_dict()` used for all output |
| No real secrets committed to Git | Secret-safety grep confirms clean; runtime files not tracked |
| Service account JSON outside repo | `GOOGLE_APPLICATION_CREDENTIALS` points to path outside `~/kaiju/` |
| Operator profile outside repo | `~/.kaiju/gcp-v513.env` — never committed |
| Temporary test secrets deleted | Each phase cleaned up after itself; GCP confirmed removal via `get_secret_status` |
| No credential ref values in docs | All `credential_ref` and `secret_id` values recorded as `<redacted>` |

---

## Cost Guarantees

| Guarantee | Status |
|-----------|--------|
| Pay-per-use only | GCP Secret Manager API: charged per operation, no standing cost |
| No fixed-cost infrastructure | No Cloud Run, GKE, Compute Engine, Cloud SQL, BigQuery, Pub/Sub, Scheduler, Load Balancer, NAT Gateway, Redis/Memorystore |
| No committed use or reserved capacity | Confirmed |
| No paid Marketplace services | Confirmed |
| No production deployment | Confirmed |

---

## Smoke Tests

| Suite | Result |
|-------|--------|
| `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | **28/28 PASS** — imports, disabled mode, read/write/delete/list mock paths, `SecretStoreFactory`, provider/factory integration, secret-safety, git hygiene |
| `scripts/smoke_test_v5_credentials.sh` | **All sections PASS** — env/imports, model demo, stores, resolver, secret store + provider, adapter non-live, OpenClaw admin endpoints, secret-safety + git hygiene |

---

## Migration / Operator Notes

No migration steps are required for this release. V5.13 is validation-only — no source code was changed.

**To enable GCP Secret Manager in a local or deployed environment:**

```bash
GCP_SECRET_MANAGER_ENABLED=true
GCP_PROJECT_ID=<your-project-id>
GCP_SECRET_MANAGER_PREFIX=kaiju
GCP_SECRET_MANAGER_ENV=dev        # or: staging, prod
GOOGLE_APPLICATION_CREDENTIALS=<path-to-service-account.json>
GOOGLE_ADS_CREDENTIAL_SOURCE=provider
GOOGLE_ADS_LIVE_ENABLED=false     # keep false until real credentials are validated
```

The system defaults to `InMemorySecretStore` when `GCP_SECRET_MANAGER_ENABLED` is unset or `false`. No changes to existing local developer setup are required.

See [`docs/GCP_SECRET_MANAGER_RUNBOOK.md`](GCP_SECRET_MANAGER_RUNBOOK.md) for full IAM setup, secret naming, and Cloud Run deployment instructions.

---

## Not Included in v5.13.0-beta

The following remain deferred:

- **Real Google Ads credentials** — OAuth credentials (`developer_token`, `client_secret`, `refresh_token`) were not validated against the Google Ads API; live call testing remains future work
- **Google Ads live API execution** — `GOOGLE_ADS_LIVE_ENABLED=false` throughout; no live API calls were made
- **Production deployment** — no Cloud Run deployment was performed; deployment runbook is in [`docs/GCP_SECRET_MANAGER_RUNBOOK.md`](GCP_SECRET_MANAGER_RUNBOOK.md)
- **OpenClaw admin → GCPSecretManagerStore wiring** — the admin credential write path wired to live GCP (V5.12.6 deferred item) remains deferred
- **Frontend credential onboarding UI** — deferred to a future branch
- **OAuth connect flow** — requires Google OAuth consent screen; not in scope
- **Multi-tenant production hardening** — per-tenant IAM isolation, automatic secret rotation, audit log integration are future work

---

## Recommended Next Steps

1. **Merge and tag** — merge `v5.13-manual-gcp-validation` into `master`; tag `v5.13.0-beta`
2. **Wire OpenClaw admin endpoint to GCPSecretManagerStore** — complete the deferred V5.12.6 item: `POST /credentials/google-ads` writes to live Secret Manager when `GCP_SECRET_MANAGER_ENABLED=true`
3. **Controlled real credential onboarding** — run a controlled, non-production credential write and resolution test with real (but isolated) Google Ads OAuth credentials, still with `GOOGLE_ADS_LIVE_ENABLED=false`
4. **Cloud Run deployment** — deploy OpenClaw to Cloud Run with Secret Manager integration, following [`docs/GCP_SECRET_MANAGER_RUNBOOK.md`](GCP_SECRET_MANAGER_RUNBOOK.md)
5. **Controlled live Google Ads fetch** — single scoped test call with explicit operator approval and known-safe account

All steps should maintain the established cost and secret guardrails: pay-as-you-go only, no fixed-cost infrastructure, no secrets committed, explicit operator approval before any live Google Ads API call.

---

## Related Documents

- [V5.13 Branch Closure](V5_13_BRANCH_CLOSURE.md)
- [V5.13 Live GCP Validation Results](V5_13_LIVE_GCP_VALIDATION_RESULTS.md)
- [V5.13 Manual GCP Validation Plan](V5_13_MANUAL_GCP_VALIDATION_PLAN.md)
- [V5.13 Pre-flight Checks](V5_13_PREFLIGHT_CHECKS.md)
- [V5.12 GCP Secret Manager Release Notes](V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [Roadmap](ROADMAP.md)

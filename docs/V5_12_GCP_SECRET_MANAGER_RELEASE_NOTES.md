# Kaiju Command Center V5.12 — GCP Secret Manager Backend Foundation

**Branch:** `v5.12-gcp-secret-manager`
**Base tag:** `v5.0.0-beta`
**Recommended tag:** `v5.12.0-beta`
**Status:** Beta — mocked validation complete · live GCP validation deferred to `v5.13-manual-gcp-validation`

---

## Scope

This release adds a production-oriented GCP Secret Manager backend for the existing `SecretStore` abstraction introduced in V5. The `GCPSecretManagerStore` implements the same `SecretStore` ABC as the existing `InMemorySecretStore`, selected at runtime via `SecretStoreFactory` and a single environment variable flag. All automated tests run without real GCP credentials. The system remains fully functional in disabled mode (default).

---

## Included in V5.12

| Step | What was added |
|------|----------------|
| V5.12.1 | GCP Secret Manager design document (`docs/V5_12_GCP_SECRET_MANAGER_DESIGN.md`) |
| V5.12.2 | `google-cloud-secret-manager>=2.20.0` dependency · lazy import guard · `GCPSecretManagerStore` scaffold (disabled mode) · env config helpers · `build_gcp_secret_id` / `build_gcp_secret_resource_name` · `gcp_secret_manager_status()` |
| V5.12.3 | `get_secret_bundle()` read via `access_secret_version` · `get_secret_status()` redacted view · `parse_gcp_secret_payload()` with field validation · `_map_gcp_exception_to_error_code()` |
| V5.12.4 | `put_secret_bundle()` via `create_secret` + `add_secret_version` · `AlreadyExists` handled safely · `build_gcp_secret_payload()` · `_is_gcp_already_exists()` · `_map_gcp_write_exception_to_error_code()` |
| V5.12.5 | `delete_secret_bundle()` · `list_secret_records()` (no payload access) · `parse_gcp_secret_id()` reversal helper · `_is_gcp_not_found()` · all-safe error returns |
| V5.12.6 | `credentials/secret_store_factory.py` · `create_secret_store()` · `get_secret_store_backend_name()` · `secret_store_factory_status()` · `compose_google_ads_credentials` uses factory when no `secret_store` arg passed |
| V5.12.7 | `scripts/smoke_test_v5_12_gcp_secret_manager.sh` · 8 sections · 28 checks · no real GCP credentials required |
| V5.12.8 | `docs/GCP_SECRET_MANAGER_RUNBOOK.md` · Cloud Run deployment · IAM setup · secret rotation · failure modes · security checklist |

---

## Not Included in V5.12

The following are explicitly deferred:

- **Live GCP validation** — no real GCP project targeted in automated tests; deferred to `v5.13-manual-gcp-validation`
- **Real production secret creation** — no secrets written to any GCP project in this branch
- **Frontend credential onboarding UI** — deferred to a future `v5.13-frontend-onboarding` branch
- **OAuth connect flow** — requires Google OAuth consent screen submission; not in scope
- **User management** — registration, login, password reset not included
- **Billing or subscription management** — not in scope
- **Automatic credential rotation endpoint** — rotation procedure documented in runbook; automated scheduling deferred

---

## Security Model

| Invariant | How enforced |
|-----------|--------------|
| GCP disabled by default | `GCP_SECRET_MANAGER_ENABLED=false` — no GCP client instantiated, no network calls |
| No live GCP calls in automated tests | All tests use injected mock clients via `GCPSecretManagerStore(client=MockClient())` |
| No real credentials in repo | `grep` secret-safety check in `smoke_test_v5_12_gcp_secret_manager.sh` Section 8 |
| No service account JSON in repo | `find` check confirms no `*service-account*.json` or `*credentials*.json` present |
| Secret payloads never returned in public/status responses | `get_secret_status()` returns only `configured_fields` and metadata — no token values |
| List does not access payloads | `list_secret_records()` uses `list_secrets` API only; `access_secret_version` is never called |
| Provider output remains redacted | `compose_google_ads_credentials()` produces `GoogleAdsCredentials` with `is_redacted=True` in status views |
| Fallback to in-memory when GCP disabled | `SecretStoreFactory` returns `InMemorySecretStore()` when `GCP_SECRET_MANAGER_ENABLED != "true"` |

---

## Feature Flags and Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GCP_SECRET_MANAGER_ENABLED` | `false` | Master gate for live Secret Manager calls |
| `GCP_PROJECT_ID` | `` | GCP project for Secret Manager API calls |
| `GCP_SECRET_MANAGER_PREFIX` | `kaiju` | Secret name prefix (e.g. `kaiju-prod-google_ads-...`) |
| `GCP_SECRET_MANAGER_ENV` | `local` | Env segment in secret names (`local`, `dev`, `staging`, `prod`) |
| `GCP_SECRET_MANAGER_LOCATION` | `global` | Secret Manager location |
| `GOOGLE_ADS_CREDENTIAL_SOURCE` | `env` | Set to `provider` to use the SecretStore-backed provider path |
| `GOOGLE_ADS_LIVE_ENABLED` | `false` | Gate for live Google Ads API calls |

---

## Secret Naming Convention

```
{prefix}-{env}-{integration_type}-{credential_ref}
```

Example: `kaiju-prod-google_ads-cred_google_ads_abc123`

Secret payload (UTF-8 JSON bytes):

```json
{
  "developer_token": "...",
  "client_id": "...",
  "client_secret": "...",
  "refresh_token": "..."
}
```

Fields excluded from payload: `login_customer_id`, `customer_id`, `is_mcc`, `access_token`, `id_token`, `token_expiry`.

---

## Testing Completed

| Suite | Script | Status |
|-------|--------|--------|
| V5.12 GCP Secret Manager mocked | `scripts/smoke_test_v5_12_gcp_secret_manager.sh` | Pass |
| V5 credentials | `scripts/smoke_test_v5_credentials.sh` | Pass |
| V4 integrations | `scripts/smoke_test_v4_integrations.sh` | Pass |
| V3 OpenClaw audit | `scripts/smoke_test_v3_openclaw_audit.sh` | Pass |
| V3 OpenClaw HTTP | `scripts/smoke_test_v3_openclaw_http.sh` | Pass |
| V3 OpenClaw | `scripts/smoke_test_v3_openclaw.sh` | Pass |
| V2 memory | `scripts/smoke_test_v2_memory.sh` | Pass |
| V1 graph | `scripts/smoke_test_v1_graph.sh` | Pass |
| V0 | `scripts/smoke_test_v0.sh` (legacy mode) | Pass |

**Live GCP validation:** not performed in automated suite — requires real project, service account, and IAM binding. See `docs/GCP_SECRET_MANAGER_RUNBOOK.md` Section 10 (Manual Validation) for the step-by-step procedure.

---

## Operational Runbook

Full Cloud Run deployment, IAM setup, secret rotation, rollback, failure modes, and security checklist:

**[docs/GCP_SECRET_MANAGER_RUNBOOK.md](GCP_SECRET_MANAGER_RUNBOOK.md)**

---

## Recommended Next Branches

| Branch | Focus | When |
|--------|-------|------|
| `v5.13-manual-gcp-validation` | Run live GCP validation with real project/service account · confirm read/write/delete/list against real Secret Manager | **Recommended first** |
| `v5.13-frontend-onboarding` | Credential submission UI · tenant onboarding form | After live validation passes |
| `v5.13-oauth-connect-flow` | Google OAuth consent screen · token exchange · automatic credential storage | After frontend onboarding |

**Recommendation:** Start with `v5.13-manual-gcp-validation`. The backend is fully implemented and mocked-tested; live validation de-risks the GCP IAM model and secret naming before any frontend work begins.

---

## Merge and Tag Recommendation

Once the final smoke suite passes:

```bash
git checkout master
git merge --no-ff v5.12-gcp-secret-manager
git tag v5.12.0-beta
```

Tag message: `V5.12.0-beta — GCP Secret Manager backend foundation (mocked validation complete)`

---

## Related Documents

- [V5.12 Design Document](V5_12_GCP_SECRET_MANAGER_DESIGN.md)
- [GCP Secret Manager Runbook](GCP_SECRET_MANAGER_RUNBOOK.md)
- [V5 Beta Release Notes](V5_BETA_RELEASE_NOTES.md)
- [V5 Tenant Credentials and Onboarding Design](V5_TENANT_CREDENTIALS_AND_ONBOARDING_DESIGN.md)
- [Roadmap](ROADMAP.md)

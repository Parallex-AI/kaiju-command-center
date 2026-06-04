# GCP Secret Manager Runbook

**Kaiju Command Center — V5.12**

This runbook documents how to deploy and operate the V5.12 GCP Secret Manager backend safely in Cloud Run. It covers IAM setup, environment configuration, secret naming, payload format, rotation, rollback, failure modes, and the manual live validation policy.

---

## 1. Purpose

The `GCPSecretManagerStore` (V5.12) is the production secret backend for tenant Google Ads credentials. It replaces `InMemorySecretStore` for deployed environments while keeping `InMemorySecretStore` as the safe, credential-free default for local development and all automated tests.

This runbook describes how an operator configures and operates that backend in production — without committing secrets to source control, without logging credential values, and without enabling live API access before the deployment is validated.

---

## 2. Current Implementation Status

| Component | Status |
|---|---|
| `GCPSecretManagerStore` — read/status | Complete (V5.12.3) |
| `GCPSecretManagerStore` — write | Complete (V5.12.4) |
| `GCPSecretManagerStore` — delete/list | Complete (V5.12.5) |
| `SecretStoreFactory` | Complete (V5.12.6) |
| Google Ads provider uses factory | Complete (V5.12.6) |
| Mocked smoke test | Complete (V5.12.7) |
| Live GCP validation | **Not yet run — operator-run only** |

**Default behavior is safe.** `GCP_SECRET_MANAGER_ENABLED` defaults to `false`. No GCP client is instantiated, no network calls are made, and the system falls back to `InMemorySecretStore` unless explicitly configured otherwise.

---

## 3. Architecture

```
Client Request
    │
    ▼
OpenClaw (HTTP server)
    │
    ▼
Ads Agent → Google Ads CredentialProvider
    │               │
    │               ▼
    │       SecretStoreFactory
    │               │
    │      ┌────────┴─────────┐
    │      │                  │
    │      ▼                  ▼
    │  InMemorySecretStore   GCPSecretManagerStore
    │  (local/dev/test)      (production)
    │                         │
    │                         ▼
    │                  GCP Secret Manager API
    │
    ▼
Google Ads Adapter (fetch_google_ads_metrics)
```

**Separation of concerns:**

| Data | Where it lives |
|---|---|
| `developer_token`, `client_id`, `client_secret`, `refresh_token` | GCP Secret Manager (secret payload) |
| `customer_id`, `login_customer_id` | `CredentialReference` metadata store (local file or future DB) |
| `access_token`, `oauth_code` | Never stored — ephemeral, rejected by validation layer |

The secret payload and the credential reference metadata are stored separately by design. `credential_ref` is an opaque hash-based identifier that links the two without embedding secret values in metadata.

---

## 4. Required Environment Variables

### Production values

```
GCP_SECRET_MANAGER_ENABLED=true
GCP_PROJECT_ID=<your-gcp-project-id>
GCP_SECRET_MANAGER_PREFIX=kaiju
GCP_SECRET_MANAGER_ENV=prod
GOOGLE_ADS_CREDENTIAL_SOURCE=provider
GOOGLE_ADS_LIVE_ENABLED=false   # set true only after manual validation
```

### Safe local / dev defaults (no GCP access)

```
GCP_SECRET_MANAGER_ENABLED=false
GCP_PROJECT_ID=
GCP_SECRET_MANAGER_PREFIX=kaiju
GCP_SECRET_MANAGER_ENV=local
GOOGLE_ADS_CREDENTIAL_SOURCE=env
GOOGLE_ADS_LIVE_ENABLED=false
```

When `GCP_SECRET_MANAGER_ENABLED=false`, no GCP client is instantiated and `SecretStoreFactory` returns `InMemorySecretStore`. All existing smoke tests run in this mode.

### Full variable reference

| Variable | Default | Production value |
|---|---|---|
| `GCP_SECRET_MANAGER_ENABLED` | `false` | `true` |
| `GCP_PROJECT_ID` | `` (empty) | `<project-id>` |
| `GCP_SECRET_MANAGER_PREFIX` | `kaiju` | `kaiju` |
| `GCP_SECRET_MANAGER_ENV` | `local` | `prod` |
| `GOOGLE_ADS_CREDENTIAL_SOURCE` | `env` | `provider` |
| `GOOGLE_ADS_LIVE_ENABLED` | `false` | `false` initially; `true` only after validation |

---

## 5. Secret Naming Convention

Secret IDs follow a deterministic format built by `build_gcp_secret_id()`:

```
{prefix}-{env}-{integration_type}-{credential_ref}
```

**Example (placeholder values only):**

```
kaiju-prod-google_ads-cred_google_ads_example123abcdef
```

**Segment rules:**

| Segment | Source | Example |
|---|---|---|
| `prefix` | `GCP_SECRET_MANAGER_PREFIX` | `kaiju` |
| `env` | `GCP_SECRET_MANAGER_ENV` | `prod` |
| `integration_type` | sanitized integration type | `google_ads` |
| `credential_ref` | `CredentialReference.credential_ref` | `cred_google_ads_<hash>` |

All segments are sanitized: only `[A-Za-z0-9-_]`, lowercased. This ensures `prod` secrets are never reachable by `local` or `staging` service accounts when IAM conditions are scoped by prefix/env segment.

---

## 6. Secret Payload Format

Secrets are stored as a JSON object encoded as UTF-8 bytes. Keys are sorted for deterministic output.

```json
{
  "client_id": "...",
  "client_secret": "...",
  "developer_token": "...",
  "refresh_token": "..."
}
```

**Allowed fields:** `developer_token`, `client_id`, `client_secret`, `refresh_token`

**Rejected fields (never stored):**

| Field | Reason |
|---|---|
| `customer_id` | Non-secret metadata — lives in `CredentialReference` |
| `login_customer_id` | Non-secret metadata — lives in `CredentialReference` |
| `access_token` | Ephemeral OAuth token — never persisted |
| `oauth_code` | One-time authorization code — never persisted |
| `password` | Not part of Google Ads OAuth flow |
| `authorization` | Header value — never stored |

Validation is enforced by `build_gcp_secret_payload()` and `parse_gcp_secret_payload()` before any GCP API call. Rejected fields raise `ValueError` before touching the network.

---

## 7. IAM Model

The principle of least privilege applies. No `Owner`, `Editor`, or `Secret Manager Admin` role in production.

### Required IAM roles by operation

| Operation | IAM role |
|---|---|
| Read a secret version (`get_secret_bundle`) | `roles/secretmanager.secretAccessor` |
| Add a new secret version (`put_secret_bundle`) | `roles/secretmanager.secretVersionAdder` |
| Create a new secret (`put_secret_bundle` first call) | `roles/secretmanager.secretCreator` |
| Delete a secret (`delete_secret_bundle`) | `roles/secretmanager.secretDeleter` |
| List secrets (`list_secret_records`) | `roles/secretmanager.viewer` |

### Recommended scoping

Bind roles **per-secret prefix using IAM conditions**, not project-wide:

```
resource.name.startsWith("projects/PROJECT_ID/secrets/kaiju-prod-")
```

This prevents a `prod` service account from reading `dev` or `staging` secrets, and vice versa.

### Minimum production surface

A Cloud Run service account that only reads secrets needs:

```
roles/secretmanager.secretAccessor
  condition: resource.name.startsWith("projects/PROJECT_ID/secrets/kaiju-prod-")
```

The write path (credential submission flow) additionally needs:

```
roles/secretmanager.secretVersionAdder
roles/secretmanager.secretCreator
  condition: resource.name.startsWith("projects/PROJECT_ID/secrets/kaiju-prod-")
```

Delete is optional and should be disabled at the IAM level unless the operator intentionally enables it.

---

## 8. Suggested Service Accounts

Use one service account per environment to prevent cross-environment access:

| Environment | Service Account |
|---|---|
| Development | `kaiju-openclaw-dev@PROJECT_ID.iam.gserviceaccount.com` |
| Staging | `kaiju-openclaw-staging@PROJECT_ID.iam.gserviceaccount.com` |
| Production | `kaiju-openclaw-prod@PROJECT_ID.iam.gserviceaccount.com` |

Replace `PROJECT_ID` with your actual GCP project ID. These are examples — use your organization's naming conventions.

---

## 9. GCP Setup Commands

> **These are reference commands with placeholder values. Do not run them until you have reviewed all variables and confirmed the correct project, service account names, and IAM roles for your environment.**

```bash
# 1. Enable the Secret Manager API
gcloud services enable secretmanager.googleapis.com \
  --project=PROJECT_ID

# 2. Create the production service account
gcloud iam service-accounts create kaiju-openclaw-prod \
  --display-name="Kaiju OpenClaw Production" \
  --project=PROJECT_ID

# 3. Grant secretAccessor (read) scoped to prod prefix
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:kaiju-openclaw-prod@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --condition='expression=resource.name.startsWith("projects/PROJECT_ID/secrets/kaiju-prod-"),title=kaiju-prod-secrets-read'

# 4. Grant secretVersionAdder (write new versions) scoped to prod prefix
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:kaiju-openclaw-prod@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretVersionAdder" \
  --condition='expression=resource.name.startsWith("projects/PROJECT_ID/secrets/kaiju-prod-"),title=kaiju-prod-secrets-write'

# 5. Grant secretCreator (create new secrets) scoped to prod prefix
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:kaiju-openclaw-prod@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretCreator" \
  --condition='expression=resource.name.startsWith("projects/PROJECT_ID/secrets/kaiju-prod-"),title=kaiju-prod-secrets-create'

# 6. Verify the service account exists
gcloud iam service-accounts describe \
  kaiju-openclaw-prod@PROJECT_ID.iam.gserviceaccount.com \
  --project=PROJECT_ID
```

**Do not create or download a service account JSON key.** Cloud Run uses the service account directly via Workload Identity / attached service account — no key file required.

---

## 10. Cloud Run Deployment Example

> **Placeholder values. Replace all `PROJECT_ID`, `REGION`, and `IMAGE` values before running.**

```bash
gcloud run deploy kaiju-openclaw \
  --image=REGION-docker.pkg.dev/PROJECT_ID/kaiju/openclaw:latest \
  --region=REGION \
  --platform=managed \
  --service-account=kaiju-openclaw-prod@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars="\
GCP_SECRET_MANAGER_ENABLED=true,\
GCP_PROJECT_ID=PROJECT_ID,\
GCP_SECRET_MANAGER_PREFIX=kaiju,\
GCP_SECRET_MANAGER_ENV=prod,\
GOOGLE_ADS_CREDENTIAL_SOURCE=provider,\
GOOGLE_ADS_LIVE_ENABLED=false,\
OPENCLAW_ENV=production,\
OPENCLAW_API_AUTH_ENABLED=true" \
  --no-allow-unauthenticated \
  --project=PROJECT_ID
```

**Notes:**
- `GOOGLE_ADS_LIVE_ENABLED=false` during initial deployment — enable only after manual validation (see Section 11).
- `--no-allow-unauthenticated` — all requests require authentication.
- Sensitive env vars such as `OPENCLAW_API_KEYS` should be injected via Secret Manager references (`--set-secrets`) rather than plain `--set-env-vars`.

---

## 11. Manual Validation Steps

> **Operator-run only. Do not automate these steps. Do not paste credentials into any chat session.**

These steps validate the Secret Manager integration after initial deployment with live Google Ads calls still disabled.

### Phase 1: Infrastructure validation (no credentials)

1. Deploy with `GOOGLE_ADS_LIVE_ENABLED=false` (see Section 10).
2. Call the health endpoint and confirm `200 OK`:
   ```bash
   curl https://SERVICE_URL/openclaw/health
   ```
3. Call the GCP status helper (future admin endpoint) or use a test script to confirm `gcp_secret_manager_status()` returns `enabled: true`.

### Phase 2: Credential reference metadata (no secrets)

4. POST a `CredentialReference` via the admin endpoint:
   ```bash
   curl -X POST https://SERVICE_URL/openclaw/admin/tenants/TENANT/clients/CLIENT/credentials/google-ads \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"customer_id": "YOUR_CUSTOMER_ID"}'
   ```
5. Confirm the response includes `"ok": true` and a `credential_ref`.

### Phase 3: Secret bundle (requires real credentials — terminal only)

6. Write the secret bundle **directly to GCP Secret Manager** using `gcloud` from a secure terminal — not through the application:
   ```bash
   # Build the secret ID using the naming convention:
   # kaiju-prod-google_ads-<credential_ref>
   SECRET_ID="kaiju-prod-google_ads-CREDENTIAL_REF"

   # Create the payload file in a secure temp location (delete after use)
   cat > /tmp/secret_payload.json <<'EOF'
   {
     "developer_token": "REAL_VALUE_FROM_SECURE_SOURCE",
     "client_id": "REAL_VALUE_FROM_SECURE_SOURCE",
     "client_secret": "REAL_VALUE_FROM_SECURE_SOURCE",
     "refresh_token": "REAL_VALUE_FROM_SECURE_SOURCE"
   }
   EOF

   gcloud secrets create "$SECRET_ID" \
     --project=PROJECT_ID \
     --replication-policy=automatic

   gcloud secrets versions add "$SECRET_ID" \
     --project=PROJECT_ID \
     --data-file=/tmp/secret_payload.json

   # Immediately delete the local temp file
   rm -f /tmp/secret_payload.json
   ```

### Phase 4: Provider validation (no live Google Ads)

7. GET the credential status endpoint and confirm the secret is found:
   ```bash
   curl https://SERVICE_URL/openclaw/admin/tenants/TENANT/clients/CLIENT/credentials/google-ads/status \
     -H "Authorization: Bearer YOUR_API_KEY"
   ```
   Expect `"configured": true` in the response.

8. Run `smoke_test_v5_12_gcp_secret_manager.sh` against the deployed service if applicable, or run local mocked tests to confirm no regressions.

### Phase 5: Live validation (final, optional)

9. Only once Phases 1–4 pass: set `GOOGLE_ADS_LIVE_ENABLED=true` and redeploy.
10. Perform a minimal live adapter call against a non-production Google Ads test account.
11. Confirm the response contains expected metrics with no credential values in logs or response bodies.

---

## 12. Rollback Strategy

If the GCP Secret Manager integration is unstable or causes errors, rollback is non-destructive and requires no code changes:

```bash
gcloud run services update kaiju-openclaw \
  --region=REGION \
  --update-env-vars="\
GCP_SECRET_MANAGER_ENABLED=false,\
GOOGLE_ADS_CREDENTIAL_SOURCE=env,\
GOOGLE_ADS_LIVE_ENABLED=false" \
  --project=PROJECT_ID
```

This immediately returns the service to `InMemorySecretStore` behavior with environment-variable credentials. Secrets in GCP Secret Manager are unaffected — they remain in place for re-enablement once the issue is resolved.

If an image-level rollback is needed:

```bash
gcloud run services update-traffic kaiju-openclaw \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=REGION \
  --project=PROJECT_ID
```

---

## 13. Secret Rotation Strategy

Credentials should be rotated by adding a new Secret Manager version rather than replacing the secret. The `credential_ref` remains stable across rotations.

**Rotation steps:**

1. Obtain new credentials from the Google Ads API console.
2. Prepare the new payload in a secure terminal (same format as Section 6).
3. Add a new version to the existing secret:
   ```bash
   gcloud secrets versions add "kaiju-prod-google_ads-CREDENTIAL_REF" \
     --project=PROJECT_ID \
     --data-file=/tmp/new_secret_payload.json
   rm -f /tmp/new_secret_payload.json
   ```
4. `GCPSecretManagerStore` always reads `versions/latest` — it will use the new version automatically on the next request.
5. Validate that the provider composition succeeds (GET status, non-live provider test).
6. Disable or destroy the old version according to your organization's secret lifecycle policy:
   ```bash
   gcloud secrets versions disable VERSION_NUMBER \
     --secret="kaiju-prod-google_ads-CREDENTIAL_REF" \
     --project=PROJECT_ID
   ```

**Rules:**
- Never expose `refresh_token` in logs, API responses, or monitoring dashboards.
- Never paste credentials into any chat interface (Claude, ChatGPT, Slack, etc.).
- Rotate if any credential is suspected to have been exposed, regardless of confirmed evidence.

---

## 14. Logging and Audit Policy

The following values must **never** appear in application logs, Cloud Logging, audit JSONL, API responses, or monitoring alerts:

| Value | Policy |
|---|---|
| `developer_token` | Never log — GCP Secret Manager payload only |
| `client_secret` | Never log — GCP Secret Manager payload only |
| `refresh_token` | Never log — GCP Secret Manager payload only |
| `client_id` (OAuth) | Never log as a raw value |
| `access_token` | Never stored; never log if transiently available |
| `Authorization` header | Never log request headers containing credentials |
| GCP Secret Manager payload bytes | Never log raw `response.payload.data` |

**What is safe to log:**

| Value | Example |
|---|---|
| `tenant_id` | `acme` |
| `client_id` (platform) | `c1` |
| `integration_type` | `google_ads` |
| `credential_ref` | `cred_google_ads_abc123` (opaque hash) |
| `secret_id` | `kaiju-prod-google_ads-cred_google_ads_abc123` |
| Error codes | `gcp_secret_not_found`, `gcp_secret_access_denied` |
| `configured: true/false` | Boolean presence flag |
| `configured_fields` | Field name → presence boolean map |

**Audit records** must contain only tenant/client/integration/status/error codes. No secret values, no payload bytes, no raw GCP error messages that may contain resource names with embedded identifiers.

---

## 15. Failure Modes and Troubleshooting

| Error code | Likely cause | Safe action | Do not |
|---|---|---|---|
| `gcp_secret_not_found` | Secret does not exist in Secret Manager yet | Create the secret via the write path or `gcloud secrets create` | Log or return the full GCP error message |
| `gcp_secret_access_denied` | Service account lacks `secretAccessor` / `secretVersionAdder` / `secretCreator` role for this prefix | Review IAM bindings; check IAM conditions are correctly scoped | Grant `roles/secretmanager.admin` as a shortcut |
| `gcp_secret_payload_invalid` | Stored payload is not valid JSON, contains disallowed fields, or has empty values | Inspect the secret version in GCP Console (value only, never log it); re-write with a corrected payload | Return raw payload content in error responses |
| `gcp_secret_write_failed` | Generic write failure (quota, network, API not enabled) | Check Secret Manager API is enabled; check quotas; check network connectivity from Cloud Run | Retry blindly without investigating the root cause |
| `gcp_dependency_missing` | `google-cloud-secret-manager` package not installed | Add `google-cloud-secret-manager>=2.20.0` to `requirements.txt` and rebuild the image | Set `GCP_SECRET_MANAGER_ENABLED=true` without the dependency installed |
| `gcp_project_id_missing` | `GCP_PROJECT_ID` and `GOOGLE_CLOUD_PROJECT` are both empty when `GCP_SECRET_MANAGER_ENABLED=true` | Set `GCP_PROJECT_ID` in Cloud Run env vars | Ignore this error — reads and writes will silently fail |
| `credential_provider_failed` | `compose_google_ads_credentials` returned `ok=False` | Check `CredentialReference` status; check secret bundle presence; check `configured_fields` in status response | Log or return the raw `credentials` object |

**General troubleshooting steps:**

1. Call the status endpoint (`GET /credentials/google-ads/status`) and inspect `metadata.error_code`.
2. Check Cloud Logging for the `gcp_` error code (not the raw GCP error message).
3. Verify IAM bindings with `gcloud projects get-iam-policy PROJECT_ID`.
4. Verify the secret exists with `gcloud secrets list --project=PROJECT_ID --filter="name~kaiju-prod"`.
5. If in doubt, set `GCP_SECRET_MANAGER_ENABLED=false` to restore InMemory behavior (see Section 12).

---

## 16. Security Checklist

Before deploying to production, verify all of the following:

- [ ] No service account JSON key files exist in the repository (`find . -name "*service-account*.json"`)
- [ ] No real credentials in `.env.example` or any committed `.env` file
- [ ] Cloud Run service account uses Workload Identity — no downloaded key files
- [ ] Secret Manager API is enabled in the target project
- [ ] IAM bindings are scoped to the `kaiju-prod-` prefix, not project-wide
- [ ] No `roles/owner`, `roles/editor`, or `roles/secretmanager.admin` granted to the Cloud Run service account
- [ ] `GOOGLE_ADS_LIVE_ENABLED=false` during initial deployment
- [ ] All automated smoke tests (`smoke_test_v5_12_gcp_secret_manager.sh`) pass before deploy
- [ ] Secret payload validation enforced by `build_gcp_secret_payload()` — no raw values bypass this
- [ ] No API endpoint returns raw secret values — `SecretRecord` and `redact_secret_status()` used throughout
- [ ] `GCP_SECRET_MANAGER_ENV=prod` is distinct from `local`/`dev`/`staging` to prevent cross-environment access
- [ ] Credential rotation plan documented and understood by the operating team

---

## 17. Manual Live Test Policy

Live testing of the Google Ads API integration requires real credentials and must follow this policy:

**Permitted:**
- Operator runs live tests from a secure terminal on a non-production Google Ads test account
- Credentials are sourced from GCP Secret Manager or secure local `.env` file (not committed)
- Output is reviewed for expected metric shapes only — no raw credential values are examined or logged
- Results are summarized as redacted metadata (`configured: true`, `customer_id: present`, etc.)

**Prohibited:**
- Pasting any credential value into any chat interface (Claude, ChatGPT, Slack, GitHub Issues, etc.)
- Storing credentials in any file that is tracked by Git
- Using production customer accounts for initial validation
- Sharing `refresh_token`, `client_secret`, or `developer_token` over any communication channel
- Running live tests in automated CI/CD pipelines until the full credential rotation and secret lifecycle is operationally validated

**When a live test produces an error:**
- Log only the safe error code (`google_ads_api_error`, `credentials_missing`, etc.)
- Do not log the raw Google Ads API error message if it may contain credential-adjacent identifiers
- Rotate credentials if there is any suspicion of exposure

---

## 18. Related Documents

| Document | Purpose |
|---|---|
| [docs/V5_12_GCP_SECRET_MANAGER_DESIGN.md](V5_12_GCP_SECRET_MANAGER_DESIGN.md) | Full design specification, error codes, API surface, implementation phases |
| [docs/ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) | All environment variable reference including GCP Secret Manager variables |
| [docs/GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md](GOOGLE_ADS_LIVE_INTEGRATION_RUNBOOK.md) | OAuth2 credential setup, GAQL queries, live adapter test plan |
| [docs/GCP_DEPLOYMENT_PLAN.md](GCP_DEPLOYMENT_PLAN.md) | Cloud Run deployment overview for OpenClaw service |
| [docs/V5_BETA_RELEASE_NOTES.md](V5_BETA_RELEASE_NOTES.md) | V5 beta summary including credential architecture |
| [scripts/smoke_test_v5_12_gcp_secret_manager.sh](../scripts/smoke_test_v5_12_gcp_secret_manager.sh) | Mocked smoke test — run before any production deployment |

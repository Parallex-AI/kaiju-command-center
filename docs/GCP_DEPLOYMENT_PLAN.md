# GCP Cloud Run Deployment Plan

**Status:** Documentation only — no real GCP deployment has been executed.
**Branch:** `v3.5-saas-readiness`
**Depends on:** V3.5.5 Docker container readiness

---

## 1. Purpose

This document describes the path to deploying OpenClaw to Google Cloud Run. It is a planning document: all commands use placeholder variables, no cloud resources have been created, and no real credentials are referenced.

---

## 2. Current Local Status

| Artifact | Status |
|---|---|
| `docker/openclaw.Dockerfile` | ✓ Builds successfully |
| `docker run` health check | ✓ Passes locally |
| `docker run` process endpoint | ✓ `ok=true`, `data.router_response` present |
| `docker compose up` | ✓ Service starts, health confirmed, teardown clean |
| GCP deployment | Not executed |

---

## 3. Target Cloud Run Architecture

```
Client / API Consumer
  ↓
Cloud Run: kaiju-openclaw
  (OpenClaw HTTP server — FastAPI — port $PORT)
  ↓
Router + Ads Agent modules (inside container)
  ↓
n8n webhook (external — flows.kaiju.digital or future GCP-hosted)
  ↓
MemPalace
  Current: local container filesystem (not durable across restarts)
  Future:  Firestore / Cloud Storage / Cloud SQL
  ↓
OpenClaw audit log
  Current: local container filesystem (not durable)
  Future:  Cloud Logging / BigQuery / GCS
```

---

## 4. Required GCP Resources (Future)

| Resource | Purpose |
|---|---|
| GCP Project | Billing and resource namespace |
| Artifact Registry | Store Docker images |
| Cloud Run service | Serve OpenClaw HTTP API |
| Secret Manager | Store API keys, n8n URL, future credentials |
| IAM service account | Least-privilege identity for Cloud Run |
| Cloud Logging | Structured audit log sink (future) |
| Cloud Storage / Firestore | Durable memory store (future) |

---

## 5. Docker Build

From the repo root:

```bash
docker build -f docker/openclaw.Dockerfile -t kaiju-openclaw .
```

Local test before pushing:

```bash
docker run --rm -p 8100:8100 \
  -e PORT=8100 \
  -e OPENCLAW_ENV=local \
  kaiju-openclaw

curl http://localhost:8100/openclaw/health
```

---

## 6. Artifact Registry — Push Image (Future)

Replace placeholders before running:

```bash
# Variables
PROJECT_ID=your-gcp-project-id
REGION=us-central1
REPO=kaiju
IMAGE_NAME=openclaw
IMAGE_TAG=latest
IMAGE_URL=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}:${IMAGE_TAG}

# Create repository (one-time)
gcloud artifacts repositories create ${REPO} \
  --repository-format=docker \
  --location=${REGION} \
  --description="Kaiju Command Center images"

# Authenticate Docker to Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Tag and push
docker tag kaiju-openclaw:latest ${IMAGE_URL}
docker push ${IMAGE_URL}
```

---

## 7. Cloud Run Deploy (Future)

```bash
# Variables
PROJECT_ID=your-gcp-project-id
REGION=us-central1
SERVICE_NAME=kaiju-openclaw
IMAGE_URL=${REGION}-docker.pkg.dev/${PROJECT_ID}/kaiju/openclaw:latest
SERVICE_ACCOUNT=kaiju-openclaw-sa@${PROJECT_ID}.iam.gserviceaccount.com

gcloud run deploy ${SERVICE_NAME} \
  --image=${IMAGE_URL} \
  --region=${REGION} \
  --platform=managed \
  --service-account=${SERVICE_ACCOUNT} \
  --port=8080 \
  --allow-unauthenticated \
  --set-env-vars="OPENCLAW_ENV=production" \
  --set-env-vars="OPENCLAW_API_AUTH_ENABLED=true" \
  --set-env-vars="OPENCLAW_ALLOWED_ORIGINS=https://app.kaiju.digital" \
  --update-secrets="OPENCLAW_API_KEYS=openclaw-api-keys:latest" \
  --update-secrets="N8N_ADS_WEBHOOK_URL=n8n-ads-webhook-url:latest" \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1
```

> Cloud Run sets `PORT` automatically. The container CMD uses `${PORT:-8100}` and will pick it up correctly.

---

## 8. Environment Variables in Cloud Run

Non-secret variables are set via `--set-env-vars`. Secrets are referenced from Secret Manager via `--update-secrets`.

Full variable reference: [docs/ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)

| Variable | Source in Cloud Run |
|---|---|
| `OPENCLAW_ENV` | `--set-env-vars` |
| `OPENCLAW_API_AUTH_ENABLED` | `--set-env-vars` |
| `OPENCLAW_API_KEYS` | Secret Manager via `--update-secrets` |
| `OPENCLAW_ALLOWED_ORIGINS` | `--set-env-vars` |
| `OPENCLAW_DEFAULT_TENANT` | `--set-env-vars` |
| `OPENCLAW_REQUIRE_TENANT_HEADER` | `--set-env-vars` |
| `OPENCLAW_AUDIT_ENABLED` | `--set-env-vars` |
| `MEMORY_ENABLED` | `--set-env-vars` |
| `N8N_ADS_WEBHOOK_URL` | Secret Manager via `--update-secrets` |
| `N8N_WEBHOOK_TIMEOUT` | `--set-env-vars` |
| `PORT` | Set automatically by Cloud Run |

---

## 9. Secret Management

```bash
# Create secrets (one-time)
echo -n "key1,key2" | gcloud secrets create openclaw-api-keys --data-file=-
echo -n "https://flows.kaiju.digital/webhook/ads-agent-demo" \
  | gcloud secrets create n8n-ads-webhook-url --data-file=-

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding openclaw-api-keys \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

Rules:
- Never store secrets in the repository
- Never store secrets in MemPalace memory files
- Never log secrets — audit log must not include `Authorization` headers or raw payloads
- Rotate secrets via Secret Manager versions; update Cloud Run to reference `latest`

---

## 10. Health and Readiness Endpoint

Cloud Run uses `GET /openclaw/health` for startup probes:

```bash
curl https://SERVICE_URL/openclaw/health
# Expected: {"ok": true, "service": "kaiju-openclaw", "status": "healthy"}
```

Configure in Cloud Run:

```bash
gcloud run services update ${SERVICE_NAME} \
  --region=${REGION} \
  --startup-cpu-boost \
  --health-check-path=/openclaw/health
```

---

## 11. Production Gaps (Must Resolve Before Public Launch)

| Gap | Current State | Required For Production |
|---|---|---|
| MemPalace storage | Local container filesystem | Firestore / Cloud Storage |
| Audit log | Local JSONL file | Cloud Logging or BigQuery |
| Auth | API key placeholder (env var) | Proper Secret Manager integration |
| Rate limiting | Not implemented | Per-tenant quota enforcement |
| Tenant database | Not implemented | Firestore / Cloud SQL |
| Google Ads API | n8n fixture/webhook | Direct API integration |
| Multi-region | Not planned | Cloud Run multi-region traffic |

---

## 12. Recommended Phased Deployment

| Phase | Scope |
|---|---|
| **Phase 1** | Internal Cloud Run smoke deployment — team-only, API key protected, local memory/audit still used |
| **Phase 2** | API key protected staging endpoint — external testers, Secret Manager wired |
| **Phase 3** | Audit externalized to Cloud Logging or BigQuery |
| **Phase 4** | Memory externalized to Firestore or Cloud Storage |
| **Phase 5** | Tenant database, real auth/credential store, production GA |

---

## 13. Rollback Strategy

1. Cloud Run preserves previous revisions automatically
2. Tag releases: `gcloud run services update-traffic --to-revisions=REVISION=100`
3. Monitor health endpoint after each deploy
4. If `/openclaw/health` fails: roll back traffic immediately
5. Keep at least the previous two revisions live

```bash
# List revisions
gcloud run revisions list --service=${SERVICE_NAME} --region=${REGION}

# Roll back to a specific revision
gcloud run services update-traffic ${SERVICE_NAME} \
  --region=${REGION} \
  --to-revisions=REVISION_NAME=100
```

---

## 14. Post-Deploy Smoke Tests

```bash
SERVICE_URL=https://SERVICE_URL_FROM_CLOUD_RUN

# Health check
curl ${SERVICE_URL}/openclaw/health

# Process request (auth disabled staging)
curl -s -X POST ${SERVICE_URL}/openclaw/process \
  -H "Content-Type: application/json" \
  -d '{"client_id":"smoke-client","agent":"ads-agent","request":"summary"}'

# Auth enabled — valid key
curl -s -X POST ${SERVICE_URL}/openclaw/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{"client_id":"smoke-client","agent":"ads-agent","request":"summary"}'

# Auth enabled — invalid key (expect 401)
curl -si -X POST ${SERVICE_URL}/openclaw/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer wrong-key" \
  -d '{"client_id":"smoke-client","agent":"ads-agent","request":"summary"}'

# CORS preflight
curl -si -X OPTIONS ${SERVICE_URL}/openclaw/process \
  -H "Origin: https://app.kaiju.digital" \
  -H "Access-Control-Request-Method: POST"
```

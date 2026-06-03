# Kaiju Command Center

AI agent lab for Kaiju Digital.

## Current milestone

**V5 beta — Tenant Credentials & Secure Onboarding Foundation** — tag: `v5.0.0-beta`

V5 establishes the full credential management foundation for multi-tenant Google Ads integrations. Included: `CredentialReference` model, `CredentialStore` abstraction, `LocalFileCredentialReferenceStore`, OpenClaw admin GET/POST credential endpoints, credential resolver bridge, `SecretStore` abstraction, Google Ads `CredentialProvider`, adapter `GOOGLE_ADS_CREDENTIAL_SOURCE` feature flag, and V5 credential chain smoke test. No credentials are stored in Git, returned in API responses, written to audit logs, or surfaced in MemPalace. Default adapter behavior (`ADS_DATA_SOURCE=n8n_demo`, `GOOGLE_ADS_LIVE_ENABLED=false`) is unchanged. Next: `v5.12-gcp-secret-manager` or `v5.12-frontend-onboarding`.

## Architecture

```
Demo Client (HTTP POST)
    ↓
Router HTTP Server  (FastAPI · localhost:8000)
    ↓
Router Core         (route_request · validation · dispatch)
    ↓
Ads Agent           (n8n_client · request type routing)
    ↓
n8n Webhook         (flows.kaiju.digital · production)
    ↓
JSON Response
```

## Quick start

**1. Start the Router server**

```bash
cd ~/kaiju/agents/router
~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

**2. Run the Demo Client**

```bash
cd ~/kaiju/projects/demo-client
~/kaiju/.venv/bin/python3 client.py summary
~/kaiju/.venv/bin/python3 client.py cpa
~/kaiju/.venv/bin/python3 client.py conversions
~/kaiju/.venv/bin/python3 client.py raw
```

**3. Run the interactive chat client**

```bash
~/kaiju/.venv/bin/python3 chat_client.py
```

## Documentation

- [V0 Architecture](docs/V0_ARCHITECTURE.md)
- [V0 Runbook](docs/V0_RUNBOOK.md)
- [Roadmap](docs/ROADMAP.md)

## Roadmap summary

| Version | Focus | Status |
|---|---|---|
| V0 | Ads Agent · Router · n8n · Demo Client | **Complete** — `v0.0.1` |
| V1 | LangGraph · stateful analysis | **Complete** — `v1.4.1` |
| V2 | MemPalace · persistent client memory | **Beta complete** — `v2.0.0-beta` |
| V3 | OpenClaw · HTTP API · tenant context · audit log | **Alpha complete** — `v3.0.0-alpha` |
| V3.5 | Config · auth placeholder · CORS · Docker · GCP plan | **Beta complete** — `v3.5.0-beta` |
| V4 | Real integrations · Google Ads API · data source resolver | **Beta complete** — `v4.0.0-beta` |
| V4.5.1 | Live Google Ads read-only fetch · GAQL · credential safety gates | **Alpha** — `v4.5.1-alpha` |
| V5 | Tenant credentials · secure onboarding · secret store · OAuth | **Beta complete** — `v5.0.0-beta` |

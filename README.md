# Kaiju Command Center

AI agent lab for Kaiju Digital.

## Current milestone

**V5.13 — Manual GCP Validation complete** (branch: `v5.13-manual-gcp-validation` · tag candidate: `v5.13.0-beta`)

V5.13 validated `GCPSecretManagerStore` against a real GCP project. All six phases (config, write, read, list, delete, provider composition) passed using fake Google Ads values only — no real credentials, no live API calls, no fixed-cost infrastructure. Temporary test secrets were deleted. Smoke suites pass. Ready for merge and tag.

See [V5.13 Branch Closure](docs/V5_13_BRANCH_CLOSURE.md), [v5.13.0-beta Release Notes](docs/RELEASE_NOTES_V5_13_0_BETA.md), [Validation Results](docs/V5_13_LIVE_GCP_VALIDATION_RESULTS.md), and [Runbook](docs/GCP_SECRET_MANAGER_RUNBOOK.md).

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
- [V5.12 Release Notes](docs/V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [GCP Secret Manager Runbook](docs/GCP_SECRET_MANAGER_RUNBOOK.md)
- [V5.13 Branch Closure](docs/V5_13_BRANCH_CLOSURE.md)
- [v5.13.0-beta Release Notes](docs/RELEASE_NOTES_V5_13_0_BETA.md)
- [V5.13 Manual GCP Validation Plan](docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md)
- [V5.13 Live GCP Validation Results](docs/V5_13_LIVE_GCP_VALIDATION_RESULTS.md)

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
| V5.12 | GCP Secret Manager backend · `GCPSecretManagerStore` · IAM · rotation | **Beta complete** — `v5.12.0-beta` |
| V5.13 | Live GCP validation · Phases A–F PASS · provider composition confirmed | **Beta complete** — `v5.13.0-beta` (tag candidate) |

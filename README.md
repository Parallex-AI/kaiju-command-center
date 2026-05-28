# Kaiju Command Center

AI agent lab for Kaiju Digital.

## Current milestone

**V3 OpenClaw alpha complete** — tag `v3.0.0-alpha`

V3.1–V3.4 are implemented and tested: OpenClaw local orchestrator, FastAPI HTTP server (port 8100), tenant context enrichment with HTTP header propagation, and an append-only JSONL audit log. Three dedicated smoke test suites (core, HTTP, audit). V3.5 SaaS and GCP production are next.

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
| V1 | LangGraph · stateful analysis | **Complete** — `v1.4.1-n8n-resilience` |
| V2 | MemPalace · persistent client memory | **Beta complete** — `v2-mempalace` |
| V3 | OpenClaw · SaaS · multi-tenant · GCP production | **Alpha complete** — `v3.0.0-alpha` |

# Kaiju Command Center — V0 Architecture

## Project

**Kaiju Command Center** is an AI agent lab built by Kaiju Digital. It provides a structured pipeline for dispatching client requests to specialized AI agents that analyze marketing performance data and return actionable insights.

## V0 Architecture diagram

```
┌─────────────────────────────────────────────────┐
│  Demo Client                                    │
│  projects/demo-client/client.py                 │
│  projects/demo-client/chat_client.py            │
│                                                 │
│  HTTP POST /route                               │
│  Payload: { client_id, agent, request }         │
└────────────────────┬────────────────────────────┘
                     │ http://localhost:8000/route
                     ▼
┌─────────────────────────────────────────────────┐
│  Router HTTP Server                             │
│  agents/router/server.py                        │
│                                                 │
│  GET  /health                                   │
│  GET  /                                         │
│  POST /route  →  route_request(payload)         │
│                                                 │
│  Framework: FastAPI + uvicorn                   │
└────────────────────┬────────────────────────────┘
                     │ in-process function call
                     ▼
┌─────────────────────────────────────────────────┐
│  Router Core                                    │
│  agents/router/router.py                        │
│                                                 │
│  - Validates payload                            │
│  - Checks agent is supported                   │
│  - Checks request type is valid                │
│  - Dispatches to correct agent                 │
│  - Returns ok:true / ok:false envelope          │
└────────────────────┬────────────────────────────┘
                     │ in-process function call
                     ▼
┌─────────────────────────────────────────────────┐
│  Ads Agent                                      │
│  agents/ads-agent/n8n_client.py                 │
│                                                 │
│  fetch_ads_data_from_n8n(client_id, request)    │
│                                                 │
│  - Validates request_type                       │
│  - Builds webhook payload                       │
│  - Handles HTTP errors + non-JSON responses     │
└────────────────────┬────────────────────────────┘
                     │ HTTPS POST
                     ▼
┌─────────────────────────────────────────────────┐
│  n8n Production Webhook                         │
│  https://flows.kaiju.digital/webhook/           │
│                 ads-agent-demo                  │
│                                                 │
│  Branches by request type                       │
│  Returns structured JSON                        │
└────────────────────┬────────────────────────────┘
                     │ JSON response
                     ▼
                 Client receives
               structured response

```

## Layer descriptions

### Demo Client
`projects/demo-client/client.py` and `chat_client.py`

The entry point of the V0 flow. Sends an HTTP POST to the Router server with a structured payload. Supports CLI mode (one request, print and exit) and chat mode (interactive loop). Does not call the Ads Agent or n8n directly — all requests go through the Router.

### Router HTTP Server
`agents/router/server.py`

A minimal FastAPI application. Exposes `/health`, `/` (metadata), and `/POST /route`. Parses the JSON body and delegates entirely to `route_request()`. Contains no business logic. Returns structured JSON for all outcomes including errors.

### Router Core
`agents/router/router.py`

The routing and validation layer. Validates the payload type, checks the agent against the supported list, checks the request type against the valid set, dispatches to the correct agent fetch function, and wraps the result in a consistent `ok: true / ok: false` envelope.

### Ads Agent
`agents/ads-agent/n8n_client.py`

Handles the outbound call to n8n. Validates the request type, builds the webhook payload, and makes the HTTP POST. Has named error handlers for connection errors, timeouts, HTTP errors, and non-JSON responses.

### n8n Webhook
`https://flows.kaiju.digital/webhook/ads-agent-demo`

A production n8n workflow maintained manually in the n8n UI. Receives the payload, branches by the `request` field, and returns request-type-specific JSON. Managed by the operator — not modified by code.

> **Note:** The `/webhook-test/` URL is a temporary n8n test endpoint and must never be used by agent code.

## Supported agent

| Agent | File | Status |
|---|---|---|
| `ads-agent` | `agents/ads-agent/n8n_client.py` | Active |

## Supported request types

| Type | Description |
|---|---|
| `summary` | Full campaign metrics: spend, conversions, clicks, impressions, CPA, executive summary |
| `cpa` | Spend, conversions, and computed CPA |
| `conversions` | Campaign name and conversion count only |
| `raw` | Full unfiltered JSON envelope from n8n |

## Data flow

```
client_id: "demo-client"
agent:     "ads-agent"
request:   "summary"

→ Router validates → dispatches → n8n returns →

{
  "ok": true,
  "router": "kaiju-command-center-router",
  "agent": "ads-agent",
  "client_id": "demo-client",
  "request": "summary",
  "data": {
    "campaign": "Demo Google Ads Campaign",
    "spend": 125000,
    "conversions": 62,
    "clicks": 3100,
    "impressions": 85000,
    "currency": "ARS",
    "cpa": 2016.13
  }
}
```

## Current limitations

| Area | Status |
|---|---|
| OpenClaw gateway | Not implemented — client calls Router directly |
| LangGraph | Not implemented — agent logic is stateless |
| MemPalace / persistent memory | Not implemented |
| SaaS / auth / multi-tenant | Not implemented |
| Real Google Ads or GA4 API | Not implemented — n8n returns fixture data |
| Docker production deployment | Not implemented — local only |
| Multiple agents | Not implemented — only `ads-agent` |

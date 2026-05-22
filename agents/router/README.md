# Router

The Router receives incoming client requests, validates them, and dispatches them to the appropriate agent.

## Architecture Position

```
Client → Router → Agent → n8n → Response
```

> OpenClaw (the public-facing gateway) is not yet implemented. The Router is currently called directly.

## Responsibilities

- Validate incoming request payload
- Identify target agent from the `agent` field
- Validate request type
- Dispatch to the correct agent's data fetch function
- Return a structured `ok: true / ok: false` response

## Supported Agents

| Agent | Status |
|---|---|
| `ads-agent` | Active |

## Supported Request Types

| Type | Description |
|---|---|
| `summary` | Full campaign metrics and executive summary |
| `cpa` | Spend, conversions, and CPA |
| `conversions` | Campaign name and conversion count |
| `raw` | Raw JSON from n8n |

## Request Payload

```json
{
  "client_id": "demo-client",
  "agent": "ads-agent",
  "request": "summary"
}
```

## Response — success

```json
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
    "currency": "ARS"
  }
}
```

## Response — error

```json
{
  "ok": false,
  "error": "unsupported_agent",
  "message": "Unsupported agent: unknown-agent",
  "supported_agents": ["ads-agent"]
}
```

## CLI Demo

```bash
cd ~/kaiju/agents/router
python3 run_router_demo.py              # defaults to summary
python3 run_router_demo.py summary
python3 run_router_demo.py cpa
python3 run_router_demo.py conversions
python3 run_router_demo.py raw
```

## Chat Demo (Spanish)

```bash
cd ~/kaiju/agents/router
python3 chat_router_demo.py
```

Available commands: `Resumen`, `CPA`, `Conversiones`, `Raw`, `JSON`, `¿Cómo viene la campaña?`, `salir`

All commands are routed through `route_request()` — no direct calls to the Ads Agent.

## HTTP Server

The Router exposes a local HTTP API via FastAPI.

### Dependencies

```bash
sudo apt install python3-pip        # if pip is not available
pip3 install -r requirements.txt    # fastapi, uvicorn, requests
```

### Start the server

```bash
cd ~/kaiju/agents/router
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

> This is for local development only. The server is not production-hardened.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Service metadata |
| `GET` | `/health` | Health check |
| `POST` | `/route` | Dispatch a request to an agent |

### Health check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"ok": true, "service": "kaiju-command-center-router", "status": "healthy"}
```

### Route requests

```bash
# summary
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"summary"}'

# cpa
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"cpa"}'

# conversions
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"conversions"}'

# raw
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"raw"}'
```

### Error path tests

```bash
# unsupported agent
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"analytics-agent","request":"summary"}'

# unsupported request type
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"client_id":"demo-client","agent":"ads-agent","request":"invalid"}'
```

Both return structured `ok: false` JSON — no server 500.

## Status

V0 — Router functional with CLI, chat, and HTTP API.
Dispatches to Ads Agent via n8n production webhook.
OpenClaw gateway not yet implemented.

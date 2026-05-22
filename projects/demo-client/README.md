# Demo Client

HTTP client that sends requests to the Kaiju Router and displays responses. This is the entry point of the V0 end-to-end flow.

## Architecture

```
Demo Client → Router HTTP server → Router → Ads Agent → n8n → response
```

## Requirement: Router server must be running

Start the Router server before using this client:

```bash
cd ~/kaiju/agents/router
~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Leave it running in a terminal. The client connects to `http://localhost:8000/route` by default.

## CLI client

```bash
cd ~/kaiju/projects/demo-client

~/kaiju/.venv/bin/python3 client.py              # defaults to summary
~/kaiju/.venv/bin/python3 client.py summary
~/kaiju/.venv/bin/python3 client.py cpa
~/kaiju/.venv/bin/python3 client.py conversions
~/kaiju/.venv/bin/python3 client.py raw
```

## Chat client (Spanish/English)

```bash
cd ~/kaiju/projects/demo-client
~/kaiju/.venv/bin/python3 chat_client.py
```

Available commands: `resumen`, `summary`, `cpa`, `conversiones`, `conversions`, `raw`, `json`, `salir`

## Supported request types

| Type | Description |
|---|---|
| `summary` | Full campaign metrics and executive summary |
| `cpa` | Spend, conversions, and CPA |
| `conversions` | Campaign name and conversion count |
| `raw` | Raw JSON from n8n via Router |

## Environment variable override

To point the client at a different Router instance:

```bash
export KAIJU_ROUTER_URL=http://other-host:8000/route
~/kaiju/.venv/bin/python3 client.py summary
```

## Example payload

```json
{
  "client_id": "demo-client",
  "agent": "ads-agent",
  "request": "summary"
}
```

## Example response

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
    "currency": "ARS",
    "cpa": 2016.13
  }
}
```

## Current limitations

- Local V0 demo only. Not production-hardened.
- Client ID and agent are fixed to `demo-client` / `ads-agent`.
- No authentication. No TLS.
- OpenClaw gateway is not yet implemented — the client calls the Router directly.

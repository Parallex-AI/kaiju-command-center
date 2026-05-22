# Kaiju Command Center — V0 Runbook

Operational guide for running the V0 stack locally.

## Prerequisites

- WSL2 with Python 3.12
- `.venv` created at `~/kaiju/.venv` with FastAPI, uvicorn, and requests installed
- n8n production webhook accessible at `https://flows.kaiju.digital/webhook/ads-agent-demo`

To verify the venv:
```bash
~/kaiju/.venv/bin/python3 -c "import fastapi, uvicorn, requests; print('OK')"
```

---

## 1. Start the Router HTTP server

The Router server must be running before using the Demo Client or running HTTP tests.

```bash
cd ~/kaiju/agents/router
~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Leave this running in a terminal. The server listens on `http://0.0.0.0:8000`.

---

## 2. Health check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"ok": true, "service": "kaiju-command-center-router", "status": "healthy"}
```

---

## 3. Route tests via curl

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

---

## 4. Demo Client — CLI mode

The Router server must be running.

```bash
cd ~/kaiju/projects/demo-client

~/kaiju/.venv/bin/python3 client.py              # defaults to summary
~/kaiju/.venv/bin/python3 client.py summary
~/kaiju/.venv/bin/python3 client.py cpa
~/kaiju/.venv/bin/python3 client.py conversions
~/kaiju/.venv/bin/python3 client.py raw
```

To point the client at a different Router instance:
```bash
export KAIJU_ROUTER_URL=http://other-host:8000/route
~/kaiju/.venv/bin/python3 client.py summary
```

---

## 5. Demo Client — chat mode

```bash
cd ~/kaiju/projects/demo-client
~/kaiju/.venv/bin/python3 chat_client.py
```

Available commands: `resumen`, `summary`, `cpa`, `conversiones`, `conversions`, `raw`, `json`, `salir`

---

## 6. Router CLI demos (no HTTP server required)

These call `route_request()` directly, bypassing the HTTP layer.

```bash
cd ~/kaiju/agents/router

~/kaiju/.venv/bin/python3 run_router_demo.py summary
~/kaiju/.venv/bin/python3 run_router_demo.py cpa
~/kaiju/.venv/bin/python3 run_router_demo.py conversions
~/kaiju/.venv/bin/python3 run_router_demo.py raw
```

Interactive:
```bash
~/kaiju/.venv/bin/python3 chat_router_demo.py
```

---

## 7. Ads Agent n8n demos (no Router required)

These call `fetch_ads_data_from_n8n()` directly, bypassing the Router.

```bash
cd ~/kaiju/agents/ads-agent

~/kaiju/.venv/bin/python3 run_n8n_demo.py summary
~/kaiju/.venv/bin/python3 run_n8n_demo.py cpa
~/kaiju/.venv/bin/python3 run_n8n_demo.py conversions
~/kaiju/.venv/bin/python3 run_n8n_demo.py raw
```

Interactive (Spanish):
```bash
~/kaiju/.venv/bin/python3 chat_n8n_demo.py
```

---

## 8. Ads Agent local demo (no n8n required)

Uses the local fixture `projects/demo-client/demo-data.json`. No network required.

```bash
cd ~/kaiju/agents/ads-agent
python3 run_demo.py
python3 chat_demo.py
```

---

## 9. Failure mode test

Verify the client fails gracefully when the Router is unavailable.

1. Stop the Router server (Ctrl+C in its terminal)
2. Run:
   ```bash
   cd ~/kaiju/projects/demo-client
   ~/kaiju/.venv/bin/python3 client.py summary
   ```
3. Expected output:
   ```
   Router server is not available. Start it with:
     cd ~/kaiju/agents/router
     ~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
   ```
   No traceback. Clean exit.

---

## 10. Run full V0 smoke test

Runs all checks in sequence: venv, dependencies, Router server (starts it if needed), HTTP routes, Demo Client, and CLI regressions. Stops the server after the run if it started it.

```bash
cd ~/kaiju
./scripts/smoke_test_v0.sh
```

Expected final line: `=== V0 smoke test passed. ===`

---

## Notes

- **n8n webhook:** Always use the production URL `https://flows.kaiju.digital/webhook/ads-agent-demo`. The `/webhook-test/` URL is temporary and must never appear in agent code.
- **Virtual environment:** `.venv/` lives at `~/kaiju/.venv` and is ignored by Git. It must be activated or referenced by full path — it is not a system-wide install.
- **Server persistence:** The uvicorn process is not daemonized. If the terminal closes, the server stops. There is no process manager in V0.
- **n8n workflow:** The n8n workflow is maintained manually in the n8n UI. Do not attempt to edit it via API or code.

# Ads Agent

The Ads Agent is responsible for analyzing Google Ads performance data and generating actionable recommendations for clients.

## Responsibilities

- Ingest and interpret Google Ads metrics (spend, conversions, CPA, ROAS)
- Detect anomalies and performance trends
- Generate optimization recommendations
- Respond to client queries about campaign performance

## Inputs

- Campaign metrics from Google Ads (via n8n or direct API)
- Client memory context (from `memory/client-memory`)
- Router instructions

## Outputs

- Structured analysis report
- Optimization recommendations
- Natural language response to client

## Architecture Position

```
Router → Ads Agent → Response
```

## Local Demo

Runs against a local JSON fixture at `projects/demo-client/demo-data.json`. Does not require n8n.

```bash
cd ~/kaiju/agents/ads-agent
python3 run_demo.py
python3 chat_demo.py
```

## n8n Webhook Integration

The agent fetches live campaign data from an n8n workflow via HTTP webhook.

**Production webhook URL:**
```
https://flows.kaiju.digital/webhook/ads-agent-demo
```

**Environment variable override (optional):**
```bash
export N8N_ADS_WEBHOOK_URL=https://flows.kaiju.digital/webhook/ads-agent-demo
```

### Supported request types

| Type | Description |
|---|---|
| `summary` | Full campaign metrics and executive summary |
| `cpa` | Spend, conversions, and CPA only |
| `conversions` | Campaign name and conversion count only |
| `raw` | Raw JSON returned by n8n, formatted with indentation |

### curl examples

```bash
# summary
curl -X POST https://flows.kaiju.digital/webhook/ads-agent-demo \
  -H "Content-Type: application/json" \
  -d '{"client_id": "demo-client", "agent": "ads-agent", "request": "summary"}'

# cpa
curl -X POST https://flows.kaiju.digital/webhook/ads-agent-demo \
  -H "Content-Type: application/json" \
  -d '{"client_id": "demo-client", "agent": "ads-agent", "request": "cpa"}'

# conversions
curl -X POST https://flows.kaiju.digital/webhook/ads-agent-demo \
  -H "Content-Type: application/json" \
  -d '{"client_id": "demo-client", "agent": "ads-agent", "request": "conversions"}'

# raw
curl -X POST https://flows.kaiju.digital/webhook/ads-agent-demo \
  -H "Content-Type: application/json" \
  -d '{"client_id": "demo-client", "agent": "ads-agent", "request": "raw"}'
```

### Run the n8n report demo

```bash
cd ~/kaiju/agents/ads-agent
python3 run_n8n_demo.py              # defaults to summary
python3 run_n8n_demo.py summary
python3 run_n8n_demo.py cpa
python3 run_n8n_demo.py conversions
python3 run_n8n_demo.py raw
```

### Run the n8n chat demo (Spanish)

```bash
cd ~/kaiju/agents/ads-agent
python3 chat_n8n_demo.py
```

Available chat commands: `CPA`, `Conversiones`, `Resumen`, `¿Cómo viene la campaña?`, `Raw`, `JSON`, `salir`

> **Note:** The `/webhook-test/` URL is a temporary n8n test endpoint. The agent must always use `/webhook/ads-agent-demo` (production). Never use `/webhook-test/` in Python agent code.

## V1 LangGraph Graph Demo

The graph demo runs a multi-step LangGraph `StateGraph` through the Ads Agent pipeline: validate → fetch → normalize → analyze → recommend → format. It is isolated and does not affect the Router or any V0 path.

**Dependency install (into `.venv`):**
```bash
~/kaiju/.venv/bin/python3 -m pip install langgraph
```

Or install from the requirements file:
```bash
~/kaiju/.venv/bin/pip install -r ~/kaiju/agents/ads-agent/requirements.txt
```

**Run the graph demo:**
```bash
cd ~/kaiju/agents/ads-agent

~/kaiju/.venv/bin/python3 run_graph_demo.py              # defaults to summary
~/kaiju/.venv/bin/python3 run_graph_demo.py summary
~/kaiju/.venv/bin/python3 run_graph_demo.py cpa
~/kaiju/.venv/bin/python3 run_graph_demo.py conversions
~/kaiju/.venv/bin/python3 run_graph_demo.py raw
```

The graph response envelope includes `execution_mode: "graph"`, `metrics`, `analysis`, and `recommendations` for `summary`; focused subsets for `cpa` and `conversions`; and the raw n8n payload for `raw`.

> The legacy scripts `run_n8n_demo.py` and `chat_n8n_demo.py` are unchanged and continue to work independently of the graph.

## n8n Client Resilience

The n8n client (`n8n_client.py`) retries transient network failures automatically.

| Behavior | Detail |
|---|---|
| Attempts | 3 |
| Backoff | 1s after attempt 1, 2s after attempt 2 |
| Retries on | `Timeout`, `ConnectionError`, other request errors without an HTTP response |
| Does not retry | HTTP errors (4xx / 5xx) |
| Retry logging | Each non-final failure prints a timestamped line to stderr |

**Configurable timeout:**

```bash
# Default is 15 seconds. Override with:
export N8N_WEBHOOK_TIMEOUT=30

# Or inline:
N8N_WEBHOOK_TIMEOUT=30 python3 run_n8n_demo.py summary
```

If `N8N_WEBHOOK_TIMEOUT` is missing, invalid, zero, or negative, the client falls back to 15 seconds.

## Status

V1.4.1 complete. n8n client resilience hotfix merged into master (branch: `v1.4.1-n8n-resilience`).

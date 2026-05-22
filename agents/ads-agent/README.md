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

**curl test:**
```bash
curl -X POST https://flows.kaiju.digital/webhook/ads-agent-demo \
  -H "Content-Type: application/json" \
  -d '{"client_id": "demo-client", "agent": "ads-agent", "request": "summary"}'
```

**Run the n8n report demo:**
```bash
cd ~/kaiju/agents/ads-agent
python3 run_n8n_demo.py
```

**Run the n8n chat demo (Spanish):**
```bash
cd ~/kaiju/agents/ads-agent
python3 chat_n8n_demo.py
```

Available chat commands: `CPA`, `Conversiones`, `Resumen`, `¿Cómo viene la campaña?`, `salir`

> **Note:** The `/webhook-test/` URL is a temporary n8n test endpoint. The agent must always use `/webhook/ads-agent-demo` (production). Never use `/webhook-test/` in Python agent code.

## Status

MVP complete with local demo and n8n webhook integration.

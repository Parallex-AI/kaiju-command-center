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

## Status

MVP — structure only. No code yet.

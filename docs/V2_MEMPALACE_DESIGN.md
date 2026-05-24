# Kaiju Command Center — V2 MemPalace Design

**Branch:** `v2-mempalace`  
**Status:** Design / Pre-implementation

---

## 1. Purpose

V2 introduces a persistent memory layer — MemPalace — for client-specific campaign context. It stores historical analysis, previous recommendations, recurring insights, and trend data so that the Ads Agent Graph can reason across sessions rather than treating every request as isolated.

MemPalace does **not** replace:
- n8n — the live data source
- LangGraph — the execution framework
- Router — the HTTP dispatch layer
- Ads Agent — the agent logic

It **augments** the Ads Agent Graph with historical context, enabling trend detection, recommendation tracking, and continuity between runs.

---

## 2. What MemPalace Is

MemPalace is a **local-first memory subsystem** for V2. It is:

| Property | Detail |
|---|---|
| **Client-scoped** | Each client has an isolated memory directory |
| **Agent-aware** | Memory is organized per agent (e.g. `ads-agent/`) |
| **Structured** | Fixed JSON/JSONL schemas per memory type |
| **Append-friendly** | New data is appended, not destructively overwritten |
| **Inspectable** | Plain files, readable with any text editor or `jq` |
| **Locally safe** | No external service required in V2 |
| **SaaS-compatible** | Directory-per-client design maps directly to future GCP bucket paths or database tenant isolation |

---

## 3. Target V2 Architecture

### Current (V1.4.1)

```
Client
  ↓
Router HTTP Server
  ↓
Router Core
  ↓
Ads Agent Graph (LangGraph StateGraph)
  ↓
n8n Client  →  n8n production webhook
  ↓
Analysis + Recommendations + Executive Summary
  ↓
Router response
```

### Target (V2)

```
Client
  ↓
Router HTTP Server
  ↓
Router Core
  ↓
Ads Agent Graph (LangGraph StateGraph)
  ↓
Memory Load Node      ← reads profile + recent snapshots
  ↓
n8n Tool Node         ← fetches live metrics
  ↓
Analysis Node         ← enriched with historical context
  ↓
Recommendation Node   ← detects recurring vs. new issues
  ↓
Memory Write Node     ← writes snapshot + recommendations + insights
  ↓
Response Formatter
  ↓
Router response
```

---

## 4. Memory Scope

### What to store

| Category | Fields |
|---|---|
| Client profile | client_id, display_name, timezone, currency, business_goal, default_cpa_target, notes |
| Campaign snapshots | timestamp, metrics, analysis, recommendations, executive_summary |
| Recommendation history | recommendation_id, type, severity, status (open/accepted/rejected/resolved/ignored) |
| Insights | insight_type, summary, evidence |
| Timestamps | ISO 8601 UTC on every write |
| Agent name | e.g. `ads-agent` |
| Request type | summary, cpa, conversions, raw |

### What NOT to store

- API credentials or OAuth tokens
- Raw secrets of any kind
- Full raw n8n payloads (unless explicitly enabled via `MEMORY_STORE_RAW_PAYLOADS=true`)
- Private user data unrelated to campaign performance
- Personally identifiable information (PII)

---

## 5. Initial Storage Strategy

For V2 local-first operation, all memory is stored as files under:

```
memory/client-memory/
```

### Proposed directory structure

```
memory/client-memory/
  demo-client/
    profile.json
    ads-agent/
      snapshots/
        2026-05-22T16-30-00Z_summary.json
        2026-05-23T09-15-00Z_summary.json
      recommendations.jsonl
      insights.jsonl
      latest_summary.json
```

### Why files, not a database

| Reason | Detail |
|---|---|
| Easy to inspect | `cat`, `jq`, any editor — no query language needed |
| Zero setup friction | No database install or credentials required locally |
| Works offline | No external service dependency |
| Migratable | File paths map cleanly to GCP Cloud Storage keys or DB table keys later |
| Auditable | Plain-text history is trivially version-controllable for debugging |

---

## 6. Memory File Formats

### `profile.json`

```json
{
  "client_id": "demo-client",
  "display_name": "Demo Client",
  "timezone": "America/Argentina/Buenos_Aires",
  "currency": "ARS",
  "business_goal": "Lead generation",
  "default_cpa_target": 2000.0,
  "notes": ""
}
```

### Snapshot JSON (one file per run)

Filename: `{timestamp}_{request_type}.json`

```json
{
  "timestamp": "2026-05-22T16:30:00Z",
  "client_id": "demo-client",
  "agent": "ads-agent",
  "request_type": "summary",
  "metrics": { "...": "..." },
  "analysis": { "...": "..." },
  "recommendations": [ "..." ],
  "executive_summary": { "...": "..." }
}
```

### `recommendations.jsonl`

One JSON object per line. Appended on each write.

```json
{"timestamp": "2026-05-22T16:30:00Z", "recommendation_id": "abc123", "type": "optimization", "severity": "high", "priority": "high", "area": "CPA Efficiency", "action": "Review targeting and placements", "expected_impact": "Reduce CPA toward target range", "rationale": "CPA of 4800 ARS exceeds 4000 ARS threshold.", "status": "open"}
```

### `insights.jsonl`

One JSON object per line. Appended on each write.

```json
{"timestamp": "2026-05-22T16:30:00Z", "insight_type": "trend", "summary": "CPA has improved 12% over the last 3 runs.", "evidence": {"previous_cpa": 2280.0, "current_cpa": 2016.13}}
```

### `latest_summary.json`

Always overwritten with the most recent full analysis result for quick loading without scanning snapshots.

---

## 7. Ads Graph Integration Points

### Proposed new nodes

#### `load_client_memory`

- Reads `profile.json` for the current `client_id`
- Loads the most recent N snapshots (controlled by `MEMORY_MAX_RECENT_SNAPSHOTS`)
- Reads `latest_summary.json` if it exists
- Stores all loaded data in `state["memory_context"]`
- If memory directory does not exist or memory is disabled: stores `None`, continues without error

#### `compare_with_history`

- Compares current metrics with previous snapshots
- Identifies trend direction (improving / stable / degrading) for CPA, CTR, conversion rate
- Flags recurring issues (same recommendation appearing across N consecutive runs)
- Stores result in `state["historical_comparison"]`

#### `write_memory`

- Writes current snapshot as a new file in `snapshots/`
- Appends new recommendations to `recommendations.jsonl`
- Appends new insights to `insights.jsonl`
- Overwrites `latest_summary.json`
- If write fails: logs warning to stderr, does not crash the graph
- Stores outcome in `state["memory_write_result"]`

### Proposed `AdsAgentState` additions

```python
class AdsAgentState(TypedDict):
    # ... existing fields ...
    memory_context: dict          # loaded from MemPalace; None if disabled/missing
    historical_comparison: dict   # trend and recurrence analysis
    memory_write_result: dict     # success/failure of memory write
```

---

## 8. Request Type Behavior with Memory

| Request | Load memory | Compare history | Write memory |
|---|---|---|---|
| `summary` | Full profile + recent snapshots | Full comparison | Full snapshot + recommendations + insights |
| `cpa` | Profile + recent CPA history | CPA trend only | CPA snapshot |
| `conversions` | Profile + recent conversion history | Conversion trend only | Conversion snapshot |
| `raw` | No (skip by default) | No | No (unless `MEMORY_STORE_RAW_PAYLOADS=true`) |

---

## 9. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MEMORY_ROOT` | `memory/client-memory` | Root directory for all client memory |
| `MEMORY_ENABLED` | `true` | Set to `false` to disable all memory reads and writes |
| `MEMORY_STORE_RAW_PAYLOADS` | `false` | Set to `true` to write raw n8n payloads to memory |
| `MEMORY_MAX_RECENT_SNAPSHOTS` | `5` | Number of recent snapshots to load for historical comparison |

All variables are optional. The graph must run correctly with none of them set.

---

## 10. Privacy and Safety Principles

- All memory is stored under `{MEMORY_ROOT}/{client_id}/` — paths are client-scoped and never cross-contaminate
- No secrets, OAuth tokens, or credentials may be written to memory files
- PII unrelated to campaign performance must not be stored
- Local memory files should be excluded from accidental public commits via `.gitignore`
- Future SaaS deployment must enforce tenant-level directory isolation (one bucket prefix per tenant)
- Encryption at rest should be considered before any production multi-tenant deployment
- Memory writes must be deterministic and inspectable — no opaque binary formats in V2

---

## 11. Backward Compatibility

V2 must not break any existing behavior:

| Contract | Requirement |
|---|---|
| Router public contract | `ok`, `router`, `agent`, `client_id`, `request`, `execution_mode`, `data` — unchanged |
| Demo Client | Must continue to work for all 4 request types |
| Graph execution mode | Default graph, legacy opt-out via `ADS_AGENT_EXECUTION_MODE=legacy` |
| V1 graph smoke test | Must pass (33/33) |
| V0 legacy smoke test | Must pass (20/20) |
| Memory failures | Must not crash the graph — degrade to warning only |

Memory is **additive**. If `MEMORY_ENABLED=false` or the memory directory does not exist, the graph runs exactly as it did in V1.4.1.

---

## 12. Implementation Phases

### V2.1 — Memory utility module

- Create `agents/ads-agent/mempalace.py`
- Read/write `profile.json`
- Read/write snapshot JSON files
- Append to `recommendations.jsonl` and `insights.jsonl`
- Overwrite `latest_summary.json`
- Handle missing directories and disabled memory gracefully
- No graph integration yet — utility layer only

### V2.2 — Memory nodes in Ads Graph

- Add `load_client_memory` node before analysis
- Add `write_memory` node after response formatting
- Add `memory_context` and `memory_write_result` to `AdsAgentState`
- Graph continues on memory failure (warn, don't raise)

### V2.3 — Historical comparison

- Add `compare_with_history` node
- Trend direction for CPA, CTR, conversion rate
- Recurring recommendation detection
- Add `historical_comparison` to `AdsAgentState`
- Enrich executive_summary with trend signals when available

### V2.4 — Memory smoke test and docs

- Add memory smoke test script
- Verify create, read, write, append flows
- Update agent and runbook docs

### V2.5 — Retention controls and raw payload flag

- Implement `MEMORY_MAX_RECENT_SNAPSHOTS` pruning
- Implement `MEMORY_STORE_RAW_PAYLOADS` for raw mode
- Ensure old snapshots beyond retention limit are pruned safely

---

## 13. Acceptance Criteria for First V2 Implementation (V2.1 + V2.2)

- [ ] Memory utility can create client memory directory if it does not exist
- [ ] `profile.json` can be read and written
- [ ] Snapshot JSON files can be written to `snapshots/`
- [ ] `latest_summary.json` is updated on each summary run
- [ ] `recommendations.jsonl` receives a new line per recommendation per run
- [ ] Graph runs without error if memory directory does not exist
- [ ] Graph runs without error if `MEMORY_ENABLED=false`
- [ ] Memory write failure logs a warning to stderr and does not crash the graph
- [ ] V1 graph smoke test still passes (33/33)
- [ ] V0 legacy smoke test still passes (20/20)

---

## 14. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Memory file corruption | Atomic writes via temp file + rename in a later phase; V2.1 uses direct writes |
| Storing too much raw data | Default `MEMORY_STORE_RAW_PAYLOADS=false`; raw mode skips memory by default |
| Multi-tenant memory leakage | Client-ID-scoped directories; future tenant isolation layer in V3 OpenClaw |
| Memory changes breaking graph | All memory failures are caught and converted to stderr warnings; graph continues |
| Recommendation duplication | `recommendation_id` field included from V2.1; deduplication logic added in V2.3 |
| Snapshot accumulation | `MEMORY_MAX_RECENT_SNAPSHOTS` controls load window; full pruning in V2.5 |

---

## 15. Open Questions

The following must be resolved before or during V2.1 implementation:

1. **Profile creation** — Should `profile.json` be manually authored before first run, or auto-created with defaults on first write?
2. **Memory enabled by default** — Should `MEMORY_ENABLED` default to `true` in local dev, or should memory be opt-in initially?
3. **Snapshot load window** — How many recent snapshots should be loaded? Default 5 — is this enough for meaningful trend analysis?
4. **Recommendation IDs** — Should `recommendation_id` be a deterministic hash of (client_id + type + area + action), or a random UUID? Deterministic hashes enable deduplication; UUIDs are simpler.
5. **Memory write for cpa/conversions** — Should partial request types (cpa, conversions) write full snapshots or only the fields they receive?
6. **Raw mode memory** — Should raw mode ever write memory? Current proposal: no by default, opt-in via `MEMORY_STORE_RAW_PAYLOADS=true`.

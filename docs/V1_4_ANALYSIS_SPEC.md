# Kaiju Command Center — V1.4 Analysis Micro-Spec

## 1. Purpose

V1.4 enriches the Ads Agent graph analysis layer. It adds richer KPI interpretation, a structured recommendation schema, and an executive summary block to the graph response.

The following are **not changed** by V1.4:

- Router public contract (`route_request` payload and response envelope)
- Demo Client behavior
- n8n workflow
- Execution mode mechanism (`ADS_AGENT_EXECUTION_MODE`)
- Legacy fallback path

---

## 2. Current Baseline

### Current graph response shape

```
metrics
analysis
recommendations
```

### Current limitations

| Limitation | Description |
|---|---|
| Basic analysis | `analyze_performance` only classifies CPA into three bands |
| Simple recommendations | No severity, action, or expected impact fields |
| No executive summary | No human-readable headline or next-best-action |
| No derived metrics | CTR, CPC, conversion rate not computed |
| No performance score | No single scalar rating of campaign health |

---

## 3. Target Response Shape

### `summary` response `data` block

```json
{
  "metrics": {
    "client": "...",
    "campaign": "...",
    "spend": 0.0,
    "conversions": 0,
    "clicks": 0,
    "impressions": 0,
    "currency": "ARS",
    "cpa": 0.0,
    "ctr": 0.0,
    "cpc": 0.0,
    "conversion_rate": 0.0,
    "cpm": 0.0
  },
  "analysis": {
    "status": "efficient|warning|critical|no_data",
    "performance_score": 0,
    "cpa_level": "efficient|needs_optimization|inefficient|no_conversions",
    "ctr_level": "strong|acceptable|weak|unknown",
    "conversion_rate_level": "strong|acceptable|weak|unknown",
    "spend_efficiency": "strong|moderate|weak|critical",
    "efficiency_notes": ["..."],
    "risk_flags": ["..."]
  },
  "recommendations": [
    {
      "type": "optimization|budget|creative|tracking|strategy",
      "severity": "low|medium|high|critical",
      "priority": "low|medium|high",
      "area": "...",
      "action": "...",
      "expected_impact": "...",
      "rationale": "..."
    }
  ],
  "executive_summary": {
    "headline": "...",
    "summary": "...",
    "next_best_action": "...",
    "confidence": "low|medium|high"
  }
}
```

---

## 4. Available Metrics

### Metrics from n8n today

| Field | Type | Description |
|---|---|---|
| `spend` | float | Total campaign spend |
| `conversions` | int | Total conversions |
| `clicks` | int | Total clicks |
| `impressions` | int | Total impressions |
| `cpa` | float | Cost per acquisition (from n8n) |
| `currency` | str | Currency code (e.g. ARS) |
| `campaign` | str | Campaign name |
| `client` | str | Client ID |

### Derived metrics computable today

| Field | Formula | Notes |
|---|---|---|
| `cpa` | `spend / conversions` | Recompute locally; use n8n value as fallback |
| `ctr` | `clicks / impressions` | Requires impressions > 0 |
| `cpc` | `spend / clicks` | Requires clicks > 0 |
| `conversion_rate` | `conversions / clicks` | Requires clicks > 0 |
| `cpm` | `spend / impressions * 1000` | Requires impressions > 0 |

### Metrics not available in V1.4

The following fields do not exist in the current n8n data source. They must **not** be fabricated or estimated.

- `revenue` / `roas`
- `impression_share` / `search_lost_IS`
- `quality_score`
- `search_term` data
- Creative performance split (headline/description)
- Device split
- Geo split
- GA4 session or revenue data

If a derived metric cannot be computed (missing or zero denominator), set it to `null` and omit it from analysis.

---

## 5. Analysis Rules

All rules are deterministic. No LLM inference in V1.4.

### CPA classification

| Condition | `cpa_level` |
|---|---|
| conversions == 0 | `no_conversions` |
| cpa <= 2000 | `efficient` |
| cpa <= 4000 | `needs_optimization` |
| cpa > 4000 | `inefficient` |

### CTR classification

| Condition | `ctr_level` |
|---|---|
| impressions <= 0 or clicks unavailable | `unknown` |
| ctr >= 0.03 | `strong` |
| ctr >= 0.01 | `acceptable` |
| ctr < 0.01 | `weak` |

### Conversion rate classification

| Condition | `conversion_rate_level` |
|---|---|
| clicks <= 0 | `unknown` |
| conversion_rate >= 0.05 | `strong` |
| conversion_rate >= 0.02 | `acceptable` |
| conversion_rate < 0.02 | `weak` |

### Spend efficiency classification

| Condition | `spend_efficiency` |
|---|---|
| spend > 0 and conversions == 0 | `critical` |
| cpa_level == `efficient` and conversion_rate_level == `strong` | `strong` |
| cpa_level == `needs_optimization` | `moderate` |
| cpa_level == `inefficient` | `weak` |
| default | `moderate` |

### Performance score

Deterministic integer from 0 to 100.

```
score = 50

if cpa_level == "efficient":         score += 25
if cpa_level == "needs_optimization": score += 10
if cpa_level == "inefficient":        score -= 15
if cpa_level == "no_conversions":     score -= 30

if ctr_level == "strong":   score += 10
if ctr_level == "weak":     score -= 10

if conversion_rate_level == "strong": score += 15
if conversion_rate_level == "weak":   score -= 10

score = max(0, min(100, score))
```

### Overall status mapping

| Condition | `status` |
|---|---|
| score >= 70 | `efficient` |
| score >= 40 | `warning` |
| score < 40 or spend_efficiency == `critical` | `critical` |
| no metrics available | `no_data` |

---

## 6. Recommendation Generation Rules

Each recommendation uses the structured schema defined in Section 3.

| Trigger | type | severity | area | action | expected_impact |
|---|---|---|---|---|---|
| `cpa_level == no_conversions` | `tracking` | `critical` | Conversion Tracking | Verify conversion tracking setup and landing page flow | Restore conversion data visibility |
| `cpa_level == no_conversions` (alt) | `strategy` | `critical` | Campaign Strategy | Review campaign objective, targeting, and ad relevance | Identify root cause of zero conversions |
| `cpa_level == inefficient` | `optimization` | `high` | CPA Efficiency | Review targeting, search terms, placements, and creative efficiency | Reduce CPA toward target range |
| `ctr_level == weak` | `creative` | `medium` | Ad Creative | Test new hooks, headlines, and visual angles | Improve CTR above 1% |
| `conversion_rate_level == weak` | `strategy` | `high` | Landing Page | Review landing page relevance, offer clarity, and CTA | Improve conversion rate above 2% |
| `cpa_level == efficient` and `conversion_rate_level == strong` | `budget` | `low` | Budget Scaling | Consider controlled budget scaling of 10–20% | Increase conversion volume while maintaining efficiency |

`rationale` is a concise sentence explaining why the rule fired (e.g. "CPA of 4800 ARS exceeds the 4000 ARS threshold.").

Rules are evaluated in order. Multiple recommendations may fire. An empty recommendations list is valid for a healthy campaign.

---

## 7. Executive Summary Rules

### Fields

| Field | Description |
|---|---|
| `headline` | One-sentence status headline (e.g. "Campaign is efficient with room to scale.") |
| `summary` | 2–3 sentence overview of campaign health and key signals |
| `next_best_action` | The single highest-priority action from recommendations, or "No action required." |
| `confidence` | Confidence in the analysis based on data completeness |

### Confidence rules

| Condition | `confidence` |
|---|---|
| spend, clicks, impressions, and conversions all available and > 0 | `high` |
| At least two of the four metrics available | `medium` |
| Fewer than two metrics available | `low` |

### `next_best_action` selection

Select the action field from the first recommendation with `severity == "critical"`. If none, use the first with `severity == "high"`. If none, use the first recommendation's action. If recommendations is empty, use `"No action required."`.

---

## 8. Request Type Behavior

| Request | `metrics` | `analysis` | `recommendations` | `executive_summary` |
|---|---|---|---|---|
| `summary` | Full derived metrics | Full analysis | Full recommendations | Full summary |
| `cpa` | CPA-focused (spend, conversions, cpa) | CPA analysis + performance_score | CPA and efficiency recommendations | Headline + next_best_action mentioning CPA status |
| `conversions` | Conversion-focused (campaign, conversions, clicks, conversion_rate) | Conversion rate analysis | Conversion volume/rate recommendations | Brief summary focused on conversion signal |
| `raw` | Raw n8n payload (pass-through) | Minimal or omitted | Empty | `"Raw mode: full analysis not performed."` in headline |

---

## 9. Backward Compatibility

The following must remain true after V1.4 is implemented:

| Contract | Requirement |
|---|---|
| Router response envelope | `ok`, `router`, `agent`, `client_id`, `request`, `execution_mode`, `data` — unchanged |
| Demo Client | Must continue to work for all 4 request types |
| `run_graph_demo.py` | Must continue to work for all 4 request types |
| V1 graph smoke test | Update assertions after implementation to include new fields |
| V0 legacy smoke test | Must pass with `ADS_AGENT_EXECUTION_MODE=legacy` |
| `n8n_client.py` | Not modified |
| `router.py` | Not modified |
| `server.py` | Not modified |

---

## 10. Implementation Plan

### Phase V1.4.1 — Helper functions

Add to `ads_graph.py`:

```python
def calculate_derived_metrics(raw: dict) -> dict
def classify_cpa(cpa, conversions) -> str
def classify_ctr(ctr) -> str
def classify_conversion_rate(cr) -> str
def classify_spend_efficiency(spend, conversions, cpa_level, cr_level) -> str
def score_performance(cpa_level, ctr_level, cr_level) -> int
def map_status(score, spend_efficiency) -> str
```

### Phase V1.4.2 — Expand `analyze_performance`

- Compute derived metrics: CTR, CPC, conversion rate, CPM
- Apply all classification rules
- Compute `performance_score`
- Populate `efficiency_notes` and `risk_flags`

### Phase V1.4.3 — Expand `generate_recommendations`

- Apply rule table from Section 6
- Emit structured recommendation objects with all fields

### Phase V1.4.4 — Add `executive_summary` to `format_response`

- Build `headline`, `summary`, `next_best_action`, `confidence`
- Include `executive_summary` in `summary` and `cpa` response shapes
- Minimal / static `executive_summary` for `conversions` and `raw`

### Phase V1.4.5 — Update smoke test

- Add assertion that `summary` response contains `executive_summary`
- Add assertion that `summary` response contains `performance_score`
- Confirm all 4 request types still return `ok: true` and `execution_mode: "graph"`

---

## 11. Acceptance Criteria

- [ ] `summary` response includes `executive_summary` with `headline`, `summary`, `next_best_action`, `confidence`
- [ ] `summary` response includes `analysis.performance_score` (integer 0–100)
- [ ] `analysis` includes `ctr_level`, `conversion_rate_level`, `spend_efficiency`, `risk_flags`
- [ ] Recommendations use structured schema: `type`, `severity`, `priority`, `area`, `action`, `expected_impact`, `rationale`
- [ ] Derived metrics (`ctr`, `cpc`, `conversion_rate`, `cpm`) are included in `metrics` when inputs are available
- [ ] Unavailable metrics are `null` or omitted — not fabricated
- [ ] V1 graph smoke test passes (updated assertions)
- [ ] V0 legacy smoke test passes with `ADS_AGENT_EXECUTION_MODE=legacy`
- [ ] Router contract unchanged
- [ ] `n8n_client.py` unchanged

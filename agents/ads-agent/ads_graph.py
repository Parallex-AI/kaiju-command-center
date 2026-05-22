from pathlib import Path
import sys
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from langgraph.graph import StateGraph, START, END
from n8n_client import fetch_ads_data_from_n8n, VALID_REQUEST_TYPES


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AdsAgentState(TypedDict):
    client_id: str
    request_type: str
    raw_metrics: dict
    normalized_metrics: dict
    analysis: dict
    recommendations: list
    response: dict
    errors: list


# ---------------------------------------------------------------------------
# Unavailable metrics declaration
# ---------------------------------------------------------------------------

UNAVAILABLE_METRICS = [
    "revenue",
    "roas",
    "impression_share",
    "quality_score",
    "search_term_data",
    "creative_split",
    "device_split",
    "geo_split",
    "ga4_revenue",
]


# ---------------------------------------------------------------------------
# Helpers — type coercion
# ---------------------------------------------------------------------------

def safe_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=None):
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Helpers — derived metrics
# ---------------------------------------------------------------------------

def calculate_derived_metrics(metrics: dict) -> dict:
    spend = metrics.get("spend")
    conversions = metrics.get("conversions")
    clicks = metrics.get("clicks")
    impressions = metrics.get("impressions")

    cpa = metrics.get("cpa")
    if cpa is None and spend is not None and conversions and conversions > 0:
        cpa = spend / conversions

    ctr = clicks / impressions if (impressions and impressions > 0 and clicks is not None) else None
    cpc = spend / clicks if (clicks and clicks > 0 and spend is not None) else None
    conversion_rate = conversions / clicks if (clicks and clicks > 0 and conversions is not None) else None
    cpm = spend / impressions * 1000 if (impressions and impressions > 0 and spend is not None) else None

    return {
        "cpa": cpa,
        "ctr": ctr,
        "cpc": cpc,
        "conversion_rate": conversion_rate,
        "cpm": cpm,
    }


# ---------------------------------------------------------------------------
# Helpers — classification
# ---------------------------------------------------------------------------

def classify_cpa(cpa, conversions) -> str:
    if conversions is None or conversions <= 0:
        return "no_conversions"
    if cpa is None:
        return "unknown"
    if cpa <= 2000:
        return "efficient"
    if cpa <= 4000:
        return "needs_optimization"
    return "inefficient"


def classify_ctr(ctr, impressions=None, clicks=None) -> str:
    if ctr is None:
        return "unknown"
    if ctr >= 0.03:
        return "strong"
    if ctr >= 0.01:
        return "acceptable"
    return "weak"


def classify_conversion_rate(conversion_rate, clicks=None) -> str:
    if conversion_rate is None:
        return "unknown"
    if conversion_rate >= 0.05:
        return "strong"
    if conversion_rate >= 0.02:
        return "acceptable"
    return "weak"


def classify_spend_efficiency(spend, conversions, cpa_level, conversion_rate_level) -> str:
    if spend and spend > 0 and (conversions is None or conversions == 0):
        return "critical"
    if cpa_level == "efficient" and conversion_rate_level == "strong":
        return "strong"
    if cpa_level == "needs_optimization":
        return "moderate"
    if cpa_level == "inefficient":
        return "weak"
    return "unknown"


def score_performance(cpa_level, ctr_level, conversion_rate_level, conversions) -> int:
    score = 50

    if cpa_level == "efficient":
        score += 25
    elif cpa_level == "needs_optimization":
        score += 10
    elif cpa_level == "inefficient":
        score -= 15
    elif cpa_level == "no_conversions":
        score -= 30

    if ctr_level == "strong":
        score += 10
    elif ctr_level == "weak":
        score -= 10

    if conversion_rate_level == "strong":
        score += 15
    elif conversion_rate_level == "weak":
        score -= 10

    return max(0, min(100, score))


def map_status(score, spend_efficiency) -> str:
    if spend_efficiency == "critical":
        return "critical"
    if score >= 70:
        return "efficient"
    if score >= 40:
        return "warning"
    return "critical"


# ---------------------------------------------------------------------------
# Helpers — recommendations
# ---------------------------------------------------------------------------

def make_recommendation(rec_type, severity, priority, area, action, expected_impact, rationale) -> dict:
    return {
        "type":            rec_type,
        "severity":        severity,
        "priority":        priority,
        "area":            area,
        "action":          action,
        "expected_impact": expected_impact,
        "rationale":       rationale,
    }


def _filter_recommendations(recommendations: list, request_type: str) -> list:
    if request_type == "summary":
        return recommendations

    monitoring = make_recommendation(
        rec_type="strategy",
        severity="low",
        priority="low",
        area="Monitoring",
        action="Continue monitoring performance and collect more data before making major changes.",
        expected_impact="Avoids premature optimization based on limited or inconclusive signals.",
        rationale="No critical performance issue was detected from the currently available metrics.",
    )

    if request_type == "cpa":
        filtered = [
            r for r in recommendations
            if r.get("type") in ("optimization", "tracking")
            or "cpa" in r.get("area", "").lower()
        ]
        return filtered if filtered else [monitoring]

    if request_type == "conversions":
        filtered = [
            r for r in recommendations
            if r.get("type") in ("strategy", "tracking")
            or "conversion" in r.get("area", "").lower()
        ]
        return filtered if filtered else [monitoring]

    return []


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def validate_input(state: AdsAgentState) -> dict:
    errors = list(state.get("errors") or [])

    if not state.get("client_id"):
        errors.append("client_id is required")

    request_type = state.get("request_type", "")
    if request_type not in VALID_REQUEST_TYPES:
        errors.append(
            f"Unsupported request_type: '{request_type}'. "
            f"Supported: {sorted(VALID_REQUEST_TYPES)}"
        )

    return {"errors": errors}


def fetch_metrics_from_n8n(state: AdsAgentState) -> dict:
    try:
        raw = fetch_ads_data_from_n8n(
            client_id=state["client_id"],
            request_type=state["request_type"],
        )
        return {"raw_metrics": raw}
    except (RuntimeError, ValueError) as error:
        errors = list(state.get("errors") or [])
        errors.append(str(error))
        return {"errors": errors}


def normalize_metrics(state: AdsAgentState) -> dict:
    raw = state.get("raw_metrics") or {}
    request_type = state.get("request_type", "")

    # raw responses are nested: {"request": "raw", "data": {...}}
    data = raw.get("data", raw) if request_type == "raw" else raw

    cpa_raw = data.get("cpa")
    cpa = safe_float(cpa_raw) if cpa_raw is not None else None

    spend = safe_float(data.get("spend", 0), default=0.0)
    conversions = safe_int(data.get("conversions", 0), default=0)
    clicks = safe_int(data.get("clicks", 0), default=0)
    impressions = safe_int(data.get("impressions", 0), default=0)

    if cpa is None and conversions and conversions > 0:
        cpa = spend / conversions

    ctr = clicks / impressions if impressions and impressions > 0 else None
    cpc = spend / clicks if clicks and clicks > 0 else None
    conversion_rate = conversions / clicks if clicks and clicks > 0 else None
    cpm = spend / impressions * 1000 if impressions and impressions > 0 else None

    normalized = {
        "client":              data.get("client", state.get("client_id", "")),
        "campaign":            data.get("campaign", ""),
        "spend":               spend,
        "conversions":         conversions,
        "clicks":              clicks,
        "impressions":         impressions,
        "currency":            data.get("currency", "ARS"),
        "cpa":                 cpa,
        "ctr":                 ctr,
        "cpc":                 cpc,
        "conversion_rate":     conversion_rate,
        "cpm":                 cpm,
        "unavailable_metrics": UNAVAILABLE_METRICS,
    }
    return {"normalized_metrics": normalized}


def analyze_performance(state: AdsAgentState) -> dict:
    metrics = state.get("normalized_metrics") or {}
    cpa = metrics.get("cpa")
    conversions = metrics.get("conversions", 0)
    spend = metrics.get("spend", 0)
    ctr = metrics.get("ctr")
    conversion_rate = metrics.get("conversion_rate")

    cpa_level = classify_cpa(cpa, conversions)
    ctr_level = classify_ctr(ctr)
    conversion_rate_level = classify_conversion_rate(conversion_rate)
    spend_efficiency = classify_spend_efficiency(spend, conversions, cpa_level, conversion_rate_level)
    performance_score = score_performance(cpa_level, ctr_level, conversion_rate_level, conversions)
    status = map_status(performance_score, spend_efficiency)

    notes = []
    risk_flags = []

    if cpa_level == "efficient":
        notes.append("Campaign is performing within an efficient CPA range.")
    elif cpa_level == "needs_optimization":
        notes.append("Campaign is converting, but CPA optimization is recommended.")
    elif cpa_level == "inefficient":
        notes.append("CPA is high. Budget, targeting, and creatives should be reviewed.")
        risk_flags.append("CPA exceeds 4000 threshold.")
    elif cpa_level == "no_conversions":
        notes.append("Campaign has spend but no recorded conversions.")
        risk_flags.append("Zero conversions with active spend.")

    if ctr_level == "weak":
        risk_flags.append("CTR below 1% — ad creative may need improvement.")
    elif ctr_level == "strong":
        notes.append("CTR is strong.")

    if conversion_rate_level == "weak":
        risk_flags.append("Conversion rate below 2% — landing page review recommended.")
    elif conversion_rate_level == "strong":
        notes.append("Conversion rate is strong.")

    # Preserve legacy conversion_level for backward compatibility
    conversion_volume = conversions or 0
    conversion_level = "high" if conversion_volume > 100 else "medium" if conversion_volume > 30 else "low"

    return {
        "analysis": {
            "status":                status,
            "performance_score":     performance_score,
            "cpa_level":             cpa_level,
            "ctr_level":             ctr_level,
            "conversion_rate_level": conversion_rate_level,
            "spend_efficiency":      spend_efficiency,
            "conversion_level":      conversion_level,
            "notes":                 notes,
            "risk_flags":            risk_flags,
        }
    }


def generate_recommendations(state: AdsAgentState) -> dict:
    analysis = state.get("analysis") or {}
    metrics = state.get("normalized_metrics") or {}

    cpa_level = analysis.get("cpa_level", "unknown")
    ctr_level = analysis.get("ctr_level", "unknown")
    conversion_rate_level = analysis.get("conversion_rate_level", "unknown")
    performance_score = analysis.get("performance_score", 50)
    conversions = metrics.get("conversions", 0)
    spend = metrics.get("spend", 0)
    cpa = metrics.get("cpa")

    recommendations = []

    # A: No conversions
    if cpa_level == "no_conversions" or (not conversions and spend and spend > 0):
        recommendations.append(make_recommendation(
            rec_type="tracking",
            severity="critical",
            priority="high",
            area="Conversion Tracking",
            action="Verify conversion tracking, landing page flow, and post-click events before scaling spend.",
            expected_impact="Prevents budget waste and confirms whether the campaign is truly failing or measurement is broken.",
            rationale="Spend exists but no conversions were recorded.",
        ))

    # B: CPA inefficient
    if cpa_level == "inefficient":
        recommendations.append(make_recommendation(
            rec_type="optimization",
            severity="high",
            priority="high",
            area="CPA Efficiency",
            action="Review targeting, search terms, placements, bidding signals, and creative efficiency to reduce CPA.",
            expected_impact="Improves cost efficiency and reduces acquisition waste.",
            rationale="CPA is above the efficient range.",
        ))

    # C: CPA needs optimization
    if cpa_level == "needs_optimization":
        recommendations.append(make_recommendation(
            rec_type="optimization",
            severity="medium",
            priority="medium",
            area="CPA Optimization",
            action="Identify high-cost segments and test budget reallocation toward better-performing audiences or keywords.",
            expected_impact="Can reduce CPA while preserving conversion volume.",
            rationale="CPA is acceptable enough to keep running, but still above the ideal efficiency threshold.",
        ))

    # D: CTR weak
    if ctr_level == "weak":
        recommendations.append(make_recommendation(
            rec_type="creative",
            severity="medium",
            priority="medium",
            area="Ad Engagement",
            action="Test new hooks, headlines, thumbnails, and value propositions to improve click-through rate.",
            expected_impact="Can increase qualified traffic without increasing media spend.",
            rationale="CTR is below the acceptable threshold.",
        ))

    # E: Conversion rate weak
    if conversion_rate_level == "weak":
        recommendations.append(make_recommendation(
            rec_type="strategy",
            severity="high",
            priority="high",
            area="Post-Click Conversion",
            action="Review landing page relevance, offer clarity, form friction, and checkout or registration flow.",
            expected_impact="Can increase conversion volume from the same traffic base.",
            rationale="Conversion rate is weak relative to the current click volume.",
        ))

    # F: Strong performance
    if performance_score >= 80:
        recommendations.append(make_recommendation(
            rec_type="budget",
            severity="low",
            priority="medium",
            area="Budget Scaling",
            action="Consider controlled budget scaling while monitoring CPA and conversion rate stability.",
            expected_impact="Can increase conversion volume without immediately degrading efficiency.",
            rationale="Performance score indicates strong campaign health.",
        ))

    # G: No specific issue found
    if not recommendations:
        recommendations.append(make_recommendation(
            rec_type="strategy",
            severity="low",
            priority="low",
            area="Monitoring",
            action="Continue monitoring performance and collect more data before making major changes.",
            expected_impact="Avoids premature optimization based on limited or inconclusive signals.",
            rationale="No critical performance issue was detected from the currently available metrics.",
        ))

    return {"recommendations": recommendations}


def format_response(state: AdsAgentState) -> dict:
    client_id = state.get("client_id", "")
    request_type = state.get("request_type", "")
    errors = state.get("errors") or []

    if errors:
        return {
            "response": {
                "ok": False,
                "agent": "ads-agent",
                "execution_mode": "graph",
                "client_id": client_id,
                "request": request_type,
                "errors": errors,
            }
        }

    metrics = state.get("normalized_metrics") or state.get("raw_metrics") or {}
    analysis = state.get("analysis") or {}
    recommendations = state.get("recommendations") or []

    if request_type == "raw":
        data = {
            "metrics": state.get("raw_metrics") or {},
            "analysis": {},
            "recommendations": [],
        }
    elif request_type == "conversions":
        data = {
            "metrics": {
                "campaign":        metrics.get("campaign"),
                "conversions":     metrics.get("conversions"),
                "clicks":          metrics.get("clicks"),
                "conversion_rate": metrics.get("conversion_rate"),
            },
            "analysis": {},
            "recommendations": _filter_recommendations(recommendations, "conversions"),
        }
    elif request_type == "cpa":
        data = {
            "metrics": {
                "spend":       metrics.get("spend"),
                "conversions": metrics.get("conversions"),
                "cpa":         metrics.get("cpa"),
                "currency":    metrics.get("currency"),
            },
            "analysis": {
                "cpa_level":         analysis.get("cpa_level"),
                "performance_score": analysis.get("performance_score"),
                "status":            analysis.get("status"),
                "notes":             analysis.get("notes", []),
            },
            "recommendations": _filter_recommendations(recommendations, "cpa"),
        }
    else:  # summary
        data = {
            "metrics":         metrics,
            "analysis":        analysis,
            "recommendations": recommendations,
        }

    return {
        "response": {
            "ok": True,
            "agent": "ads-agent",
            "execution_mode": "graph",
            "client_id": client_id,
            "request": request_type,
            "data": data,
        }
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_after_validate(state: AdsAgentState) -> str:
    return "format_response" if state.get("errors") else "fetch_metrics_from_n8n"


def _route_after_fetch(state: AdsAgentState) -> str:
    return "format_response" if state.get("errors") else "normalize_metrics"


def _route_after_normalize(state: AdsAgentState) -> str:
    if state.get("errors"):
        return "format_response"
    if state.get("request_type") == "raw":
        return "format_response"
    return "analyze_performance"


def _route_after_analyze(state: AdsAgentState) -> str:
    if state.get("errors"):
        return "format_response"
    return "generate_recommendations"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def _build_graph() -> object:
    graph = StateGraph(AdsAgentState)

    graph.add_node("validate_input",           validate_input)
    graph.add_node("fetch_metrics_from_n8n",   fetch_metrics_from_n8n)
    graph.add_node("normalize_metrics",        normalize_metrics)
    graph.add_node("analyze_performance",      analyze_performance)
    graph.add_node("generate_recommendations", generate_recommendations)
    graph.add_node("format_response",          format_response)

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges("validate_input",           _route_after_validate)
    graph.add_conditional_edges("fetch_metrics_from_n8n",   _route_after_fetch)
    graph.add_conditional_edges("normalize_metrics",        _route_after_normalize)
    graph.add_conditional_edges("analyze_performance",      _route_after_analyze)
    graph.add_edge("generate_recommendations", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()


_compiled_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_ads_graph(client_id: str = "demo-client", request_type: str = "summary") -> dict:
    initial_state: AdsAgentState = {
        "client_id":          client_id,
        "request_type":       request_type,
        "raw_metrics":        {},
        "normalized_metrics": {},
        "analysis":           {},
        "recommendations":    [],
        "response":           {},
        "errors":             [],
    }
    result = _compiled_graph.invoke(initial_state)
    return result["response"]

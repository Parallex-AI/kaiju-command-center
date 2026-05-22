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
# Helpers
# ---------------------------------------------------------------------------

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


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

    spend = safe_float(data.get("spend", 0))
    conversions = safe_int(data.get("conversions", 0))

    if cpa is None and conversions > 0:
        cpa = spend / conversions

    normalized = {
        "client":      data.get("client", state.get("client_id", "")),
        "campaign":    data.get("campaign", ""),
        "spend":       spend,
        "conversions": conversions,
        "clicks":      safe_int(data.get("clicks", 0)),
        "impressions": safe_int(data.get("impressions", 0)),
        "currency":    data.get("currency", "ARS"),
        "cpa":         cpa,
    }
    return {"normalized_metrics": normalized}


def analyze_performance(state: AdsAgentState) -> dict:
    metrics = state.get("normalized_metrics") or {}
    cpa = metrics.get("cpa")
    conversions = metrics.get("conversions", 0)

    if conversions == 0:
        cpa_level, status = "no_conversions", "no_conversions"
        notes = ["Campaign has spend but no recorded conversions."]
    elif cpa is None:
        cpa_level, status = "unknown", "unknown"
        notes = ["CPA could not be determined."]
    elif cpa <= 2000:
        cpa_level, status = "efficient", "healthy"
        notes = ["Campaign is performing within an efficient CPA range."]
    elif cpa <= 4000:
        cpa_level, status = "needs_optimization", "warning"
        notes = ["Campaign is converting, but CPA optimization is recommended."]
    else:
        cpa_level, status = "inefficient", "critical"
        notes = ["CPA is high. Budget, targeting, and creatives should be reviewed."]

    conversion_volume = conversions
    conversion_level = "high" if conversion_volume > 100 else "medium" if conversion_volume > 30 else "low"

    return {
        "analysis": {
            "status": status,
            "cpa_level": cpa_level,
            "conversion_level": conversion_level,
            "notes": notes,
        }
    }


def generate_recommendations(state: AdsAgentState) -> dict:
    analysis = state.get("analysis") or {}
    status = analysis.get("status", "unknown")
    cpa_level = analysis.get("cpa_level", "unknown")
    conversion_level = analysis.get("conversion_level", "unknown")

    recommendations = []

    if status == "no_conversions":
        recommendations.append({
            "priority": "high",
            "area": "Conversions",
            "recommendation": (
                "No conversions recorded. Review conversion tracking, "
                "landing pages, and audience targeting."
            ),
        })

    if cpa_level == "needs_optimization":
        recommendations.append({
            "priority": "medium",
            "area": "CPA",
            "recommendation": "Review targeting and creative efficiency to reduce CPA.",
        })
    elif cpa_level == "inefficient":
        recommendations.append({
            "priority": "high",
            "area": "CPA",
            "recommendation": (
                "CPA is critically high. Pause underperforming ad groups "
                "and reallocate budget to top performers."
            ),
        })

    if conversion_level == "low" and status not in ("no_conversions", "unknown"):
        recommendations.append({
            "priority": "medium",
            "area": "Volume",
            "recommendation": (
                "Conversion volume is low. Consider expanding audience "
                "targeting or increasing budget."
            ),
        })

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
                "campaign":    metrics.get("campaign"),
                "conversions": metrics.get("conversions"),
            },
            "analysis": {},
            "recommendations": [],
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
                "cpa_level": analysis.get("cpa_level"),
                "status":    analysis.get("status"),
                "notes":     analysis.get("notes", []),
            },
            "recommendations": [],
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
    if state.get("request_type") in ("cpa", "conversions"):
        return "format_response"
    return "generate_recommendations"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def _build_graph() -> object:
    graph = StateGraph(AdsAgentState)

    graph.add_node("validate_input",         validate_input)
    graph.add_node("fetch_metrics_from_n8n", fetch_metrics_from_n8n)
    graph.add_node("normalize_metrics",      normalize_metrics)
    graph.add_node("analyze_performance",    analyze_performance)
    graph.add_node("generate_recommendations", generate_recommendations)
    graph.add_node("format_response",        format_response)

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges("validate_input",         _route_after_validate)
    graph.add_conditional_edges("fetch_metrics_from_n8n", _route_after_fetch)
    graph.add_conditional_edges("normalize_metrics",      _route_after_normalize)
    graph.add_conditional_edges("analyze_performance",    _route_after_analyze)
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

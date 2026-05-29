import copy
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from langgraph.graph import StateGraph, START, END
from n8n_client import VALID_REQUEST_TYPES
from integrations.resolver import resolve_ads_data
import mempalace


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AdsAgentState(TypedDict):
    client_id: str
    request_type: str
    data_source: str
    raw_metrics: dict
    normalized_metrics: dict
    analysis: dict
    recommendations: list
    response: dict
    errors: list
    memory_context: dict
    historical_comparison: dict
    memory_write_result: dict
    warnings: list


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
# Helpers — historical comparison
# ---------------------------------------------------------------------------

def extract_snapshot_metrics(snapshot: dict) -> dict:
    if not isinstance(snapshot, dict):
        return {}
    for getter in [
        lambda s: s.get("metrics"),
        lambda s: (s.get("data") or {}).get("metrics"),
        lambda s: ((s.get("response") or {}).get("data") or {}).get("metrics"),
        lambda s: (s.get("snapshot") or {}).get("metrics"),
    ]:
        try:
            result = getter(snapshot)
            if isinstance(result, dict):
                return result
        except Exception:
            pass
    return {}


def extract_snapshot_analysis(snapshot: dict) -> dict:
    if not isinstance(snapshot, dict):
        return {}
    for getter in [
        lambda s: s.get("analysis"),
        lambda s: (s.get("data") or {}).get("analysis"),
        lambda s: ((s.get("response") or {}).get("data") or {}).get("analysis"),
    ]:
        try:
            result = getter(snapshot)
            if isinstance(result, dict):
                return result
        except Exception:
            pass
    return {}


def compare_numeric_direction(
    current,
    previous,
    tolerance_ratio: float = 0.03,
    lower_is_better: bool = False,
) -> str:
    try:
        current = float(current)
        previous = float(previous)
    except (TypeError, ValueError):
        return "unknown"

    if previous == 0 and current == 0:
        return "stable"

    if previous == 0:
        if current > 0:
            return "worsened" if lower_is_better else "improved"
        return "improved" if lower_is_better else "worsened"

    tolerance = abs(previous) * tolerance_ratio
    diff = current - previous

    if lower_is_better:
        if diff < -tolerance:
            return "improved"
        if diff > tolerance:
            return "worsened"
        return "stable"
    else:
        if diff > tolerance:
            return "improved"
        if diff < -tolerance:
            return "worsened"
        return "stable"


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


def generate_executive_summary(request_type: str, metrics: dict, analysis: dict, recommendations: list) -> dict:
    spend = metrics.get("spend", 0) or 0
    clicks = metrics.get("clicks", 0) or 0
    impressions = metrics.get("impressions", 0) or 0
    conversions = metrics.get("conversions")
    currency = metrics.get("currency", "ARS")
    campaign = metrics.get("campaign", "")
    cpa = metrics.get("cpa")

    cpa_level = analysis.get("cpa_level", "unknown")
    performance_score = analysis.get("performance_score")

    # Confidence
    if request_type == "raw":
        confidence = "low"
    elif spend > 0 and clicks > 0 and impressions > 0 and conversions is not None:
        confidence = "high"
    elif spend > 0 and conversions is not None:
        confidence = "medium"
    else:
        confidence = "low"

    # Headline
    if request_type == "raw":
        headline = "Raw campaign data returned without full strategic analysis."
    elif cpa_level == "no_conversions":
        headline = "Campaign spend is active but no conversions were recorded."
    elif cpa_level == "efficient":
        headline = "Campaign CPA is currently efficient."
    elif cpa_level == "needs_optimization":
        headline = "Campaign is converting, but CPA optimization is recommended."
    elif cpa_level == "inefficient":
        headline = "Campaign CPA is inefficient and requires intervention."
    else:
        headline = "Campaign performance analysis completed."

    # Summary text
    if request_type == "raw":
        summary_text = "Raw payload returned. Full analysis was not performed."
    else:
        label = f"The campaign '{campaign}'" if campaign else "The campaign"
        if spend > 0:
            label += f" invested {currency} {spend:,.2f}"
        if conversions is not None and conversions > 0:
            if spend > 0:
                label += f" and generated {conversions} conversion{'s' if conversions != 1 else ''}"
            else:
                label += f" generated {conversions} conversion{'s' if conversions != 1 else ''}"
        elif conversions is not None:
            label += " but recorded no conversions"
        parts = [label + "."]
        if cpa is not None and cpa > 0 and conversions and conversions > 0:
            parts.append(f"CPA is {currency} {cpa:,.2f} ({cpa_level.replace('_', ' ')}).")
        if performance_score is not None:
            parts.append(f"Performance score: {performance_score}/100.")
        summary_text = " ".join(parts)

    # Next best action
    if request_type == "raw":
        next_best_action = "Review raw payload before running strategic analysis."
    elif recommendations:
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_recs = sorted(
            recommendations,
            key=lambda r: priority_order.get(r.get("severity", "low"), 3),
        )
        next_best_action = sorted_recs[0].get("action", "Continue monitoring performance until more data is available.")
    else:
        next_best_action = "Continue monitoring performance until more data is available."

    return {
        "headline":         headline,
        "summary":          summary_text,
        "next_best_action": next_best_action,
        "confidence":       confidence,
    }


# ---------------------------------------------------------------------------
# Memory helper
# ---------------------------------------------------------------------------

def _inject_memory_into_response(response: dict, memory_block: dict) -> dict:
    if not response.get("ok"):
        return response
    updated = copy.deepcopy(response)
    if "data" in updated:
        updated["data"]["memory"] = memory_block
    return updated


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


def load_client_memory(state: AdsAgentState) -> dict:
    warnings = list(state.get("warnings") or [])

    if not mempalace.is_memory_enabled():
        return {
            "memory_context": {"enabled": False},
            "warnings": warnings,
        }

    client_id = state.get("client_id", "")

    try:
        profile = mempalace.read_profile(client_id)
        latest_summary = mempalace.read_latest_summary(client_id)
        recent_snapshots = mempalace.read_recent_snapshots(client_id)

        memory_context = {
            "enabled": True,
            "profile": profile,
            "latest_summary": latest_summary,
            "recent_snapshots": recent_snapshots,
        }
    except Exception as error:
        warnings.append(f"Memory load failed: {error}")
        memory_context = {"enabled": False, "error": str(error)}

    return {
        "memory_context": memory_context,
        "warnings": warnings,
    }


def fetch_metrics(state: AdsAgentState) -> dict:
    client_id = state["client_id"]
    request_type = state["request_type"]

    try:
        result = resolve_ads_data(client_id, request_type)
    except Exception as error:
        errors = list(state.get("errors") or [])
        errors.append(f"Integration resolver error: {error}")
        return {"errors": errors}

    if not result.get("ok"):
        errors = list(state.get("errors") or [])
        err = result.get("error") or {}
        err_code = err.get("code", "integration_error")
        err_msg = err.get("message", str(result))
        errors.append(f"[{err_code}] {err_msg}")
        return {"errors": errors, "data_source": result.get("data_source", "")}

    data_source = result.get("data_source", "n8n_demo")

    # For n8n_demo preserve the original n8n response shape so the existing
    # normalize_metrics node continues to work exactly as before.
    # For other sources (mock_fixture, future google_ads) the canonical metrics
    # dict has the same field names the normalize_metrics node expects.
    if data_source == "n8n_demo":
        raw_metrics = result.get("raw_data") or result.get("data") or {}
    else:
        raw_metrics = result.get("data") or {}

    return {
        "raw_metrics": raw_metrics,
        "data_source": data_source,
    }


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


def compare_with_history(state: AdsAgentState) -> dict:
    memory_context = state.get("memory_context") or {}
    metrics = state.get("normalized_metrics") or {}
    warnings = list(state.get("warnings") or [])

    _no_history_base = {
        "has_history": False,
        "history_count": 0,
        "comparison_window": 0,
        "cpa_direction": "unknown",
        "conversions_direction": "unknown",
        "ctr_direction": "unknown",
        "conversion_rate_direction": "unknown",
        "performance_score_direction": "unknown",
        "recurring_risk_flags": [],
        "recurring_recommendation_areas": [],
        "notes": [],
    }

    if not memory_context.get("enabled"):
        return {
            "historical_comparison": {**_no_history_base, "notes": ["Memory is disabled or unavailable."]},
            "warnings": warnings,
        }

    recent_snapshots = memory_context.get("recent_snapshots") or []
    comparison_window = len(recent_snapshots)

    # Collect usable snapshots (parseable, have extractable metrics)
    usable = [
        s for s in recent_snapshots
        if isinstance(s, dict) and "warning" not in s and extract_snapshot_metrics(s)
    ]

    # Fall back to latest_summary if snapshot list is empty
    if not usable:
        latest = memory_context.get("latest_summary")
        if isinstance(latest, dict) and "warning" not in latest and extract_snapshot_metrics(latest):
            usable = [latest]
            comparison_window = max(comparison_window, 1)

    history_count = len(usable)

    if history_count == 0:
        return {
            "historical_comparison": {
                **_no_history_base,
                "comparison_window": comparison_window,
                "notes": ["No previous memory available for comparison."],
            },
            "warnings": warnings,
        }

    # Compare against most recent usable snapshot (list is sorted descending by timestamp)
    prev_snap = usable[0]
    prev_metrics = extract_snapshot_metrics(prev_snap)
    prev_analysis = extract_snapshot_analysis(prev_snap)

    cpa_direction = compare_numeric_direction(
        metrics.get("cpa"), prev_metrics.get("cpa"), lower_is_better=True
    )
    conversions_direction = compare_numeric_direction(
        metrics.get("conversions"), prev_metrics.get("conversions"), lower_is_better=False
    )
    ctr_direction = compare_numeric_direction(
        metrics.get("ctr"), prev_metrics.get("ctr"), lower_is_better=False
    )
    conversion_rate_direction = compare_numeric_direction(
        metrics.get("conversion_rate"), prev_metrics.get("conversion_rate"), lower_is_better=False
    )

    # performance_score not yet computed for current run; finalized later in write_memory
    prev_score = prev_analysis.get("performance_score")
    performance_score_direction = "pending" if prev_score is not None else "unknown"

    # Recurring signals: flags/areas appearing in 2+ usable snapshots
    flag_counts: dict = {}
    area_counts: dict = {}
    for snap in usable:
        a = extract_snapshot_analysis(snap)
        for flag in (a.get("risk_flags") or []):
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
        for rec in (snap.get("recommendations") or []):
            area = rec.get("area", "")
            if area:
                area_counts[area] = area_counts.get(area, 0) + 1

    recurring_risk_flags = [f for f, n in flag_counts.items() if n >= 2]
    recurring_recommendation_areas = [a for a, n in area_counts.items() if n >= 2]

    # Notes: concise directional signals used by analyze_performance for [History] entries
    notes = []
    if cpa_direction in ("improved", "worsened"):
        curr_cpa = metrics.get("cpa")
        prev_cpa = prev_metrics.get("cpa")
        if curr_cpa is not None and prev_cpa is not None:
            notes.append(f"CPA {cpa_direction} from {prev_cpa:.2f} to {curr_cpa:.2f}.")
        else:
            notes.append(f"CPA {cpa_direction} compared with previous snapshot.")
    if conversions_direction in ("improved", "worsened"):
        notes.append(
            f"Conversions {conversions_direction} from "
            f"{prev_metrics.get('conversions')} to {metrics.get('conversions')}."
        )
    if not notes:
        notes.append("Campaign metrics are stable compared to the previous run.")

    return {
        "historical_comparison": {
            "has_history": True,
            "history_count": history_count,
            "comparison_window": comparison_window,
            "cpa_direction": cpa_direction,
            "conversions_direction": conversions_direction,
            "ctr_direction": ctr_direction,
            "conversion_rate_direction": conversion_rate_direction,
            "performance_score_direction": performance_score_direction,
            "recurring_risk_flags": recurring_risk_flags,
            "recurring_recommendation_areas": recurring_recommendation_areas,
            "notes": notes,
        },
        "warnings": warnings,
    }


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

    # Enrich notes with historical comparison signals
    historical = state.get("historical_comparison") or {}
    if historical.get("has_history"):
        cpa_dir = historical.get("cpa_direction", "unknown")
        if cpa_dir in ("improved", "worsened"):
            notes.append(f"[History] CPA {cpa_dir} compared with previous snapshot.")
        conv_dir = historical.get("conversions_direction", "unknown")
        if conv_dir in ("improved", "worsened"):
            notes.append(f"[History] Conversions {conv_dir} compared with previous snapshot.")
        for flag in (historical.get("recurring_risk_flags") or []):
            notes.append(f"[History] Recurring risk flag detected: {flag}")

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
    data_source = state.get("data_source") or "n8n_demo"
    errors = state.get("errors") or []

    if errors:
        return {
            "response": {
                "ok": False,
                "agent": "ads-agent",
                "execution_mode": "graph",
                "client_id": client_id,
                "request": request_type,
                "data_source": data_source,
                "errors": errors,
            }
        }

    metrics = state.get("normalized_metrics") or state.get("raw_metrics") or {}
    analysis = state.get("analysis") or {}
    recommendations = state.get("recommendations") or []

    if request_type == "raw":
        data = {
            "metrics":           state.get("raw_metrics") or {},
            "analysis":          {},
            "recommendations":   [],
            "executive_summary": generate_executive_summary("raw", {}, {}, []),
        }
    elif request_type == "conversions":
        filtered_recs = _filter_recommendations(recommendations, "conversions")
        data = {
            "metrics": {
                "campaign":        metrics.get("campaign"),
                "conversions":     metrics.get("conversions"),
                "clicks":          metrics.get("clicks"),
                "conversion_rate": metrics.get("conversion_rate"),
            },
            "analysis":          {},
            "recommendations":   filtered_recs,
            "executive_summary": generate_executive_summary("conversions", metrics, {}, filtered_recs),
        }
    elif request_type == "cpa":
        filtered_recs = _filter_recommendations(recommendations, "cpa")
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
            "recommendations":   filtered_recs,
            "executive_summary": generate_executive_summary("cpa", metrics, analysis, filtered_recs),
        }
    else:  # summary
        data = {
            "metrics":           metrics,
            "analysis":          analysis,
            "recommendations":   recommendations,
            "executive_summary": generate_executive_summary("summary", metrics, analysis, recommendations),
        }

    return {
        "response": {
            "ok": True,
            "agent": "ads-agent",
            "execution_mode": "graph",
            "client_id": client_id,
            "request": request_type,
            "data_source": data_source,
            "data": data,
        }
    }


def write_memory(state: AdsAgentState) -> dict:
    warnings = list(state.get("warnings") or [])
    request_type = state.get("request_type", "")
    client_id = state.get("client_id", "")
    response = state.get("response") or {}
    memory_context = state.get("memory_context") or {}
    historical_comparison = dict(state.get("historical_comparison") or {})
    memory_enabled = mempalace.is_memory_enabled()

    memory_block = {
        "enabled": memory_enabled,
        "has_history": historical_comparison.get("has_history", False),
        "historical_comparison": historical_comparison,
        "warnings": warnings,
    }

    def _finish(write_result):
        mb = {**memory_block, "write_result": write_result, "warnings": warnings}
        return {
            "memory_write_result": write_result,
            "response": _inject_memory_into_response(response, mb),
            "warnings": warnings,
        }

    # Skip for raw mode — never store raw payload
    if request_type == "raw":
        return _finish({"ok": True, "skipped": True, "reason": "raw mode: memory write skipped"})

    # Skip if memory disabled
    if not memory_enabled:
        return _finish({"ok": False, "skipped": True, "reason": "Memory disabled"})

    # Skip if graph returned an error
    if not response.get("ok"):
        return _finish({"ok": False, "skipped": True, "reason": "Graph returned error; no memory written"})

    # Finalize performance_score_direction now that analysis is complete
    if historical_comparison.get("performance_score_direction") == "pending":
        try:
            current_score = (state.get("analysis") or {}).get("performance_score")
            recent = memory_context.get("recent_snapshots") or []
            prev_snap = next(
                (s for s in recent if isinstance(s, dict) and "warning" not in s), None
            )
            if prev_snap is None:
                ls = memory_context.get("latest_summary")
                if isinstance(ls, dict) and "warning" not in ls:
                    prev_snap = ls
            if prev_snap is not None and current_score is not None:
                prev_score = extract_snapshot_analysis(prev_snap).get("performance_score")
                if prev_score is not None:
                    historical_comparison["performance_score_direction"] = compare_numeric_direction(
                        current_score, prev_score, lower_is_better=False
                    )
        except Exception:
            pass

    snapshot = {
        "metrics":               state.get("normalized_metrics") or {},
        "analysis":              state.get("analysis") or {},
        "recommendations":       state.get("recommendations") or [],
        "executive_summary":     (response.get("data") or {}).get("executive_summary"),
        "historical_comparison": historical_comparison,
    }

    write_results = {}

    try:
        snap_result = mempalace.write_snapshot(
            client_id=client_id,
            snapshot=snapshot,
            agent="ads-agent",
            request_type=request_type,
        )
        write_results["snapshot"] = snap_result
    except Exception as error:
        warnings.append(f"Memory snapshot write failed: {error}")
        write_results["snapshot"] = {"ok": False, "error": str(error)}

    try:
        recs = state.get("recommendations") or []
        if recs:
            rec_result = mempalace.append_recommendations(
                client_id=client_id,
                recommendations=recs,
                agent="ads-agent",
            )
            write_results["recommendations"] = rec_result
    except Exception as error:
        warnings.append(f"Memory recommendations write failed: {error}")
        write_results["recommendations"] = {"ok": False, "error": str(error)}

    try:
        hist = historical_comparison
        if hist.get("has_history") and hist.get("notes"):
            insight_result = mempalace.append_insight(
                client_id=client_id,
                insight={
                    "insight_type": "trend",
                    "summary": "; ".join(hist.get("notes", [])),
                    "evidence": {
                        "cpa_direction": hist.get("cpa_direction"),
                        "conversions_direction": hist.get("conversions_direction"),
                        "performance_score_direction": hist.get("performance_score_direction"),
                    },
                },
                agent="ads-agent",
            )
            write_results["insight"] = insight_result
    except Exception as error:
        warnings.append(f"Memory insight write failed: {error}")
        write_results["insight"] = {"ok": False, "error": str(error)}

    return _finish({"ok": True, "results": write_results})


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_after_validate(state: AdsAgentState) -> str:
    return "format_response" if state.get("errors") else "load_client_memory"


def _route_after_fetch(state: AdsAgentState) -> str:
    return "format_response" if state.get("errors") else "normalize_metrics"


def _route_after_normalize(state: AdsAgentState) -> str:
    if state.get("errors"):
        return "format_response"
    if state.get("request_type") == "raw":
        return "format_response"
    return "compare_with_history"


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
    graph.add_node("load_client_memory",       load_client_memory)
    graph.add_node("fetch_metrics",            fetch_metrics)
    graph.add_node("normalize_metrics",        normalize_metrics)
    graph.add_node("compare_with_history",     compare_with_history)
    graph.add_node("analyze_performance",      analyze_performance)
    graph.add_node("generate_recommendations", generate_recommendations)
    graph.add_node("format_response",          format_response)
    graph.add_node("write_memory",             write_memory)

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges("validate_input",     _route_after_validate)
    graph.add_edge("load_client_memory", "fetch_metrics")
    graph.add_conditional_edges("fetch_metrics",      _route_after_fetch)
    graph.add_conditional_edges("normalize_metrics",  _route_after_normalize)
    graph.add_edge("compare_with_history", "analyze_performance")
    graph.add_conditional_edges("analyze_performance",      _route_after_analyze)
    graph.add_edge("generate_recommendations", "format_response")
    graph.add_edge("format_response", "write_memory")
    graph.add_edge("write_memory", END)

    return graph.compile()


_compiled_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_ads_graph(client_id: str = "demo-client", request_type: str = "summary") -> dict:
    initial_state: AdsAgentState = {
        "client_id":             client_id,
        "request_type":          request_type,
        "data_source":           "",
        "raw_metrics":           {},
        "normalized_metrics":    {},
        "analysis":              {},
        "recommendations":       [],
        "response":              {},
        "errors":                [],
        "memory_context":        {},
        "historical_comparison": {},
        "memory_write_result":   {},
        "warnings":              [],
    }
    result = _compiled_graph.invoke(initial_state)
    return result["response"]

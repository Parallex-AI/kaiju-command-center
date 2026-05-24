"""
V2.1 MemPalace utility demo.

Exercises all memory utilities: config, dirs, profile, snapshot,
recommendations, insights, latest summary, and recent snapshots.
Does not call n8n or ads_graph.py.

Usage:
    python3 run_mempalace_demo.py
    python3 run_mempalace_demo.py demo-client
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mempalace


def pp(label: str, data) -> None:
    print(f"\n--- {label} ---")
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def main() -> None:
    client_id = sys.argv[1] if len(sys.argv) > 1 else "demo-client"

    print("=== Kaiju MemPalace V2.1 Demo ===")
    print(f"Client:          {client_id}")
    print(f"Memory enabled:  {mempalace.is_memory_enabled()}")
    print(f"Memory root:     {mempalace.get_memory_root()}")
    print(f"Max snapshots:   {mempalace.get_max_recent_snapshots()}")

    # 1. Ensure directories
    dirs = mempalace.ensure_client_memory_dirs(client_id)
    pp("ensure_client_memory_dirs", dirs)

    # 2. Read profile (creates default if missing)
    profile = mempalace.read_profile(client_id)
    pp("read_profile (initial)", profile)

    # 3. Write enriched profile
    profile["display_name"] = "Demo Client (Kaiju)"
    profile["notes"] = ["Demo account — synthetic data only"]
    write_result = mempalace.write_profile(client_id, profile)
    pp("write_profile", write_result)

    # 4. Read profile back
    profile_back = mempalace.read_profile(client_id)
    pp("read_profile (after write)", profile_back)

    # 5. Write a demo summary snapshot
    demo_snapshot = {
        "metrics": {
            "spend": 125000.0,
            "conversions": 62,
            "clicks": 3100,
            "impressions": 85000,
            "currency": "ARS",
            "cpa": 2016.13,
            "ctr": 0.03647,
            "cpc": 40.32,
            "conversion_rate": 0.02,
            "cpm": 1470.59,
        },
        "analysis": {
            "status": "warning",
            "performance_score": 70,
            "cpa_level": "needs_optimization",
            "ctr_level": "strong",
            "conversion_rate_level": "acceptable",
            "spend_efficiency": "moderate",
        },
        "executive_summary": {
            "headline": "Campaign is generating conversions, but CPA optimization is recommended.",
            "summary": "Demo Google Ads Campaign spent ARS 125,000 and generated 62 conversions at CPA ARS 2,016.",
            "next_best_action": "Review targeting and budget allocation.",
            "confidence": "high",
        },
    }
    snap_result = mempalace.write_snapshot(
        client_id=client_id,
        snapshot=demo_snapshot,
        agent="ads-agent",
        request_type="summary",
    )
    pp("write_snapshot (summary)", snap_result)

    # 6. Append demo recommendations
    demo_recommendations = [
        {
            "type": "optimization",
            "severity": "high",
            "priority": "high",
            "area": "CPA Efficiency",
            "action": "Review targeting, search terms, placements, and creative efficiency",
            "expected_impact": "Reduce CPA toward target range",
            "rationale": "CPA of 2016 ARS is in the needs_optimization band (2000–4000 ARS).",
        },
        {
            "type": "budget",
            "severity": "low",
            "priority": "low",
            "area": "Budget Scaling",
            "action": "Consider controlled budget scaling of 10–20%",
            "expected_impact": "Increase conversion volume while maintaining efficiency",
            "rationale": "CTR is strong and conversion rate is acceptable.",
        },
    ]
    rec_result = mempalace.append_recommendations(
        client_id=client_id,
        recommendations=demo_recommendations,
        agent="ads-agent",
    )
    pp("append_recommendations", rec_result)

    # 7. Append a demo insight
    demo_insight = {
        "insight_type": "trend",
        "summary": "CPA has remained stable in the needs_optimization band across this demo run.",
        "evidence": {
            "cpa": 2016.13,
            "cpa_level": "needs_optimization",
            "performance_score": 70,
        },
    }
    insight_result = mempalace.append_insight(
        client_id=client_id,
        insight=demo_insight,
        agent="ads-agent",
    )
    pp("append_insight", insight_result)

    # 8. Read latest summary
    latest = mempalace.read_latest_summary(client_id=client_id, agent="ads-agent")
    if latest:
        pp("read_latest_summary", {
            "timestamp": latest.get("timestamp"),
            "request_type": latest.get("request_type"),
            "performance_score": latest.get("analysis", {}).get("performance_score"),
            "headline": latest.get("executive_summary", {}).get("headline"),
        })
    else:
        print("\n--- read_latest_summary ---\nNone (memory disabled or no summary written)")

    # 9. Read recent snapshots
    snapshots = mempalace.read_recent_snapshots(client_id=client_id, agent="ads-agent")
    pp("read_recent_snapshots", [
        {
            "timestamp": s.get("timestamp"),
            "request_type": s.get("request_type"),
            "performance_score": s.get("analysis", {}).get("performance_score"),
        }
        for s in snapshots
        if "warning" not in s
    ])

    print("\n=== MemPalace V2.1 Demo complete. ===\n")


if __name__ == "__main__":
    main()

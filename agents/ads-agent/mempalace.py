import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DEFAULT_MAX_RECENT_SNAPSHOTS = 5

# Repo root is two levels up from this file (agents/ads-agent/mempalace.py → repo root)
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MEMORY_ROOT = str(_REPO_ROOT / "memory" / "client-memory")


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def is_memory_enabled() -> bool:
    raw = os.getenv("MEMORY_ENABLED", "true").strip().lower()
    return raw not in {"false", "0", "no", "off"}


def get_memory_root() -> Path:
    raw = os.getenv("MEMORY_ROOT", DEFAULT_MEMORY_ROOT).strip()
    return Path(raw) if raw else Path(DEFAULT_MEMORY_ROOT)


def get_max_recent_snapshots() -> int:
    raw = os.getenv("MEMORY_MAX_RECENT_SNAPSHOTS", "")
    try:
        value = int(raw)
        if value > 0:
            return value
    except (TypeError, ValueError):
        pass
    return DEFAULT_MAX_RECENT_SNAPSHOTS


# ---------------------------------------------------------------------------
# Path sanitization
# ---------------------------------------------------------------------------

def sanitize_path_part(value: str) -> str:
    if not value or not value.strip():
        return "unknown"
    sanitized = "".join(c if (c.isalnum() or c in "-_") else "-" for c in value.strip())
    return sanitized or "unknown"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_client_memory_dir(client_id: str) -> Path:
    return get_memory_root() / sanitize_path_part(client_id)


def get_agent_memory_dir(client_id: str, agent: str = "ads-agent") -> Path:
    return get_client_memory_dir(client_id) / sanitize_path_part(agent)


def get_snapshots_dir(client_id: str, agent: str = "ads-agent") -> Path:
    return get_agent_memory_dir(client_id, agent) / "snapshots"


# ---------------------------------------------------------------------------
# Directory helper
# ---------------------------------------------------------------------------

def ensure_client_memory_dirs(client_id: str, agent: str = "ads-agent") -> dict:
    if not is_memory_enabled():
        return {"enabled": False, "message": "Memory disabled"}

    client_dir = get_client_memory_dir(client_id)
    agent_dir = get_agent_memory_dir(client_id, agent)
    snapshots_dir = get_snapshots_dir(client_id, agent)

    for d in (client_dir, agent_dir, snapshots_dir):
        d.mkdir(parents=True, exist_ok=True)

    return {
        "enabled": True,
        "client_dir": str(client_dir),
        "agent_dir": str(agent_dir),
        "snapshots_dir": str(snapshots_dir),
    }


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


# ---------------------------------------------------------------------------
# Atomic-ish write helper
# ---------------------------------------------------------------------------

def _write_json_safe(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Profile functions
# ---------------------------------------------------------------------------

def default_profile(client_id: str) -> dict:
    return {
        "client_id": client_id,
        "display_name": client_id,
        "timezone": "America/Argentina/Buenos_Aires",
        "currency": "ARS",
        "business_goal": "campaign_performance",
        "default_cpa_target": 2000,
        "notes": [],
    }


def read_profile(client_id: str) -> dict:
    if not is_memory_enabled():
        profile = default_profile(client_id)
        profile["_memory_enabled"] = False
        return profile

    profile_path = get_client_memory_dir(client_id) / "profile.json"

    if not profile_path.exists():
        return default_profile(client_id)

    try:
        return json.loads(profile_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        print(f"[MemPalace] Warning: corrupt profile.json for {client_id}: {error}", file=sys.stderr)
        profile = default_profile(client_id)
        profile["_warning"] = "profile.json was unreadable; using defaults"
        return profile


def write_profile(client_id: str, profile: dict) -> dict:
    if not is_memory_enabled():
        return {"ok": False, "message": "Memory disabled"}

    ensure_client_memory_dirs(client_id)
    profile_path = get_client_memory_dir(client_id) / "profile.json"

    try:
        _write_json_safe(profile_path, profile)
        return {"ok": True, "path": str(profile_path)}
    except OSError as error:
        print(f"[MemPalace] Warning: could not write profile.json: {error}", file=sys.stderr)
        return {"ok": False, "message": str(error)}


# ---------------------------------------------------------------------------
# Snapshot functions
# ---------------------------------------------------------------------------

def write_snapshot(
    client_id: str,
    snapshot: dict,
    agent: str = "ads-agent",
    request_type: str = "summary",
) -> dict:
    if not is_memory_enabled():
        return {"ok": False, "message": "Memory disabled"}

    ensure_client_memory_dirs(client_id, agent)
    snapshots_dir = get_snapshots_dir(client_id, agent)

    timestamp = _utc_now_iso()
    filename_ts = _utc_now_filename()
    safe_req = sanitize_path_part(request_type)
    filename = f"{filename_ts}_{safe_req}.json"
    snapshot_path = snapshots_dir / filename

    full_snapshot = {
        "timestamp": timestamp,
        "client_id": client_id,
        "agent": agent,
        "request_type": request_type,
        **snapshot,
    }

    try:
        _write_json_safe(snapshot_path, full_snapshot)
    except OSError as error:
        print(f"[MemPalace] Warning: could not write snapshot: {error}", file=sys.stderr)
        return {"ok": False, "message": str(error)}

    result = {"ok": True, "path": str(snapshot_path)}

    if request_type == "summary":
        latest_path = get_agent_memory_dir(client_id, agent) / "latest_summary.json"
        try:
            _write_json_safe(latest_path, full_snapshot)
            result["latest_summary_path"] = str(latest_path)
        except OSError as error:
            print(f"[MemPalace] Warning: could not update latest_summary.json: {error}", file=sys.stderr)
            result["latest_summary_warning"] = str(error)

    return result


# ---------------------------------------------------------------------------
# Recommendation ID helper
# ---------------------------------------------------------------------------

def _recommendation_id(client_id: str, rec: dict) -> str:
    raw = "|".join([
        client_id,
        rec.get("area", ""),
        rec.get("action", ""),
        rec.get("rationale", ""),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Recommendations JSONL
# ---------------------------------------------------------------------------

def append_recommendations(
    client_id: str,
    recommendations: list,
    agent: str = "ads-agent",
) -> dict:
    if not is_memory_enabled():
        return {"ok": False, "message": "Memory disabled"}

    if not recommendations:
        return {"ok": True, "written": 0}

    ensure_client_memory_dirs(client_id, agent)
    rec_path = get_agent_memory_dir(client_id, agent) / "recommendations.jsonl"
    timestamp = _utc_now_iso()

    try:
        with rec_path.open("a", encoding="utf-8") as f:
            for rec in recommendations:
                line = {
                    "timestamp": timestamp,
                    "recommendation_id": _recommendation_id(client_id, rec),
                    "status": "open",
                    **rec,
                }
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        return {"ok": True, "written": len(recommendations), "path": str(rec_path)}
    except OSError as error:
        print(f"[MemPalace] Warning: could not append recommendations: {error}", file=sys.stderr)
        return {"ok": False, "message": str(error)}


# ---------------------------------------------------------------------------
# Insights JSONL
# ---------------------------------------------------------------------------

def append_insight(
    client_id: str,
    insight: dict,
    agent: str = "ads-agent",
) -> dict:
    if not is_memory_enabled():
        return {"ok": False, "message": "Memory disabled"}

    ensure_client_memory_dirs(client_id, agent)
    insights_path = get_agent_memory_dir(client_id, agent) / "insights.jsonl"
    timestamp = _utc_now_iso()

    line = {
        "timestamp": timestamp,
        "insight_type": insight.get("insight_type", "note"),
        "summary": insight.get("summary", ""),
        "evidence": insight.get("evidence", {}),
        **{k: v for k, v in insight.items() if k not in {"insight_type", "summary", "evidence"}},
    }

    try:
        with insights_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        return {"ok": True, "path": str(insights_path)}
    except OSError as error:
        print(f"[MemPalace] Warning: could not append insight: {error}", file=sys.stderr)
        return {"ok": False, "message": str(error)}


# ---------------------------------------------------------------------------
# Latest summary
# ---------------------------------------------------------------------------

def read_latest_summary(client_id: str, agent: str = "ads-agent") -> Optional[dict]:
    if not is_memory_enabled():
        return None

    latest_path = get_agent_memory_dir(client_id, agent) / "latest_summary.json"

    if not latest_path.exists():
        return None

    try:
        return json.loads(latest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        print(f"[MemPalace] Warning: corrupt latest_summary.json: {error}", file=sys.stderr)
        return {"warning": "corrupt latest_summary.json"}


# ---------------------------------------------------------------------------
# Recent snapshots
# ---------------------------------------------------------------------------

def read_recent_snapshots(
    client_id: str,
    agent: str = "ads-agent",
    limit: Optional[int] = None,
) -> list:
    if not is_memory_enabled():
        return []

    snapshots_dir = get_snapshots_dir(client_id, agent)

    if not snapshots_dir.exists():
        return []

    if limit is None:
        limit = get_max_recent_snapshots()

    files = sorted(snapshots_dir.glob("*.json"), reverse=True)[:limit]
    results = []

    for f in files:
        try:
            results.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as error:
            print(f"[MemPalace] Warning: skipping corrupt snapshot {f.name}: {error}", file=sys.stderr)
            results.append({"warning": f"corrupt snapshot: {f.name}"})

    return results

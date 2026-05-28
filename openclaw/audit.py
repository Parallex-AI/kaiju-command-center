import os
import json
from datetime import datetime, timezone
from pathlib import Path


def is_audit_enabled() -> bool:
    val = os.getenv("OPENCLAW_AUDIT_ENABLED", "true").strip().lower()
    return val not in ("false", "0", "no", "off")


def get_audit_root() -> Path:
    env_root = os.getenv("OPENCLAW_AUDIT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    # Default: openclaw/audit/ under repo root
    return Path(__file__).resolve().parent / "audit"


def build_audit_event(
    openclaw_response: dict,
    normalized_payload: dict | None = None,
) -> dict:
    oc = openclaw_response.get("openclaw") or {}
    errors = openclaw_response.get("errors") or []
    warnings = openclaw_response.get("warnings") or []

    event = {
        "timestamp": oc.get("started_at") or datetime.now(timezone.utc).isoformat(),
        "request_id": oc.get("request_id", ""),
        "trace_id": oc.get("trace_id", ""),
        "tenant": oc.get("tenant", ""),
        "user_id": oc.get("user_id", ""),
        "channel": oc.get("channel", ""),
        "agent": oc.get("agent", ""),
        "request": (normalized_payload or {}).get("request"),
        "execution_mode": oc.get("execution_mode", ""),
        "ok": openclaw_response.get("ok", False),
        "duration_ms": oc.get("duration_ms", 0),
        "error_codes": [e.get("code") for e in errors if isinstance(e, dict)],
        "warning_count": len(warnings),
        "source": "openclaw",
    }

    # Only include tenant_id if present
    tenant_id = oc.get("tenant_id")
    if tenant_id is not None:
        event["tenant_id"] = tenant_id

    return event


def append_audit_event(event: dict) -> dict:
    if not is_audit_enabled():
        return {"ok": False, "skipped": True, "reason": "audit disabled"}

    try:
        audit_root = get_audit_root()
        audit_root.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        audit_file = audit_root / f"{date_str}.jsonl"

        with open(audit_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, default=str) + "\n")

        return {"ok": True, "path": str(audit_file)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

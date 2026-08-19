import hashlib
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    import fcntl as _fcntl
    _HAS_FCNTL = True
except ImportError:
    _fcntl = None
    _HAS_FCNTL = False


def is_audit_enabled() -> bool:
    val = os.getenv("OPENCLAW_AUDIT_ENABLED", "true").strip().lower()
    return val not in ("false", "0", "no", "off")


def get_audit_root() -> Path:
    env_root = os.getenv("OPENCLAW_AUDIT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    # Default: openclaw/audit/ under repo root
    return Path(__file__).resolve().parent / "audit"


def _compute_file_digest(path: Path) -> str:
    """SHA-256 of all file bytes; empty string if file is missing or empty."""
    try:
        data = path.read_bytes()
        if not data:
            return ""
        return hashlib.sha256(data).hexdigest()
    except (FileNotFoundError, OSError):
        return ""


def _next_audit_seq(path: Path) -> int:
    """Count of non-empty lines in file plus 1; returns 1 if file is missing or empty."""
    try:
        count = sum(
            1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        )
        return count + 1
    except (FileNotFoundError, OSError):
        return 1


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


def build_credential_audit_event(
    tenant_id: str,
    client_id: str,
    integration_type: str,
    operation: str,
    ok: bool,
    request_id: str = "",
    trace_id: str = "",
    error_codes: Optional[List[str]] = None,
) -> Dict:
    """
    Build a safe audit event for admin credential operations.

    Never includes secret values, credential_ref, secret_id, customer_id,
    login_customer_id, or any payload echo.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "credential_operation",
        "tenant_id": tenant_id,
        "client_id": client_id,
        "integration_type": integration_type,
        "operation": operation,
        "ok": ok,
        "error_codes": error_codes or [],
        "request_id": request_id or "",
        "trace_id": trace_id or "",
        "source": "openclaw_admin",
    }


def build_live_guard_audit_event(
    operation: str,
    ok: bool,
    event_type: str = "live_gate_check",
    error_codes: Optional[List[str]] = None,
    request_id: str = "",
    trace_id: str = "",
    live_api_tested: bool = False,
    live_enabled: bool = False,
    approval_present: bool = False,
    approval_valid: bool = False,
    credential_status: str = "",
    live_gate_allowed: bool = False,
) -> Dict:
    """
    Build a safe audit event for live guard/preflight checks.

    Never includes tenant_id, client_id, approval_id, credential_ref,
    secret_id, customer_id, login_customer_id, refresh_token, access_token,
    developer_token, client_secret, or any secret payload values.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "integration_type": "google_ads",
        "operation": operation,
        "ok": ok,
        "live_enabled": live_enabled,
        "approval_present": approval_present,
        "approval_valid": approval_valid,
        "credential_status": credential_status,
        "live_gate_allowed": live_gate_allowed,
        "live_api_tested": live_api_tested,
        "error_codes": error_codes or [],
        "request_id": request_id or "",
        "trace_id": trace_id or "",
        "source": "server_live_guard",
    }


def append_audit_event(event: dict) -> dict:
    if not is_audit_enabled():
        return {"ok": False, "skipped": True, "reason": "audit disabled"}

    try:
        audit_root = get_audit_root()
        audit_root.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        audit_file = audit_root / f"{date_str}.jsonl"

        lock_used = False

        if _HAS_FCNTL:
            # Compute seq and file_digest while holding an exclusive file lock so
            # concurrent writers in the same process group cannot race on the chain.
            audit_file.touch(exist_ok=True)
            with open(audit_file, "r+b") as fh:
                _fcntl.flock(fh.fileno(), _fcntl.LOCK_EX)
                current_bytes = fh.read()
                file_digest = hashlib.sha256(current_bytes).hexdigest() if current_bytes else ""
                seq = (
                    sum(
                        1
                        for line in current_bytes.decode("utf-8", errors="replace").splitlines()
                        if line.strip()
                    )
                    + 1
                )
                event["seq"] = seq
                event["file_digest"] = file_digest
                line_bytes = (json.dumps(event, default=str) + "\n").encode("utf-8")
                fh.seek(0, 2)
                fh.write(line_bytes)
                fh.flush()
                _fcntl.flock(fh.fileno(), _fcntl.LOCK_UN)
            lock_used = True
        else:
            # Fallback: no locking available (non-Unix platforms).
            # seq/file_digest may have gaps if multiple writers race.
            file_digest = _compute_file_digest(audit_file)
            seq = _next_audit_seq(audit_file)
            event["seq"] = seq
            event["file_digest"] = file_digest
            with open(audit_file, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, default=str) + "\n")

        return {
            "ok": True,
            "path": str(audit_file),
            "seq": seq,
            "file_digest": file_digest,
            "lock_used": lock_used,
        }
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}

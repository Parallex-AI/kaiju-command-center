import uuid
from datetime import datetime, timezone

OPENCLAW_VERSION = "0.1.0"


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def generate_trace_id() -> str:
    return f"trace_{uuid.uuid4().hex[:16]}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_error(
    code: str,
    message: str,
    recoverable: bool = False,
    source: str = "openclaw",
) -> dict:
    return {
        "code": code,
        "message": message,
        "recoverable": recoverable,
        "source": source,
    }


def make_openclaw_envelope(
    ok: bool,
    request_id: str,
    trace_id: str,
    tenant: str,
    agent: str,
    execution_mode: str,
    started_at: str,
    finished_at: str,
    duration_ms: int,
    data: dict = None,
    errors: list = None,
    warnings: list = None,
) -> dict:
    return {
        "ok": ok,
        "openclaw": {
            "version": OPENCLAW_VERSION,
            "request_id": request_id,
            "trace_id": trace_id,
            "tenant": tenant,
            "agent": agent,
            "execution_mode": execution_mode,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": duration_ms,
        },
        "data": data if data is not None else {},
        "errors": errors if errors is not None else [],
        "warnings": warnings if warnings is not None else [],
    }

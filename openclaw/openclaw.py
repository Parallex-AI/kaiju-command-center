from pathlib import Path as _Path
import sys as _sys
import time

_OPENCLAW_DIR = str(_Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in _sys.path:
    _sys.path.insert(0, _OPENCLAW_DIR)

_ROUTER_DIR = str(_Path(__file__).resolve().parents[1] / "agents" / "router")
if _ROUTER_DIR not in _sys.path:
    _sys.path.insert(0, _ROUTER_DIR)

from schemas import (
    generate_request_id,
    generate_trace_id,
    utc_now_iso,
    make_error,
    make_openclaw_envelope,
)
from registry import get_agent
from policy import validate_request_policy
from context import resolve_context
from router import route_request


def process_request(payload: dict) -> dict:
    started_at = utc_now_iso()
    t0 = time.monotonic()
    request_id = generate_request_id()
    trace_id = generate_trace_id()

    context = resolve_context(payload if isinstance(payload, dict) else {})
    context_warnings = context.get("warnings", [])

    agent = payload.get("agent", "ads-agent") if isinstance(payload, dict) else "ads-agent"
    request_type = payload.get("request", "summary") if isinstance(payload, dict) else "summary"
    client_id = context["client_id"]

    normalized = {
        "client_id": client_id,
        "agent": agent,
        "request": request_type,
    }

    policy_ok, policy_errors = validate_request_policy(normalized)

    if not policy_ok:
        finished_at = utc_now_iso()
        duration_ms = int((time.monotonic() - t0) * 1000)
        return make_openclaw_envelope(
            ok=False,
            request_id=request_id,
            trace_id=trace_id,
            tenant=client_id,
            agent=agent,
            execution_mode="none",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            data={},
            errors=policy_errors,
            warnings=context_warnings,
        )

    try:
        router_response = route_request(normalized)
    except Exception as exc:
        finished_at = utc_now_iso()
        duration_ms = int((time.monotonic() - t0) * 1000)
        return make_openclaw_envelope(
            ok=False,
            request_id=request_id,
            trace_id=trace_id,
            tenant=client_id,
            agent=agent,
            execution_mode="unknown",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            data={},
            errors=[make_error("internal_error", "An internal error occurred.", source="openclaw")],
            warnings=context_warnings,
        )

    finished_at = utc_now_iso()
    duration_ms = int((time.monotonic() - t0) * 1000)

    ok = bool(router_response.get("ok"))
    execution_mode = router_response.get("execution_mode", "unknown")

    errors = []
    if not ok:
        errors.append(make_error(
            router_response.get("error", "router_error"),
            router_response.get("message", "Router returned an error."),
            source="router",
        ))

    return make_openclaw_envelope(
        ok=ok,
        request_id=request_id,
        trace_id=trace_id,
        tenant=client_id,
        agent=agent,
        execution_mode=execution_mode,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        data={"router_response": router_response},
        errors=errors,
        warnings=context_warnings,
    )

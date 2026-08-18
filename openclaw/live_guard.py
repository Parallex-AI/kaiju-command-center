"""
V5.19 Phase 5 — Server-side guard for future live Google Ads operations.

Provides reusable response builders and guard functions callable at adapter
boundaries before any live Google Ads operation.

Pure local logic. No GCP calls. No Google Ads API calls.
No credential fetch. No secret payload access. No environment variable reads.
Claude Code does not self-approve and does not execute live operations.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)

from live_gate import LiveGateInput, LiveGateResult, check_live_gate
from preflight import (
    LiveOperationPreflightInput,
    LiveOperationPreflightResult,
    check_live_operation_preflight,
)

LIVE_GUARD_INTEGRATION_TYPE = "google_ads"

# Keys that must never appear in a live guard response body.
LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS: frozenset = frozenset({
    "approval_id",
    "tenant_id",
    "client_id",
    "credential_ref",
    "secret_id",
    "customer_id",
    "login_customer_id",
    "refresh_token",
    "access_token",
    "developer_token",
    "client_secret",
})

# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def _base_guard_response(
    gate_result: LiveGateResult,
    approval_valid: bool,
    operation: str,
    sanitized_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "live_allowed": gate_result.allowed,
        "live_api_tested": False,
        "reasons": list(gate_result.reasons),
        "required_actions": list(gate_result.required_actions),
        "operation": operation,
        "integration_type": LIVE_GUARD_INTEGRATION_TYPE,
        "approval_valid": approval_valid,
        "sanitized_summary": sanitized_summary or {},
    }


def build_live_guard_denied_response(
    gate_result: LiveGateResult,
    approval_valid: bool = False,
    operation: str = "",
    sanitized_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a safe denied response dict from a live gate result.

    Never includes tenant_id, client_id, approval_id, credential fields,
    secret fields, or resource paths.
    """
    base = _base_guard_response(gate_result, approval_valid, operation, sanitized_summary)
    base.update({
        "ok": False,
        "error": "live_preflight_failed",
        "error_code": gate_result.error_code,
    })
    return base


def build_live_guard_allowed_response(
    gate_result: LiveGateResult,
    approval_valid: bool = True,
    operation: str = "",
    sanitized_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a safe allowed response dict from a live gate result.

    live_api_tested is always False — the guard does not execute the operation.
    """
    base = _base_guard_response(gate_result, approval_valid, operation, sanitized_summary)
    base.update({
        "ok": True,
        "error": None,
        "error_code": None,
    })
    return base


def response_has_no_forbidden_keys(d: Dict[str, Any]) -> bool:
    """Return True if no forbidden keys appear at the top level of d."""
    return not any(k in LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS for k in d)

# ---------------------------------------------------------------------------
# Guard functions
# ---------------------------------------------------------------------------

def guard_live_google_ads_operation(
    inp: LiveOperationPreflightInput,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the full live operation preflight check and return a safe response dict.

    For use at adapter boundaries where a real ApprovalRecord object is available.
    Returns denied response dict if any condition fails; allowed response if all pass.
    live_api_tested is always False — the guard never executes the operation.
    Never fetches credentials. Never calls GCP or Google Ads API.
    """
    result: LiveOperationPreflightResult = check_live_operation_preflight(inp, now=now)
    gate_result = LiveGateResult(
        allowed=result.live_gate_allowed,
        error_code=result.live_gate_error_code,
        reasons=result.reasons,
        required_actions=result.required_actions,
    )
    if not result.allowed:
        return build_live_guard_denied_response(
            gate_result,
            approval_valid=result.approval_valid,
            operation=inp.operation,
            sanitized_summary=result.sanitized_summary,
        )
    return build_live_guard_allowed_response(
        gate_result,
        approval_valid=result.approval_valid,
        operation=inp.operation,
        sanitized_summary=result.sanitized_summary,
    )


def guard_live_google_ads_from_signals(
    live_enabled: bool,
    approval_present: bool,
    approval_valid: bool,
    preflight_passed: bool,
    audit_enabled: bool,
    credential_configured: bool,
    credential_status: str,
    tenant_allowed: bool,
    client_allowed: bool,
    rollback_plan_present: bool,
    operator_confirmed: bool,
    operation: str = "",
) -> Dict[str, Any]:
    """
    Evaluate the live gate using pre-resolved boolean signals and return a safe response dict.

    For use by HTTP routes where an ApprovalRecord object is not available.
    Constructs a LiveGateInput directly from the supplied signals.
    Never fetches credentials. Never calls GCP or Google Ads API.
    """
    gate_inp = LiveGateInput(
        live_enabled=live_enabled,
        approval_present=approval_present,
        approval_valid=approval_valid,
        preflight_passed=preflight_passed,
        audit_enabled=audit_enabled,
        credential_configured=credential_configured,
        credential_status=credential_status,
        tenant_allowed=tenant_allowed,
        client_allowed=client_allowed,
        rollback_plan_present=rollback_plan_present,
        operator_confirmed=operator_confirmed,
    )
    gate_result = check_live_gate(gate_inp)

    sanitized_summary: Dict[str, Any] = {
        "operation": operation,
        "integration_type": LIVE_GUARD_INTEGRATION_TYPE,
        "live_enabled": live_enabled,
        "approval_present": approval_present,
        "approval_valid": approval_valid,
        "preflight_passed": preflight_passed,
        "audit_enabled": audit_enabled,
        "credential_status": credential_status,
        "tenant_allowed": tenant_allowed,
        "client_allowed": client_allowed,
        "rollback_plan_present": rollback_plan_present,
        "operator_confirmed": operator_confirmed,
        "live_gate_allowed": gate_result.allowed,
        "error_code": gate_result.error_code,
    }

    if not gate_result.allowed:
        return build_live_guard_denied_response(
            gate_result,
            approval_valid=approval_valid,
            operation=operation,
            sanitized_summary=sanitized_summary,
        )
    return build_live_guard_allowed_response(
        gate_result,
        approval_valid=approval_valid,
        operation=operation,
        sanitized_summary=sanitized_summary,
    )

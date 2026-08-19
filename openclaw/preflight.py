"""
V5.19 Phase 4 — Live operation preflight checker.

Composes approval record validation (Phase 3) with the live readiness gate
(Phase 2) into a single check_live_operation_preflight() call.

Pure local logic. No GCP calls. No Google Ads API calls.
No credentials read or written. No environment variable reads.
Claude Code does not self-approve.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)

from approval import ApprovalRecord, is_approval_valid
from live_gate import LiveGateInput, LiveGateResult, check_live_gate

# ---------------------------------------------------------------------------
# Input / Result
# ---------------------------------------------------------------------------

@dataclass
class LiveOperationPreflightInput:
    tenant_id: str
    client_id: str
    integration_type: str
    operation: str
    live_enabled: bool
    approval_record: Optional[ApprovalRecord]
    required_approval_scope: str
    preflight_passed: bool
    audit_enabled: bool
    credential_configured: bool
    credential_status: str
    tenant_allowed: bool
    client_allowed: bool
    rollback_plan_present: bool
    operator_confirmed: bool


@dataclass
class LiveOperationPreflightResult:
    allowed: bool
    error_code: Optional[str]
    reasons: List[str]
    required_actions: List[str]
    approval_valid: bool
    live_gate_allowed: bool
    live_gate_error_code: Optional[str]
    sanitized_summary: Dict[str, Any]

# ---------------------------------------------------------------------------
# Preflight function
# ---------------------------------------------------------------------------

def check_live_operation_preflight(
    inp: LiveOperationPreflightInput,
    now: Optional[str] = None,
) -> LiveOperationPreflightResult:
    """
    Compose approval validation and live gate check into a single preflight result.

    Validates the approval record (if present) against the required scope,
    tenant, client, and integration type, then passes all signals to
    check_live_gate(). allowed=True only when every condition passes.

    Never reads credentials, calls GCP, or calls Google Ads API.
    """
    if inp.approval_record is None:
        approval_present = False
        approval_valid = False
    else:
        approval_valid = is_approval_valid(
            inp.approval_record,
            required_scope=inp.required_approval_scope,
            tenant_id=inp.tenant_id,
            client_id=inp.client_id,
            integration_type=inp.integration_type,
            now=now,
        )
        approval_present = True

    gate_inp = LiveGateInput(
        live_enabled=inp.live_enabled,
        approval_present=approval_present,
        approval_valid=approval_valid,
        preflight_passed=inp.preflight_passed,
        audit_enabled=inp.audit_enabled,
        credential_configured=inp.credential_configured,
        credential_status=inp.credential_status,
        tenant_allowed=inp.tenant_allowed,
        client_allowed=inp.client_allowed,
        rollback_plan_present=inp.rollback_plan_present,
        operator_confirmed=inp.operator_confirmed,
    )
    gate_result = check_live_gate(gate_inp)

    sanitized_summary: Dict[str, Any] = {
        "operation": inp.operation,
        "integration_type": inp.integration_type,
        "live_enabled": inp.live_enabled,
        "approval_present": approval_present,
        "approval_valid": approval_valid,
        "preflight_passed": inp.preflight_passed,
        "audit_enabled": inp.audit_enabled,
        "credential_status": inp.credential_status,
        "tenant_allowed": inp.tenant_allowed,
        "client_allowed": inp.client_allowed,
        "rollback_plan_present": inp.rollback_plan_present,
        "operator_confirmed": inp.operator_confirmed,
        "live_gate_allowed": gate_result.allowed,
        "error_code": gate_result.error_code,
    }

    return LiveOperationPreflightResult(
        allowed=gate_result.allowed,
        error_code=gate_result.error_code,
        reasons=gate_result.reasons,
        required_actions=gate_result.required_actions,
        approval_valid=approval_valid,
        live_gate_allowed=gate_result.allowed,
        live_gate_error_code=gate_result.error_code,
        sanitized_summary=sanitized_summary,
    )

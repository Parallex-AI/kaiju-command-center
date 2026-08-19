"""
V5.19 Phase 2 — Live Google Ads readiness gate.

Pure local evaluation of pre-supplied readiness signals.
No external I/O. No GCP calls. No Google Ads API calls.
GOOGLE_ADS_LIVE_ENABLED=false by default and must remain false
unless all gate conditions are explicitly satisfied.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)

# ---------------------------------------------------------------------------
# Denial codes
# ---------------------------------------------------------------------------

class LiveGateDenialCode:
    LIVE_DISABLED = "live_disabled"
    APPROVAL_MISSING = "approval_missing"
    APPROVAL_INVALID = "approval_invalid"
    PREFLIGHT_MISSING = "preflight_missing"
    AUDIT_DISABLED = "audit_disabled"
    CREDENTIAL_MISSING = "credential_missing"
    CREDENTIAL_NOT_ACTIVE = "credential_not_active"
    TENANT_NOT_ALLOWED = "tenant_not_allowed"
    CLIENT_NOT_ALLOWED = "client_not_allowed"
    ROLLBACK_PLAN_MISSING = "rollback_plan_missing"
    OPERATOR_CONFIRMATION_MISSING = "operator_confirmation_missing"


ACTIVE_CREDENTIAL_STATUS = "ACTIVE"

# ---------------------------------------------------------------------------
# Input / Result
# ---------------------------------------------------------------------------

@dataclass
class LiveGateInput:
    live_enabled: bool
    approval_present: bool
    approval_valid: bool
    preflight_passed: bool
    audit_enabled: bool
    credential_configured: bool
    credential_status: str
    tenant_allowed: bool
    client_allowed: bool
    rollback_plan_present: bool
    operator_confirmed: bool


@dataclass
class LiveGateResult:
    allowed: bool
    error_code: Optional[str]
    reasons: List[str]
    required_actions: List[str]

# ---------------------------------------------------------------------------
# Gate function
# ---------------------------------------------------------------------------

def check_live_gate(inp: LiveGateInput) -> LiveGateResult:
    """
    Evaluate all live-mode readiness conditions in priority order.

    Returns LiveGateResult with allowed=True only when every condition passes.
    Never reads credentials, calls GCP, or calls Google Ads API.
    """
    if not inp.live_enabled:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.LIVE_DISABLED,
            reasons=["Live mode is disabled (GOOGLE_ADS_LIVE_ENABLED=false)."],
            required_actions=[
                "Enable live mode only after all other gate conditions are satisfied"
                " and explicit operator approval is obtained."
            ],
        )

    if not inp.approval_present:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.APPROVAL_MISSING,
            reasons=["No operator approval record is present for this tenant/client."],
            required_actions=[
                "Create an approval record with operator identity, scope, tenant,"
                " client, rollback plan, and expiry."
            ],
        )

    if not inp.approval_valid:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.APPROVAL_INVALID,
            reasons=["The operator approval record is present but invalid (expired or revoked)."],
            required_actions=["Issue a new unexpired, unrevoked approval record."],
        )

    if not inp.preflight_passed:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.PREFLIGHT_MISSING,
            reasons=["Preflight checks did not pass."],
            required_actions=["Run and resolve all preflight checks before attempting live mode."],
        )

    if not inp.audit_enabled:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.AUDIT_DISABLED,
            reasons=["Audit logging is disabled (OPENCLAW_AUDIT_ENABLED=false)."],
            required_actions=["Enable audit logging before activating live mode."],
        )

    if not inp.credential_configured:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.CREDENTIAL_MISSING,
            reasons=["No credential bundle is configured for this tenant/client."],
            required_actions=["Write a complete credential bundle before activating live mode."],
        )

    if inp.credential_status != ACTIVE_CREDENTIAL_STATUS:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE,
            reasons=[f"Credential status is '{inp.credential_status}', not ACTIVE."],
            required_actions=[
                "Ensure credential is written and structurally valid (status=ACTIVE)"
                " before live mode."
            ],
        )

    if not inp.tenant_allowed:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.TENANT_NOT_ALLOWED,
            reasons=["The requesting token is not authorized for this tenant."],
            required_actions=[
                "Configure OPENCLAW_TENANT_KEYS to allow this token for the target tenant."
            ],
        )

    if not inp.client_allowed:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.CLIENT_NOT_ALLOWED,
            reasons=["The requesting token is not authorized for this client."],
            required_actions=["Verify client-level authorization before activating live mode."],
        )

    if not inp.rollback_plan_present:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.ROLLBACK_PLAN_MISSING,
            reasons=["No rollback plan is documented in the approval record."],
            required_actions=["Add a rollback plan to the approval record before proceeding."],
        )

    if not inp.operator_confirmed:
        return LiveGateResult(
            allowed=False,
            error_code=LiveGateDenialCode.OPERATOR_CONFIRMATION_MISSING,
            reasons=["Operator has not confirmed readiness for live mode."],
            required_actions=["Obtain explicit operator confirmation before activating live mode."],
        )

    return LiveGateResult(
        allowed=True,
        error_code=None,
        reasons=["All gate conditions satisfied."],
        required_actions=[],
    )

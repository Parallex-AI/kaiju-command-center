"""
V5.19 Phase 4 — Live operation preflight checker demo/test script.

Verifies check_live_operation_preflight() for all 16 denial conditions,
the allow path, and the sanitized summary safety invariant.

Pure local logic. No GCP, no Google Ads API, no real credentials,
no real env vars, no file I/O (approval records are in-memory only).
"""

import sys
from pathlib import Path

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
_ADS_AGENT_DIR = str(Path(__file__).resolve().parents[1] / "agents" / "ads-agent")
for _p in (_OPENCLAW_DIR, _ADS_AGENT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from approval import (
    ApprovalRecord,
    ApprovalScope,
    ApprovalStatus,
    create_approval_record,
)
from live_gate import LiveGateDenialCode
from preflight import (
    LiveOperationPreflightInput,
    LiveOperationPreflightResult,
    check_live_operation_preflight,
)

_PASS = "[PASS]"
_FAIL = "[FAIL]"
_failures: list = []


def _assert(condition: bool, label: str) -> bool:
    tag = _PASS if condition else _FAIL
    print(f"  {tag} {label}")
    if not condition:
        _failures.append(label)
    return condition


_TENANT = "preflight-tenant"
_CLIENT = "preflight-client"
_INTEGRATION = "google_ads"
_SCOPE = ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION
_OPERATOR = "preflight-operator"
_REASON = "Controlled preflight testing"
_ROLLBACK = "Disable live mode and revoke approval"


def _make_valid_approval(**overrides) -> ApprovalRecord:
    base = dict(
        tenant_id=_TENANT,
        client_id=_CLIENT,
        integration_type=_INTEGRATION,
        scope=_SCOPE,
        operator_label=_OPERATOR,
        reason=_REASON,
        rollback_plan=_ROLLBACK,
        status=ApprovalStatus.APPROVED,
    )
    base.update(overrides)
    return create_approval_record(**base)


def _all_pass_input(**overrides) -> LiveOperationPreflightInput:
    base = dict(
        tenant_id=_TENANT,
        client_id=_CLIENT,
        integration_type=_INTEGRATION,
        operation="google_ads_metrics_fetch",
        live_enabled=True,
        approval_record=_make_valid_approval(),
        required_approval_scope=_SCOPE,
        preflight_passed=True,
        audit_enabled=True,
        credential_configured=True,
        credential_status="ACTIVE",
        tenant_allowed=True,
        client_allowed=True,
        rollback_plan_present=True,
        operator_confirmed=True,
    )
    base.update(overrides)
    return LiveOperationPreflightInput(**base)


# ---------------------------------------------------------------------------
# Test 1 — live disabled
# ---------------------------------------------------------------------------
print("\n── Test 1: live disabled")
r = check_live_operation_preflight(_all_pass_input(live_enabled=False))
_assert(r.allowed is False, "live disabled: allowed=False")
_assert(r.error_code == LiveGateDenialCode.LIVE_DISABLED, "live disabled: error_code=live_disabled")
_assert(r.live_gate_allowed is False, "live disabled: live_gate_allowed=False")
_assert(len(r.reasons) > 0, "live disabled: reasons non-empty")

# ---------------------------------------------------------------------------
# Test 2 — missing approval
# ---------------------------------------------------------------------------
print("\n── Test 2: missing approval")
r = check_live_operation_preflight(_all_pass_input(approval_record=None))
_assert(r.allowed is False, "missing approval: allowed=False")
_assert(r.error_code == LiveGateDenialCode.APPROVAL_MISSING, "missing approval: error_code=approval_missing")
_assert(r.approval_valid is False, "missing approval: approval_valid=False")
_assert(r.sanitized_summary["approval_present"] is False, "missing approval: summary.approval_present=False")

# ---------------------------------------------------------------------------
# Test 3 — expired approval
# ---------------------------------------------------------------------------
print("\n── Test 3: expired approval")
expired_rec = _make_valid_approval(expires_at="2020-01-01T00:00:00Z")
r = check_live_operation_preflight(_all_pass_input(approval_record=expired_rec))
_assert(r.allowed is False, "expired approval: allowed=False")
_assert(r.error_code == LiveGateDenialCode.APPROVAL_INVALID, "expired approval: error_code=approval_invalid")
_assert(r.approval_valid is False, "expired approval: approval_valid=False")

# ---------------------------------------------------------------------------
# Test 4 — revoked approval
# ---------------------------------------------------------------------------
print("\n── Test 4: revoked approval")
revoked_rec = _make_valid_approval(status=ApprovalStatus.REVOKED)
r = check_live_operation_preflight(_all_pass_input(approval_record=revoked_rec))
_assert(r.allowed is False, "revoked approval: allowed=False")
_assert(r.error_code == LiveGateDenialCode.APPROVAL_INVALID, "revoked approval: error_code=approval_invalid")
_assert(r.approval_valid is False, "revoked approval: approval_valid=False")

# ---------------------------------------------------------------------------
# Test 5 — wrong scope
# ---------------------------------------------------------------------------
print("\n── Test 5: wrong scope")
r = check_live_operation_preflight(
    _all_pass_input(required_approval_scope=ApprovalScope.GOOGLE_ADS_CREDENTIAL_ROTATION)
)
_assert(r.allowed is False, "wrong scope: allowed=False")
_assert(r.error_code == LiveGateDenialCode.APPROVAL_INVALID, "wrong scope: error_code=approval_invalid")
_assert(r.approval_valid is False, "wrong scope: approval_valid=False")

# ---------------------------------------------------------------------------
# Test 6 — wrong tenant
# ---------------------------------------------------------------------------
print("\n── Test 6: wrong tenant")
r = check_live_operation_preflight(_all_pass_input(tenant_id="other-tenant"))
_assert(r.allowed is False, "wrong tenant: allowed=False")
_assert(r.error_code == LiveGateDenialCode.APPROVAL_INVALID, "wrong tenant: error_code=approval_invalid")
_assert(r.approval_valid is False, "wrong tenant: approval_valid=False")

# ---------------------------------------------------------------------------
# Test 7 — wrong client
# ---------------------------------------------------------------------------
print("\n── Test 7: wrong client")
r = check_live_operation_preflight(_all_pass_input(client_id="other-client"))
_assert(r.allowed is False, "wrong client: allowed=False")
_assert(r.error_code == LiveGateDenialCode.APPROVAL_INVALID, "wrong client: error_code=approval_invalid")
_assert(r.approval_valid is False, "wrong client: approval_valid=False")

# ---------------------------------------------------------------------------
# Test 8 — missing preflight
# ---------------------------------------------------------------------------
print("\n── Test 8: missing preflight")
r = check_live_operation_preflight(_all_pass_input(preflight_passed=False))
_assert(r.allowed is False, "missing preflight: allowed=False")
_assert(r.error_code == LiveGateDenialCode.PREFLIGHT_MISSING, "missing preflight: error_code=preflight_missing")
_assert(r.approval_valid is True, "missing preflight: approval_valid=True (approval ok)")

# ---------------------------------------------------------------------------
# Test 9 — audit disabled
# ---------------------------------------------------------------------------
print("\n── Test 9: audit disabled")
r = check_live_operation_preflight(_all_pass_input(audit_enabled=False))
_assert(r.allowed is False, "audit disabled: allowed=False")
_assert(r.error_code == LiveGateDenialCode.AUDIT_DISABLED, "audit disabled: error_code=audit_disabled")

# ---------------------------------------------------------------------------
# Test 10 — credential missing
# ---------------------------------------------------------------------------
print("\n── Test 10: credential missing")
r = check_live_operation_preflight(_all_pass_input(credential_configured=False))
_assert(r.allowed is False, "credential missing: allowed=False")
_assert(r.error_code == LiveGateDenialCode.CREDENTIAL_MISSING, "credential missing: error_code=credential_missing")

# ---------------------------------------------------------------------------
# Test 11 — credential REVOKED (not active)
# ---------------------------------------------------------------------------
print("\n── Test 11: credential REVOKED")
r = check_live_operation_preflight(_all_pass_input(credential_status="REVOKED"))
_assert(r.allowed is False, "credential REVOKED: allowed=False")
_assert(r.error_code == LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE, "credential REVOKED: error_code=credential_not_active")
_assert(r.sanitized_summary["credential_status"] == "REVOKED", "credential REVOKED: summary.credential_status=REVOKED")

# ---------------------------------------------------------------------------
# Test 12 — tenant not allowed
# ---------------------------------------------------------------------------
print("\n── Test 12: tenant not allowed")
r = check_live_operation_preflight(_all_pass_input(tenant_allowed=False))
_assert(r.allowed is False, "tenant not allowed: allowed=False")
_assert(r.error_code == LiveGateDenialCode.TENANT_NOT_ALLOWED, "tenant not allowed: error_code=tenant_not_allowed")

# ---------------------------------------------------------------------------
# Test 13 — client not allowed
# ---------------------------------------------------------------------------
print("\n── Test 13: client not allowed")
r = check_live_operation_preflight(_all_pass_input(client_allowed=False))
_assert(r.allowed is False, "client not allowed: allowed=False")
_assert(r.error_code == LiveGateDenialCode.CLIENT_NOT_ALLOWED, "client not allowed: error_code=client_not_allowed")

# ---------------------------------------------------------------------------
# Test 14 — rollback plan missing
# ---------------------------------------------------------------------------
print("\n── Test 14: rollback plan missing")
r = check_live_operation_preflight(_all_pass_input(rollback_plan_present=False))
_assert(r.allowed is False, "rollback missing: allowed=False")
_assert(r.error_code == LiveGateDenialCode.ROLLBACK_PLAN_MISSING, "rollback missing: error_code=rollback_plan_missing")

# ---------------------------------------------------------------------------
# Test 15 — operator confirmation missing
# ---------------------------------------------------------------------------
print("\n── Test 15: operator confirmation missing")
r = check_live_operation_preflight(_all_pass_input(operator_confirmed=False))
_assert(r.allowed is False, "operator missing: allowed=False")
_assert(r.error_code == LiveGateDenialCode.OPERATOR_CONFIRMATION_MISSING, "operator missing: error_code=operator_confirmation_missing")

# ---------------------------------------------------------------------------
# Test 16 — all conditions satisfied
# ---------------------------------------------------------------------------
print("\n── Test 16: allow path — all conditions satisfied")
r = check_live_operation_preflight(_all_pass_input())
_assert(r.allowed is True, "allow path: allowed=True")
_assert(r.error_code is None, "allow path: error_code=None")
_assert(r.approval_valid is True, "allow path: approval_valid=True")
_assert(r.live_gate_allowed is True, "allow path: live_gate_allowed=True")
_assert(r.live_gate_error_code is None, "allow path: live_gate_error_code=None")
_assert(len(r.reasons) > 0, "allow path: reasons non-empty")
_assert(r.required_actions == [], "allow path: required_actions=[]")

# ---------------------------------------------------------------------------
# Test 17 — sanitized summary contains no forbidden identifiers
# ---------------------------------------------------------------------------
print("\n── Test 17: sanitized summary safety")
summary = r.sanitized_summary
_assert("tenant_id" not in summary, "sanitized summary: tenant_id absent")
_assert("client_id" not in summary, "sanitized summary: client_id absent")
_assert("approval_id" not in summary, "sanitized summary: approval_id absent")
_assert("refresh_token" not in summary, "sanitized summary: refresh_token absent")
_assert("developer_token" not in summary, "sanitized summary: developer_token absent")
_assert("client_secret" not in summary, "sanitized summary: client_secret absent")
_assert(isinstance(summary.get("approval_present"), bool), "sanitized summary: approval_present is bool")
_assert(isinstance(summary.get("approval_valid"), bool), "sanitized summary: approval_valid is bool")
_assert(isinstance(summary.get("live_gate_allowed"), bool), "sanitized summary: live_gate_allowed is bool")
_assert("operation" in summary, "sanitized summary: operation present")
_assert("integration_type" in summary, "sanitized summary: integration_type present")

# ---------------------------------------------------------------------------
# Test 18 — wrong integration_type in preflight input → approval_invalid
# ---------------------------------------------------------------------------
print("\n── Test 18: wrong integration_type → approval_invalid")
r = check_live_operation_preflight(_all_pass_input(integration_type="facebook_ads"))
_assert(r.allowed is False, "wrong integration: allowed=False")
_assert(r.error_code == LiveGateDenialCode.APPROVAL_INVALID, "wrong integration: error_code=approval_invalid")
_assert(r.approval_valid is False, "wrong integration: approval_valid=False")

# ---------------------------------------------------------------------------
# Test 19 — credential_status CONFIGURED → credential_not_active
# ---------------------------------------------------------------------------
print("\n── Test 19: credential_status CONFIGURED → credential_not_active")
r = check_live_operation_preflight(_all_pass_input(credential_status="CONFIGURED"))
_assert(r.allowed is False, "credential CONFIGURED: allowed=False")
_assert(r.error_code == LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE, "credential CONFIGURED: error_code=credential_not_active")
_assert(r.sanitized_summary["credential_status"] == "CONFIGURED", "credential CONFIGURED: summary.credential_status=CONFIGURED")

# ---------------------------------------------------------------------------
# Test 20 — credential_status VALIDATION_FAILED → credential_not_active
# ---------------------------------------------------------------------------
print("\n── Test 20: credential_status VALIDATION_FAILED → credential_not_active")
r = check_live_operation_preflight(_all_pass_input(credential_status="VALIDATION_FAILED"))
_assert(r.allowed is False, "credential VALIDATION_FAILED: allowed=False")
_assert(r.error_code == LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE, "credential VALIDATION_FAILED: error_code=credential_not_active")
_assert(r.sanitized_summary["credential_status"] == "VALIDATION_FAILED", "credential VALIDATION_FAILED: summary.credential_status=VALIDATION_FAILED")

# ---------------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------------
print()
if _failures:
    print(f"[FAIL] {len(_failures)} assertion(s) failed:")
    for f in _failures:
        print(f"  - {f}")
    sys.exit(1)

print("All assertions passed.")

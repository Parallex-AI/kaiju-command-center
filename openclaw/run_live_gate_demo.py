"""
V5.19 Phase 2 — Live gate demo and test script.

Verifies check_live_gate() returns the correct denial code and allowed=False
for each of the 11 gate conditions, and allowed=True when all conditions pass.

Pure Python. No external I/O. No GCP. No Google Ads API.
GOOGLE_ADS_LIVE_ENABLED is not read by this script — LiveGateInput.live_enabled
is a pre-resolved signal, not an env var read.
"""

import sys
from pathlib import Path

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
_ADS_AGENT_DIR = str(Path(__file__).resolve().parents[1] / "agents" / "ads-agent")
for _p in (_OPENCLAW_DIR, _ADS_AGENT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from live_gate import (
    LiveGateDenialCode,
    LiveGateInput,
    check_live_gate,
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


def _all_pass_input(**overrides) -> LiveGateInput:
    """Return a LiveGateInput with all conditions satisfied, optionally overriding fields."""
    base = dict(
        live_enabled=True,
        approval_present=True,
        approval_valid=True,
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
    return LiveGateInput(**base)


# ---------------------------------------------------------------------------
# Test 1 — live_disabled
# ---------------------------------------------------------------------------
print("\n── Test 1: live_disabled")
r = check_live_gate(_all_pass_input(live_enabled=False))
_assert(r.allowed is False, "live_disabled: allowed=False")
_assert(r.error_code == LiveGateDenialCode.LIVE_DISABLED, "live_disabled: error_code=live_disabled")
_assert(len(r.reasons) > 0, "live_disabled: reasons non-empty")
_assert(len(r.required_actions) > 0, "live_disabled: required_actions non-empty")

# ---------------------------------------------------------------------------
# Test 2 — approval_missing
# ---------------------------------------------------------------------------
print("\n── Test 2: approval_missing")
r = check_live_gate(_all_pass_input(approval_present=False))
_assert(r.allowed is False, "approval_missing: allowed=False")
_assert(r.error_code == LiveGateDenialCode.APPROVAL_MISSING, "approval_missing: error_code=approval_missing")
_assert(len(r.reasons) > 0, "approval_missing: reasons non-empty")

# ---------------------------------------------------------------------------
# Test 3 — approval_invalid
# ---------------------------------------------------------------------------
print("\n── Test 3: approval_invalid")
r = check_live_gate(_all_pass_input(approval_valid=False))
_assert(r.allowed is False, "approval_invalid: allowed=False")
_assert(r.error_code == LiveGateDenialCode.APPROVAL_INVALID, "approval_invalid: error_code=approval_invalid")
_assert(len(r.reasons) > 0, "approval_invalid: reasons non-empty")

# ---------------------------------------------------------------------------
# Test 4 — preflight_missing
# ---------------------------------------------------------------------------
print("\n── Test 4: preflight_missing")
r = check_live_gate(_all_pass_input(preflight_passed=False))
_assert(r.allowed is False, "preflight_missing: allowed=False")
_assert(r.error_code == LiveGateDenialCode.PREFLIGHT_MISSING, "preflight_missing: error_code=preflight_missing")
_assert(len(r.reasons) > 0, "preflight_missing: reasons non-empty")

# ---------------------------------------------------------------------------
# Test 5 — audit_disabled
# ---------------------------------------------------------------------------
print("\n── Test 5: audit_disabled")
r = check_live_gate(_all_pass_input(audit_enabled=False))
_assert(r.allowed is False, "audit_disabled: allowed=False")
_assert(r.error_code == LiveGateDenialCode.AUDIT_DISABLED, "audit_disabled: error_code=audit_disabled")
_assert(len(r.reasons) > 0, "audit_disabled: reasons non-empty")

# ---------------------------------------------------------------------------
# Test 6 — credential_missing
# ---------------------------------------------------------------------------
print("\n── Test 6: credential_missing")
r = check_live_gate(_all_pass_input(credential_configured=False))
_assert(r.allowed is False, "credential_missing: allowed=False")
_assert(r.error_code == LiveGateDenialCode.CREDENTIAL_MISSING, "credential_missing: error_code=credential_missing")
_assert(len(r.reasons) > 0, "credential_missing: reasons non-empty")

# ---------------------------------------------------------------------------
# Test 7 — credential_not_active (REVOKED)
# ---------------------------------------------------------------------------
print("\n── Test 7: credential_not_active (REVOKED)")
r = check_live_gate(_all_pass_input(credential_status="REVOKED"))
_assert(r.allowed is False, "credential_not_active(REVOKED): allowed=False")
_assert(r.error_code == LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE, "credential_not_active(REVOKED): error_code correct")
_assert("REVOKED" in r.reasons[0], "credential_not_active(REVOKED): reason mentions REVOKED")

# ---------------------------------------------------------------------------
# Test 8 — credential_not_active (CONFIGURED)
# ---------------------------------------------------------------------------
print("\n── Test 8: credential_not_active (CONFIGURED)")
r = check_live_gate(_all_pass_input(credential_status="CONFIGURED"))
_assert(r.allowed is False, "credential_not_active(CONFIGURED): allowed=False")
_assert(r.error_code == LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE, "credential_not_active(CONFIGURED): error_code correct")
_assert("CONFIGURED" in r.reasons[0], "credential_not_active(CONFIGURED): reason mentions CONFIGURED")

# ---------------------------------------------------------------------------
# Test 9 — credential_not_active (VALIDATION_FAILED)
# ---------------------------------------------------------------------------
print("\n── Test 9: credential_not_active (VALIDATION_FAILED)")
r = check_live_gate(_all_pass_input(credential_status="VALIDATION_FAILED"))
_assert(r.allowed is False, "credential_not_active(VALIDATION_FAILED): allowed=False")
_assert(r.error_code == LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE, "credential_not_active(VALIDATION_FAILED): error_code correct")
_assert("VALIDATION_FAILED" in r.reasons[0], "credential_not_active(VALIDATION_FAILED): reason mentions status")

# ---------------------------------------------------------------------------
# Test 10 — tenant_not_allowed
# ---------------------------------------------------------------------------
print("\n── Test 10: tenant_not_allowed")
r = check_live_gate(_all_pass_input(tenant_allowed=False))
_assert(r.allowed is False, "tenant_not_allowed: allowed=False")
_assert(r.error_code == LiveGateDenialCode.TENANT_NOT_ALLOWED, "tenant_not_allowed: error_code=tenant_not_allowed")
_assert(len(r.reasons) > 0, "tenant_not_allowed: reasons non-empty")

# ---------------------------------------------------------------------------
# Test 11 — client_not_allowed
# ---------------------------------------------------------------------------
print("\n── Test 11: client_not_allowed")
r = check_live_gate(_all_pass_input(client_allowed=False))
_assert(r.allowed is False, "client_not_allowed: allowed=False")
_assert(r.error_code == LiveGateDenialCode.CLIENT_NOT_ALLOWED, "client_not_allowed: error_code=client_not_allowed")
_assert(len(r.reasons) > 0, "client_not_allowed: reasons non-empty")

# ---------------------------------------------------------------------------
# Test 12 — rollback_plan_missing
# ---------------------------------------------------------------------------
print("\n── Test 12: rollback_plan_missing")
r = check_live_gate(_all_pass_input(rollback_plan_present=False))
_assert(r.allowed is False, "rollback_plan_missing: allowed=False")
_assert(r.error_code == LiveGateDenialCode.ROLLBACK_PLAN_MISSING, "rollback_plan_missing: error_code correct")
_assert(len(r.reasons) > 0, "rollback_plan_missing: reasons non-empty")

# ---------------------------------------------------------------------------
# Test 13 — operator_confirmation_missing
# ---------------------------------------------------------------------------
print("\n── Test 13: operator_confirmation_missing")
r = check_live_gate(_all_pass_input(operator_confirmed=False))
_assert(r.allowed is False, "operator_confirmation_missing: allowed=False")
_assert(r.error_code == LiveGateDenialCode.OPERATOR_CONFIRMATION_MISSING, "operator_confirmation_missing: error_code correct")
_assert(len(r.reasons) > 0, "operator_confirmation_missing: reasons non-empty")

# ---------------------------------------------------------------------------
# Test 14 — allow path (all conditions satisfied)
# ---------------------------------------------------------------------------
print("\n── Test 14: allow path — all conditions satisfied")
r = check_live_gate(_all_pass_input())
_assert(r.allowed is True, "allow path: allowed=True")
_assert(r.error_code is None, "allow path: error_code=None")
_assert(len(r.reasons) > 0, "allow path: reasons non-empty")
_assert(r.required_actions == [], "allow path: required_actions=[]")

# ---------------------------------------------------------------------------
# Test 15 — credential_not_active (empty status)
# ---------------------------------------------------------------------------
print("\n── Test 15: credential_not_active (empty status)")
r = check_live_gate(_all_pass_input(credential_status=""))
_assert(r.allowed is False, "credential_not_active(empty): allowed=False")
_assert(r.error_code == LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE, "credential_not_active(empty): error_code correct")
_assert(len(r.reasons) > 0, "credential_not_active(empty): reasons non-empty")

# ---------------------------------------------------------------------------
# Test 16 — credential_not_active (unknown status string)
# ---------------------------------------------------------------------------
print("\n── Test 16: credential_not_active (unknown status)")
r = check_live_gate(_all_pass_input(credential_status="UNKNOWN"))
_assert(r.allowed is False, "credential_not_active(UNKNOWN): allowed=False")
_assert(r.error_code == LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE, "credential_not_active(UNKNOWN): error_code correct")

# ---------------------------------------------------------------------------
# Test 17 — required_actions non-empty on all 11 denial paths
# ---------------------------------------------------------------------------
print("\n── Test 17: required_actions non-empty on all denial paths")
_denial_cases = [
    ("live_disabled", dict(live_enabled=False)),
    ("approval_missing", dict(approval_present=False)),
    ("approval_invalid", dict(approval_valid=False)),
    ("preflight_missing", dict(preflight_passed=False)),
    ("audit_disabled", dict(audit_enabled=False)),
    ("credential_missing", dict(credential_configured=False)),
    ("credential_not_active", dict(credential_status="REVOKED")),
    ("tenant_not_allowed", dict(tenant_allowed=False)),
    ("client_not_allowed", dict(client_allowed=False)),
    ("rollback_plan_missing", dict(rollback_plan_present=False)),
    ("operator_confirmation_missing", dict(operator_confirmed=False)),
]
for _label, _kwargs in _denial_cases:
    _r = check_live_gate(_all_pass_input(**_kwargs))
    _assert(len(_r.required_actions) > 0, f"{_label}: required_actions non-empty")

# ---------------------------------------------------------------------------
# Test 18 — no forbidden field names in LiveGateResult keys or serialized output
# ---------------------------------------------------------------------------
print("\n── Test 18: no forbidden field names in LiveGateResult keys")
import dataclasses as _dc
import json as _json
_r_allow = check_live_gate(_all_pass_input())
_result_dict = _dc.asdict(_r_allow)
_FORBIDDEN_GATE_KEYS = frozenset({
    "credential_ref", "secret_id", "developer_token", "client_secret",
    "refresh_token", "access_token", "customer_id", "login_customer_id",
    "google_ads_client_id", "approval_id", "tenant_id", "client_id",
})
_found_forbidden = _FORBIDDEN_GATE_KEYS & set(_result_dict.keys())
_assert(not _found_forbidden,
        f"no forbidden field names in LiveGateResult keys (found: {_found_forbidden})")
_result_json = _json.dumps(_result_dict)
_assert("projects/" not in _result_json, "no GCP resource paths in serialized result")

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

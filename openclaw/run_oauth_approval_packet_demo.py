"""
V5.21 Phase 6 — OAuth operator approval packet model demo.

41 test scenarios covering all OAuthApprovalPacketFailureCode cases, approval record
requirements, participant requirements, execution window requirements, validator gate
requirements, audit/ceremony requirements, hard-stop detections, forbidden field/value
detection, sanitized_summary exclusions, multiple-failure accumulation, and
required_actions behavior.

No real credentials. No real approval records. No real operator identities.
No real tenant/client IDs. No OAuth. No GCP commands. No network calls. No filesystem I/O.
GOOGLE_ADS_LIVE_ENABLED remains false.
"""

import sys
from pathlib import Path

_DIR = str(Path(__file__).resolve().parent)
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from oauth_approval_packet import (
    OAuthApprovalPacketDecision,
    OAuthApprovalPacketFailureCode,
    OAuthApprovalPacketInput,
    validate_oauth_approval_packet,
)

_PASS = 0
_FAIL = 0


def _check(label: str, condition: bool, *, detail: str = "") -> None:
    global _PASS, _FAIL
    if condition:
        print(f"  [PASS] {label}")
        _PASS += 1
    else:
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f": {detail}"
        print(msg)
        _FAIL += 1


def _valid() -> OAuthApprovalPacketInput:
    """Return a fully-valid OAuthApprovalPacketInput with all conditions met."""
    return OAuthApprovalPacketInput(
        approval_present=True,
        approval_approved=True,
        approval_unexpired=True,
        approval_scope_valid=True,
        operator_present=True,
        reviewer_present=True,
        tenant_ref_present=True,
        client_ref_present=True,
        rollback_owner_present=True,
        emergency_revoke_owner_present=True,
        evidence_owner_present=True,
        stop_authority_present=True,
        execution_window_present=True,
        execution_window_timeboxed=True,
        oauth_auth_url_gate_present=True,
        oauth_callback_gate_present=True,
        credential_handoff_protocol_present=True,
        credential_intake_gate_present=True,
        secret_version_policy_gate_present=True,
        rollback_drill_gate_present=True,
        live_gate_requirement_present=True,
        audit_requirement_present=True,
        safety_grep_requirement_present=True,
        smoke_test_requirement_present=True,
        final_live_flag_reset_requirement_present=True,
        real_credential_present=False,
        oauth_execution_detected=False,
        google_ads_api_called=False,
        gcp_commands_used=False,
        secret_manager_called=False,
        token_exchange_attempted=False,
    )


print("=== V5.21 Phase 6: OAuth Operator Approval Packet Validator Demo ===")
print()

# ---------------------------------------------------------------------------
# Test 1: valid input → PASS
# ---------------------------------------------------------------------------
print("--- Test 1: valid input ---")
r = validate_oauth_approval_packet(_valid())
_check("ok=True", r.ok)
_check("decision=PASS", r.decision == OAuthApprovalPacketDecision.PASS)
_check("failure_codes empty", r.failure_codes == [])
_check("sanitized_summary is dict", isinstance(r.sanitized_summary, dict))

# ---------------------------------------------------------------------------
# Test 2: approval_present=False → approval_missing
# ---------------------------------------------------------------------------
print("--- Test 2: approval_present=False ---")
inp = _valid()
inp.approval_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "approval_missing in failure_codes",
    OAuthApprovalPacketFailureCode.APPROVAL_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 3: approval_approved=False → approval_not_approved
# ---------------------------------------------------------------------------
print("--- Test 3: approval_approved=False ---")
inp = _valid()
inp.approval_approved = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "approval_not_approved in failure_codes",
    OAuthApprovalPacketFailureCode.APPROVAL_NOT_APPROVED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 4: approval_unexpired=False → approval_expired
# ---------------------------------------------------------------------------
print("--- Test 4: approval_unexpired=False ---")
inp = _valid()
inp.approval_unexpired = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "approval_expired in failure_codes",
    OAuthApprovalPacketFailureCode.APPROVAL_EXPIRED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 5: approval_scope_valid=False → approval_scope_invalid
# ---------------------------------------------------------------------------
print("--- Test 5: approval_scope_valid=False ---")
inp = _valid()
inp.approval_scope_valid = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "approval_scope_invalid in failure_codes",
    OAuthApprovalPacketFailureCode.APPROVAL_SCOPE_INVALID in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 6: operator_present=False → operator_missing
# ---------------------------------------------------------------------------
print("--- Test 6: operator_present=False ---")
inp = _valid()
inp.operator_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "operator_missing in failure_codes",
    OAuthApprovalPacketFailureCode.OPERATOR_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 7: reviewer_present=False → reviewer_missing
# ---------------------------------------------------------------------------
print("--- Test 7: reviewer_present=False ---")
inp = _valid()
inp.reviewer_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "reviewer_missing in failure_codes",
    OAuthApprovalPacketFailureCode.REVIEWER_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 8: tenant_ref_present=False → tenant_ref_missing
# ---------------------------------------------------------------------------
print("--- Test 8: tenant_ref_present=False ---")
inp = _valid()
inp.tenant_ref_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "tenant_ref_missing in failure_codes",
    OAuthApprovalPacketFailureCode.TENANT_REF_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 9: client_ref_present=False → client_ref_missing
# ---------------------------------------------------------------------------
print("--- Test 9: client_ref_present=False ---")
inp = _valid()
inp.client_ref_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "client_ref_missing in failure_codes",
    OAuthApprovalPacketFailureCode.CLIENT_REF_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 10: execution_window_present=False → execution_window_missing
# ---------------------------------------------------------------------------
print("--- Test 10: execution_window_present=False ---")
inp = _valid()
inp.execution_window_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "execution_window_missing in failure_codes",
    OAuthApprovalPacketFailureCode.EXECUTION_WINDOW_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 11: execution_window_timeboxed=False → execution_window_not_timeboxed
# ---------------------------------------------------------------------------
print("--- Test 11: execution_window_timeboxed=False ---")
inp = _valid()
inp.execution_window_timeboxed = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "execution_window_not_timeboxed in failure_codes",
    OAuthApprovalPacketFailureCode.EXECUTION_WINDOW_NOT_TIMEBOXED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 12: rollback_owner_present=False → rollback_owner_missing
# ---------------------------------------------------------------------------
print("--- Test 12: rollback_owner_present=False ---")
inp = _valid()
inp.rollback_owner_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "rollback_owner_missing in failure_codes",
    OAuthApprovalPacketFailureCode.ROLLBACK_OWNER_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 13: emergency_revoke_owner_present=False → emergency_revoke_owner_missing
# ---------------------------------------------------------------------------
print("--- Test 13: emergency_revoke_owner_present=False ---")
inp = _valid()
inp.emergency_revoke_owner_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "emergency_revoke_owner_missing in failure_codes",
    OAuthApprovalPacketFailureCode.EMERGENCY_REVOKE_OWNER_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 14: evidence_owner_present=False → evidence_owner_missing
# ---------------------------------------------------------------------------
print("--- Test 14: evidence_owner_present=False ---")
inp = _valid()
inp.evidence_owner_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "evidence_owner_missing in failure_codes",
    OAuthApprovalPacketFailureCode.EVIDENCE_OWNER_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 15: stop_authority_present=False → stop_authority_missing
# ---------------------------------------------------------------------------
print("--- Test 15: stop_authority_present=False ---")
inp = _valid()
inp.stop_authority_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "stop_authority_missing in failure_codes",
    OAuthApprovalPacketFailureCode.STOP_AUTHORITY_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 16: oauth_auth_url_gate_present=False → oauth_auth_url_gate_missing
# ---------------------------------------------------------------------------
print("--- Test 16: oauth_auth_url_gate_present=False ---")
inp = _valid()
inp.oauth_auth_url_gate_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "oauth_auth_url_gate_missing in failure_codes",
    OAuthApprovalPacketFailureCode.OAUTH_AUTH_URL_GATE_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 17: oauth_callback_gate_present=False → oauth_callback_gate_missing
# ---------------------------------------------------------------------------
print("--- Test 17: oauth_callback_gate_present=False ---")
inp = _valid()
inp.oauth_callback_gate_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "oauth_callback_gate_missing in failure_codes",
    OAuthApprovalPacketFailureCode.OAUTH_CALLBACK_GATE_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 18: credential_handoff_protocol_present=False → credential_handoff_protocol_missing
# ---------------------------------------------------------------------------
print("--- Test 18: credential_handoff_protocol_present=False ---")
inp = _valid()
inp.credential_handoff_protocol_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "credential_handoff_protocol_missing in failure_codes",
    OAuthApprovalPacketFailureCode.CREDENTIAL_HANDOFF_PROTOCOL_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 19: credential_intake_gate_present=False → credential_intake_gate_missing
# ---------------------------------------------------------------------------
print("--- Test 19: credential_intake_gate_present=False ---")
inp = _valid()
inp.credential_intake_gate_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "credential_intake_gate_missing in failure_codes",
    OAuthApprovalPacketFailureCode.CREDENTIAL_INTAKE_GATE_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 20: secret_version_policy_gate_present=False → secret_version_policy_gate_missing
# ---------------------------------------------------------------------------
print("--- Test 20: secret_version_policy_gate_present=False ---")
inp = _valid()
inp.secret_version_policy_gate_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "secret_version_policy_gate_missing in failure_codes",
    OAuthApprovalPacketFailureCode.SECRET_VERSION_POLICY_GATE_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 21: rollback_drill_gate_present=False → rollback_drill_gate_missing
# ---------------------------------------------------------------------------
print("--- Test 21: rollback_drill_gate_present=False ---")
inp = _valid()
inp.rollback_drill_gate_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "rollback_drill_gate_missing in failure_codes",
    OAuthApprovalPacketFailureCode.ROLLBACK_DRILL_GATE_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 22: live_gate_requirement_present=False → live_gate_requirement_missing
# ---------------------------------------------------------------------------
print("--- Test 22: live_gate_requirement_present=False ---")
inp = _valid()
inp.live_gate_requirement_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "live_gate_requirement_missing in failure_codes",
    OAuthApprovalPacketFailureCode.LIVE_GATE_REQUIREMENT_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 23: audit_requirement_present=False → audit_requirement_missing
# ---------------------------------------------------------------------------
print("--- Test 23: audit_requirement_present=False ---")
inp = _valid()
inp.audit_requirement_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "audit_requirement_missing in failure_codes",
    OAuthApprovalPacketFailureCode.AUDIT_REQUIREMENT_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 24: safety_grep_requirement_present=False → safety_grep_requirement_missing
# ---------------------------------------------------------------------------
print("--- Test 24: safety_grep_requirement_present=False ---")
inp = _valid()
inp.safety_grep_requirement_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "safety_grep_requirement_missing in failure_codes",
    OAuthApprovalPacketFailureCode.SAFETY_GREP_REQUIREMENT_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 25: smoke_test_requirement_present=False → smoke_test_requirement_missing
# ---------------------------------------------------------------------------
print("--- Test 25: smoke_test_requirement_present=False ---")
inp = _valid()
inp.smoke_test_requirement_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "smoke_test_requirement_missing in failure_codes",
    OAuthApprovalPacketFailureCode.SMOKE_TEST_REQUIREMENT_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 26: final_live_flag_reset_requirement_present=False → final_live_flag_reset_requirement_missing
# ---------------------------------------------------------------------------
print("--- Test 26: final_live_flag_reset_requirement_present=False ---")
inp = _valid()
inp.final_live_flag_reset_requirement_present = False
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "final_live_flag_reset_requirement_missing in failure_codes",
    OAuthApprovalPacketFailureCode.FINAL_LIVE_FLAG_RESET_REQUIREMENT_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 27: real_credential_present=True → real_credential_present
# ---------------------------------------------------------------------------
print("--- Test 27: real_credential_present=True ---")
inp = _valid()
inp.real_credential_present = True
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "real_credential_present in failure_codes",
    OAuthApprovalPacketFailureCode.REAL_CREDENTIAL_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 28: oauth_execution_detected=True → oauth_execution_detected
# ---------------------------------------------------------------------------
print("--- Test 28: oauth_execution_detected=True ---")
inp = _valid()
inp.oauth_execution_detected = True
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "oauth_execution_detected in failure_codes",
    OAuthApprovalPacketFailureCode.OAUTH_EXECUTION_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 29: google_ads_api_called=True → google_ads_api_called
# ---------------------------------------------------------------------------
print("--- Test 29: google_ads_api_called=True ---")
inp = _valid()
inp.google_ads_api_called = True
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "google_ads_api_called in failure_codes",
    OAuthApprovalPacketFailureCode.GOOGLE_ADS_API_CALLED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 30: gcp_commands_used=True → gcp_commands_used
# ---------------------------------------------------------------------------
print("--- Test 30: gcp_commands_used=True ---")
inp = _valid()
inp.gcp_commands_used = True
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "gcp_commands_used in failure_codes",
    OAuthApprovalPacketFailureCode.GCP_COMMANDS_USED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 31: secret_manager_called=True → secret_manager_called
# ---------------------------------------------------------------------------
print("--- Test 31: secret_manager_called=True ---")
inp = _valid()
inp.secret_manager_called = True
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "secret_manager_called in failure_codes",
    OAuthApprovalPacketFailureCode.SECRET_MANAGER_CALLED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 32: token_exchange_attempted=True → token_exchange_attempted
# ---------------------------------------------------------------------------
print("--- Test 32: token_exchange_attempted=True ---")
inp = _valid()
inp.token_exchange_attempted = True
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "token_exchange_attempted in failure_codes",
    OAuthApprovalPacketFailureCode.TOKEN_EXCHANGE_ATTEMPTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 33: forbidden field in evidence → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 33: forbidden field in evidence ---")
inp = _valid()
inp.evidence = {"approval_raw_payload": "some-placeholder-value"}
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes",
    OAuthApprovalPacketFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 34: forbidden field in metadata → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 34: forbidden field in metadata ---")
inp = _valid()
inp.metadata = {"real_operator_email": "placeholder"}
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes (metadata)",
    OAuthApprovalPacketFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 35: forbidden value in evidence (refresh token prefix pattern)
# ---------------------------------------------------------------------------
print("--- Test 35: forbidden value in evidence (refresh token pattern) ---")
inp = _valid()
inp.evidence = {"notes": "1//abc"}
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (refresh token prefix)",
    OAuthApprovalPacketFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 36: forbidden value in metadata (credential field name as value)
# ---------------------------------------------------------------------------
print("--- Test 36: forbidden value in metadata (field name as value) ---")
inp = _valid()
inp.metadata = {"note": "callback_url"}
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (metadata)",
    OAuthApprovalPacketFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 37: sanitized_summary excludes evidence and metadata
# ---------------------------------------------------------------------------
print("--- Test 37: sanitized_summary excludes evidence/metadata ---")
inp = _valid()
inp.evidence = {"notes": "redacted-ceremony-note"}
inp.metadata = {"source": "local-approval-check"}
r = validate_oauth_approval_packet(inp)
_check("evidence not in sanitized_summary", "evidence" not in r.sanitized_summary)
_check("metadata not in sanitized_summary", "metadata" not in r.sanitized_summary)

# ---------------------------------------------------------------------------
# Test 38: sanitized_summary contains expected approval packet fields
# ---------------------------------------------------------------------------
print("--- Test 38: sanitized_summary shape ---")
r = validate_oauth_approval_packet(_valid())
summary = r.sanitized_summary
_check("approval_present in summary", "approval_present" in summary)
_check("approval_approved in summary", "approval_approved" in summary)
_check("approval_unexpired in summary", "approval_unexpired" in summary)
_check("approval_scope_valid in summary", "approval_scope_valid" in summary)
_check("operator_present in summary", "operator_present" in summary)
_check("reviewer_present in summary", "reviewer_present" in summary)
_check("tenant_ref_present in summary", "tenant_ref_present" in summary)
_check("client_ref_present in summary", "client_ref_present" in summary)
_check("execution_window_present in summary", "execution_window_present" in summary)
_check("execution_window_timeboxed in summary", "execution_window_timeboxed" in summary)
_check("rollback_owner_present in summary", "rollback_owner_present" in summary)
_check("emergency_revoke_owner_present in summary", "emergency_revoke_owner_present" in summary)
_check("oauth_auth_url_gate_present in summary", "oauth_auth_url_gate_present" in summary)
_check("oauth_callback_gate_present in summary", "oauth_callback_gate_present" in summary)
_check("credential_handoff_protocol_present in summary", "credential_handoff_protocol_present" in summary)
_check("credential_intake_gate_present in summary", "credential_intake_gate_present" in summary)
_check("secret_version_policy_gate_present in summary", "secret_version_policy_gate_present" in summary)
_check("rollback_drill_gate_present in summary", "rollback_drill_gate_present" in summary)
_check("live_gate_requirement_present in summary", "live_gate_requirement_present" in summary)
_check("final_live_flag_reset_requirement_present in summary", "final_live_flag_reset_requirement_present" in summary)
_check("real_credential_present in summary", "real_credential_present" in summary)
_check("oauth_execution_detected in summary", "oauth_execution_detected" in summary)
_check("google_ads_api_called in summary", "google_ads_api_called" in summary)
_check("gcp_commands_used in summary", "gcp_commands_used" in summary)
_check("secret_manager_called in summary", "secret_manager_called" in summary)
_check("token_exchange_attempted in summary", "token_exchange_attempted" in summary)
_check(
    "ok + decision + failure_count in summary",
    "ok" in summary and "decision" in summary and "failure_count" in summary,
)

# ---------------------------------------------------------------------------
# Test 39: multiple failures accumulate in failure_codes
# ---------------------------------------------------------------------------
print("--- Test 39: multiple failures ---")
inp = _valid()
inp.approval_present = False
inp.operator_present = False
inp.execution_window_present = False
inp.oauth_auth_url_gate_present = False
inp.real_credential_present = True
r = validate_oauth_approval_packet(inp)
_check("ok=False", not r.ok)
_check("failure_count >= 5", r.sanitized_summary["failure_count"] >= 5)
_check("failure_codes len >= 5", len(r.failure_codes) >= 5)

# ---------------------------------------------------------------------------
# Test 40: required_actions non-empty on failure; length matches failure_codes
# ---------------------------------------------------------------------------
print("--- Test 40: required_actions non-empty on failure ---")
inp = _valid()
inp.rollback_owner_present = False
r = validate_oauth_approval_packet(inp)
_check("required_actions non-empty", len(r.required_actions) > 0)
_check(
    "required_actions length matches failure_codes",
    len(r.required_actions) == len(r.failure_codes),
)

# ---------------------------------------------------------------------------
# Test 41: required_actions empty on PASS
# ---------------------------------------------------------------------------
print("--- Test 41: required_actions empty on PASS ---")
r_pass = validate_oauth_approval_packet(_valid())
_check("required_actions empty on PASS", r_pass.required_actions == [])
_check("decision=PASS", r_pass.decision == OAuthApprovalPacketDecision.PASS)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f"Results: {_PASS} passed, {_FAIL} failed")
if _FAIL == 0:
    print("All assertions passed.")
else:
    sys.exit(1)

"""
V5.20 Phase 6 — Rollback and emergency revoke drill demo and tests.

28 test scenarios covering all RollbackDrillFailureCode cases, hard-stop
detection, forbidden field/value detection, sanitized_summary exclusions,
multiple-failure accumulation, and required_actions behavior.

No real credentials. No OAuth. No GCP commands. No network calls. No filesystem I/O.
GOOGLE_ADS_LIVE_ENABLED remains false.
"""

import sys
from pathlib import Path

_DIR = str(Path(__file__).resolve().parent)
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from rollback_drill import (
    RollbackDrillDecision,
    RollbackDrillFailureCode,
    RollbackDrillInput,
    validate_rollback_drill,
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


def _valid() -> RollbackDrillInput:
    """Return a fully-valid RollbackDrillInput with all conditions met."""
    return RollbackDrillInput(
        live_flag_disabled=True,
        approval_revoked=True,
        credential_marked_revoked=True,
        credential_bundle_deleted_or_revoked=True,
        post_revoke_status_verified=True,
        secret_status_verified=True,
        live_gate_denied_after_revoke=True,
        smoke_tests_passed=True,
        safety_grep_clean=True,
        audit_chain_verified=True,
        final_state_documented=True,
        real_credentials_present=False,
        google_ads_api_called=False,
        gcp_commands_used=False,
        secret_manager_called=False,
        oauth_execution_detected=False,
        network_call_detected=False,
        filesystem_write_detected=False,
    )


print("=== V5.20 Phase 6: Rollback and Emergency Revoke Drill Demo ===")
print()

# ---------------------------------------------------------------------------
# Test 1: valid input → PASS
# ---------------------------------------------------------------------------
print("--- Test 1: valid input ---")
r = validate_rollback_drill(_valid())
_check("ok=True", r.ok)
_check("decision=PASS", r.decision == RollbackDrillDecision.PASS)
_check("failure_codes empty", r.failure_codes == [])
_check("sanitized_summary is dict", isinstance(r.sanitized_summary, dict))

# ---------------------------------------------------------------------------
# Test 2: live_flag_disabled=False → live_flag_not_disabled
# ---------------------------------------------------------------------------
print("--- Test 2: live_flag_disabled=False ---")
inp = _valid()
inp.live_flag_disabled = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "live_flag_not_disabled in failure_codes",
    RollbackDrillFailureCode.LIVE_FLAG_NOT_DISABLED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 3: approval_revoked=False → approval_not_revoked
# ---------------------------------------------------------------------------
print("--- Test 3: approval_revoked=False ---")
inp = _valid()
inp.approval_revoked = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "approval_not_revoked in failure_codes",
    RollbackDrillFailureCode.APPROVAL_NOT_REVOKED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 4: credential_marked_revoked=False → credential_not_revoked
# ---------------------------------------------------------------------------
print("--- Test 4: credential_marked_revoked=False ---")
inp = _valid()
inp.credential_marked_revoked = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "credential_not_revoked in failure_codes",
    RollbackDrillFailureCode.CREDENTIAL_NOT_REVOKED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 5: credential_bundle_deleted_or_revoked=False
# ---------------------------------------------------------------------------
print("--- Test 5: credential_bundle_deleted_or_revoked=False ---")
inp = _valid()
inp.credential_bundle_deleted_or_revoked = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "credential_bundle_not_deleted_or_revoked in failure_codes",
    RollbackDrillFailureCode.CREDENTIAL_BUNDLE_NOT_DELETED_OR_REVOKED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 6: post_revoke_status_verified=False → post_revoke_status_not_verified
# ---------------------------------------------------------------------------
print("--- Test 6: post_revoke_status_verified=False ---")
inp = _valid()
inp.post_revoke_status_verified = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "post_revoke_status_not_verified in failure_codes",
    RollbackDrillFailureCode.POST_REVOKE_STATUS_NOT_VERIFIED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 7: secret_status_verified=False → secret_status_not_verified
# ---------------------------------------------------------------------------
print("--- Test 7: secret_status_verified=False ---")
inp = _valid()
inp.secret_status_verified = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "secret_status_not_verified in failure_codes",
    RollbackDrillFailureCode.SECRET_STATUS_NOT_VERIFIED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 8: live_gate_denied_after_revoke=False → live_gate_not_denied_after_revoke
# ---------------------------------------------------------------------------
print("--- Test 8: live_gate_denied_after_revoke=False ---")
inp = _valid()
inp.live_gate_denied_after_revoke = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "live_gate_not_denied_after_revoke in failure_codes",
    RollbackDrillFailureCode.LIVE_GATE_NOT_DENIED_AFTER_REVOKE in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 9: smoke_tests_passed=False → smoke_tests_not_passed
# ---------------------------------------------------------------------------
print("--- Test 9: smoke_tests_passed=False ---")
inp = _valid()
inp.smoke_tests_passed = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "smoke_tests_not_passed in failure_codes",
    RollbackDrillFailureCode.SMOKE_TESTS_NOT_PASSED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 10: safety_grep_clean=False → safety_grep_not_clean
# ---------------------------------------------------------------------------
print("--- Test 10: safety_grep_clean=False ---")
inp = _valid()
inp.safety_grep_clean = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "safety_grep_not_clean in failure_codes",
    RollbackDrillFailureCode.SAFETY_GREP_NOT_CLEAN in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 11: audit_chain_verified=False → audit_chain_not_verified
# ---------------------------------------------------------------------------
print("--- Test 11: audit_chain_verified=False ---")
inp = _valid()
inp.audit_chain_verified = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "audit_chain_not_verified in failure_codes",
    RollbackDrillFailureCode.AUDIT_CHAIN_NOT_VERIFIED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 12: final_state_documented=False → final_state_not_documented
# ---------------------------------------------------------------------------
print("--- Test 12: final_state_documented=False ---")
inp = _valid()
inp.final_state_documented = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "final_state_not_documented in failure_codes",
    RollbackDrillFailureCode.FINAL_STATE_NOT_DOCUMENTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 13: real_credentials_present=True → real_credentials_present
# ---------------------------------------------------------------------------
print("--- Test 13: real_credentials_present=True ---")
inp = _valid()
inp.real_credentials_present = True
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "real_credentials_present in failure_codes",
    RollbackDrillFailureCode.REAL_CREDENTIALS_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 14: google_ads_api_called=True → google_ads_api_called
# ---------------------------------------------------------------------------
print("--- Test 14: google_ads_api_called=True ---")
inp = _valid()
inp.google_ads_api_called = True
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "google_ads_api_called in failure_codes",
    RollbackDrillFailureCode.GOOGLE_ADS_API_CALLED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 15: gcp_commands_used=True → gcp_commands_used
# ---------------------------------------------------------------------------
print("--- Test 15: gcp_commands_used=True ---")
inp = _valid()
inp.gcp_commands_used = True
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "gcp_commands_used in failure_codes",
    RollbackDrillFailureCode.GCP_COMMANDS_USED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 16: secret_manager_called=True → secret_manager_called
# ---------------------------------------------------------------------------
print("--- Test 16: secret_manager_called=True ---")
inp = _valid()
inp.secret_manager_called = True
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "secret_manager_called in failure_codes",
    RollbackDrillFailureCode.SECRET_MANAGER_CALLED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 17: oauth_execution_detected=True → oauth_execution_detected
# ---------------------------------------------------------------------------
print("--- Test 17: oauth_execution_detected=True ---")
inp = _valid()
inp.oauth_execution_detected = True
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "oauth_execution_detected in failure_codes",
    RollbackDrillFailureCode.OAUTH_EXECUTION_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 18: network_call_detected=True → network_call_detected
# ---------------------------------------------------------------------------
print("--- Test 18: network_call_detected=True ---")
inp = _valid()
inp.network_call_detected = True
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "network_call_detected in failure_codes",
    RollbackDrillFailureCode.NETWORK_CALL_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 19: filesystem_write_detected=True → filesystem_write_detected
# ---------------------------------------------------------------------------
print("--- Test 19: filesystem_write_detected=True ---")
inp = _valid()
inp.filesystem_write_detected = True
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "filesystem_write_detected in failure_codes",
    RollbackDrillFailureCode.FILESYSTEM_WRITE_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 20: forbidden field in evidence → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 20: forbidden field in evidence ---")
inp = _valid()
inp.evidence = {"oauth_code": "some-placeholder-value"}
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes",
    RollbackDrillFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 21: forbidden field in metadata → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 21: forbidden field in metadata ---")
inp = _valid()
inp.metadata = {"api_response_payload": "placeholder"}
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes (metadata)",
    RollbackDrillFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 22: forbidden value in evidence (GCP resource path pattern)
# ---------------------------------------------------------------------------
print("--- Test 22: forbidden value in evidence (GCP path) ---")
inp = _valid()
inp.evidence = {"drill_notes": "projects/my-test-project/secrets/my-test-secret"}
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (GCP path)",
    RollbackDrillFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 23: forbidden value in metadata (credential field name as value)
# ---------------------------------------------------------------------------
print("--- Test 23: forbidden value in metadata (bare credential field name) ---")
inp = _valid()
inp.metadata = {"note": "refresh_token"}
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (metadata)",
    RollbackDrillFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 24: sanitized_summary excludes evidence and metadata
# ---------------------------------------------------------------------------
print("--- Test 24: sanitized_summary excludes evidence/metadata ---")
inp = _valid()
inp.evidence = {"notes": "redacted-drill-note"}
inp.metadata = {"source": "local-drill"}
r = validate_rollback_drill(inp)
_check("evidence not in sanitized_summary", "evidence" not in r.sanitized_summary)
_check("metadata not in sanitized_summary", "metadata" not in r.sanitized_summary)

# ---------------------------------------------------------------------------
# Test 25: sanitized_summary contains all expected fields
# ---------------------------------------------------------------------------
print("--- Test 25: sanitized_summary shape ---")
summary = r.sanitized_summary
_check("live_flag_disabled in summary", "live_flag_disabled" in summary)
_check("approval_revoked in summary", "approval_revoked" in summary)
_check("credential_marked_revoked in summary", "credential_marked_revoked" in summary)
_check("credential_bundle_deleted_or_revoked in summary", "credential_bundle_deleted_or_revoked" in summary)
_check("live_gate_denied_after_revoke in summary", "live_gate_denied_after_revoke" in summary)
_check("audit_chain_verified in summary", "audit_chain_verified" in summary)
_check("secret_manager_called in summary", "secret_manager_called" in summary)
_check("google_ads_api_called in summary", "google_ads_api_called" in summary)
_check("gcp_commands_used in summary", "gcp_commands_used" in summary)
_check(
    "ok + decision + failure_count in summary",
    "ok" in summary and "decision" in summary and "failure_count" in summary,
)

# ---------------------------------------------------------------------------
# Test 26: multiple failures accumulate in failure_codes
# ---------------------------------------------------------------------------
print("--- Test 26: multiple failures ---")
inp = _valid()
inp.live_flag_disabled = False
inp.audit_chain_verified = False
inp.final_state_documented = False
r = validate_rollback_drill(inp)
_check("ok=False", not r.ok)
_check("failure_count >= 3", r.sanitized_summary["failure_count"] >= 3)
_check("failure_codes len >= 3", len(r.failure_codes) >= 3)

# ---------------------------------------------------------------------------
# Test 27: required_actions non-empty on failure, length matches failure_codes
# ---------------------------------------------------------------------------
print("--- Test 27: required_actions non-empty on failure ---")
inp = _valid()
inp.smoke_tests_passed = False
r = validate_rollback_drill(inp)
_check("required_actions non-empty", len(r.required_actions) > 0)
_check(
    "required_actions length matches failure_codes",
    len(r.required_actions) == len(r.failure_codes),
)

# ---------------------------------------------------------------------------
# Test 28: required_actions empty on PASS
# ---------------------------------------------------------------------------
print("--- Test 28: required_actions empty on PASS ---")
r = validate_rollback_drill(_valid())
_check("required_actions empty on PASS", r.required_actions == [])
_check("decision=PASS", r.decision == RollbackDrillDecision.PASS)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f"Results: {_PASS} passed, {_FAIL} failed")
if _FAIL == 0:
    print("All assertions passed.")
else:
    sys.exit(1)

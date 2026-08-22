"""
V5.21 Phase 4 — OAuth callback and token-exchange boundary design validator demo.

40 test scenarios covering all OAuthCallbackDesignFailureCode cases, hard-stop
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

from oauth_callback import (
    OAuthCallbackDesignDecision,
    OAuthCallbackDesignFailureCode,
    OAuthCallbackDesignInput,
    validate_oauth_callback_design,
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


def _valid() -> OAuthCallbackDesignInput:
    """Return a fully-valid OAuthCallbackDesignInput with all conditions met."""
    return OAuthCallbackDesignInput(
        oauth_execution_detected=False,
        callback_url_received=False,
        callback_url_logged=False,
        callback_url_committed=False,
        auth_code_received=False,
        auth_code_logged=False,
        auth_code_committed=False,
        auth_code_pasted_to_chat=False,
        token_exchange_attempted=False,
        token_response_received=False,
        token_response_logged=False,
        token_response_committed=False,
        refresh_token_present=False,
        access_token_present=False,
        client_secret_present=False,
        real_client_id_present=False,
        redirect_uri_value_present=False,
        state_value_present=False,
        state_verification_present=True,
        state_bound_to_ceremony=True,
        state_reuse_blocked=True,
        token_exchange_approval_present=True,
        token_exchange_window_present=True,
        secure_channel_present=True,
        redacted_status_verification_present=True,
        storage_boundary_present=True,
        rollback_boundary_present=True,
        audit_requirement_present=True,
        evidence_requirement_present=True,
        operator_confirmation_present=True,
    )


print("=== V5.21 Phase 4: OAuth Callback and Token-Exchange Boundary Validator Demo ===")
print()

# ---------------------------------------------------------------------------
# Test 1: valid input → PASS
# ---------------------------------------------------------------------------
print("--- Test 1: valid input ---")
r = validate_oauth_callback_design(_valid())
_check("ok=True", r.ok)
_check("decision=PASS", r.decision == OAuthCallbackDesignDecision.PASS)
_check("failure_codes empty", r.failure_codes == [])
_check("sanitized_summary is dict", isinstance(r.sanitized_summary, dict))

# ---------------------------------------------------------------------------
# Test 2: oauth_execution_detected=True → oauth_execution_detected
# ---------------------------------------------------------------------------
print("--- Test 2: oauth_execution_detected=True ---")
inp = _valid()
inp.oauth_execution_detected = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "oauth_execution_detected in failure_codes",
    OAuthCallbackDesignFailureCode.OAUTH_EXECUTION_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 3: callback_url_received=True → callback_url_received
# ---------------------------------------------------------------------------
print("--- Test 3: callback_url_received=True ---")
inp = _valid()
inp.callback_url_received = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "callback_url_received in failure_codes",
    OAuthCallbackDesignFailureCode.CALLBACK_URL_RECEIVED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 4: callback_url_logged=True → callback_url_logged
# ---------------------------------------------------------------------------
print("--- Test 4: callback_url_logged=True ---")
inp = _valid()
inp.callback_url_logged = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "callback_url_logged in failure_codes",
    OAuthCallbackDesignFailureCode.CALLBACK_URL_LOGGED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 5: callback_url_committed=True → callback_url_committed
# ---------------------------------------------------------------------------
print("--- Test 5: callback_url_committed=True ---")
inp = _valid()
inp.callback_url_committed = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "callback_url_committed in failure_codes",
    OAuthCallbackDesignFailureCode.CALLBACK_URL_COMMITTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 6: auth_code_received=True → auth_code_received
# ---------------------------------------------------------------------------
print("--- Test 6: auth_code_received=True ---")
inp = _valid()
inp.auth_code_received = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "auth_code_received in failure_codes",
    OAuthCallbackDesignFailureCode.AUTH_CODE_RECEIVED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 7: auth_code_logged=True → auth_code_logged
# ---------------------------------------------------------------------------
print("--- Test 7: auth_code_logged=True ---")
inp = _valid()
inp.auth_code_logged = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "auth_code_logged in failure_codes",
    OAuthCallbackDesignFailureCode.AUTH_CODE_LOGGED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 8: auth_code_committed=True → auth_code_committed
# ---------------------------------------------------------------------------
print("--- Test 8: auth_code_committed=True ---")
inp = _valid()
inp.auth_code_committed = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "auth_code_committed in failure_codes",
    OAuthCallbackDesignFailureCode.AUTH_CODE_COMMITTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 9: auth_code_pasted_to_chat=True → auth_code_pasted_to_chat
# ---------------------------------------------------------------------------
print("--- Test 9: auth_code_pasted_to_chat=True ---")
inp = _valid()
inp.auth_code_pasted_to_chat = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "auth_code_pasted_to_chat in failure_codes",
    OAuthCallbackDesignFailureCode.AUTH_CODE_PASTED_TO_CHAT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 10: token_exchange_attempted=True → token_exchange_attempted
# ---------------------------------------------------------------------------
print("--- Test 10: token_exchange_attempted=True ---")
inp = _valid()
inp.token_exchange_attempted = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "token_exchange_attempted in failure_codes",
    OAuthCallbackDesignFailureCode.TOKEN_EXCHANGE_ATTEMPTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 11: token_response_received=True → token_response_received
# ---------------------------------------------------------------------------
print("--- Test 11: token_response_received=True ---")
inp = _valid()
inp.token_response_received = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "token_response_received in failure_codes",
    OAuthCallbackDesignFailureCode.TOKEN_RESPONSE_RECEIVED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 12: token_response_logged=True → token_response_logged
# ---------------------------------------------------------------------------
print("--- Test 12: token_response_logged=True ---")
inp = _valid()
inp.token_response_logged = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "token_response_logged in failure_codes",
    OAuthCallbackDesignFailureCode.TOKEN_RESPONSE_LOGGED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 13: token_response_committed=True → token_response_committed
# ---------------------------------------------------------------------------
print("--- Test 13: token_response_committed=True ---")
inp = _valid()
inp.token_response_committed = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "token_response_committed in failure_codes",
    OAuthCallbackDesignFailureCode.TOKEN_RESPONSE_COMMITTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 14: refresh_token_present=True → refresh_token_present
# ---------------------------------------------------------------------------
print("--- Test 14: refresh_token_present=True ---")
inp = _valid()
inp.refresh_token_present = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "refresh_token_present in failure_codes",
    OAuthCallbackDesignFailureCode.REFRESH_TOKEN_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 15: access_token_present=True → access_token_present
# ---------------------------------------------------------------------------
print("--- Test 15: access_token_present=True ---")
inp = _valid()
inp.access_token_present = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "access_token_present in failure_codes",
    OAuthCallbackDesignFailureCode.ACCESS_TOKEN_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 16: client_secret_present=True → client_secret_present
# ---------------------------------------------------------------------------
print("--- Test 16: client_secret_present=True ---")
inp = _valid()
inp.client_secret_present = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "client_secret_present in failure_codes",
    OAuthCallbackDesignFailureCode.CLIENT_SECRET_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 17: real_client_id_present=True → real_client_id_present
# ---------------------------------------------------------------------------
print("--- Test 17: real_client_id_present=True ---")
inp = _valid()
inp.real_client_id_present = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "real_client_id_present in failure_codes",
    OAuthCallbackDesignFailureCode.REAL_CLIENT_ID_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 18: redirect_uri_value_present=True → redirect_uri_value_present
# ---------------------------------------------------------------------------
print("--- Test 18: redirect_uri_value_present=True ---")
inp = _valid()
inp.redirect_uri_value_present = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "redirect_uri_value_present in failure_codes",
    OAuthCallbackDesignFailureCode.REDIRECT_URI_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 19: state_value_present=True → state_value_present
# ---------------------------------------------------------------------------
print("--- Test 19: state_value_present=True ---")
inp = _valid()
inp.state_value_present = True
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "state_value_present in failure_codes",
    OAuthCallbackDesignFailureCode.STATE_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 20: state_verification_present=False → state_verification_missing
# ---------------------------------------------------------------------------
print("--- Test 20: state_verification_present=False ---")
inp = _valid()
inp.state_verification_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "state_verification_missing in failure_codes",
    OAuthCallbackDesignFailureCode.STATE_VERIFICATION_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 21: state_bound_to_ceremony=False → state_not_bound_to_ceremony
# ---------------------------------------------------------------------------
print("--- Test 21: state_bound_to_ceremony=False ---")
inp = _valid()
inp.state_bound_to_ceremony = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "state_not_bound_to_ceremony in failure_codes",
    OAuthCallbackDesignFailureCode.STATE_NOT_BOUND_TO_CEREMONY in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 22: state_reuse_blocked=False → state_reuse_not_blocked
# ---------------------------------------------------------------------------
print("--- Test 22: state_reuse_blocked=False ---")
inp = _valid()
inp.state_reuse_blocked = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "state_reuse_not_blocked in failure_codes",
    OAuthCallbackDesignFailureCode.STATE_REUSE_NOT_BLOCKED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 23: token_exchange_approval_present=False → token_exchange_approval_missing
# ---------------------------------------------------------------------------
print("--- Test 23: token_exchange_approval_present=False ---")
inp = _valid()
inp.token_exchange_approval_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "token_exchange_approval_missing in failure_codes",
    OAuthCallbackDesignFailureCode.TOKEN_EXCHANGE_APPROVAL_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 24: token_exchange_window_present=False → token_exchange_window_missing
# ---------------------------------------------------------------------------
print("--- Test 24: token_exchange_window_present=False ---")
inp = _valid()
inp.token_exchange_window_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "token_exchange_window_missing in failure_codes",
    OAuthCallbackDesignFailureCode.TOKEN_EXCHANGE_WINDOW_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 25: secure_channel_present=False → secure_channel_missing
# ---------------------------------------------------------------------------
print("--- Test 25: secure_channel_present=False ---")
inp = _valid()
inp.secure_channel_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "secure_channel_missing in failure_codes",
    OAuthCallbackDesignFailureCode.SECURE_CHANNEL_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 26: redacted_status_verification_present=False → redacted_status_verification_missing
# ---------------------------------------------------------------------------
print("--- Test 26: redacted_status_verification_present=False ---")
inp = _valid()
inp.redacted_status_verification_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "redacted_status_verification_missing in failure_codes",
    OAuthCallbackDesignFailureCode.REDACTED_STATUS_VERIFICATION_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 27: storage_boundary_present=False → storage_boundary_missing
# ---------------------------------------------------------------------------
print("--- Test 27: storage_boundary_present=False ---")
inp = _valid()
inp.storage_boundary_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "storage_boundary_missing in failure_codes",
    OAuthCallbackDesignFailureCode.STORAGE_BOUNDARY_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 28: rollback_boundary_present=False → rollback_boundary_missing
# ---------------------------------------------------------------------------
print("--- Test 28: rollback_boundary_present=False ---")
inp = _valid()
inp.rollback_boundary_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "rollback_boundary_missing in failure_codes",
    OAuthCallbackDesignFailureCode.ROLLBACK_BOUNDARY_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 29: audit_requirement_present=False → audit_requirement_missing
# ---------------------------------------------------------------------------
print("--- Test 29: audit_requirement_present=False ---")
inp = _valid()
inp.audit_requirement_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "audit_requirement_missing in failure_codes",
    OAuthCallbackDesignFailureCode.AUDIT_REQUIREMENT_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 30: evidence_requirement_present=False → evidence_requirement_missing
# ---------------------------------------------------------------------------
print("--- Test 30: evidence_requirement_present=False ---")
inp = _valid()
inp.evidence_requirement_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "evidence_requirement_missing in failure_codes",
    OAuthCallbackDesignFailureCode.EVIDENCE_REQUIREMENT_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 31: operator_confirmation_present=False → operator_confirmation_missing
# ---------------------------------------------------------------------------
print("--- Test 31: operator_confirmation_present=False ---")
inp = _valid()
inp.operator_confirmation_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "operator_confirmation_missing in failure_codes",
    OAuthCallbackDesignFailureCode.OPERATOR_CONFIRMATION_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 32: forbidden field in evidence → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 32: forbidden field in evidence ---")
inp = _valid()
inp.evidence = {"oauth_callback_url": "some-placeholder-value"}
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes",
    OAuthCallbackDesignFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 33: forbidden field in metadata → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 33: forbidden field in metadata ---")
inp = _valid()
inp.metadata = {"api_response_payload": "placeholder"}
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes (metadata)",
    OAuthCallbackDesignFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 34: forbidden value in evidence (refresh token prefix pattern)
# ---------------------------------------------------------------------------
print("--- Test 34: forbidden value in evidence (refresh token pattern) ---")
inp = _valid()
inp.evidence = {"notes": "1//abc"}
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (refresh token prefix)",
    OAuthCallbackDesignFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 35: forbidden value in metadata (credential field name as value)
# ---------------------------------------------------------------------------
print("--- Test 35: forbidden value in metadata (field name as value) ---")
inp = _valid()
inp.metadata = {"note": "callback_url"}
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (metadata)",
    OAuthCallbackDesignFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 36: sanitized_summary excludes evidence and metadata
# ---------------------------------------------------------------------------
print("--- Test 36: sanitized_summary excludes evidence/metadata ---")
inp = _valid()
inp.evidence = {"notes": "redacted-ceremony-note"}
inp.metadata = {"source": "local-boundary-check"}
r = validate_oauth_callback_design(inp)
_check("evidence not in sanitized_summary", "evidence" not in r.sanitized_summary)
_check("metadata not in sanitized_summary", "metadata" not in r.sanitized_summary)

# ---------------------------------------------------------------------------
# Test 37: sanitized_summary contains expected fields
# ---------------------------------------------------------------------------
print("--- Test 37: sanitized_summary shape ---")
r = validate_oauth_callback_design(_valid())
summary = r.sanitized_summary
_check("oauth_execution_detected in summary", "oauth_execution_detected" in summary)
_check("callback_url_received in summary", "callback_url_received" in summary)
_check("callback_url_logged in summary", "callback_url_logged" in summary)
_check("callback_url_committed in summary", "callback_url_committed" in summary)
_check("auth_code_received in summary", "auth_code_received" in summary)
_check("auth_code_logged in summary", "auth_code_logged" in summary)
_check("auth_code_committed in summary", "auth_code_committed" in summary)
_check("token_exchange_attempted in summary", "token_exchange_attempted" in summary)
_check("token_response_received in summary", "token_response_received" in summary)
_check("refresh_token_present in summary", "refresh_token_present" in summary)
_check("access_token_present in summary", "access_token_present" in summary)
_check("state_verification_present in summary", "state_verification_present" in summary)
_check("state_bound_to_ceremony in summary", "state_bound_to_ceremony" in summary)
_check("state_reuse_blocked in summary", "state_reuse_blocked" in summary)
_check("secure_channel_present in summary", "secure_channel_present" in summary)
_check("redacted_status_verification_present in summary", "redacted_status_verification_present" in summary)
_check(
    "ok + decision + failure_count in summary",
    "ok" in summary and "decision" in summary and "failure_count" in summary,
)

# ---------------------------------------------------------------------------
# Test 38: multiple failures accumulate in failure_codes
# ---------------------------------------------------------------------------
print("--- Test 38: multiple failures ---")
inp = _valid()
inp.token_exchange_attempted = True
inp.auth_code_received = True
inp.state_reuse_blocked = False
inp.secure_channel_present = False
r = validate_oauth_callback_design(inp)
_check("ok=False", not r.ok)
_check("failure_count >= 4", r.sanitized_summary["failure_count"] >= 4)
_check("failure_codes len >= 4", len(r.failure_codes) >= 4)

# ---------------------------------------------------------------------------
# Test 39: required_actions non-empty on failure; length matches failure_codes
# ---------------------------------------------------------------------------
print("--- Test 39: required_actions non-empty on failure ---")
inp = _valid()
inp.rollback_boundary_present = False
r = validate_oauth_callback_design(inp)
_check("required_actions non-empty", len(r.required_actions) > 0)
_check(
    "required_actions length matches failure_codes",
    len(r.required_actions) == len(r.failure_codes),
)

# ---------------------------------------------------------------------------
# Test 40: required_actions empty on PASS
# ---------------------------------------------------------------------------
print("--- Test 40: required_actions empty on PASS ---")
r_pass = validate_oauth_callback_design(_valid())
_check("required_actions empty on PASS", r_pass.required_actions == [])
_check("decision=PASS", r_pass.decision == OAuthCallbackDesignDecision.PASS)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f"Results: {_PASS} passed, {_FAIL} failed")
if _FAIL == 0:
    print("All assertions passed.")
else:
    sys.exit(1)

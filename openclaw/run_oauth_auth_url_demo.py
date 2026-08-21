"""
V5.21 Phase 3 — OAuth authorization URL design validator demo and tests.

34 test scenarios covering all OAuthAuthUrlDesignFailureCode cases, hard-stop
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

from oauth_auth_url import (
    OAuthAuthUrlDesignDecision,
    OAuthAuthUrlDesignFailureCode,
    OAuthAuthUrlDesignInput,
    validate_oauth_auth_url_design,
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


def _valid() -> OAuthAuthUrlDesignInput:
    """Return a fully-valid OAuthAuthUrlDesignInput with all conditions met."""
    return OAuthAuthUrlDesignInput(
        oauth_execution_detected=False,
        authorization_url_generated=False,
        browser_open_detected=False,
        real_client_id_present=False,
        client_secret_present=False,
        auth_code_present=False,
        token_present=False,
        redirect_uri_present=True,
        redirect_uri_approved=True,
        scopes_present=True,
        scopes_approved=True,
        broad_scope_detected=False,
        unexpected_scope_present=False,
        state_present=True,
        state_one_time_use=True,
        state_bound_to_ceremony=True,
        prompt_is_consent=True,
        access_type_is_offline=True,
        include_granted_scopes_is_false=True,
        approval_present=True,
        approval_valid=True,
        execution_window_present=True,
        operator_confirmation_present=True,
        evidence_requirement_present=True,
    )


print("=== V5.21 Phase 3: OAuth Authorization URL Design Validator Demo ===")
print()

# ---------------------------------------------------------------------------
# Test 1: valid input → PASS
# ---------------------------------------------------------------------------
print("--- Test 1: valid input ---")
r = validate_oauth_auth_url_design(_valid())
_check("ok=True", r.ok)
_check("decision=PASS", r.decision == OAuthAuthUrlDesignDecision.PASS)
_check("failure_codes empty", r.failure_codes == [])
_check("sanitized_summary is dict", isinstance(r.sanitized_summary, dict))

# ---------------------------------------------------------------------------
# Test 2: oauth_execution_detected=True → oauth_execution_detected
# ---------------------------------------------------------------------------
print("--- Test 2: oauth_execution_detected=True ---")
inp = _valid()
inp.oauth_execution_detected = True
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "oauth_execution_detected in failure_codes",
    OAuthAuthUrlDesignFailureCode.OAUTH_EXECUTION_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 3: authorization_url_generated=True → authorization_url_generated
# ---------------------------------------------------------------------------
print("--- Test 3: authorization_url_generated=True ---")
inp = _valid()
inp.authorization_url_generated = True
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "authorization_url_generated in failure_codes",
    OAuthAuthUrlDesignFailureCode.AUTHORIZATION_URL_GENERATED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 4: browser_open_detected=True → browser_open_detected
# ---------------------------------------------------------------------------
print("--- Test 4: browser_open_detected=True ---")
inp = _valid()
inp.browser_open_detected = True
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "browser_open_detected in failure_codes",
    OAuthAuthUrlDesignFailureCode.BROWSER_OPEN_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 5: real_client_id_present=True → real_client_id_present
# ---------------------------------------------------------------------------
print("--- Test 5: real_client_id_present=True ---")
inp = _valid()
inp.real_client_id_present = True
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "real_client_id_present in failure_codes",
    OAuthAuthUrlDesignFailureCode.REAL_CLIENT_ID_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 6: client_secret_present=True → client_secret_present
# ---------------------------------------------------------------------------
print("--- Test 6: client_secret_present=True ---")
inp = _valid()
inp.client_secret_present = True
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "client_secret_present in failure_codes",
    OAuthAuthUrlDesignFailureCode.CLIENT_SECRET_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 7: auth_code_present=True → auth_code_present
# ---------------------------------------------------------------------------
print("--- Test 7: auth_code_present=True ---")
inp = _valid()
inp.auth_code_present = True
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "auth_code_present in failure_codes",
    OAuthAuthUrlDesignFailureCode.AUTH_CODE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 8: token_present=True → token_present
# ---------------------------------------------------------------------------
print("--- Test 8: token_present=True ---")
inp = _valid()
inp.token_present = True
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "token_present in failure_codes",
    OAuthAuthUrlDesignFailureCode.TOKEN_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 9: redirect_uri_present=False → redirect_uri_missing
# ---------------------------------------------------------------------------
print("--- Test 9: redirect_uri_present=False ---")
inp = _valid()
inp.redirect_uri_present = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "redirect_uri_missing in failure_codes",
    OAuthAuthUrlDesignFailureCode.REDIRECT_URI_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 10: redirect_uri_approved=False → redirect_uri_not_approved
# ---------------------------------------------------------------------------
print("--- Test 10: redirect_uri_approved=False ---")
inp = _valid()
inp.redirect_uri_approved = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "redirect_uri_not_approved in failure_codes",
    OAuthAuthUrlDesignFailureCode.REDIRECT_URI_NOT_APPROVED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 11: scopes_present=False → scopes_missing
# ---------------------------------------------------------------------------
print("--- Test 11: scopes_present=False ---")
inp = _valid()
inp.scopes_present = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "scopes_missing in failure_codes",
    OAuthAuthUrlDesignFailureCode.SCOPES_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 12: scopes_approved=False → scopes_not_approved
# ---------------------------------------------------------------------------
print("--- Test 12: scopes_approved=False ---")
inp = _valid()
inp.scopes_approved = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "scopes_not_approved in failure_codes",
    OAuthAuthUrlDesignFailureCode.SCOPES_NOT_APPROVED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 13: broad_scope_detected=True → broad_scope_detected
# ---------------------------------------------------------------------------
print("--- Test 13: broad_scope_detected=True ---")
inp = _valid()
inp.broad_scope_detected = True
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "broad_scope_detected in failure_codes",
    OAuthAuthUrlDesignFailureCode.BROAD_SCOPE_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 14: unexpected_scope_present=True → unexpected_scope_present
# ---------------------------------------------------------------------------
print("--- Test 14: unexpected_scope_present=True ---")
inp = _valid()
inp.unexpected_scope_present = True
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "unexpected_scope_present in failure_codes",
    OAuthAuthUrlDesignFailureCode.UNEXPECTED_SCOPE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 15: state_present=False → state_missing
# ---------------------------------------------------------------------------
print("--- Test 15: state_present=False ---")
inp = _valid()
inp.state_present = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "state_missing in failure_codes",
    OAuthAuthUrlDesignFailureCode.STATE_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 16: state_one_time_use=False → state_not_one_time_use
# ---------------------------------------------------------------------------
print("--- Test 16: state_one_time_use=False ---")
inp = _valid()
inp.state_one_time_use = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "state_not_one_time_use in failure_codes",
    OAuthAuthUrlDesignFailureCode.STATE_NOT_ONE_TIME_USE in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 17: state_bound_to_ceremony=False → state_not_bound_to_ceremony
# ---------------------------------------------------------------------------
print("--- Test 17: state_bound_to_ceremony=False ---")
inp = _valid()
inp.state_bound_to_ceremony = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "state_not_bound_to_ceremony in failure_codes",
    OAuthAuthUrlDesignFailureCode.STATE_NOT_BOUND_TO_CEREMONY in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 18: prompt_is_consent=False → prompt_not_consent
# ---------------------------------------------------------------------------
print("--- Test 18: prompt_is_consent=False ---")
inp = _valid()
inp.prompt_is_consent = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "prompt_not_consent in failure_codes",
    OAuthAuthUrlDesignFailureCode.PROMPT_NOT_CONSENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 19: access_type_is_offline=False → access_type_not_offline
# ---------------------------------------------------------------------------
print("--- Test 19: access_type_is_offline=False ---")
inp = _valid()
inp.access_type_is_offline = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "access_type_not_offline in failure_codes",
    OAuthAuthUrlDesignFailureCode.ACCESS_TYPE_NOT_OFFLINE in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 20: include_granted_scopes_is_false=False → include_granted_scopes_not_false
# ---------------------------------------------------------------------------
print("--- Test 20: include_granted_scopes_is_false=False ---")
inp = _valid()
inp.include_granted_scopes_is_false = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "include_granted_scopes_not_false in failure_codes",
    OAuthAuthUrlDesignFailureCode.INCLUDE_GRANTED_SCOPES_NOT_FALSE in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 21: approval_present=False → approval_missing
# ---------------------------------------------------------------------------
print("--- Test 21: approval_present=False ---")
inp = _valid()
inp.approval_present = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "approval_missing in failure_codes",
    OAuthAuthUrlDesignFailureCode.APPROVAL_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 22: approval_valid=False → approval_not_valid
# ---------------------------------------------------------------------------
print("--- Test 22: approval_valid=False ---")
inp = _valid()
inp.approval_valid = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "approval_not_valid in failure_codes",
    OAuthAuthUrlDesignFailureCode.APPROVAL_NOT_VALID in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 23: execution_window_present=False → execution_window_missing
# ---------------------------------------------------------------------------
print("--- Test 23: execution_window_present=False ---")
inp = _valid()
inp.execution_window_present = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "execution_window_missing in failure_codes",
    OAuthAuthUrlDesignFailureCode.EXECUTION_WINDOW_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 24: operator_confirmation_present=False → operator_confirmation_missing
# ---------------------------------------------------------------------------
print("--- Test 24: operator_confirmation_present=False ---")
inp = _valid()
inp.operator_confirmation_present = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "operator_confirmation_missing in failure_codes",
    OAuthAuthUrlDesignFailureCode.OPERATOR_CONFIRMATION_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 25: evidence_requirement_present=False → evidence_requirement_missing
# ---------------------------------------------------------------------------
print("--- Test 25: evidence_requirement_present=False ---")
inp = _valid()
inp.evidence_requirement_present = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "evidence_requirement_missing in failure_codes",
    OAuthAuthUrlDesignFailureCode.EVIDENCE_REQUIREMENT_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 26: forbidden field in evidence → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 26: forbidden field in evidence ---")
inp = _valid()
inp.evidence = {"client_id": "some-placeholder-value"}
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes",
    OAuthAuthUrlDesignFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 27: forbidden field in metadata → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 27: forbidden field in metadata ---")
inp = _valid()
inp.metadata = {"api_response_payload": "placeholder"}
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes (metadata)",
    OAuthAuthUrlDesignFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 28: forbidden value in evidence (refresh token prefix pattern)
# ---------------------------------------------------------------------------
print("--- Test 28: forbidden value in evidence (refresh token pattern) ---")
inp = _valid()
inp.evidence = {"notes": "1//abc"}
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (refresh token prefix)",
    OAuthAuthUrlDesignFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 29: forbidden value in metadata (credential field name as value)
# ---------------------------------------------------------------------------
print("--- Test 29: forbidden value in metadata (credential field name as value) ---")
inp = _valid()
inp.metadata = {"note": "client_secret"}
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (metadata)",
    OAuthAuthUrlDesignFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 30: forbidden value in evidence (GCP resource path pattern)
# ---------------------------------------------------------------------------
print("--- Test 30: forbidden value in evidence (GCP path) ---")
inp = _valid()
inp.evidence = {"drill_notes": "projects/my-test-project/secrets/my-test-secret"}
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (GCP path)",
    OAuthAuthUrlDesignFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 31: sanitized_summary excludes evidence and metadata
# ---------------------------------------------------------------------------
print("--- Test 31: sanitized_summary excludes evidence/metadata ---")
inp = _valid()
inp.evidence = {"notes": "redacted-ceremony-note"}
inp.metadata = {"source": "local-design-check"}
r = validate_oauth_auth_url_design(inp)
_check("evidence not in sanitized_summary", "evidence" not in r.sanitized_summary)
_check("metadata not in sanitized_summary", "metadata" not in r.sanitized_summary)

# ---------------------------------------------------------------------------
# Test 32: sanitized_summary contains expected fields
# ---------------------------------------------------------------------------
print("--- Test 32: sanitized_summary shape ---")
r = validate_oauth_auth_url_design(_valid())
summary = r.sanitized_summary
_check("oauth_execution_detected in summary", "oauth_execution_detected" in summary)
_check("authorization_url_generated in summary", "authorization_url_generated" in summary)
_check("browser_open_detected in summary", "browser_open_detected" in summary)
_check("redirect_uri_approved in summary", "redirect_uri_approved" in summary)
_check("scopes_approved in summary", "scopes_approved" in summary)
_check("state_one_time_use in summary", "state_one_time_use" in summary)
_check("state_bound_to_ceremony in summary", "state_bound_to_ceremony" in summary)
_check("prompt_is_consent in summary", "prompt_is_consent" in summary)
_check("access_type_is_offline in summary", "access_type_is_offline" in summary)
_check("include_granted_scopes_is_false in summary", "include_granted_scopes_is_false" in summary)
_check(
    "ok + decision + failure_count in summary",
    "ok" in summary and "decision" in summary and "failure_count" in summary,
)

# ---------------------------------------------------------------------------
# Test 33: multiple failures accumulate in failure_codes
# ---------------------------------------------------------------------------
print("--- Test 33: multiple failures ---")
inp = _valid()
inp.authorization_url_generated = True
inp.scopes_approved = False
inp.state_one_time_use = False
inp.approval_valid = False
r = validate_oauth_auth_url_design(inp)
_check("ok=False", not r.ok)
_check("failure_count >= 4", r.sanitized_summary["failure_count"] >= 4)
_check("failure_codes len >= 4", len(r.failure_codes) >= 4)

# ---------------------------------------------------------------------------
# Test 34: required_actions non-empty on failure; empty on PASS
# ---------------------------------------------------------------------------
print("--- Test 34: required_actions behavior ---")
inp = _valid()
inp.operator_confirmation_present = False
r = validate_oauth_auth_url_design(inp)
_check("required_actions non-empty on failure", len(r.required_actions) > 0)
_check(
    "required_actions length matches failure_codes",
    len(r.required_actions) == len(r.failure_codes),
)
r_pass = validate_oauth_auth_url_design(_valid())
_check("required_actions empty on PASS", r_pass.required_actions == [])
_check("decision=PASS", r_pass.decision == OAuthAuthUrlDesignDecision.PASS)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f"Results: {_PASS} passed, {_FAIL} failed")
if _FAIL == 0:
    print("All assertions passed.")
else:
    sys.exit(1)

"""
V5.22 Phase 3 — OAuth dry-run execution packet validator demo.

55 test scenarios covering all OAuthDryRunExecutionFailureCode cases: packet
completeness requirements, pre-flight and validator gate requirements, dry-run
sequence and evidence requirements, hard-stop detections, forbidden field/value
detection, sanitized_summary exclusions, multiple-failure accumulation, and
required_actions behavior.

No real credentials. No real approval records. No real participant identities.
No real tenant/client IDs. No OAuth. No browser. No auth URL. No callback URL.
No auth code. No token exchange. No GCP commands. No Secret Manager. No network calls.
No filesystem I/O. GOOGLE_ADS_LIVE_ENABLED remains false.
"""

import sys
from pathlib import Path

_DIR = str(Path(__file__).resolve().parent)
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from oauth_dry_run_execution import (
    OAuthDryRunExecutionDecision,
    OAuthDryRunExecutionFailureCode,
    OAuthDryRunExecutionInput,
    validate_oauth_dry_run_execution,
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


def _valid() -> OAuthDryRunExecutionInput:
    """Return a fully-valid OAuthDryRunExecutionInput with all conditions met."""
    return OAuthDryRunExecutionInput(
        packet_present=True,
        packet_identity_present=True,
        branch_ref_present=True,
        baseline_ref_present=True,
        participant_placeholders_present=True,
        target_context_placeholders_present=True,
        timed_window_present=True,
        timed_window_timeboxed=True,
        stop_authority_present=True,
        rollback_owner_present=True,
        emergency_revoke_owner_present=True,
        evidence_owner_present=True,
        preflight_gates_present=True,
        approval_packet_gate_passed=True,
        auth_url_design_gate_passed=True,
        callback_boundary_gate_passed=True,
        credential_intake_gate_passed=True,
        secret_version_policy_gate_passed=True,
        rollback_drill_gate_passed=True,
        onboarding_ceremony_gate_passed=True,
        smoke_credentials_passed=True,
        smoke_secret_manager_passed=True,
        safety_grep_clean=True,
        dry_run_sequence_complete=True,
        validator_evidence_present=True,
        no_execution_confirmations_present=True,
        evidence_package_redacted=True,
        stop_conditions_reviewed=True,
        rollback_rehearsal_present=True,
        final_decision_present=True,
        real_credential_present=False,
        real_approval_created=False,
        oauth_execution_detected=False,
        browser_opened=False,
        authorization_url_generated=False,
        callback_url_received=False,
        auth_code_received=False,
        token_exchange_attempted=False,
        token_response_received=False,
        secret_manager_called=False,
        google_ads_api_called=False,
        gcp_commands_used=False,
        deploy_performed=False,
        iam_api_billing_changed=False,
        live_flag_activated=False,
    )


print("=== V5.22 Phase 3: OAuth Dry-Run Execution Packet Validator Demo ===")
print()

# ---------------------------------------------------------------------------
# Test 1: valid input → PASS
# ---------------------------------------------------------------------------
print("--- Test 1: valid input ---")
r = validate_oauth_dry_run_execution(_valid())
_check("ok=True", r.ok)
_check("decision=PASS", r.decision == OAuthDryRunExecutionDecision.PASS)
_check("failure_codes empty", r.failure_codes == [])
_check("sanitized_summary is dict", isinstance(r.sanitized_summary, dict))

# ---------------------------------------------------------------------------
# Test 2: packet_present=False → packet_missing
# ---------------------------------------------------------------------------
print("--- Test 2: packet_present=False ---")
inp = _valid()
inp.packet_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "packet_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.PACKET_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 3: packet_identity_present=False → packet_identity_missing
# ---------------------------------------------------------------------------
print("--- Test 3: packet_identity_present=False ---")
inp = _valid()
inp.packet_identity_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "packet_identity_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.PACKET_IDENTITY_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 4: branch_ref_present=False → branch_ref_missing
# ---------------------------------------------------------------------------
print("--- Test 4: branch_ref_present=False ---")
inp = _valid()
inp.branch_ref_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "branch_ref_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.BRANCH_REF_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 5: baseline_ref_present=False → baseline_ref_missing
# ---------------------------------------------------------------------------
print("--- Test 5: baseline_ref_present=False ---")
inp = _valid()
inp.baseline_ref_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "baseline_ref_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.BASELINE_REF_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 6: participant_placeholders_present=False → participant_placeholders_missing
# ---------------------------------------------------------------------------
print("--- Test 6: participant_placeholders_present=False ---")
inp = _valid()
inp.participant_placeholders_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "participant_placeholders_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.PARTICIPANT_PLACEHOLDERS_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 7: target_context_placeholders_present=False → target_context_placeholders_missing
# ---------------------------------------------------------------------------
print("--- Test 7: target_context_placeholders_present=False ---")
inp = _valid()
inp.target_context_placeholders_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "target_context_placeholders_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.TARGET_CONTEXT_PLACEHOLDERS_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 8: timed_window_present=False → timed_window_missing
# ---------------------------------------------------------------------------
print("--- Test 8: timed_window_present=False ---")
inp = _valid()
inp.timed_window_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "timed_window_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.TIMED_WINDOW_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 9: timed_window_timeboxed=False → timed_window_not_timeboxed
# ---------------------------------------------------------------------------
print("--- Test 9: timed_window_timeboxed=False ---")
inp = _valid()
inp.timed_window_timeboxed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "timed_window_not_timeboxed in failure_codes",
    OAuthDryRunExecutionFailureCode.TIMED_WINDOW_NOT_TIMEBOXED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 10: stop_authority_present=False → stop_authority_missing
# ---------------------------------------------------------------------------
print("--- Test 10: stop_authority_present=False ---")
inp = _valid()
inp.stop_authority_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "stop_authority_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.STOP_AUTHORITY_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 11: rollback_owner_present=False → rollback_owner_missing
# ---------------------------------------------------------------------------
print("--- Test 11: rollback_owner_present=False ---")
inp = _valid()
inp.rollback_owner_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "rollback_owner_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.ROLLBACK_OWNER_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 12: emergency_revoke_owner_present=False → emergency_revoke_owner_missing
# ---------------------------------------------------------------------------
print("--- Test 12: emergency_revoke_owner_present=False ---")
inp = _valid()
inp.emergency_revoke_owner_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "emergency_revoke_owner_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.EMERGENCY_REVOKE_OWNER_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 13: evidence_owner_present=False → evidence_owner_missing
# ---------------------------------------------------------------------------
print("--- Test 13: evidence_owner_present=False ---")
inp = _valid()
inp.evidence_owner_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "evidence_owner_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.EVIDENCE_OWNER_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 14: preflight_gates_present=False → preflight_gates_missing
# ---------------------------------------------------------------------------
print("--- Test 14: preflight_gates_present=False ---")
inp = _valid()
inp.preflight_gates_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "preflight_gates_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.PREFLIGHT_GATES_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 15: approval_packet_gate_passed=False → approval_packet_gate_not_passed
# ---------------------------------------------------------------------------
print("--- Test 15: approval_packet_gate_passed=False ---")
inp = _valid()
inp.approval_packet_gate_passed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "approval_packet_gate_not_passed in failure_codes",
    OAuthDryRunExecutionFailureCode.APPROVAL_PACKET_GATE_NOT_PASSED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 16: auth_url_design_gate_passed=False → auth_url_design_gate_not_passed
# ---------------------------------------------------------------------------
print("--- Test 16: auth_url_design_gate_passed=False ---")
inp = _valid()
inp.auth_url_design_gate_passed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "auth_url_design_gate_not_passed in failure_codes",
    OAuthDryRunExecutionFailureCode.AUTH_URL_DESIGN_GATE_NOT_PASSED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 17: callback_boundary_gate_passed=False → callback_boundary_gate_not_passed
# ---------------------------------------------------------------------------
print("--- Test 17: callback_boundary_gate_passed=False ---")
inp = _valid()
inp.callback_boundary_gate_passed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "callback_boundary_gate_not_passed in failure_codes",
    OAuthDryRunExecutionFailureCode.CALLBACK_BOUNDARY_GATE_NOT_PASSED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 18: credential_intake_gate_passed=False → credential_intake_gate_not_passed
# ---------------------------------------------------------------------------
print("--- Test 18: credential_intake_gate_passed=False ---")
inp = _valid()
inp.credential_intake_gate_passed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "credential_intake_gate_not_passed in failure_codes",
    OAuthDryRunExecutionFailureCode.CREDENTIAL_INTAKE_GATE_NOT_PASSED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 19: secret_version_policy_gate_passed=False → secret_version_policy_gate_not_passed
# ---------------------------------------------------------------------------
print("--- Test 19: secret_version_policy_gate_passed=False ---")
inp = _valid()
inp.secret_version_policy_gate_passed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "secret_version_policy_gate_not_passed in failure_codes",
    OAuthDryRunExecutionFailureCode.SECRET_VERSION_POLICY_GATE_NOT_PASSED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 20: rollback_drill_gate_passed=False → rollback_drill_gate_not_passed
# ---------------------------------------------------------------------------
print("--- Test 20: rollback_drill_gate_passed=False ---")
inp = _valid()
inp.rollback_drill_gate_passed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "rollback_drill_gate_not_passed in failure_codes",
    OAuthDryRunExecutionFailureCode.ROLLBACK_DRILL_GATE_NOT_PASSED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 21: onboarding_ceremony_gate_passed=False → onboarding_ceremony_gate_not_passed
# ---------------------------------------------------------------------------
print("--- Test 21: onboarding_ceremony_gate_passed=False ---")
inp = _valid()
inp.onboarding_ceremony_gate_passed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "onboarding_ceremony_gate_not_passed in failure_codes",
    OAuthDryRunExecutionFailureCode.ONBOARDING_CEREMONY_GATE_NOT_PASSED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 22: smoke_credentials_passed=False → smoke_credentials_not_passed
# ---------------------------------------------------------------------------
print("--- Test 22: smoke_credentials_passed=False ---")
inp = _valid()
inp.smoke_credentials_passed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "smoke_credentials_not_passed in failure_codes",
    OAuthDryRunExecutionFailureCode.SMOKE_CREDENTIALS_NOT_PASSED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 23: smoke_secret_manager_passed=False → smoke_secret_manager_not_passed
# ---------------------------------------------------------------------------
print("--- Test 23: smoke_secret_manager_passed=False ---")
inp = _valid()
inp.smoke_secret_manager_passed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "smoke_secret_manager_not_passed in failure_codes",
    OAuthDryRunExecutionFailureCode.SMOKE_SECRET_MANAGER_NOT_PASSED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 24: safety_grep_clean=False → safety_grep_not_clean
# ---------------------------------------------------------------------------
print("--- Test 24: safety_grep_clean=False ---")
inp = _valid()
inp.safety_grep_clean = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "safety_grep_not_clean in failure_codes",
    OAuthDryRunExecutionFailureCode.SAFETY_GREP_NOT_CLEAN in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 25: dry_run_sequence_complete=False → dry_run_sequence_incomplete
# ---------------------------------------------------------------------------
print("--- Test 25: dry_run_sequence_complete=False ---")
inp = _valid()
inp.dry_run_sequence_complete = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "dry_run_sequence_incomplete in failure_codes",
    OAuthDryRunExecutionFailureCode.DRY_RUN_SEQUENCE_INCOMPLETE in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 26: validator_evidence_present=False → validator_evidence_missing
# ---------------------------------------------------------------------------
print("--- Test 26: validator_evidence_present=False ---")
inp = _valid()
inp.validator_evidence_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "validator_evidence_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.VALIDATOR_EVIDENCE_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 27: no_execution_confirmations_present=False → no_execution_confirmations_missing
# ---------------------------------------------------------------------------
print("--- Test 27: no_execution_confirmations_present=False ---")
inp = _valid()
inp.no_execution_confirmations_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "no_execution_confirmations_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.NO_EXECUTION_CONFIRMATIONS_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 28: evidence_package_redacted=False → evidence_package_not_redacted
# ---------------------------------------------------------------------------
print("--- Test 28: evidence_package_redacted=False ---")
inp = _valid()
inp.evidence_package_redacted = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "evidence_package_not_redacted in failure_codes",
    OAuthDryRunExecutionFailureCode.EVIDENCE_PACKAGE_NOT_REDACTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 29: stop_conditions_reviewed=False → stop_conditions_not_reviewed
# ---------------------------------------------------------------------------
print("--- Test 29: stop_conditions_reviewed=False ---")
inp = _valid()
inp.stop_conditions_reviewed = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "stop_conditions_not_reviewed in failure_codes",
    OAuthDryRunExecutionFailureCode.STOP_CONDITIONS_NOT_REVIEWED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 30: rollback_rehearsal_present=False → rollback_rehearsal_missing
# ---------------------------------------------------------------------------
print("--- Test 30: rollback_rehearsal_present=False ---")
inp = _valid()
inp.rollback_rehearsal_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "rollback_rehearsal_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.ROLLBACK_REHEARSAL_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 31: final_decision_present=False → final_decision_missing
# ---------------------------------------------------------------------------
print("--- Test 31: final_decision_present=False ---")
inp = _valid()
inp.final_decision_present = False
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "final_decision_missing in failure_codes",
    OAuthDryRunExecutionFailureCode.FINAL_DECISION_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 32: real_credential_present=True → real_credential_present
# ---------------------------------------------------------------------------
print("--- Test 32: real_credential_present=True ---")
inp = _valid()
inp.real_credential_present = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "real_credential_present in failure_codes",
    OAuthDryRunExecutionFailureCode.REAL_CREDENTIAL_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 33: real_approval_created=True → real_approval_created
# ---------------------------------------------------------------------------
print("--- Test 33: real_approval_created=True ---")
inp = _valid()
inp.real_approval_created = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "real_approval_created in failure_codes",
    OAuthDryRunExecutionFailureCode.REAL_APPROVAL_CREATED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 34: oauth_execution_detected=True → oauth_execution_detected
# ---------------------------------------------------------------------------
print("--- Test 34: oauth_execution_detected=True ---")
inp = _valid()
inp.oauth_execution_detected = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "oauth_execution_detected in failure_codes",
    OAuthDryRunExecutionFailureCode.OAUTH_EXECUTION_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 35: browser_opened=True → browser_opened
# ---------------------------------------------------------------------------
print("--- Test 35: browser_opened=True ---")
inp = _valid()
inp.browser_opened = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "browser_opened in failure_codes",
    OAuthDryRunExecutionFailureCode.BROWSER_OPENED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 36: authorization_url_generated=True → authorization_url_generated
# ---------------------------------------------------------------------------
print("--- Test 36: authorization_url_generated=True ---")
inp = _valid()
inp.authorization_url_generated = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "authorization_url_generated in failure_codes",
    OAuthDryRunExecutionFailureCode.AUTHORIZATION_URL_GENERATED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 37: callback_url_received=True → callback_url_received
# ---------------------------------------------------------------------------
print("--- Test 37: callback_url_received=True ---")
inp = _valid()
inp.callback_url_received = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "callback_url_received in failure_codes",
    OAuthDryRunExecutionFailureCode.CALLBACK_URL_RECEIVED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 38: auth_code_received=True → auth_code_received
# ---------------------------------------------------------------------------
print("--- Test 38: auth_code_received=True ---")
inp = _valid()
inp.auth_code_received = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "auth_code_received in failure_codes",
    OAuthDryRunExecutionFailureCode.AUTH_CODE_RECEIVED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 39: token_exchange_attempted=True → token_exchange_attempted
# ---------------------------------------------------------------------------
print("--- Test 39: token_exchange_attempted=True ---")
inp = _valid()
inp.token_exchange_attempted = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "token_exchange_attempted in failure_codes",
    OAuthDryRunExecutionFailureCode.TOKEN_EXCHANGE_ATTEMPTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 40: token_response_received=True → token_response_received
# ---------------------------------------------------------------------------
print("--- Test 40: token_response_received=True ---")
inp = _valid()
inp.token_response_received = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "token_response_received in failure_codes",
    OAuthDryRunExecutionFailureCode.TOKEN_RESPONSE_RECEIVED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 41: secret_manager_called=True → secret_manager_called
# ---------------------------------------------------------------------------
print("--- Test 41: secret_manager_called=True ---")
inp = _valid()
inp.secret_manager_called = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "secret_manager_called in failure_codes",
    OAuthDryRunExecutionFailureCode.SECRET_MANAGER_CALLED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 42: google_ads_api_called=True → google_ads_api_called
# ---------------------------------------------------------------------------
print("--- Test 42: google_ads_api_called=True ---")
inp = _valid()
inp.google_ads_api_called = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "google_ads_api_called in failure_codes",
    OAuthDryRunExecutionFailureCode.GOOGLE_ADS_API_CALLED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 43: gcp_commands_used=True → gcp_commands_used
# ---------------------------------------------------------------------------
print("--- Test 43: gcp_commands_used=True ---")
inp = _valid()
inp.gcp_commands_used = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "gcp_commands_used in failure_codes",
    OAuthDryRunExecutionFailureCode.GCP_COMMANDS_USED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 44: deploy_performed=True → deploy_performed
# ---------------------------------------------------------------------------
print("--- Test 44: deploy_performed=True ---")
inp = _valid()
inp.deploy_performed = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "deploy_performed in failure_codes",
    OAuthDryRunExecutionFailureCode.DEPLOY_PERFORMED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 45: iam_api_billing_changed=True → iam_api_billing_changed
# ---------------------------------------------------------------------------
print("--- Test 45: iam_api_billing_changed=True ---")
inp = _valid()
inp.iam_api_billing_changed = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "iam_api_billing_changed in failure_codes",
    OAuthDryRunExecutionFailureCode.IAM_API_BILLING_CHANGED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 46: live_flag_activated=True → live_flag_activated
# ---------------------------------------------------------------------------
print("--- Test 46: live_flag_activated=True ---")
inp = _valid()
inp.live_flag_activated = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "live_flag_activated in failure_codes",
    OAuthDryRunExecutionFailureCode.LIVE_FLAG_ACTIVATED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 47: forbidden field in evidence → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 47: forbidden field in evidence ---")
inp = _valid()
inp.evidence = {"raw_packet_payload": "placeholder-value"}
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes",
    OAuthDryRunExecutionFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 48: forbidden field in metadata → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 48: forbidden field in metadata ---")
inp = _valid()
inp.metadata = {"real_participant_name": "placeholder"}
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes (metadata)",
    OAuthDryRunExecutionFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 49: forbidden value in evidence (refresh token prefix pattern)
# ---------------------------------------------------------------------------
print("--- Test 49: forbidden value in evidence (refresh token pattern) ---")
inp = _valid()
inp.evidence = {"notes": "1//abc"}
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (refresh token prefix)",
    OAuthDryRunExecutionFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 50: forbidden value in metadata (credential field name as value)
# ---------------------------------------------------------------------------
print("--- Test 50: forbidden value in metadata (field name as value) ---")
inp = _valid()
inp.metadata = {"note": "callback_url"}
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (metadata field-name-as-value)",
    OAuthDryRunExecutionFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 51: sanitized_summary excludes evidence and metadata
# ---------------------------------------------------------------------------
print("--- Test 51: sanitized_summary excludes evidence/metadata ---")
inp = _valid()
inp.evidence = {"raw_evidence_payload": "placeholder"}
r = validate_oauth_dry_run_execution(inp)
_check("evidence not in sanitized_summary", "evidence" not in r.sanitized_summary)
_check("metadata not in sanitized_summary", "metadata" not in r.sanitized_summary)

# ---------------------------------------------------------------------------
# Test 52: sanitized_summary excludes forbidden values
# ---------------------------------------------------------------------------
print("--- Test 52: sanitized_summary excludes forbidden values ---")
inp = _valid()
inp.evidence = {"notes": "1//abc"}
r = validate_oauth_dry_run_execution(inp)
summary_values = [v for v in r.sanitized_summary.values() if isinstance(v, str)]
_check(
    "forbidden refresh token prefix not in sanitized_summary values",
    not any("1//abc" in v for v in summary_values),
)

# ---------------------------------------------------------------------------
# Test 53: multiple failures accumulate in failure_codes
# ---------------------------------------------------------------------------
print("--- Test 53: multiple failures ---")
inp = _valid()
inp.packet_present = False
inp.participant_placeholders_present = False
inp.approval_packet_gate_passed = False
inp.safety_grep_clean = False
inp.real_credential_present = True
r = validate_oauth_dry_run_execution(inp)
_check("ok=False", not r.ok)
_check("failure_count >= 5", r.sanitized_summary["failure_count"] >= 5)
_check("failure_codes len >= 5", len(r.failure_codes) >= 5)

# ---------------------------------------------------------------------------
# Test 54: required_actions non-empty on failure; length matches failure_codes
# ---------------------------------------------------------------------------
print("--- Test 54: required_actions non-empty on failure ---")
inp = _valid()
inp.rollback_owner_present = False
r = validate_oauth_dry_run_execution(inp)
_check("required_actions non-empty", len(r.required_actions) > 0)
_check(
    "required_actions length matches failure_codes",
    len(r.required_actions) == len(r.failure_codes),
)

# ---------------------------------------------------------------------------
# Test 55: required_actions empty on PASS
# ---------------------------------------------------------------------------
print("--- Test 55: required_actions empty on PASS ---")
r_pass = validate_oauth_dry_run_execution(_valid())
_check("required_actions empty on PASS", r_pass.required_actions == [])
_check("decision=PASS", r_pass.decision == OAuthDryRunExecutionDecision.PASS)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f"Results: {_PASS} passed, {_FAIL} failed")
if _FAIL == 0:
    print("All assertions passed.")
else:
    sys.exit(1)

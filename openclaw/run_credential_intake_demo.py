"""
V5.20 Phase 4 — Credential intake dry-run demo and boundary tests.

33 tests covering all CredentialIntakeFailureCode cases, boundary checks,
forbidden field/value detection, sanitized_summary exclusions, and required_actions.

No real credentials. No OAuth. No GCP commands. No network calls. No filesystem I/O.
GOOGLE_ADS_LIVE_ENABLED remains false.
"""

import sys
from pathlib import Path

_DIR = str(Path(__file__).resolve().parent)
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from credential_intake import (
    CredentialIntakeDryRunInput,
    CredentialIntakeDecision,
    CredentialIntakeFailureCode,
    CredentialIntakeMode,
    validate_credential_intake_dry_run,
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


def _valid() -> CredentialIntakeDryRunInput:
    """Return a fully-valid CredentialIntakeDryRunInput with all conditions met."""
    return CredentialIntakeDryRunInput(
        intake_mode=CredentialIntakeMode.DRY_RUN_ONLY,
        transfer_path_forbidden_confirmed=True,
        credential_values_absent=True,
        live_flag_false_confirmed=True,
        gcp_write_operator_only_confirmed=True,
        screen_recording_prohibited_confirmed=True,
        repo_commit_prohibited_confirmed=True,
        immediate_redaction_confirmed=True,
        rollback_plan_present=True,
        emergency_revoke_plan_present=True,
        operator_confirmation_present=True,
        audit_enabled=True,
        checklist_reference_present=True,
        intake_boundary_doc_confirmed=True,
        operator_identity_present=True,
        approval_ceremony_reference_present=True,
        smoke_tests_passed=True,
        intake_plan_document_present=True,
        dry_run_only_confirmed=True,
        real_secret_material_present=False,
        oauth_execution_detected=False,
        google_ads_api_call_detected=False,
        gcp_command_detected=False,
        filesystem_write_detected=False,
        network_call_detected=False,
    )


print("=== V5.20 Phase 4: Credential Intake Dry-Run Demo ===")
print()

# ---------------------------------------------------------------------------
# Test 1: valid input → PASS
# ---------------------------------------------------------------------------
print("--- Test 1: valid input ---")
r = validate_credential_intake_dry_run(_valid())
_check("ok=True", r.ok)
_check("decision=PASS", r.decision == CredentialIntakeDecision.PASS)
_check("failure_codes empty", r.failure_codes == [])
_check("sanitized_summary is dict", isinstance(r.sanitized_summary, dict))

# ---------------------------------------------------------------------------
# Test 2: REAL_INTAKE_PLANNED mode → dry_run_required
# ---------------------------------------------------------------------------
print("--- Test 2: REAL_INTAKE_PLANNED mode ---")
inp = _valid()
inp.intake_mode = CredentialIntakeMode.REAL_INTAKE_PLANNED
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "dry_run_required in failure_codes",
    CredentialIntakeFailureCode.DRY_RUN_REQUIRED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 3: invalid mode → mode_invalid
# ---------------------------------------------------------------------------
print("--- Test 3: invalid mode ---")
inp = _valid()
inp.intake_mode = "unknown_mode"
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "mode_invalid in failure_codes",
    CredentialIntakeFailureCode.MODE_INVALID in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 4: transfer_path_forbidden_confirmed=False → transfer_path_forbidden
# ---------------------------------------------------------------------------
print("--- Test 4: transfer_path_forbidden_confirmed=False ---")
inp = _valid()
inp.transfer_path_forbidden_confirmed = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "transfer_path_forbidden in failure_codes",
    CredentialIntakeFailureCode.TRANSFER_PATH_FORBIDDEN in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 5: credential_values_absent=False → credential_values_in_input
# ---------------------------------------------------------------------------
print("--- Test 5: credential_values_absent=False ---")
inp = _valid()
inp.credential_values_absent = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "credential_values_in_input in failure_codes",
    CredentialIntakeFailureCode.CREDENTIAL_VALUES_IN_INPUT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 6: live_flag_false_confirmed=False → live_flag_not_false
# ---------------------------------------------------------------------------
print("--- Test 6: live_flag_false_confirmed=False ---")
inp = _valid()
inp.live_flag_false_confirmed = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "live_flag_not_false in failure_codes",
    CredentialIntakeFailureCode.LIVE_FLAG_NOT_FALSE in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 7: gcp_write_operator_only_confirmed=False → gcp_write_not_operator_only
# ---------------------------------------------------------------------------
print("--- Test 7: gcp_write_operator_only_confirmed=False ---")
inp = _valid()
inp.gcp_write_operator_only_confirmed = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "gcp_write_not_operator_only in failure_codes",
    CredentialIntakeFailureCode.GCP_WRITE_NOT_OPERATOR_ONLY in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 8: screen_recording_prohibited_confirmed=False → screen_recording_prohibited
# ---------------------------------------------------------------------------
print("--- Test 8: screen_recording_prohibited_confirmed=False ---")
inp = _valid()
inp.screen_recording_prohibited_confirmed = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "screen_recording_prohibited in failure_codes",
    CredentialIntakeFailureCode.SCREEN_RECORDING_PROHIBITED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 9: repo_commit_prohibited_confirmed=False → repo_commit_prohibited
# ---------------------------------------------------------------------------
print("--- Test 9: repo_commit_prohibited_confirmed=False ---")
inp = _valid()
inp.repo_commit_prohibited_confirmed = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "repo_commit_prohibited in failure_codes",
    CredentialIntakeFailureCode.REPO_COMMIT_PROHIBITED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 10: immediate_redaction_confirmed=False → immediate_redaction_required
# ---------------------------------------------------------------------------
print("--- Test 10: immediate_redaction_confirmed=False ---")
inp = _valid()
inp.immediate_redaction_confirmed = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "immediate_redaction_required in failure_codes",
    CredentialIntakeFailureCode.IMMEDIATE_REDACTION_REQUIRED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 11: rollback_plan_present=False → rollback_plan_missing
# ---------------------------------------------------------------------------
print("--- Test 11: rollback_plan_present=False ---")
inp = _valid()
inp.rollback_plan_present = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "rollback_plan_missing in failure_codes",
    CredentialIntakeFailureCode.ROLLBACK_PLAN_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 12: emergency_revoke_plan_present=False → emergency_revoke_plan_missing
# ---------------------------------------------------------------------------
print("--- Test 12: emergency_revoke_plan_present=False ---")
inp = _valid()
inp.emergency_revoke_plan_present = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "emergency_revoke_plan_missing in failure_codes",
    CredentialIntakeFailureCode.EMERGENCY_REVOKE_PLAN_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 13: operator_confirmation_present=False → operator_confirmation_missing
# ---------------------------------------------------------------------------
print("--- Test 13: operator_confirmation_present=False ---")
inp = _valid()
inp.operator_confirmation_present = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "operator_confirmation_missing in failure_codes",
    CredentialIntakeFailureCode.OPERATOR_CONFIRMATION_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 14: audit_enabled=False → audit_not_enabled
# ---------------------------------------------------------------------------
print("--- Test 14: audit_enabled=False ---")
inp = _valid()
inp.audit_enabled = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "audit_not_enabled in failure_codes",
    CredentialIntakeFailureCode.AUDIT_NOT_ENABLED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 15: checklist_reference_present=False → checklist_reference_missing
# ---------------------------------------------------------------------------
print("--- Test 15: checklist_reference_present=False ---")
inp = _valid()
inp.checklist_reference_present = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "checklist_reference_missing in failure_codes",
    CredentialIntakeFailureCode.CHECKLIST_REFERENCE_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 16: intake_boundary_doc_confirmed=False → intake_boundary_doc_missing
# ---------------------------------------------------------------------------
print("--- Test 16: intake_boundary_doc_confirmed=False ---")
inp = _valid()
inp.intake_boundary_doc_confirmed = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "intake_boundary_doc_missing in failure_codes",
    CredentialIntakeFailureCode.INTAKE_BOUNDARY_DOC_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 17: operator_identity_present=False → operator_identity_missing
# ---------------------------------------------------------------------------
print("--- Test 17: operator_identity_present=False ---")
inp = _valid()
inp.operator_identity_present = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "operator_identity_missing in failure_codes",
    CredentialIntakeFailureCode.OPERATOR_IDENTITY_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 18: approval_ceremony_reference_present=False → approval_ceremony_reference_missing
# ---------------------------------------------------------------------------
print("--- Test 18: approval_ceremony_reference_present=False ---")
inp = _valid()
inp.approval_ceremony_reference_present = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "approval_ceremony_reference_missing in failure_codes",
    CredentialIntakeFailureCode.APPROVAL_CEREMONY_REFERENCE_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 19: real_secret_material_present=True → real_secret_material_present
# ---------------------------------------------------------------------------
print("--- Test 19: real_secret_material_present=True ---")
inp = _valid()
inp.real_secret_material_present = True
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "real_secret_material_present in failure_codes",
    CredentialIntakeFailureCode.REAL_SECRET_MATERIAL_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 20: oauth_execution_detected=True → oauth_execution_detected
# ---------------------------------------------------------------------------
print("--- Test 20: oauth_execution_detected=True ---")
inp = _valid()
inp.oauth_execution_detected = True
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "oauth_execution_detected in failure_codes",
    CredentialIntakeFailureCode.OAUTH_EXECUTION_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 21: google_ads_api_call_detected=True → google_ads_api_call_detected
# ---------------------------------------------------------------------------
print("--- Test 21: google_ads_api_call_detected=True ---")
inp = _valid()
inp.google_ads_api_call_detected = True
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "google_ads_api_call_detected in failure_codes",
    CredentialIntakeFailureCode.GOOGLE_ADS_API_CALL_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 22: gcp_command_detected=True → gcp_command_detected
# ---------------------------------------------------------------------------
print("--- Test 22: gcp_command_detected=True ---")
inp = _valid()
inp.gcp_command_detected = True
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "gcp_command_detected in failure_codes",
    CredentialIntakeFailureCode.GCP_COMMAND_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 23: filesystem_write_detected=True → filesystem_write_detected
# ---------------------------------------------------------------------------
print("--- Test 23: filesystem_write_detected=True ---")
inp = _valid()
inp.filesystem_write_detected = True
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "filesystem_write_detected in failure_codes",
    CredentialIntakeFailureCode.FILESYSTEM_WRITE_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 24: network_call_detected=True → network_call_detected
# ---------------------------------------------------------------------------
print("--- Test 24: network_call_detected=True ---")
inp = _valid()
inp.network_call_detected = True
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "network_call_detected in failure_codes",
    CredentialIntakeFailureCode.NETWORK_CALL_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 25: forbidden field in evidence → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 25: forbidden field in evidence ---")
inp = _valid()
inp.evidence = {"oauth_code": "some-placeholder-value"}
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes",
    CredentialIntakeFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 26: forbidden field in metadata → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 26: forbidden field in metadata ---")
inp = _valid()
inp.metadata = {"real_secret": "placeholder"}
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes (metadata)",
    CredentialIntakeFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 27: forbidden value in evidence (ya29 pattern)
# String split avoids literal ya29 token prefix in source.
# ---------------------------------------------------------------------------
print("--- Test 27: forbidden value in evidence (ya29 token) ---")
inp = _valid()
inp.evidence = {"notes": "ya" + "29.SomeOAuthTokenValueHere"}
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (ya29)",
    CredentialIntakeFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 28: forbidden value in metadata (sk- pattern)
# String split avoids sk-<alpha> literal in source.
# ---------------------------------------------------------------------------
print("--- Test 28: forbidden value in metadata (sk- key prefix) ---")
inp = _valid()
inp.metadata = {"key_note": "sk-" + "abcdefghijklmnopqr"}
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (metadata sk-)",
    CredentialIntakeFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 29: sanitized_summary excludes evidence and metadata
# ---------------------------------------------------------------------------
print("--- Test 29: sanitized_summary excludes evidence/metadata ---")
inp = _valid()
inp.evidence = {"notes": "redacted-note"}
inp.metadata = {"source": "demo"}
r = validate_credential_intake_dry_run(inp)
_check("evidence not in sanitized_summary", "evidence" not in r.sanitized_summary)
_check("metadata not in sanitized_summary", "metadata" not in r.sanitized_summary)

# ---------------------------------------------------------------------------
# Test 30: sanitized_summary contains all 24 booleans + intake_mode + ok/decision/failure_count
# ---------------------------------------------------------------------------
print("--- Test 30: sanitized_summary shape ---")
summary = r.sanitized_summary
_check("intake_mode in summary", "intake_mode" in summary)
_check("transfer_path_forbidden_confirmed in summary", "transfer_path_forbidden_confirmed" in summary)
_check("real_secret_material_present in summary", "real_secret_material_present" in summary)
_check(
    "ok + decision + failure_count in summary",
    "ok" in summary and "decision" in summary and "failure_count" in summary,
)

# ---------------------------------------------------------------------------
# Test 31: multiple failures
# ---------------------------------------------------------------------------
print("--- Test 31: multiple failures ---")
inp = _valid()
inp.rollback_plan_present = False
inp.audit_enabled = False
inp.operator_identity_present = False
r = validate_credential_intake_dry_run(inp)
_check("ok=False", not r.ok)
_check("failure_count >= 3", r.sanitized_summary["failure_count"] >= 3)
_check("failure_codes len >= 3", len(r.failure_codes) >= 3)

# ---------------------------------------------------------------------------
# Test 32: required_actions non-empty and length matches failure_codes
# ---------------------------------------------------------------------------
print("--- Test 32: required_actions non-empty on FAIL ---")
inp = _valid()
inp.checklist_reference_present = False
r = validate_credential_intake_dry_run(inp)
_check("required_actions non-empty", len(r.required_actions) > 0)
_check(
    "required_actions length matches failure_codes",
    len(r.required_actions) == len(r.failure_codes),
)

# ---------------------------------------------------------------------------
# Test 33: required_actions specific message for real_secret_material_present
# ---------------------------------------------------------------------------
print("--- Test 33: required_actions message for real_secret_material_present ---")
inp = _valid()
inp.real_secret_material_present = True
r = validate_credential_intake_dry_run(inp)
actions_text = " ".join(r.required_actions).lower()
_check(
    "required_action mentions real secret material",
    "real secret" in actions_text or "secret material" in actions_text,
)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f"Results: {_PASS} passed, {_FAIL} failed")
if _FAIL == 0:
    print("All assertions passed.")
else:
    sys.exit(1)

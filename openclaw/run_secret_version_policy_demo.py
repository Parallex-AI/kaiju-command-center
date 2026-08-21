"""
V5.20 Phase 7 — Secret Manager version lifecycle policy demo and tests.

30 test scenarios covering all SecretVersionPolicyFailureCode cases, lifecycle mode
validation, grace period checks, hard-stop detection, forbidden field/value detection,
sanitized_summary exclusions, multiple-failure accumulation, and required_actions behavior.

No real credentials. No OAuth. No GCP commands. No network calls. No filesystem I/O.
GOOGLE_ADS_LIVE_ENABLED remains false.
"""

import sys
from pathlib import Path

_DIR = str(Path(__file__).resolve().parent)
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from secret_version_policy import (
    SecretVersionLifecycleMode,
    SecretVersionPolicyDecision,
    SecretVersionPolicyFailureCode,
    SecretVersionPolicyInput,
    validate_secret_version_policy,
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


def _valid() -> SecretVersionPolicyInput:
    """Return a fully-valid SecretVersionPolicyInput with all conditions met."""
    return SecretVersionPolicyInput(
        lifecycle_mode=SecretVersionLifecycleMode.DISABLE_PREVIOUS_WITH_GRACE_PERIOD,
        grace_period_hours=24,
        disable_previous_version_required=True,
        destroy_previous_requires_separate_approval=True,
        rollback_window_present=True,
        audit_requirement_present=True,
        evidence_requirement_present=True,
        operator_confirmation_present=True,
        real_secret_reference_present=False,
        secret_manager_called=False,
        gcp_commands_used=False,
        google_ads_api_called=False,
        oauth_execution_detected=False,
        destructive_action_detected=False,
    )


print("=== V5.20 Phase 7: Secret Manager Version Lifecycle Policy Demo ===")
print()

# ---------------------------------------------------------------------------
# Test 1: valid DISABLE_PREVIOUS_WITH_GRACE_PERIOD → PASS
# ---------------------------------------------------------------------------
print("--- Test 1: valid DISABLE_PREVIOUS_WITH_GRACE_PERIOD policy ---")
r = validate_secret_version_policy(_valid())
_check("ok=True", r.ok)
_check("decision=PASS", r.decision == SecretVersionPolicyDecision.PASS)
_check("failure_codes empty", r.failure_codes == [])
_check("sanitized_summary is dict", isinstance(r.sanitized_summary, dict))

# ---------------------------------------------------------------------------
# Test 2: UNDECIDED → lifecycle_mode_undecided
# ---------------------------------------------------------------------------
print("--- Test 2: lifecycle_mode=UNDECIDED ---")
inp = _valid()
inp.lifecycle_mode = SecretVersionLifecycleMode.UNDECIDED
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "lifecycle_mode_undecided in failure_codes",
    SecretVersionPolicyFailureCode.LIFECYCLE_MODE_UNDECIDED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 3: KEEP_PREVIOUS_ENABLED → keep_previous_enabled_not_allowed
# ---------------------------------------------------------------------------
print("--- Test 3: lifecycle_mode=KEEP_PREVIOUS_ENABLED ---")
inp = _valid()
inp.lifecycle_mode = SecretVersionLifecycleMode.KEEP_PREVIOUS_ENABLED
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "keep_previous_enabled_not_allowed in failure_codes",
    SecretVersionPolicyFailureCode.KEEP_PREVIOUS_ENABLED_NOT_ALLOWED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 4: DESTROY_PREVIOUS_AFTER_GRACE_PERIOD → destroy_requires_separate_approval_missing
# ---------------------------------------------------------------------------
print("--- Test 4: lifecycle_mode=DESTROY_PREVIOUS_AFTER_GRACE_PERIOD ---")
inp = _valid()
inp.lifecycle_mode = SecretVersionLifecycleMode.DESTROY_PREVIOUS_AFTER_GRACE_PERIOD
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "destroy_requires_separate_approval_missing in failure_codes",
    SecretVersionPolicyFailureCode.DESTROY_REQUIRES_SEPARATE_APPROVAL_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 5: invalid lifecycle mode string → lifecycle_mode_invalid
# ---------------------------------------------------------------------------
print("--- Test 5: invalid lifecycle_mode string ---")
inp = _valid()
inp.lifecycle_mode = "UNSUPPORTED_MODE"
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "lifecycle_mode_invalid in failure_codes",
    SecretVersionPolicyFailureCode.LIFECYCLE_MODE_INVALID in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 6: grace_period_hours=None → grace_period_missing
# ---------------------------------------------------------------------------
print("--- Test 6: grace_period_hours=None ---")
inp = _valid()
inp.grace_period_hours = None
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "grace_period_missing in failure_codes",
    SecretVersionPolicyFailureCode.GRACE_PERIOD_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 7: grace_period_hours=0 → grace_period_invalid
# ---------------------------------------------------------------------------
print("--- Test 7: grace_period_hours=0 ---")
inp = _valid()
inp.grace_period_hours = 0
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "grace_period_invalid in failure_codes (zero)",
    SecretVersionPolicyFailureCode.GRACE_PERIOD_INVALID in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 8: grace_period_hours=-1 → grace_period_invalid
# ---------------------------------------------------------------------------
print("--- Test 8: grace_period_hours=-1 ---")
inp = _valid()
inp.grace_period_hours = -1
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "grace_period_invalid in failure_codes (negative)",
    SecretVersionPolicyFailureCode.GRACE_PERIOD_INVALID in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 9: grace_period_hours=169 → grace_period_invalid
# ---------------------------------------------------------------------------
print("--- Test 9: grace_period_hours=169 ---")
inp = _valid()
inp.grace_period_hours = 169
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "grace_period_invalid in failure_codes (exceeds 168)",
    SecretVersionPolicyFailureCode.GRACE_PERIOD_INVALID in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 10: disable_previous_version_required=False → disable_previous_not_confirmed
# ---------------------------------------------------------------------------
print("--- Test 10: disable_previous_version_required=False ---")
inp = _valid()
inp.disable_previous_version_required = False
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "disable_previous_not_confirmed in failure_codes",
    SecretVersionPolicyFailureCode.DISABLE_PREVIOUS_NOT_CONFIRMED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 11: destroy_previous_requires_separate_approval=False → destroy_requires_separate_approval_missing
# ---------------------------------------------------------------------------
print("--- Test 11: destroy_previous_requires_separate_approval=False ---")
inp = _valid()
inp.destroy_previous_requires_separate_approval = False
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "destroy_requires_separate_approval_missing in failure_codes",
    SecretVersionPolicyFailureCode.DESTROY_REQUIRES_SEPARATE_APPROVAL_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 12: rollback_window_present=False → rollback_window_missing
# ---------------------------------------------------------------------------
print("--- Test 12: rollback_window_present=False ---")
inp = _valid()
inp.rollback_window_present = False
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "rollback_window_missing in failure_codes",
    SecretVersionPolicyFailureCode.ROLLBACK_WINDOW_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 13: audit_requirement_present=False → audit_requirement_missing
# ---------------------------------------------------------------------------
print("--- Test 13: audit_requirement_present=False ---")
inp = _valid()
inp.audit_requirement_present = False
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "audit_requirement_missing in failure_codes",
    SecretVersionPolicyFailureCode.AUDIT_REQUIREMENT_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 14: evidence_requirement_present=False → evidence_requirement_missing
# ---------------------------------------------------------------------------
print("--- Test 14: evidence_requirement_present=False ---")
inp = _valid()
inp.evidence_requirement_present = False
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "evidence_requirement_missing in failure_codes",
    SecretVersionPolicyFailureCode.EVIDENCE_REQUIREMENT_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 15: operator_confirmation_present=False → operator_confirmation_missing
# ---------------------------------------------------------------------------
print("--- Test 15: operator_confirmation_present=False ---")
inp = _valid()
inp.operator_confirmation_present = False
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "operator_confirmation_missing in failure_codes",
    SecretVersionPolicyFailureCode.OPERATOR_CONFIRMATION_MISSING in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 16: real_secret_reference_present=True → real_secret_reference_present
# ---------------------------------------------------------------------------
print("--- Test 16: real_secret_reference_present=True ---")
inp = _valid()
inp.real_secret_reference_present = True
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "real_secret_reference_present in failure_codes",
    SecretVersionPolicyFailureCode.REAL_SECRET_REFERENCE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 17: secret_manager_called=True → secret_manager_called
# ---------------------------------------------------------------------------
print("--- Test 17: secret_manager_called=True ---")
inp = _valid()
inp.secret_manager_called = True
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "secret_manager_called in failure_codes",
    SecretVersionPolicyFailureCode.SECRET_MANAGER_CALLED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 18: gcp_commands_used=True → gcp_commands_used
# ---------------------------------------------------------------------------
print("--- Test 18: gcp_commands_used=True ---")
inp = _valid()
inp.gcp_commands_used = True
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "gcp_commands_used in failure_codes",
    SecretVersionPolicyFailureCode.GCP_COMMANDS_USED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 19: google_ads_api_called=True → google_ads_api_called
# ---------------------------------------------------------------------------
print("--- Test 19: google_ads_api_called=True ---")
inp = _valid()
inp.google_ads_api_called = True
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "google_ads_api_called in failure_codes",
    SecretVersionPolicyFailureCode.GOOGLE_ADS_API_CALLED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 20: oauth_execution_detected=True → oauth_execution_detected
# ---------------------------------------------------------------------------
print("--- Test 20: oauth_execution_detected=True ---")
inp = _valid()
inp.oauth_execution_detected = True
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "oauth_execution_detected in failure_codes",
    SecretVersionPolicyFailureCode.OAUTH_EXECUTION_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 21: destructive_action_detected=True → destructive_action_detected
# ---------------------------------------------------------------------------
print("--- Test 21: destructive_action_detected=True ---")
inp = _valid()
inp.destructive_action_detected = True
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "destructive_action_detected in failure_codes",
    SecretVersionPolicyFailureCode.DESTRUCTIVE_ACTION_DETECTED in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 22: forbidden field in evidence → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 22: forbidden field in evidence ---")
inp = _valid()
inp.evidence = {"secret_version": "placeholder-only"}
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes",
    SecretVersionPolicyFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 23: forbidden field in metadata → forbidden_field_present
# ---------------------------------------------------------------------------
print("--- Test 23: forbidden field in metadata ---")
inp = _valid()
inp.metadata = {"api_response_payload": "placeholder"}
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_field_present in failure_codes (metadata)",
    SecretVersionPolicyFailureCode.FORBIDDEN_FIELD_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 24: forbidden value in evidence (Secret Manager version path pattern)
# ---------------------------------------------------------------------------
print("--- Test 24: forbidden value in evidence (version path) ---")
inp = _valid()
inp.evidence = {"policy_notes": "versions/12"}
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (version path)",
    SecretVersionPolicyFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 25: forbidden value in metadata (credential field name as value)
# ---------------------------------------------------------------------------
print("--- Test 25: forbidden value in metadata (bare credential field name) ---")
inp = _valid()
inp.metadata = {"note": "refresh_token"}
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check(
    "forbidden_value_present in failure_codes (metadata)",
    SecretVersionPolicyFailureCode.FORBIDDEN_VALUE_PRESENT in r.failure_codes,
)

# ---------------------------------------------------------------------------
# Test 26: sanitized_summary excludes evidence and metadata
# ---------------------------------------------------------------------------
print("--- Test 26: sanitized_summary excludes evidence/metadata ---")
inp = _valid()
inp.evidence = {"notes": "redacted-policy-note"}
inp.metadata = {"source": "local-policy-check"}
r = validate_secret_version_policy(inp)
_check("evidence not in sanitized_summary", "evidence" not in r.sanitized_summary)
_check("metadata not in sanitized_summary", "metadata" not in r.sanitized_summary)

# ---------------------------------------------------------------------------
# Test 27: sanitized_summary contains all expected fields
# ---------------------------------------------------------------------------
print("--- Test 27: sanitized_summary shape ---")
summary = r.sanitized_summary
_check("lifecycle_mode in summary", "lifecycle_mode" in summary)
_check("grace_period_hours in summary", "grace_period_hours" in summary)
_check("disable_previous_version_required in summary", "disable_previous_version_required" in summary)
_check(
    "destroy_previous_requires_separate_approval in summary",
    "destroy_previous_requires_separate_approval" in summary,
)
_check("rollback_window_present in summary", "rollback_window_present" in summary)
_check("secret_manager_called in summary", "secret_manager_called" in summary)
_check("google_ads_api_called in summary", "google_ads_api_called" in summary)
_check("gcp_commands_used in summary", "gcp_commands_used" in summary)
_check("destructive_action_detected in summary", "destructive_action_detected" in summary)
_check(
    "ok + decision + failure_count in summary",
    "ok" in summary and "decision" in summary and "failure_count" in summary,
)

# ---------------------------------------------------------------------------
# Test 28: multiple failures accumulate in failure_codes
# ---------------------------------------------------------------------------
print("--- Test 28: multiple failures ---")
inp = _valid()
inp.grace_period_hours = None
inp.disable_previous_version_required = False
inp.operator_confirmation_present = False
r = validate_secret_version_policy(inp)
_check("ok=False", not r.ok)
_check("failure_count >= 3", r.sanitized_summary["failure_count"] >= 3)
_check("failure_codes len >= 3", len(r.failure_codes) >= 3)

# ---------------------------------------------------------------------------
# Test 29: required_actions non-empty on failure, length matches failure_codes
# ---------------------------------------------------------------------------
print("--- Test 29: required_actions non-empty on failure ---")
inp = _valid()
inp.rollback_window_present = False
r = validate_secret_version_policy(inp)
_check("required_actions non-empty", len(r.required_actions) > 0)
_check(
    "required_actions length matches failure_codes",
    len(r.required_actions) == len(r.failure_codes),
)

# ---------------------------------------------------------------------------
# Test 30: required_actions empty on PASS
# ---------------------------------------------------------------------------
print("--- Test 30: required_actions empty on PASS ---")
r = validate_secret_version_policy(_valid())
_check("required_actions empty on PASS", r.required_actions == [])
_check("decision=PASS", r.decision == SecretVersionPolicyDecision.PASS)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f"Results: {_PASS} passed, {_FAIL} failed")
if _FAIL == 0:
    print("All assertions passed.")
else:
    sys.exit(1)

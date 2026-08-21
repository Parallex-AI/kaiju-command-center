"""
V5.20 Phase 7 — Secret Manager version lifecycle policy validator.

Pure local logic. No GCP calls. No Google Ads API calls.
No secrets, tokens, credential values, or resource paths.
No os.environ reads. No network calls. No filesystem I/O.
Claude Code does not execute real Secret Manager version operations.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SecretVersionPolicyDecision:
    PASS = "PASS"
    FAIL = "FAIL"


class SecretVersionLifecycleMode:
    DISABLE_PREVIOUS_WITH_GRACE_PERIOD = "DISABLE_PREVIOUS_WITH_GRACE_PERIOD"
    DESTROY_PREVIOUS_AFTER_GRACE_PERIOD = "DESTROY_PREVIOUS_AFTER_GRACE_PERIOD"
    KEEP_PREVIOUS_ENABLED = "KEEP_PREVIOUS_ENABLED"
    UNDECIDED = "UNDECIDED"

    _VALID: frozenset = frozenset({
        "DISABLE_PREVIOUS_WITH_GRACE_PERIOD",
        "DESTROY_PREVIOUS_AFTER_GRACE_PERIOD",
        "KEEP_PREVIOUS_ENABLED",
        "UNDECIDED",
    })


class SecretVersionPolicyFailureCode:
    # Lifecycle mode validation (5)
    LIFECYCLE_MODE_INVALID = "lifecycle_mode_invalid"
    LIFECYCLE_MODE_UNDECIDED = "lifecycle_mode_undecided"
    KEEP_PREVIOUS_ENABLED_NOT_ALLOWED = "keep_previous_enabled_not_allowed"
    GRACE_PERIOD_MISSING = "grace_period_missing"
    GRACE_PERIOD_INVALID = "grace_period_invalid"
    # Policy requirements (6)
    DISABLE_PREVIOUS_NOT_CONFIRMED = "disable_previous_not_confirmed"
    DESTROY_REQUIRES_SEPARATE_APPROVAL_MISSING = "destroy_requires_separate_approval_missing"
    ROLLBACK_WINDOW_MISSING = "rollback_window_missing"
    AUDIT_REQUIREMENT_MISSING = "audit_requirement_missing"
    EVIDENCE_REQUIREMENT_MISSING = "evidence_requirement_missing"
    OPERATOR_CONFIRMATION_MISSING = "operator_confirmation_missing"
    # Detection hard-stops (6)
    REAL_SECRET_REFERENCE_PRESENT = "real_secret_reference_present"
    SECRET_MANAGER_CALLED = "secret_manager_called"
    GCP_COMMANDS_USED = "gcp_commands_used"
    GOOGLE_ADS_API_CALLED = "google_ads_api_called"
    OAUTH_EXECUTION_DETECTED = "oauth_execution_detected"
    DESTRUCTIVE_ACTION_DETECTED = "destructive_action_detected"
    # Forbidden field / value (2)
    FORBIDDEN_FIELD_PRESENT = "forbidden_field_present"
    FORBIDDEN_VALUE_PRESENT = "forbidden_value_present"


# ---------------------------------------------------------------------------
# Forbidden field and value constants
# ---------------------------------------------------------------------------

# All names stored in lowercase; checked with key.lower() for case-insensitive match.
_FORBIDDEN_FIELD_NAMES: frozenset = frozenset({
    "credential_ref",
    "secret_id",
    "secret_version",
    "customer_id",
    "login_customer_id",
    "developer_token",
    "client_secret",
    "refresh_token",
    "access_token",
    "google_ads_client_id",
    "project_id",
    "project_number",
    "service_account_email",
    "credential_file_path",
    "google_application_credentials",
    "real_secret",
    "raw_secret",
    "token_value",
    "oauth_code",
    "api_response_payload",
})

_FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"ya29\.[A-Za-z0-9_\-]{5,}"),                     # OAuth access token prefix
    re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}"),                      # API key prefix
    re.compile(r"\bprojects/[a-zA-Z0-9\-_]+/"),                   # GCP resource paths
    re.compile(r"\bsecrets/[a-zA-Z0-9\-_]+"),                     # Secret Manager secret paths
    re.compile(r"\bversions/[a-zA-Z0-9\-_]+"),                    # Secret Manager version paths
    re.compile(r"[a-zA-Z0-9._%+\-]{2,}@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),  # email-like
    re.compile(r"\.json\b"),                                       # JSON key file references
    re.compile(r"fake-v52[0-9]"),                                  # fake payload sentinels (V5.20+)
    re.compile(r"\bclient_secret\b"),                              # credential field name as value
    re.compile(r"\brefresh_token\b"),                              # credential field name as value
    re.compile(r"\bdeveloper_token\b"),                            # credential field name as value
    re.compile(r"\bcustomer_id\b"),                                # account identifier as value
    re.compile(r"\blogin_customer_id\b"),                          # account identifier as value
]

# ---------------------------------------------------------------------------
# Sanitized summary input fields (excludes evidence and metadata)
# ---------------------------------------------------------------------------

_SANITIZED_SUMMARY_FIELDS = (
    "lifecycle_mode",
    "grace_period_hours",
    "disable_previous_version_required",
    "destroy_previous_requires_separate_approval",
    "rollback_window_present",
    "audit_requirement_present",
    "evidence_requirement_present",
    "operator_confirmation_present",
    "real_secret_reference_present",
    "secret_manager_called",
    "gcp_commands_used",
    "google_ads_api_called",
    "oauth_execution_detected",
    "destructive_action_detected",
)

# ---------------------------------------------------------------------------
# Required actions mapping
# ---------------------------------------------------------------------------

_REQUIRED_ACTIONS: Dict[str, str] = {
    SecretVersionPolicyFailureCode.LIFECYCLE_MODE_INVALID: (
        "Set lifecycle_mode to one of: DISABLE_PREVIOUS_WITH_GRACE_PERIOD, "
        "DESTROY_PREVIOUS_AFTER_GRACE_PERIOD, KEEP_PREVIOUS_ENABLED, UNDECIDED."
    ),
    SecretVersionPolicyFailureCode.LIFECYCLE_MODE_UNDECIDED: (
        "A lifecycle mode decision is required before real credential rotation. "
        "V5.20 authorized mode is DISABLE_PREVIOUS_WITH_GRACE_PERIOD."
    ),
    SecretVersionPolicyFailureCode.KEEP_PREVIOUS_ENABLED_NOT_ALLOWED: (
        "KEEP_PREVIOUS_ENABLED is not acceptable for real credential rotation. "
        "Prior versions must be disabled after rotation. Use DISABLE_PREVIOUS_WITH_GRACE_PERIOD."
    ),
    SecretVersionPolicyFailureCode.GRACE_PERIOD_MISSING: (
        "Provide a grace_period_hours value. Must be a positive integer not exceeding 168 hours (7 days)."
    ),
    SecretVersionPolicyFailureCode.GRACE_PERIOD_INVALID: (
        "grace_period_hours must be an integer > 0 and <= 168. "
        "Choose a window appropriate for the rotation, typically 24–72 hours."
    ),
    SecretVersionPolicyFailureCode.DISABLE_PREVIOUS_NOT_CONFIRMED: (
        "Confirm that disable_previous_version_required=True. "
        "The prior secret version must be disabled after rotation, not kept enabled."
    ),
    SecretVersionPolicyFailureCode.DESTROY_REQUIRES_SEPARATE_APPROVAL_MISSING: (
        "DESTROY_PREVIOUS_AFTER_GRACE_PERIOD requires a separate explicit destructive-action authorization. "
        "No such authorization exists in V5.20. Use DISABLE_PREVIOUS_WITH_GRACE_PERIOD instead, "
        "or confirm destroy_previous_requires_separate_approval=True to acknowledge this constraint."
    ),
    SecretVersionPolicyFailureCode.ROLLBACK_WINDOW_MISSING: (
        "Document a rollback window before rotation. The prior version must remain "
        "recoverable (disabled, not destroyed) within the grace period."
    ),
    SecretVersionPolicyFailureCode.AUDIT_REQUIREMENT_MISSING: (
        "Enable audit logging (OPENCLAW_AUDIT_ENABLED=true) before secret version lifecycle operations."
    ),
    SecretVersionPolicyFailureCode.EVIDENCE_REQUIREMENT_MISSING: (
        "Document evidence requirements for the rotation: operator identity, timestamp, "
        "version before/after, and post-rotation status check."
    ),
    SecretVersionPolicyFailureCode.OPERATOR_CONFIRMATION_MISSING: (
        "Obtain written operator confirmation before any secret version lifecycle operation."
    ),
    SecretVersionPolicyFailureCode.REAL_SECRET_REFERENCE_PRESENT: (
        "Real secret references must not be present in this validator. "
        "Stop immediately. Use structural/placeholder inputs only."
    ),
    SecretVersionPolicyFailureCode.SECRET_MANAGER_CALLED: (
        "Secret Manager must not be called during policy validation. "
        "This validator is pure local logic only."
    ),
    SecretVersionPolicyFailureCode.GCP_COMMANDS_USED: (
        "GCP commands must not be run by Claude Code. "
        "All GCP operations are operator-only and out-of-band."
    ),
    SecretVersionPolicyFailureCode.GOOGLE_ADS_API_CALLED: (
        "Google Ads API must not be called during policy validation."
    ),
    SecretVersionPolicyFailureCode.OAUTH_EXECUTION_DETECTED: (
        "OAuth execution must not occur during policy validation. "
        "Stop and revert any OAuth flow that has been initiated."
    ),
    SecretVersionPolicyFailureCode.DESTRUCTIVE_ACTION_DETECTED: (
        "Destructive actions (secret version destroy, delete, or wipe) must not occur "
        "during policy validation. No destructive operations are authorized in V5.20."
    ),
    SecretVersionPolicyFailureCode.FORBIDDEN_FIELD_PRESENT: (
        "Remove all forbidden field names from evidence and metadata."
    ),
    SecretVersionPolicyFailureCode.FORBIDDEN_VALUE_PRESENT: (
        "Remove all forbidden value patterns from evidence and metadata."
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SecretVersionPolicyInput:
    lifecycle_mode: str
    grace_period_hours: Optional[int]
    # Policy requirement confirmations (6)
    disable_previous_version_required: bool
    destroy_previous_requires_separate_approval: bool
    rollback_window_present: bool
    audit_requirement_present: bool
    evidence_requirement_present: bool
    operator_confirmation_present: bool
    # Detection hard-stops (6; must be False to PASS)
    real_secret_reference_present: bool
    secret_manager_called: bool
    gcp_commands_used: bool
    google_ads_api_called: bool
    oauth_execution_detected: bool
    destructive_action_detected: bool
    # Evidence and metadata (excluded from sanitized_summary)
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecretVersionPolicyResult:
    ok: bool
    decision: str
    failure_codes: List[str]
    required_actions: List[str]
    sanitized_summary: Dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_mapping_for_forbidden(
    d: Mapping[str, Any],
    field_failure: str,
    value_failure: str,
) -> List[str]:
    errors: List[str] = []
    seen_field = False
    seen_value = False
    for key, value in d.items():
        if not seen_field and key.lower() in _FORBIDDEN_FIELD_NAMES:
            errors.append(field_failure)
            seen_field = True
        if isinstance(value, str) and not seen_value:
            for pattern in _FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(value):
                    errors.append(value_failure)
                    seen_value = True
                    break
    return errors


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def validate_secret_version_policy(
    inp: SecretVersionPolicyInput,
) -> SecretVersionPolicyResult:
    """
    Validate the Secret Manager version lifecycle policy decision against all V5.20 conditions.

    Returns ok=True only when:
    - lifecycle_mode is DISABLE_PREVIOUS_WITH_GRACE_PERIOD
    - grace_period_hours is a valid integer (1–168)
    - all six policy requirement confirmations are True
    - all six detection hard-stop flags are False
    - evidence and metadata contain no forbidden fields or values

    Never reads real credentials, calls GCP, calls Secret Manager, calls Google Ads API,
    writes to the filesystem, or makes network calls.
    Claude Code does not execute real Secret Manager version operations.
    """
    failure_codes: List[str] = []

    # Hard stops — detection booleans surface immediately
    if inp.real_secret_reference_present:
        failure_codes.append(SecretVersionPolicyFailureCode.REAL_SECRET_REFERENCE_PRESENT)
    if inp.secret_manager_called:
        failure_codes.append(SecretVersionPolicyFailureCode.SECRET_MANAGER_CALLED)
    if inp.gcp_commands_used:
        failure_codes.append(SecretVersionPolicyFailureCode.GCP_COMMANDS_USED)
    if inp.google_ads_api_called:
        failure_codes.append(SecretVersionPolicyFailureCode.GOOGLE_ADS_API_CALLED)
    if inp.oauth_execution_detected:
        failure_codes.append(SecretVersionPolicyFailureCode.OAUTH_EXECUTION_DETECTED)
    if inp.destructive_action_detected:
        failure_codes.append(SecretVersionPolicyFailureCode.DESTRUCTIVE_ACTION_DETECTED)

    # Lifecycle mode validation
    if inp.lifecycle_mode not in SecretVersionLifecycleMode._VALID:
        failure_codes.append(SecretVersionPolicyFailureCode.LIFECYCLE_MODE_INVALID)
    elif inp.lifecycle_mode == SecretVersionLifecycleMode.UNDECIDED:
        failure_codes.append(SecretVersionPolicyFailureCode.LIFECYCLE_MODE_UNDECIDED)
    elif inp.lifecycle_mode == SecretVersionLifecycleMode.KEEP_PREVIOUS_ENABLED:
        failure_codes.append(SecretVersionPolicyFailureCode.KEEP_PREVIOUS_ENABLED_NOT_ALLOWED)
    elif inp.lifecycle_mode == SecretVersionLifecycleMode.DESTROY_PREVIOUS_AFTER_GRACE_PERIOD:
        # Destroy requires separate explicit authorization — always fails in Phase 7
        failure_codes.append(
            SecretVersionPolicyFailureCode.DESTROY_REQUIRES_SEPARATE_APPROVAL_MISSING
        )
    else:
        # DISABLE_PREVIOUS_WITH_GRACE_PERIOD — current authorized V5.20 mode
        # Grace period validation
        if inp.grace_period_hours is None:
            failure_codes.append(SecretVersionPolicyFailureCode.GRACE_PERIOD_MISSING)
        elif not (isinstance(inp.grace_period_hours, int) and 0 < inp.grace_period_hours <= 168):
            failure_codes.append(SecretVersionPolicyFailureCode.GRACE_PERIOD_INVALID)

        # Policy requirement confirmations
        if not inp.disable_previous_version_required:
            failure_codes.append(SecretVersionPolicyFailureCode.DISABLE_PREVIOUS_NOT_CONFIRMED)
        if not inp.destroy_previous_requires_separate_approval:
            failure_codes.append(
                SecretVersionPolicyFailureCode.DESTROY_REQUIRES_SEPARATE_APPROVAL_MISSING
            )
        if not inp.rollback_window_present:
            failure_codes.append(SecretVersionPolicyFailureCode.ROLLBACK_WINDOW_MISSING)
        if not inp.audit_requirement_present:
            failure_codes.append(SecretVersionPolicyFailureCode.AUDIT_REQUIREMENT_MISSING)
        if not inp.evidence_requirement_present:
            failure_codes.append(SecretVersionPolicyFailureCode.EVIDENCE_REQUIREMENT_MISSING)
        if not inp.operator_confirmation_present:
            failure_codes.append(SecretVersionPolicyFailureCode.OPERATOR_CONFIRMATION_MISSING)

    # Evidence and metadata forbidden field/value checks
    failure_codes.extend(_check_mapping_for_forbidden(
        inp.evidence,
        SecretVersionPolicyFailureCode.FORBIDDEN_FIELD_PRESENT,
        SecretVersionPolicyFailureCode.FORBIDDEN_VALUE_PRESENT,
    ))
    failure_codes.extend(_check_mapping_for_forbidden(
        inp.metadata,
        SecretVersionPolicyFailureCode.FORBIDDEN_FIELD_PRESENT,
        SecretVersionPolicyFailureCode.FORBIDDEN_VALUE_PRESENT,
    ))

    ok = len(failure_codes) == 0
    decision = SecretVersionPolicyDecision.PASS if ok else SecretVersionPolicyDecision.FAIL

    required_actions = [
        _REQUIRED_ACTIONS.get(code, f"Resolve: {code}")
        for code in failure_codes
    ]

    sanitized_summary: Dict[str, Any] = {
        f: getattr(inp, f)
        for f in _SANITIZED_SUMMARY_FIELDS
    }
    sanitized_summary["decision"] = decision
    sanitized_summary["ok"] = ok
    sanitized_summary["failure_count"] = len(failure_codes)

    return SecretVersionPolicyResult(
        ok=ok,
        decision=decision,
        failure_codes=failure_codes,
        required_actions=required_actions,
        sanitized_summary=sanitized_summary,
    )

"""
V5.20 Phase 3 — Onboarding approval ceremony model and checklist validator.

Pure local logic. No GCP calls. No Google Ads API calls.
No secrets, tokens, credential values, or resource paths.
No os.environ reads. No network calls. No filesystem I/O.
Claude Code does not self-approve and does not execute real onboarding.
"""

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OnboardingOperation:
    CREDENTIAL_ONBOARDING = "credential_onboarding"
    LIVE_VALIDATION = "live_validation"
    ROTATION = "rotation"
    REVOKE = "revoke"

    _ALL: frozenset = frozenset({
        "credential_onboarding",
        "live_validation",
        "rotation",
        "revoke",
    })


class ChecklistDecision:
    PASS = "PASS"
    FAIL = "FAIL"


class ChecklistFailureCode:
    OPERATOR_LABEL_MISSING = "operator_label_missing"
    TENANT_MISSING = "tenant_missing"
    CLIENT_MISSING = "client_missing"
    INTEGRATION_INVALID = "integration_invalid"
    OPERATION_INVALID = "operation_invalid"
    APPROVAL_SCOPE_MISSING = "approval_scope_missing"
    RISK_ACKNOWLEDGEMENT_MISSING = "risk_acknowledgement_missing"
    ROLLBACK_PLAN_MISSING = "rollback_plan_missing"
    EMERGENCY_REVOKE_PLAN_MISSING = "emergency_revoke_plan_missing"
    EVIDENCE_LOCATION_MISSING = "evidence_location_missing"
    APPROVED_AT_MISSING = "approved_at_missing"
    EXPIRES_AT_MISSING = "expires_at_missing"
    APPROVAL_NOT_APPROVED = "approval_not_approved"
    APPROVAL_EXPIRED = "approval_expired"
    AUDIT_NOT_ENABLED = "audit_not_enabled"
    SMOKE_TESTS_MISSING = "smoke_tests_missing"
    PREFLIGHT_MISSING = "preflight_missing"
    LIVE_GATE_MISSING = "live_gate_missing"
    REVOKE_PATH_MISSING = "revoke_path_missing"
    CREDENTIAL_INTAKE_BOUNDARY_MISSING = "credential_intake_boundary_missing"
    OAUTH_BOUNDARY_NOT_DESIGN_ONLY = "oauth_boundary_not_design_only"
    LIVE_FLAG_NOT_FALSE = "live_flag_not_false"
    REAL_CREDENTIALS_PRESENT = "real_credentials_present"
    GOOGLE_ADS_API_CALLED = "google_ads_api_called"
    GCP_COMMANDS_USED = "gcp_commands_used"
    FORBIDDEN_FIELD_PRESENT = "forbidden_field_present"
    FORBIDDEN_VALUE_PRESENT = "forbidden_value_present"


# ---------------------------------------------------------------------------
# Forbidden field and value constants
# ---------------------------------------------------------------------------

_FORBIDDEN_FIELD_NAMES: frozenset = frozenset({
    "credential_ref",
    "secret_id",
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
    "GOOGLE_APPLICATION_CREDENTIALS",
})

# Patterns match at runtime; source strings use regex escapes so literal
# forbidden prefixes (e.g. ya29 followed by a literal dot) never appear here.
_FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"ya29\.[A-Za-z0-9_\-]{5,}"),           # OAuth access tokens  # ya29 forbidden
    re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}"),            # API key prefix
    re.compile(r"\bprojects/[a-zA-Z0-9\-_]+/"),         # GCP resource paths
    re.compile(r"\bsecrets/[a-zA-Z0-9\-_]+"),           # Secret Manager paths
    re.compile(r"[a-zA-Z0-9._%+\-]{2,}@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),  # email-like
    re.compile(r"\.json\b"),                             # JSON key file references
    re.compile(r"fake-v52[0-9]"),                        # fake payload sentinels (V5.20+)
]

_REQUIRED_APPROVAL_STATUS = "APPROVED"
_REQUIRED_INTEGRATION_TYPE = "google_ads"

# ---------------------------------------------------------------------------
# Sanitized summary — included and excluded fields
# ---------------------------------------------------------------------------

_SANITIZED_SUMMARY_FIELDS = (
    "integration_type",
    "intended_operation",
    "approval_status",
    "audit_enabled",
    "smoke_tests_passed",
    "preflight_available",
    "live_gate_available",
    "revoke_path_available",
    "credential_intake_boundary_confirmed",
    "oauth_boundary_design_only",
    "live_flag_false_confirmed",
    "real_credentials_present",
    "google_ads_api_called",
    "gcp_commands_used",
)

# Fields that must never appear in sanitized_summary
_SANITIZED_SUMMARY_NEVER = frozenset({
    "tenant_id",
    "client_id",
    "operator_label",
    "evidence_location",
    "approved_at",
    "expires_at",
    "evidence",
    "metadata",
})

# ---------------------------------------------------------------------------
# Required actions mapping
# ---------------------------------------------------------------------------

_REQUIRED_ACTIONS: Dict[str, str] = {
    ChecklistFailureCode.OPERATOR_LABEL_MISSING: (
        "Provide a named operator label (not a team name)."
    ),
    ChecklistFailureCode.TENANT_MISSING: (
        "Specify the target tenant_id."
    ),
    ChecklistFailureCode.CLIENT_MISSING: (
        "Specify the target client_id."
    ),
    ChecklistFailureCode.INTEGRATION_INVALID: (
        f"Set integration_type to '{_REQUIRED_INTEGRATION_TYPE}'."
    ),
    ChecklistFailureCode.OPERATION_INVALID: (
        "Set intended_operation to one of: credential_onboarding, live_validation, rotation, revoke."
    ),
    ChecklistFailureCode.APPROVAL_SCOPE_MISSING: (
        "Document the approval scope."
    ),
    ChecklistFailureCode.RISK_ACKNOWLEDGEMENT_MISSING: (
        "Record a risk acknowledgement summary (no credential values)."
    ),
    ChecklistFailureCode.ROLLBACK_PLAN_MISSING: (
        "Document a rollback plan with named operator and steps."
    ),
    ChecklistFailureCode.EMERGENCY_REVOKE_PLAN_MISSING: (
        "Document an emergency revoke plan."
    ),
    ChecklistFailureCode.EVIDENCE_LOCATION_MISSING: (
        "Provide an evidence location (redacted local path or ticket ID)."
    ),
    ChecklistFailureCode.APPROVED_AT_MISSING: (
        "Set approved_at to the ISO 8601 UTC approval timestamp."
    ),
    ChecklistFailureCode.EXPIRES_AT_MISSING: (
        "Set expires_at to the ISO 8601 UTC expiry timestamp."
    ),
    ChecklistFailureCode.APPROVAL_NOT_APPROVED: (
        "Approval status must be APPROVED before proceeding."
    ),
    ChecklistFailureCode.APPROVAL_EXPIRED: (
        "Approval has expired. Obtain a new approval record."
    ),
    ChecklistFailureCode.AUDIT_NOT_ENABLED: (
        "Enable audit logging (OPENCLAW_AUDIT_ENABLED=true) before proceeding."
    ),
    ChecklistFailureCode.SMOKE_TESTS_MISSING: (
        "All smoke tests must pass: smoke_test_v5_credentials.sh 26/26 "
        "and smoke_test_v5_12_gcp_secret_manager.sh 8/8."
    ),
    ChecklistFailureCode.PREFLIGHT_MISSING: (
        "Verify check_live_operation_preflight() is available and functional."
    ),
    ChecklistFailureCode.LIVE_GATE_MISSING: (
        "Verify check_live_gate() is available and functional."
    ),
    ChecklistFailureCode.REVOKE_PATH_MISSING: (
        "Confirm the revoke/delete path is available and tested with a fake credential."
    ),
    ChecklistFailureCode.CREDENTIAL_INTAKE_BOUNDARY_MISSING: (
        "Confirm the credential intake boundary (Section C) is understood and accepted."
    ),
    ChecklistFailureCode.OAUTH_BOUNDARY_NOT_DESIGN_ONLY: (
        "OAuth onboarding boundary must be design-only at this stage. No OAuth execution."
    ),
    ChecklistFailureCode.LIVE_FLAG_NOT_FALSE: (
        "GOOGLE_ADS_LIVE_ENABLED must be false. "
        "Do not set it to true without completing all checklist sections."
    ),
    ChecklistFailureCode.REAL_CREDENTIALS_PRESENT: (
        "Real credentials must not be present. Remove any real credential values immediately."
    ),
    ChecklistFailureCode.GOOGLE_ADS_API_CALLED: (
        "Google Ads API must not be called at this stage. "
        "Stop and revoke any live calls per Section G of the checklist."
    ),
    ChecklistFailureCode.GCP_COMMANDS_USED: (
        "GCP commands must not be run by Claude Code. All GCP operations are operator-only."
    ),
    ChecklistFailureCode.FORBIDDEN_FIELD_PRESENT: (
        "Remove all forbidden field names from evidence and metadata."
    ),
    ChecklistFailureCode.FORBIDDEN_VALUE_PRESENT: (
        "Remove all forbidden value patterns from evidence and metadata."
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class OnboardingCeremonyInput:
    operator_label: str
    tenant_id: str
    client_id: str
    integration_type: str
    intended_operation: str
    approval_scope: str
    risk_acknowledgement: str
    rollback_plan_present: bool
    emergency_revoke_plan_present: bool
    evidence_location: str
    approved_at: Optional[str]
    expires_at: Optional[str]
    approval_status: str
    audit_enabled: bool
    smoke_tests_passed: bool
    preflight_available: bool
    live_gate_available: bool
    revoke_path_available: bool
    credential_intake_boundary_confirmed: bool
    oauth_boundary_design_only: bool
    live_flag_false_confirmed: bool
    real_credentials_present: bool
    google_ads_api_called: bool
    gcp_commands_used: bool
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OnboardingCeremonyResult:
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


def _is_expired(expires_at: str, now: Optional[str]) -> bool:
    _now = now or datetime.now(timezone.utc).isoformat()
    try:
        exp = expires_at.rstrip("Z")
        cur = _now.rstrip("Z")
        return cur >= exp
    except Exception:
        return True

# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def validate_onboarding_ceremony(
    inp: OnboardingCeremonyInput,
    now: Optional[str] = None,
) -> OnboardingCeremonyResult:
    """
    Validate the onboarding ceremony input against all V5.20 checklist conditions.

    Returns ok=True only when every condition passes.
    Never reads credentials, calls GCP, or calls Google Ads API.
    Claude Code does not self-approve.
    """
    failure_codes: List[str] = []

    # Identity fields
    if not inp.operator_label.strip():
        failure_codes.append(ChecklistFailureCode.OPERATOR_LABEL_MISSING)
    if not inp.tenant_id.strip():
        failure_codes.append(ChecklistFailureCode.TENANT_MISSING)
    if not inp.client_id.strip():
        failure_codes.append(ChecklistFailureCode.CLIENT_MISSING)

    # Integration and operation
    if inp.integration_type != _REQUIRED_INTEGRATION_TYPE:
        failure_codes.append(ChecklistFailureCode.INTEGRATION_INVALID)
    if inp.intended_operation not in OnboardingOperation._ALL:
        failure_codes.append(ChecklistFailureCode.OPERATION_INVALID)

    # Approval ceremony fields
    if not inp.approval_scope.strip():
        failure_codes.append(ChecklistFailureCode.APPROVAL_SCOPE_MISSING)
    if not inp.risk_acknowledgement.strip():
        failure_codes.append(ChecklistFailureCode.RISK_ACKNOWLEDGEMENT_MISSING)
    if not inp.rollback_plan_present:
        failure_codes.append(ChecklistFailureCode.ROLLBACK_PLAN_MISSING)
    if not inp.emergency_revoke_plan_present:
        failure_codes.append(ChecklistFailureCode.EMERGENCY_REVOKE_PLAN_MISSING)
    if not inp.evidence_location.strip():
        failure_codes.append(ChecklistFailureCode.EVIDENCE_LOCATION_MISSING)

    # Timestamps
    if not inp.approved_at:
        failure_codes.append(ChecklistFailureCode.APPROVED_AT_MISSING)
    if not inp.expires_at:
        failure_codes.append(ChecklistFailureCode.EXPIRES_AT_MISSING)

    # Approval status and expiry
    if inp.approval_status != _REQUIRED_APPROVAL_STATUS:
        failure_codes.append(ChecklistFailureCode.APPROVAL_NOT_APPROVED)
    elif inp.expires_at and _is_expired(inp.expires_at, now):
        failure_codes.append(ChecklistFailureCode.APPROVAL_EXPIRED)

    # Infrastructure readiness
    if not inp.audit_enabled:
        failure_codes.append(ChecklistFailureCode.AUDIT_NOT_ENABLED)
    if not inp.smoke_tests_passed:
        failure_codes.append(ChecklistFailureCode.SMOKE_TESTS_MISSING)
    if not inp.preflight_available:
        failure_codes.append(ChecklistFailureCode.PREFLIGHT_MISSING)
    if not inp.live_gate_available:
        failure_codes.append(ChecklistFailureCode.LIVE_GATE_MISSING)
    if not inp.revoke_path_available:
        failure_codes.append(ChecklistFailureCode.REVOKE_PATH_MISSING)

    # Boundary confirmations
    if not inp.credential_intake_boundary_confirmed:
        failure_codes.append(ChecklistFailureCode.CREDENTIAL_INTAKE_BOUNDARY_MISSING)
    if not inp.oauth_boundary_design_only:
        failure_codes.append(ChecklistFailureCode.OAUTH_BOUNDARY_NOT_DESIGN_ONLY)
    if not inp.live_flag_false_confirmed:
        failure_codes.append(ChecklistFailureCode.LIVE_FLAG_NOT_FALSE)

    # Hard safety stops
    if inp.real_credentials_present:
        failure_codes.append(ChecklistFailureCode.REAL_CREDENTIALS_PRESENT)
    if inp.google_ads_api_called:
        failure_codes.append(ChecklistFailureCode.GOOGLE_ADS_API_CALLED)
    if inp.gcp_commands_used:
        failure_codes.append(ChecklistFailureCode.GCP_COMMANDS_USED)

    # Evidence and metadata forbidden field/value checks
    failure_codes.extend(_check_mapping_for_forbidden(
        inp.evidence,
        ChecklistFailureCode.FORBIDDEN_FIELD_PRESENT,
        ChecklistFailureCode.FORBIDDEN_VALUE_PRESENT,
    ))
    failure_codes.extend(_check_mapping_for_forbidden(
        inp.metadata,
        ChecklistFailureCode.FORBIDDEN_FIELD_PRESENT,
        ChecklistFailureCode.FORBIDDEN_VALUE_PRESENT,
    ))

    ok = len(failure_codes) == 0
    decision = ChecklistDecision.PASS if ok else ChecklistDecision.FAIL

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

    return OnboardingCeremonyResult(
        ok=ok,
        decision=decision,
        failure_codes=failure_codes,
        required_actions=required_actions,
        sanitized_summary=sanitized_summary,
    )

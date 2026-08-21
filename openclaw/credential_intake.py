"""
V5.20 Phase 4 — Credential intake dry-run boundary enforcement.

Pure local logic. No GCP calls. No Google Ads API calls.
No secrets, tokens, credential values, or resource paths.
No os.environ reads. No network calls. No filesystem I/O.
Claude Code does not execute real credential intake.
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

class CredentialIntakeMode:
    DRY_RUN_ONLY = "dry_run_only"
    REAL_INTAKE_PLANNED = "real_intake_planned"

    _VALID: frozenset = frozenset({"dry_run_only", "real_intake_planned"})


class CredentialIntakeDecision:
    PASS = "PASS"
    FAIL = "FAIL"


class CredentialIntakeFailureCode:
    # Mode
    MODE_INVALID = "mode_invalid"
    DRY_RUN_REQUIRED = "dry_run_required"
    # Boundary (7)
    TRANSFER_PATH_FORBIDDEN = "transfer_path_forbidden"
    CREDENTIAL_VALUES_IN_INPUT = "credential_values_in_input"
    LIVE_FLAG_NOT_FALSE = "live_flag_not_false"
    GCP_WRITE_NOT_OPERATOR_ONLY = "gcp_write_not_operator_only"
    SCREEN_RECORDING_PROHIBITED = "screen_recording_prohibited"
    REPO_COMMIT_PROHIBITED = "repo_commit_prohibited"
    IMMEDIATE_REDACTION_REQUIRED = "immediate_redaction_required"
    # Plan (4)
    ROLLBACK_PLAN_MISSING = "rollback_plan_missing"
    EMERGENCY_REVOKE_PLAN_MISSING = "emergency_revoke_plan_missing"
    OPERATOR_CONFIRMATION_MISSING = "operator_confirmation_missing"
    AUDIT_NOT_ENABLED = "audit_not_enabled"
    # Reference / confirmation (4)
    CHECKLIST_REFERENCE_MISSING = "checklist_reference_missing"
    INTAKE_BOUNDARY_DOC_MISSING = "intake_boundary_doc_missing"
    OPERATOR_IDENTITY_MISSING = "operator_identity_missing"
    APPROVAL_CEREMONY_REFERENCE_MISSING = "approval_ceremony_reference_missing"
    # Detection — hard stops (6)
    REAL_SECRET_MATERIAL_PRESENT = "real_secret_material_present"
    OAUTH_EXECUTION_DETECTED = "oauth_execution_detected"
    GOOGLE_ADS_API_CALL_DETECTED = "google_ads_api_call_detected"
    GCP_COMMAND_DETECTED = "gcp_command_detected"
    FILESYSTEM_WRITE_DETECTED = "filesystem_write_detected"
    NETWORK_CALL_DETECTED = "network_call_detected"
    # Forbidden field / value
    FORBIDDEN_FIELD_PRESENT = "forbidden_field_present"
    FORBIDDEN_VALUE_PRESENT = "forbidden_value_present"


# ---------------------------------------------------------------------------
# Forbidden field and value constants
# ---------------------------------------------------------------------------

# All names stored in lowercase; checked with key.lower() so case-insensitive.
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
    "google_application_credentials",
    "real_secret",
    "raw_secret",
    "token_value",
    "oauth_code",
})

# Patterns match at runtime; source strings use regex escapes so literal
# forbidden prefixes never appear here.
_FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"ya29\.[A-Za-z0-9_\-]{5,}"),           # ya29 forbidden
    re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}"),            # API key prefix
    re.compile(r"\bprojects/[a-zA-Z0-9\-_]+/"),         # GCP resource paths
    re.compile(r"\bsecrets/[a-zA-Z0-9\-_]+"),           # Secret Manager paths
    re.compile(r"[a-zA-Z0-9._%+\-]{2,}@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),  # email-like
    re.compile(r"\.json\b"),                             # JSON key file references
    re.compile(r"fake-v52[0-9]"),                        # fake payload sentinels (V5.20+)
    re.compile(r"\bclient_secret\b"),                    # bare credential field name as value
    re.compile(r"\brefresh_token\b"),                    # bare credential field name as value
    re.compile(r"\bdeveloper_token\b"),                  # bare credential field name as value
]

# ---------------------------------------------------------------------------
# Sanitized summary fields (24 booleans + intake_mode; excludes evidence/metadata)
# ---------------------------------------------------------------------------

_SANITIZED_SUMMARY_FIELDS = (
    "intake_mode",
    "transfer_path_forbidden_confirmed",
    "credential_values_absent",
    "live_flag_false_confirmed",
    "gcp_write_operator_only_confirmed",
    "screen_recording_prohibited_confirmed",
    "repo_commit_prohibited_confirmed",
    "immediate_redaction_confirmed",
    "rollback_plan_present",
    "emergency_revoke_plan_present",
    "operator_confirmation_present",
    "audit_enabled",
    "checklist_reference_present",
    "intake_boundary_doc_confirmed",
    "operator_identity_present",
    "approval_ceremony_reference_present",
    "smoke_tests_passed",
    "intake_plan_document_present",
    "dry_run_only_confirmed",
    "real_secret_material_present",
    "oauth_execution_detected",
    "google_ads_api_call_detected",
    "gcp_command_detected",
    "filesystem_write_detected",
    "network_call_detected",
)

# ---------------------------------------------------------------------------
# Required actions mapping
# ---------------------------------------------------------------------------

_REQUIRED_ACTIONS: Dict[str, str] = {
    CredentialIntakeFailureCode.MODE_INVALID: (
        "Set intake_mode to 'dry_run_only'. Real intake is not authorized in V5.20."
    ),
    CredentialIntakeFailureCode.DRY_RUN_REQUIRED: (
        "This validator enforces dry-run mode only. "
        "Real credential intake requires a separate authorized milestone."
    ),
    CredentialIntakeFailureCode.TRANSFER_PATH_FORBIDDEN: (
        "Confirm that no credential values will travel through Claude Code, "
        "chat interfaces, or any log sink. Operator writes directly to GCP Secret Manager."
    ),
    CredentialIntakeFailureCode.CREDENTIAL_VALUES_IN_INPUT: (
        "Remove all credential values from input. "
        "This dry-run validator must never receive real token values."
    ),
    CredentialIntakeFailureCode.LIVE_FLAG_NOT_FALSE: (
        "GOOGLE_ADS_LIVE_ENABLED must be false throughout credential intake. "
        "Do not set it to true without completing all checklist sections."
    ),
    CredentialIntakeFailureCode.GCP_WRITE_NOT_OPERATOR_ONLY: (
        "Confirm that GCP Secret Manager writes are performed by the operator "
        "on a controlled terminal only. Claude Code does not participate in the write."
    ),
    CredentialIntakeFailureCode.SCREEN_RECORDING_PROHIBITED: (
        "Confirm that screen recording is disabled or covered during credential entry. "
        "No credential value may be captured by any recording."
    ),
    CredentialIntakeFailureCode.REPO_COMMIT_PROHIBITED: (
        "Confirm that no credential value will be committed to the repository "
        "in any form — no .env, no JSON key file, no Python literal, no YAML."
    ),
    CredentialIntakeFailureCode.IMMEDIATE_REDACTION_REQUIRED: (
        "Confirm that an immediate redaction check will be run after credential write "
        "to verify no value appears in any log, audit file, or git-tracked file."
    ),
    CredentialIntakeFailureCode.ROLLBACK_PLAN_MISSING: (
        "Document a rollback plan with named operator, exact steps, "
        "and estimated time to full credential revocation."
    ),
    CredentialIntakeFailureCode.EMERGENCY_REVOKE_PLAN_MISSING: (
        "Document an emergency revoke plan for anomalous behavior during intake."
    ),
    CredentialIntakeFailureCode.OPERATOR_CONFIRMATION_MISSING: (
        "Obtain written operator confirmation before proceeding with credential intake."
    ),
    CredentialIntakeFailureCode.AUDIT_NOT_ENABLED: (
        "Enable audit logging (OPENCLAW_AUDIT_ENABLED=true) before credential intake."
    ),
    CredentialIntakeFailureCode.CHECKLIST_REFERENCE_MISSING: (
        "Reference the completed GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST before "
        "proceeding. All sections must be verified by a named operator."
    ),
    CredentialIntakeFailureCode.INTAKE_BOUNDARY_DOC_MISSING: (
        "Confirm the credential intake boundary (Section C of the checklist) "
        "has been reviewed and accepted by the authorizing operator."
    ),
    CredentialIntakeFailureCode.OPERATOR_IDENTITY_MISSING: (
        "Record the full name of the authorizing operator. "
        "Team names are not acceptable."
    ),
    CredentialIntakeFailureCode.APPROVAL_CEREMONY_REFERENCE_MISSING: (
        "Reference the completed onboarding ceremony approval record "
        "before proceeding with credential intake."
    ),
    CredentialIntakeFailureCode.REAL_SECRET_MATERIAL_PRESENT: (
        "Real secret material must not be present. "
        "Stop immediately and remove any real credential values."
    ),
    CredentialIntakeFailureCode.OAUTH_EXECUTION_DETECTED: (
        "OAuth execution must not occur during dry-run validation. "
        "Stop and revert any OAuth flow that has been initiated."
    ),
    CredentialIntakeFailureCode.GOOGLE_ADS_API_CALL_DETECTED: (
        "Google Ads API must not be called during credential intake validation. "
        "Stop and revoke any live calls per the rollback runbook."
    ),
    CredentialIntakeFailureCode.GCP_COMMAND_DETECTED: (
        "GCP commands must not be run by Claude Code. "
        "All GCP operations are operator-only."
    ),
    CredentialIntakeFailureCode.FILESYSTEM_WRITE_DETECTED: (
        "Filesystem writes are prohibited during dry-run validation. "
        "No credential value may be written to any local file by this validator."
    ),
    CredentialIntakeFailureCode.NETWORK_CALL_DETECTED: (
        "Network calls are prohibited during credential intake validation. "
        "This validator is pure local logic only."
    ),
    CredentialIntakeFailureCode.FORBIDDEN_FIELD_PRESENT: (
        "Remove all forbidden field names from evidence and metadata."
    ),
    CredentialIntakeFailureCode.FORBIDDEN_VALUE_PRESENT: (
        "Remove all forbidden value patterns from evidence and metadata."
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CredentialIntakeDryRunInput:
    intake_mode: str
    # Boundary confirmations (7)
    transfer_path_forbidden_confirmed: bool
    credential_values_absent: bool
    live_flag_false_confirmed: bool
    gcp_write_operator_only_confirmed: bool
    screen_recording_prohibited_confirmed: bool
    repo_commit_prohibited_confirmed: bool
    immediate_redaction_confirmed: bool
    # Plan fields (4)
    rollback_plan_present: bool
    emergency_revoke_plan_present: bool
    operator_confirmation_present: bool
    audit_enabled: bool
    # Reference / confirmation fields (4)
    checklist_reference_present: bool
    intake_boundary_doc_confirmed: bool
    operator_identity_present: bool
    approval_ceremony_reference_present: bool
    # Informational booleans (3) — included in sanitized_summary; no failure code
    smoke_tests_passed: bool
    intake_plan_document_present: bool
    dry_run_only_confirmed: bool
    # Detection hard-stops (6)
    real_secret_material_present: bool
    oauth_execution_detected: bool
    google_ads_api_call_detected: bool
    gcp_command_detected: bool
    filesystem_write_detected: bool
    network_call_detected: bool
    # Evidence and metadata (excluded from sanitized_summary)
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CredentialIntakeDryRunResult:
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

def validate_credential_intake_dry_run(
    inp: CredentialIntakeDryRunInput,
) -> CredentialIntakeDryRunResult:
    """
    Validate the credential intake dry-run input against all V5.20 boundary conditions.

    Returns ok=True only when every condition passes.
    Never reads real credentials, calls GCP, calls Google Ads API,
    writes to the filesystem, or makes network calls.
    Claude Code does not execute real credential intake.
    """
    failure_codes: List[str] = []

    # Mode validation
    if inp.intake_mode not in CredentialIntakeMode._VALID:
        failure_codes.append(CredentialIntakeFailureCode.MODE_INVALID)
    elif inp.intake_mode == CredentialIntakeMode.REAL_INTAKE_PLANNED:
        failure_codes.append(CredentialIntakeFailureCode.DRY_RUN_REQUIRED)

    # Hard stops — detection booleans surface immediately
    if inp.real_secret_material_present:
        failure_codes.append(CredentialIntakeFailureCode.REAL_SECRET_MATERIAL_PRESENT)
    if inp.oauth_execution_detected:
        failure_codes.append(CredentialIntakeFailureCode.OAUTH_EXECUTION_DETECTED)
    if inp.google_ads_api_call_detected:
        failure_codes.append(CredentialIntakeFailureCode.GOOGLE_ADS_API_CALL_DETECTED)
    if inp.gcp_command_detected:
        failure_codes.append(CredentialIntakeFailureCode.GCP_COMMAND_DETECTED)
    if inp.filesystem_write_detected:
        failure_codes.append(CredentialIntakeFailureCode.FILESYSTEM_WRITE_DETECTED)
    if inp.network_call_detected:
        failure_codes.append(CredentialIntakeFailureCode.NETWORK_CALL_DETECTED)

    # Boundary confirmations
    if not inp.transfer_path_forbidden_confirmed:
        failure_codes.append(CredentialIntakeFailureCode.TRANSFER_PATH_FORBIDDEN)
    if not inp.credential_values_absent:
        failure_codes.append(CredentialIntakeFailureCode.CREDENTIAL_VALUES_IN_INPUT)
    if not inp.live_flag_false_confirmed:
        failure_codes.append(CredentialIntakeFailureCode.LIVE_FLAG_NOT_FALSE)
    if not inp.gcp_write_operator_only_confirmed:
        failure_codes.append(CredentialIntakeFailureCode.GCP_WRITE_NOT_OPERATOR_ONLY)
    if not inp.screen_recording_prohibited_confirmed:
        failure_codes.append(CredentialIntakeFailureCode.SCREEN_RECORDING_PROHIBITED)
    if not inp.repo_commit_prohibited_confirmed:
        failure_codes.append(CredentialIntakeFailureCode.REPO_COMMIT_PROHIBITED)
    if not inp.immediate_redaction_confirmed:
        failure_codes.append(CredentialIntakeFailureCode.IMMEDIATE_REDACTION_REQUIRED)

    # Plan fields
    if not inp.rollback_plan_present:
        failure_codes.append(CredentialIntakeFailureCode.ROLLBACK_PLAN_MISSING)
    if not inp.emergency_revoke_plan_present:
        failure_codes.append(CredentialIntakeFailureCode.EMERGENCY_REVOKE_PLAN_MISSING)
    if not inp.operator_confirmation_present:
        failure_codes.append(CredentialIntakeFailureCode.OPERATOR_CONFIRMATION_MISSING)
    if not inp.audit_enabled:
        failure_codes.append(CredentialIntakeFailureCode.AUDIT_NOT_ENABLED)

    # Reference / confirmation fields
    if not inp.checklist_reference_present:
        failure_codes.append(CredentialIntakeFailureCode.CHECKLIST_REFERENCE_MISSING)
    if not inp.intake_boundary_doc_confirmed:
        failure_codes.append(CredentialIntakeFailureCode.INTAKE_BOUNDARY_DOC_MISSING)
    if not inp.operator_identity_present:
        failure_codes.append(CredentialIntakeFailureCode.OPERATOR_IDENTITY_MISSING)
    if not inp.approval_ceremony_reference_present:
        failure_codes.append(CredentialIntakeFailureCode.APPROVAL_CEREMONY_REFERENCE_MISSING)

    # Evidence and metadata forbidden field/value checks
    failure_codes.extend(_check_mapping_for_forbidden(
        inp.evidence,
        CredentialIntakeFailureCode.FORBIDDEN_FIELD_PRESENT,
        CredentialIntakeFailureCode.FORBIDDEN_VALUE_PRESENT,
    ))
    failure_codes.extend(_check_mapping_for_forbidden(
        inp.metadata,
        CredentialIntakeFailureCode.FORBIDDEN_FIELD_PRESENT,
        CredentialIntakeFailureCode.FORBIDDEN_VALUE_PRESENT,
    ))

    ok = len(failure_codes) == 0
    decision = CredentialIntakeDecision.PASS if ok else CredentialIntakeDecision.FAIL

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

    return CredentialIntakeDryRunResult(
        ok=ok,
        decision=decision,
        failure_codes=failure_codes,
        required_actions=required_actions,
        sanitized_summary=sanitized_summary,
    )

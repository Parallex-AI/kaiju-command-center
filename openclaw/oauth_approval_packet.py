"""
V5.21 Phase 6 — OAuth operator approval packet model and validator.

Pure local logic. No GCP calls. No Google Ads API calls. No OAuth execution.
No real approval record created. No real operator identities. No real tenant/client IDs.
No real credentials. No real resource paths. No real project IDs or emails.
No os.environ reads. No filesystem I/O. No network calls. No browser interaction.
Claude Code does not create real approvals and does not execute real OAuth onboarding.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)


# ---------------------------------------------------------------------------
# Decision and failure code constants
# ---------------------------------------------------------------------------

class OAuthApprovalPacketDecision:
    PASS = "PASS"
    FAIL = "FAIL"


class OAuthApprovalPacketFailureCode:
    # Approval record requirements — must all be True (4)
    APPROVAL_MISSING = "approval_missing"
    APPROVAL_NOT_APPROVED = "approval_not_approved"
    APPROVAL_EXPIRED = "approval_expired"
    APPROVAL_SCOPE_INVALID = "approval_scope_invalid"
    # Participant requirements — must all be True (7)
    OPERATOR_MISSING = "operator_missing"
    REVIEWER_MISSING = "reviewer_missing"
    TENANT_REF_MISSING = "tenant_ref_missing"
    CLIENT_REF_MISSING = "client_ref_missing"
    ROLLBACK_OWNER_MISSING = "rollback_owner_missing"
    EMERGENCY_REVOKE_OWNER_MISSING = "emergency_revoke_owner_missing"
    EVIDENCE_OWNER_MISSING = "evidence_owner_missing"
    STOP_AUTHORITY_MISSING = "stop_authority_missing"
    # Execution window requirements — must all be True (2)
    EXECUTION_WINDOW_MISSING = "execution_window_missing"
    EXECUTION_WINDOW_NOT_TIMEBOXED = "execution_window_not_timeboxed"
    # Validator gate requirements — must all be True (7)
    OAUTH_AUTH_URL_GATE_MISSING = "oauth_auth_url_gate_missing"
    OAUTH_CALLBACK_GATE_MISSING = "oauth_callback_gate_missing"
    CREDENTIAL_HANDOFF_PROTOCOL_MISSING = "credential_handoff_protocol_missing"
    CREDENTIAL_INTAKE_GATE_MISSING = "credential_intake_gate_missing"
    SECRET_VERSION_POLICY_GATE_MISSING = "secret_version_policy_gate_missing"
    ROLLBACK_DRILL_GATE_MISSING = "rollback_drill_gate_missing"
    LIVE_GATE_REQUIREMENT_MISSING = "live_gate_requirement_missing"
    # Audit and ceremony requirements — must all be True (4)
    AUDIT_REQUIREMENT_MISSING = "audit_requirement_missing"
    SAFETY_GREP_REQUIREMENT_MISSING = "safety_grep_requirement_missing"
    SMOKE_TEST_REQUIREMENT_MISSING = "smoke_test_requirement_missing"
    FINAL_LIVE_FLAG_RESET_REQUIREMENT_MISSING = "final_live_flag_reset_requirement_missing"
    # Hard-stop detections — must all be False (6)
    REAL_CREDENTIAL_PRESENT = "real_credential_present"
    OAUTH_EXECUTION_DETECTED = "oauth_execution_detected"
    GOOGLE_ADS_API_CALLED = "google_ads_api_called"
    GCP_COMMANDS_USED = "gcp_commands_used"
    SECRET_MANAGER_CALLED = "secret_manager_called"
    TOKEN_EXCHANGE_ATTEMPTED = "token_exchange_attempted"
    # Forbidden field / value (2)
    FORBIDDEN_FIELD_PRESENT = "forbidden_field_present"
    FORBIDDEN_VALUE_PRESENT = "forbidden_value_present"


# ---------------------------------------------------------------------------
# Forbidden field and value constants
# ---------------------------------------------------------------------------

# All names stored in lowercase; checked with key.lower() for case-insensitive match.
_FORBIDDEN_FIELD_NAMES: frozenset = frozenset({
    "client_id",
    "google_ads_client_id",
    "client_secret",
    "refresh_token",
    "access_token",
    "auth_code",
    "authorization_code",
    "callback_url",
    "oauth_callback_url",
    "token_response",
    "token_payload",
    "developer_token",
    "customer_id",
    "login_customer_id",
    "credential_ref",
    "secret_id",
    "project_id",
    "project_number",
    "service_account_email",
    "credential_file_path",
    "google_application_credentials",
    "oauth_url",
    "authorization_url",
    "redirect_uri_value",
    "raw_redirect_uri",
    "state_value",
    "raw_state",
    "token_value",
    "raw_secret",
    "api_response_payload",
    "approval_raw_payload",
    "real_operator_email",
})

_FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"ya29\.[A-Za-z0-9_\-]{5,}"),               # OAuth access token prefix
    re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}"),               # API key prefix
    re.compile(r"4/0[A-Za-z][A-Za-z0-9_\-]{3,}"),          # Google auth code prefix
    re.compile(r"1//[A-Za-z0-9_\-]{3,}"),                  # Google refresh token prefix
    re.compile(r"\bprojects/[a-zA-Z0-9\-_]+/"),            # GCP resource paths
    re.compile(r"\bsecrets/[a-zA-Z0-9\-_]+"),              # Secret Manager paths
    re.compile(r"[a-zA-Z0-9._%+\-]{2,}@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),  # email-like
    re.compile(r"\.json\b"),                                # JSON key file references
    re.compile(r"accounts\.google\.com"),                   # real OAuth domain
    re.compile(r"oauth2\.googleapis\.com"),                 # real OAuth token endpoint
    re.compile(r"fake-v52[0-9]"),                           # fake payload sentinels (V5.21+)
    re.compile(r"\bclient_secret\b"),                       # credential field name as value
    re.compile(r"\brefresh_token\b"),                       # credential field name as value
    re.compile(r"\baccess_token\b"),                        # credential field name as value
    re.compile(r"\bauth_code\b"),                           # credential field name as value
    re.compile(r"\bauthorization_code\b"),                  # credential field name as value
    re.compile(r"\bcallback_url\b"),                        # callback URL field name as value
    re.compile(r"\btoken_response\b"),                      # token response field name as value
    re.compile(r"\bdeveloper_token\b"),                     # credential field name as value
    re.compile(r"\bcustomer_id\b"),                         # account identifier as value
    re.compile(r"\blogin_customer_id\b"),                   # account identifier as value
]

# ---------------------------------------------------------------------------
# Sanitized summary fields (excludes evidence, metadata, and any credential-
# shaped values; includes all boolean approval checks plus decision metadata)
# ---------------------------------------------------------------------------

_SANITIZED_SUMMARY_FIELDS = (
    "approval_present",
    "approval_approved",
    "approval_unexpired",
    "approval_scope_valid",
    "operator_present",
    "reviewer_present",
    "tenant_ref_present",
    "client_ref_present",
    "execution_window_present",
    "execution_window_timeboxed",
    "rollback_owner_present",
    "emergency_revoke_owner_present",
    "evidence_owner_present",
    "stop_authority_present",
    "oauth_auth_url_gate_present",
    "oauth_callback_gate_present",
    "credential_handoff_protocol_present",
    "credential_intake_gate_present",
    "secret_version_policy_gate_present",
    "rollback_drill_gate_present",
    "live_gate_requirement_present",
    "audit_requirement_present",
    "safety_grep_requirement_present",
    "smoke_test_requirement_present",
    "final_live_flag_reset_requirement_present",
    "real_credential_present",
    "oauth_execution_detected",
    "google_ads_api_called",
    "gcp_commands_used",
    "secret_manager_called",
    "token_exchange_attempted",
)

# ---------------------------------------------------------------------------
# Required actions mapping
# ---------------------------------------------------------------------------

_REQUIRED_ACTIONS: Dict[str, str] = {
    OAuthApprovalPacketFailureCode.APPROVAL_MISSING: (
        "An approval record must be present before the ceremony window opens. "
        "Obtain operator approval and record it in LocalFileApprovalStore outside the repository."
    ),
    OAuthApprovalPacketFailureCode.APPROVAL_NOT_APPROVED: (
        "The approval record must have status APPROVED. "
        "Verify the record status and update it before the ceremony window opens."
    ),
    OAuthApprovalPacketFailureCode.APPROVAL_EXPIRED: (
        "The approval record has expired. "
        "Obtain a new time-limited approval before the ceremony window opens."
    ),
    OAuthApprovalPacketFailureCode.APPROVAL_SCOPE_INVALID: (
        "The approval scope must match the OAuth onboarding operation. "
        "Verify scope alignment and update the approval record before proceeding."
    ),
    OAuthApprovalPacketFailureCode.OPERATOR_MISSING: (
        "The primary operator must be confirmed and present before the ceremony window opens. "
        "Confirm operator availability and record confirmation."
    ),
    OAuthApprovalPacketFailureCode.REVIEWER_MISSING: (
        "The secondary reviewer must be confirmed and present before the ceremony window opens. "
        "Confirm reviewer availability and record confirmation."
    ),
    OAuthApprovalPacketFailureCode.TENANT_REF_MISSING: (
        "The tenant reference must be confirmed (redacted form only) before the ceremony window opens. "
        "Record the tenant ref in the approval record outside the repository."
    ),
    OAuthApprovalPacketFailureCode.CLIENT_REF_MISSING: (
        "The client reference must be confirmed (redacted form only) before the ceremony window opens. "
        "Record the client ref in the approval record outside the repository."
    ),
    OAuthApprovalPacketFailureCode.EXECUTION_WINDOW_MISSING: (
        "An execution window with start time and end time must be defined before the ceremony window opens. "
        "Specify the window in the approval record and confirm with the approval owner."
    ),
    OAuthApprovalPacketFailureCode.EXECUTION_WINDOW_NOT_TIMEBOXED: (
        "The execution window must have a defined maximum duration. "
        "Specify the timebox in the approval record before proceeding."
    ),
    OAuthApprovalPacketFailureCode.ROLLBACK_OWNER_MISSING: (
        "A rollback owner must be confirmed and reachable before the ceremony window opens. "
        "Confirm rollback owner availability and record confirmation."
    ),
    OAuthApprovalPacketFailureCode.EMERGENCY_REVOKE_OWNER_MISSING: (
        "An emergency revoke owner must be confirmed and reachable before the ceremony window opens. "
        "Confirm emergency revoke owner availability and record confirmation."
    ),
    OAuthApprovalPacketFailureCode.EVIDENCE_OWNER_MISSING: (
        "An evidence package owner must be confirmed before the ceremony window opens. "
        "Confirm evidence owner availability and record confirmation."
    ),
    OAuthApprovalPacketFailureCode.STOP_AUTHORITY_MISSING: (
        "A stop authority must be confirmed and reachable before the ceremony window opens. "
        "Confirm stop authority availability and record confirmation."
    ),
    OAuthApprovalPacketFailureCode.OAUTH_AUTH_URL_GATE_MISSING: (
        "The OAuth authorization URL design validator PASS must be confirmed before the ceremony window opens. "
        "Run validate_oauth_auth_url_design() and confirm PASS."
    ),
    OAuthApprovalPacketFailureCode.OAUTH_CALLBACK_GATE_MISSING: (
        "The OAuth callback design validator PASS must be confirmed before the ceremony window opens. "
        "Run validate_oauth_callback_design() and confirm PASS."
    ),
    OAuthApprovalPacketFailureCode.CREDENTIAL_HANDOFF_PROTOCOL_MISSING: (
        "The credential handoff protocol (docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md) must be reviewed "
        "and confirmed before the ceremony window opens. Confirm all 14 sections reviewed."
    ),
    OAuthApprovalPacketFailureCode.CREDENTIAL_INTAKE_GATE_MISSING: (
        "The credential intake validator PASS must be confirmed before the ceremony window opens. "
        "Run validate_credential_intake() and confirm PASS."
    ),
    OAuthApprovalPacketFailureCode.SECRET_VERSION_POLICY_GATE_MISSING: (
        "The secret version lifecycle policy validator PASS must be confirmed before the ceremony window opens. "
        "Run validate_secret_version_policy() and confirm PASS."
    ),
    OAuthApprovalPacketFailureCode.ROLLBACK_DRILL_GATE_MISSING: (
        "The rollback drill validator PASS must be confirmed before the ceremony window opens. "
        "Run validate_rollback_drill() and confirm PASS."
    ),
    OAuthApprovalPacketFailureCode.LIVE_GATE_REQUIREMENT_MISSING: (
        "The live gate requirement must be confirmed before the ceremony window opens. "
        "Confirm check_live_gate() PASS with correct approval conditions."
    ),
    OAuthApprovalPacketFailureCode.AUDIT_REQUIREMENT_MISSING: (
        "The audit event requirement must be confirmed before the ceremony window opens. "
        "Confirm audit logging is enabled and the audit path is writable."
    ),
    OAuthApprovalPacketFailureCode.SAFETY_GREP_REQUIREMENT_MISSING: (
        "A safety grep CLEAN result must be confirmed before the ceremony window opens. "
        "Run all safety greps on ceremony-modified files and confirm CLEAN."
    ),
    OAuthApprovalPacketFailureCode.SMOKE_TEST_REQUIREMENT_MISSING: (
        "Both smoke suites PASS must be confirmed before the ceremony window opens. "
        "Run smoke_test_v5_credentials.sh and smoke_test_v5_12_gcp_secret_manager.sh and confirm PASS."
    ),
    OAuthApprovalPacketFailureCode.FINAL_LIVE_FLAG_RESET_REQUIREMENT_MISSING: (
        "The final GOOGLE_ADS_LIVE_ENABLED reset requirement must be confirmed before the ceremony window opens. "
        "Confirm that GOOGLE_ADS_LIVE_ENABLED will be reset to false immediately after the ceremony."
    ),
    OAuthApprovalPacketFailureCode.REAL_CREDENTIAL_PRESENT: (
        "Real credentials must not be present in this validator input. "
        "Remove all credential values immediately. Credentials must never appear in validator inputs, logs, docs, or chat."
    ),
    OAuthApprovalPacketFailureCode.OAUTH_EXECUTION_DETECTED: (
        "OAuth execution must not occur during Phase 6. "
        "Stop immediately. No OAuth flow may be initiated by this validator."
    ),
    OAuthApprovalPacketFailureCode.GOOGLE_ADS_API_CALLED: (
        "The Google Ads API must not be called during Phase 6. "
        "Stop immediately. API calls require separate explicit operator authorization."
    ),
    OAuthApprovalPacketFailureCode.GCP_COMMANDS_USED: (
        "GCP commands must not be run during Phase 6. "
        "Stop immediately. GCP operations require separate explicit operator authorization."
    ),
    OAuthApprovalPacketFailureCode.SECRET_MANAGER_CALLED: (
        "Secret Manager must not be called during Phase 6. "
        "Stop immediately. Secret Manager calls require separate explicit operator authorization."
    ),
    OAuthApprovalPacketFailureCode.TOKEN_EXCHANGE_ATTEMPTED: (
        "Token exchange must not be attempted during Phase 6. "
        "Stop immediately. Token exchange requires separate explicit operator authorization."
    ),
    OAuthApprovalPacketFailureCode.FORBIDDEN_FIELD_PRESENT: (
        "Remove all forbidden field names from evidence and metadata. "
        "Credential-shaped keys must not appear in validator inputs."
    ),
    OAuthApprovalPacketFailureCode.FORBIDDEN_VALUE_PRESENT: (
        "Remove all forbidden value patterns from evidence and metadata. "
        "Token-shaped, URL-shaped, and resource-path-shaped values must not appear."
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class OAuthApprovalPacketInput:
    # Approval record requirements (must all be True to PASS)
    approval_present: bool
    approval_approved: bool
    approval_unexpired: bool
    approval_scope_valid: bool
    # Participant requirements (must all be True to PASS)
    operator_present: bool
    reviewer_present: bool
    tenant_ref_present: bool
    client_ref_present: bool
    rollback_owner_present: bool
    emergency_revoke_owner_present: bool
    evidence_owner_present: bool
    stop_authority_present: bool
    # Execution window requirements (must all be True to PASS)
    execution_window_present: bool
    execution_window_timeboxed: bool
    # Validator gate requirements (must all be True to PASS)
    oauth_auth_url_gate_present: bool
    oauth_callback_gate_present: bool
    credential_handoff_protocol_present: bool
    credential_intake_gate_present: bool
    secret_version_policy_gate_present: bool
    rollback_drill_gate_present: bool
    live_gate_requirement_present: bool
    # Audit and ceremony requirements (must all be True to PASS)
    audit_requirement_present: bool
    safety_grep_requirement_present: bool
    smoke_test_requirement_present: bool
    final_live_flag_reset_requirement_present: bool
    # Hard-stop detections (must all be False to PASS)
    real_credential_present: bool
    oauth_execution_detected: bool
    google_ads_api_called: bool
    gcp_commands_used: bool
    secret_manager_called: bool
    token_exchange_attempted: bool
    # Evidence and metadata (excluded from sanitized_summary)
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OAuthApprovalPacketResult:
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

def validate_oauth_approval_packet(inp: OAuthApprovalPacketInput) -> OAuthApprovalPacketResult:
    """
    Validate that an operator approval packet is complete before any future OAuth ceremony.

    Returns ok=True only when all approval packet requirements are met, all hard-stop
    detections are False, and evidence/metadata contain no forbidden field names or
    value patterns.

    Never creates a real approval record. Never executes OAuth. Never calls Google Ads API,
    GCP, or Secret Manager. Never reads real credentials. Never makes network calls.
    Never writes to the filesystem. Never uses real operator identities or tenant/client IDs.
    Claude Code does not create real approvals and does not execute real OAuth onboarding.
    """
    failure_codes: List[str] = []

    # Approval record requirements — must all be True
    if not inp.approval_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.APPROVAL_MISSING)
    if not inp.approval_approved:
        failure_codes.append(OAuthApprovalPacketFailureCode.APPROVAL_NOT_APPROVED)
    if not inp.approval_unexpired:
        failure_codes.append(OAuthApprovalPacketFailureCode.APPROVAL_EXPIRED)
    if not inp.approval_scope_valid:
        failure_codes.append(OAuthApprovalPacketFailureCode.APPROVAL_SCOPE_INVALID)

    # Participant requirements — must all be True
    if not inp.operator_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.OPERATOR_MISSING)
    if not inp.reviewer_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.REVIEWER_MISSING)
    if not inp.tenant_ref_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.TENANT_REF_MISSING)
    if not inp.client_ref_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.CLIENT_REF_MISSING)
    if not inp.rollback_owner_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.ROLLBACK_OWNER_MISSING)
    if not inp.emergency_revoke_owner_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.EMERGENCY_REVOKE_OWNER_MISSING)
    if not inp.evidence_owner_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.EVIDENCE_OWNER_MISSING)
    if not inp.stop_authority_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.STOP_AUTHORITY_MISSING)

    # Execution window requirements — must all be True
    if not inp.execution_window_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.EXECUTION_WINDOW_MISSING)
    if not inp.execution_window_timeboxed:
        failure_codes.append(OAuthApprovalPacketFailureCode.EXECUTION_WINDOW_NOT_TIMEBOXED)

    # Validator gate requirements — must all be True
    if not inp.oauth_auth_url_gate_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.OAUTH_AUTH_URL_GATE_MISSING)
    if not inp.oauth_callback_gate_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.OAUTH_CALLBACK_GATE_MISSING)
    if not inp.credential_handoff_protocol_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.CREDENTIAL_HANDOFF_PROTOCOL_MISSING)
    if not inp.credential_intake_gate_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.CREDENTIAL_INTAKE_GATE_MISSING)
    if not inp.secret_version_policy_gate_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.SECRET_VERSION_POLICY_GATE_MISSING)
    if not inp.rollback_drill_gate_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.ROLLBACK_DRILL_GATE_MISSING)
    if not inp.live_gate_requirement_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.LIVE_GATE_REQUIREMENT_MISSING)

    # Audit and ceremony requirements — must all be True
    if not inp.audit_requirement_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.AUDIT_REQUIREMENT_MISSING)
    if not inp.safety_grep_requirement_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.SAFETY_GREP_REQUIREMENT_MISSING)
    if not inp.smoke_test_requirement_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.SMOKE_TEST_REQUIREMENT_MISSING)
    if not inp.final_live_flag_reset_requirement_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.FINAL_LIVE_FLAG_RESET_REQUIREMENT_MISSING)

    # Hard-stop detections — must all be False
    if inp.real_credential_present:
        failure_codes.append(OAuthApprovalPacketFailureCode.REAL_CREDENTIAL_PRESENT)
    if inp.oauth_execution_detected:
        failure_codes.append(OAuthApprovalPacketFailureCode.OAUTH_EXECUTION_DETECTED)
    if inp.google_ads_api_called:
        failure_codes.append(OAuthApprovalPacketFailureCode.GOOGLE_ADS_API_CALLED)
    if inp.gcp_commands_used:
        failure_codes.append(OAuthApprovalPacketFailureCode.GCP_COMMANDS_USED)
    if inp.secret_manager_called:
        failure_codes.append(OAuthApprovalPacketFailureCode.SECRET_MANAGER_CALLED)
    if inp.token_exchange_attempted:
        failure_codes.append(OAuthApprovalPacketFailureCode.TOKEN_EXCHANGE_ATTEMPTED)

    # Forbidden field/value detection in evidence and metadata
    for mapping in (inp.evidence, inp.metadata):
        failure_codes.extend(
            _check_mapping_for_forbidden(
                mapping,
                OAuthApprovalPacketFailureCode.FORBIDDEN_FIELD_PRESENT,
                OAuthApprovalPacketFailureCode.FORBIDDEN_VALUE_PRESENT,
            )
        )

    ok = len(failure_codes) == 0
    decision = OAuthApprovalPacketDecision.PASS if ok else OAuthApprovalPacketDecision.FAIL
    required_actions = [_REQUIRED_ACTIONS[c] for c in failure_codes if c in _REQUIRED_ACTIONS]

    sanitized_summary: Dict[str, Any] = {
        f: getattr(inp, f) for f in _SANITIZED_SUMMARY_FIELDS
    }
    sanitized_summary["decision"] = decision
    sanitized_summary["ok"] = ok
    sanitized_summary["failure_count"] = len(failure_codes)

    return OAuthApprovalPacketResult(
        ok=ok,
        decision=decision,
        failure_codes=failure_codes,
        required_actions=required_actions,
        sanitized_summary=sanitized_summary,
    )

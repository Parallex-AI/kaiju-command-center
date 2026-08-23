"""
V5.22 Phase 3 — OAuth dry-run execution packet model and validator.

Pure local logic. No GCP calls. No Google Ads API calls. No OAuth execution.
No real credentials. No real approval record created. No real participant identities.
No real tenant/client IDs. No real auth codes. No real tokens. No token exchange.
No Secret Manager calls. No browser interaction. No authorization URL generation.
No callback URL. No os.environ reads. No filesystem I/O. No network calls.
Claude Code does not execute dry-run ceremonies and does not authorize real OAuth onboarding.
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

class OAuthDryRunExecutionDecision:
    PASS = "PASS"
    FAIL = "FAIL"


class OAuthDryRunExecutionFailureCode:
    # Packet completeness requirements — must all be True (12)
    PACKET_MISSING = "packet_missing"
    PACKET_IDENTITY_MISSING = "packet_identity_missing"
    BRANCH_REF_MISSING = "branch_ref_missing"
    BASELINE_REF_MISSING = "baseline_ref_missing"
    PARTICIPANT_PLACEHOLDERS_MISSING = "participant_placeholders_missing"
    TARGET_CONTEXT_PLACEHOLDERS_MISSING = "target_context_placeholders_missing"
    TIMED_WINDOW_MISSING = "timed_window_missing"
    TIMED_WINDOW_NOT_TIMEBOXED = "timed_window_not_timeboxed"
    STOP_AUTHORITY_MISSING = "stop_authority_missing"
    ROLLBACK_OWNER_MISSING = "rollback_owner_missing"
    EMERGENCY_REVOKE_OWNER_MISSING = "emergency_revoke_owner_missing"
    EVIDENCE_OWNER_MISSING = "evidence_owner_missing"
    # Pre-flight and validator gate requirements — must all be True (11)
    PREFLIGHT_GATES_MISSING = "preflight_gates_missing"
    APPROVAL_PACKET_GATE_NOT_PASSED = "approval_packet_gate_not_passed"
    AUTH_URL_DESIGN_GATE_NOT_PASSED = "auth_url_design_gate_not_passed"
    CALLBACK_BOUNDARY_GATE_NOT_PASSED = "callback_boundary_gate_not_passed"
    CREDENTIAL_INTAKE_GATE_NOT_PASSED = "credential_intake_gate_not_passed"
    SECRET_VERSION_POLICY_GATE_NOT_PASSED = "secret_version_policy_gate_not_passed"
    ROLLBACK_DRILL_GATE_NOT_PASSED = "rollback_drill_gate_not_passed"
    ONBOARDING_CEREMONY_GATE_NOT_PASSED = "onboarding_ceremony_gate_not_passed"
    SMOKE_CREDENTIALS_NOT_PASSED = "smoke_credentials_not_passed"
    SMOKE_SECRET_MANAGER_NOT_PASSED = "smoke_secret_manager_not_passed"
    SAFETY_GREP_NOT_CLEAN = "safety_grep_not_clean"
    # Dry-run sequence and evidence requirements — must all be True (7)
    DRY_RUN_SEQUENCE_INCOMPLETE = "dry_run_sequence_incomplete"
    VALIDATOR_EVIDENCE_MISSING = "validator_evidence_missing"
    NO_EXECUTION_CONFIRMATIONS_MISSING = "no_execution_confirmations_missing"
    EVIDENCE_PACKAGE_NOT_REDACTED = "evidence_package_not_redacted"
    STOP_CONDITIONS_NOT_REVIEWED = "stop_conditions_not_reviewed"
    ROLLBACK_REHEARSAL_MISSING = "rollback_rehearsal_missing"
    FINAL_DECISION_MISSING = "final_decision_missing"
    # Hard-stop detections — must all be False (15)
    REAL_CREDENTIAL_PRESENT = "real_credential_present"
    REAL_APPROVAL_CREATED = "real_approval_created"
    OAUTH_EXECUTION_DETECTED = "oauth_execution_detected"
    BROWSER_OPENED = "browser_opened"
    AUTHORIZATION_URL_GENERATED = "authorization_url_generated"
    CALLBACK_URL_RECEIVED = "callback_url_received"
    AUTH_CODE_RECEIVED = "auth_code_received"
    TOKEN_EXCHANGE_ATTEMPTED = "token_exchange_attempted"
    TOKEN_RESPONSE_RECEIVED = "token_response_received"
    SECRET_MANAGER_CALLED = "secret_manager_called"
    GOOGLE_ADS_API_CALLED = "google_ads_api_called"
    GCP_COMMANDS_USED = "gcp_commands_used"
    DEPLOY_PERFORMED = "deploy_performed"
    IAM_API_BILLING_CHANGED = "iam_api_billing_changed"
    LIVE_FLAG_ACTIVATED = "live_flag_activated"
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
    "real_participant_name",
    "real_account_identifier",
    "raw_packet_payload",
    "raw_evidence_payload",
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
    re.compile(r"fake-v52[0-9]"),                           # fake payload sentinels (V5.22+)
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
# shaped values; includes all 45 boolean checks plus decision metadata)
# ---------------------------------------------------------------------------

_SANITIZED_SUMMARY_FIELDS = (
    # Packet completeness
    "packet_present",
    "packet_identity_present",
    "branch_ref_present",
    "baseline_ref_present",
    "participant_placeholders_present",
    "target_context_placeholders_present",
    "timed_window_present",
    "timed_window_timeboxed",
    "stop_authority_present",
    "rollback_owner_present",
    "emergency_revoke_owner_present",
    "evidence_owner_present",
    # Pre-flight and validator gates
    "preflight_gates_present",
    "approval_packet_gate_passed",
    "auth_url_design_gate_passed",
    "callback_boundary_gate_passed",
    "credential_intake_gate_passed",
    "secret_version_policy_gate_passed",
    "rollback_drill_gate_passed",
    "onboarding_ceremony_gate_passed",
    "smoke_credentials_passed",
    "smoke_secret_manager_passed",
    "safety_grep_clean",
    # Dry-run sequence and evidence
    "dry_run_sequence_complete",
    "validator_evidence_present",
    "no_execution_confirmations_present",
    "evidence_package_redacted",
    "stop_conditions_reviewed",
    "rollback_rehearsal_present",
    "final_decision_present",
    # Hard-stop detections
    "real_credential_present",
    "real_approval_created",
    "oauth_execution_detected",
    "browser_opened",
    "authorization_url_generated",
    "callback_url_received",
    "auth_code_received",
    "token_exchange_attempted",
    "token_response_received",
    "secret_manager_called",
    "google_ads_api_called",
    "gcp_commands_used",
    "deploy_performed",
    "iam_api_billing_changed",
    "live_flag_activated",
)

# ---------------------------------------------------------------------------
# Required actions mapping
# ---------------------------------------------------------------------------

_REQUIRED_ACTIONS: Dict[str, str] = {
    OAuthDryRunExecutionFailureCode.PACKET_MISSING: (
        "A dry-run execution packet document must exist before recording results. "
        "Complete docs/GOOGLE_ADS_OAUTH_DRY_RUN_EXECUTION_PACKET.md and confirm packet_present=True."
    ),
    OAuthDryRunExecutionFailureCode.PACKET_IDENTITY_MISSING: (
        "The packet identity fields (packet_ref, branch, baseline_ref, timestamp_label) must be present. "
        "Populate Section B of the dry-run execution packet with placeholder labels only."
    ),
    OAuthDryRunExecutionFailureCode.BRANCH_REF_MISSING: (
        "The branch reference must be recorded in the packet identity section. "
        "Confirm the branch name and record it as a placeholder label in the packet."
    ),
    OAuthDryRunExecutionFailureCode.BASELINE_REF_MISSING: (
        "The baseline commit reference must be recorded in the packet identity section. "
        "Confirm the baseline commit hash and record it as a placeholder label in the packet."
    ),
    OAuthDryRunExecutionFailureCode.PARTICIPANT_PLACEHOLDERS_MISSING: (
        "All participant roles must be present as placeholder labels in Section C. "
        "Confirm all 11 roles are populated with <label> placeholders — no real identities."
    ),
    OAuthDryRunExecutionFailureCode.TARGET_CONTEXT_PLACEHOLDERS_MISSING: (
        "All target context fields must be present as placeholder references in Section D. "
        "Confirm all 7 reference fields are populated with redacted placeholder values."
    ),
    OAuthDryRunExecutionFailureCode.TIMED_WINDOW_MISSING: (
        "A timed execution window with date, start time, duration, and state fields must be defined. "
        "Populate Section E of the dry-run execution packet."
    ),
    OAuthDryRunExecutionFailureCode.TIMED_WINDOW_NOT_TIMEBOXED: (
        "The execution window must have a defined maximum duration. "
        "Confirm the window_duration_max_minutes field is specified in Section E."
    ),
    OAuthDryRunExecutionFailureCode.STOP_AUTHORITY_MISSING: (
        "A stop authority must be confirmed as a placeholder label in Section C. "
        "Confirm stop authority availability and record the placeholder label."
    ),
    OAuthDryRunExecutionFailureCode.ROLLBACK_OWNER_MISSING: (
        "A rollback owner must be confirmed as a placeholder label in Section C. "
        "Confirm rollback owner availability and record the placeholder label."
    ),
    OAuthDryRunExecutionFailureCode.EMERGENCY_REVOKE_OWNER_MISSING: (
        "An emergency revoke owner must be confirmed as a placeholder label in Section C. "
        "Confirm emergency revoke owner availability and record the placeholder label."
    ),
    OAuthDryRunExecutionFailureCode.EVIDENCE_OWNER_MISSING: (
        "An evidence package owner must be confirmed as a placeholder label in Section C. "
        "Confirm evidence owner availability and record the placeholder label."
    ),
    OAuthDryRunExecutionFailureCode.PREFLIGHT_GATES_MISSING: (
        "All 15 pre-flight gates in Section F must be reviewed and marked PASS or PENDING. "
        "Complete the pre-flight gate review before proceeding."
    ),
    OAuthDryRunExecutionFailureCode.APPROVAL_PACKET_GATE_NOT_PASSED: (
        "The OAuth approval packet validator gate must be PASS before dry-run execution. "
        "Run validate_oauth_approval_packet() and confirm PASS in Section F."
    ),
    OAuthDryRunExecutionFailureCode.AUTH_URL_DESIGN_GATE_NOT_PASSED: (
        "The OAuth auth URL design validator gate must be PASS before dry-run execution. "
        "Run validate_oauth_auth_url_design() and confirm PASS in Section F."
    ),
    OAuthDryRunExecutionFailureCode.CALLBACK_BOUNDARY_GATE_NOT_PASSED: (
        "The OAuth callback boundary design validator gate must be PASS before dry-run execution. "
        "Run validate_oauth_callback_design() and confirm PASS in Section F."
    ),
    OAuthDryRunExecutionFailureCode.CREDENTIAL_INTAKE_GATE_NOT_PASSED: (
        "The credential intake validator gate must be PASS before dry-run execution. "
        "Run validate_credential_intake_dry_run() and confirm PASS in Section F."
    ),
    OAuthDryRunExecutionFailureCode.SECRET_VERSION_POLICY_GATE_NOT_PASSED: (
        "The secret version policy validator gate must be PASS before dry-run execution. "
        "Run validate_secret_version_policy() and confirm PASS in Section F."
    ),
    OAuthDryRunExecutionFailureCode.ROLLBACK_DRILL_GATE_NOT_PASSED: (
        "The rollback drill validator gate must be PASS before dry-run execution. "
        "Run validate_rollback_drill() and confirm PASS in Section F."
    ),
    OAuthDryRunExecutionFailureCode.ONBOARDING_CEREMONY_GATE_NOT_PASSED: (
        "The onboarding ceremony validator gate must be PASS before dry-run execution. "
        "Run the onboarding ceremony validator demo and confirm PASS in Section F."
    ),
    OAuthDryRunExecutionFailureCode.SMOKE_CREDENTIALS_NOT_PASSED: (
        "The credentials smoke suite (smoke_test_v5_credentials.sh) must PASS before dry-run execution. "
        "Run the smoke suite and confirm the result in Section F."
    ),
    OAuthDryRunExecutionFailureCode.SMOKE_SECRET_MANAGER_NOT_PASSED: (
        "The GCP Secret Manager smoke suite (smoke_test_v5_12_gcp_secret_manager.sh) must PASS. "
        "Run the smoke suite and confirm the result in Section F."
    ),
    OAuthDryRunExecutionFailureCode.SAFETY_GREP_NOT_CLEAN: (
        "A safety grep CLEAN result must be confirmed before dry-run execution. "
        "Run all safety greps on ceremony-modified files and confirm CLEAN in Section F."
    ),
    OAuthDryRunExecutionFailureCode.DRY_RUN_SEQUENCE_INCOMPLETE: (
        "All 24 steps of the dry-run sequence checklist (Section G, G-01–G-24) must be reviewed. "
        "Complete each step entry and confirm the step outcome."
    ),
    OAuthDryRunExecutionFailureCode.VALIDATOR_EVIDENCE_MISSING: (
        "Validator evidence fields (Section H) must be populated for all 10 validators/suites. "
        "Record PASS/FAIL for each validator or smoke suite result."
    ),
    OAuthDryRunExecutionFailureCode.NO_EXECUTION_CONFIRMATIONS_MISSING: (
        "All 16 no-execution confirmations (Section I) must be present and set to NO. "
        "Populate Section I and confirm all items are pre-filled NO."
    ),
    OAuthDryRunExecutionFailureCode.EVIDENCE_PACKAGE_NOT_REDACTED: (
        "All evidence in the package (Section J) must use placeholder/redacted content only. "
        "Remove any real values and replace with placeholder labels before proceeding."
    ),
    OAuthDryRunExecutionFailureCode.STOP_CONDITIONS_NOT_REVIEWED: (
        "All 21 stop conditions (Section K, K-01–K-21) must be reviewed and marked. "
        "Complete the stop-condition checklist and record each condition outcome."
    ),
    OAuthDryRunExecutionFailureCode.ROLLBACK_REHEARSAL_MISSING: (
        "The rollback and emergency revoke rehearsal (Section L) must be completed. "
        "Populate all 12 rollback rehearsal fields before recording a dry-run result."
    ),
    OAuthDryRunExecutionFailureCode.FINAL_DECISION_MISSING: (
        "The final dry-run decision block (Section M) must be completed. "
        "All 12 decision fields including sign-off must be populated before the dry-run record is created."
    ),
    OAuthDryRunExecutionFailureCode.REAL_CREDENTIAL_PRESENT: (
        "Real credentials must not be present in any dry-run input or packet field. "
        "Remove all credential values immediately. Credentials must never appear in validator inputs, logs, docs, or chat."
    ),
    OAuthDryRunExecutionFailureCode.REAL_APPROVAL_CREATED: (
        "A real approval record must not be created during dry-run execution. "
        "Stop immediately. Real approval creation is deferred to a separately authorized future ceremony."
    ),
    OAuthDryRunExecutionFailureCode.OAUTH_EXECUTION_DETECTED: (
        "OAuth execution must not occur during dry-run execution. "
        "Stop immediately. No OAuth flow may be initiated during a dry-run rehearsal."
    ),
    OAuthDryRunExecutionFailureCode.BROWSER_OPENED: (
        "A browser must not be opened during dry-run execution. "
        "Stop immediately. Browser interaction is deferred to a separately authorized real ceremony."
    ),
    OAuthDryRunExecutionFailureCode.AUTHORIZATION_URL_GENERATED: (
        "A real OAuth authorization URL must not be generated during dry-run execution. "
        "Stop immediately. Auth URL generation requires separate explicit operator authorization."
    ),
    OAuthDryRunExecutionFailureCode.CALLBACK_URL_RECEIVED: (
        "A real OAuth callback URL must not be received during dry-run execution. "
        "Stop immediately. Callback URL handling is deferred to a separately authorized real ceremony."
    ),
    OAuthDryRunExecutionFailureCode.AUTH_CODE_RECEIVED: (
        "A real authorization code must not be received during dry-run execution. "
        "Stop immediately. Auth code handling is deferred to a separately authorized real ceremony."
    ),
    OAuthDryRunExecutionFailureCode.TOKEN_EXCHANGE_ATTEMPTED: (
        "Token exchange must not be attempted during dry-run execution. "
        "Stop immediately. Token exchange requires separate explicit operator authorization."
    ),
    OAuthDryRunExecutionFailureCode.TOKEN_RESPONSE_RECEIVED: (
        "A real token response must not be received during dry-run execution. "
        "Stop immediately. Token response handling is deferred to a separately authorized real ceremony."
    ),
    OAuthDryRunExecutionFailureCode.SECRET_MANAGER_CALLED: (
        "Secret Manager must not be called during dry-run execution. "
        "Stop immediately. Secret Manager calls require separate explicit operator authorization."
    ),
    OAuthDryRunExecutionFailureCode.GOOGLE_ADS_API_CALLED: (
        "The Google Ads API must not be called during dry-run execution. "
        "Stop immediately. API calls require separate explicit operator authorization."
    ),
    OAuthDryRunExecutionFailureCode.GCP_COMMANDS_USED: (
        "GCP commands must not be run during dry-run execution. "
        "Stop immediately. GCP operations require separate explicit operator authorization."
    ),
    OAuthDryRunExecutionFailureCode.DEPLOY_PERFORMED: (
        "A deployment must not be performed during dry-run execution. "
        "Stop immediately. Deployment requires separate explicit operator authorization."
    ),
    OAuthDryRunExecutionFailureCode.IAM_API_BILLING_CHANGED: (
        "IAM, API, or billing settings must not be changed during dry-run execution. "
        "Stop immediately. Infrastructure changes require separate explicit operator authorization."
    ),
    OAuthDryRunExecutionFailureCode.LIVE_FLAG_ACTIVATED: (
        "GOOGLE_ADS_LIVE_ENABLED must not be activated during dry-run execution. "
        "Stop immediately. Live flag activation requires separate explicit operator authorization."
    ),
    OAuthDryRunExecutionFailureCode.FORBIDDEN_FIELD_PRESENT: (
        "Remove all forbidden field names from evidence and metadata. "
        "Credential-shaped keys must not appear in validator inputs."
    ),
    OAuthDryRunExecutionFailureCode.FORBIDDEN_VALUE_PRESENT: (
        "Remove all forbidden value patterns from evidence and metadata. "
        "Token-shaped, URL-shaped, and resource-path-shaped values must not appear."
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class OAuthDryRunExecutionInput:
    # Packet completeness requirements (must all be True to PASS)
    packet_present: bool
    packet_identity_present: bool
    branch_ref_present: bool
    baseline_ref_present: bool
    participant_placeholders_present: bool
    target_context_placeholders_present: bool
    timed_window_present: bool
    timed_window_timeboxed: bool
    stop_authority_present: bool
    rollback_owner_present: bool
    emergency_revoke_owner_present: bool
    evidence_owner_present: bool
    # Pre-flight and validator gate requirements (must all be True to PASS)
    preflight_gates_present: bool
    approval_packet_gate_passed: bool
    auth_url_design_gate_passed: bool
    callback_boundary_gate_passed: bool
    credential_intake_gate_passed: bool
    secret_version_policy_gate_passed: bool
    rollback_drill_gate_passed: bool
    onboarding_ceremony_gate_passed: bool
    smoke_credentials_passed: bool
    smoke_secret_manager_passed: bool
    safety_grep_clean: bool
    # Dry-run sequence and evidence requirements (must all be True to PASS)
    dry_run_sequence_complete: bool
    validator_evidence_present: bool
    no_execution_confirmations_present: bool
    evidence_package_redacted: bool
    stop_conditions_reviewed: bool
    rollback_rehearsal_present: bool
    final_decision_present: bool
    # Hard-stop detections (must all be False to PASS)
    real_credential_present: bool
    real_approval_created: bool
    oauth_execution_detected: bool
    browser_opened: bool
    authorization_url_generated: bool
    callback_url_received: bool
    auth_code_received: bool
    token_exchange_attempted: bool
    token_response_received: bool
    secret_manager_called: bool
    google_ads_api_called: bool
    gcp_commands_used: bool
    deploy_performed: bool
    iam_api_billing_changed: bool
    live_flag_activated: bool
    # Evidence and metadata (excluded from sanitized_summary)
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OAuthDryRunExecutionResult:
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

def validate_oauth_dry_run_execution(inp: OAuthDryRunExecutionInput) -> OAuthDryRunExecutionResult:
    """
    Validate that an OAuth dry-run execution packet is complete before recording results.

    Returns ok=True only when all packet completeness requirements are met, all gate
    checks PASS, all hard-stop detections are False, and evidence/metadata contain no
    forbidden field names or value patterns.

    Never executes a real dry-run ceremony. Never creates a real approval record.
    Never executes OAuth. Never opens a browser. Never generates a real authorization URL.
    Never receives a real callback URL or auth code. Never attempts token exchange.
    Never calls Google Ads API, GCP, or Secret Manager. Never reads real credentials.
    Never makes network calls. Never writes to the filesystem. Never uses real operator
    identities or tenant/client IDs.
    Claude Code does not execute dry-run ceremonies and does not authorize real OAuth onboarding.
    """
    failure_codes: List[str] = []

    # Packet completeness requirements — must all be True
    if not inp.packet_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.PACKET_MISSING)
    if not inp.packet_identity_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.PACKET_IDENTITY_MISSING)
    if not inp.branch_ref_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.BRANCH_REF_MISSING)
    if not inp.baseline_ref_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.BASELINE_REF_MISSING)
    if not inp.participant_placeholders_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.PARTICIPANT_PLACEHOLDERS_MISSING)
    if not inp.target_context_placeholders_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.TARGET_CONTEXT_PLACEHOLDERS_MISSING)
    if not inp.timed_window_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.TIMED_WINDOW_MISSING)
    if not inp.timed_window_timeboxed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.TIMED_WINDOW_NOT_TIMEBOXED)
    if not inp.stop_authority_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.STOP_AUTHORITY_MISSING)
    if not inp.rollback_owner_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.ROLLBACK_OWNER_MISSING)
    if not inp.emergency_revoke_owner_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.EMERGENCY_REVOKE_OWNER_MISSING)
    if not inp.evidence_owner_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.EVIDENCE_OWNER_MISSING)

    # Pre-flight and validator gate requirements — must all be True
    if not inp.preflight_gates_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.PREFLIGHT_GATES_MISSING)
    if not inp.approval_packet_gate_passed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.APPROVAL_PACKET_GATE_NOT_PASSED)
    if not inp.auth_url_design_gate_passed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.AUTH_URL_DESIGN_GATE_NOT_PASSED)
    if not inp.callback_boundary_gate_passed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.CALLBACK_BOUNDARY_GATE_NOT_PASSED)
    if not inp.credential_intake_gate_passed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.CREDENTIAL_INTAKE_GATE_NOT_PASSED)
    if not inp.secret_version_policy_gate_passed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.SECRET_VERSION_POLICY_GATE_NOT_PASSED)
    if not inp.rollback_drill_gate_passed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.ROLLBACK_DRILL_GATE_NOT_PASSED)
    if not inp.onboarding_ceremony_gate_passed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.ONBOARDING_CEREMONY_GATE_NOT_PASSED)
    if not inp.smoke_credentials_passed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.SMOKE_CREDENTIALS_NOT_PASSED)
    if not inp.smoke_secret_manager_passed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.SMOKE_SECRET_MANAGER_NOT_PASSED)
    if not inp.safety_grep_clean:
        failure_codes.append(OAuthDryRunExecutionFailureCode.SAFETY_GREP_NOT_CLEAN)

    # Dry-run sequence and evidence requirements — must all be True
    if not inp.dry_run_sequence_complete:
        failure_codes.append(OAuthDryRunExecutionFailureCode.DRY_RUN_SEQUENCE_INCOMPLETE)
    if not inp.validator_evidence_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.VALIDATOR_EVIDENCE_MISSING)
    if not inp.no_execution_confirmations_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.NO_EXECUTION_CONFIRMATIONS_MISSING)
    if not inp.evidence_package_redacted:
        failure_codes.append(OAuthDryRunExecutionFailureCode.EVIDENCE_PACKAGE_NOT_REDACTED)
    if not inp.stop_conditions_reviewed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.STOP_CONDITIONS_NOT_REVIEWED)
    if not inp.rollback_rehearsal_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.ROLLBACK_REHEARSAL_MISSING)
    if not inp.final_decision_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.FINAL_DECISION_MISSING)

    # Hard-stop detections — must all be False
    if inp.real_credential_present:
        failure_codes.append(OAuthDryRunExecutionFailureCode.REAL_CREDENTIAL_PRESENT)
    if inp.real_approval_created:
        failure_codes.append(OAuthDryRunExecutionFailureCode.REAL_APPROVAL_CREATED)
    if inp.oauth_execution_detected:
        failure_codes.append(OAuthDryRunExecutionFailureCode.OAUTH_EXECUTION_DETECTED)
    if inp.browser_opened:
        failure_codes.append(OAuthDryRunExecutionFailureCode.BROWSER_OPENED)
    if inp.authorization_url_generated:
        failure_codes.append(OAuthDryRunExecutionFailureCode.AUTHORIZATION_URL_GENERATED)
    if inp.callback_url_received:
        failure_codes.append(OAuthDryRunExecutionFailureCode.CALLBACK_URL_RECEIVED)
    if inp.auth_code_received:
        failure_codes.append(OAuthDryRunExecutionFailureCode.AUTH_CODE_RECEIVED)
    if inp.token_exchange_attempted:
        failure_codes.append(OAuthDryRunExecutionFailureCode.TOKEN_EXCHANGE_ATTEMPTED)
    if inp.token_response_received:
        failure_codes.append(OAuthDryRunExecutionFailureCode.TOKEN_RESPONSE_RECEIVED)
    if inp.secret_manager_called:
        failure_codes.append(OAuthDryRunExecutionFailureCode.SECRET_MANAGER_CALLED)
    if inp.google_ads_api_called:
        failure_codes.append(OAuthDryRunExecutionFailureCode.GOOGLE_ADS_API_CALLED)
    if inp.gcp_commands_used:
        failure_codes.append(OAuthDryRunExecutionFailureCode.GCP_COMMANDS_USED)
    if inp.deploy_performed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.DEPLOY_PERFORMED)
    if inp.iam_api_billing_changed:
        failure_codes.append(OAuthDryRunExecutionFailureCode.IAM_API_BILLING_CHANGED)
    if inp.live_flag_activated:
        failure_codes.append(OAuthDryRunExecutionFailureCode.LIVE_FLAG_ACTIVATED)

    # Forbidden field/value detection in evidence and metadata
    for mapping in (inp.evidence, inp.metadata):
        failure_codes.extend(
            _check_mapping_for_forbidden(
                mapping,
                OAuthDryRunExecutionFailureCode.FORBIDDEN_FIELD_PRESENT,
                OAuthDryRunExecutionFailureCode.FORBIDDEN_VALUE_PRESENT,
            )
        )

    ok = len(failure_codes) == 0
    decision = OAuthDryRunExecutionDecision.PASS if ok else OAuthDryRunExecutionDecision.FAIL
    required_actions = [_REQUIRED_ACTIONS[c] for c in failure_codes if c in _REQUIRED_ACTIONS]

    sanitized_summary: Dict[str, Any] = {
        f: getattr(inp, f) for f in _SANITIZED_SUMMARY_FIELDS
    }
    sanitized_summary["decision"] = decision
    sanitized_summary["ok"] = ok
    sanitized_summary["failure_count"] = len(failure_codes)

    return OAuthDryRunExecutionResult(
        ok=ok,
        decision=decision,
        failure_codes=failure_codes,
        required_actions=required_actions,
        sanitized_summary=sanitized_summary,
    )

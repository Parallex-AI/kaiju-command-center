"""
V5.20 Phase 6 — Rollback and emergency revoke drill validator.

Pure local logic. No GCP calls. No Google Ads API calls.
No secrets, tokens, credential values, or resource paths.
No os.environ reads. No network calls. No filesystem I/O.
Claude Code does not execute real rollback operations.
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
# Enums
# ---------------------------------------------------------------------------

class RollbackDrillDecision:
    PASS = "PASS"
    FAIL = "FAIL"


class RollbackDrillFailureCode:
    # Rollback step confirmations (11)
    LIVE_FLAG_NOT_DISABLED = "live_flag_not_disabled"
    APPROVAL_NOT_REVOKED = "approval_not_revoked"
    CREDENTIAL_NOT_REVOKED = "credential_not_revoked"
    CREDENTIAL_BUNDLE_NOT_DELETED_OR_REVOKED = "credential_bundle_not_deleted_or_revoked"
    POST_REVOKE_STATUS_NOT_VERIFIED = "post_revoke_status_not_verified"
    SECRET_STATUS_NOT_VERIFIED = "secret_status_not_verified"
    LIVE_GATE_NOT_DENIED_AFTER_REVOKE = "live_gate_not_denied_after_revoke"
    SMOKE_TESTS_NOT_PASSED = "smoke_tests_not_passed"
    SAFETY_GREP_NOT_CLEAN = "safety_grep_not_clean"
    AUDIT_CHAIN_NOT_VERIFIED = "audit_chain_not_verified"
    FINAL_STATE_NOT_DOCUMENTED = "final_state_not_documented"
    # Detection hard-stops (7)
    REAL_CREDENTIALS_PRESENT = "real_credentials_present"
    GOOGLE_ADS_API_CALLED = "google_ads_api_called"
    GCP_COMMANDS_USED = "gcp_commands_used"
    SECRET_MANAGER_CALLED = "secret_manager_called"
    OAUTH_EXECUTION_DETECTED = "oauth_execution_detected"
    NETWORK_CALL_DETECTED = "network_call_detected"
    FILESYSTEM_WRITE_DETECTED = "filesystem_write_detected"
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
    re.compile(r"ya29\.[A-Za-z0-9_\-]{5,}"),           # OAuth access token prefix
    re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}"),            # API key prefix
    re.compile(r"\bprojects/[a-zA-Z0-9\-_]+/"),         # GCP resource paths
    re.compile(r"\bsecrets/[a-zA-Z0-9\-_]+"),           # Secret Manager paths
    re.compile(r"[a-zA-Z0-9._%+\-]{2,}@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),  # email-like
    re.compile(r"\.json\b"),                             # JSON key file references
    re.compile(r"fake-v52[0-9]"),                        # fake payload sentinels (V5.20+)
    re.compile(r"\bclient_secret\b"),                    # credential field name as value
    re.compile(r"\brefresh_token\b"),                    # credential field name as value
    re.compile(r"\bdeveloper_token\b"),                  # credential field name as value
    re.compile(r"\bcustomer_id\b"),                      # account identifier as value
    re.compile(r"\blogin_customer_id\b"),                # account identifier as value
]

# ---------------------------------------------------------------------------
# Sanitized summary fields (all booleans; excludes evidence and metadata)
# ---------------------------------------------------------------------------

_SANITIZED_SUMMARY_FIELDS = (
    "live_flag_disabled",
    "approval_revoked",
    "credential_marked_revoked",
    "credential_bundle_deleted_or_revoked",
    "post_revoke_status_verified",
    "secret_status_verified",
    "live_gate_denied_after_revoke",
    "smoke_tests_passed",
    "safety_grep_clean",
    "audit_chain_verified",
    "final_state_documented",
    "real_credentials_present",
    "google_ads_api_called",
    "gcp_commands_used",
    "secret_manager_called",
    "oauth_execution_detected",
    "network_call_detected",
    "filesystem_write_detected",
)

# ---------------------------------------------------------------------------
# Required actions mapping
# ---------------------------------------------------------------------------

_REQUIRED_ACTIONS: Dict[str, str] = {
    RollbackDrillFailureCode.LIVE_FLAG_NOT_DISABLED: (
        "Confirm GOOGLE_ADS_LIVE_ENABLED=false in the server environment. "
        "Restart or drain the server to ensure live mode is inactive."
    ),
    RollbackDrillFailureCode.APPROVAL_NOT_REVOKED: (
        "Revoke the ApprovalRecord in LocalFileApprovalStore using revoke_approval(). "
        "Verify is_approval_valid() returns False."
    ),
    RollbackDrillFailureCode.CREDENTIAL_NOT_REVOKED: (
        "Mark the credential REVOKED via POST /credentials/google-ads/revoke or equivalent. "
        "Verify GET /credentials/google-ads/status returns status=revoked."
    ),
    RollbackDrillFailureCode.CREDENTIAL_BUNDLE_NOT_DELETED_OR_REVOKED: (
        "Delete or revoke the credential bundle via DELETE /credentials/google-ads "
        "(requires OPENCLAW_ADMIN_DELETE_ENABLED=true). "
        "Verify status returns credential_not_found."
    ),
    RollbackDrillFailureCode.POST_REVOKE_STATUS_NOT_VERIFIED: (
        "Verify GET /credentials/google-ads/status returns the expected post-revoke state "
        "before closing the rollback drill."
    ),
    RollbackDrillFailureCode.SECRET_STATUS_NOT_VERIFIED: (
        "Verify GCP Secret Manager state out-of-band (operator terminal, no screen recording). "
        "Confirm secret is disabled or destroyed as required."
    ),
    RollbackDrillFailureCode.LIVE_GATE_NOT_DENIED_AFTER_REVOKE: (
        "Confirm check_live_gate() returns allowed=False after revocation. "
        "The gate must deny live use before the drill is considered complete."
    ),
    RollbackDrillFailureCode.SMOKE_TESTS_NOT_PASSED: (
        "Run smoke_test_v5_credentials.sh and confirm all sections pass. "
        "Do not close the rollback drill until smoke tests are clean."
    ),
    RollbackDrillFailureCode.SAFETY_GREP_NOT_CLEAN: (
        "Run safety grep on all changed files and confirm no sensitive hits. "
        "Remove any credential values, token prefixes, or resource paths found."
    ),
    RollbackDrillFailureCode.AUDIT_CHAIN_NOT_VERIFIED: (
        "Run verify_audit_file() on all audit files produced during the drill. "
        "Confirm ok=True on all files before closing."
    ),
    RollbackDrillFailureCode.FINAL_STATE_NOT_DOCUMENTED: (
        "Document the final state: timestamp, operator name, trigger, steps taken, "
        "and final credential status. Store outside the repository."
    ),
    RollbackDrillFailureCode.REAL_CREDENTIALS_PRESENT: (
        "Real credentials must not be present in a drill. "
        "Stop immediately. Use fake/local values only."
    ),
    RollbackDrillFailureCode.GOOGLE_ADS_API_CALLED: (
        "Google Ads API must not be called during the rollback drill. "
        "Stop and revoke any live calls per the rollback runbook."
    ),
    RollbackDrillFailureCode.GCP_COMMANDS_USED: (
        "GCP commands must not be run by Claude Code. "
        "All GCP operations are operator-only and out-of-band."
    ),
    RollbackDrillFailureCode.SECRET_MANAGER_CALLED: (
        "Secret Manager must not be called during this drill. "
        "The fake/local drill uses InMemorySecretStore only."
    ),
    RollbackDrillFailureCode.OAUTH_EXECUTION_DETECTED: (
        "OAuth execution must not occur during the rollback drill. "
        "Stop and revert any OAuth flow that has been initiated."
    ),
    RollbackDrillFailureCode.NETWORK_CALL_DETECTED: (
        "Network calls are prohibited during the rollback drill validation. "
        "This validator is pure local logic only."
    ),
    RollbackDrillFailureCode.FILESYSTEM_WRITE_DETECTED: (
        "Filesystem writes are prohibited during drill validation. "
        "No credential value may be written to any local file by this validator."
    ),
    RollbackDrillFailureCode.FORBIDDEN_FIELD_PRESENT: (
        "Remove all forbidden field names from evidence and metadata."
    ),
    RollbackDrillFailureCode.FORBIDDEN_VALUE_PRESENT: (
        "Remove all forbidden value patterns from evidence and metadata."
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RollbackDrillInput:
    # Rollback step confirmations (11)
    live_flag_disabled: bool
    approval_revoked: bool
    credential_marked_revoked: bool
    credential_bundle_deleted_or_revoked: bool
    post_revoke_status_verified: bool
    secret_status_verified: bool
    live_gate_denied_after_revoke: bool
    smoke_tests_passed: bool
    safety_grep_clean: bool
    audit_chain_verified: bool
    final_state_documented: bool
    # Detection hard-stops (7; must be False to PASS)
    real_credentials_present: bool
    google_ads_api_called: bool
    gcp_commands_used: bool
    secret_manager_called: bool
    oauth_execution_detected: bool
    network_call_detected: bool
    filesystem_write_detected: bool
    # Evidence and metadata (excluded from sanitized_summary)
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackDrillResult:
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

def validate_rollback_drill(inp: RollbackDrillInput) -> RollbackDrillResult:
    """
    Validate a rollback/emergency revoke drill against all V5.20 drill conditions.

    Returns ok=True only when all rollback step confirmations pass and all
    hard-stop detection flags are False. Never reads real credentials,
    calls GCP, calls Google Ads API, writes to the filesystem, or makes
    network calls. Claude Code does not execute real rollback operations.
    """
    failure_codes: List[str] = []

    # Hard stops — detection booleans surface immediately
    if inp.real_credentials_present:
        failure_codes.append(RollbackDrillFailureCode.REAL_CREDENTIALS_PRESENT)
    if inp.google_ads_api_called:
        failure_codes.append(RollbackDrillFailureCode.GOOGLE_ADS_API_CALLED)
    if inp.gcp_commands_used:
        failure_codes.append(RollbackDrillFailureCode.GCP_COMMANDS_USED)
    if inp.secret_manager_called:
        failure_codes.append(RollbackDrillFailureCode.SECRET_MANAGER_CALLED)
    if inp.oauth_execution_detected:
        failure_codes.append(RollbackDrillFailureCode.OAUTH_EXECUTION_DETECTED)
    if inp.network_call_detected:
        failure_codes.append(RollbackDrillFailureCode.NETWORK_CALL_DETECTED)
    if inp.filesystem_write_detected:
        failure_codes.append(RollbackDrillFailureCode.FILESYSTEM_WRITE_DETECTED)

    # Rollback step confirmations
    if not inp.live_flag_disabled:
        failure_codes.append(RollbackDrillFailureCode.LIVE_FLAG_NOT_DISABLED)
    if not inp.approval_revoked:
        failure_codes.append(RollbackDrillFailureCode.APPROVAL_NOT_REVOKED)
    if not inp.credential_marked_revoked:
        failure_codes.append(RollbackDrillFailureCode.CREDENTIAL_NOT_REVOKED)
    if not inp.credential_bundle_deleted_or_revoked:
        failure_codes.append(RollbackDrillFailureCode.CREDENTIAL_BUNDLE_NOT_DELETED_OR_REVOKED)
    if not inp.post_revoke_status_verified:
        failure_codes.append(RollbackDrillFailureCode.POST_REVOKE_STATUS_NOT_VERIFIED)
    if not inp.secret_status_verified:
        failure_codes.append(RollbackDrillFailureCode.SECRET_STATUS_NOT_VERIFIED)
    if not inp.live_gate_denied_after_revoke:
        failure_codes.append(RollbackDrillFailureCode.LIVE_GATE_NOT_DENIED_AFTER_REVOKE)
    if not inp.smoke_tests_passed:
        failure_codes.append(RollbackDrillFailureCode.SMOKE_TESTS_NOT_PASSED)
    if not inp.safety_grep_clean:
        failure_codes.append(RollbackDrillFailureCode.SAFETY_GREP_NOT_CLEAN)
    if not inp.audit_chain_verified:
        failure_codes.append(RollbackDrillFailureCode.AUDIT_CHAIN_NOT_VERIFIED)
    if not inp.final_state_documented:
        failure_codes.append(RollbackDrillFailureCode.FINAL_STATE_NOT_DOCUMENTED)

    # Evidence and metadata forbidden field/value checks
    failure_codes.extend(_check_mapping_for_forbidden(
        inp.evidence,
        RollbackDrillFailureCode.FORBIDDEN_FIELD_PRESENT,
        RollbackDrillFailureCode.FORBIDDEN_VALUE_PRESENT,
    ))
    failure_codes.extend(_check_mapping_for_forbidden(
        inp.metadata,
        RollbackDrillFailureCode.FORBIDDEN_FIELD_PRESENT,
        RollbackDrillFailureCode.FORBIDDEN_VALUE_PRESENT,
    ))

    ok = len(failure_codes) == 0
    decision = RollbackDrillDecision.PASS if ok else RollbackDrillDecision.FAIL

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

    return RollbackDrillResult(
        ok=ok,
        decision=decision,
        failure_codes=failure_codes,
        required_actions=required_actions,
        sanitized_summary=sanitized_summary,
    )

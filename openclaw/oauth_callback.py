"""
V5.21 Phase 4 — OAuth callback and token-exchange boundary design validator.

Pure local logic. No GCP calls. No Google Ads API calls. No OAuth execution.
No real callback URL received. No auth code received. No token exchange.
No real client IDs, secrets, tokens, resource paths, or credential values.
No os.environ reads. No filesystem I/O. No network calls. No browser interaction.
Claude Code does not receive OAuth callback URLs and does not execute token exchange.
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

class OAuthCallbackDesignDecision:
    PASS = "PASS"
    FAIL = "FAIL"


class OAuthCallbackDesignFailureCode:
    # Hard-stop detection — must all be False (18)
    OAUTH_EXECUTION_DETECTED = "oauth_execution_detected"
    CALLBACK_URL_RECEIVED = "callback_url_received"
    CALLBACK_URL_LOGGED = "callback_url_logged"
    CALLBACK_URL_COMMITTED = "callback_url_committed"
    AUTH_CODE_RECEIVED = "auth_code_received"
    AUTH_CODE_LOGGED = "auth_code_logged"
    AUTH_CODE_COMMITTED = "auth_code_committed"
    AUTH_CODE_PASTED_TO_CHAT = "auth_code_pasted_to_chat"
    TOKEN_EXCHANGE_ATTEMPTED = "token_exchange_attempted"
    TOKEN_RESPONSE_RECEIVED = "token_response_received"
    TOKEN_RESPONSE_LOGGED = "token_response_logged"
    TOKEN_RESPONSE_COMMITTED = "token_response_committed"
    REFRESH_TOKEN_PRESENT = "refresh_token_present"
    ACCESS_TOKEN_PRESENT = "access_token_present"
    CLIENT_SECRET_PRESENT = "client_secret_present"
    REAL_CLIENT_ID_PRESENT = "real_client_id_present"
    REDIRECT_URI_VALUE_PRESENT = "redirect_uri_value_present"
    STATE_VALUE_PRESENT = "state_value_present"
    # Boundary requirements — must all be True (12)
    STATE_VERIFICATION_MISSING = "state_verification_missing"
    STATE_NOT_BOUND_TO_CEREMONY = "state_not_bound_to_ceremony"
    STATE_REUSE_NOT_BLOCKED = "state_reuse_not_blocked"
    TOKEN_EXCHANGE_APPROVAL_MISSING = "token_exchange_approval_missing"
    TOKEN_EXCHANGE_WINDOW_MISSING = "token_exchange_window_missing"
    SECURE_CHANNEL_MISSING = "secure_channel_missing"
    REDACTED_STATUS_VERIFICATION_MISSING = "redacted_status_verification_missing"
    STORAGE_BOUNDARY_MISSING = "storage_boundary_missing"
    ROLLBACK_BOUNDARY_MISSING = "rollback_boundary_missing"
    AUDIT_REQUIREMENT_MISSING = "audit_requirement_missing"
    EVIDENCE_REQUIREMENT_MISSING = "evidence_requirement_missing"
    OPERATOR_CONFIRMATION_MISSING = "operator_confirmation_missing"
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
# shaped values; includes all boolean design checks plus decision metadata)
# ---------------------------------------------------------------------------

_SANITIZED_SUMMARY_FIELDS = (
    "oauth_execution_detected",
    "callback_url_received",
    "callback_url_logged",
    "callback_url_committed",
    "auth_code_received",
    "auth_code_logged",
    "auth_code_committed",
    "auth_code_pasted_to_chat",
    "token_exchange_attempted",
    "token_response_received",
    "token_response_logged",
    "token_response_committed",
    "refresh_token_present",
    "access_token_present",
    "client_secret_present",
    "real_client_id_present",
    "redirect_uri_value_present",
    "state_value_present",
    "state_verification_present",
    "state_bound_to_ceremony",
    "state_reuse_blocked",
    "token_exchange_approval_present",
    "token_exchange_window_present",
    "secure_channel_present",
    "redacted_status_verification_present",
    "storage_boundary_present",
    "rollback_boundary_present",
    "audit_requirement_present",
    "evidence_requirement_present",
    "operator_confirmation_present",
)

# ---------------------------------------------------------------------------
# Required actions mapping
# ---------------------------------------------------------------------------

_REQUIRED_ACTIONS: Dict[str, str] = {
    OAuthCallbackDesignFailureCode.OAUTH_EXECUTION_DETECTED: (
        "OAuth execution must not occur during Phase 4. "
        "Stop immediately. No OAuth flow may be initiated by this validator."
    ),
    OAuthCallbackDesignFailureCode.CALLBACK_URL_RECEIVED: (
        "A real callback URL must not be received by this validator. "
        "Callback URL handling is deferred to a separately authorized future ceremony step."
    ),
    OAuthCallbackDesignFailureCode.CALLBACK_URL_LOGGED: (
        "A callback URL must never be logged to a file or terminal. "
        "Stop immediately. Remove any callback URL from logs before proceeding."
    ),
    OAuthCallbackDesignFailureCode.CALLBACK_URL_COMMITTED: (
        "A callback URL must never be committed to the repository. "
        "Stop immediately. Remove the commit or file before proceeding."
    ),
    OAuthCallbackDesignFailureCode.AUTH_CODE_RECEIVED: (
        "A real authorization code must not be received by this validator. "
        "Auth code handling is deferred to a separately authorized future ceremony step."
    ),
    OAuthCallbackDesignFailureCode.AUTH_CODE_LOGGED: (
        "An authorization code must never be logged to a file or terminal. "
        "Stop immediately. Remove any auth code from logs before proceeding."
    ),
    OAuthCallbackDesignFailureCode.AUTH_CODE_COMMITTED: (
        "An authorization code must never be committed to the repository. "
        "Stop immediately. Remove the commit or file before proceeding."
    ),
    OAuthCallbackDesignFailureCode.AUTH_CODE_PASTED_TO_CHAT: (
        "An authorization code must never be pasted into chat. "
        "Stop immediately. Treat the code as compromised and revoke it."
    ),
    OAuthCallbackDesignFailureCode.TOKEN_EXCHANGE_ATTEMPTED: (
        "Token exchange must not be attempted during Phase 4. "
        "Stop immediately. Token exchange requires separate explicit operator approval."
    ),
    OAuthCallbackDesignFailureCode.TOKEN_RESPONSE_RECEIVED: (
        "A real token response must not be received by this validator. "
        "Token response handling is deferred to a separately authorized future ceremony step."
    ),
    OAuthCallbackDesignFailureCode.TOKEN_RESPONSE_LOGGED: (
        "A token response must never be logged to a file or terminal. "
        "Stop immediately. Remove any token response from logs before proceeding."
    ),
    OAuthCallbackDesignFailureCode.TOKEN_RESPONSE_COMMITTED: (
        "A token response must never be committed to the repository. "
        "Stop immediately. Remove the commit or file before proceeding."
    ),
    OAuthCallbackDesignFailureCode.REFRESH_TOKEN_PRESENT: (
        "A real refresh token must not be present in this validator input. "
        "Refresh tokens must never appear in validator inputs, logs, docs, or chat."
    ),
    OAuthCallbackDesignFailureCode.ACCESS_TOKEN_PRESENT: (
        "A real access token must not be present in this validator input. "
        "Access tokens must never appear in validator inputs, logs, docs, or chat."
    ),
    OAuthCallbackDesignFailureCode.CLIENT_SECRET_PRESENT: (
        "A real client secret must not be present in this validator input. "
        "Client secrets must never appear in validator inputs, logs, docs, or chat."
    ),
    OAuthCallbackDesignFailureCode.REAL_CLIENT_ID_PRESENT: (
        "A real OAuth client ID must not be present in this validator input. "
        "Use only design metadata and boolean flags. Remove real credential values."
    ),
    OAuthCallbackDesignFailureCode.REDIRECT_URI_VALUE_PRESENT: (
        "A real redirect URI value must not be present in this validator input. "
        "Use only design metadata and boolean flags."
    ),
    OAuthCallbackDesignFailureCode.STATE_VALUE_PRESENT: (
        "A real OAuth state value must not be present in this validator input. "
        "State values must be handled out-of-band only."
    ),
    OAuthCallbackDesignFailureCode.STATE_VERIFICATION_MISSING: (
        "State parameter verification must be on record before any callback is handled. "
        "Confirm state_verification_present=True."
    ),
    OAuthCallbackDesignFailureCode.STATE_NOT_BOUND_TO_CEREMONY: (
        "The state parameter must be bound to this specific ceremony instance. "
        "Ensure the state verification confirms ceremony-specific binding."
    ),
    OAuthCallbackDesignFailureCode.STATE_REUSE_NOT_BLOCKED: (
        "State parameter reuse must be blocked before any callback is handled. "
        "Ensure state is invalidated immediately after first use."
    ),
    OAuthCallbackDesignFailureCode.TOKEN_EXCHANGE_APPROVAL_MISSING: (
        "Separate explicit operator approval for token exchange must be on record. "
        "Obtain and record approval before any token exchange step."
    ),
    OAuthCallbackDesignFailureCode.TOKEN_EXCHANGE_WINDOW_MISSING: (
        "A token exchange execution window must be defined before any callback is handled. "
        "Specify start time, end time, and maximum duration out-of-band."
    ),
    OAuthCallbackDesignFailureCode.SECURE_CHANNEL_MISSING: (
        "A secure channel for auth code and token handling must be defined. "
        "Confirm the secure channel design is approved out-of-band."
    ),
    OAuthCallbackDesignFailureCode.REDACTED_STATUS_VERIFICATION_MISSING: (
        "Redacted status verification must be required after token exchange. "
        "Confirm redacted_status_verification_present=True before proceeding."
    ),
    OAuthCallbackDesignFailureCode.STORAGE_BOUNDARY_MISSING: (
        "A credential storage boundary must be defined before any token exchange. "
        "Confirm the storage boundary design is approved out-of-band."
    ),
    OAuthCallbackDesignFailureCode.ROLLBACK_BOUNDARY_MISSING: (
        "A rollback boundary must be defined before any callback or token exchange step. "
        "Confirm the rollback plan is approved and accessible."
    ),
    OAuthCallbackDesignFailureCode.AUDIT_REQUIREMENT_MISSING: (
        "An audit requirement must be declared before any callback or token exchange step. "
        "Define audit events and storage path out-of-band."
    ),
    OAuthCallbackDesignFailureCode.EVIDENCE_REQUIREMENT_MISSING: (
        "An evidence package requirement must be declared before any callback gate. "
        "Define the evidence package path and required contents out-of-band."
    ),
    OAuthCallbackDesignFailureCode.OPERATOR_CONFIRMATION_MISSING: (
        "Operator confirmation must be on record before any callback boundary review. "
        "Obtain and record operator confirmation."
    ),
    OAuthCallbackDesignFailureCode.FORBIDDEN_FIELD_PRESENT: (
        "Remove all forbidden field names from evidence and metadata. "
        "Credential-shaped keys must not appear in validator inputs."
    ),
    OAuthCallbackDesignFailureCode.FORBIDDEN_VALUE_PRESENT: (
        "Remove all forbidden value patterns from evidence and metadata. "
        "Token-shaped, URL-shaped, and resource-path-shaped values must not appear."
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class OAuthCallbackDesignInput:
    # Hard-stop detection booleans (must all be False to PASS)
    oauth_execution_detected: bool
    callback_url_received: bool
    callback_url_logged: bool
    callback_url_committed: bool
    auth_code_received: bool
    auth_code_logged: bool
    auth_code_committed: bool
    auth_code_pasted_to_chat: bool
    token_exchange_attempted: bool
    token_response_received: bool
    token_response_logged: bool
    token_response_committed: bool
    refresh_token_present: bool
    access_token_present: bool
    client_secret_present: bool
    real_client_id_present: bool
    redirect_uri_value_present: bool
    state_value_present: bool
    # Boundary requirements (must all be True to PASS)
    state_verification_present: bool
    state_bound_to_ceremony: bool
    state_reuse_blocked: bool
    token_exchange_approval_present: bool
    token_exchange_window_present: bool
    secure_channel_present: bool
    redacted_status_verification_present: bool
    storage_boundary_present: bool
    rollback_boundary_present: bool
    audit_requirement_present: bool
    evidence_requirement_present: bool
    operator_confirmation_present: bool
    # Evidence and metadata (excluded from sanitized_summary)
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OAuthCallbackDesignResult:
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

def validate_oauth_callback_design(inp: OAuthCallbackDesignInput) -> OAuthCallbackDesignResult:
    """
    Validate the design metadata for a future OAuth callback and token-exchange boundary.

    Returns ok=True only when all boundary checks pass, all hard-stop detections are
    False, and evidence/metadata contain no forbidden field names or value patterns.

    Never receives a real callback URL. Never processes a real authorization code.
    Never attempts token exchange. Never calls Google OAuth token endpoint, Google Ads API,
    GCP, or Secret Manager. Never reads real credentials. Never makes network calls.
    Never writes to the filesystem.
    Claude Code does not receive OAuth callback URLs and does not execute token exchange.
    """
    failure_codes: List[str] = []

    # Hard-stop detection — must all be False
    if inp.oauth_execution_detected:
        failure_codes.append(OAuthCallbackDesignFailureCode.OAUTH_EXECUTION_DETECTED)
    if inp.callback_url_received:
        failure_codes.append(OAuthCallbackDesignFailureCode.CALLBACK_URL_RECEIVED)
    if inp.callback_url_logged:
        failure_codes.append(OAuthCallbackDesignFailureCode.CALLBACK_URL_LOGGED)
    if inp.callback_url_committed:
        failure_codes.append(OAuthCallbackDesignFailureCode.CALLBACK_URL_COMMITTED)
    if inp.auth_code_received:
        failure_codes.append(OAuthCallbackDesignFailureCode.AUTH_CODE_RECEIVED)
    if inp.auth_code_logged:
        failure_codes.append(OAuthCallbackDesignFailureCode.AUTH_CODE_LOGGED)
    if inp.auth_code_committed:
        failure_codes.append(OAuthCallbackDesignFailureCode.AUTH_CODE_COMMITTED)
    if inp.auth_code_pasted_to_chat:
        failure_codes.append(OAuthCallbackDesignFailureCode.AUTH_CODE_PASTED_TO_CHAT)
    if inp.token_exchange_attempted:
        failure_codes.append(OAuthCallbackDesignFailureCode.TOKEN_EXCHANGE_ATTEMPTED)
    if inp.token_response_received:
        failure_codes.append(OAuthCallbackDesignFailureCode.TOKEN_RESPONSE_RECEIVED)
    if inp.token_response_logged:
        failure_codes.append(OAuthCallbackDesignFailureCode.TOKEN_RESPONSE_LOGGED)
    if inp.token_response_committed:
        failure_codes.append(OAuthCallbackDesignFailureCode.TOKEN_RESPONSE_COMMITTED)
    if inp.refresh_token_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.REFRESH_TOKEN_PRESENT)
    if inp.access_token_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.ACCESS_TOKEN_PRESENT)
    if inp.client_secret_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.CLIENT_SECRET_PRESENT)
    if inp.real_client_id_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.REAL_CLIENT_ID_PRESENT)
    if inp.redirect_uri_value_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.REDIRECT_URI_VALUE_PRESENT)
    if inp.state_value_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.STATE_VALUE_PRESENT)

    # Boundary requirements — must all be True
    if not inp.state_verification_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.STATE_VERIFICATION_MISSING)
    if not inp.state_bound_to_ceremony:
        failure_codes.append(OAuthCallbackDesignFailureCode.STATE_NOT_BOUND_TO_CEREMONY)
    if not inp.state_reuse_blocked:
        failure_codes.append(OAuthCallbackDesignFailureCode.STATE_REUSE_NOT_BLOCKED)
    if not inp.token_exchange_approval_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.TOKEN_EXCHANGE_APPROVAL_MISSING)
    if not inp.token_exchange_window_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.TOKEN_EXCHANGE_WINDOW_MISSING)
    if not inp.secure_channel_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.SECURE_CHANNEL_MISSING)
    if not inp.redacted_status_verification_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.REDACTED_STATUS_VERIFICATION_MISSING)
    if not inp.storage_boundary_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.STORAGE_BOUNDARY_MISSING)
    if not inp.rollback_boundary_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.ROLLBACK_BOUNDARY_MISSING)
    if not inp.audit_requirement_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.AUDIT_REQUIREMENT_MISSING)
    if not inp.evidence_requirement_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.EVIDENCE_REQUIREMENT_MISSING)
    if not inp.operator_confirmation_present:
        failure_codes.append(OAuthCallbackDesignFailureCode.OPERATOR_CONFIRMATION_MISSING)

    # Forbidden field/value detection in evidence and metadata
    for mapping in (inp.evidence, inp.metadata):
        failure_codes.extend(
            _check_mapping_for_forbidden(
                mapping,
                OAuthCallbackDesignFailureCode.FORBIDDEN_FIELD_PRESENT,
                OAuthCallbackDesignFailureCode.FORBIDDEN_VALUE_PRESENT,
            )
        )

    ok = len(failure_codes) == 0
    decision = OAuthCallbackDesignDecision.PASS if ok else OAuthCallbackDesignDecision.FAIL
    required_actions = [_REQUIRED_ACTIONS[c] for c in failure_codes if c in _REQUIRED_ACTIONS]

    sanitized_summary: Dict[str, Any] = {
        f: getattr(inp, f) for f in _SANITIZED_SUMMARY_FIELDS
    }
    sanitized_summary["decision"] = decision
    sanitized_summary["ok"] = ok
    sanitized_summary["failure_count"] = len(failure_codes)

    return OAuthCallbackDesignResult(
        ok=ok,
        decision=decision,
        failure_codes=failure_codes,
        required_actions=required_actions,
        sanitized_summary=sanitized_summary,
    )

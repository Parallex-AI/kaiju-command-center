"""
V5.21 Phase 3 — OAuth authorization URL design validator.

Pure local logic. No GCP calls. No Google Ads API calls. No OAuth execution.
No real authorization URL generation. No browser interaction. No network calls.
No secrets, tokens, credential values, resource paths, or real client IDs.
No os.environ reads. No filesystem I/O.
Claude Code does not generate real OAuth URLs and does not execute real OAuth flows.
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

class OAuthAuthUrlDesignDecision:
    PASS = "PASS"
    FAIL = "FAIL"


class OAuthAuthUrlDesignFailureCode:
    # Hard-stop detection (8)
    OAUTH_EXECUTION_DETECTED = "oauth_execution_detected"
    AUTHORIZATION_URL_GENERATED = "authorization_url_generated"
    BROWSER_OPEN_DETECTED = "browser_open_detected"
    REAL_CLIENT_ID_PRESENT = "real_client_id_present"
    CLIENT_SECRET_PRESENT = "client_secret_present"
    AUTH_CODE_PRESENT = "auth_code_present"
    TOKEN_PRESENT = "token_present"
    # Redirect URI (2)
    REDIRECT_URI_MISSING = "redirect_uri_missing"
    REDIRECT_URI_NOT_APPROVED = "redirect_uri_not_approved"
    # Scopes (4)
    SCOPES_MISSING = "scopes_missing"
    SCOPES_NOT_APPROVED = "scopes_not_approved"
    BROAD_SCOPE_DETECTED = "broad_scope_detected"
    UNEXPECTED_SCOPE_PRESENT = "unexpected_scope_present"
    # State parameter (3)
    STATE_MISSING = "state_missing"
    STATE_NOT_ONE_TIME_USE = "state_not_one_time_use"
    STATE_NOT_BOUND_TO_CEREMONY = "state_not_bound_to_ceremony"
    # OAuth params (3)
    PROMPT_NOT_CONSENT = "prompt_not_consent"
    ACCESS_TYPE_NOT_OFFLINE = "access_type_not_offline"
    INCLUDE_GRANTED_SCOPES_NOT_FALSE = "include_granted_scopes_not_false"
    # Approval and ceremony (5)
    APPROVAL_MISSING = "approval_missing"
    APPROVAL_NOT_VALID = "approval_not_valid"
    EXECUTION_WINDOW_MISSING = "execution_window_missing"
    OPERATOR_CONFIRMATION_MISSING = "operator_confirmation_missing"
    EVIDENCE_REQUIREMENT_MISSING = "evidence_requirement_missing"
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
    "authorization_url_generated",
    "browser_open_detected",
    "real_client_id_present",
    "client_secret_present",
    "auth_code_present",
    "token_present",
    "redirect_uri_present",
    "redirect_uri_approved",
    "scopes_present",
    "scopes_approved",
    "broad_scope_detected",
    "unexpected_scope_present",
    "state_present",
    "state_one_time_use",
    "state_bound_to_ceremony",
    "prompt_is_consent",
    "access_type_is_offline",
    "include_granted_scopes_is_false",
    "approval_present",
    "approval_valid",
    "execution_window_present",
    "operator_confirmation_present",
    "evidence_requirement_present",
)

# ---------------------------------------------------------------------------
# Required actions mapping
# ---------------------------------------------------------------------------

_REQUIRED_ACTIONS: Dict[str, str] = {
    OAuthAuthUrlDesignFailureCode.OAUTH_EXECUTION_DETECTED: (
        "OAuth execution must not occur during Phase 3. "
        "Stop immediately. No OAuth flow may be initiated by this validator."
    ),
    OAuthAuthUrlDesignFailureCode.AUTHORIZATION_URL_GENERATED: (
        "A real authorization URL must not be generated by this validator. "
        "URL generation is deferred to a separately authorized future ceremony step."
    ),
    OAuthAuthUrlDesignFailureCode.BROWSER_OPEN_DETECTED: (
        "Browser interaction must not occur during Phase 3. "
        "Stop immediately. No browser flow may be opened by this validator."
    ),
    OAuthAuthUrlDesignFailureCode.REAL_CLIENT_ID_PRESENT: (
        "A real OAuth client ID must not be present in this validator input. "
        "Use only design metadata and boolean flags. Remove real credential values."
    ),
    OAuthAuthUrlDesignFailureCode.CLIENT_SECRET_PRESENT: (
        "A real client secret must not be present in this validator input. "
        "Client secrets must never appear in validator inputs, docs, or chat."
    ),
    OAuthAuthUrlDesignFailureCode.AUTH_CODE_PRESENT: (
        "An authorization code must not be present in this validator input. "
        "Auth codes must be handled only through approved secure channels, never in validators."
    ),
    OAuthAuthUrlDesignFailureCode.TOKEN_PRESENT: (
        "A token value must not be present in this validator input. "
        "Tokens must never appear in validator inputs, logs, docs, or chat."
    ),
    OAuthAuthUrlDesignFailureCode.REDIRECT_URI_MISSING: (
        "A redirect URI must be declared in the URL design before any ceremony proceeds. "
        "Define and approve the redirect URI out-of-band."
    ),
    OAuthAuthUrlDesignFailureCode.REDIRECT_URI_NOT_APPROVED: (
        "The redirect URI must be reviewed and approved before the URL review gate. "
        "Obtain approval out-of-band and confirm redirect_uri_approved=True."
    ),
    OAuthAuthUrlDesignFailureCode.SCOPES_MISSING: (
        "OAuth scopes must be declared in the URL design. "
        "Define the required scope list out-of-band before the ceremony."
    ),
    OAuthAuthUrlDesignFailureCode.SCOPES_NOT_APPROVED: (
        "The scope list must be reviewed and approved before any authorization URL is generated. "
        "Confirm scope approval out-of-band and set scopes_approved=True."
    ),
    OAuthAuthUrlDesignFailureCode.BROAD_SCOPE_DETECTED: (
        "A broad or overpermissioned scope was detected. "
        "Remove it and request only the minimum required scopes."
    ),
    OAuthAuthUrlDesignFailureCode.UNEXPECTED_SCOPE_PRESENT: (
        "An unexpected scope not in the approved list was detected. "
        "Remove it. Scope mismatch is a stop condition."
    ),
    OAuthAuthUrlDesignFailureCode.STATE_MISSING: (
        "A CSRF state parameter must be present in the URL design. "
        "Define a one-time-use ceremony-bound state parameter."
    ),
    OAuthAuthUrlDesignFailureCode.STATE_NOT_ONE_TIME_USE: (
        "The state parameter must be single-use only. "
        "Ensure the state is generated fresh for each ceremony and cannot be reused."
    ),
    OAuthAuthUrlDesignFailureCode.STATE_NOT_BOUND_TO_CEREMONY: (
        "The state parameter must be bound to this specific ceremony instance. "
        "Ensure the state includes ceremony-specific context."
    ),
    OAuthAuthUrlDesignFailureCode.PROMPT_NOT_CONSENT: (
        "The prompt parameter must be set to 'consent' for the authorization URL. "
        "Set prompt=consent in the URL design."
    ),
    OAuthAuthUrlDesignFailureCode.ACCESS_TYPE_NOT_OFFLINE: (
        "The access_type parameter must be 'offline' to obtain a refresh token. "
        "Set access_type=offline in the URL design."
    ),
    OAuthAuthUrlDesignFailureCode.INCLUDE_GRANTED_SCOPES_NOT_FALSE: (
        "include_granted_scopes must be false to prevent scope accumulation. "
        "Set include_granted_scopes=false in the URL design."
    ),
    OAuthAuthUrlDesignFailureCode.APPROVAL_MISSING: (
        "An approval record must be present before any URL design review proceeds. "
        "Provide an ApprovalRecord via LocalFileApprovalStore."
    ),
    OAuthAuthUrlDesignFailureCode.APPROVAL_NOT_VALID: (
        "The approval record must be APPROVED and not expired. "
        "Check is_approval_valid() and renew if expired."
    ),
    OAuthAuthUrlDesignFailureCode.EXECUTION_WINDOW_MISSING: (
        "An execution window must be defined before any ceremony step proceeds. "
        "Specify start time, end time, and maximum duration out-of-band."
    ),
    OAuthAuthUrlDesignFailureCode.OPERATOR_CONFIRMATION_MISSING: (
        "Operator confirmation must be on record before any URL design review proceeds. "
        "Obtain and record operator confirmation."
    ),
    OAuthAuthUrlDesignFailureCode.EVIDENCE_REQUIREMENT_MISSING: (
        "An evidence package requirement must be declared before the URL review gate. "
        "Define the evidence package path and required contents out-of-band."
    ),
    OAuthAuthUrlDesignFailureCode.FORBIDDEN_FIELD_PRESENT: (
        "Remove all forbidden field names from evidence and metadata. "
        "Credential-shaped keys must not appear in validator inputs."
    ),
    OAuthAuthUrlDesignFailureCode.FORBIDDEN_VALUE_PRESENT: (
        "Remove all forbidden value patterns from evidence and metadata. "
        "Token-shaped, URL-shaped, and resource-path-shaped values must not appear."
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class OAuthAuthUrlDesignInput:
    # Hard-stop detection booleans (must all be False to PASS)
    oauth_execution_detected: bool
    authorization_url_generated: bool
    browser_open_detected: bool
    real_client_id_present: bool
    client_secret_present: bool
    auth_code_present: bool
    token_present: bool
    # URL design checks (must all be True to PASS)
    redirect_uri_present: bool
    redirect_uri_approved: bool
    scopes_present: bool
    scopes_approved: bool
    # Scope safety (must all be False to PASS)
    broad_scope_detected: bool
    unexpected_scope_present: bool
    # State parameter (must all be True to PASS)
    state_present: bool
    state_one_time_use: bool
    state_bound_to_ceremony: bool
    # OAuth parameter design (must all be True to PASS)
    prompt_is_consent: bool
    access_type_is_offline: bool
    include_granted_scopes_is_false: bool
    # Ceremony controls (must all be True to PASS)
    approval_present: bool
    approval_valid: bool
    execution_window_present: bool
    operator_confirmation_present: bool
    evidence_requirement_present: bool
    # Evidence and metadata (excluded from sanitized_summary)
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OAuthAuthUrlDesignResult:
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

def validate_oauth_auth_url_design(inp: OAuthAuthUrlDesignInput) -> OAuthAuthUrlDesignResult:
    """
    Validate the design metadata for a future Google OAuth authorization URL ceremony.

    Returns ok=True only when all design checks pass, all hard-stop detections are
    False, and evidence/metadata contain no forbidden field names or value patterns.

    Never generates a real authorization URL. Never opens a browser. Never calls
    Google OAuth, Google Ads API, GCP, or Secret Manager. Never reads real credentials.
    Never makes network calls. Never writes to the filesystem.
    Claude Code does not generate real OAuth URLs and does not execute real OAuth flows.
    """
    failure_codes: List[str] = []

    # Hard-stop detection — must all be False
    if inp.oauth_execution_detected:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.OAUTH_EXECUTION_DETECTED)
    if inp.authorization_url_generated:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.AUTHORIZATION_URL_GENERATED)
    if inp.browser_open_detected:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.BROWSER_OPEN_DETECTED)
    if inp.real_client_id_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.REAL_CLIENT_ID_PRESENT)
    if inp.client_secret_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.CLIENT_SECRET_PRESENT)
    if inp.auth_code_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.AUTH_CODE_PRESENT)
    if inp.token_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.TOKEN_PRESENT)

    # URL design checks — must be True
    if not inp.redirect_uri_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.REDIRECT_URI_MISSING)
    if not inp.redirect_uri_approved:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.REDIRECT_URI_NOT_APPROVED)
    if not inp.scopes_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.SCOPES_MISSING)
    if not inp.scopes_approved:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.SCOPES_NOT_APPROVED)

    # Scope safety — must be False
    if inp.broad_scope_detected:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.BROAD_SCOPE_DETECTED)
    if inp.unexpected_scope_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.UNEXPECTED_SCOPE_PRESENT)

    # State parameter — must be True
    if not inp.state_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.STATE_MISSING)
    if not inp.state_one_time_use:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.STATE_NOT_ONE_TIME_USE)
    if not inp.state_bound_to_ceremony:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.STATE_NOT_BOUND_TO_CEREMONY)

    # OAuth parameter design — must be True
    if not inp.prompt_is_consent:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.PROMPT_NOT_CONSENT)
    if not inp.access_type_is_offline:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.ACCESS_TYPE_NOT_OFFLINE)
    if not inp.include_granted_scopes_is_false:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.INCLUDE_GRANTED_SCOPES_NOT_FALSE)

    # Ceremony controls — must be True
    if not inp.approval_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.APPROVAL_MISSING)
    if not inp.approval_valid:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.APPROVAL_NOT_VALID)
    if not inp.execution_window_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.EXECUTION_WINDOW_MISSING)
    if not inp.operator_confirmation_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.OPERATOR_CONFIRMATION_MISSING)
    if not inp.evidence_requirement_present:
        failure_codes.append(OAuthAuthUrlDesignFailureCode.EVIDENCE_REQUIREMENT_MISSING)

    # Forbidden field/value detection in evidence and metadata
    for mapping in (inp.evidence, inp.metadata):
        failure_codes.extend(
            _check_mapping_for_forbidden(
                mapping,
                OAuthAuthUrlDesignFailureCode.FORBIDDEN_FIELD_PRESENT,
                OAuthAuthUrlDesignFailureCode.FORBIDDEN_VALUE_PRESENT,
            )
        )

    ok = len(failure_codes) == 0
    decision = OAuthAuthUrlDesignDecision.PASS if ok else OAuthAuthUrlDesignDecision.FAIL
    required_actions = [_REQUIRED_ACTIONS[c] for c in failure_codes if c in _REQUIRED_ACTIONS]

    sanitized_summary: Dict[str, Any] = {
        f: getattr(inp, f) for f in _SANITIZED_SUMMARY_FIELDS
    }
    sanitized_summary["decision"] = decision
    sanitized_summary["ok"] = ok
    sanitized_summary["failure_count"] = len(failure_codes)

    return OAuthAuthUrlDesignResult(
        ok=ok,
        decision=decision,
        failure_codes=failure_codes,
        required_actions=required_actions,
        sanitized_summary=sanitized_summary,
    )

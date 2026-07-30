import sys
from enum import Enum
from pathlib import Path
from typing import Optional

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)

from config import get_config
from schemas import make_error


# ---------------------------------------------------------------------------
# Scopes
# ---------------------------------------------------------------------------

class AdminScope(str, Enum):
    READ = "read"
    WRITE = "write"
    VALIDATE = "validate"
    ROTATE = "rotate"
    DELETE = "delete"
    ADMIN = "admin"


def resolve_token_scope(token: str, config) -> Optional[AdminScope]:
    """
    Return the AdminScope for a token, or None if the token is not recognized.

    Priority: admin_keys > read_keys > api_keys (backward-compat READ fallback).
    """
    if token in config.admin_keys:
        return AdminScope.ADMIN
    if token in config.read_keys:
        return AdminScope.READ
    if token in config.api_keys:
        return AdminScope.READ
    return None


def scope_allows(actual: AdminScope, required: AdminScope) -> bool:
    """Return True if actual scope satisfies the required scope."""
    if actual == AdminScope.ADMIN:
        return True
    return actual == required


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    if not authorization_header or not authorization_header.strip():
        return None
    parts = authorization_header.strip().split(None, 1)
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token if token else None


# ---------------------------------------------------------------------------
# Auth validation
# ---------------------------------------------------------------------------

def validate_api_auth(
    headers: Optional[dict] = None,
    required_scope: Optional[AdminScope] = None,
    config=None,
) -> tuple:
    """
    Validate API auth and optionally enforce a required scope.

    Returns (True, []) on success.
    Returns (False, errors) on failure — error code is one of:
      - auth_not_configured: auth enabled but no keys configured
      - unauthorized: missing or invalid token (→ HTTP 401)
      - scope_not_granted: valid token but insufficient scope (→ HTTP 403)

    When required_scope is None, only token presence/validity is checked
    (backward-compatible with callers that do not pass a scope).
    """
    if config is None:
        config = get_config()

    if not config.api_auth_enabled:
        return True, []

    all_keys_empty = not config.admin_keys and not config.read_keys and not config.api_keys
    if all_keys_empty:
        return False, [make_error(
            "auth_not_configured",
            "API auth is enabled but no API keys are configured. Contact the administrator.",
            recoverable=False,
            source="openclaw",
        )]

    authorization = (headers or {}).get("authorization") or (headers or {}).get("Authorization")
    token = extract_bearer_token(authorization)

    if token is None:
        return False, [make_error(
            "unauthorized",
            "Missing or malformed Authorization header. Expected: Authorization: Bearer <token>",
            recoverable=True,
            source="openclaw",
        )]

    actual_scope = resolve_token_scope(token, config)

    if actual_scope is None:
        return False, [make_error(
            "unauthorized",
            "Invalid bearer token.",
            recoverable=True,
            source="openclaw",
        )]

    if required_scope is None:
        return True, []

    required = AdminScope(required_scope) if not isinstance(required_scope, AdminScope) else required_scope
    if not scope_allows(actual_scope, required):
        return False, [make_error(
            "scope_not_granted",
            f"Token does not have the required scope for this operation.",
            recoverable=False,
            source="openclaw",
        )]

    return True, []

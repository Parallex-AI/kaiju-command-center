import sys
from pathlib import Path
from typing import Optional

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)

from config import get_config
from schemas import make_error


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

def validate_api_auth(headers: Optional[dict] = None, config=None) -> tuple:
    if config is None:
        config = get_config()

    if not config.api_auth_enabled:
        return True, []

    # Auth enabled but no keys configured — misconfiguration, not caller error
    if not config.api_keys:
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

    if token not in config.api_keys:
        return False, [make_error(
            "unauthorized",
            "Invalid bearer token.",
            recoverable=True,
            source="openclaw",
        )]

    return True, []

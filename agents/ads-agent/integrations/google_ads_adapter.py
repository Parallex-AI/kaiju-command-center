import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.schemas import make_integration_error

_REQUIRED_FIELDS = (
    "developer_token",
    "client_id",
    "client_secret",
    "refresh_token",
    "customer_id",
)


@dataclass
class GoogleAdsCredentials:
    developer_token: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]
    refresh_token: Optional[str]
    login_customer_id: Optional[str]
    customer_id: Optional[str]


def is_google_ads_live_enabled() -> bool:
    raw = os.getenv("GOOGLE_ADS_LIVE_ENABLED", "").strip().lower()
    return raw in ("true", "1", "yes", "on")


def load_google_ads_credentials() -> GoogleAdsCredentials:
    def _env(key: str) -> Optional[str]:
        val = os.getenv(key, "").strip()
        return val if val else None

    return GoogleAdsCredentials(
        developer_token=_env("GOOGLE_ADS_DEVELOPER_TOKEN"),
        client_id=_env("GOOGLE_ADS_CLIENT_ID"),
        client_secret=_env("GOOGLE_ADS_CLIENT_SECRET"),
        refresh_token=_env("GOOGLE_ADS_REFRESH_TOKEN"),
        login_customer_id=_env("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        customer_id=_env("GOOGLE_ADS_CUSTOMER_ID"),
    )


def validate_google_ads_credentials(
    credentials: GoogleAdsCredentials,
) -> Tuple[bool, List[dict]]:
    missing = [
        field
        for field in _REQUIRED_FIELDS
        if not getattr(credentials, field, None)
    ]

    if not missing:
        return True, []

    error = make_integration_error(
        code="credentials_missing",
        message=f"Missing required Google Ads credential fields: {', '.join(missing)}",
        recoverable=True,
        source="google_ads",
    )
    return False, [error]


def redacted_google_ads_credentials(credentials: GoogleAdsCredentials) -> dict:
    fields = (
        "developer_token",
        "client_id",
        "client_secret",
        "refresh_token",
        "login_customer_id",
        "customer_id",
    )
    return {
        field: {"configured": bool(getattr(credentials, field, None))}
        for field in fields
    }


def fetch_google_ads_metrics(client_id: str, request_type: str) -> dict:
    if not is_google_ads_live_enabled():
        return {
            "ok": False,
            "data_source": "google_ads",
            "error": make_integration_error(
                code="google_ads_live_disabled",
                message=(
                    "Google Ads live integration is disabled. "
                    "Set GOOGLE_ADS_LIVE_ENABLED=true after configuring credentials."
                ),
                recoverable=True,
                source="google_ads",
            ),
        }

    credentials = load_google_ads_credentials()
    valid, errors = validate_google_ads_credentials(credentials)

    if not valid:
        return {
            "ok": False,
            "data_source": "google_ads",
            "error": errors[0],
        }

    # Credentials are present and valid — live fetch is not yet implemented in V4.4.
    return {
        "ok": False,
        "data_source": "google_ads",
        "error": make_integration_error(
            code="google_ads_live_not_implemented",
            message=(
                "Google Ads credential validation passed, "
                "but live fetch is not implemented in V4.4."
            ),
            recoverable=True,
            source="google_ads",
        ),
    }

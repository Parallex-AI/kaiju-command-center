import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.schemas import make_integration_error, normalize_metrics

_REQUIRED_FIELDS = (
    "developer_token",
    "client_id",
    "client_secret",
    "refresh_token",
    "customer_id",
)

_GAQL_LAST_30_DAYS = """
SELECT
  campaign.id,
  campaign.name,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
LIMIT 20
""".strip()


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


def normalize_customer_id(customer_id: Optional[str]) -> Optional[str]:
    if customer_id is None:
        return None
    normalized = customer_id.strip().replace("-", "")
    return normalized if normalized else None


def build_google_ads_client_config(credentials: GoogleAdsCredentials) -> dict:
    """Build the config dict for GoogleAdsClient.load_from_dict. Never print this."""
    config = {
        "developer_token": credentials.developer_token,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "refresh_token": credentials.refresh_token,
        "use_proto_plus": True,
    }
    normalized_login_id = normalize_customer_id(credentials.login_customer_id)
    if normalized_login_id:
        config["login_customer_id"] = normalized_login_id
    return config


def _sanitize_message(msg: str, credentials: GoogleAdsCredentials) -> str:
    """Remove credential values from error messages before surfacing them."""
    for field in _REQUIRED_FIELDS:
        val = getattr(credentials, field, None)
        if val and len(val) > 4 and val in msg:
            msg = msg.replace(val, "[REDACTED]")
    return msg


def _do_live_fetch(
    credentials: GoogleAdsCredentials,
    client_id: str,
    request_type: str,
) -> dict:
    try:
        from google.ads.googleads.client import GoogleAdsClient
        from google.ads.googleads.errors import GoogleAdsException
    except ImportError:
        return {
            "ok": False,
            "data_source": "google_ads",
            "error": make_integration_error(
                code="google_ads_dependency_missing",
                message=(
                    "google-ads library is not installed. "
                    "Run: pip install google-ads>=23.1.0"
                ),
                recoverable=True,
                source="google_ads",
            ),
        }

    customer_id = normalize_customer_id(credentials.customer_id)
    if not customer_id:
        return {
            "ok": False,
            "data_source": "google_ads",
            "error": make_integration_error(
                code="credentials_missing",
                message="GOOGLE_ADS_CUSTOMER_ID is required and must be non-empty after normalization.",
                recoverable=True,
                source="google_ads",
            ),
        }

    try:
        config = build_google_ads_client_config(credentials)
        google_ads_client = GoogleAdsClient.load_from_dict(config)
        service = google_ads_client.get_service("GoogleAdsService")

        impressions = 0
        clicks = 0
        cost_micros = 0
        conversions = 0.0
        campaign_count = 0

        stream = service.search_stream(
            customer_id=customer_id,
            query=_GAQL_LAST_30_DAYS,
        )
        for batch in stream:
            for row in batch.results:
                impressions += row.metrics.impressions
                clicks += row.metrics.clicks
                cost_micros += row.metrics.cost_micros
                conversions += row.metrics.conversions
                campaign_count += 1

    except GoogleAdsException as exc:
        try:
            error_count = len(exc.failure.errors)
            summary = f"Google Ads API error ({error_count} error(s) in response)"
        except Exception:
            summary = "Google Ads API returned an error"
        return {
            "ok": False,
            "data_source": "google_ads",
            "error": make_integration_error(
                code="google_ads_api_error",
                message=summary,
                recoverable=True,
                source="google_ads",
            ),
        }

    except Exception as exc:
        msg = _sanitize_message(str(exc), credentials)
        is_timeout = any(
            word in msg.lower()
            for word in ("timeout", "deadline", "timed out")
        )
        return {
            "ok": False,
            "data_source": "google_ads",
            "error": make_integration_error(
                code="integration_timeout" if is_timeout else "google_ads_api_error",
                message=(
                    f"Google Ads integration error: "
                    f"{type(exc).__name__}: {msg[:200]}"
                ),
                recoverable=True,
                source="google_ads",
            ),
        }

    if campaign_count == 0:
        return {
            "ok": False,
            "data_source": "google_ads",
            "error": make_integration_error(
                code="no_data",
                message="Google Ads API returned no campaign metrics for LAST_30_DAYS.",
                recoverable=True,
                source="google_ads",
            ),
        }

    spend = cost_micros / 1_000_000
    currency = os.getenv("GOOGLE_ADS_CURRENCY", "ARS").strip().upper() or "ARS"

    payload = {
        "client": client_id,
        "campaign": (
            f"Aggregated ({campaign_count} "
            f"campaign{'s' if campaign_count != 1 else ''})"
        ),
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": int(conversions),
        "currency": currency,
    }

    canonical = normalize_metrics(payload, source="google_ads")

    return {
        "ok": True,
        "data_source": "google_ads",
        "data": canonical,
        "raw_data": {
            "campaign_count": campaign_count,
            "query": "LAST_30_DAYS campaign summary",
        },
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

    return _do_live_fetch(credentials, client_id, request_type)

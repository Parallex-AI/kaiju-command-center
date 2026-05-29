import os

VALID_DATA_SOURCES = {"n8n_demo", "mock_fixture", "google_ads"}
DEFAULT_DATA_SOURCE = "n8n_demo"


def get_ads_data_source() -> str:
    raw = os.getenv("ADS_DATA_SOURCE", "").strip().lower()
    if raw in VALID_DATA_SOURCES:
        return raw
    return DEFAULT_DATA_SOURCE


def make_integration_error(
    code: str,
    message: str,
    recoverable: bool = True,
    source: str = "integration",
) -> dict:
    return {
        "code": code,
        "message": message,
        "recoverable": recoverable,
        "source": source,
    }


def _safe_float(value, default=None):
    try:
        f = float(value)
        return f if f > 0 else default
    except (TypeError, ValueError):
        return default


def normalize_metrics(payload: dict, source: str) -> dict:
    spend = _safe_float(payload.get("spend"), 0) or 0
    conversions = _safe_float(payload.get("conversions"), 0) or 0
    clicks = _safe_float(payload.get("clicks"), 0) or 0
    impressions = _safe_float(payload.get("impressions"), 0) or 0

    ctr = round(clicks / impressions, 4) if impressions > 0 else None
    cpc = round(spend / clicks, 2) if clicks > 0 else None
    cpa = round(spend / conversions, 2) if conversions > 0 else None
    conversion_rate = round(conversions / clicks, 4) if clicks > 0 else None

    date_range_raw = payload.get("date_range") or {}
    if not isinstance(date_range_raw, dict):
        date_range_raw = {}

    return {
        "source": source,
        "client": payload.get("client") or payload.get("client_id") or None,
        "campaign": payload.get("campaign") or None,
        "date_range": {
            "start_date": date_range_raw.get("start_date") or None,
            "end_date": date_range_raw.get("end_date") or None,
        },
        "currency": payload.get("currency") or "ARS",
        "spend": spend,
        "conversions": int(conversions),
        "clicks": int(clicks),
        "impressions": int(impressions),
        "ctr": ctr,
        "cpc": cpc,
        "cpa": cpa,
        "conversion_rate": conversion_rate,
        "raw_source": source,
    }

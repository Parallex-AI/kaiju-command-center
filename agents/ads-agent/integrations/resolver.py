import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.schemas import get_ads_data_source, make_integration_error, normalize_metrics
from integrations.mock_fixture_adapter import load_mock_fixture


def resolve_ads_data(client_id: str, request_type: str) -> dict:
    data_source = get_ads_data_source()

    if data_source == "n8n_demo":
        return _resolve_n8n_demo(client_id, request_type)

    if data_source == "mock_fixture":
        return load_mock_fixture(client_id, request_type)

    if data_source == "google_ads":
        return {
            "ok": False,
            "data_source": "google_ads",
            "error": make_integration_error(
                "google_ads_not_implemented",
                "Google Ads integration is not implemented yet. Use ADS_DATA_SOURCE=n8n_demo or mock_fixture.",
                recoverable=True,
                source="google_ads",
            ),
        }

    # Defensive: get_ads_data_source() always returns a valid value, but guard anyway.
    return {
        "ok": False,
        "data_source": data_source,
        "error": make_integration_error(
            "unsupported_data_source",
            f"Unknown data source: {data_source!r}",
            recoverable=False,
            source="integration",
        ),
    }


def _resolve_n8n_demo(client_id: str, request_type: str) -> dict:
    from n8n_client import fetch_ads_data_from_n8n

    try:
        raw = fetch_ads_data_from_n8n(client_id=client_id, request_type=request_type)
    except Exception as exc:
        return {
            "ok": False,
            "data_source": "n8n_demo",
            "error": make_integration_error(
                "n8n_demo_failed",
                f"n8n demo fetch failed: {exc}",
                recoverable=True,
                source="n8n_demo",
            ),
        }

    # n8n returns various shapes depending on request_type; normalize what we can.
    metrics_payload = raw if isinstance(raw, dict) else {}
    try:
        metrics = normalize_metrics(metrics_payload, source="n8n_demo")
    except Exception:
        metrics = {"source": "n8n_demo", "raw_source": "n8n_demo"}

    return {
        "ok": True,
        "data_source": "n8n_demo",
        "data": metrics,
        "raw_data": raw,
    }

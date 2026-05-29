import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.schemas import make_integration_error, normalize_metrics

_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "google_ads_summary_fixture.json"


def load_mock_fixture(client_id: str = "demo-client", request_type: str = "summary") -> dict:
    try:
        with open(_FIXTURE_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:
        return {
            "ok": False,
            "data_source": "mock_fixture",
            "error": make_integration_error(
                "fixture_load_failed",
                f"Could not load mock fixture: {exc}",
                recoverable=True,
                source="mock_fixture",
            ),
        }

    if client_id:
        payload["client"] = client_id

    metrics = normalize_metrics(payload, source="mock_fixture")

    return {
        "ok": True,
        "data_source": "mock_fixture",
        "data": metrics,
    }

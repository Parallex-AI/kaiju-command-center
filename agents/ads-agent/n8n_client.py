import os
import sys
import time
from datetime import datetime, timezone

import requests


DEFAULT_N8N_WEBHOOK_URL = "https://flows.kaiju.digital/webhook/ads-agent-demo"

VALID_REQUEST_TYPES = {"summary", "cpa", "conversions", "raw"}

_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = [1, 2]


def _get_timeout() -> float:
    raw = os.getenv("N8N_WEBHOOK_TIMEOUT", "")
    try:
        value = float(raw)
        if value > 0:
            return value
    except (TypeError, ValueError):
        pass
    return 15.0


def _truncate(text: str, limit: int = 500) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [{len(text) - limit} chars truncated]"


def _log_retry(attempt: int, max_attempts: int, error_type: str, sleep_seconds: int) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    print(
        f"[{ts}] n8n retry {attempt}/{max_attempts} after {error_type}; sleeping {sleep_seconds}s",
        file=sys.stderr,
    )


def fetch_ads_data_from_n8n(client_id="demo-client", request_type="summary"):
    if request_type not in VALID_REQUEST_TYPES:
        raise ValueError(f"Unsupported request_type: {request_type}")

    webhook_url = os.getenv("N8N_ADS_WEBHOOK_URL", DEFAULT_N8N_WEBHOOK_URL)
    timeout = _get_timeout()

    payload = {
        "client_id": client_id,
        "agent": "ads-agent",
        "request": request_type,
    }

    last_error = None
    last_error_type = "RequestException"

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = requests.post(webhook_url, json=payload, timeout=timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise RuntimeError(
                f"n8n webhook HTTP error. Status: {response.status_code}. "
                f"URL: {webhook_url}. Body: {_truncate(response.text)}"
            )
        except requests.exceptions.Timeout as error:
            last_error = error
            last_error_type = "Timeout"
        except requests.exceptions.ConnectionError as error:
            last_error = error
            last_error_type = "ConnectionError"
        except requests.exceptions.RequestException as error:
            last_error = error
            last_error_type = "RequestException"
        else:
            try:
                return response.json()
            except ValueError:
                raise RuntimeError(
                    f"n8n webhook returned non-JSON response. "
                    f"URL: {webhook_url}. Body preview: {_truncate(response.text)}"
                )

        if attempt < _MAX_ATTEMPTS:
            sleep_secs = _BACKOFF_SECONDS[attempt - 1]
            _log_retry(attempt, _MAX_ATTEMPTS, last_error_type, sleep_secs)
            time.sleep(sleep_secs)

    if last_error_type == "Timeout":
        raise RuntimeError(
            f"n8n webhook timeout after {_MAX_ATTEMPTS} attempts. "
            f"URL: {webhook_url}. Last error: {last_error}"
        )
    if last_error_type == "ConnectionError":
        raise RuntimeError(
            f"n8n webhook connection error after {_MAX_ATTEMPTS} attempts. "
            f"URL: {webhook_url}. Last error: {last_error}"
        )
    raise RuntimeError(
        f"n8n webhook request failed after {_MAX_ATTEMPTS} attempts. "
        f"URL: {webhook_url}. Last error: {last_error}"
    )

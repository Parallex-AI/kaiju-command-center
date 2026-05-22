import os
import requests


DEFAULT_N8N_WEBHOOK_URL = "https://flows.kaiju.digital/webhook/ads-agent-demo"


def fetch_ads_data_from_n8n(client_id="demo-client", request_type="summary"):
    webhook_url = os.getenv("N8N_ADS_WEBHOOK_URL", DEFAULT_N8N_WEBHOOK_URL)

    payload = {
        "client_id": client_id,
        "agent": "ads-agent",
        "request": request_type
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=15)
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        raise RuntimeError(f"n8n webhook returned HTTP error {response.status_code}: {error}")
    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(f"Could not connect to n8n webhook: {error}")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"n8n webhook timed out after 15 seconds: {webhook_url}")
    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"Error calling n8n webhook: {error}")

    try:
        return response.json()
    except ValueError:
        raise RuntimeError(
            f"n8n webhook returned a non-JSON response (status {response.status_code}): "
            f"{response.text[:200]}"
        )

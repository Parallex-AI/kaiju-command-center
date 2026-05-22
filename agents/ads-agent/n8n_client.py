import os
import requests


DEFAULT_N8N_WEBHOOK_URL = "https://flows.kaiju.digital/webhook-test/ads-agent-demo"


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
        return response.json()

    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"Error calling n8n webhook: {error}")

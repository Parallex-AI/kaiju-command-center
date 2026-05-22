import json
import os
import sys

import requests

DEFAULT_ROUTER_URL = "http://localhost:8000/route"
VALID_REQUEST_TYPES = ["summary", "cpa", "conversions", "raw"]

CLIENT_ID = "demo-client"
AGENT = "ads-agent"


def get_router_url():
    return os.getenv("KAIJU_ROUTER_URL", DEFAULT_ROUTER_URL)


def send_request(request_type):
    url = get_router_url()
    payload = {
        "client_id": CLIENT_ID,
        "agent": AGENT,
        "request": request_type,
    }

    print(f"\n=== Kaiju Demo Client | request={request_type} ===\n")
    print("Payload:")
    print(json.dumps(payload, indent=2))
    print()

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(
            f"Router server is not available. Start it with:\n"
            f"  cd ~/kaiju/agents/router\n"
            f"  ~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000"
        )
        return
    except requests.exceptions.Timeout:
        print(f"Request timed out after 15 seconds. Is the Router running at {url}?")
        return
    except requests.exceptions.HTTPError as error:
        print(f"HTTP error {response.status_code}: {error}")
        return
    except requests.exceptions.RequestException as error:
        print(f"Request failed: {error}")
        return

    try:
        result = response.json()
    except ValueError:
        print(f"Router returned a non-JSON response (status {response.status_code}):")
        print(response.text[:300])
        return

    print("Router response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    request_type = sys.argv[1] if len(sys.argv) > 1 else "summary"

    if request_type not in VALID_REQUEST_TYPES:
        print(f"Unknown request type: '{request_type}'")
        print(f"Valid options: {', '.join(VALID_REQUEST_TYPES)}")
        sys.exit(1)

    send_request(request_type)

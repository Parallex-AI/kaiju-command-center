from pathlib import Path
import sys

ADS_AGENT_DIR = Path(__file__).resolve().parents[1] / "ads-agent"
if str(ADS_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(ADS_AGENT_DIR))

from n8n_client import fetch_ads_data_from_n8n, VALID_REQUEST_TYPES

SUPPORTED_AGENTS = ["ads-agent"]
ROUTER_ID = "kaiju-command-center-router"


def route_request(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "error": "invalid_payload",
            "message": "Payload must be a JSON object.",
        }

    client_id = payload.get("client_id", "demo-client")
    agent = payload.get("agent", "ads-agent")
    request = payload.get("request", "summary")

    if agent not in SUPPORTED_AGENTS:
        return {
            "ok": False,
            "error": "unsupported_agent",
            "message": f"Unsupported agent: {agent}",
            "supported_agents": SUPPORTED_AGENTS,
        }

    if request not in VALID_REQUEST_TYPES:
        return {
            "ok": False,
            "error": "unsupported_request",
            "message": f"Unsupported request type: {request}",
            "supported_requests": sorted(VALID_REQUEST_TYPES),
        }

    try:
        data = fetch_ads_data_from_n8n(client_id=client_id, request_type=request)
    except (RuntimeError, ValueError) as error:
        return {
            "ok": False,
            "error": "agent_execution_failed",
            "message": str(error),
            "agent": agent,
            "client_id": client_id,
            "request": request,
        }

    return {
        "ok": True,
        "router": ROUTER_ID,
        "agent": agent,
        "client_id": client_id,
        "request": request,
        "data": data,
    }

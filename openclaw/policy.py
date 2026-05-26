from pathlib import Path as _Path
import sys as _sys

_OPENCLAW_DIR = str(_Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in _sys.path:
    _sys.path.insert(0, _OPENCLAW_DIR)

from schemas import make_error
from registry import get_supported_agents, get_supported_requests


def validate_request_policy(payload: dict) -> tuple[bool, list]:
    errors = []

    if not isinstance(payload, dict):
        errors.append(make_error("invalid_payload", "Payload must be a JSON object."))
        return False, errors

    agent = payload.get("agent", "ads-agent")
    request = payload.get("request", "summary")
    client_id = payload.get("client_id")

    supported_agents = get_supported_agents()
    if agent not in supported_agents:
        errors.append(make_error(
            "unsupported_agent",
            f"Unsupported agent: '{agent}'. Supported: {supported_agents}",
        ))

    if not errors:
        supported_requests = get_supported_requests(agent)
        if request not in supported_requests:
            errors.append(make_error(
                "unsupported_request",
                f"Unsupported request type: '{request}' for agent '{agent}'. Supported: {supported_requests}",
            ))

    if client_id is not None and (not isinstance(client_id, str) or not client_id.strip()):
        errors.append(make_error(
            "invalid_client_id",
            "client_id must be a non-empty string if provided.",
        ))

    return len(errors) == 0, errors

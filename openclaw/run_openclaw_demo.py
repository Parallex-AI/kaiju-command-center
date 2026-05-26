import json
import sys
from pathlib import Path

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)

from openclaw import process_request

VALID_REQUESTS = ["summary", "cpa", "conversions", "raw"]

BANNER = "=== Kaiju OpenClaw | V3.1 Demo ==="


def run_demo(request_type: str = "summary", agent: str = "ads-agent") -> None:
    print(BANNER)
    print(f"Request : {request_type}")
    print(f"Agent   : {agent}")
    print()

    payload = {
        "client_id": "demo-client",
        "agent": agent,
        "request": request_type,
    }

    result = process_request(payload)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    args = sys.argv[1:]
    req = args[0] if len(args) >= 1 else "summary"
    agt = args[1] if len(args) >= 2 else "ads-agent"
    run_demo(request_type=req, agent=agt)

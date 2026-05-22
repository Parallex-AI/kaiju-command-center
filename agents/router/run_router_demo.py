import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from router import route_request, SUPPORTED_AGENTS

VALID_REQUESTS = ["summary", "cpa", "conversions", "raw"]


if __name__ == "__main__":
    request_type = sys.argv[1] if len(sys.argv) > 1 else "summary"

    if request_type not in VALID_REQUESTS:
        print(f"Unknown request type: '{request_type}'")
        print(f"Valid options: {', '.join(VALID_REQUESTS)}")
        sys.exit(1)

    payload = {
        "client_id": "demo-client",
        "agent": "ads-agent",
        "request": request_type,
    }

    print(f"\n=== Kaiju Router Demo | request={request_type} ===\n")
    print("Payload sent to router:")
    print(json.dumps(payload, indent=2))
    print()

    result = route_request(payload)

    print("Router response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

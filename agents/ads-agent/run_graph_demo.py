import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ads_graph import run_ads_graph
from n8n_client import VALID_REQUEST_TYPES

if __name__ == "__main__":
    request_type = sys.argv[1] if len(sys.argv) > 1 else "summary"

    if request_type not in VALID_REQUEST_TYPES:
        print(f"Unknown request type: '{request_type}'")
        print(f"Valid options: {', '.join(sorted(VALID_REQUEST_TYPES))}")
        sys.exit(1)

    print(f"\n=== Kaiju Ads Agent | Graph Demo | request={request_type} ===\n")

    result = run_ads_graph(request_type=request_type)
    print(json.dumps(result, indent=2, ensure_ascii=False))

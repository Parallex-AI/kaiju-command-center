import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrations.resolver import resolve_ads_data
from integrations.schemas import get_ads_data_source

VALID_REQUEST_TYPES = {"summary", "cpa", "conversions", "raw"}


def main():
    request_type = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if request_type not in VALID_REQUEST_TYPES:
        print(f"Unknown request type: {request_type!r}. Valid: {sorted(VALID_REQUEST_TYPES)}")
        sys.exit(1)

    active_source = get_ads_data_source()
    print(f"ADS_DATA_SOURCE: {active_source}")
    print(f"Request type:    {request_type}")
    print()

    result = resolve_ads_data("demo-client", request_type)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()

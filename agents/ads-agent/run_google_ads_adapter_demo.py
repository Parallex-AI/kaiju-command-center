import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrations.google_ads_adapter import (
    fetch_google_ads_metrics,
    is_google_ads_live_enabled,
    load_google_ads_credentials,
    redacted_google_ads_credentials,
    validate_google_ads_credentials,
)


def main():
    print("=== Kaiju Ads Agent | Google Ads Adapter Demo ===")
    print()

    live_enabled = is_google_ads_live_enabled()
    print(f"GOOGLE_ADS_LIVE_ENABLED: {live_enabled}")
    print()

    credentials = load_google_ads_credentials()
    redacted = redacted_google_ads_credentials(credentials)
    print("Credentials (redacted):")
    print(json.dumps(redacted, indent=2))
    print()

    valid, errors = validate_google_ads_credentials(credentials)
    print(f"Credential validation: {'PASS' if valid else 'FAIL'}")
    if errors:
        for err in errors:
            print(f"  [{err['code']}] {err['message']}")
    print()

    print("fetch_google_ads_metrics('demo-client', 'summary'):")
    result = fetch_google_ads_metrics("demo-client", "summary")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()

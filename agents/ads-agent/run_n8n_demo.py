import json
import sys

from n8n_client import fetch_ads_data_from_n8n, VALID_REQUEST_TYPES


def safe_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def calculate_cpa(spend, conversions):
    spend = safe_float(spend)
    conversions = safe_float(conversions)
    if conversions == 0:
        return None
    return spend / conversions


def print_summary(data):
    campaign = data.get("campaign", "Unknown campaign")
    spend = data.get("spend", 0)
    conversions = data.get("conversions", 0)
    clicks = data.get("clicks", 0)
    impressions = data.get("impressions", 0)
    currency = data.get("currency", "ARS")
    cpa = calculate_cpa(spend, conversions)

    print("\n=== Kaiju Ads Agent | n8n Demo ===\n")
    print(f"Campaign:     {campaign}")
    print(f"Spend:        {currency} {safe_float(spend):,.2f}")
    print(f"Conversions:  {safe_int(conversions)}")
    print(f"Clicks:       {safe_int(clicks)}")
    print(f"Impressions:  {safe_int(impressions)}")

    if cpa is not None:
        print(f"CPA:          {currency} {cpa:,.2f}")
    else:
        print("CPA:          unavailable (no conversions)")

    print("\nExecutive Summary:")
    if cpa is None:
        print("The campaign has spend but no conversions. Immediate review is required.")
    elif cpa <= 2000:
        print("The campaign is performing within an efficient CPA range.")
    elif cpa <= 4000:
        print("The campaign is generating conversions, but CPA optimization is recommended.")
    else:
        print("The campaign CPA is high. Budget, targeting, and creatives should be reviewed.")


def print_cpa(data):
    spend = data.get("spend", 0)
    conversions = data.get("conversions", 0)
    currency = data.get("currency", "ARS")
    cpa = calculate_cpa(spend, conversions)

    print("\n=== Kaiju Ads Agent | CPA ===\n")
    print(f"Spend:        {currency} {safe_float(spend):,.2f}")
    print(f"Conversions:  {safe_int(conversions)}")

    if cpa is not None:
        print(f"CPA:          {currency} {cpa:,.2f}")
    else:
        print("CPA:          unavailable (no conversions)")


def print_conversions(data):
    campaign = data.get("campaign", "Unknown campaign")
    conversions = data.get("conversions", 0)

    print("\n=== Kaiju Ads Agent | Conversions ===\n")
    print(f"Campaign:     {campaign}")
    print(f"Conversions:  {safe_int(conversions)}")


def print_raw(data):
    print("\n=== Kaiju Ads Agent | Raw JSON ===\n")
    print(json.dumps(data, indent=2, ensure_ascii=False))


PRINTERS = {
    "summary": print_summary,
    "cpa": print_cpa,
    "conversions": print_conversions,
    "raw": print_raw,
}


if __name__ == "__main__":
    request_type = sys.argv[1] if len(sys.argv) > 1 else "summary"

    if request_type not in VALID_REQUEST_TYPES:
        print(f"Unknown request type: '{request_type}'")
        print(f"Valid options: {', '.join(sorted(VALID_REQUEST_TYPES))}")
        sys.exit(1)

    try:
        data = fetch_ads_data_from_n8n(request_type=request_type)
    except (RuntimeError, ValueError) as error:
        print(f"\nError fetching data from n8n: {error}\n")
        sys.exit(1)

    PRINTERS[request_type](data)

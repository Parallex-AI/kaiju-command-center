from n8n_client import fetch_ads_data_from_n8n


def calculate_cpa(spend, conversions):
    spend = float(spend)
    conversions = float(conversions)

    if conversions == 0:
        return None

    return spend / conversions


def generate_summary(data):
    spend = data.get("spend", 0)
    conversions = data.get("conversions", 0)
    clicks = data.get("clicks", 0)
    impressions = data.get("impressions", 0)
    currency = data.get("currency", "ARS")
    campaign = data.get("campaign", "Unknown campaign")

    cpa = calculate_cpa(spend, conversions)

    print("\n=== Kaiju Ads Agent | n8n Demo ===\n")
    print(f"Campaign: {campaign}")
    print(f"Spend: {currency} {float(spend):,.2f}")
    print(f"Conversions: {int(float(conversions))}")
    print(f"Clicks: {int(float(clicks))}")
    print(f"Impressions: {int(float(impressions))}")

    if cpa is not None:
        print(f"CPA: {currency} {cpa:,.2f}")
    else:
        print("CPA: unavailable, no conversions")

    print("\nExecutive Summary:")

    if cpa is None:
        print("The campaign has spend but no conversions. Immediate review is required.")
    elif cpa <= 2000:
        print("The campaign is performing within an efficient CPA range.")
    elif cpa <= 4000:
        print("The campaign is generating conversions, but CPA optimization is recommended.")
    else:
        print("The campaign CPA is high. Budget allocation, targeting and creative should be reviewed.")


if __name__ == "__main__":
    ads_data = fetch_ads_data_from_n8n()
    generate_summary(ads_data)

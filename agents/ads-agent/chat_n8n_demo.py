from n8n_client import fetch_ads_data_from_n8n


def calculate_cpa(spend, conversions):
    spend = float(spend)
    conversions = float(conversions)

    if conversions == 0:
        return None

    return spend / conversions


def load_data():
    return fetch_ads_data_from_n8n()


def print_help():
    print("\nComandos disponibles:")
    print("- ¿Cómo viene la campaña?")
    print("- CPA")
    print("- Conversiones")
    print("- Resumen")
    print("- salir\n")


def main():
    print("\nKaiju Ads Agent conectado a n8n")
    print("Escribí una consulta o 'salir' para terminar.")
    print_help()

    while True:
        user_input = input("> ").strip().lower()

        if user_input in ["salir", "exit", "quit"]:
            print("Cerrando Ads Agent.")
            break

        try:
            data = load_data()
        except RuntimeError as error:
            print(f"\nNo pude obtener datos desde n8n: {error}\n")
            continue

        spend = data.get("spend", 0)
        conversions = data.get("conversions", 0)
        clicks = data.get("clicks", 0)
        impressions = data.get("impressions", 0)
        currency = data.get("currency", "ARS")
        campaign = data.get("campaign", "Unknown campaign")

        cpa = calculate_cpa(spend, conversions)

        if "cpa" in user_input:
            if cpa is None:
                print("\nCPA no disponible porque no hay conversiones.\n")
            else:
                print(f"\nEl CPA actual es {currency} {cpa:,.2f}.\n")

        elif "conversion" in user_input:
            print(f"\nLa campaña tiene {int(float(conversions))} conversiones.\n")

        elif "resumen" in user_input or "cómo viene" in user_input or "campaña" in user_input:
            print(f"\nCampaña: {campaign}")
            print(f"Inversión: {currency} {float(spend):,.2f}")
            print(f"Conversiones: {int(float(conversions))}")
            print(f"Clicks: {int(float(clicks))}")
            print(f"Impresiones: {int(float(impressions))}")

            if cpa is not None:
                print(f"CPA: {currency} {cpa:,.2f}")

            if cpa is None:
                print("Diagnóstico: hay inversión pero todavía no hay conversiones registradas.\n")
            elif cpa <= 2000:
                print("Diagnóstico: la campaña viene eficiente.\n")
            elif cpa <= 4000:
                print("Diagnóstico: la campaña convierte, pero hay oportunidad de optimización.\n")
            else:
                print("Diagnóstico: el CPA está alto. Conviene revisar presupuesto, segmentación y creatividades.\n")

        else:
            print("\nNo entendí la consulta. Probá con: CPA, Conversiones, Resumen o ¿Cómo viene la campaña?\n")


if __name__ == "__main__":
    main()

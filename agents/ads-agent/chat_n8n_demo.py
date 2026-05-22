from n8n_client import fetch_ads_data_from_n8n


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


def load_data(request_type="summary"):
    return fetch_ads_data_from_n8n(request_type=request_type)


def print_help():
    print("\nComandos disponibles:")
    print("- CPA")
    print("- Conversiones")
    print("- Resumen")
    print("- ¿Cómo viene la campaña?")
    print("- Raw  /  JSON")
    print("- salir\n")


def handle_cpa(data):
    spend = data.get("spend", 0)
    conversions = data.get("conversions", 0)
    currency = data.get("currency", "ARS")
    cpa = calculate_cpa(spend, conversions)

    if cpa is None:
        print("\nCPA no disponible porque no hay conversiones.\n")
    else:
        print(f"\nEl CPA actual es {currency} {cpa:,.2f}.\n")


def handle_conversions(data):
    conversions = data.get("conversions", 0)
    print(f"\nLa campaña tiene {safe_int(conversions)} conversiones.\n")


def handle_summary(data):
    campaign = data.get("campaign", "Unknown campaign")
    spend = data.get("spend", 0)
    conversions = data.get("conversions", 0)
    clicks = data.get("clicks", 0)
    impressions = data.get("impressions", 0)
    currency = data.get("currency", "ARS")
    cpa = calculate_cpa(spend, conversions)

    print(f"\nCampaña:      {campaign}")
    print(f"Inversión:    {currency} {safe_float(spend):,.2f}")
    print(f"Conversiones: {safe_int(conversions)}")
    print(f"Clicks:       {safe_int(clicks)}")
    print(f"Impresiones:  {safe_int(impressions)}")

    if cpa is not None:
        print(f"CPA:          {currency} {cpa:,.2f}")

    if cpa is None:
        print("Diagnóstico: hay inversión pero todavía no hay conversiones registradas.\n")
    elif cpa <= 2000:
        print("Diagnóstico: la campaña viene eficiente.\n")
    elif cpa <= 4000:
        print("Diagnóstico: la campaña convierte, pero hay oportunidad de optimización.\n")
    else:
        print("Diagnóstico: el CPA está alto. Conviene revisar presupuesto, segmentación y creatividades.\n")


def handle_raw(data):
    import json
    print()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()


COMMANDS = {
    "cpa": ("cpa", handle_cpa),
    "conversiones": ("conversions", handle_conversions),
    "resumen": ("summary", handle_summary),
    "cómo viene": ("summary", handle_summary),
    "campaña": ("summary", handle_summary),
    "raw": ("raw", handle_raw),
    "json": ("raw", handle_raw),
}


def resolve_command(user_input):
    for keyword, (request_type, handler) in COMMANDS.items():
        if keyword in user_input:
            return request_type, handler
    return None, None


def main():
    print("\nKaiju Ads Agent conectado a n8n")
    print("Escribí una consulta o 'salir' para terminar.")
    print_help()

    while True:
        user_input = input("> ").strip().lower()

        if user_input in ["salir", "exit", "quit"]:
            print("Cerrando Ads Agent.")
            break

        request_type, handler = resolve_command(user_input)

        if request_type is None:
            print("\nNo entendí la consulta. Probá con: CPA, Conversiones, Resumen, Raw o ¿Cómo viene la campaña?\n")
            continue

        try:
            data = load_data(request_type=request_type)
        except (RuntimeError, ValueError) as error:
            print(f"\nNo pude obtener datos desde n8n: {error}\n")
            continue

        handler(data)


if __name__ == "__main__":
    main()

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from router import route_request

CLIENT_ID = "demo-client"
AGENT = "ads-agent"

COMMANDS = {
    "resumen": "summary",
    "cómo viene": "summary",
    "campaña": "summary",
    "cpa": "cpa",
    "conversiones": "conversions",
    "raw": "raw",
    "json": "raw",
}


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


def print_cpa(data):
    spend = data.get("spend", 0)
    conversions = data.get("conversions", 0)
    currency = data.get("currency", "ARS")
    cpa = calculate_cpa(spend, conversions)

    if cpa is None:
        print("\nCPA no disponible porque no hay conversiones.\n")
    else:
        print(f"\nInversión: {currency} {safe_float(spend):,.2f}")
        print(f"Conversiones: {safe_int(conversions)}")
        print(f"CPA actual: {currency} {cpa:,.2f}\n")


def print_conversions(data):
    campaign = data.get("campaign", "Unknown campaign")
    conversions = data.get("conversions", 0)
    print(f"\nCampaña: {campaign}")
    print(f"Conversiones: {safe_int(conversions)}\n")


def print_raw(data):
    print()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()


PRINTERS = {
    "summary": print_summary,
    "cpa": print_cpa,
    "conversions": print_conversions,
    "raw": print_raw,
}


def resolve_command(user_input):
    for keyword, request_type in COMMANDS.items():
        if keyword in user_input:
            return request_type
    return None


def print_help():
    print("\nComandos disponibles:")
    print("- Resumen  /  ¿Cómo viene la campaña?")
    print("- CPA")
    print("- Conversiones")
    print("- Raw  /  JSON")
    print("- salir\n")


def main():
    print("\nKaiju Router — chat demo")
    print(f"Agente activo: {AGENT}  |  Cliente: {CLIENT_ID}")
    print_help()

    while True:
        user_input = input("> ").strip().lower()

        if user_input in ["salir", "exit", "quit"]:
            print("Cerrando Router demo.")
            break

        request_type = resolve_command(user_input)

        if request_type is None:
            print("\nNo entendí la consulta. Probá con: Resumen, CPA, Conversiones, Raw o ¿Cómo viene la campaña?\n")
            continue

        payload = {
            "client_id": CLIENT_ID,
            "agent": AGENT,
            "request": request_type,
        }

        result = route_request(payload)

        if not result.get("ok"):
            print(f"\nError del router: {result.get('message', 'Unknown error')}\n")
            continue

        printer = PRINTERS.get(request_type, print_raw)
        printer(result["data"])


if __name__ == "__main__":
    main()

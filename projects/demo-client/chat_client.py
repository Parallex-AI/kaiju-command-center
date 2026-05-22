import json
import os

import requests

DEFAULT_ROUTER_URL = "http://localhost:8000/route"

CLIENT_ID = "demo-client"
AGENT = "ads-agent"

COMMANDS = {
    "resumen": "summary",
    "summary": "summary",
    "cómo viene": "summary",
    "campaña": "summary",
    "cpa": "cpa",
    "conversiones": "conversions",
    "conversions": "conversions",
    "raw": "raw",
    "json": "raw",
}


def get_router_url():
    return os.getenv("KAIJU_ROUTER_URL", DEFAULT_ROUTER_URL)


def resolve_command(user_input):
    for keyword, request_type in COMMANDS.items():
        if keyword in user_input:
            return request_type
    return None


def call_router(request_type):
    url = get_router_url()
    payload = {
        "client_id": CLIENT_ID,
        "agent": AGENT,
        "request": request_type,
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Router server is not available. Start it with:\n"
            f"  cd ~/kaiju/agents/router\n"
            f"  ~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Request timed out. Is the Router running at {url}?")
    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"Request failed: {error}")
    except ValueError:
        raise RuntimeError(f"Router returned a non-JSON response.")


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


def print_summary(data):
    campaign = data.get("campaign", "Unknown")
    spend = data.get("spend", 0)
    conversions = data.get("conversions", 0)
    clicks = data.get("clicks", 0)
    impressions = data.get("impressions", 0)
    currency = data.get("currency", "ARS")
    cpa = data.get("cpa") or (safe_float(spend) / safe_float(conversions) if safe_float(conversions) else None)

    print(f"\nCampaña:      {campaign}")
    print(f"Inversión:    {currency} {safe_float(spend):,.2f}")
    print(f"Conversiones: {safe_int(conversions)}")
    print(f"Clicks:       {safe_int(clicks)}")
    print(f"Impresiones:  {safe_int(impressions)}")
    if cpa is not None:
        print(f"CPA:          {currency} {safe_float(cpa):,.2f}")

    if cpa is None:
        print("Diagnóstico: hay inversión pero todavía no hay conversiones.\n")
    elif safe_float(cpa) <= 2000:
        print("Diagnóstico: la campaña viene eficiente.\n")
    elif safe_float(cpa) <= 4000:
        print("Diagnóstico: la campaña convierte, pero hay oportunidad de optimización.\n")
    else:
        print("Diagnóstico: el CPA está alto. Revisar presupuesto, segmentación y creatividades.\n")


def print_cpa(data):
    spend = data.get("spend", 0)
    conversions = data.get("conversions", 0)
    currency = data.get("currency", "ARS")
    cpa = data.get("cpa")

    print(f"\nInversión:    {currency} {safe_float(spend):,.2f}")
    print(f"Conversiones: {safe_int(conversions)}")
    if cpa is not None:
        print(f"CPA:          {currency} {safe_float(cpa):,.2f}\n")
    else:
        print("CPA:          no disponible (sin conversiones)\n")


def print_conversions(data):
    campaign = data.get("campaign", "Unknown")
    conversions = data.get("conversions", 0)
    print(f"\nCampaña:      {campaign}")
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


def print_help():
    print("\nComandos disponibles:")
    print("- resumen  /  summary  /  ¿Cómo viene la campaña?")
    print("- cpa")
    print("- conversiones  /  conversions")
    print("- raw  /  json")
    print("- salir\n")


def main():
    print("\nKaiju Demo Client — chat mode")
    print(f"Router: {get_router_url()}")
    print_help()

    while True:
        user_input = input("> ").strip().lower()

        if user_input in ["salir", "exit", "quit"]:
            print("Cerrando Demo Client.")
            break

        request_type = resolve_command(user_input)

        if request_type is None:
            print("\nNo entendí la consulta. Probá con: resumen, cpa, conversiones, raw o salir.\n")
            continue

        try:
            result = call_router(request_type)
        except RuntimeError as error:
            print(f"\nError: {error}\n")
            continue

        if not result.get("ok"):
            print(f"\nRouter error [{result.get('error')}]: {result.get('message')}\n")
            continue

        printer = PRINTERS.get(request_type, print_raw)
        printer(result.get("data", result))


if __name__ == "__main__":
    main()

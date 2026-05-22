import json
import os

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "../../projects/demo-client/demo-data.json"
)


def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def handle(query, data):
    metrics = data["metrics"]
    spend = metrics["spend"]
    conversions = metrics["conversions"]
    cpa = spend / conversions if conversions else float("inf")
    campaign = data.get("campaign", "N/A")
    client = data.get("client", "N/A")

    q = query.strip().lower()

    if any(k in q for k in ["cómo viene", "como viene", "campaña"]):
        status = "dentro del objetivo" if cpa <= 2000 else "por encima del objetivo"
        return (
            f"La campaña {campaign} de {client} tiene una inversión de ${spend:,.0f} "
            f"con {conversions:,} conversiones y un CPA de ${cpa:,.2f}. "
            f"El rendimiento está {status}."
        )

    if "resumen" in q:
        rec = (
            "Mantener estrategia actual."
            if cpa <= 2000
            else "Optimizar segmentación, creatividades y pujas."
        )
        return (
            f"Resumen — {campaign} ({client})\n"
            f"  Inversión:    ${spend:,.0f}\n"
            f"  Conversiones: {conversions:,}\n"
            f"  CPA:          ${cpa:,.2f}\n"
            f"  Recomendación: {rec}"
        )

    if q == "cpa":
        label = "dentro del objetivo" if cpa <= 2000 else "por encima del objetivo"
        return f"CPA actual: ${cpa:,.2f} ({label}, objetivo ≤ $2,000)."

    if "conversiones" in q:
        return f"La campaña registra {conversions:,} conversiones hasta el momento."

    return "No entendí la consulta. Puedes preguntar: ¿Cómo viene la campaña?, Resumen, CPA, Conversiones."


def main():
    data = load_data(DATA_PATH)
    print("Ads Agent — modo interactivo. Escribe 'salir' para terminar.")
    print("-" * 52)
    while True:
        try:
            query = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            break
        if not query:
            continue
        if query.lower() == "salir":
            print("Hasta luego.")
            break
        print(f"Agente: {handle(query, data)}\n")


if __name__ == "__main__":
    main()

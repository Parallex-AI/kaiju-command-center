import json
import os

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "../../projects/demo-client/demo-data.json"
)


def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_metrics(data):
    metrics = data["metrics"]
    spend = metrics["spend"]
    conversions = metrics["conversions"]
    cpa = spend / conversions if conversions else float("inf")
    return spend, conversions, cpa


def recommendation(cpa):
    if cpa <= 2000:
        return "El rendimiento está dentro del objetivo. Se recomienda mantener la estrategia actual."
    return "El CPA supera el objetivo. Se requiere optimización: revisar segmentación, creatividades y pujas."


def main():
    data = load_data(DATA_PATH)
    spend, conversions, cpa = calculate_metrics(data)

    print("=" * 50)
    print("RESUMEN EJECUTIVO — CAMPAÑA: {}".format(data.get("campaign", "N/A")))
    print("Cliente: {}".format(data.get("client", "N/A")))
    print("=" * 50)
    print("Inversión total:   ${:,.0f}".format(spend))
    print("Conversiones:      {:,}".format(conversions))
    print("CPA calculado:     ${:,.2f}".format(cpa))
    print("-" * 50)
    print("Recomendación:")
    print("  " + recommendation(cpa))
    print("=" * 50)


if __name__ == "__main__":
    main()

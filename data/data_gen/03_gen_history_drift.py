"""Generate 365-day behavioral history for drift detection."""

import os
import csv
import random
from datetime import datetime, timedelta
from typing import List, Dict

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data_raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET_ENTITY = "Precision Parts GmbH"

# Sector transition (drift pattern)
SECTORS = {
    "months_1_6": ["Manufacturing", "Raw Materials", "Industrial Equipment"],
    "months_7_9": ["Manufacturing", "Raw Materials", "Consulting"],  # Drift starts
    "months_10_12": ["Consulting", "Advisory", "Financial Services"],  # Full drift
}


def generate_history():
    """Generate 365 days of transaction history showing behavioral drift."""

    history = []
    start_date = datetime.now() - timedelta(days=365)

    for day in range(365):
        current_date = start_date + timedelta(days=day)
        month = (day // 30) + 1

        # Determine sector based on month (showing drift)
        if month <= 6:
            sectors = SECTORS["months_1_6"]
            amount_range = (40000, 80000)
            frequency = random.randint(2, 4)  # Normal frequency
        elif month <= 9:
            sectors = SECTORS["months_7_9"]
            amount_range = (20000, 60000)
            frequency = random.randint(3, 6)  # Increasing frequency
        else:
            sectors = SECTORS["months_10_12"]
            amount_range = (800, 9500)  # Structuring amounts
            frequency = random.randint(5, 10)  # High frequency

        # Generate transactions for this day
        for _ in range(frequency):
            sector = random.choice(sectors)
            amount = random.uniform(*amount_range)

            counterparty = f"{sector} Supplier {random.randint(1, 50)}"
            if month > 9:
                counterparty = f"Consulting Firm {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])}"

            history.append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "entity": TARGET_ENTITY,
                    "counterparty": counterparty,
                    "amount": round(amount, 2),
                    "currency": "EUR",
                    "sector": sector,
                    "purpose": f"{sector} payment",
                    "is_drift": month > 6,
                }
            )

    return history


def calculate_drift_metrics(history: List[Dict]) -> Dict:
    """Calculate drift metrics from history."""

    early_period = [h for h in history if not h["is_drift"]]
    late_period = [h for h in history if h["is_drift"]]

    early_avg_amount = (
        sum(h["amount"] for h in early_period) / len(early_period)
        if early_period
        else 0
    )
    late_avg_amount = (
        sum(h["amount"] for h in late_period) / len(late_period) if late_period else 0
    )

    early_sectors = set(h["sector"] for h in early_period)
    late_sectors = set(h["sector"] for h in late_period)

    sector_overlap = (
        len(early_sectors & late_sectors) / len(early_sectors | late_sectors)
        if early_sectors | late_sectors
        else 1
    )

    return {
        "entity": TARGET_ENTITY,
        "early_avg_amount": round(early_avg_amount, 2),
        "late_avg_amount": round(late_avg_amount, 2),
        "amount_change_pct": round(
            (late_avg_amount - early_avg_amount) / early_avg_amount * 100, 2
        )
        if early_avg_amount
        else 0,
        "early_sectors": list(early_sectors),
        "late_sectors": list(late_sectors),
        "sector_overlap": round(sector_overlap, 2),
        "drift_score": round(1 - sector_overlap, 2),
        "total_transactions": len(history),
        "drift_detected": sector_overlap < 0.5,
    }


def main():
    print(f"Generating 365-day history for {TARGET_ENTITY}...")

    history = generate_history()

    # Write CSV
    csv_path = os.path.join(OUTPUT_DIR, "account_history_365d.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=history[0].keys())
        writer.writeheader()
        writer.writerows(history)

    print(f"Written {len(history)} transactions to {csv_path}")

    # Calculate and write drift metrics
    metrics = calculate_drift_metrics(history)

    import json

    metrics_path = os.path.join(OUTPUT_DIR, "drift_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Drift metrics: {metrics}")
    print(f"Written to {metrics_path}")


if __name__ == "__main__":
    main()

"""Load entity behavioral baselines into Mem0 agent memory."""

import json
import os
from typing import Any

from mem0 import MemoryClient

from backend.config import settings

DATA_RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "data_raw")


def get_client() -> MemoryClient:
    """Get Mem0 client."""
    return MemoryClient(api_key=settings.mem0_api_key)


def load_entity_baselines(client: MemoryClient) -> int:
    """Load entity behavioral baselines from JSON file."""
    profiles_path = os.path.join(DATA_RAW_DIR, "mem0_agent_profiles.json")

    if not os.path.exists(profiles_path):
        print(f"Agent profiles file not found: {profiles_path}")
        return 0

    with open(profiles_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("entities", [])
    loaded = 0

    for entity in entities:
        entity_name = entity.get("name", "Unknown")
        facts = entity.get("facts", [])

        for fact in facts:
            try:
                client.add(
                    messages=[
                        {
                            "role": "user",
                            "content": f"Entity baseline for {entity_name}: {fact}",
                        }
                    ],
                    user_id=f"entity_{entity_name.lower().replace(' ', '_')}",
                    metadata={
                        "entity_name": entity_name,
                        "fact_type": "baseline",
                        "source": "initial_load",
                    },
                )
                loaded += 1
            except Exception as e:
                print(f"Failed to add memory for {entity_name}: {e}")

    print(f"Loaded {loaded} entity baseline facts")
    return loaded


def load_transaction_patterns(client: MemoryClient) -> int:
    """Load historical transaction patterns as behavioral baselines."""
    history_path = os.path.join(DATA_RAW_DIR, "account_history_365d.csv")

    if not os.path.exists(history_path):
        print(f"Account history file not found: {history_path}")
        return _load_default_patterns(client)

    import csv

    entity_stats: dict[str, dict[str, Any]] = {}

    with open(history_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Support multiple column name formats for compatibility
            entity = (
                row.get("entity_name")
                or row.get("entity_id")
                or row.get("debtor")
                or "Unknown"
            )
            try:
                amount = float(row.get("amount", 0))
            except (ValueError, TypeError):
                amount = 0.0

            if entity not in entity_stats:
                entity_stats[entity] = {"count": 0, "total": 0, "amounts": []}

            entity_stats[entity]["count"] += 1
            entity_stats[entity]["total"] += amount
            entity_stats[entity]["amounts"].append(amount)

    loaded = 0
    for entity_name, stats in entity_stats.items():
        avg_amount = stats["total"] / stats["count"] if stats["count"] > 0 else 0
        amounts = sorted(stats["amounts"])
        median = amounts[len(amounts) // 2] if amounts else 0

        baseline = {
            "transaction_count_365d": stats["count"],
            "average_amount": round(avg_amount, 2),
            "median_amount": round(median, 2),
            "total_volume": round(stats["total"], 2),
        }

        try:
            client.add(
                messages=[
                    {
                        "role": "user",
                        "content": f"Transaction baseline for {entity_name}: {json.dumps(baseline)}",
                    }
                ],
                user_id=f"entity_{entity_name.lower().replace(' ', '_')}",
                metadata={
                    "entity_name": entity_name,
                    "fact_type": "transaction_baseline",
                    "source": "account_history",
                },
            )
            loaded += 1
        except Exception as e:
            print(f"Failed to add transaction baseline for {entity_name}: {e}")

    print(f"Loaded {loaded} transaction pattern baselines")
    return loaded


def _load_default_patterns(client: MemoryClient) -> int:
    """Load default behavioral patterns when no history file exists."""
    default_baselines = [
        {
            "entity_name": "Precision Parts Gmbh",
            "patterns": {
                "typical_payment_range": "800-1200 EUR for consultants",
                "payment_frequency": "weekly for consultants, monthly for materials",
                "verified_counterparties": ["AWS EMEA SARL", "Salesforce.com"],
                "unusual_threshold": ">50000 EUR requires board approval",
            },
        },
        {
            "entity_name": "Global Trade Corp Ltd",
            "patterns": {
                "typical_payment_range": "5000-15000 EUR",
                "payment_frequency": "bi-weekly",
                "high_risk_jurisdictions": [],
                "unusual_threshold": ">100000 EUR",
            },
        },
        {
            "entity_name": "Müller & Sons KG",
            "patterns": {
                "typical_payment_range": "1000-20000 EUR",
                "payment_frequency": "weekly",
                "verified_counterparties": ["AWS EMEA SARL", "Salesforce.com"],
                "unusual_threshold": ">50000 EUR",
            },
        },
    ]

    loaded = 0
    for baseline in default_baselines:
        entity_name = baseline["entity_name"]
        patterns = baseline["patterns"]

        try:
            client.add(
                messages=[
                    {
                        "role": "user",
                        "content": f"Behavioral baseline for {entity_name}: {json.dumps(patterns)}",
                    }
                ],
                user_id=f"entity_{entity_name.lower().replace(' ', '_')}",
                metadata={
                    "entity_name": entity_name,
                    "fact_type": "behavioral_baseline",
                    "source": "default",
                },
            )
            loaded += 1
        except Exception as e:
            print(f"Failed to add default baseline for {entity_name}: {e}")

    print(f"Loaded {loaded} default behavioral baselines")
    return loaded


def load_agent_expertise(client: MemoryClient) -> int:
    """Load agent expertise and decision patterns."""
    agent_profiles = [
        {
            "agent_id": "prosecutor",
            "expertise": [
                "Specializes in identifying fraud patterns and risk indicators",
                "Trained on OFAC sanctions lists and PEP databases",
                "Focuses on transaction anomalies and network topology",
                "Uses graph analysis to detect layering and structuring",
            ],
        },
        {
            "agent_id": "skeptic",
            "expertise": [
                "Specializes in finding exculpatory evidence and legitimate explanations",
                "Trained on corporate governance documents and business practices",
                "Focuses on payment grid compliance and authorized transactions",
                "Validates business relationships and normal trading patterns",
            ],
        },
        {
            "agent_id": "judge",
            "expertise": [
                "Arbitrates between prosecutor and skeptic findings",
                "Applies EU AI Act transparency requirements",
                "Ensures explainability and audit trail compliance",
                "Makes final determination with confidence scoring",
            ],
        },
    ]

    loaded = 0
    for profile in agent_profiles:
        agent_id = profile["agent_id"]

        for expertise in profile["expertise"]:
            try:
                client.add(
                    messages=[
                        {
                            "role": "assistant",
                            "content": f"Agent capability: {expertise}",
                        }
                    ],
                    user_id=f"agent_{agent_id}",
                    metadata={
                        "agent_id": agent_id,
                        "fact_type": "expertise",
                        "source": "initial_load",
                    },
                )
                loaded += 1
            except Exception as e:
                print(f"Failed to add expertise for {agent_id}: {e}")

    print(f"Loaded {loaded} agent expertise memories")
    return loaded


def main():
    """Main loader function."""
    print("=" * 50)
    print("MEM0 AGENT MEMORY LOADER")
    print("=" * 50)

    print("\nInitializing Mem0 connection...")
    try:
        client = get_client()
        print("Connected to Mem0 successfully")
    except Exception as e:
        print(f"Failed to connect to Mem0: {e}")
        return

    print("\nLoading entity baselines...")
    load_entity_baselines(client)

    print("\nLoading transaction patterns...")
    load_transaction_patterns(client)

    print("\nLoading agent expertise...")
    load_agent_expertise(client)

    print("\nMemory loading complete!")


if __name__ == "__main__":
    main()

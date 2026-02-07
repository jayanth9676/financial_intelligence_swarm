"""Generate reference data: sanctions lists, PEP lists, and entity behavioral history."""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict
import random
import hashlib

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data_raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sanctioned entities (using FollowTheMoney schema for entities.ftm.json)
SANCTIONED_ENTITIES = [
    {
        "id": "ofac-sdn-001",
        "schema": "Person",
        "properties": {
            "name": ["Viktor Petrov", "Viktor Ivanovich Petrov", "Виктор Петров"],
            "nationality": ["RU"],
            "birthDate": ["1968-11-28"],
            "idNumber": ["RU-12345678"],
            "topics": ["sanction"],
            "notes": ["OFAC SDN List - Specially Designated Nationals"],
        },
        "datasets": ["ofac_sdn", "eu_sanctions"],
    },
    {
        "id": "ofac-sdn-002",
        "schema": "Person",
        "properties": {
            "name": ["Aleksandr Morozov", "Alexander Morozov"],
            "nationality": ["RU"],
            "birthDate": ["1972-05-15"],
            "topics": ["sanction"],
            "notes": ["OFAC SDN List - Energy sector sanctions"],
        },
        "datasets": ["ofac_sdn"],
    },
    {
        "id": "ofac-sdn-003",
        "schema": "Company",
        "properties": {
            "name": ["Rosneft Oil Company", "Rosneft"],
            "jurisdiction": ["RU"],
            "topics": ["sanction"],
            "notes": ["Sectoral sanctions - energy"],
        },
        "datasets": ["ofac_sdn", "eu_sanctions"],
    },
    {
        "id": "eu-sanc-001",
        "schema": "Person",
        "properties": {
            "name": ["Yevgeny Prigozhin"],
            "nationality": ["RU"],
            "birthDate": ["1961-06-01"],
            "topics": ["sanction", "pep"],
            "notes": ["EU sanctions list - Wagner Group association"],
        },
        "datasets": ["eu_sanctions"],
    },
    {
        "id": "un-sanc-001",
        "schema": "Person",
        "properties": {
            "name": ["Kim Jong Un", "Kim Jong-un"],
            "nationality": ["KP"],
            "topics": ["sanction", "pep"],
            "notes": ["UN Security Council sanctions"],
        },
        "datasets": ["un_sanctions"],
    },
    {
        "id": "uk-sanc-001",
        "schema": "Company",
        "properties": {
            "name": ["Huawei Technologies Co., Ltd.", "Huawei"],
            "jurisdiction": ["CN"],
            "topics": ["sanction"],
            "notes": ["UK sanctions - telecom restrictions"],
        },
        "datasets": ["uk_sanctions"],
    },
]

# PEP (Politically Exposed Persons) list
PEP_ENTITIES = [
    {
        "id": "pep-001",
        "schema": "Person",
        "properties": {
            "name": ["Mohammed bin Salman Al Saud", "MBS"],
            "nationality": ["SA"],
            "position": ["Crown Prince of Saudi Arabia"],
            "topics": ["pep"],
        },
        "datasets": ["world_pep"],
    },
    {
        "id": "pep-002",
        "schema": "Person",
        "properties": {
            "name": ["Sheikh Mohammed bin Rashid Al Maktoum"],
            "nationality": ["AE"],
            "position": ["Prime Minister and Vice President of UAE"],
            "topics": ["pep"],
        },
        "datasets": ["world_pep"],
    },
    {
        "id": "pep-003",
        "schema": "Person",
        "properties": {
            "name": ["Viktor Orbán"],
            "nationality": ["HU"],
            "position": ["Prime Minister of Hungary"],
            "topics": ["pep"],
        },
        "datasets": ["world_pep"],
    },
]

# High-risk jurisdictions
HIGH_RISK_JURISDICTIONS = [
    {"code": "KP", "name": "North Korea", "risk_level": "prohibited"},
    {"code": "IR", "name": "Iran", "risk_level": "prohibited"},
    {"code": "SY", "name": "Syria", "risk_level": "prohibited"},
    {"code": "CU", "name": "Cuba", "risk_level": "high"},
    {"code": "VE", "name": "Venezuela", "risk_level": "high"},
    {"code": "RU", "name": "Russia", "risk_level": "high"},
    {"code": "BY", "name": "Belarus", "risk_level": "high"},
    {"code": "MM", "name": "Myanmar", "risk_level": "high"},
    {"code": "AF", "name": "Afghanistan", "risk_level": "high"},
    {"code": "YE", "name": "Yemen", "risk_level": "high"},
]

# Entity behavioral baselines for drift detection
ENTITY_BEHAVIORAL_HISTORY = {
    "Precision Parts GmbH": {
        "entity_id": "target_debtor",
        "baseline_period": "2023-01-01 to 2024-12-31",
        "metrics": {
            "avg_transaction_amount": 12500.00,
            "std_transaction_amount": 3200.00,
            "avg_monthly_volume": 45,
            "avg_monthly_value": 562500.00,
            "typical_counterparties": [
                "BMW AG",
                "Siemens AG",
                "Bosch GmbH",
                "Continental AG",
            ],
            "typical_purposes": ["SUPP", "GDDS"],
            "typical_currencies": ["EUR", "USD"],
            "typical_destinations": ["DE", "FR", "IT", "US"],
            "max_single_transaction": 35000.00,
            "business_hours_percentage": 0.92,
        },
        "drift_thresholds": {
            "amount_zscore": 3.0,
            "new_counterparty_alert": True,
            "new_jurisdiction_alert": True,
            "purpose_change_alert": True,
            "off_hours_threshold": 0.15,
        },
        "recent_anomalies": [
            {
                "date": (datetime.now() - timedelta(days=2)).isoformat(),
                "type": "new_counterparty",
                "details": "First transaction to Al-Ghazali Trading LLC",
                "uetr": "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e",
            },
            {
                "date": (datetime.now() - timedelta(days=2)).isoformat(),
                "type": "amount_anomaly",
                "details": "Transaction amount 75000 EUR exceeds 2x historical max",
                "zscore": 19.5,
                "uetr": "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e",
            },
            {
                "date": (datetime.now() - timedelta(days=2)).isoformat(),
                "type": "new_jurisdiction",
                "details": "First transaction to AE (United Arab Emirates)",
                "uetr": "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e",
            },
        ],
    },
    "Al-Ghazali Trading LLC": {
        "entity_id": "shell_001",
        "baseline_period": "2023-06-15 to 2024-12-31",
        "metrics": {
            "avg_transaction_amount": 85000.00,
            "std_transaction_amount": 45000.00,
            "avg_monthly_volume": 8,
            "avg_monthly_value": 680000.00,
            "typical_counterparties": [
                "Desert Oasis Imports FZE",
                "Golden Sands Consulting DMCC",
            ],
            "typical_purposes": ["INTC", "CONS"],
            "typical_currencies": ["EUR", "USD", "AED"],
            "typical_destinations": ["AE", "BVI", "CY"],
            "max_single_transaction": 250000.00,
            "business_hours_percentage": 0.45,
        },
        "risk_indicators": {
            "shell_company_score": 0.85,
            "dormancy_periods": 3,
            "rapid_fund_movement": True,
            "layering_pattern_detected": True,
            "shared_director_count": 4,
        },
    },
}


def generate_ftm_entities() -> List[Dict]:
    """Generate FollowTheMoney formatted entity file."""
    all_entities = []

    for entity in SANCTIONED_ENTITIES + PEP_ENTITIES:
        ftm_entity = {
            "id": entity["id"],
            "schema": entity["schema"],
            "properties": entity["properties"],
            "datasets": entity["datasets"],
            "referents": [],
            "caption": entity["properties"]["name"][0],
            "first_seen": (
                datetime.now() - timedelta(days=random.randint(365, 1825))
            ).isoformat(),
            "last_seen": datetime.now().isoformat(),
            "target": True,
        }
        all_entities.append(ftm_entity)

    return all_entities


def generate_behavioral_baselines() -> Dict:
    """Generate entity behavioral baselines for drift detection."""
    baselines = {}

    for entity_name, data in ENTITY_BEHAVIORAL_HISTORY.items():
        entity_hash = hashlib.sha256(entity_name.encode()).hexdigest()[:16]
        baselines[entity_hash] = {
            "entity_name": entity_name,
            **data,
            "last_updated": datetime.now().isoformat(),
        }

    return baselines


def generate_negative_news_corpus() -> List[Dict]:
    """Generate sample negative news articles for semantic search."""
    articles = [
        {
            "id": "news-001",
            "headline": "Russian Oligarch Viktor Petrov Linked to Money Laundering Scheme",
            "source": "Financial Times",
            "date": (datetime.now() - timedelta(days=45)).isoformat(),
            "entities_mentioned": ["Viktor Petrov"],
            "keywords": [
                "money laundering",
                "shell companies",
                "UAE",
                "sanctions evasion",
            ],
            "risk_score": 0.95,
            "summary": "Investigation reveals complex web of shell companies in Dubai used to evade Western sanctions.",
        },
        {
            "id": "news-002",
            "headline": "UAE Free Zone Companies Under Scrutiny for Sanctions Circumvention",
            "source": "Reuters",
            "date": (datetime.now() - timedelta(days=30)).isoformat(),
            "entities_mentioned": ["Dubai", "DMCC", "FZE"],
            "keywords": ["sanctions", "shell companies", "trade finance", "UAE"],
            "risk_score": 0.75,
            "summary": "Regulators examining increased use of UAE free zone entities for suspicious trade activities.",
        },
        {
            "id": "news-003",
            "headline": "Al-Ghazali Trading Under Investigation for Suspicious Transactions",
            "source": "Gulf News",
            "date": (datetime.now() - timedelta(days=15)).isoformat(),
            "entities_mentioned": ["Al-Ghazali Trading LLC", "Hassan Al-Rashid"],
            "keywords": ["investigation", "suspicious transactions", "trade finance"],
            "risk_score": 0.90,
            "summary": "Dubai-based trading company faces probe over unusual transaction patterns with European manufacturers.",
        },
    ]
    return articles


def main():
    """Generate all reference data files."""
    print("Generating reference data files...")

    # 1. Generate FTM entities (sanctions + PEP)
    ftm_entities = generate_ftm_entities()
    ftm_path = os.path.join(OUTPUT_DIR, "entities.ftm.json")
    with open(ftm_path, "w") as f:
        for entity in ftm_entities:
            f.write(json.dumps(entity) + "\n")
    print(f"  Created: {ftm_path} ({len(ftm_entities)} entities)")

    # 2. Generate sanctions list (structured)
    sanctions_path = os.path.join(OUTPUT_DIR, "sanctions_list.json")
    with open(sanctions_path, "w") as f:
        json.dump(
            {
                "lists": {
                    "ofac_sdn": {
                        "name": "OFAC Specially Designated Nationals",
                        "source": "US Treasury",
                        "last_updated": datetime.now().isoformat(),
                    },
                    "eu_sanctions": {
                        "name": "EU Consolidated Sanctions List",
                        "source": "European Commission",
                        "last_updated": datetime.now().isoformat(),
                    },
                    "un_sanctions": {
                        "name": "UN Security Council Sanctions",
                        "source": "United Nations",
                        "last_updated": datetime.now().isoformat(),
                    },
                    "uk_sanctions": {
                        "name": "UK Sanctions List",
                        "source": "HM Treasury",
                        "last_updated": datetime.now().isoformat(),
                    },
                },
                "entities": SANCTIONED_ENTITIES,
                "high_risk_jurisdictions": HIGH_RISK_JURISDICTIONS,
            },
            f,
            indent=2,
        )
    print(f"  Created: {sanctions_path}")

    # 3. Generate PEP list
    pep_path = os.path.join(OUTPUT_DIR, "pep_list.json")
    with open(pep_path, "w") as f:
        json.dump(
            {
                "source": "World PEP Database",
                "last_updated": datetime.now().isoformat(),
                "entities": PEP_ENTITIES,
            },
            f,
            indent=2,
        )
    print(f"  Created: {pep_path}")

    # 4. Generate behavioral baselines
    baselines = generate_behavioral_baselines()
    baselines_path = os.path.join(OUTPUT_DIR, "entity_behavioral_baselines.json")
    with open(baselines_path, "w") as f:
        json.dump(baselines, f, indent=2)
    print(f"  Created: {baselines_path}")

    # 5. Generate negative news corpus
    news = generate_negative_news_corpus()
    news_path = os.path.join(OUTPUT_DIR, "negative_news_corpus.json")
    with open(news_path, "w") as f:
        json.dump(news, f, indent=2)
    print(f"  Created: {news_path}")

    # 6. Generate high-risk jurisdictions
    jurisdictions_path = os.path.join(OUTPUT_DIR, "high_risk_jurisdictions.json")
    with open(jurisdictions_path, "w") as f:
        json.dump(
            {
                "last_updated": datetime.now().isoformat(),
                "jurisdictions": HIGH_RISK_JURISDICTIONS,
            },
            f,
            indent=2,
        )
    print(f"  Created: {jurisdictions_path}")

    print("\nReference data generation complete!")
    print(f"  - {len(SANCTIONED_ENTITIES)} sanctioned entities")
    print(f"  - {len(PEP_ENTITIES)} PEP entries")
    print(f"  - {len(HIGH_RISK_JURISDICTIONS)} high-risk jurisdictions")
    print(f"  - {len(ENTITY_BEHAVIORAL_HISTORY)} behavioral baselines")
    print(f"  - {len(news)} negative news articles")


if __name__ == "__main__":
    main()

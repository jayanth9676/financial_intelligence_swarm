"""Generate Neo4j graph topology with fraud ring and shared director patterns."""

import os
import json
from datetime import datetime, timedelta
from typing import Dict
import random

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data_raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Target entities from ISO ingestion
TARGET_UETR = "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"
TARGET_DEBTOR = "Precision Parts GmbH"
TARGET_CREDITOR = "Al-Ghazali Trading LLC"

# Fraud ring entities
FRAUD_RING = {
    "shell_companies": [
        {
            "id": "shell_001",
            "name": "Al-Ghazali Trading LLC",
            "country": "AE",
            "incorporation_date": "2023-06-15",
        },
        {
            "id": "shell_002",
            "name": "Desert Oasis Imports FZE",
            "country": "AE",
            "incorporation_date": "2023-07-22",
        },
        {
            "id": "shell_003",
            "name": "Golden Sands Consulting DMCC",
            "country": "AE",
            "incorporation_date": "2023-08-10",
        },
        {
            "id": "shell_004",
            "name": "Crescent Moon Ventures Ltd",
            "country": "BVI",
            "incorporation_date": "2023-05-01",
        },
    ],
    "shared_director": {
        "id": "dir_001",
        "name": "Hassan Al-Rashid",
        "nationality": "AE",
        "dob": "1975-03-12",
        "pep_status": False,
        "sanctioned": False,
    },
    "beneficial_owner": {
        "id": "bo_001",
        "name": "Viktor Petrov",
        "nationality": "RU",
        "dob": "1968-11-28",
        "pep_status": True,
        "sanctioned": True,
        "sanction_list": "OFAC SDN",
    },
    "bank_accounts": [
        {
            "id": "acc_001",
            "iban": "AE070331234567890123456",
            "bank": "Emirates NBD",
            "company_id": "shell_001",
        },
        {
            "id": "acc_002",
            "iban": "AE080441234567890123457",
            "bank": "Dubai Islamic Bank",
            "company_id": "shell_002",
        },
        {
            "id": "acc_003",
            "iban": "AE090551234567890123458",
            "bank": "Mashreq Bank",
            "company_id": "shell_003",
        },
        {
            "id": "acc_004",
            "iban": "VG96VPVG0000012345678901",
            "bank": "VP Bank BVI",
            "company_id": "shell_004",
        },
    ],
}

# Legitimate entities for noise
LEGITIMATE_ENTITIES = [
    {"id": "legit_001", "name": "BMW AG", "country": "DE", "industry": "Automotive"},
    {
        "id": "legit_002",
        "name": "Siemens AG",
        "country": "DE",
        "industry": "Industrial",
    },
    {"id": "legit_003", "name": "SAP SE", "country": "DE", "industry": "Technology"},
    {"id": "legit_004", "name": "BASF SE", "country": "DE", "industry": "Chemicals"},
    {
        "id": "legit_005",
        "name": "Deutsche Bank AG",
        "country": "DE",
        "industry": "Banking",
    },
]


def generate_cypher_create_statements() -> str:
    """Generate Cypher statements to create the fraud ring topology."""
    statements = []

    statements.append("// ===========================================")
    statements.append("// Financial Intelligence Swarm - Graph Topology")
    statements.append(f"// Generated: {datetime.now().isoformat()}")
    statements.append("// ===========================================\n")

    # Create constraints and indexes
    statements.append("// Constraints and Indexes")
    statements.append(
        "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE;"
    )
    statements.append(
        "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;"
    )
    statements.append(
        "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:BankAccount) REQUIRE a.id IS UNIQUE;"
    )
    statements.append(
        "CREATE CONSTRAINT transaction_uetr IF NOT EXISTS FOR (t:Transaction) REQUIRE t.uetr IS UNIQUE;"
    )
    statements.append(
        "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name);"
    )
    statements.append(
        "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name);"
    )
    statements.append("")

    # Create shell companies (fraud ring)
    statements.append("// Shell Companies (Fraud Ring)")
    for company in FRAUD_RING["shell_companies"]:
        statements.append(f"""
CREATE (c:Company:ShellCompany {{
    id: '{company["id"]}',
    name: '{company["name"]}',
    country: '{company["country"]}',
    incorporation_date: date('{company["incorporation_date"]}'),
    risk_score: 0.85,
    is_shell: true
}});""")

    # Create shared director
    director = FRAUD_RING["shared_director"]
    statements.append("\n// Shared Director (Key Fraud Indicator)")
    statements.append(f"""
CREATE (p:Person:Director {{
    id: '{director["id"]}',
    name: '{director["name"]}',
    nationality: '{director["nationality"]}',
    dob: date('{director["dob"]}'),
    pep_status: {str(director["pep_status"]).lower()},
    sanctioned: {str(director["sanctioned"]).lower()}
}});""")

    # Create beneficial owner (sanctioned)
    bo = FRAUD_RING["beneficial_owner"]
    statements.append("\n// Beneficial Owner (Sanctioned Entity)")
    statements.append(f"""
CREATE (p:Person:BeneficialOwner:Sanctioned {{
    id: '{bo["id"]}',
    name: '{bo["name"]}',
    nationality: '{bo["nationality"]}',
    dob: date('{bo["dob"]}'),
    pep_status: {str(bo["pep_status"]).lower()},
    sanctioned: {str(bo["sanctioned"]).lower()},
    sanction_list: '{bo["sanction_list"]}'
}});""")

    # Create bank accounts
    statements.append("\n// Bank Accounts")
    for account in FRAUD_RING["bank_accounts"]:
        statements.append(f"""
CREATE (a:BankAccount {{
    id: '{account["id"]}',
    iban: '{account["iban"]}',
    bank: '{account["bank"]}',
    opened_date: date('{(datetime.now() - timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d")}')
}});""")

    # Create legitimate companies
    statements.append("\n// Legitimate Companies (Noise)")
    for entity in LEGITIMATE_ENTITIES:
        statements.append(f"""
CREATE (c:Company {{
    id: '{entity["id"]}',
    name: '{entity["name"]}',
    country: '{entity["country"]}',
    industry: '{entity["industry"]}',
    risk_score: {random.uniform(0.1, 0.3):.2f},
    is_shell: false
}});""")

    # Create target debtor company
    statements.append("\n// Target Debtor Company")
    statements.append(f"""
CREATE (c:Company {{
    id: 'target_debtor',
    name: '{TARGET_DEBTOR}',
    country: 'DE',
    industry: 'Manufacturing',
    risk_score: 0.25,
    is_shell: false
}});""")

    # Create the target transaction as a reified node
    statements.append("\n// Target Transaction (Reified Node)")
    statements.append(f"""
CREATE (t:Transaction {{
    uetr: '{TARGET_UETR}',
    amount: 75000.00,
    currency: 'EUR',
    purpose: 'SUPP',
    remittance_info: 'Industrial equipment - Q4 order',
    timestamp: datetime(),
    risk_score: 0.0,
    status: 'pending_review'
}});""")

    # Create relationships
    statements.append("\n// ===========================================")
    statements.append("// RELATIONSHIPS")
    statements.append("// ===========================================\n")

    # Director -> Shell Companies (SHARED_DIRECTOR pattern)
    statements.append("// Shared Director Pattern (Key Fraud Indicator)")
    for company in FRAUD_RING["shell_companies"]:
        statements.append(f"""
MATCH (p:Person {{id: '{director["id"]}'}}), (c:Company {{id: '{company["id"]}'}})
CREATE (p)-[:DIRECTOR_OF {{appointed_date: date('{company["incorporation_date"]}'), role: 'Managing Director'}}]->(c);""")

    # Beneficial Owner -> Shell Companies (hidden ownership)
    statements.append("\n// Hidden Beneficial Ownership")
    for company in FRAUD_RING["shell_companies"]:
        ownership_pct = random.randint(25, 100)
        statements.append(f"""
MATCH (p:Person {{id: '{bo["id"]}'}}), (c:Company {{id: '{company["id"]}'}})
CREATE (p)-[:BENEFICIAL_OWNER_OF {{ownership_percentage: {ownership_pct}, disclosed: false}}]->(c);""")

    # Bank Accounts -> Companies
    statements.append("\n// Bank Account Ownership")
    for account in FRAUD_RING["bank_accounts"]:
        statements.append(f"""
MATCH (a:BankAccount {{id: '{account["id"]}'}}), (c:Company {{id: '{account["company_id"]}'}})
CREATE (c)-[:OWNS_ACCOUNT]->(a);""")

    # Transaction relationships
    statements.append("\n// Transaction Relationships (Reified Model)")
    statements.append(f"""
MATCH (t:Transaction {{uetr: '{TARGET_UETR}'}}), 
      (debtor:Company {{name: '{TARGET_DEBTOR}'}}),
      (creditor:Company {{name: '{TARGET_CREDITOR}'}})
CREATE (debtor)-[:INITIATES]->(t),
       (t)-[:PAYS]->(creditor);""")

    # Inter-company transactions (layering pattern)
    statements.append("\n// Layering Pattern (Inter-Shell Transactions)")
    shell_ids = [c["id"] for c in FRAUD_RING["shell_companies"]]
    for i, src_id in enumerate(shell_ids[:-1]):
        dst_id = shell_ids[i + 1]
        amount = random.uniform(50000, 200000)
        statements.append(f"""
MATCH (src:Company {{id: '{src_id}'}}), (dst:Company {{id: '{dst_id}'}})
CREATE (layering_tx_{i}:Transaction {{
    uetr: '{str(__import__("uuid").uuid4())}',
    amount: {amount:.2f},
    currency: 'EUR',
    purpose: 'INTC',
    timestamp: datetime() - duration({{days: {random.randint(1, 30)}}})
}})
CREATE (src)-[:INITIATES]->(layering_tx_{i})-[:PAYS]->(dst);""")

    return "\n".join(statements)


def generate_cypher_queries() -> str:
    """Generate useful Cypher queries for fraud detection."""
    queries = []

    queries.append("// ===========================================")
    queries.append("// FRAUD DETECTION QUERIES")
    queries.append("// ===========================================\n")

    # Query 1: Find shared directors
    queries.append("// Query 1: Find Shared Directors (Fraud Ring Indicator)")
    queries.append("""
MATCH (p:Person)-[:DIRECTOR_OF]->(c:Company)
WITH p, collect(c) as companies
WHERE size(companies) > 1
RETURN p.name as director, 
       [c in companies | c.name] as companies,
       size(companies) as company_count
ORDER BY company_count DESC;
""")

    # Query 2: Find sanctioned beneficial owners
    queries.append("// Query 2: Find Sanctioned Beneficial Owners")
    queries.append("""
MATCH (p:Person:Sanctioned)-[:BENEFICIAL_OWNER_OF]->(c:Company)
RETURN p.name as sanctioned_person,
       p.sanction_list as sanction_list,
       c.name as company,
       p.nationality as nationality;
""")

    # Query 3: Trace transaction path
    queries.append("// Query 3: Trace Transaction Path (Follow the Money)")
    queries.append(f"""
MATCH path = (debtor:Company)-[:INITIATES]->(t:Transaction)-[:PAYS]->(creditor:Company)
WHERE t.uetr = '{TARGET_UETR}'
OPTIONAL MATCH (creditor)<-[:DIRECTOR_OF]-(director:Person)
OPTIONAL MATCH (creditor)<-[:BENEFICIAL_OWNER_OF]-(bo:Person)
RETURN debtor.name as debtor,
       t.amount as amount,
       creditor.name as creditor,
       collect(DISTINCT director.name) as directors,
       collect(DISTINCT bo.name) as beneficial_owners;
""")

    # Query 4: Find layering patterns
    queries.append("// Query 4: Detect Layering Patterns")
    queries.append("""
MATCH path = (c1:ShellCompany)-[:INITIATES]->(:Transaction)-[:PAYS]->(c2:ShellCompany)
             -[:INITIATES]->(:Transaction)-[:PAYS]->(c3:ShellCompany)
RETURN [n in nodes(path) | 
        CASE 
            WHEN n:Company THEN n.name 
            WHEN n:Transaction THEN '$' + toString(n.amount)
        END] as money_flow;
""")

    # Query 5: Risk scoring
    queries.append("// Query 5: Calculate Entity Risk Score")
    queries.append("""
MATCH (c:Company)
OPTIONAL MATCH (c)<-[:DIRECTOR_OF]-(d:Person)
OPTIONAL MATCH (c)<-[:BENEFICIAL_OWNER_OF]-(bo:Person)
WITH c, 
     count(DISTINCT d) as director_count,
     any(bo IN collect(bo) WHERE bo.sanctioned = true) as has_sanctioned_bo,
     c.is_shell as is_shell
RETURN c.name as company,
       CASE 
           WHEN has_sanctioned_bo THEN 1.0
           WHEN is_shell THEN 0.85
           WHEN director_count > 3 THEN 0.5
           ELSE 0.2
       END as calculated_risk
ORDER BY calculated_risk DESC;
""")

    return "\n".join(queries)


def generate_graph_json() -> Dict:
    """Generate graph data as JSON for alternative loading."""
    return {
        "nodes": {
            "companies": FRAUD_RING["shell_companies"]
            + [{"id": "target_debtor", "name": TARGET_DEBTOR, "country": "DE"}]
            + LEGITIMATE_ENTITIES,
            "persons": [FRAUD_RING["shared_director"], FRAUD_RING["beneficial_owner"]],
            "accounts": FRAUD_RING["bank_accounts"],
            "transactions": [
                {
                    "uetr": TARGET_UETR,
                    "amount": 75000.00,
                    "currency": "EUR",
                    "debtor": TARGET_DEBTOR,
                    "creditor": TARGET_CREDITOR,
                }
            ],
        },
        "relationships": {
            "director_of": [
                {"from": FRAUD_RING["shared_director"]["id"], "to": c["id"]}
                for c in FRAUD_RING["shell_companies"]
            ],
            "beneficial_owner_of": [
                {"from": FRAUD_RING["beneficial_owner"]["id"], "to": c["id"]}
                for c in FRAUD_RING["shell_companies"]
            ],
            "owns_account": [
                {"from": a["company_id"], "to": a["id"]}
                for a in FRAUD_RING["bank_accounts"]
            ],
        },
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "target_uetr": TARGET_UETR,
            "fraud_indicators": [
                "shared_director_pattern",
                "sanctioned_beneficial_owner",
                "shell_company_network",
                "layering_transactions",
            ],
        },
    }


def main():
    """Generate all graph topology files."""
    print("Generating Neo4j graph topology...")

    # Generate Cypher create statements
    cypher_create = generate_cypher_create_statements()
    cypher_path = os.path.join(OUTPUT_DIR, "graph_topology.cypher")
    with open(cypher_path, "w") as f:
        f.write(cypher_create)
    print(f"  Created: {cypher_path}")

    # Generate Cypher queries
    cypher_queries = generate_cypher_queries()
    queries_path = os.path.join(OUTPUT_DIR, "fraud_detection_queries.cypher")
    with open(queries_path, "w") as f:
        f.write(cypher_queries)
    print(f"  Created: {queries_path}")

    # Generate JSON representation
    graph_json = generate_graph_json()
    json_path = os.path.join(OUTPUT_DIR, "graph_topology.json")
    with open(json_path, "w") as f:
        json.dump(graph_json, f, indent=2)
    print(f"  Created: {json_path}")

    print("\nGraph topology generated with:")
    print(f"  - {len(FRAUD_RING['shell_companies'])} shell companies")
    print("  - 1 shared director (fraud ring indicator)")
    print("  - 1 sanctioned beneficial owner")
    print(f"  - {len(FRAUD_RING['bank_accounts'])} bank accounts")
    print(f"  - {len(LEGITIMATE_ENTITIES)} legitimate companies (noise)")


if __name__ == "__main__":
    main()

"""Load data into Neo4j graph database."""

import os
import json

import xmltodict
from neo4j import GraphDatabase

from backend.config import settings

DATA_RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "data_raw")


def get_driver():
    """Get Neo4j driver."""
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )


def setup_schema(driver):
    """Create constraints and indexes."""
    schema_queries = [
        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
        "CREATE CONSTRAINT account_iban IF NOT EXISTS FOR (a:Account) REQUIRE a.iban IS UNIQUE",
        "CREATE CONSTRAINT transaction_uetr IF NOT EXISTS FOR (t:Transaction) REQUIRE t.uetr IS UNIQUE",
        "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
        "CREATE INDEX transaction_date IF NOT EXISTS FOR (t:Transaction) ON (t.date)",
    ]

    with driver.session() as session:
        for query in schema_queries:
            try:
                session.run(query)
                print(f"Executed: {query[:50]}...")
            except Exception as e:
                print(f"Schema query failed (may already exist): {e}")


def load_sanctions_list(driver, filepath: str):
    """Load sanctions list as :Sanctioned entities."""
    if not os.path.exists(filepath):
        print(f"Sanctions file not found: {filepath}")
        return 0

    with open(filepath, "r") as f:
        data = json.load(f)

    entities = data if isinstance(data, list) else data.get("entities", [])

    with driver.session() as session:
        for entity in entities:
            props = entity.get("properties", {})
            name = (
                props.get("name", ["Unknown"])[0]
                if props.get("name")
                else entity.get("id", "Unknown")
            )
            sanctions = props.get("sanctions", [])
            session.run(
                """
                MERGE (e:Entity:Sanctioned {name: $name})
                SET e.entity_id = $entity_id,
                    e.sanctions = $sanctions,
                    e.source = 'sanctions_list'
                """,
                name=name,
                entity_id=entity.get("id", ""),
                sanctions=sanctions,
            )

    print(f"Loaded {len(entities)} sanctioned entities")
    return len(entities)


def load_fraud_ring_topology(driver, cypher_file: str | None = None):
    """Load fraud ring topology from Cypher file."""
    if cypher_file and os.path.exists(cypher_file):
        with open(cypher_file, "r") as f:
            topology_query = f.read()
    else:
        default_path = os.path.join(DATA_RAW_DIR, "graph_topology_seed.cypher")
        if os.path.exists(default_path):
            with open(default_path, "r") as f:
                topology_query = f.read()
        else:
            # Use MERGE for all relationships to make idempotent (can re-run safely)
            topology_query = """
            // Core fraud ring entities
            MERGE (ring_leader:Entity:HighRisk {name: "Viktor Petrov"})
            SET ring_leader.type = "Person"
            MERGE (shell1:Entity {name: "Global Ventures Ltd"})
            SET shell1.type = "Company"
            MERGE (shell2:Entity {name: "Eastern Trading Co"})
            SET shell2.type = "Company"
            MERGE (shell3:Entity {name: "Euroasia Investments"})
            SET shell3.type = "Company"
            MERGE (director:Entity:PEP {name: "Dr. A. Schmidt"})
            SET director.type = "Person", director.role = "Director"
            MERGE (target:Entity {name: "Precision Parts GmbH"})
            SET target.type = "Company"
            MERGE (sanctioned:Entity:Sanctioned {name: "Al-Ghazali Trading LLC"})
            SET sanctioned.type = "Company", sanctioned.jurisdiction = "UAE", sanctioned.sanctions_program = "OFAC"
            
            // Target UETR entities for demo
            MERGE (shell_alpha:Entity:HighRisk {name: "Shell Company Alpha"})
            SET shell_alpha.type = "Company"
            MERGE (offshore:Entity {name: "Offshore Holdings LLC"})
            SET offshore.type = "Company"
            MERGE (shared_director:Entity:PEP {name: "John Dmitri"})
            SET shared_director.type = "Person", shared_director.role = "Director"
            
            // Accounts for target entities
            MERGE (shell_alpha_acct:Account {iban: "DE89370400440532013000"})
            MERGE (offshore_acct:Account {iban: "CH9300762011623852957"})
            
            // Create fraud ring relationships (using MERGE for idempotency)
            MERGE (ring_leader)-[:CONTROLS]->(shell1)
            MERGE (ring_leader)-[:CONTROLS]->(shell2)
            MERGE (shell1)-[sf1:SENT_FUNDS]->(shell2)
            SET sf1.amount = 500000, sf1.date = "2025-06-15"
            MERGE (shell2)-[sf2:SENT_FUNDS]->(shell3)
            SET sf2.amount = 450000, sf2.date = "2025-06-20"
            MERGE (shell3)-[sf3:SENT_FUNDS]->(shell1)
            SET sf3.amount = 400000, sf3.date = "2025-06-25"
            MERGE (director)-[:DIRECTOR_OF]->(target)
            MERGE (director)-[:ADVISOR_TO]->(shell1)
            MERGE (director)-[sa:SHARES_ADDRESS]->(ring_leader)
            SET sa.address = "Zurich, Switzerland"
            MERGE (target)-[sf4:SENT_FUNDS]->(sanctioned)
            SET sf4.amount = 75000, sf4.date = "2026-02-03"
            
            // Target UETR relationships - Shell Company Alpha to Offshore Holdings LLC
            // Shared director creates hidden link to sanctioned entity
            MERGE (shared_director)-[:DIRECTOR_OF]->(shell_alpha)
            MERGE (shared_director)-[:DIRECTOR_OF]->(offshore)
            MERGE (shared_director)-[:SHARES_DIRECTOR]->(sanctioned)
            MERGE (shell_alpha)-[:HAS_ACCOUNT]->(shell_alpha_acct)
            MERGE (offshore)-[:HAS_ACCOUNT]->(offshore_acct)
            
            // Target transaction with UETR
            MERGE (tx_target:Transaction {uetr: "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"})
            SET tx_target.amount = 245000, tx_target.currency = "EUR", tx_target.date = "2026-02-03"
            MERGE (shell_alpha)-[:SENT_FUNDS]->(tx_target)
            MERGE (tx_target)-[:RECEIVED_FUNDS]->(offshore)
            """

    # First, clean up any conflicting nodes with similar names (case variations)
    cleanup_queries = [
        "MATCH (e:Entity) WHERE e.name =~ '(?i)Precision Parts Gmbh' DETACH DELETE e",
    ]

    with driver.session() as session:
        # Run cleanup first
        for cleanup in cleanup_queries:
            try:
                session.run(cleanup)
            except Exception:
                pass  # Ignore cleanup errors

        # Run the topology query
        try:
            session.run(topology_query)
            print("Loaded fraud ring topology successfully")
        except Exception as e:
            print(f"Topology loading failed: {e}")
            # Try splitting by semicolon for files with multiple statements
            for statement in topology_query.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("//"):
                    try:
                        session.run(statement)
                    except Exception as stmt_e:
                        print(f"Statement failed: {stmt_e}")


def load_transactions_from_xml(driver, xml_dir: str, limit: int = 100):
    """Load transactions from XML files into the graph.

    Supports both individual pacs.008 files and batch/high-volume files.
    """
    if not os.path.exists(xml_dir):
        print(f"XML directory not found: {xml_dir}")
        return 0

    xml_files = [
        f for f in os.listdir(xml_dir) if f.endswith(".xml") and "pacs.008" in f
    ]

    loaded = 0
    for filename in xml_files[:limit]:
        filepath = os.path.join(xml_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                xml_content = f.read()

            doc = xmltodict.parse(xml_content)

            # Handle batch documents with wrapper elements
            if "BatchDocument" in doc:
                documents = doc["BatchDocument"].get("Document", [])
                if not isinstance(documents, list):
                    documents = [documents]
            elif "Documents" in doc:
                documents = doc["Documents"].get("Document", [])
                if not isinstance(documents, list):
                    documents = [documents]
            else:
                # Single document
                documents = [doc]

            for single_doc in documents:
                root = single_doc.get("Document", single_doc)
                fi_to_fi = root.get("FIToFICstmrCdtTrf", {})
                cdt_trf_list = fi_to_fi.get("CdtTrfTxInf", [])

                if not isinstance(cdt_trf_list, list):
                    cdt_trf_list = [cdt_trf_list] if cdt_trf_list else []

                with driver.session() as session:
                    for cdt_trf in cdt_trf_list:
                        if not cdt_trf:
                            continue
                        pmt_id = cdt_trf.get("PmtId", {})
                        uetr = pmt_id.get("UETR", "")
                        if not uetr:
                            continue

                        dbtr = cdt_trf.get("Dbtr", {})
                        cdtr = cdt_trf.get("Cdtr", {})

                        amt = cdt_trf.get("IntrBkSttlmAmt", {})
                        if isinstance(amt, dict):
                            amount = float(amt.get("#text", 0))
                            currency = amt.get("@Ccy", "EUR")
                        else:
                            amount = float(amt) if amt else 0
                            currency = "EUR"

                        session.run(
                            """
                            MERGE (d:Entity {name: $debtor})
                            MERGE (c:Entity {name: $creditor})
                            MERGE (t:Transaction {uetr: $uetr})
                            SET t.amount = $amount,
                                t.currency = $currency,
                                t.end_to_end_id = $e2e_id
                            MERGE (d)-[:SENT_FUNDS]->(t)
                            MERGE (t)-[:RECEIVED_FUNDS]->(c)
                            """,
                            debtor=dbtr.get("Nm", "Unknown"),
                            creditor=cdtr.get("Nm", "Unknown"),
                            uetr=uetr,
                            amount=amount,
                            currency=currency,
                            e2e_id=pmt_id.get("EndToEndId", ""),
                        )
                        loaded += 1

        except Exception as e:
            print(f"Failed to load {filename}: {e}")

    print(f"Loaded {loaded} transactions from XML")
    return loaded


def main():
    """Main loader function."""
    print("=" * 50)
    print("NEO4J GRAPH LOADER")
    print("=" * 50)

    print("\nInitializing Neo4j connection...")
    driver = get_driver()

    try:
        driver.verify_connectivity()
        print("Connected to Neo4j successfully")
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        return

    print("\nSetting up schema...")
    setup_schema(driver)

    print("\nLoading fraud ring topology...")
    load_fraud_ring_topology(driver)

    sanctions_path = os.path.join(DATA_RAW_DIR, "entities.ftm.json")
    if os.path.exists(sanctions_path):
        print("\nLoading sanctions list...")
        load_sanctions_list(driver, sanctions_path)

    if os.path.exists(DATA_RAW_DIR):
        print("\nLoading transactions from XML...")
        load_transactions_from_xml(driver, DATA_RAW_DIR, limit=100)

    driver.close()
    print("\nGraph loading complete!")


if __name__ == "__main__":
    main()

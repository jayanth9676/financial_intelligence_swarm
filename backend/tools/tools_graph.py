"""Neo4j graph tools for fraud detection."""

from typing import Any, Dict

from langchain_core.tools import tool
from neo4j import GraphDatabase

from backend.config import settings

_driver = None


def get_driver():
    """Get Neo4j driver singleton."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
    return _driver


@tool
def find_hidden_links(entity_name: str, max_hops: int = 3) -> Dict[str, Any]:
    """Find shortest paths between an entity and any sanctioned/high-risk entities.

    Args:
        entity_name: Name of the entity to investigate
        max_hops: Maximum relationship hops to search (default 3)

    Returns:
        Dict with paths to sanctioned entities and risk indicators
    """
    # Validate and clamp max_hops to safe range
    max_hops = max(1, min(int(max_hops), 10))

    query = """
    MATCH (start:Entity {name: $entity_name})
    MATCH (risk:Entity) WHERE risk:Sanctioned OR risk:HighRisk OR risk:PEP
    MATCH path = shortestPath((start)-[*1..{max_hops}]-(risk))
    RETURN path, length(path) as distance, risk.name as risk_entity, labels(risk) as risk_labels
    ORDER BY distance
    LIMIT 10
    """.replace("{max_hops}", str(max_hops))

    try:
        with get_driver().session() as session:
            result = session.run(query, entity_name=entity_name)
            paths = []
            for record in result:
                path_data = {
                    "distance": record["distance"],
                    "risk_entity": record["risk_entity"],
                    "risk_labels": record["risk_labels"],
                    "path_nodes": [node["name"] for node in record["path"].nodes],
                }
                paths.append(path_data)

            return {
                "entity": entity_name,
                "connections_found": len(paths),
                "paths": paths,
                "has_hidden_links": len(paths) > 0,
            }
    except Exception as e:
        return {
            "entity": entity_name,
            "connections_found": 0,
            "paths": [],
            "has_hidden_links": False,
            "error": str(e),
        }


@tool
def detect_fraud_rings() -> Dict[str, Any]:
    """Detect potential fraud rings using Weakly Connected Components algorithm.

    Returns:
        Dict with identified communities and their risk scores
    """
    import uuid

    # Use unique graph name to avoid race conditions
    graph_name = f"fraud_detection_{uuid.uuid4().hex[:8]}"

    project_query = f"""
    CALL gds.graph.project.cypher(
        '{graph_name}',
        'MATCH (n:Entity) RETURN id(n) AS id',
        'MATCH (n:Entity)-[r:SENT_FUNDS|RECEIVED_FUNDS|SHARES_DIRECTOR|SHARES_ADDRESS]-(m:Entity) 
         RETURN id(n) AS source, id(m) AS target'
    )
    """

    wcc_query = f"""
    CALL gds.wcc.stream('{graph_name}')
    YIELD nodeId, componentId
    WITH componentId, collect(gds.util.asNode(nodeId).name) AS members
    WHERE size(members) > 2
    RETURN componentId, members, size(members) AS ring_size
    ORDER BY ring_size DESC
    LIMIT 10
    """

    cleanup_query = f"CALL gds.graph.drop('{graph_name}', false)"

    with get_driver().session() as session:
        try:
            session.run(project_query)
            result = session.run(wcc_query)
            rings = [
                {
                    "component_id": r["componentId"],
                    "members": r["members"],
                    "size": r["ring_size"],
                }
                for r in result
            ]
        except Exception as e:
            # Always try to cleanup even on error
            try:
                session.run(cleanup_query)
            except Exception:
                pass
            return {
                "error": str(e),
                "rings": [],
                "rings_detected": 0,
                "high_risk": False,
            }
        finally:
            # Ensure cleanup happens
            try:
                session.run(cleanup_query)
            except Exception:
                pass

        return {
            "rings_detected": len(rings),
            "rings": rings,
            "high_risk": any(r["size"] > 5 for r in rings),
        }


@tool
def analyze_transaction_topology(uetr: str) -> Dict[str, Any]:
    """Analyze the network topology around a specific transaction.

    Args:
        uetr: Unique End-to-End Transaction Reference

    Returns:
        Dict with transaction parties and their network metrics
    """
    query = """
    MATCH (t:Transaction {uetr: $uetr})
    OPTIONAL MATCH (d:Entity)-[:SENT_FUNDS]->(t)
    OPTIONAL MATCH (t)-[:RECEIVED_FUNDS]->(c:Entity)
    OPTIONAL MATCH (d)-[:HAS_ACCOUNT]->(da:Account)
    OPTIONAL MATCH (c)-[:HAS_ACCOUNT]->(ca:Account)
    
    // Get transaction count for debtor
    OPTIONAL MATCH (d)-[:SENT_FUNDS]->(other_tx:Transaction)
    WITH t, d, c, da, ca, count(other_tx) as debtor_tx_count
    
    // Check for shared directors/addresses
    OPTIONAL MATCH (d)-[:SHARES_DIRECTOR|SHARES_ADDRESS]-(connected:Entity)
    
    RETURN t, d.name as debtor, c.name as creditor,
           da.iban as debtor_account, ca.iban as creditor_account,
           debtor_tx_count,
           collect(DISTINCT connected.name) as connected_entities
    """

    try:
        with get_driver().session() as session:
            result = session.run(query, uetr=uetr)
            record = result.single()

            if not record:
                return {"error": "Transaction not found", "uetr": uetr}

            return {
                "uetr": uetr,
                "debtor": record["debtor"],
                "creditor": record["creditor"],
                "debtor_account": record["debtor_account"],
                "creditor_account": record["creditor_account"],
                "debtor_transaction_count": record["debtor_tx_count"],
                "connected_entities": record["connected_entities"],
                "network_complexity": "high"
                if len(record["connected_entities"]) > 3
                else "low",
            }
    except Exception as e:
        return {"error": str(e), "uetr": uetr}


@tool
def find_layering_patterns(
    entity_name: str, min_cycle_length: int = 3, max_cycle_length: int = 6
) -> Dict[str, Any]:
    """Detect circular money flows (layering) involving an entity.

    Args:
        entity_name: Name of the entity to check
        min_cycle_length: Minimum cycle length to detect
        max_cycle_length: Maximum cycle length to detect

    Returns:
        Dict with detected cycles and layering risk score
    """
    # Validate and clamp cycle lengths
    min_cycle_length = max(2, min(int(min_cycle_length), 10))
    max_cycle_length = max(min_cycle_length, min(int(max_cycle_length), 10))

    query = """
    MATCH path = (start:Entity {name: $entity_name})-[:SENT_FUNDS*{min}..{max}]->(start)
    RETURN [node IN nodes(path) | node.name] AS cycle_members,
           length(path) AS cycle_length,
           reduce(total = 0, rel IN relationships(path) | total + rel.amount) AS total_flow
    LIMIT 5
    """.replace("{min}", str(min_cycle_length)).replace("{max}", str(max_cycle_length))

    try:
        with get_driver().session() as session:
            result = session.run(query, entity_name=entity_name)
            cycles = [
                {
                    "members": r["cycle_members"],
                    "length": r["cycle_length"],
                    "total_flow": r["total_flow"],
                }
                for r in result
            ]

            return {
                "entity": entity_name,
                "cycles_detected": len(cycles),
                "cycles": cycles,
                "layering_risk": "high" if len(cycles) > 0 else "low",
            }
    except Exception as e:
        return {
            "entity": entity_name,
            "cycles_detected": 0,
            "cycles": [],
            "layering_risk": "unknown",
            "error": str(e),
        }

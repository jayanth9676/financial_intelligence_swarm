# Graph Investigator Skill

## Purpose
Investigate financial entities using Neo4j graph database to discover hidden relationships, fraud rings, and connections to sanctioned parties.

## When to Use
- Investigating a transaction for hidden links to sanctioned entities
- Detecting fraud ring patterns in payment networks
- Analyzing transaction topology and layering patterns
- Finding beneficial ownership connections

## Available Tools

### 1. `find_hidden_links`
Find shortest paths between an entity and sanctioned/high-risk parties.

```python
from backend.tools.tools_graph import find_hidden_links

result = find_hidden_links.invoke({
    "entity_name": "Shell Company Alpha",
    "max_hops": 3
})

# Returns:
# {
#     "has_hidden_links": True,
#     "paths": [{"start": "...", "end": "...", "path": [...]}],
#     "risk_score": 0.85
# }
```

### 2. `detect_fraud_rings`
Use Weakly Connected Components (WCC) algorithm to identify fraud ring clusters.

```python
from backend.tools.tools_graph import detect_fraud_rings

result = detect_fraud_rings.invoke({})

# Returns:
# {
#     "high_risk": True,
#     "components": [{"id": 1, "size": 5, "entities": [...]}],
#     "largest_component_size": 5
# }
```

### 3. `analyze_transaction_topology`
Analyze the network structure around a specific transaction.

```python
from backend.tools.tools_graph import analyze_transaction_topology

result = analyze_transaction_topology.invoke({
    "uetr": "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"
})

# Returns network metrics: degree, centrality, clustering coefficient
```

### 4. `find_layering_patterns`
Detect circular money flows indicating layering/structuring.

```python
from backend.tools.tools_graph import find_layering_patterns

result = find_layering_patterns.invoke({
    "entity_name": "Shell Company Alpha",
    "min_cycle_length": 3,
    "max_cycle_length": 6
})

# Returns:
# {
#     "layering_risk": "high",
#     "cycles_found": 2,
#     "cycles": [...]
# }
```

## Graph Schema

```cypher
// Nodes
(:Entity {name, type, jurisdiction, sanctions_status})
(:Account {iban, bic, currency})
(:Transaction {uetr, amount, currency, timestamp, status})
(:Director {name, nationality})

// Relationships
(:Entity)-[:OWNS]->(:Account)
(:Entity)-[:HAS_DIRECTOR]->(:Director)
(:Account)-[:SENDS]->(:Transaction)
(:Transaction)-[:RECEIVES]->(:Account)
(:Entity)-[:SANCTIONED_BY]->(:SanctionsList)
```

## Key Patterns to Detect

### Shared Director (Hidden Link)
```cypher
MATCH (e1:Entity)-[:HAS_DIRECTOR]->(d:Director)<-[:HAS_DIRECTOR]-(e2:Entity)
WHERE e2.sanctions_status = 'sanctioned'
RETURN e1, d, e2
```

### Fraud Ring (WCC)
```cypher
CALL gds.wcc.stream('fraud_graph')
YIELD nodeId, componentId
WHERE size(collect(nodeId)) > 3
RETURN componentId, collect(gds.util.asNode(nodeId).name)
```

### Layering (Cycles)
```cypher
MATCH path = (start:Entity)-[:PAYS*3..6]->(start)
RETURN path, length(path) as cycle_length
```

## Risk Scoring

| Finding | Risk Score Impact |
|---------|-------------------|
| Hidden link to sanctioned entity | +0.8 |
| Fraud ring membership | +0.9 |
| Layering pattern detected | +0.85 |
| Shared director with high-risk entity | +0.7 |

## Integration with Prosecutor Agent

The Prosecutor agent uses these tools to build an indictment:

```python
from backend.agents.prosecutor import prosecutor_agent

# Tools are automatically bound to the LLM
# Prosecutor will call find_hidden_links, detect_fraud_rings, etc.
# based on the transaction context
```

## Error Handling

All tools return error dicts instead of raising exceptions:

```python
result = find_hidden_links.invoke({"entity_name": "Unknown"})
if "error" in result:
    # Handle gracefully
    print(f"Graph query failed: {result['error']}")
```

## Prerequisites

- Neo4j 5.x with APOC and Graph Data Science plugins
- Environment variables: `NEO4J_URI`, `NEO4J_PASSWORD`

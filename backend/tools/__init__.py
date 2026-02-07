"""Tools package for the Financial Intelligence Swarm."""

from backend.tools.tools_graph import (
    find_hidden_links,
    detect_fraud_rings,
    analyze_transaction_topology,
    find_layering_patterns,
)

from backend.tools.tools_docs import (
    search_alibi,
    consult_regulation,
    search_payment_justification,
    search_adverse_media,
)

from backend.tools.tools_memory import (
    check_behavioral_drift,
    get_entity_profile,
    store_investigation_finding,
    compare_to_peer_group,
    get_investigation_history,
)

from backend.tools.tools_iso import (
    parse_pacs008,
    parse_pain001,
    parse_camt053,
    detect_structuring_pattern,
)

from backend.tools.tools_alerts import (
    check_velocity,
    detect_structuring,
    check_jurisdiction_risk,
    detect_round_amounts,
    analyze_transaction_patterns,
    create_alert,
    get_alert_queue,
    clear_alert_queue,
)

__all__ = [
    # Graph tools
    "find_hidden_links",
    "detect_fraud_rings",
    "analyze_transaction_topology",
    "find_layering_patterns",
    # Document tools
    "search_alibi",
    "consult_regulation",
    "search_payment_justification",
    "search_adverse_media",
    # Memory tools
    "check_behavioral_drift",
    "get_entity_profile",
    "store_investigation_finding",
    "compare_to_peer_group",
    "get_investigation_history",
    # ISO tools
    "parse_pacs008",
    "parse_pain001",
    "parse_camt053",
    "detect_structuring_pattern",
    # Alert tools
    "check_velocity",
    "detect_structuring",
    "check_jurisdiction_risk",
    "detect_round_amounts",
    "analyze_transaction_patterns",
    "create_alert",
    "get_alert_queue",
    "clear_alert_queue",
]

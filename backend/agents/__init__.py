"""Agents package for the Financial Intelligence Swarm."""

from backend.agents.prosecutor import prosecutor_agent
from backend.agents.skeptic import skeptic_agent
from backend.agents.judge import judge_agent
from backend.agents.monitor import (
    monitor_agent,
    monitor_transaction,
    monitor_batch,
    get_monitoring_thresholds,
    get_high_risk_jurisdictions,
)
from backend.agents.compliance_reviewer import (
    compliance_review_agent,
    get_compliance_deadlines,
    get_compliance_status,
    generate_compliance_report,
)
from backend.agents.partner_fraud import (
    partner_fraud_agent,
    analyze_partner_network,
    detect_circular_referrals,
    get_partner_risk_score,
)
from backend.agents.reconciliation import (
    reconciliation_agent,
    match_transactions,
    get_reconciliation_status,
)

__all__ = [
    # Core investigation agents
    "prosecutor_agent",
    "skeptic_agent",
    "judge_agent",
    # Monitoring
    "monitor_agent",
    "monitor_transaction",
    "monitor_batch",
    "get_monitoring_thresholds",
    "get_high_risk_jurisdictions",
    # Compliance
    "compliance_review_agent",
    "get_compliance_deadlines",
    "get_compliance_status",
    "generate_compliance_report",
    # Partner fraud
    "partner_fraud_agent",
    "analyze_partner_network",
    "detect_circular_referrals",
    "get_partner_risk_score",
    # Reconciliation
    "reconciliation_agent",
    "match_transactions",
    "get_reconciliation_status",
]


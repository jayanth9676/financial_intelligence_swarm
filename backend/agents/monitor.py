"""Transaction Monitor Agent for real-time pattern detection.

This agent performs continuous monitoring of transactions for:
- Velocity anomalies (rapid successive transactions)
- Structuring patterns (amounts just below thresholds)
- High-risk jurisdiction involvement
- Round amount detection
- Cross-border suspicious patterns

It can operate in both real-time streaming mode and batch processing mode.
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from backend.models.state import AgentState
from backend.tools.tools_alerts import (
    check_velocity,
    detect_structuring,
    check_jurisdiction_risk,
    detect_round_amounts,
    analyze_transaction_patterns,
    create_alert,
    get_alert_queue,
    _analyze_transaction_patterns,
    _create_alert,
)
from backend.llm_provider import get_llm, invoke_with_fallback


MONITOR_SYSTEM_PROMPT = """You are an AI-powered Transaction Monitor for AML/CFT compliance.

Your role is to analyze transactions in real-time and detect suspicious patterns that may indicate:
- Money laundering
- Terrorist financing
- Sanctions evasion
- Fraud

AVAILABLE TOOLS:
- check_velocity: Detect rapid transaction patterns for an entity
- detect_structuring: Identify amounts kept below reporting thresholds
- check_jurisdiction_risk: Flag high-risk countries (FATF grey/black list)
- detect_round_amounts: Identify suspiciously round transaction amounts
- analyze_transaction_patterns: Comprehensive pattern analysis
- create_alert: Generate an alert for investigation queue
- get_alert_queue: View current monitoring alerts

DETECTION PRIORITY:
1. CRITICAL: Sanctioned country involvement (KP, IR)
2. HIGH: Structuring patterns, high-risk jurisdictions
3. MEDIUM: Velocity anomalies, round amounts
4. LOW: Minor pattern deviations

OUTPUT FORMAT:
For each transaction, provide:
- Pattern Analysis Summary
- Alerts Generated (if any)
- Risk Level: critical/high/medium/low
- Recommended Action: escalate_immediately/queue_investigation/monitor/clear

Be thorough but avoid false positives. Consider business context when available.
"""


def get_monitor_llm():
    """Get the LLM for the Monitor agent."""
    return get_llm(temperature=0.2)  # Lower temperature for consistent monitoring


def monitor_transaction(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """Monitor a single transaction for suspicious patterns.

    This is the main entry point for real-time monitoring.

    Args:
        transaction: Transaction data including:
            - uetr: Transaction identifier
            - amount: Transaction amount (dict with value/currency)
            - debtor: Debtor info (dict with name, country)
            - creditor: Creditor info (dict with name, country)

    Returns:
        Monitoring result with alerts and risk assessment
    """
    uetr = transaction.get("uetr", "")
    amount_data = transaction.get("amount", {})
    amount = float(amount_data.get("value", 0))
    currency = amount_data.get("currency", "EUR")

    debtor = transaction.get("debtor", {})
    creditor = transaction.get("creditor", {})

    # Run comprehensive pattern analysis
    # Use direct function call instead of tool invocation for reliability
    analysis = _analyze_transaction_patterns(
        transaction_uetr=uetr,
        amount=amount,
        currency=currency,
        debtor_country=debtor.get("country"),
        creditor_country=creditor.get("country"),
        debtor_name=debtor.get("name", ""),
        creditor_name=creditor.get("name", ""),
    )

    # Create alerts for any detected patterns
    alerts_created = []
    for alert_data in analysis.get("alerts", []):
        alert_result = _create_alert(
            transaction_uetr=uetr,
            alert_type=alert_data["type"],
            severity=alert_data["severity"],
            details=alert_data["details"],
        )
        alerts_created.append(alert_result["alert"])

    # Determine recommended action
    risk = analysis.get("overall_risk", "low")
    if risk == "critical":
        action = "escalate_immediately"
    elif risk == "high":
        action = "queue_investigation"
    elif risk == "medium":
        action = "monitor"
    else:
        action = "clear"

    return {
        "uetr": uetr,
        "analysis": analysis,
        "alerts_created": len(alerts_created),
        "alerts": alerts_created,
        "overall_risk": risk,
        "recommended_action": action,
        "timestamp": datetime.now().isoformat(),
    }


def monitor_batch(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Monitor a batch of transactions (e.g., from camt.053 statement).

    Args:
        transactions: List of transactions to monitor

    Returns:
        Batch monitoring summary with aggregated results
    """
    results = []
    risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total_alerts = 0

    for tx in transactions:
        result = monitor_transaction(tx)
        results.append(result)
        risk_counts[result["overall_risk"]] += 1
        total_alerts += result["alerts_created"]

    return {
        "batch_size": len(transactions),
        "results": results,
        "risk_summary": risk_counts,
        "total_alerts": total_alerts,
        "critical_count": risk_counts["critical"],
        "high_risk_count": risk_counts["high"],
        "requires_immediate_attention": risk_counts["critical"] > 0,
        "timestamp": datetime.now().isoformat(),
    }


def monitor_agent(state: AgentState) -> Dict[str, Any]:
    """LangGraph-compatible monitor agent node.

    Can be integrated into the investigation workflow to add
    real-time monitoring capabilities.

    Args:
        state: Current investigation state

    Returns:
        Updated state with monitoring results
    """
    llm = get_monitor_llm()
    tools = [
        check_velocity,
        detect_structuring,
        check_jurisdiction_risk,
        detect_round_amounts,
        analyze_transaction_patterns,
        create_alert,
        get_alert_queue,
    ]

    # Extract transaction from state
    iso_message = state.get("iso_message", {})
    uetr = state.get("uetr", "")

    # Run automatic pattern detection
    amount = iso_message.get("amount", {})
    debtor = iso_message.get("debtor", {})
    creditor = iso_message.get("creditor", {})

    # Execute pattern analysis
    analysis = analyze_transaction_patterns.invoke(
        {
            "transaction_uetr": uetr,
            "amount": float(amount.get("value", 0)),
            "currency": amount.get("currency", "EUR"),
            "debtor_country": debtor.get("country"),
            "creditor_country": creditor.get("country"),
            "debtor_name": debtor.get("name", ""),
            "creditor_name": creditor.get("name", ""),
        }
    )

    # Build context for LLM
    monitoring_prompt = f"""
TRANSACTION MONITORING ANALYSIS:

Transaction: {uetr}
Amount: {amount.get("value", 0)} {amount.get("currency", "EUR")}
Debtor: {debtor.get("name", "Unknown")} ({debtor.get("country", "N/A")})
Creditor: {creditor.get("name", "Unknown")} ({creditor.get("country", "N/A")})

AUTOMATED PATTERN DETECTION RESULTS:
{json.dumps(analysis, indent=2, default=str)}

Based on this analysis, provide:
1. Summary of detected patterns
2. Any additional checks needed
3. Recommended monitoring actions
4. Risk justification
"""

    messages = [
        SystemMessage(content=MONITOR_SYSTEM_PROMPT),
        HumanMessage(content=monitoring_prompt),
    ]

    # Get LLM analysis
    response = invoke_with_fallback(llm, messages, tools)

    # Process response
    raw_content = response.content if hasattr(response, "content") else str(response)
    if isinstance(raw_content, list):
        content = "\n".join(str(item) for item in raw_content)
    else:
        content = str(raw_content)

    # Create monitoring record
    monitoring_record = {
        "speaker": "monitor",  # Note: Not part of debate, separate channel
        "content": content,
        "patterns_detected": analysis.get("alerts", []),
        "risk_level": analysis.get("overall_risk", "low"),
        "timestamp": datetime.now().isoformat(),
    }

    # Determine if investigation should be triggered
    should_investigate = analysis.get("requires_investigation", False)

    return {
        "monitoring_result": monitoring_record,
        "monitoring_alerts": analysis.get("alerts", []),
        "monitoring_risk": analysis.get("overall_risk", "low"),
        "needs_more_evidence": should_investigate,
    }


# API-friendly functions
def get_monitoring_thresholds() -> Dict[str, Any]:
    """Get current monitoring thresholds."""
    from backend.tools.tools_alerts import DEFAULT_THRESHOLDS

    return DEFAULT_THRESHOLDS


def get_high_risk_jurisdictions() -> Dict[str, str]:
    """Get list of high-risk jurisdictions."""
    from backend.tools.tools_alerts import HIGH_RISK_JURISDICTIONS

    return HIGH_RISK_JURISDICTIONS

"""Partner/Affiliate Fraud Detection Agent.

This agent specializes in:
- Network analysis for partner relationships
- Commission fraud pattern detection
- Affiliate relationship mapping
- Partner risk scoring
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

from backend.llm_provider import get_llm, invoke_with_fallback


PARTNER_FRAUD_SYSTEM_PROMPT = """You are a specialized Partner/Affiliate Fraud Detection Agent.

Your role is to analyze partner networks for:
1. Commission fraud - fake referrals, self-referrals, inflated commissions
2. Collusion patterns - coordinated fraudulent activity between partners
3. Account manipulation - shell accounts, layered arrangements
4. Volume anomalies - sudden spikes or unusual patterns

DETECTION PATTERNS:
- Circular referral chains
- Concentrated client acquisition from single sources
- Abnormal conversion rates (too high or too low)
- Geographic clustering anomalies
- Time-based patterns (batch referrals)

OUTPUT FORMAT:
- Partner Risk Score (0-100)
- Detected Patterns
- Network Connections
- Recommended Actions
"""


# Mock partner network data
_partner_network: Dict[str, Dict[str, Any]] = {
    "PARTNER-001": {
        "name": "Global Payments Ltd",
        "type": "payment_processor",
        "risk_score": 25,
        "status": "active",
        "total_volume": 5000000,
        "total_commission": 150000,
        "referrals": 250,
        "conversion_rate": 0.68,
        "joined_date": "2024-01-15",
        "connections": ["PARTNER-002", "PARTNER-005"],
        "flags": [],
    },
    "PARTNER-002": {
        "name": "FastExchange Corp",
        "type": "exchange",
        "risk_score": 65,
        "status": "under_review",
        "total_volume": 2500000,
        "total_commission": 125000,
        "referrals": 180,
        "conversion_rate": 0.92,  # Suspiciously high
        "joined_date": "2024-03-20",
        "connections": ["PARTNER-001", "PARTNER-003"],
        "flags": ["high_conversion_rate", "volume_spike"],
    },
    "PARTNER-003": {
        "name": "CryptoFlow Partners",
        "type": "crypto_broker",
        "risk_score": 85,
        "status": "suspended",
        "total_volume": 1800000,
        "total_commission": 180000,  # Abnormal commission ratio
        "referrals": 95,
        "conversion_rate": 0.95,
        "joined_date": "2024-06-01",
        "connections": ["PARTNER-002", "PARTNER-004"],
        "flags": ["circular_referral", "abnormal_commission", "shell_accounts"],
    },
    "PARTNER-004": {
        "name": "SecurePay Africa",
        "type": "regional_partner",
        "risk_score": 40,
        "status": "active",
        "total_volume": 800000,
        "total_commission": 24000,
        "referrals": 65,
        "conversion_rate": 0.55,
        "joined_date": "2024-02-10",
        "connections": ["PARTNER-003"],
        "flags": ["geographic_concentration"],
    },
    "PARTNER-005": {
        "name": "EuroFinance GmbH",
        "type": "financial_institution",
        "risk_score": 15,
        "status": "active",
        "total_volume": 8000000,
        "total_commission": 200000,
        "referrals": 420,
        "conversion_rate": 0.62,
        "joined_date": "2023-11-01",
        "connections": ["PARTNER-001"],
        "flags": [],
    },
}


@tool
def analyze_partner_network(partner_id: str = None) -> Dict[str, Any]:
    """Analyze the partner network for fraud patterns.
    
    Args:
        partner_id: Specific partner to analyze, or None for all
    
    Returns:
        Network analysis results
    """
    if partner_id and partner_id in _partner_network:
        partners = {partner_id: _partner_network[partner_id]}
    else:
        partners = _partner_network
    
    # Calculate network statistics
    high_risk = [p for p, d in partners.items() if d["risk_score"] >= 70]
    suspicious_patterns = []
    
    for pid, data in partners.items():
        if data["conversion_rate"] > 0.85:
            suspicious_patterns.append({
                "partner": pid,
                "pattern": "abnormally_high_conversion",
                "value": data["conversion_rate"],
            })
        if data["total_commission"] / max(data["total_volume"], 1) > 0.08:
            suspicious_patterns.append({
                "partner": pid,
                "pattern": "abnormal_commission_ratio",
                "value": data["total_commission"] / data["total_volume"],
            })
    
    # Detect circular patterns
    circular = detect_circular_referrals.invoke({})
    
    return {
        "total_partners": len(partners),
        "high_risk_count": len(high_risk),
        "high_risk_partners": high_risk,
        "suspicious_patterns": suspicious_patterns,
        "circular_referrals": circular.get("circular_chains", []),
        "network_health": "healthy" if len(high_risk) == 0 else "at_risk",
    }


@tool
def detect_circular_referrals() -> Dict[str, Any]:
    """Detect circular referral patterns in the partner network.
    
    Returns:
        Detected circular referral chains
    """
    # Simple cycle detection in mock data
    circular_chains = []
    
    # Known circular pattern from mock data
    if "PARTNER-002" in _partner_network and "PARTNER-003" in _partner_network:
        if "PARTNER-003" in _partner_network["PARTNER-002"]["connections"]:
            circular_chains.append({
                "chain": ["PARTNER-002", "PARTNER-003", "PARTNER-004"],
                "risk_level": "high",
                "total_volume": 4300000,
            })
    
    return {
        "circular_chains": circular_chains,
        "total_detected": len(circular_chains),
        "risk_exposure": sum(c["total_volume"] for c in circular_chains),
    }


@tool
def get_partner_risk_score(partner_id: str) -> Dict[str, Any]:
    """Get detailed risk score breakdown for a partner.
    
    Args:
        partner_id: Partner identifier
    
    Returns:
        Risk score with contributing factors
    """
    if partner_id not in _partner_network:
        return {"error": f"Partner {partner_id} not found"}
    
    partner = _partner_network[partner_id]
    
    # Calculate component scores
    volume_score = min(30, (partner["total_volume"] / 1000000) * 5)
    conversion_score = 0 if partner["conversion_rate"] < 0.8 else (partner["conversion_rate"] - 0.5) * 100
    commission_ratio = partner["total_commission"] / max(partner["total_volume"], 1)
    commission_score = 0 if commission_ratio < 0.05 else min(30, commission_ratio * 300)
    flag_score = len(partner["flags"]) * 15
    
    total_score = min(100, volume_score + conversion_score + commission_score + flag_score)
    
    return {
        "partner_id": partner_id,
        "name": partner["name"],
        "overall_risk_score": total_score,
        "risk_components": {
            "volume_risk": volume_score,
            "conversion_risk": conversion_score,
            "commission_risk": commission_score,
            "flag_risk": flag_score,
        },
        "flags": partner["flags"],
        "status": partner["status"],
        "connections": partner["connections"],
        "recommendation": "suspend" if total_score > 70 else "review" if total_score > 40 else "monitor",
    }


@tool
def detect_commission_fraud(partner_id: str = None) -> Dict[str, Any]:
    """Detect commission fraud patterns.
    
    Args:
        partner_id: Specific partner or None for all
    
    Returns:
        Commission fraud analysis
    """
    fraudulent_patterns = []
    
    for pid, data in _partner_network.items():
        if partner_id and pid != partner_id:
            continue
            
        issues = []
        
        # Check commission ratio
        ratio = data["total_commission"] / max(data["total_volume"], 1)
        if ratio > 0.08:
            issues.append("abnormal_commission_ratio")
        
        # Check conversion rate
        if data["conversion_rate"] > 0.85:
            issues.append("suspicious_conversion")
        
        # Check for known flags
        if "shell_accounts" in data["flags"]:
            issues.append("shell_account_referrals")
        
        if issues:
            fraudulent_patterns.append({
                "partner_id": pid,
                "name": data["name"],
                "issues": issues,
                "estimated_fraud_amount": data["total_commission"] * 0.3 if len(issues) > 1 else 0,
            })
    
    return {
        "fraudulent_patterns": fraudulent_patterns,
        "total_affected": len(fraudulent_patterns),
        "estimated_total_fraud": sum(p["estimated_fraud_amount"] for p in fraudulent_patterns),
    }


@tool
def get_affiliate_connections(partner_id: str, depth: int = 2) -> Dict[str, Any]:
    """Get affiliate connection network up to specified depth.
    
    Args:
        partner_id: Starting partner
        depth: How many levels deep to traverse
    
    Returns:
        Network connection graph
    """
    if partner_id not in _partner_network:
        return {"error": f"Partner {partner_id} not found"}
    
    visited = set()
    nodes = []
    edges = []
    
    def traverse(pid: str, current_depth: int):
        if current_depth > depth or pid in visited:
            return
        visited.add(pid)
        
        partner = _partner_network.get(pid)
        if not partner:
            return
        
        nodes.append({
            "id": pid,
            "name": partner["name"],
            "type": partner["type"],
            "risk_score": partner["risk_score"],
        })
        
        for conn in partner.get("connections", []):
            edges.append({"from": pid, "to": conn})
            traverse(conn, current_depth + 1)
    
    traverse(partner_id, 0)
    
    return {
        "root_partner": partner_id,
        "depth": depth,
        "nodes": nodes,
        "edges": edges,
        "total_connections": len(nodes) - 1,
    }


def get_partner_fraud_llm():
    """Get the LLM for the Partner Fraud agent."""
    return get_llm(temperature=0.2)


def partner_fraud_agent(partner_id: str = None) -> Dict[str, Any]:
    """Analyze partner network for fraud.
    
    Args:
        partner_id: Specific partner to analyze
    
    Returns:
        Comprehensive fraud analysis
    """
    llm = get_partner_fraud_llm()
    tools = [
        analyze_partner_network,
        detect_circular_referrals,
        get_partner_risk_score,
        detect_commission_fraud,
        get_affiliate_connections,
    ]
    
    # Run analyses
    network_analysis = analyze_partner_network.invoke({"partner_id": partner_id})
    commission_fraud = detect_commission_fraud.invoke({"partner_id": partner_id})
    
    analysis_prompt = f"""
PARTNER FRAUD ANALYSIS REQUEST:

Target Partner: {partner_id or "All Partners"}

NETWORK ANALYSIS:
{json.dumps(network_analysis, indent=2)}

COMMISSION FRAUD DETECTION:
{json.dumps(commission_fraud, indent=2)}

Please provide:
1. Executive summary of findings
2. High-risk partners requiring immediate action
3. Recommended remediation steps
4. Monitoring recommendations
"""
    
    messages = [
        SystemMessage(content=PARTNER_FRAUD_SYSTEM_PROMPT),
        HumanMessage(content=analysis_prompt),
    ]
    
    response = invoke_with_fallback(llm, messages, tools)
    
    raw_content = response.content if hasattr(response, "content") else str(response)
    if isinstance(raw_content, list):
        content = "\n".join(str(item) for item in raw_content)
    else:
        content = str(raw_content)
    
    return {
        "partner_id": partner_id,
        "network_analysis": network_analysis,
        "commission_fraud": commission_fraud,
        "ai_assessment": content,
        "timestamp": datetime.now().isoformat(),
    }


# API-friendly functions
def get_all_partners() -> Dict[str, Dict[str, Any]]:
    """Get all partner data."""
    return _partner_network


def get_partner(partner_id: str) -> Optional[Dict[str, Any]]:
    """Get specific partner data."""
    return _partner_network.get(partner_id)

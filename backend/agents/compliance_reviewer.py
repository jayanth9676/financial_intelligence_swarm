"""Compliance Review Agent for regulatory document analysis and deadline tracking.

This agent handles:
- Regulatory compliance status checks
- Deadline tracking for filings and submissions
- Automated compliance documentation generation
- Policy adherence verification
"""

import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.llm_provider import get_llm, invoke_with_fallback


COMPLIANCE_SYSTEM_PROMPT = """You are an AI Compliance Manager for financial institutions.

Your role is to:
1. Track regulatory deadlines and compliance obligations
2. Review transactions for regulatory adherence
3. Generate compliance documentation
4. Identify compliance gaps and recommend remediation

REGULATORY FRAMEWORKS YOU MONITOR:
- EU AML Directive (6th AMLD)
- FATF Recommendations
- PSD2/PSD3
- MiCA (for crypto assets)
- GDPR (data protection aspects)
- EU AI Act (for AI systems)

OUTPUT FORMAT:
- Compliance Status: compliant/partially_compliant/non_compliant
- Risk Areas identified
- Required Actions with deadlines
- Documentation gaps
"""


# In-memory compliance calendar
_compliance_calendar: List[Dict[str, Any]] = [
    {
        "id": "REG-001",
        "title": "Quarterly SAR Filing",
        "regulation": "EU 6th AMLD",
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "status": "pending",
        "priority": "high",
        "description": "Submit quarterly Suspicious Activity Reports to FIU",
    },
    {
        "id": "REG-002",
        "title": "Annual AML Review",
        "regulation": "FATF Recommendations",
        "due_date": (datetime.now() + timedelta(days=90)).isoformat(),
        "status": "pending",
        "priority": "medium",
        "description": "Complete annual review of AML procedures and controls",
    },
    {
        "id": "REG-003",
        "title": "EU AI Act Compliance Audit",
        "regulation": "EU AI Act",
        "due_date": (datetime.now() + timedelta(days=60)).isoformat(),
        "status": "pending",
        "priority": "high",
        "description": "Audit high-risk AI systems for Article 13 and Annex IV compliance",
    },
    {
        "id": "REG-004",
        "title": "PSD2 Strong Authentication Review",
        "regulation": "PSD2",
        "due_date": (datetime.now() + timedelta(days=45)).isoformat(),
        "status": "pending",
        "priority": "medium",
        "description": "Review SCA implementation for payment transactions",
    },
]

# Compliance status tracking
_compliance_status: Dict[str, Dict[str, Any]] = {
    "aml": {
        "framework": "EU 6th AMLD",
        "status": "compliant",
        "last_review": datetime.now().isoformat(),
        "controls": ["Transaction Monitoring", "SAR Filing", "KYC/CDD", "Sanctions Screening"],
        "gaps": [],
    },
    "ai_act": {
        "framework": "EU AI Act",
        "status": "partially_compliant",
        "last_review": datetime.now().isoformat(),
        "controls": ["Article 13 Transparency", "Human Oversight", "Risk Assessment"],
        "gaps": ["Full Annex IV technical documentation pending"],
    },
    "psd2": {
        "framework": "PSD2/PSD3",
        "status": "compliant",
        "last_review": datetime.now().isoformat(),
        "controls": ["SCA", "TPP Access Controls", "Fraud Monitoring"],
        "gaps": [],
    },
    "gdpr": {
        "framework": "GDPR",
        "status": "compliant",
        "last_review": datetime.now().isoformat(),
        "controls": ["Data Minimization", "Consent Management", "Data Subject Rights"],
        "gaps": [],
    },
}


class ComplianceCheckInput(BaseModel):
    """Input for compliance check."""
    transaction_uetr: str = Field(description="Transaction UETR to check")
    check_type: str = Field(default="full", description="Type: full|aml|sanctions|pep")


class DeadlineInput(BaseModel):
    """Input for deadline operations."""
    days_ahead: int = Field(default=30, description="Days to look ahead")


@tool
def check_transaction_compliance(transaction_uetr: str, check_type: str = "full") -> Dict[str, Any]:
    """Check if a transaction meets regulatory compliance requirements.
    
    Args:
        transaction_uetr: Transaction identifier
        check_type: Type of check (full, aml, sanctions, pep)
    
    Returns:
        Compliance check results
    """
    # In production, this would query actual compliance systems
    checks_performed = []
    issues_found = []
    
    if check_type in ["full", "aml"]:
        checks_performed.append("AML screening")
        # Mock: Check for suspicious patterns
        
    if check_type in ["full", "sanctions"]:
        checks_performed.append("Sanctions screening")
        # Mock: Check against sanctions lists
        
    if check_type in ["full", "pep"]:
        checks_performed.append("PEP screening")
        # Mock: Check politically exposed persons database
    
    return {
        "transaction_uetr": transaction_uetr,
        "check_type": check_type,
        "checks_performed": checks_performed,
        "issues_found": issues_found,
        "compliance_status": "compliant" if not issues_found else "requires_review",
        "timestamp": datetime.now().isoformat(),
    }


@tool
def get_compliance_deadlines(days_ahead: int = 30) -> Dict[str, Any]:
    """Get upcoming regulatory compliance deadlines.
    
    Args:
        days_ahead: Number of days to look ahead
    
    Returns:
        List of upcoming deadlines
    """
    cutoff = datetime.now() + timedelta(days=days_ahead)
    upcoming = [
        d for d in _compliance_calendar
        if datetime.fromisoformat(d["due_date"]) <= cutoff
    ]
    
    # Sort by due date
    upcoming.sort(key=lambda x: x["due_date"])
    
    return {
        "deadlines": upcoming,
        "total": len(upcoming),
        "high_priority": len([d for d in upcoming if d["priority"] == "high"]),
        "overdue": len([d for d in upcoming if datetime.fromisoformat(d["due_date"]) < datetime.now()]),
    }


@tool
def get_compliance_status(framework: str = "all") -> Dict[str, Any]:
    """Get current compliance status for regulatory frameworks.
    
    Args:
        framework: Specific framework or "all"
    
    Returns:
        Compliance status details
    """
    if framework == "all":
        statuses = _compliance_status
    else:
        statuses = {framework: _compliance_status.get(framework, {"status": "unknown"})}
    
    # Calculate overall status
    all_statuses = [s["status"] for s in _compliance_status.values()]
    if "non_compliant" in all_statuses:
        overall = "non_compliant"
    elif "partially_compliant" in all_statuses:
        overall = "partially_compliant"
    else:
        overall = "compliant"
    
    return {
        "frameworks": statuses,
        "overall_status": overall,
        "last_updated": datetime.now().isoformat(),
    }


@tool
def generate_compliance_report(report_type: str = "summary") -> Dict[str, Any]:
    """Generate a compliance report.
    
    Args:
        report_type: Type of report (summary, detailed, regulatory)
    
    Returns:
        Generated compliance report
    """
    deadlines = get_compliance_deadlines.invoke({"days_ahead": 90})
    status = get_compliance_status.invoke({"framework": "all"})
    
    report = {
        "report_type": report_type,
        "generated_at": datetime.now().isoformat(),
        "executive_summary": {
            "overall_compliance": status["overall_status"],
            "upcoming_deadlines": deadlines["total"],
            "high_priority_items": deadlines["high_priority"],
        },
        "framework_status": status["frameworks"],
        "upcoming_deadlines": deadlines["deadlines"][:5],  # Top 5
        "recommendations": [
            "Complete EU AI Act Annex IV documentation",
            "Schedule quarterly SAR filing review",
            "Update sanctions screening lists",
        ],
    }
    
    return report


@tool
def add_compliance_deadline(
    title: str,
    regulation: str,
    due_date: str,
    priority: str = "medium",
    description: str = ""
) -> Dict[str, Any]:
    """Add a new compliance deadline to the calendar.
    
    Args:
        title: Deadline title
        regulation: Regulatory framework
        due_date: Due date (ISO format)
        priority: Priority level (low, medium, high)
        description: Description of the deadline
    
    Returns:
        Created deadline
    """
    deadline_id = f"REG-{len(_compliance_calendar) + 1:03d}"
    
    deadline = {
        "id": deadline_id,
        "title": title,
        "regulation": regulation,
        "due_date": due_date,
        "status": "pending",
        "priority": priority,
        "description": description,
    }
    
    _compliance_calendar.append(deadline)
    
    return {
        "success": True,
        "deadline": deadline,
    }


def get_compliance_llm():
    """Get the LLM for the Compliance agent."""
    return get_llm(temperature=0.2)


def compliance_review_agent(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """Review a transaction for compliance requirements.
    
    Args:
        transaction: Transaction data
    
    Returns:
        Compliance review results
    """
    llm = get_compliance_llm()
    tools = [
        check_transaction_compliance,
        get_compliance_deadlines,
        get_compliance_status,
        generate_compliance_report,
    ]
    
    uetr = transaction.get("uetr", "")
    amount = transaction.get("amount", {})
    
    # Run compliance checks
    compliance_result = check_transaction_compliance.invoke({
        "transaction_uetr": uetr,
        "check_type": "full",
    })
    
    # Build prompt for AI analysis
    review_prompt = f"""
COMPLIANCE REVIEW REQUEST:

Transaction: {uetr}
Amount: {amount.get("value", 0)} {amount.get("currency", "EUR")}

AUTOMATED COMPLIANCE CHECK RESULTS:
{json.dumps(compliance_result, indent=2)}

Please provide:
1. Compliance assessment
2. Any regulatory concerns
3. Required documentation
4. Recommended actions
"""
    
    messages = [
        SystemMessage(content=COMPLIANCE_SYSTEM_PROMPT),
        HumanMessage(content=review_prompt),
    ]
    
    response = invoke_with_fallback(llm, messages, tools)
    
    raw_content = response.content if hasattr(response, "content") else str(response)
    if isinstance(raw_content, list):
        content = "\n".join(str(item) for item in raw_content)
    else:
        content = str(raw_content)
    
    return {
        "uetr": uetr,
        "compliance_check": compliance_result,
        "ai_assessment": content,
        "timestamp": datetime.now().isoformat(),
    }


# API-friendly functions
def get_calendar() -> List[Dict[str, Any]]:
    """Get the full compliance calendar."""
    return _compliance_calendar


def get_all_frameworks() -> Dict[str, Dict[str, Any]]:
    """Get all compliance framework statuses."""
    return _compliance_status

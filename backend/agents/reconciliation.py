"""Financial Reconciliation Agent for camt.053 statement matching.

Handles:
- Statement parsing and matching
- Discrepancy detection
- Resolution workflow
- Exception handling
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

from backend.llm_provider import get_llm, invoke_with_fallback


RECONCILIATION_SYSTEM_PROMPT = """You are a Financial Reconciliation Assistant.

Your role is to:
1. Match transactions between internal records and bank statements (camt.053)
2. Identify discrepancies and their root causes
3. Suggest resolution actions
4. Generate reconciliation reports

MATCHING CRITERIA:
- UETR/Reference matching (exact)
- Amount matching (within tolerance)
- Date matching (within settlement window)
- Counterparty matching (fuzzy)

DISCREPANCY TYPES:
- Missing in statement (pending settlement)
- Missing in records (unbooked transaction)
- Amount mismatch
- Date mismatch
- Duplicate entry

OUTPUT FORMAT:
- Match Status: matched/unmatched/partial
- Confidence Score
- Discrepancies identified
- Suggested resolution
"""


# Mock reconciliation data
_internal_records: List[Dict[str, Any]] = [
    {
        "record_id": "INT-001",
        "uetr": "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e",
        "amount": 15000.00,
        "currency": "EUR",
        "date": "2026-02-05",
        "debtor": "TechCorp Munich",
        "creditor": "Shell Corp Cyprus",
        "status": "pending_match",
    },
    {
        "record_id": "INT-002",
        "uetr": "abc12345-def6-7890-ghij-klmnopqrstuv",
        "amount": 5250.00,
        "currency": "EUR",
        "date": "2026-02-05",
        "debtor": "Local Shop",
        "creditor": "Supplier Inc",
        "status": "pending_match",
    },
    {
        "record_id": "INT-003",
        "uetr": "xyz98765-4321-abcd-efgh-ijklmnopqrst",
        "amount": 32000.00,
        "currency": "EUR",
        "date": "2026-02-06",
        "debtor": "Import Export Ltd",
        "creditor": "Foreign Partner",
        "status": "pending_match",
    },
]

_bank_statements: List[Dict[str, Any]] = [
    {
        "entry_id": "STMT-001",
        "reference": "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e",
        "amount": 15000.00,
        "currency": "EUR",
        "booking_date": "2026-02-05",
        "value_date": "2026-02-05",
        "creditor_name": "Shell Corp Cyprus",
        "status": "booked",
    },
    {
        "entry_id": "STMT-002",
        "reference": "abc12345-def6-7890-ghij-klmnopqrstuv",
        "amount": 5200.00,  # Different amount - discrepancy
        "currency": "EUR",
        "booking_date": "2026-02-05",
        "value_date": "2026-02-05",
        "creditor_name": "Supplier Inc",
        "status": "booked",
    },
    # Missing STMT-003 (INT-003 not yet in statement)
    {
        "entry_id": "STMT-004",
        "reference": "unknown-ref-12345",
        "amount": 8500.00,
        "currency": "EUR",
        "booking_date": "2026-02-06",
        "value_date": "2026-02-06",
        "creditor_name": "Unknown Beneficiary",
        "status": "booked",
    },
]

_reconciliation_results: List[Dict[str, Any]] = []


@tool
def match_transactions(
    tolerance_amount: float = 0.01,
    tolerance_days: int = 3
) -> Dict[str, Any]:
    """Match internal records against bank statement entries.
    
    Args:
        tolerance_amount: Percentage tolerance for amount matching
        tolerance_days: Days tolerance for date matching
    
    Returns:
        Matching results with matched, unmatched, and discrepancies
    """
    matched = []
    unmatched_internal = []
    unmatched_statement = []
    discrepancies = []
    
    matched_statement_ids = set()
    
    for record in _internal_records:
        best_match = None
        best_score = 0
        
        for entry in _bank_statements:
            if entry["entry_id"] in matched_statement_ids:
                continue
            
            score = 0
            issues = []
            
            # Reference matching
            if record["uetr"] == entry["reference"]:
                score += 50
            
            # Amount matching
            amount_diff = abs(record["amount"] - entry["amount"])
            if amount_diff == 0:
                score += 30
            elif amount_diff / record["amount"] <= tolerance_amount:
                score += 20
                issues.append(f"Amount difference: {amount_diff}")
            else:
                issues.append(f"Amount mismatch: {record['amount']} vs {entry['amount']}")
            
            # Currency matching
            if record["currency"] == entry["currency"]:
                score += 10
            
            # Date matching
            try:
                rec_date = datetime.fromisoformat(record["date"])
                stmt_date = datetime.fromisoformat(entry["booking_date"])
                if abs((rec_date - stmt_date).days) <= tolerance_days:
                    score += 10
            except:
                pass
            
            if score > best_score:
                best_score = score
                best_match = {"entry": entry, "score": score, "issues": issues}
        
        if best_match and best_score >= 50:
            matched_statement_ids.add(best_match["entry"]["entry_id"])
            match_result = {
                "record": record,
                "statement_entry": best_match["entry"],
                "confidence": best_score,
                "issues": best_match["issues"],
            }
            matched.append(match_result)
            
            if best_match["issues"]:
                discrepancies.append({
                    "type": "partial_match",
                    "record_id": record["record_id"],
                    "entry_id": best_match["entry"]["entry_id"],
                    "issues": best_match["issues"],
                })
        else:
            unmatched_internal.append(record)
    
    # Find unmatched statement entries
    for entry in _bank_statements:
        if entry["entry_id"] not in matched_statement_ids:
            unmatched_statement.append(entry)
            discrepancies.append({
                "type": "missing_internal_record",
                "entry_id": entry["entry_id"],
                "amount": entry["amount"],
                "reference": entry["reference"],
            })
    
    return {
        "matched": matched,
        "matched_count": len(matched),
        "unmatched_internal": unmatched_internal,
        "unmatched_internal_count": len(unmatched_internal),
        "unmatched_statement": unmatched_statement,
        "unmatched_statement_count": len(unmatched_statement),
        "discrepancies": discrepancies,
        "discrepancy_count": len(discrepancies),
        "match_rate": len(matched) / len(_internal_records) * 100 if _internal_records else 0,
    }


@tool
def get_reconciliation_status() -> Dict[str, Any]:
    """Get overall reconciliation status.
    
    Returns:
        Current reconciliation status and statistics
    """
    result = match_transactions.invoke({})
    
    total_internal_amount = sum(r["amount"] for r in _internal_records)
    total_statement_amount = sum(e["amount"] for e in _bank_statements)
    variance = total_statement_amount - total_internal_amount
    
    return {
        "internal_records": len(_internal_records),
        "statement_entries": len(_bank_statements),
        "matched": result["matched_count"],
        "unmatched": result["unmatched_internal_count"] + result["unmatched_statement_count"],
        "discrepancies": result["discrepancy_count"],
        "match_rate": result["match_rate"],
        "total_internal_value": total_internal_amount,
        "total_statement_value": total_statement_amount,
        "variance": variance,
        "variance_percentage": (variance / total_internal_amount * 100) if total_internal_amount else 0,
        "last_reconciled": datetime.now().isoformat(),
    }


@tool
def identify_discrepancy(record_id: str) -> Dict[str, Any]:
    """Identify the root cause of a discrepancy.
    
    Args:
        record_id: Internal record ID
    
    Returns:
        Discrepancy analysis
    """
    record = next((r for r in _internal_records if r["record_id"] == record_id), None)
    if not record:
        return {"error": f"Record {record_id} not found"}
    
    # Find potential matches
    potential_matches = []
    for entry in _bank_statements:
        if record["uetr"] == entry["reference"]:
            potential_matches.append(entry)
    
    if not potential_matches:
        return {
            "record_id": record_id,
            "discrepancy_type": "missing_statement_entry",
            "root_cause": "Transaction not yet booked in bank statement",
            "suggested_action": "Wait for settlement or check with bank",
            "record": record,
        }
    
    # Check for amount mismatches
    for match in potential_matches:
        if record["amount"] != match["amount"]:
            return {
                "record_id": record_id,
                "discrepancy_type": "amount_mismatch",
                "root_cause": "Amount differs between internal record and bank statement",
                "internal_amount": record["amount"],
                "statement_amount": match["amount"],
                "difference": record["amount"] - match["amount"],
                "suggested_action": "Investigate fee deduction or booking error",
            }
    
    return {
        "record_id": record_id,
        "discrepancy_type": "none",
        "status": "matched",
    }


@tool
def resolve_discrepancy(
    record_id: str,
    resolution_type: str,
    notes: str = ""
) -> Dict[str, Any]:
    """Resolve a reconciliation discrepancy.
    
    Args:
        record_id: Internal record ID
        resolution_type: Type of resolution (adjust, write_off, investigate)
        notes: Resolution notes
    
    Returns:
        Resolution result
    """
    record = next((r for r in _internal_records if r["record_id"] == record_id), None)
    if not record:
        return {"error": f"Record {record_id} not found"}
    
    resolution = {
        "record_id": record_id,
        "resolution_type": resolution_type,
        "notes": notes,
        "resolved_at": datetime.now().isoformat(),
        "resolved_by": "system",
    }
    
    # Update record status
    record["status"] = "reconciled"
    record["resolution"] = resolution
    
    _reconciliation_results.append(resolution)
    
    return {
        "success": True,
        "resolution": resolution,
    }


@tool
def generate_reconciliation_report(report_type: str = "summary") -> Dict[str, Any]:
    """Generate a reconciliation report.
    
    Args:
        report_type: Type of report (summary, detailed, exceptions)
    
    Returns:
        Generated report
    """
    status = get_reconciliation_status.invoke({})
    matching = match_transactions.invoke({})
    
    report = {
        "report_type": report_type,
        "generated_at": datetime.now().isoformat(),
        "period": f"{datetime.now().strftime('%Y-%m')}", 
        "summary": {
            "total_records": status["internal_records"],
            "total_entries": status["statement_entries"],
            "matched": status["matched"],
            "match_rate": f"{status['match_rate']:.1f}%",
            "variance": status["variance"],
        },
        "discrepancies": matching["discrepancies"],
        "unresolved_count": len([d for d in matching["discrepancies"] if d.get("type") != "resolved"]),
        "recommendations": [
            "Review amount mismatches for potential fee adjustments",
            "Investigate unknown references in statement",
            "Check pending settlements for unmatched records",
        ],
    }
    
    return report


def get_reconciliation_llm():
    """Get the LLM for the Reconciliation agent."""
    return get_llm(temperature=0.2)


def reconciliation_agent(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run AI-assisted reconciliation analysis.
    
    Args:
        params: Optional parameters for the analysis
    
    Returns:
        Comprehensive reconciliation analysis
    """
    llm = get_reconciliation_llm()
    tools = [
        match_transactions,
        get_reconciliation_status,
        identify_discrepancy,
        generate_reconciliation_report,
    ]
    
    # Run matching
    status = get_reconciliation_status.invoke({})
    matching = match_transactions.invoke({})
    
    analysis_prompt = f"""
RECONCILIATION ANALYSIS REQUEST:

CURRENT STATUS:
{json.dumps(status, indent=2)}

MATCHING RESULTS:
- Matched: {matching['matched_count']}
- Unmatched Internal: {matching['unmatched_internal_count']}
- Unmatched Statement: {matching['unmatched_statement_count']}
- Discrepancies: {matching['discrepancy_count']}

DISCREPANCY DETAILS:
{json.dumps(matching['discrepancies'], indent=2)}

Please provide:
1. Executive summary of reconciliation status
2. Root cause analysis of discrepancies
3. Priority actions required
4. Recommendations for process improvement
"""
    
    messages = [
        SystemMessage(content=RECONCILIATION_SYSTEM_PROMPT),
        HumanMessage(content=analysis_prompt),
    ]
    
    response = invoke_with_fallback(llm, messages, tools)
    
    raw_content = response.content if hasattr(response, "content") else str(response)
    if isinstance(raw_content, list):
        content = "\n".join(str(item) for item in raw_content)
    else:
        content = str(raw_content)
    
    return {
        "status": status,
        "matching": matching,
        "ai_analysis": content,
        "timestamp": datetime.now().isoformat(),
    }


# API-friendly functions
def get_internal_records() -> List[Dict[str, Any]]:
    """Get all internal records."""
    return _internal_records


def get_statement_entries() -> List[Dict[str, Any]]:
    """Get all bank statement entries."""
    return _bank_statements


def add_statement_entry(entry: Dict[str, Any]):
    """Add a bank statement entry."""
    _bank_statements.append(entry)

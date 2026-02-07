"""Payment Approval Workflow Router.

Implements multi-level authorization workflow for payments:
- Risk-based routing
- Multi-level approval chains
- Integration with investigation results
- Approval analytics
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


router = APIRouter(prefix="/approval", tags=["Approval Workflow"])


class ApprovalLevel(str, Enum):
    """Approval authorization levels."""
    AUTO = "auto"
    LEVEL_1 = "level_1"  # Analyst
    LEVEL_2 = "level_2"  # Senior Analyst
    LEVEL_3 = "level_3"  # Manager
    LEVEL_4 = "level_4"  # Director/Compliance Officer


class ApprovalStatus(str, Enum):
    """Approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"


class ApprovalRequest(BaseModel):
    """Approval request model."""
    uetr: str
    action: str  # approve, reject, escalate
    notes: Optional[str] = None
    approver_id: str = "system"


class EscalateRequest(BaseModel):
    """Escalation request model."""
    uetr: str
    reason: str
    target_level: Optional[ApprovalLevel] = None


from backend.store import approval_queue as _approval_queue
# Approval thresholds
APPROVAL_THRESHOLDS = {
    "auto_approve_max_amount": 1000,
    "level_1_max_amount": 10000,
    "level_2_max_amount": 50000,
    "level_3_max_amount": 200000,
    # Above level_3 requires level_4 (director)
}

# Risk-based approval routing
RISK_APPROVAL_LEVELS = {
    "low": ApprovalLevel.AUTO,
    "medium": ApprovalLevel.LEVEL_1,
    "high": ApprovalLevel.LEVEL_2,
    "critical": ApprovalLevel.LEVEL_3,
}


def determine_approval_level(amount: float, risk_level: str) -> ApprovalLevel:
    """Determine required approval level based on amount and risk."""
    # Start with risk-based level
    risk_based = RISK_APPROVAL_LEVELS.get(risk_level, ApprovalLevel.LEVEL_2)
    
    # Check amount thresholds
    if amount <= APPROVAL_THRESHOLDS["auto_approve_max_amount"] and risk_level == "low":
        amount_based = ApprovalLevel.AUTO
    elif amount <= APPROVAL_THRESHOLDS["level_1_max_amount"]:
        amount_based = ApprovalLevel.LEVEL_1
    elif amount <= APPROVAL_THRESHOLDS["level_2_max_amount"]:
        amount_based = ApprovalLevel.LEVEL_2
    elif amount <= APPROVAL_THRESHOLDS["level_3_max_amount"]:
        amount_based = ApprovalLevel.LEVEL_3
    else:
        amount_based = ApprovalLevel.LEVEL_4
    
    # Take the higher of the two levels
    level_order = [ApprovalLevel.AUTO, ApprovalLevel.LEVEL_1, ApprovalLevel.LEVEL_2, 
                   ApprovalLevel.LEVEL_3, ApprovalLevel.LEVEL_4]
    risk_idx = level_order.index(risk_based)
    amount_idx = level_order.index(amount_based)
    
    return level_order[max(risk_idx, amount_idx)]


def add_to_approval_queue(
    uetr: str,
    amount: float,
    currency: str,
    risk_level: str,
    debtor: str,
    creditor: str,
    investigation_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Add a transaction to the approval queue."""
    required_level = determine_approval_level(amount, risk_level)
    
    approval_item = {
        "uetr": uetr,
        "amount": amount,
        "currency": currency,
        "risk_level": risk_level,
        "debtor": debtor,
        "creditor": creditor,
        "required_level": required_level.value,
        "status": ApprovalStatus.PENDING.value,
        "created_at": datetime.now().isoformat(),
        "investigation_result": investigation_result,
        "approval_chain": [],
        "notes": [],
    }
    
    # Auto-approve if eligible
    if required_level == ApprovalLevel.AUTO:
        approval_item["status"] = ApprovalStatus.APPROVED.value
        approval_item["approval_chain"].append({
            "level": "auto",
            "approver": "system",
            "action": "auto_approved",
            "timestamp": datetime.now().isoformat(),
        })
    
    _approval_queue[uetr] = approval_item
    return approval_item


@router.get("/queue")
async def get_approval_queue(
    status: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Get approval queue with optional filters."""
    items = list(_approval_queue.values())
    
    if status:
        items = [i for i in items if i["status"] == status]
    if level:
        items = [i for i in items if i["required_level"] == level]
    
    # Sort by created_at descending
    items.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "items": items[:limit],
        "total": len(items),
        "pending": len([i for i in _approval_queue.values() if i["status"] == "pending"]),
        "by_level": {
            "level_1": len([i for i in items if i["required_level"] == "level_1"]),
            "level_2": len([i for i in items if i["required_level"] == "level_2"]),
            "level_3": len([i for i in items if i["required_level"] == "level_3"]),
            "level_4": len([i for i in items if i["required_level"] == "level_4"]),
        },
    }


@router.get("/queue/{uetr}")
async def get_approval_item(uetr: str) -> Dict[str, Any]:
    """Get specific approval item."""
    if uetr not in _approval_queue:
        raise HTTPException(status_code=404, detail="Approval item not found")
    return _approval_queue[uetr]


@router.post("/approve")
async def approve_transaction(request: ApprovalRequest) -> Dict[str, Any]:
    """Approve a transaction."""
    if request.uetr not in _approval_queue:
        raise HTTPException(status_code=404, detail="Approval item not found")
    
    item = _approval_queue[request.uetr]
    
    if item["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Item is already {item['status']}")
    
    item["status"] = ApprovalStatus.APPROVED.value
    item["approval_chain"].append({
        "level": item["required_level"],
        "approver": request.approver_id,
        "action": "approved",
        "notes": request.notes,
        "timestamp": datetime.now().isoformat(),
    })
    
    return {"success": True, "item": item}


@router.post("/reject")
async def reject_transaction(request: ApprovalRequest) -> Dict[str, Any]:
    """Reject a transaction."""
    if request.uetr not in _approval_queue:
        raise HTTPException(status_code=404, detail="Approval item not found")
    
    item = _approval_queue[request.uetr]
    
    if item["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Item is already {item['status']}")
    
    item["status"] = ApprovalStatus.REJECTED.value
    item["approval_chain"].append({
        "level": item["required_level"],
        "approver": request.approver_id,
        "action": "rejected",
        "notes": request.notes,
        "timestamp": datetime.now().isoformat(),
    })
    
    return {"success": True, "item": item}


@router.post("/escalate")
async def escalate_transaction(request: EscalateRequest) -> Dict[str, Any]:
    """Escalate a transaction to higher approval level."""
    if request.uetr not in _approval_queue:
        raise HTTPException(status_code=404, detail="Approval item not found")
    
    item = _approval_queue[request.uetr]
    
    if item["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Item is already {item['status']}")
    
    # Determine next level
    level_order = ["level_1", "level_2", "level_3", "level_4"]
    current_idx = level_order.index(item["required_level"]) if item["required_level"] in level_order else 0
    
    if request.target_level:
        new_level = request.target_level.value
    elif current_idx < len(level_order) - 1:
        new_level = level_order[current_idx + 1]
    else:
        raise HTTPException(status_code=400, detail="Already at highest approval level")
    
    item["required_level"] = new_level
    item["status"] = ApprovalStatus.ESCALATED.value
    item["approval_chain"].append({
        "action": "escalated",
        "from_level": level_order[current_idx] if current_idx < len(level_order) else "unknown",
        "to_level": new_level,
        "reason": request.reason,
        "timestamp": datetime.now().isoformat(),
    })
    
    # Reset to pending for new level
    item["status"] = ApprovalStatus.PENDING.value
    
    return {"success": True, "item": item}


@router.get("/analytics")
async def get_approval_analytics() -> Dict[str, Any]:
    """Get approval workflow analytics."""
    items = list(_approval_queue.values())
    
    total = len(items)
    approved = len([i for i in items if i["status"] == "approved"])
    rejected = len([i for i in items if i["status"] == "rejected"])
    pending = len([i for i in items if i["status"] == "pending"])
    
    # Calculate average processing time for completed items
    completed = [i for i in items if i["status"] in ["approved", "rejected"]]
    
    return {
        "total_transactions": total,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "approval_rate": (approved / total * 100) if total > 0 else 0,
        "by_risk_level": {
            "low": len([i for i in items if i["risk_level"] == "low"]),
            "medium": len([i for i in items if i["risk_level"] == "medium"]),
            "high": len([i for i in items if i["risk_level"] == "high"]),
            "critical": len([i for i in items if i["risk_level"] == "critical"]),
        },
        "volume_pending": sum(i["amount"] for i in items if i["status"] == "pending"),
    }


@router.get("/thresholds")
async def get_approval_thresholds() -> Dict[str, Any]:
    """Get current approval thresholds."""
    return APPROVAL_THRESHOLDS


# Helper to integrate with main app
def init_approval_queue(transactions: Dict[str, Dict[str, Any]]):
    """Initialize approval queue from existing transactions."""
    for uetr, tx_data in transactions.items():
        if tx_data.get("status") == "completed" and tx_data.get("verdict"):
            verdict = tx_data["verdict"]
            parsed = tx_data.get("parsed_message", {})
            amount = parsed.get("amount", {})
            
            add_to_approval_queue(
                uetr=uetr,
                amount=float(amount.get("value", 0)),
                currency=amount.get("currency", "EUR"),
                risk_level=verdict.get("risk_level", "medium"),
                debtor=parsed.get("debtor", {}).get("name", "Unknown"),
                creditor=parsed.get("creditor", {}).get("name", "Unknown"),
                investigation_result=verdict,
            )

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.agents.monitor import (
    monitor_transaction,
    monitor_batch,
    get_monitoring_thresholds,
    get_high_risk_jurisdictions,
)
from backend.store import transactions_store, ALERTS_QUEUE

import logging

router = APIRouter(prefix="/monitor", tags=["Monitor"])
logger = logging.getLogger(__name__)


class MonitorRequest(BaseModel):
    uetr: str


class BatchMonitorRequest(BaseModel):
    uetrs: List[str]


@router.post("/transaction")
async def monitor_single(request: MonitorRequest):
    """Monitor a single transaction in real-time."""
    uetr = request.uetr
    if uetr not in transactions_store:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx_data = transactions_store[uetr]
    parsed = tx_data.get("parsed_message", {})

    # Build transaction object for monitoring
    transaction = {
        "uetr": uetr,
        "amount": parsed.get("amount", {}),
        "debtor": parsed.get("debtor", {}),
        "creditor": parsed.get("creditor", {}),
    }

    # monitor_transaction already creates alerts via tools
    result = monitor_transaction(transaction)

    return result


@router.post("/batch")
async def monitor_batch_endpoint(request: BatchMonitorRequest):
    """Monitor a batch of transactions."""
    transactions = []
    for uetr in request.uetrs:
        if uetr in transactions_store:
            parsed = transactions_store[uetr].get("parsed_message", {})
            transactions.append(
                {
                    "uetr": uetr,
                    "amount": parsed.get("amount", {}),
                    "debtor": parsed.get("debtor", {}),
                    "creditor": parsed.get("creditor", {}),
                }
            )

    if not transactions:
        raise HTTPException(status_code=404, detail="No valid transactions found")

    return monitor_batch(transactions)


@router.post("/all")
async def monitor_all_pending():
    """Trigger monitoring for all pending transactions in the store."""
    try:
        results = []

        # Filter for pending transactions
        pending_txs = [
            data["parsed_message"]
            for uetr, data in transactions_store.items()
            if data.get("status") == "pending"
        ]

        if not pending_txs:
            return {"message": "No pending transactions to monitor", "processed": 0}

        # Monitor using batch function
        batch_result = monitor_batch(pending_txs)

        # Alerts are already added to ALERTS_QUEUE by the tools called within monitor_batch

        return {
            "message": f"Monitored {len(pending_txs)} transactions",
            "processed": len(pending_txs),
            "alerts_generated": batch_result.get("total_alerts", 0),
            "risk_summary": batch_result.get("risk_summary"),
        }
    except Exception as e:
        logger.error(f"Monitor all failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(status: Optional[str] = None):
    """Get monitoring alerts."""
    if status and status != "all":
        return {
            "alerts": [a for a in ALERTS_QUEUE if a["status"] == status],
            "total": len(ALERTS_QUEUE),
            "by_severity": _count_severity(
                [a for a in ALERTS_QUEUE if a["status"] == status]
            ),
        }

    return {
        "alerts": ALERTS_QUEUE,
        "total": len(ALERTS_QUEUE),
        "by_severity": _count_severity(ALERTS_QUEUE),
    }


@router.post("/alerts/clear")
async def clear_alerts():
    """Clear all alerts."""
    # We need to modify the list in place or use clear()
    ALERTS_QUEUE.clear()
    return {"success": True, "message": "All alerts cleared"}


@router.get("/thresholds")
async def get_thresholds():
    """Get current monitoring thresholds."""
    return get_monitoring_thresholds()


@router.get("/high-risk-jurisdictions")
async def get_jurisdictions():
    """Get high-risk jurisdictions."""
    return get_high_risk_jurisdictions()


def _count_severity(alerts):
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for a in alerts:
        sev = a.get("severity", "low")
        if sev in counts:
            counts[sev] += 1
    return counts

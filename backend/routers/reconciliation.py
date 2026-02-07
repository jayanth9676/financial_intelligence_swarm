from fastapi import APIRouter
from pydantic import BaseModel

from backend.agents.reconciliation import (
    get_reconciliation_status,
    match_transactions,
    identify_discrepancy,
    resolve_discrepancy,
    generate_reconciliation_report,
    get_internal_records,
    get_statement_entries,
)

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])

class ResolveRequest(BaseModel):
    record_id: str
    resolution_type: str
    notes: str = ""

class StatementEntry(BaseModel):
    entry_id: str
    reference: str
    amount: float
    currency: str
    booking_date: str
    value_date: str
    creditor_name: str
    status: str

@router.get("/status")
async def get_status():
    """Get reconciliation status."""
    return get_reconciliation_status.invoke({})

@router.get("/match")
async def run_matching(tolerance_amount: float = 0.01, tolerance_days: int = 3):
    """Run transaction matching."""
    return match_transactions.invoke({
        "tolerance_amount": tolerance_amount,
        "tolerance_days": tolerance_days
    })

@router.get("/discrepancy/{record_id}")
async def get_discrepancy_details(record_id: str):
    """Identify root cause of discrepancy."""
    return identify_discrepancy.invoke({"record_id": record_id})

@router.post("/resolve")
async def resolve(request: ResolveRequest):
    """Resolve a discrepancy."""
    return resolve_discrepancy.invoke({
        "record_id": request.record_id,
        "resolution_type": request.resolution_type,
        "notes": request.notes
    })

@router.get("/report")
async def get_report(type: str = "summary"):
    """Generate reconciliation report."""
    return generate_reconciliation_report.invoke({"report_type": type})

@router.get("/records")
async def list_records():
    """Get internal records."""
    return get_internal_records()

@router.get("/entries")
async def list_entries():
    """Get bank statement entries."""
    return get_statement_entries()

from fastapi import APIRouter
from pydantic import BaseModel

from backend.agents.compliance_reviewer import (
    get_compliance_deadlines,
    get_compliance_status,
    generate_compliance_report,
    add_compliance_deadline,
    get_calendar,
    get_all_frameworks,
)
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/compliance", tags=["compliance"])
logger = logging.getLogger(__name__)


class DeadlineRequest(BaseModel):
    title: str
    regulation: str
    due_date: str
    priority: str = "medium"
    description: str = ""


@router.get("/deadlines")
async def get_deadlines(days_ahead: int = 30):
    """Get upcoming regulatory deadlines."""
    try:
        # Use direct logic instead of tool invocation for speed/reliability
        calendar = get_calendar()
        cutoff = datetime.now() + timedelta(days=days_ahead)
        upcoming = [
            d for d in calendar if datetime.fromisoformat(d["due_date"]) <= cutoff
        ]
        upcoming.sort(key=lambda x: x["due_date"])

        return {
            "deadlines": upcoming,
            "total": len(upcoming),
            "high_priority": len([d for d in upcoming if d["priority"] == "high"]),
            "overdue": len(
                [
                    d
                    for d in upcoming
                    if datetime.fromisoformat(d["due_date"]) < datetime.now()
                ]
            ),
        }
    except Exception as e:
        logger.error(f"Get deadlines failed: {e}", exc_info=True)
        # Return fallback data instead of 500 to keep UI alive
        return {
            "deadlines": [],
            "total": 0,
            "high_priority": 0,
            "overdue": 0,
            "error": str(e),
        }


@router.get("/status")
async def get_status(framework: str = "all"):
    """Get compliance status for frameworks."""
    try:
        # Use direct logic
        all_frameworks = get_all_frameworks()

        if framework == "all":
            statuses = all_frameworks
        else:
            statuses = {framework: all_frameworks.get(framework, {"status": "unknown"})}

        # Calculate overall status
        all_statuses = [s["status"] for s in all_frameworks.values()]
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
    except Exception as e:
        logger.error(f"Get status failed: {e}", exc_info=True)
        return {"frameworks": {}, "overall_status": "unknown", "error": str(e)}


@router.get("/status")
async def get_status(framework: str = "all"):
    """Get compliance status for frameworks."""
    # Use direct logic
    all_frameworks = get_all_frameworks()

    if framework == "all":
        statuses = all_frameworks
    else:
        statuses = {framework: all_frameworks.get(framework, {"status": "unknown"})}

    # Calculate overall status
    all_statuses = [s["status"] for s in all_frameworks.values()]
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


@router.get("/report")
async def get_report(type: str = "summary"):
    """Generate compliance report."""
    return generate_compliance_report.invoke({"report_type": type})


@router.post("/deadlines")
async def create_deadline(deadline: DeadlineRequest):
    """Add a new compliance deadline."""
    return add_compliance_deadline.invoke(
        {
            "title": deadline.title,
            "regulation": deadline.regulation,
            "due_date": deadline.due_date,
            "priority": deadline.priority,
            "description": deadline.description,
        }
    )

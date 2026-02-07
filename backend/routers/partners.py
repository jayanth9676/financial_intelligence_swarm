from fastapi import APIRouter, HTTPException
from typing import Optional

from backend.agents.partner_fraud import (
    get_all_partners,
    get_partner,
    analyze_partner_network,
    detect_commission_fraud,
    get_partner_risk_score,
    get_affiliate_connections,
)

router = APIRouter(prefix="/partners", tags=["partners"])

@router.get("/")
async def list_partners():
    """Get all partners."""
    return get_all_partners()

@router.get("/{partner_id}")
async def get_partner_details(partner_id: str):
    """Get specific partner details."""
    partner = get_partner(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return partner

@router.get("/{partner_id}/risk")
async def get_risk(partner_id: str):
    """Get partner risk score."""
    return get_partner_risk_score.invoke({"partner_id": partner_id})

@router.get("/{partner_id}/network")
async def get_network(partner_id: str, depth: int = 2):
    """Get affiliate connection network."""
    return get_affiliate_connections.invoke({"partner_id": partner_id, "depth": depth})

@router.post("/analyze")
async def analyze_network(partner_id: Optional[str] = None):
    """Analyze partner network for fraud patterns."""
    return analyze_partner_network.invoke({"partner_id": partner_id})

@router.get("/fraud/circular")
async def get_circular_fraud():
    """Detect circular referral patterns."""
    # This tool is available in the agent file but not exported directly in the list at the bottom
    # However, it is imported in the router if I import it. 
    # Let's import it from the agent file.
    from backend.agents.partner_fraud import detect_circular_referrals
    return detect_circular_referrals.invoke({})

@router.get("/fraud/commission")
async def get_commission_fraud(partner_id: Optional[str] = None):
    """Detect commission fraud."""
    return detect_commission_fraud.invoke({"partner_id": partner_id})

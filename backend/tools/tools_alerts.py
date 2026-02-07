"""Transaction Monitoring Alert Tools for real-time detection.

These tools implement rule-based detection patterns enhanced with AI:
- Velocity checks (rapid transactions)
- Structuring detection (amounts just below thresholds)
- High-risk jurisdiction flags
- Round amount detection
- Cross-border pattern analysis
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.store import ALERTS_QUEUE

# Default thresholds - can be configured per institution
DEFAULT_THRESHOLDS = {
    "velocity_window_hours": 24,
    "velocity_max_count": 10,
    "velocity_max_amount": 50000,
    "structuring_threshold": 10000,
    "structuring_margin_percent": 15,
    "high_value_threshold": 25000,
    "round_amount_tolerance": 100,
}

# High-risk jurisdictions (FATF grey/black list examples)
HIGH_RISK_JURISDICTIONS = {
    "KP": "North Korea",
    "IR": "Iran",
    "SY": "Syria",
    "YE": "Yemen",
    "MM": "Myanmar",
    "AF": "Afghanistan",
    "VU": "Vanuatu",
}


class AlertInput(BaseModel):
    """Input for alert creation."""

    transaction_uetr: str = Field(description="Transaction UETR")
    alert_type: str = Field(
        description="Type of alert: velocity|structuring|jurisdiction|round_amount|high_value"
    )
    severity: str = Field(description="Alert severity: low|medium|high|critical")
    details: str = Field(description="Detailed description of the alert")


class VelocityCheckInput(BaseModel):
    """Input for velocity check."""

    entity_name: str = Field(description="Name of the entity to check")
    window_hours: int = Field(default=24, description="Time window for velocity check")


class StructuringCheckInput(BaseModel):
    """Input for structuring detection."""

    amount: float = Field(description="Transaction amount")
    currency: str = Field(default="EUR", description="Currency code")


class JurisdictionCheckInput(BaseModel):
    """Input for jurisdiction risk check."""

    country_code: str = Field(description="ISO 3166-1 alpha-2 country code")


class PatternAnalysisInput(BaseModel):
    """Input for comprehensive pattern analysis."""

    transaction_uetr: str = Field(description="Transaction UETR")
    amount: float = Field(description="Transaction amount")
    currency: str = Field(description="Currency code")
    debtor_country: Optional[str] = Field(
        default=None, description="Debtor country code"
    )
    creditor_country: Optional[str] = Field(
        default=None, description="Creditor country code"
    )
    debtor_name: str = Field(description="Debtor entity name")
    creditor_name: str = Field(description="Creditor entity name")


# --- Core Logic Functions (Direct Call) ---


def _check_velocity(entity_name: str, window_hours: int = 24) -> Dict[str, Any]:
    """Core logic for velocity check."""
    # In production, query database for actual transaction history
    # Mock implementation for demo
    mock_transactions = [
        {
            "amount": 5000,
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
        },
        {
            "amount": 4500,
            "timestamp": (datetime.now() - timedelta(hours=4)).isoformat(),
        },
        {
            "amount": 4800,
            "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
        },
        {
            "amount": 5200,
            "timestamp": (datetime.now() - timedelta(hours=8)).isoformat(),
        },
    ]

    transaction_count = len(mock_transactions)
    total_amount = sum(t["amount"] for t in mock_transactions)

    velocity_exceeded = (
        transaction_count > DEFAULT_THRESHOLDS["velocity_max_count"]
        or total_amount > DEFAULT_THRESHOLDS["velocity_max_amount"]
    )

    return {
        "entity": entity_name,
        "window_hours": window_hours,
        "transaction_count": transaction_count,
        "total_amount": total_amount,
        "velocity_exceeded": velocity_exceeded,
        "max_count_threshold": DEFAULT_THRESHOLDS["velocity_max_count"],
        "max_amount_threshold": DEFAULT_THRESHOLDS["velocity_max_amount"],
        "alert_triggered": velocity_exceeded,
        "risk_level": "high" if velocity_exceeded else "low",
    }


def _detect_structuring(amount: float, currency: str = "EUR") -> Dict[str, Any]:
    """Core logic for structuring detection."""
    threshold = DEFAULT_THRESHOLDS["structuring_threshold"]
    margin = threshold * (DEFAULT_THRESHOLDS["structuring_margin_percent"] / 100)

    # Transaction is suspicious if it's just below the threshold
    is_suspicious = (threshold - margin) < amount < threshold

    # Also check for classic structuring amounts
    classic_structuring_amounts = [9900, 9500, 9000, 4999, 4900]
    is_classic_pattern = any(
        abs(amount - pattern) < DEFAULT_THRESHOLDS["round_amount_tolerance"]
        for pattern in classic_structuring_amounts
    )

    structuring_detected = is_suspicious or is_classic_pattern

    return {
        "amount": amount,
        "currency": currency,
        "threshold": threshold,
        "margin": margin,
        "is_below_threshold": amount < threshold,
        "is_within_suspicious_range": is_suspicious,
        "matches_classic_pattern": is_classic_pattern,
        "structuring_detected": structuring_detected,
        "risk_level": "high" if structuring_detected else "low",
        "alert_triggered": structuring_detected,
    }


def _check_jurisdiction_risk(country_code: str) -> Dict[str, Any]:
    """Core logic for jurisdiction check."""
    country_upper = country_code.upper() if country_code else ""
    is_high_risk = country_upper in HIGH_RISK_JURISDICTIONS

    return {
        "country_code": country_upper,
        "country_name": HIGH_RISK_JURISDICTIONS.get(country_upper, "Unknown"),
        "is_high_risk": is_high_risk,
        "fatf_status": "blacklist"
        if country_upper in ["KP", "IR"]
        else "greylist"
        if is_high_risk
        else "compliant",
        "risk_level": "critical"
        if country_upper in ["KP", "IR"]
        else "high"
        if is_high_risk
        else "low",
        "alert_triggered": is_high_risk,
        "sanctions_programs": ["OFAC", "EU", "UN"] if is_high_risk else [],
    }


def _detect_round_amounts(amount: float, currency: str = "EUR") -> Dict[str, Any]:
    """Core logic for round amount detection."""
    # Check if amount is suspiciously round
    is_perfectly_round = amount % 1000 == 0 and amount >= 1000
    is_mostly_round = amount % 100 == 0 and amount >= 5000

    # Common structuring round amounts
    suspicious_rounds = [5000, 10000, 15000, 20000, 25000, 50000, 100000]
    matches_suspicious = amount in suspicious_rounds

    is_suspicious = is_perfectly_round or matches_suspicious

    return {
        "amount": amount,
        "currency": currency,
        "is_perfectly_round": is_perfectly_round,
        "is_mostly_round": is_mostly_round,
        "matches_suspicious_pattern": matches_suspicious,
        "is_suspicious": is_suspicious,
        "risk_level": "medium" if is_suspicious else "low",
        "alert_triggered": is_suspicious
        and amount >= DEFAULT_THRESHOLDS["high_value_threshold"],
    }


def _create_alert(
    transaction_uetr: str, alert_type: str, severity: str, details: str
) -> Dict[str, Any]:
    """Core logic to create alert."""
    alert_id = f"ALERT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(ALERTS_QUEUE)}"

    alert = {
        "alert_id": alert_id,
        "transaction_uetr": transaction_uetr,
        "alert_type": alert_type,
        "severity": severity,
        "details": details,
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "acknowledged_at": None,
        "resolved_at": None,
    }

    ALERTS_QUEUE.append(alert)

    return {
        "success": True,
        "alert": alert,
        "queue_size": len(ALERTS_QUEUE),
    }


def _analyze_transaction_patterns(
    transaction_uetr: str,
    amount: float,
    currency: str,
    debtor_country: str = None,
    creditor_country: str = None,
    debtor_name: str = "",
    creditor_name: str = "",
) -> Dict[str, Any]:
    """Core logic for pattern analysis."""
    alerts = []
    overall_risk = "low"

    # Check structuring
    structuring = _detect_structuring(amount, currency)
    if structuring["alert_triggered"]:
        alerts.append(
            {
                "type": "structuring",
                "severity": structuring["risk_level"],
                "details": f"Transaction amount {amount} {currency} matches structuring pattern",
            }
        )
        overall_risk = max_risk(overall_risk, structuring["risk_level"])

    # Check round amounts
    round_check = _detect_round_amounts(amount, currency)
    if round_check["alert_triggered"]:
        alerts.append(
            {
                "type": "round_amount",
                "severity": round_check["risk_level"],
                "details": f"Suspicious round amount detected: {amount} {currency}",
            }
        )
        overall_risk = max_risk(overall_risk, round_check["risk_level"])

    # Check jurisdiction risks
    for label, country in [("debtor", debtor_country), ("creditor", creditor_country)]:
        if country:
            jurisdiction = _check_jurisdiction_risk(country)
            if jurisdiction["alert_triggered"]:
                alerts.append(
                    {
                        "type": "jurisdiction",
                        "severity": jurisdiction["risk_level"],
                        "details": f"High-risk {label} jurisdiction: {jurisdiction['country_name']} ({country})",
                    }
                )
                overall_risk = max_risk(overall_risk, jurisdiction["risk_level"])

    # Check velocity for both parties
    for entity in [debtor_name, creditor_name]:
        if entity:
            velocity = _check_velocity(entity)
            if velocity["alert_triggered"]:
                alerts.append(
                    {
                        "type": "velocity",
                        "severity": velocity["risk_level"],
                        "details": f"High transaction velocity for {entity}: {velocity['transaction_count']} transactions",
                    }
                )
                overall_risk = max_risk(overall_risk, velocity["risk_level"])

    # Cross-border check
    if debtor_country and creditor_country and debtor_country != creditor_country:
        is_cross_border = True
        # Cross-border to high-risk adds extra concern
        combined_risk = any(
            c in HIGH_RISK_JURISDICTIONS for c in [debtor_country, creditor_country]
        )
        if combined_risk:
            alerts.append(
                {
                    "type": "cross_border",
                    "severity": "high",
                    "details": "Cross-border transaction involving high-risk jurisdiction",
                }
            )
            overall_risk = max_risk(overall_risk, "high")
    else:
        is_cross_border = False

    return {
        "transaction_uetr": transaction_uetr,
        "amount": amount,
        "currency": currency,
        "is_cross_border": is_cross_border,
        "alerts_generated": len(alerts),
        "alerts": alerts,
        "overall_risk": overall_risk,
        "requires_investigation": overall_risk in ["high", "critical"],
        "timestamp": datetime.now().isoformat(),
    }


# --- Tool Wrappers (for Agents) ---


@tool
def check_velocity(entity_name: str, window_hours: int = 24) -> Dict[str, Any]:
    """Check transaction velocity for an entity.

    Detects rapid successive transactions that may indicate money laundering
    or automated fraud.

    Args:
        entity_name: Name of the entity to check
        window_hours: Time window in hours to check (default 24)

    Returns:
        Velocity analysis results with alert if threshold exceeded
    """
    return _check_velocity(entity_name, window_hours)


@tool
def detect_structuring(amount: float, currency: str = "EUR") -> Dict[str, Any]:
    """Detect potential structuring (smurfing).

    Identifies transactions deliberately kept below reporting thresholds.

    Args:
        amount: Transaction amount
        currency: Currency code

    Returns:
        Structuring analysis with risk assessment
    """
    return _detect_structuring(amount, currency)


@tool
def check_jurisdiction_risk(country_code: str) -> Dict[str, Any]:
    """Check if a jurisdiction is high-risk.

    Flags transactions involving FATF grey/black list countries.

    Args:
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        Jurisdiction risk assessment
    """
    return _check_jurisdiction_risk(country_code)


@tool
def detect_round_amounts(amount: float, currency: str = "EUR") -> Dict[str, Any]:
    """Detect suspicious round amounts.

    Round amounts may indicate manufactured transactions rather than
    legitimate commercial payments.

    Args:
        amount: Transaction amount
        currency: Currency code

    Returns:
        Round amount analysis
    """
    return _detect_round_amounts(amount, currency)


@tool
def analyze_transaction_patterns(
    transaction_uetr: str,
    amount: float,
    currency: str,
    debtor_country: str = None,
    creditor_country: str = None,
    debtor_name: str = "",
    creditor_name: str = "",
) -> Dict[str, Any]:
    """Comprehensive pattern analysis for a transaction.

    Runs all detection checks and aggregates results.

    Args:
        transaction_uetr: Transaction UETR
        amount: Transaction amount
        currency: Currency code
        debtor_country: Debtor country code
        creditor_country: Creditor country code
        debtor_name: Debtor entity name
        creditor_name: Creditor entity name

    Returns:
        Comprehensive risk analysis with all patterns checked
    """
    return _analyze_transaction_patterns(
        transaction_uetr,
        amount,
        currency,
        debtor_country,
        creditor_country,
        debtor_name,
        creditor_name,
    )


@tool
def create_alert(
    transaction_uetr: str, alert_type: str, severity: str, details: str
) -> Dict[str, Any]:
    """Create a monitoring alert and add to queue.

    Args:
        transaction_uetr: Transaction UETR
        alert_type: Type of alert
        severity: Alert severity
        details: Detailed description

    Returns:
        Created alert with ID
    """
    return _create_alert(transaction_uetr, alert_type, severity, details)


@tool
def get_alert_queue(status: str = "open") -> Dict[str, Any]:
    """Get current alert queue.

    Args:
        status: Filter by status (open|acknowledged|resolved|all)

    Returns:
        List of alerts matching the filter
    """
    if status == "all":
        alerts = ALERTS_QUEUE
    else:
        alerts = [a for a in ALERTS_QUEUE if a["status"] == status]

    return {
        "alerts": alerts,
        "total": len(alerts),
        "by_severity": {
            "critical": len([a for a in alerts if a["severity"] == "critical"]),
            "high": len([a for a in alerts if a["severity"] == "high"]),
            "medium": len([a for a in alerts if a["severity"] == "medium"]),
            "low": len([a for a in alerts if a["severity"] == "low"]),
        },
    }


def max_risk(current: str, new: str) -> str:
    """Return the higher risk level."""
    risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if risk_order.get(new, 0) > risk_order.get(current, 0):
        return new
    return current


def clear_alert_queue():
    """Clear the alert queue (for testing)."""
    ALERTS_QUEUE.clear()

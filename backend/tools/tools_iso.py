from typing import Dict, Any
import xmltodict
from langchain_core.tools import tool


@tool
def parse_pacs008(xml_content: str) -> Dict[str, Any]:
    """Parse a pacs.008 FI-to-FI Customer Credit Transfer message.

    Extracts key fields: UETR, debtor, creditor, amount, purpose codes.

    Args:
        xml_content: The raw XML content of the pacs.008 message

    Returns:
        Dict with parsed transaction details
    """
    try:
        doc = xmltodict.parse(xml_content)

        # Navigate to the main document
        root = doc.get("Document", doc)
        fi_to_fi = root.get("FIToFICstmrCdtTrf", {}) or {}

        # Group Header
        grp_hdr = fi_to_fi.get("GrpHdr", {}) or {}

        # Credit Transfer Info
        cdt_trf = fi_to_fi.get("CdtTrfTxInf", {}) or {}
        if isinstance(cdt_trf, list):
            cdt_trf = cdt_trf[0] if cdt_trf else {}  # Handle multiple transactions

        # Payment ID
        pmt_id = (cdt_trf.get("PmtId", {}) if cdt_trf else {}) or {}

        # Debtor info
        dbtr = (cdt_trf.get("Dbtr", {}) if cdt_trf else {}) or {}
        dbtr_acct_parent = (cdt_trf.get("DbtrAcct", {}) if cdt_trf else {}) or {}
        dbtr_acct = (dbtr_acct_parent.get("Id", {}) if dbtr_acct_parent else {}) or {}
        dbtr_agt_parent = (cdt_trf.get("DbtrAgt", {}) if cdt_trf else {}) or {}
        dbtr_agt = (
            dbtr_agt_parent.get("FinInstnId", {}) if dbtr_agt_parent else {}
        ) or {}

        # Creditor info
        cdtr = (cdt_trf.get("Cdtr", {}) if cdt_trf else {}) or {}
        cdtr_acct_parent = (cdt_trf.get("CdtrAcct", {}) if cdt_trf else {}) or {}
        cdtr_acct = (cdtr_acct_parent.get("Id", {}) if cdtr_acct_parent else {}) or {}
        cdtr_agt_parent = (cdt_trf.get("CdtrAgt", {}) if cdt_trf else {}) or {}
        cdtr_agt = (
            cdtr_agt_parent.get("FinInstnId", {}) if cdtr_agt_parent else {}
        ) or {}

        # Amount
        amt = (cdt_trf.get("IntrBkSttlmAmt", {}) if cdt_trf else {}) or {}

        # Remittance info
        rmt_inf = (cdt_trf.get("RmtInf", {}) if cdt_trf else {}) or {}

        # Purp handling
        purp = (cdt_trf.get("Purp", {}) if cdt_trf else {}) or {}

        return {
            "message_type": "pacs.008",
            "uetr": pmt_id.get("UETR", "") if pmt_id else "",
            "end_to_end_id": pmt_id.get("EndToEndId", "") if pmt_id else "",
            "creation_datetime": grp_hdr.get("CreDtTm", "") if grp_hdr else "",
            "settlement_date": cdt_trf.get("IntrBkSttlmDt", "") if cdt_trf else "",
            "debtor": {
                "name": dbtr.get("Nm", "") if dbtr else "",
                "address": _extract_address(dbtr.get("PstlAdr", {}) if dbtr else {}),
                "account_iban": dbtr_acct.get("IBAN", "") if dbtr_acct else "",
                "agent_bic": dbtr_agt.get("BICFI", "") if dbtr_agt else "",
            },
            "creditor": {
                "name": cdtr.get("Nm", "") if cdtr else "",
                "address": _extract_address(cdtr.get("PstlAdr", {}) if cdtr else {}),
                "account_iban": cdtr_acct.get("IBAN", "") if cdtr_acct else "",
                "agent_bic": cdtr_agt.get("BICFI", "") if cdtr_agt else "",
            },
            "amount": {
                "value": amt.get("#text", "0")
                if isinstance(amt, dict)
                else str(amt)
                if amt
                else "0",
                "currency": amt.get("@Ccy", "EUR") if isinstance(amt, dict) else "EUR",
            },
            "remittance_info": _extract_remittance(rmt_inf),
            "purpose_code": purp.get("Cd", "") if purp else "",
            "parsed_successfully": True,
        }
    except Exception as e:
        return {
            "message_type": "pacs.008",
            "parsed_successfully": False,
            "error": str(e),
        }


def _extract_address(postal_addr: Dict) -> Dict[str, str]:
    """Extract structured or unstructured address."""
    if not postal_addr:
        return {}

    return {
        "street": postal_addr.get("StrtNm", ""),
        "building": postal_addr.get("BldgNb", ""),
        "postal_code": postal_addr.get("PstCd", ""),
        "town": postal_addr.get("TwnNm", ""),
        "country": postal_addr.get("Ctry", ""),
        "address_lines": postal_addr.get("AdrLine", [])
        if isinstance(postal_addr.get("AdrLine"), list)
        else [postal_addr.get("AdrLine", "")],
    }


def _extract_remittance(rmt_inf: Dict) -> Dict[str, Any]:
    """Extract remittance information."""
    if not rmt_inf:
        return {}

    return {
        "unstructured": rmt_inf.get("Ustrd", ""),
        "structured": rmt_inf.get("Strd", {}),
    }


@tool
def parse_pain001(xml_content: str) -> Dict[str, Any]:
    """Parse a pain.001 Customer Credit Transfer Initiation message.

    Args:
        xml_content: The raw XML content of the pain.001 message

    Returns:
        Dict with parsed payment initiation details
    """
    try:
        doc = xmltodict.parse(xml_content)

        root = doc.get("Document", doc)
        cstmr_cdt_trf = root.get("CstmrCdtTrfInitn", {})

        grp_hdr = cstmr_cdt_trf.get("GrpHdr", {})
        pmt_inf = cstmr_cdt_trf.get("PmtInf", {})

        if isinstance(pmt_inf, list):
            pmt_inf = pmt_inf[0]

        cdt_trf_tx = pmt_inf.get("CdtTrfTxInf", {})
        if isinstance(cdt_trf_tx, list):
            cdt_trf_tx = cdt_trf_tx[0]

        dbtr = pmt_inf.get("Dbtr", {})
        dbtr_acct = pmt_inf.get("DbtrAcct", {}).get("Id", {})

        cdtr = cdt_trf_tx.get("Cdtr", {})
        cdtr_acct = cdt_trf_tx.get("CdtrAcct", {}).get("Id", {})

        amt = cdt_trf_tx.get("Amt", {}).get("InstdAmt", {})

        return {
            "message_type": "pain.001",
            "message_id": grp_hdr.get("MsgId", ""),
            "creation_datetime": grp_hdr.get("CreDtTm", ""),
            "number_of_transactions": grp_hdr.get("NbOfTxs", "1"),
            "payment_info_id": pmt_inf.get("PmtInfId", ""),
            "requested_execution_date": pmt_inf.get("ReqdExctnDt", ""),
            "debtor": {
                "name": dbtr.get("Nm", ""),
                "account_iban": dbtr_acct.get("IBAN", ""),
            },
            "creditor": {
                "name": cdtr.get("Nm", ""),
                "account_iban": cdtr_acct.get("IBAN", ""),
            },
            "amount": {
                "value": amt.get("#text", "0") if isinstance(amt, dict) else str(amt),
                "currency": amt.get("@Ccy", "EUR") if isinstance(amt, dict) else "EUR",
            },
            "end_to_end_id": cdt_trf_tx.get("PmtId", {}).get("EndToEndId", ""),
            "parsed_successfully": True,
        }
    except Exception as e:
        return {
            "message_type": "pain.001",
            "parsed_successfully": False,
            "error": str(e),
        }


@tool
def parse_camt053(xml_content: str) -> Dict[str, Any]:
    """Parse a camt.053 Bank-to-Customer Statement message.

    Used for reconciliation and detecting smurfing patterns.

    Args:
        xml_content: The raw XML content of the camt.053 message

    Returns:
        Dict with parsed statement details and transaction entries
    """
    try:
        doc = xmltodict.parse(xml_content)

        root = doc.get("Document", doc)
        bk_to_cstmr_stmt = root.get("BkToCstmrStmt", {})

        grp_hdr = bk_to_cstmr_stmt.get("GrpHdr", {})
        stmt = bk_to_cstmr_stmt.get("Stmt", {})

        if isinstance(stmt, list):
            stmt = stmt[0]

        # Account info
        acct = stmt.get("Acct", {})
        acct_id = acct.get("Id", {})

        # Balances
        bal_list = stmt.get("Bal", [])
        if not isinstance(bal_list, list):
            bal_list = [bal_list]

        balances = []
        for bal in bal_list:
            amt = bal.get("Amt", {})
            balances.append(
                {
                    "type": bal.get("Tp", {}).get("CdOrPrtry", {}).get("Cd", ""),
                    "amount": amt.get("#text", "0")
                    if isinstance(amt, dict)
                    else str(amt),
                    "currency": amt.get("@Ccy", "EUR")
                    if isinstance(amt, dict)
                    else "EUR",
                    "date": bal.get("Dt", {}).get("Dt", ""),
                }
            )

        # Entries (transactions)
        ntry_list = stmt.get("Ntry", [])
        if not isinstance(ntry_list, list):
            ntry_list = [ntry_list] if ntry_list else []

        entries = []
        for ntry in ntry_list:
            amt = ntry.get("Amt", {})
            entries.append(
                {
                    "amount": amt.get("#text", "0")
                    if isinstance(amt, dict)
                    else str(amt),
                    "currency": amt.get("@Ccy", "EUR")
                    if isinstance(amt, dict)
                    else "EUR",
                    "credit_debit": ntry.get("CdtDbtInd", ""),
                    "status": ntry.get("Sts", ""),
                    "booking_date": ntry.get("BookgDt", {}).get("Dt", ""),
                    "value_date": ntry.get("ValDt", {}).get("Dt", ""),
                    "reference": ntry.get("NtryRef", ""),
                }
            )

        return {
            "message_type": "camt.053",
            "message_id": grp_hdr.get("MsgId", ""),
            "creation_datetime": grp_hdr.get("CreDtTm", ""),
            "statement_id": stmt.get("Id", ""),
            "account": {
                "iban": acct_id.get("IBAN", ""),
                "currency": acct.get("Ccy", ""),
            },
            "balances": balances,
            "entries": entries,
            "entry_count": len(entries),
            "parsed_successfully": True,
        }
    except Exception as e:
        return {
            "message_type": "camt.053",
            "parsed_successfully": False,
            "error": str(e),
        }


@tool
def detect_structuring_pattern(
    entries_json: str, threshold: float = 10000
) -> Dict[str, Any]:
    """Analyze transaction entries for structuring (smurfing) patterns.

    Looks for multiple transactions just below reporting thresholds.

    Args:
        entries_json: JSON string containing list of transaction entries from camt.053.
                      Each entry should have 'amount', 'booking_date', and 'reference' fields.
                      Example: '[{"amount": "9500", "booking_date": "2026-01-15", "reference": "REF001"}]'
        threshold: The reporting threshold to check against (default 10000)

    Returns:
        Dict with structuring analysis
    """
    import json

    # Parse entries from JSON string
    try:
        entries = json.loads(entries_json) if entries_json else []
    except json.JSONDecodeError:
        return {
            "error": "Invalid JSON format for entries",
            "threshold": threshold,
            "structuring_detected": False,
            "risk_level": "unknown",
        }

    suspicious_entries = []
    near_threshold_count = 0
    total_near_threshold = 0.0

    for entry in entries:
        try:
            amount = float(entry.get("amount", 0))
            # Check if amount is suspiciously close to threshold (80-99% of threshold)
            if 0.8 * threshold <= amount < threshold:
                near_threshold_count += 1
                total_near_threshold += amount
                suspicious_entries.append(
                    {
                        "amount": amount,
                        "date": entry.get("booking_date", ""),
                        "reference": entry.get("reference", ""),
                    }
                )
        except (ValueError, TypeError):
            continue

    structuring_score = min(
        1.0, near_threshold_count / 5
    )  # 5+ transactions = max score

    return {
        "threshold": threshold,
        "near_threshold_transactions": near_threshold_count,
        "total_near_threshold_amount": total_near_threshold,
        "suspicious_entries": suspicious_entries,
        "structuring_score": structuring_score,
        "structuring_detected": near_threshold_count >= 3,
        "risk_level": "high"
        if near_threshold_count >= 5
        else "medium"
        if near_threshold_count >= 3
        else "low",
    }

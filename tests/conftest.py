"""Pytest configuration and shared fixtures for FIS tests."""

import pytest
from typing import Dict, Any


# Sample ISO 20022 messages for testing
SAMPLE_PACS008_SUSPICIOUS = {
    "uetr": "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e",
    "message_type": "pacs.008",
    "end_to_end_id": "E2E-TARGET-001",
    "debtor": {
        "name": "Shell Company Alpha",
        "account_iban": "DE89370400440532013000",
        "agent_bic": "DEUTDEFFXXX",
    },
    "creditor": {
        "name": "Offshore Holdings LLC",
        "account_iban": "CY17002001280000001200527600",
        "agent_bic": "BCYPCY2NXXX",
    },
    "amount": {
        "value": "245000.00",
        "currency": "EUR",
    },
    "settlement_date": "2026-02-03",
    "purpose_code": "CORT",
    "remittance_info": {
        "unstructured": "Consulting services Q1 2026",
    },
}

SAMPLE_PACS008_LEGITIMATE = {
    "uetr": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "message_type": "pacs.008",
    "end_to_end_id": "E2E-LEGIT-001",
    "debtor": {
        "name": "Muller & Sons KG",
        "account_iban": "DE89370400440532013000",
        "agent_bic": "DEUTDEFFXXX",
    },
    "creditor": {
        "name": "AWS EMEA SARL",
        "account_iban": "LU280019400644750000",
        "agent_bic": "BABORLPX",
    },
    "amount": {
        "value": "13836.82",
        "currency": "EUR",
    },
    "settlement_date": "2026-02-03",
    "purpose_code": "SUPP",
    "remittance_info": {
        "unstructured": "Monthly cloud services invoice #9336",
    },
}

SAMPLE_PACS008_MINIMAL = {
    "uetr": "minimal-test-uetr-12345",
    "message_type": "pacs.008",
    "debtor": {"name": "Test Debtor"},
    "creditor": {"name": "Test Creditor"},
    "amount": {"value": "1000", "currency": "EUR"},
}


@pytest.fixture
def suspicious_transaction() -> Dict[str, Any]:
    """Return a suspicious transaction for testing high-risk scenarios."""
    return SAMPLE_PACS008_SUSPICIOUS.copy()


@pytest.fixture
def legitimate_transaction() -> Dict[str, Any]:
    """Return a legitimate transaction for testing low-risk scenarios."""
    return SAMPLE_PACS008_LEGITIMATE.copy()


@pytest.fixture
def minimal_transaction() -> Dict[str, Any]:
    """Return a minimal transaction for basic testing."""
    return SAMPLE_PACS008_MINIMAL.copy()


@pytest.fixture
def target_uetr() -> str:
    """The target UETR for end-to-end testing."""
    return "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"


@pytest.fixture
def mock_graph_response_high_risk() -> Dict[str, Any]:
    """Mock Neo4j graph response indicating high risk."""
    return {
        "has_hidden_links": True,
        "paths": [
            {
                "start": "Shell Company Alpha",
                "end": "Sanctioned Entity X",
                "path": ["Shell Company Alpha", "Intermediary Corp", "Sanctioned Entity X"],
                "relationship_types": ["PAYS", "PAYS"],
                "hop_count": 2,
            }
        ],
        "risk_score": 0.85,
        "sanctioned_connections": 1,
    }


@pytest.fixture
def mock_graph_response_low_risk() -> Dict[str, Any]:
    """Mock Neo4j graph response indicating low risk."""
    return {
        "has_hidden_links": False,
        "paths": [],
        "risk_score": 0.1,
        "sanctioned_connections": 0,
    }


@pytest.fixture
def mock_alibi_evidence() -> Dict[str, Any]:
    """Mock Qdrant alibi search response."""
    return {
        "has_alibi": True,
        "evidence": [
            {
                "content": "Payment authorized per Master Service Agreement dated 2024-01-15",
                "source": "contracts/msa_alpha_2024.pdf",
                "relevance_score": 0.92,
            },
            {
                "content": "Annual payment grid approved by Finance Director",
                "source": "payment_grids/2026_approved.xlsx",
                "relevance_score": 0.88,
            },
        ],
        "exculpatory_strength": 0.85,
    }


@pytest.fixture
def mock_behavioral_drift() -> Dict[str, Any]:
    """Mock Mem0 behavioral drift response."""
    return {
        "drift_detected": True,
        "drift_score": 0.65,
        "baseline_avg_amount": 15000.0,
        "current_amount": 245000.0,
        "deviation_factor": 16.3,
        "baseline_frequency": "weekly",
        "current_frequency": "single_large_payment",
    }


@pytest.fixture
def mock_no_drift() -> Dict[str, Any]:
    """Mock Mem0 response with no behavioral drift."""
    return {
        "drift_detected": False,
        "drift_score": 0.1,
        "baseline_avg_amount": 12000.0,
        "current_amount": 13836.82,
        "deviation_factor": 1.15,
        "within_normal_range": True,
    }


# Sample XML content for ISO parsing tests
SAMPLE_PACS008_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.10">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>FIS-MSG-20260203-001</MsgId>
            <CreDtTm>2026-02-03T09:30:00Z</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <EndToEndId>E2E-TARGET-001</EndToEndId>
                <UETR>eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e</UETR>
            </PmtId>
            <IntrBkSttlmAmt Ccy="EUR">245000.00</IntrBkSttlmAmt>
            <IntrBkSttlmDt>2026-02-03</IntrBkSttlmDt>
            <Dbtr>
                <Nm>Shell Company Alpha</Nm>
            </Dbtr>
            <DbtrAcct>
                <Id>
                    <IBAN>DE89370400440532013000</IBAN>
                </Id>
            </DbtrAcct>
            <DbtrAgt>
                <FinInstnId>
                    <BICFI>DEUTDEFFXXX</BICFI>
                </FinInstnId>
            </DbtrAgt>
            <Cdtr>
                <Nm>Offshore Holdings LLC</Nm>
            </Cdtr>
            <CdtrAcct>
                <Id>
                    <IBAN>CY17002001280000001200527600</IBAN>
                </Id>
            </CdtrAcct>
            <CdtrAgt>
                <FinInstnId>
                    <BICFI>BCYPCY2NXXX</BICFI>
                </FinInstnId>
            </CdtrAgt>
            <Purp>
                <Cd>CORT</Cd>
            </Purp>
            <RmtInf>
                <Ustrd>Consulting services Q1 2026</Ustrd>
            </RmtInf>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>
"""


@pytest.fixture
def target_pacs008_xml() -> str:
    """Return the target UETR pacs.008 XML for end-to-end testing."""
    return SAMPLE_PACS008_XML

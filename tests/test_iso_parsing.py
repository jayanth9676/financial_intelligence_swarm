"""Tests for ISO 20022 message parsing tools."""

from backend.tools.tools_iso import (
    parse_pacs008,
    parse_pain001,
    parse_camt053,
    detect_structuring_pattern,
)


class TestParsePacs008:
    """Tests for pacs.008 FI-to-FI Customer Credit Transfer parsing."""

    def test_parse_valid_pacs008(self):
        """Test parsing a valid pacs.008 message."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
            <FIToFICstmrCdtTrf>
                <GrpHdr>
                    <MsgId>MSG001</MsgId>
                    <CreDtTm>2024-01-15T10:30:00Z</CreDtTm>
                </GrpHdr>
                <CdtTrfTxInf>
                    <PmtId>
                        <EndToEndId>E2E001</EndToEndId>
                        <UETR>eb6305c9-1f7f-49de-aed0-16487c27b42d</UETR>
                    </PmtId>
                    <IntrBkSttlmAmt Ccy="EUR">15000.00</IntrBkSttlmAmt>
                    <IntrBkSttlmDt>2024-01-15</IntrBkSttlmDt>
                    <Dbtr>
                        <Nm>John Doe</Nm>
                    </Dbtr>
                    <DbtrAcct>
                        <Id>
                            <IBAN>DE89370400440532013000</IBAN>
                        </Id>
                    </DbtrAcct>
                    <DbtrAgt>
                        <FinInstnId>
                            <BICFI>COBADEFFXXX</BICFI>
                        </FinInstnId>
                    </DbtrAgt>
                    <Cdtr>
                        <Nm>Jane Smith</Nm>
                    </Cdtr>
                    <CdtrAcct>
                        <Id>
                            <IBAN>FR7630006000011234567890189</IBAN>
                        </Id>
                    </CdtrAcct>
                    <CdtrAgt>
                        <FinInstnId>
                            <BICFI>BNPAFRPPXXX</BICFI>
                        </FinInstnId>
                    </CdtrAgt>
                    <Purp>
                        <Cd>SALA</Cd>
                    </Purp>
                </CdtTrfTxInf>
            </FIToFICstmrCdtTrf>
        </Document>
        """
        result = parse_pacs008.invoke({"xml_content": xml_content})

        assert result["parsed_successfully"] is True
        assert result["message_type"] == "pacs.008"
        assert result["uetr"] == "eb6305c9-1f7f-49de-aed0-16487c27b42d"
        assert result["end_to_end_id"] == "E2E001"
        assert result["debtor"]["name"] == "John Doe"
        assert result["debtor"]["account_iban"] == "DE89370400440532013000"
        assert result["creditor"]["name"] == "Jane Smith"
        assert result["creditor"]["account_iban"] == "FR7630006000011234567890189"
        assert result["purpose_code"] == "SALA"

    def test_parse_invalid_xml(self):
        """Test parsing invalid XML returns error."""
        xml_content = "<invalid><xml"
        result = parse_pacs008.invoke({"xml_content": xml_content})

        assert result["parsed_successfully"] is False
        assert "error" in result

    def test_parse_empty_pacs008(self):
        """Test parsing empty/minimal pacs.008 message."""
        xml_content = """<?xml version="1.0"?>
        <Document>
            <FIToFICstmrCdtTrf>
                <GrpHdr></GrpHdr>
                <CdtTrfTxInf></CdtTrfTxInf>
            </FIToFICstmrCdtTrf>
        </Document>
        """
        result = parse_pacs008.invoke({"xml_content": xml_content})

        assert result["parsed_successfully"] is True
        assert result["uetr"] == ""
        assert result["debtor"]["name"] == ""


class TestParsePain001:
    """Tests for pain.001 Customer Credit Transfer Initiation parsing."""

    def test_parse_valid_pain001(self):
        """Test parsing a valid pain.001 message."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
            <CstmrCdtTrfInitn>
                <GrpHdr>
                    <MsgId>PAYMENT001</MsgId>
                    <CreDtTm>2024-01-15T09:00:00Z</CreDtTm>
                    <NbOfTxs>1</NbOfTxs>
                </GrpHdr>
                <PmtInf>
                    <PmtInfId>PMT001</PmtInfId>
                    <ReqdExctnDt>2024-01-16</ReqdExctnDt>
                    <Dbtr>
                        <Nm>Acme Corporation</Nm>
                    </Dbtr>
                    <DbtrAcct>
                        <Id>
                            <IBAN>DE89370400440532013000</IBAN>
                        </Id>
                    </DbtrAcct>
                    <CdtTrfTxInf>
                        <PmtId>
                            <EndToEndId>INV-2024-001</EndToEndId>
                        </PmtId>
                        <Amt>
                            <InstdAmt Ccy="EUR">5000.00</InstdAmt>
                        </Amt>
                        <Cdtr>
                            <Nm>Supplier Ltd</Nm>
                        </Cdtr>
                        <CdtrAcct>
                            <Id>
                                <IBAN>NL91ABNA0417164300</IBAN>
                            </Id>
                        </CdtrAcct>
                    </CdtTrfTxInf>
                </PmtInf>
            </CstmrCdtTrfInitn>
        </Document>
        """
        result = parse_pain001.invoke({"xml_content": xml_content})

        assert result["parsed_successfully"] is True
        assert result["message_type"] == "pain.001"
        assert result["message_id"] == "PAYMENT001"
        assert result["debtor"]["name"] == "Acme Corporation"
        assert result["creditor"]["name"] == "Supplier Ltd"
        assert result["end_to_end_id"] == "INV-2024-001"


class TestParseCamt053:
    """Tests for camt.053 Bank-to-Customer Statement parsing."""

    def test_parse_valid_camt053(self):
        """Test parsing a valid camt.053 statement."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
            <BkToCstmrStmt>
                <GrpHdr>
                    <MsgId>STMT001</MsgId>
                    <CreDtTm>2024-01-15T18:00:00Z</CreDtTm>
                </GrpHdr>
                <Stmt>
                    <Id>STATEMENT-2024-01</Id>
                    <Acct>
                        <Id>
                            <IBAN>DE89370400440532013000</IBAN>
                        </Id>
                        <Ccy>EUR</Ccy>
                    </Acct>
                    <Bal>
                        <Tp>
                            <CdOrPrtry>
                                <Cd>OPBD</Cd>
                            </CdOrPrtry>
                        </Tp>
                        <Amt Ccy="EUR">50000.00</Amt>
                        <Dt>
                            <Dt>2024-01-15</Dt>
                        </Dt>
                    </Bal>
                    <Ntry>
                        <Amt Ccy="EUR">9500.00</Amt>
                        <CdtDbtInd>CRDT</CdtDbtInd>
                        <Sts>BOOK</Sts>
                        <BookgDt>
                            <Dt>2024-01-15</Dt>
                        </BookgDt>
                        <ValDt>
                            <Dt>2024-01-15</Dt>
                        </ValDt>
                        <NtryRef>REF001</NtryRef>
                    </Ntry>
                </Stmt>
            </BkToCstmrStmt>
        </Document>
        """
        result = parse_camt053.invoke({"xml_content": xml_content})

        assert result["parsed_successfully"] is True
        assert result["message_type"] == "camt.053"
        assert result["statement_id"] == "STATEMENT-2024-01"
        assert result["account"]["iban"] == "DE89370400440532013000"
        assert result["entry_count"] == 1
        assert len(result["entries"]) == 1
        assert result["entries"][0]["amount"] == "9500.00"


class TestDetectStructuringPattern:
    """Tests for structuring/smurfing pattern detection."""

    def test_detect_structuring_high_risk(self):
        """Test detection of high-risk structuring pattern."""
        import json

        entries = [
            {"amount": "9500", "booking_date": "2024-01-15", "reference": "TXN001"},
            {"amount": "9800", "booking_date": "2024-01-15", "reference": "TXN002"},
            {"amount": "9200", "booking_date": "2024-01-16", "reference": "TXN003"},
            {"amount": "9700", "booking_date": "2024-01-16", "reference": "TXN004"},
            {"amount": "9900", "booking_date": "2024-01-17", "reference": "TXN005"},
        ]
        result = detect_structuring_pattern.invoke(
            {"entries_json": json.dumps(entries), "threshold": 10000}
        )

        assert result["structuring_detected"] is True
        assert result["risk_level"] == "high"
        assert result["near_threshold_transactions"] == 5

    def test_detect_structuring_medium_risk(self):
        """Test detection of medium-risk structuring pattern."""
        import json

        entries = [
            {"amount": "9500", "booking_date": "2024-01-15", "reference": "TXN001"},
            {"amount": "9800", "booking_date": "2024-01-15", "reference": "TXN002"},
            {"amount": "9200", "booking_date": "2024-01-16", "reference": "TXN003"},
        ]
        result = detect_structuring_pattern.invoke(
            {"entries_json": json.dumps(entries), "threshold": 10000}
        )

        assert result["structuring_detected"] is True
        assert result["risk_level"] == "medium"
        assert result["near_threshold_transactions"] == 3

    def test_no_structuring_low_risk(self):
        """Test no structuring detected for normal transactions."""
        import json

        entries = [
            {"amount": "500", "booking_date": "2024-01-15", "reference": "TXN001"},
            {"amount": "15000", "booking_date": "2024-01-15", "reference": "TXN002"},
            {"amount": "2500", "booking_date": "2024-01-16", "reference": "TXN003"},
        ]
        result = detect_structuring_pattern.invoke(
            {"entries_json": json.dumps(entries), "threshold": 10000}
        )

        assert result["structuring_detected"] is False
        assert result["risk_level"] == "low"
        assert result["near_threshold_transactions"] == 0

    def test_structuring_with_custom_threshold(self):
        """Test structuring detection with custom threshold."""
        import json

        entries = [
            {"amount": "4500", "booking_date": "2024-01-15", "reference": "TXN001"},
            {"amount": "4800", "booking_date": "2024-01-15", "reference": "TXN002"},
            {"amount": "4200", "booking_date": "2024-01-16", "reference": "TXN003"},
        ]
        result = detect_structuring_pattern.invoke(
            {"entries_json": json.dumps(entries), "threshold": 5000}
        )

        assert result["structuring_detected"] is True
        assert result["threshold"] == 5000

    def test_structuring_with_empty_entries(self):
        """Test structuring detection with no entries."""
        result = detect_structuring_pattern.invoke(
            {"entries_json": "[]", "threshold": 10000}
        )

        assert result["structuring_detected"] is False
        assert result["near_threshold_transactions"] == 0
        assert result["suspicious_entries"] == []

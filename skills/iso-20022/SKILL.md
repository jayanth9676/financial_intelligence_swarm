# ISO 20022 Parsing Skill

## Purpose
Parse and validate ISO 20022 financial messages (pacs.008, pain.001, camt.053) to extract transaction details for investigation.

## When to Use
- Ingesting new payment messages for investigation
- Extracting debtor/creditor information
- Detecting structuring patterns across multiple transactions
- Validating message format and completeness

## Available Tools

### 1. `parse_pacs008`
Parse FI-to-FI Customer Credit Transfer (pacs.008) messages.

```python
from backend.tools.tools_iso import parse_pacs008

result = parse_pacs008.invoke({
    "xml_content": pacs008_xml_string
})

# Returns:
# {
#     "parsed_successfully": True,
#     "message_type": "pacs.008",
#     "uetr": "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e",
#     "end_to_end_id": "E2E-001",
#     "debtor": {
#         "name": "Shell Company Alpha",
#         "account_iban": "DE89370400440532013000",
#         "agent_bic": "DEUTDEFFXXX"
#     },
#     "creditor": {
#         "name": "Offshore Holdings LLC",
#         "account_iban": "CY17002001280000001200527600",
#         "agent_bic": "BCYPCY2NXXX"
#     },
#     "amount": {"value": "245000.00", "currency": "EUR"},
#     "settlement_date": "2026-02-03",
#     "purpose_code": "CORT",
#     "remittance_info": {"unstructured": "Consulting services Q1 2026"}
# }
```

### 2. `parse_pain001`
Parse Customer Credit Transfer Initiation (pain.001) messages.

```python
from backend.tools.tools_iso import parse_pain001

result = parse_pain001.invoke({
    "xml_content": pain001_xml_string
})

# Returns:
# {
#     "parsed_successfully": True,
#     "message_type": "pain.001",
#     "message_id": "PAYMENT001",
#     "debtor": {"name": "Acme Corporation", ...},
#     "creditor": {"name": "Supplier Ltd", ...},
#     "end_to_end_id": "INV-2024-001",
#     "requested_execution_date": "2024-01-16"
# }
```

### 3. `parse_camt053`
Parse Bank-to-Customer Statement (camt.053) messages.

```python
from backend.tools.tools_iso import parse_camt053

result = parse_camt053.invoke({
    "xml_content": camt053_xml_string
})

# Returns:
# {
#     "parsed_successfully": True,
#     "message_type": "camt.053",
#     "statement_id": "STATEMENT-2024-01",
#     "account": {"iban": "DE89370400440532013000", "currency": "EUR"},
#     "entry_count": 5,
#     "entries": [
#         {"amount": "9500.00", "credit_debit": "CRDT", "booking_date": "2024-01-15", ...}
#     ]
# }
```

### 4. `detect_structuring_pattern`
Analyze transaction entries for structuring/smurfing patterns.

```python
from backend.tools.tools_iso import detect_structuring_pattern

result = detect_structuring_pattern.invoke({
    "entries": [
        {"amount": "9500", "booking_date": "2024-01-15"},
        {"amount": "9800", "booking_date": "2024-01-15"},
        {"amount": "9200", "booking_date": "2024-01-16"}
    ],
    "threshold": 10000  # CTR threshold
})

# Returns:
# {
#     "structuring_detected": True,
#     "risk_level": "high",
#     "near_threshold_transactions": 3,
#     "suspicious_entries": [...]
# }
```

## Message Types

### pacs.008 - FI to FI Customer Credit Transfer
The primary message for cross-border payments.

```xml
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.10">
  <FIToFICstmrCdtTrf>
    <GrpHdr>...</GrpHdr>
    <CdtTrfTxInf>
      <PmtId><UETR>...</UETR></PmtId>
      <Dbtr>...</Dbtr>
      <Cdtr>...</Cdtr>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>
```

### pain.001 - Customer Credit Transfer Initiation
Payment initiation from corporate to bank.

### camt.053 - Bank to Customer Statement
Account statement for reconciliation and pattern analysis.

## Key Fields Extracted

| Field | Location | Risk Relevance |
|-------|----------|----------------|
| UETR | PmtId/UETR | Unique transaction identifier |
| Debtor Name | Dbtr/Nm | Entity investigation |
| Creditor Name | Cdtr/Nm | Entity investigation |
| Amount | IntrBkSttlmAmt | Structuring detection |
| Purpose Code | Purp/Cd | Transaction categorization |
| Remittance Info | RmtInf/Ustrd | Free-text context |
| Debtor IBAN | DbtrAcct/Id/IBAN | Account tracing |
| Creditor IBAN | CdtrAcct/Id/IBAN | Jurisdiction flags |

## Jurisdiction Risk Flags

Certain IBAN prefixes indicate higher-risk jurisdictions:

| Prefix | Country | Risk Level |
|--------|---------|------------|
| CY | Cyprus | Medium-High |
| MT | Malta | Medium |
| LV | Latvia | Medium |
| VG | British Virgin Islands | High |
| KY | Cayman Islands | High |

## Structuring Detection Algorithm

```python
def is_structuring(entries, threshold=10000, tolerance=0.05):
    """
    Detect if transactions are structured to avoid CTR threshold.
    
    Flags transactions that are:
    - Within 5% of threshold (e.g., $9,500 - $10,000)
    - Multiple same-day transactions
    - Cumulative total exceeds threshold
    """
    near_threshold = [
        e for e in entries 
        if threshold * (1 - tolerance) <= float(e["amount"]) < threshold
    ]
    
    if len(near_threshold) >= 3:
        return {"risk_level": "high", "count": len(near_threshold)}
    elif len(near_threshold) >= 2:
        return {"risk_level": "medium", "count": len(near_threshold)}
    else:
        return {"risk_level": "low", "count": len(near_threshold)}
```

## Integration with Ingestion API

```python
# POST /ingest endpoint
from backend.main import app

@app.post("/ingest")
async def ingest_message(request: IngestRequest):
    if request.message_type == "pacs.008":
        parsed = parse_pacs008.invoke({"xml_content": request.xml_content})
    elif request.message_type == "pain.001":
        parsed = parse_pain001.invoke({"xml_content": request.xml_content})
    
    if parsed["parsed_successfully"]:
        # Hydrate Neo4j graph
        # Trigger investigation
        pass
```

## Error Handling

XML parsing errors return structured error dict:

```python
result = parse_pacs008.invoke({"xml_content": "<invalid>xml"})

if not result["parsed_successfully"]:
    print(f"Parse error: {result['error']}")
    # Handle gracefully - don't crash the investigation
```

## Empty Element Handling

ISO 20022 messages may have empty elements. The parser handles `None` from `xmltodict`:

```python
# <Dbtr><Nm></Nm></Dbtr> returns {"Nm": None}
# Parser converts to: {"name": ""}
```

## Batch Processing

For high-volume ingestion, use batch parsing:

```python
from backend.loaders.load_graph import parse_batch_pacs008

documents = {
    "batch_id": "FIS-BATCH-001",
    "documents": [
        {"xml_content": xml1},
        {"xml_content": xml2}
    ]
}

results = parse_batch_pacs008(documents)
```

## Prerequisites

- Python `xmltodict` package for XML parsing
- Valid ISO 20022 XML conforming to XSD schema
- UTF-8 encoding for XML content

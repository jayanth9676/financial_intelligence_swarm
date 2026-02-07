"""Generate ISO 20022 XML messages for testing."""

import os
import random
from datetime import datetime, timedelta
import uuid

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data_raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Target transaction for demo
TARGET_UETR = "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"
TARGET_DEBTOR = "Precision Parts GmbH"
TARGET_CREDITOR = "Al-Ghazali Trading LLC"

# Legitimate companies for noise
LEGITIMATE_COMPANIES = [
    ("AWS Services Inc", "Amazon Web Services"),
    ("Uber Technologies", "Uber BV"),
    ("Microsoft Corp", "Azure Services"),
    ("Acme Payroll Ltd", "Employee Wages"),
    ("City Utilities", "Water & Electric"),
    ("Office Supplies Co", "Staples Inc"),
    ("Cloud Computing Ltd", "Google Cloud"),
]

# Suspicious companies (for false positive testing)
EDGE_CASE_COMPANIES = [
    ("Osama Construction Ltd", "Building Materials"),  # Safe but similar name
    ("Iran Trade Co", "Iranian Saffron Export"),  # Legitimate trade
]


def generate_pacs008(
    uetr: str,
    debtor_name: str,
    creditor_name: str,
    amount: float,
    currency: str = "EUR",
    purpose: str = "SUPP",
    remittance_info: str = "",
) -> str:
    """Generate a pacs.008 XML message."""
    creation_time = datetime.now().isoformat()
    settlement_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.10">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>MSG-{uuid.uuid4().hex[:12].upper()}</MsgId>
      <CreDtTm>{creation_time}</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <SttlmInf>
        <SttlmMtd>CLRG</SttlmMtd>
      </SttlmInf>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <EndToEndId>E2E-{uuid.uuid4().hex[:8].upper()}</EndToEndId>
        <UETR>{uetr}</UETR>
      </PmtId>
      <IntrBkSttlmAmt Ccy="{currency}">{amount:.2f}</IntrBkSttlmAmt>
      <IntrBkSttlmDt>{settlement_date}</IntrBkSttlmDt>
      <Dbtr>
        <Nm>{debtor_name}</Nm>
        <PstlAdr>
          <StrtNm>Industrial Street</StrtNm>
          <BldgNb>42</BldgNb>
          <PstCd>80331</PstCd>
          <TwnNm>Munich</TwnNm>
          <Ctry>DE</Ctry>
        </PstlAdr>
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
      <CdtrAgt>
        <FinInstnId>
          <BICFI>ARABAEADXXX</BICFI>
        </FinInstnId>
      </CdtrAgt>
      <Cdtr>
        <Nm>{creditor_name}</Nm>
        <PstlAdr>
          <TwnNm>Dubai</TwnNm>
          <Ctry>AE</Ctry>
        </PstlAdr>
      </Cdtr>
      <CdtrAcct>
        <Id>
          <IBAN>AE070331234567890123456</IBAN>
        </Id>
      </CdtrAcct>
      <Purp>
        <Cd>{purpose}</Cd>
      </Purp>
      <RmtInf>
        <Ustrd>{remittance_info or f"Payment from {debtor_name} to {creditor_name}"}</Ustrd>
      </RmtInf>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>'''


def generate_dataset():
    """Generate the full demo dataset."""
    transactions = []

    # 1. Generate legitimate noise transactions (2000+)
    print("Generating legitimate transactions...")
    for i in range(2000):
        debtor, creditor = random.choice(LEGITIMATE_COMPANIES)
        amount = random.uniform(100, 50000)
        uetr = str(uuid.uuid4())

        transactions.append(
            {
                "uetr": uetr,
                "xml": generate_pacs008(uetr, debtor, creditor, amount),
                "type": "legitimate",
            }
        )

    # 2. Generate edge case transactions (false positive tests)
    print("Generating edge case transactions...")
    for debtor, purpose in EDGE_CASE_COMPANIES:
        uetr = str(uuid.uuid4())
        amount = random.uniform(5000, 20000)

        transactions.append(
            {
                "uetr": uetr,
                "xml": generate_pacs008(
                    uetr, debtor, purpose, amount, remittance_info=purpose
                ),
                "type": "edge_case",
            }
        )

    # 3. Generate structuring pattern (smurfing)
    print("Generating structuring pattern...")
    for i in range(50):
        uetr = str(uuid.uuid4())
        amount = random.uniform(8000, 9900)  # Just below 10k threshold

        transactions.append(
            {
                "uetr": uetr,
                "xml": generate_pacs008(
                    uetr,
                    TARGET_DEBTOR,
                    "Consulting Services Ltd",
                    amount,
                    purpose="CONS",
                    remittance_info=f"Consulting fee invoice #{i + 1}",
                ),
                "type": "structuring",
            }
        )

    # 4. Generate the TARGET transaction (the needle in the haystack)
    print(f"Generating target transaction: {TARGET_UETR}")
    target_xml = generate_pacs008(
        TARGET_UETR,
        TARGET_DEBTOR,
        TARGET_CREDITOR,
        75000.00,
        purpose="SUPP",
        remittance_info="Industrial equipment - Q4 order",
    )
    transactions.append({"uetr": TARGET_UETR, "xml": target_xml, "type": "target"})

    # Shuffle to hide the target
    random.shuffle(transactions)

    # Write individual XML files
    print(f"Writing {len(transactions)} XML files...")
    for tx in transactions:
        filename = f"pacs.008.{tx['uetr']}.xml"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w") as f:
            f.write(tx["xml"])

    # Write combined high-volume file
    combined_path = os.path.join(OUTPUT_DIR, "pacs.008.high_volume.xml")
    with open(combined_path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write("<BatchDocument>\n")
        for tx in transactions:
            # Strip XML declaration from individual messages
            xml_content = tx["xml"].replace(
                '<?xml version="1.0" encoding="UTF-8"?>\n', ""
            )
            f.write(xml_content)
            f.write("\n")
        f.write("</BatchDocument>")

    # Write manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    import json

    with open(manifest_path, "w") as f:
        json.dump(
            {
                "total_transactions": len(transactions),
                "target_uetr": TARGET_UETR,
                "types": {
                    "legitimate": sum(
                        1 for t in transactions if t["type"] == "legitimate"
                    ),
                    "edge_case": sum(
                        1 for t in transactions if t["type"] == "edge_case"
                    ),
                    "structuring": sum(
                        1 for t in transactions if t["type"] == "structuring"
                    ),
                    "target": 1,
                },
                "generated_at": datetime.now().isoformat(),
            },
            f,
            indent=2,
        )

    print(f"Dataset generated in {OUTPUT_DIR}")
    print(f"Target UETR: {TARGET_UETR}")
    return transactions


if __name__ == "__main__":
    generate_dataset()

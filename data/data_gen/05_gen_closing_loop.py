import xml.etree.ElementTree as ET


def gen_loop():
    print("Generating Closing Loop Files...")
    # 1. Initiation (pain.001)
    ET.register_namespace("", "urn:iso:std:iso:20022:tech:xsd:pain.001.001.09")
    r1 = ET.Element("{urn:iso:std:iso:20022:tech:xsd:pain.001.001.09}Document")
    init = ET.SubElement(ET.SubElement(r1, "CstmrCdtTrfInitn"), "PmtInf")
    ET.SubElement(
        ET.SubElement(ET.SubElement(init, "CdtTrfTxInf"), "PmtId"), "EndToEndId"
    ).text = "E2E-REF-772910"
    ET.ElementTree(r1).write(
        "pain.001.001.09_initiation.xml", encoding="UTF-8", xml_declaration=True
    )

    # 2. Status (pacs.002)
    ET.register_namespace("", "urn:iso:std:iso:20022:tech:xsd:pacs.002.001.12")
    r2 = ET.Element("{urn:iso:std:iso:20022:tech:xsd:pacs.002.001.12}Document")
    sts = ET.SubElement(ET.SubElement(r2, "FIToFIPmtStsRpt"), "TxInfAndSts")
    ET.SubElement(sts, "OrgnlUETR").text = "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"
    ET.SubElement(sts, "TxSts").text = "ACCP"
    ET.ElementTree(r2).write(
        "pacs.002.001.12_status.xml", encoding="UTF-8", xml_declaration=True
    )

    # 3. Notification (camt.054)
    ET.register_namespace("", "urn:iso:std:iso:20022:tech:xsd:camt.054.001.08")
    r3 = ET.Element("{urn:iso:std:iso:20022:tech:xsd:camt.054.001.08}Document")
    ntf = ET.SubElement(
        ET.SubElement(
            ET.SubElement(ET.SubElement(r3, "BkToCstmrDbtCdtNtfctn"), "Ntfctn"), "Ntry"
        ),
        "NtryDtls",
    )
    ET.SubElement(
        ET.SubElement(ET.SubElement(ntf, "TxDtls"), "Refs"), "UETR"
    ).text = "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"
    ET.ElementTree(r3).write(
        "camt.054.001.08_notification.xml", encoding="UTF-8", xml_declaration=True
    )
    print("✅ Closing Loop Files Generated.")


if __name__ == "__main__":
    gen_loop()

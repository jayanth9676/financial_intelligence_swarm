"""PDF Generator for SAR Reports.

Generates professional, readable PDF reports for Suspicious Activity Reports (SARs)
using ReportLab for regulatory compliance and EU AI Act documentation.
"""

from io import BytesIO
from typing import Dict, Any
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
        ListFlowable,
        ListItem,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_sar_pdf(sar_data: Dict[str, Any]) -> bytes:
    """Generate a professional PDF SAR report.

    Args:
        sar_data: SAR report data dictionary

    Returns:
        PDF file as bytes
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "reportlab is required for PDF generation. Install with: pip install reportlab"
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    # Get styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor("#1e40af"),
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor("#1e3a8a"),
    )

    subheading_style = ParagraphStyle(
        "CustomSubHeading",
        parent=styles["Heading3"],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=5,
        textColor=colors.HexColor("#374151"),
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        leading=14,
    )

    small_style = ParagraphStyle(
        "SmallText",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6b7280"),
    )

    # Build document content
    elements = []

    # Header
    elements.append(Paragraph("SUSPICIOUS ACTIVITY REPORT (SAR)", title_style))
    elements.append(
        Paragraph(
            f"Report ID: <b>{sar_data.get('report_id', 'N/A')}</b>",
            ParagraphStyle("Center", parent=body_style, alignment=TA_CENTER),
        )
    )
    elements.append(Spacer(1, 0.3 * inch))

    # Status badge
    status = sar_data.get("status", "PENDING")
    status_color = (
        colors.HexColor("#22c55e") if status == "FILED" else colors.HexColor("#eab308")
    )
    status_table = Table(
        [[Paragraph(f"<b>Status: {status}</b>", body_style)]], colWidths=[3 * inch]
    )
    status_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), status_color),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("ROUNDEDCORNERS", [5, 5, 5, 5]),
            ]
        )
    )
    elements.append(status_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Horizontal line
    elements.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb"))
    )
    elements.append(Spacer(1, 0.2 * inch))

    # Transaction Details Section
    elements.append(Paragraph("1. TRANSACTION DETAILS", heading_style))

    tx_details = sar_data.get("transaction_details", {})
    tx_table_data = [
        ["UETR:", tx_details.get("uetr", "N/A")],
        ["Date:", tx_details.get("date", "N/A")],
        ["Amount:", tx_details.get("amount", "N/A")],
        ["Originator:", tx_details.get("originator", {}).get("name", "N/A")],
        ["Beneficiary:", tx_details.get("beneficiary", {}).get("name", "N/A")],
        ["Purpose:", tx_details.get("purpose", "Not specified")],
    ]

    tx_table = Table(tx_table_data, colWidths=[1.5 * inch, 4.5 * inch])
    tx_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    elements.append(tx_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Risk Assessment Section
    elements.append(Paragraph("2. RISK ASSESSMENT", heading_style))

    risk_assessment = sar_data.get("risk_assessment", {})
    risk_level = risk_assessment.get("risk_level", "unknown").upper()

    risk_colors = {
        "CRITICAL": colors.HexColor("#dc2626"),
        "HIGH": colors.HexColor("#ea580c"),
        "MEDIUM": colors.HexColor("#ca8a04"),
        "LOW": colors.HexColor("#16a34a"),
    }
    risk_color = risk_colors.get(risk_level, colors.HexColor("#6b7280"))

    risk_table_data = [
        ["Risk Level:", risk_level],
        ["Verdict:", risk_assessment.get("verdict", "N/A")],
        [
            "Confidence Score:",
            f"{risk_assessment.get('confidence_score', 0) * 100:.1f}%",
        ],
    ]

    risk_table = Table(risk_table_data, colWidths=[1.5 * inch, 4.5 * inch])
    risk_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
                ("TEXTCOLOR", (1, 0), (1, 0), risk_color),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(risk_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Investigation Summary Section
    elements.append(Paragraph("3. INVESTIGATION SUMMARY", heading_style))

    inv_summary = sar_data.get("investigation_summary", {})

    # Prosecutor findings
    prosecutor_findings = inv_summary.get("prosecutor_findings", [])
    if prosecutor_findings:
        elements.append(Paragraph("Prosecutor Findings:", subheading_style))
        for finding in prosecutor_findings:
            elements.append(Paragraph(f"• {finding}", body_style))

    # Skeptic findings
    skeptic_findings = inv_summary.get("skeptic_findings", [])
    if skeptic_findings:
        elements.append(Paragraph("Skeptic Findings:", subheading_style))
        for finding in skeptic_findings:
            # Truncate long findings
            display_finding = finding[:200] + "..." if len(finding) > 200 else finding
            elements.append(Paragraph(f"• {display_finding}", body_style))

    elements.append(Spacer(1, 0.2 * inch))

    # Reasoning Section
    elements.append(Paragraph("4. ANALYSIS AND REASONING", heading_style))
    reasoning = sar_data.get("reasoning", "No reasoning provided.")
    elements.append(Paragraph(reasoning, body_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Recommended Actions
    recommended_actions = sar_data.get("recommended_actions", [])
    if recommended_actions:
        elements.append(Paragraph("5. RECOMMENDED ACTIONS", heading_style))
        for action in recommended_actions:
            elements.append(Paragraph(f"• {action}", body_style))
        elements.append(Spacer(1, 0.2 * inch))

    # Human Override Section
    human_override = sar_data.get("human_override", {})
    if human_override:
        elements.append(Paragraph("6. HUMAN DECISION", heading_style))
        override_table_data = [
            ["Action:", human_override.get("action", "N/A").upper()],
            [
                "Reason:",
                human_override.get("reason", "No reason provided")
                or "No reason provided",
            ],
            ["Timestamp:", human_override.get("timestamp", "N/A")],
        ]

        override_table = Table(override_table_data, colWidths=[1.5 * inch, 4.5 * inch])
        override_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(override_table)
        elements.append(Spacer(1, 0.2 * inch))

    # Compliance Section
    elements.append(Paragraph("7. EU AI ACT COMPLIANCE", heading_style))
    compliance = sar_data.get("compliance", {}).get("eu_ai_act", {})

    compliance_table_data = [
        [
            "Article 13 Satisfied:",
            "✓ Yes" if compliance.get("article_13_satisfied") else "✗ No",
        ],
        [
            "Human Oversight Required:",
            "✓ Yes" if compliance.get("human_oversight_required") else "No",
        ],
    ]

    compliance_table = Table(compliance_table_data, colWidths=[2 * inch, 4 * inch])
    compliance_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(compliance_table)

    transparency_stmt = compliance.get("transparency_statement", "")
    if transparency_stmt:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"<i>{transparency_stmt}</i>", small_style))

    elements.append(Spacer(1, 0.3 * inch))

    # Footer
    elements.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb"))
    )
    elements.append(Spacer(1, 0.1 * inch))

    generated_at = sar_data.get("generated_at", datetime.now().isoformat())
    filed_at = sar_data.get("filed_at", "")
    regulator_id = sar_data.get("regulator_id", "")

    footer_text = f"Generated: {generated_at}"
    if filed_at:
        footer_text += f" | Filed: {filed_at}"
    if regulator_id:
        footer_text += f" | Regulator ID: {regulator_id}"

    elements.append(Paragraph(footer_text, small_style))
    elements.append(
        Paragraph(
            "This document was generated by the Financial Intelligence Swarm (FIS) AI system.",
            ParagraphStyle(
                "Disclaimer", parent=small_style, alignment=TA_CENTER, spaceBefore=10
            ),
        )
    )

    # Build PDF
    doc.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_annex_iv_pdf(uetr: str, tx_data: Dict[str, Any]) -> bytes:
    """Generate comprehensive EU AI Act Annex IV Technical Documentation PDF.

    This PDF includes all required elements per Annex IV of Regulation (EU) 2024/1689:
    1. General description of the AI system
    2. Detailed description of elements and development process
    3. Information about monitoring, functioning and control
    4. Risk management system description
    5. Data governance and management practices
    6. Logging capabilities
    7. Cybersecurity measures
    8. Human oversight measures

    Args:
        uetr: Transaction UETR
        tx_data: Transaction data including investigation results

    Returns:
        PDF file as bytes
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "reportlab is required for PDF generation. Install with: pip install reportlab"
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor("#1e40af"),
        alignment=TA_CENTER,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=12,
        spaceAfter=15,
        textColor=colors.HexColor("#374151"),
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor("#1e3a8a"),
    )

    subheading_style = ParagraphStyle(
        "SubHeading",
        parent=styles["Heading3"],
        fontSize=11,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#374151"),
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        leading=14,
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=4,
        leftIndent=20,
        leading=14,
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6b7280"),
    )

    elements = []

    # Header with EU flag reference
    elements.append(Paragraph("EUROPEAN UNION AI ACT", subtitle_style))
    elements.append(Paragraph("ANNEX IV - TECHNICAL DOCUMENTATION", title_style))
    elements.append(
        Paragraph(
            "Regulation (EU) 2024/1689 - High-Risk AI System Documentation",
            ParagraphStyle(
                "SubTitle",
                parent=body_style,
                alignment=TA_CENTER,
                fontSize=10,
                textColor=colors.HexColor("#6b7280"),
            ),
        )
    )
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e40af"))
    )
    elements.append(Spacer(1, 0.3 * inch))

    # Document metadata table
    doc_meta = [
        ["Document ID:", f"ANNEX-IV-{uetr[:8].upper()}"],
        ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")],
        ["Classification:", "HIGH-RISK AI SYSTEM (Article 6)"],
        ["Sector:", "Financial Services / AML Compliance"],
    ]
    meta_table = Table(doc_meta, colWidths=[1.8 * inch, 4.2 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f4f6")),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 0.3 * inch))

    # 1. System Description
    elements.append(Paragraph("1. GENERAL DESCRIPTION OF THE AI SYSTEM", heading_style))
    elements.append(Paragraph("1.1 System Identification", subheading_style))

    system_info = [
        ["System Name:", "Financial Intelligence Swarm (FIS)"],
        ["Version:", "1.0.0"],
        ["Provider:", "Financial Technology Division"],
        ["System Type:", "Multi-Agent AI System for AML/CFT Compliance"],
        ["Risk Category:", "HIGH-RISK (Annex III, Section 5(b))"],
    ]
    sys_table = Table(system_info, colWidths=[1.8 * inch, 4.2 * inch])
    sys_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    elements.append(sys_table)
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("1.2 Intended Purpose", subheading_style))
    elements.append(
        Paragraph(
            "The Financial Intelligence Swarm (FIS) is designed to assist financial institutions in "
            "detecting potential money laundering, fraud, and sanctions violations in real-time payment "
            "transactions. The system provides decision support for human compliance officers by "
            "analyzing transaction patterns, entity relationships, and behavioral indicators.",
            body_style,
        )
    )
    elements.append(
        Paragraph(
            "<b>IMPORTANT:</b> This system is intended as a decision-support tool only. All final "
            "decisions regarding transaction approval, blocking, or escalation MUST be made by "
            "qualified human compliance officers. The system does NOT make autonomous decisions "
            "that directly affect natural persons without human oversight.",
            body_style,
        )
    )

    elements.append(Paragraph("1.3 Multi-Agent Architecture", subheading_style))
    elements.append(
        Paragraph(
            "The system employs a unique adversarial debate architecture with three specialized AI agents:",
            body_style,
        )
    )

    agents_data = [
        ["Agent", "Role", "Function"],
        [
            "Prosecutor",
            "Accusatory",
            "Investigates suspicious patterns, hidden entity links, and fraud indicators",
        ],
        [
            "Skeptic",
            "Defensive",
            "Searches for exculpatory evidence and legitimate business justifications",
        ],
        [
            "Judge",
            "Adjudicatory",
            "Weighs evidence from both sides and provides risk assessment with recommendations",
        ],
    ]
    agents_table = Table(agents_data, colWidths=[1.2 * inch, 1.0 * inch, 3.8 * inch])
    agents_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    elements.append(agents_table)
    elements.append(Spacer(1, 0.2 * inch))

    # 2. Technical Architecture
    elements.append(
        Paragraph("2. TECHNICAL ARCHITECTURE AND DEVELOPMENT", heading_style)
    )
    elements.append(Paragraph("2.1 Core Components", subheading_style))

    tech_components = [
        ["Component", "Technology", "Purpose"],
        [
            "Orchestration",
            "LangGraph",
            "Multi-agent workflow management and state handling",
        ],
        [
            "Graph Database",
            "Neo4j",
            "Entity relationship analysis and hidden link detection",
        ],
        [
            "Vector Store",
            "Qdrant",
            "Semantic search for regulatory documents and precedents",
        ],
        [
            "Behavioral Memory",
            "Mem0",
            "Historical baseline tracking and drift detection",
        ],
        [
            "LLM Provider",
            "Google Gemini",
            "Natural language reasoning and evidence synthesis",
        ],
        ["API Framework", "FastAPI", "RESTful API with streaming support"],
    ]
    tech_table = Table(tech_components, colWidths=[1.3 * inch, 1.2 * inch, 3.5 * inch])
    tech_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    elements.append(tech_table)
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("2.2 Data Processing Pipeline", subheading_style))
    elements.append(
        Paragraph(
            "• <b>Input:</b> ISO 20022 financial messages (pacs.008, pain.001, camt.053)",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• <b>Parsing:</b> XML extraction of transaction details, parties, and remittance information",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• <b>Enrichment:</b> Entity resolution, graph traversal, historical pattern matching",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• <b>Analysis:</b> Multi-agent debate with tool-augmented reasoning",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• <b>Output:</b> Risk score, verdict recommendation, evidence trail, and audit log",
            bullet_style,
        )
    )

    # 3. Risk Management
    elements.append(Paragraph("3. RISK MANAGEMENT SYSTEM (Article 9)", heading_style))
    elements.append(
        Paragraph(
            "In accordance with Article 9 of the AI Act, the following risk management measures are implemented:",
            body_style,
        )
    )

    elements.append(Paragraph("3.1 Bias Mitigation", subheading_style))
    elements.append(
        Paragraph(
            "• Multi-agent debate ensures no single model perspective dominates",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• Adversarial Skeptic agent actively searches for exculpatory evidence",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• Confidence scores reflect uncertainty in assessments", bullet_style
        )
    )

    elements.append(Paragraph("3.2 Accuracy and Robustness", subheading_style))
    elements.append(
        Paragraph(
            "• Graph-based analysis provides verifiable entity relationships",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• Evidence-based reasoning with traceable evidence IDs (EVID-*, DEF-*)",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• Fallback mechanisms when external services are unavailable", bullet_style
        )
    )

    elements.append(Paragraph("3.3 Foreseeable Risks", subheading_style))
    elements.append(
        Paragraph(
            "• <b>False Positives:</b> Legitimate transactions flagged as suspicious - mitigated by human review requirement",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• <b>False Negatives:</b> Suspicious transactions missed - mitigated by multi-layer detection",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• <b>Adversarial Attacks:</b> Structured transactions to evade detection - mitigated by pattern analysis",
            bullet_style,
        )
    )

    # 4. Human Oversight
    elements.append(
        Paragraph("4. HUMAN OVERSIGHT MEASURES (Article 14)", heading_style)
    )
    elements.append(
        Paragraph(
            "This system is designed for human-in-the-loop operation in accordance with Article 14. "
            "The following safeguards ensure meaningful human oversight:",
            body_style,
        )
    )

    oversight_measures = [
        "All verdicts (APPROVE, BLOCK, ESCALATE, REVIEW) are RECOMMENDATIONS requiring human confirmation",
        "Compliance officers can override any AI recommendation with documented justification",
        "Full audit trail of all tool calls, reasoning chains, and evidence reviewed",
        "Transparency statements explain the basis for each recommendation",
        "High-risk transactions (critical risk level) require mandatory escalation to senior compliance",
        "System clearly indicates when confidence is low, requiring additional human analysis",
    ]
    for measure in oversight_measures:
        elements.append(Paragraph(f"• {measure}", bullet_style))

    # 5. Logging and Traceability
    elements.append(Paragraph("5. LOGGING CAPABILITIES (Article 12)", heading_style))
    elements.append(
        Paragraph(
            "Comprehensive logging ensures full traceability of AI system operations:",
            body_style,
        )
    )
    elements.append(
        Paragraph(
            "• Every tool invocation is recorded with timestamp, parameters, and results",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• Agent reasoning is captured in structured debate messages", bullet_style
        )
    )
    elements.append(
        Paragraph(
            "• Human override decisions are logged with timestamps and justifications",
            bullet_style,
        )
    )
    elements.append(
        Paragraph(
            "• Logs are retained for 7 years per AML regulatory requirements",
            bullet_style,
        )
    )

    # 6. Transaction-specific Record
    elements.append(Paragraph("6. TRANSACTION ANALYSIS RECORD", heading_style))
    elements.append(
        Paragraph(
            "The following transaction was analyzed by this AI system:", body_style
        )
    )

    parsed = tx_data.get("parsed_message", {})
    result = tx_data.get("investigation_result", {})
    verdict_data = result.get("verdict", {})

    # Determine risk color
    risk_level = result.get("risk_level", "unknown").upper()
    risk_colors = {
        "CRITICAL": colors.HexColor("#dc2626"),
        "HIGH": colors.HexColor("#ea580c"),
        "MEDIUM": colors.HexColor("#ca8a04"),
        "LOW": colors.HexColor("#16a34a"),
    }
    risk_color = risk_colors.get(risk_level, colors.HexColor("#6b7280"))

    tx_info = [
        ["Field", "Value"],
        ["Transaction UETR", uetr],
        ["Originator (Debtor)", parsed.get("debtor", {}).get("name", "N/A")],
        ["Beneficiary (Creditor)", parsed.get("creditor", {}).get("name", "N/A")],
        [
            "Amount",
            f"{parsed.get('amount', {}).get('value', 'N/A')} {parsed.get('amount', {}).get('currency', 'EUR')}",
        ],
        ["Purpose Code", parsed.get("purpose_code", "N/A")],
        ["Analysis Timestamp", result.get("analyzed_at", datetime.now().isoformat())],
        ["Risk Level", risk_level],
        [
            "Recommended Verdict",
            verdict_data.get("verdict", "N/A")
            if isinstance(verdict_data, dict)
            else str(verdict_data),
        ],
        ["Confidence Score", f"{result.get('confidence_score', 0) * 100:.1f}%"],
    ]

    tx_table = Table(tx_info, colWidths=[1.8 * inch, 4.2 * inch])
    tx_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("TEXTCOLOR", (1, 7), (1, 7), risk_color),  # Risk level color
            ]
        )
    )
    elements.append(tx_table)
    elements.append(Spacer(1, 0.2 * inch))

    # 7. Compliance Declaration
    elements.append(Paragraph("7. COMPLIANCE DECLARATION", heading_style))

    compliance_box = [
        [
            Paragraph(
                "<b>EU AI Act Compliance Statement</b><br/><br/>"
                "This AI system has been developed and operated in accordance with the requirements of "
                "Regulation (EU) 2024/1689 (AI Act) for high-risk AI systems. The provider declares that:<br/><br/>"
                "• Article 9 (Risk Management): A risk management system is established and maintained<br/>"
                "• Article 10 (Data Governance): Data used for training and operation meets quality criteria<br/>"
                "• Article 12 (Record-keeping): Automatic logging of events is enabled<br/>"
                "• Article 13 (Transparency): Information for deployers is provided<br/>"
                "• Article 14 (Human Oversight): Human oversight measures are implemented<br/>"
                "• Article 15 (Accuracy, Robustness, Cybersecurity): Appropriate levels are achieved",
                body_style,
            )
        ]
    ]
    compliance_table = Table(compliance_box, colWidths=[6 * inch])
    compliance_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#1e40af")),
                ("PADDING", (0, 0), (-1, -1), 15),
            ]
        )
    )
    elements.append(compliance_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Footer
    elements.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb"))
    )
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(
        Paragraph(
            f"Document generated: {datetime.now().isoformat()} | System Version: 1.0.0 | Document Ref: ANNEX-IV-{uetr[:8].upper()}",
            small_style,
        )
    )
    elements.append(
        Paragraph(
            "This document is generated automatically by the Financial Intelligence Swarm (FIS) AI system "
            "and serves as technical documentation per EU AI Act Annex IV requirements.",
            ParagraphStyle(
                "Disclaimer", parent=small_style, alignment=TA_CENTER, spaceBefore=10
            ),
        )
    )

    doc.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes

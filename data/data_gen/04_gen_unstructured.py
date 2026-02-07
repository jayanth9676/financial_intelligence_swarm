"""Generate unstructured annual report with payment grid for evidence extraction."""

import os
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data_raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET_ENTITY = "Precision Parts GmbH"


def generate_annual_report():
    """Generate annual report with embedded payment policy grid."""

    report = f"""# {TARGET_ENTITY} - Annual Report 2025

## Executive Summary

{TARGET_ENTITY} has completed another successful fiscal year, demonstrating resilience 
in challenging market conditions. Our manufacturing operations continue to be the 
backbone of our business, with strategic investments in automation and quality control.

## 1. Business Overview

Founded in 1987, {TARGET_ENTITY} is a leading manufacturer of precision-engineered 
components for the automotive and aerospace industries. Headquartered in Munich, Germany, 
we operate three production facilities across Bavaria.

### Key Statistics
- Employees: 847
- Annual Revenue: EUR 142.3 million
- Export Markets: 28 countries
- ISO Certifications: 9001, 14001, 45001

## 2. Operational Highlights

### Manufacturing Excellence
Our core manufacturing operations processed over 2.4 million components this year, 
maintaining a defect rate below 0.02%. Raw material procurement remains our largest 
expense category, with established relationships with certified suppliers.

### Supply Chain
Primary suppliers include:
- Steel Direct AG (raw materials)
- Industrial Metals GmbH (specialty alloys)
- Precision Tooling Corp (equipment maintenance)

## 3. Financial Governance

To support operational efficiency and our evolving business model, the Board of Directors 
has approved the following payment authorization framework:

### Authorized Payment Grid

| Category | Frequency | Amount Range | Approval Level |
|:---------|:----------|:-------------|:---------------|
| Raw Materials | Monthly | EUR 50,000 - 150,000 | CFO |
| Equipment Maintenance | Quarterly | EUR 20,000 - 80,000 | Operations Director |
| **Consultants** | **Weekly** | **EUR 800 - 1,200** | **Department Head** |
| Utilities | Monthly | EUR 8,000 - 15,000 | Automated |
| IT Services | Monthly | EUR 5,000 - 12,000 | IT Director |
| Travel & Expenses | As needed | EUR 500 - 5,000 | Manager |

### Policy Note on Consulting Payments

As part of our "Agile Workforce Initiative" announced in Q3, the Board has authorized 
a new framework for engaging external consultants. This allows for:

- Weekly payments to approved consulting firms
- Amounts between EUR 800 and EUR 1,200 per engagement
- Streamlined approval at Department Head level

This policy supports our digital transformation efforts and provides flexibility 
to engage specialized expertise as needed.

## 4. Risk Management

### Internal Controls
- Dual authorization required for payments exceeding EUR 10,000
- Quarterly audit of all vendor relationships
- Annual review of payment patterns by external auditors

### Compliance
All financial activities comply with:
- EU Anti-Money Laundering Directive (AMLD6)
- German Banking Act (KWG)
- ISO 37001 Anti-Bribery Management

## 5. Forward-Looking Statements

Looking ahead to 2026, we anticipate:
- Continued growth in core manufacturing (projected +8%)
- Expansion of consulting partnerships for digital initiatives
- Investment in sustainable manufacturing practices

## Appendix A: Board of Directors

- Dr. Hans Mueller, Chairman
- Maria Schmidt, CEO
- Thomas Weber, CFO
- Dr. Elena Fischer, COO

## Appendix B: Auditor Statement

This report has been prepared in accordance with German Commercial Code (HGB) 
and International Financial Reporting Standards (IFRS). Financial statements 
have been audited by Wirtschaftsprüfer AG.

---
*Report generated: {datetime.now().strftime("%Y-%m-%d")}*
*Document classification: Internal Use Only*
"""

    return report


def generate_payment_grid_csv():
    """Generate separate CSV of payment grid for structured extraction."""
    import csv

    grid = [
        {
            "category": "Raw Materials",
            "frequency": "Monthly",
            "amount_min": 50000,
            "amount_max": 150000,
            "approval": "CFO",
        },
        {
            "category": "Equipment Maintenance",
            "frequency": "Quarterly",
            "amount_min": 20000,
            "amount_max": 80000,
            "approval": "Operations Director",
        },
        {
            "category": "Consultants",
            "frequency": "Weekly",
            "amount_min": 800,
            "amount_max": 1200,
            "approval": "Department Head",
        },
        {
            "category": "Utilities",
            "frequency": "Monthly",
            "amount_min": 8000,
            "amount_max": 15000,
            "approval": "Automated",
        },
        {
            "category": "IT Services",
            "frequency": "Monthly",
            "amount_min": 5000,
            "amount_max": 12000,
            "approval": "IT Director",
        },
        {
            "category": "Travel & Expenses",
            "frequency": "As needed",
            "amount_min": 500,
            "amount_max": 5000,
            "approval": "Manager",
        },
    ]

    csv_path = os.path.join(OUTPUT_DIR, "payment_policy_grid.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=grid[0].keys())
        writer.writeheader()
        writer.writerows(grid)

    return csv_path, grid


def main():
    print(f"Generating annual report for {TARGET_ENTITY}...")

    # Generate markdown report
    report = generate_annual_report()
    report_path = os.path.join(OUTPUT_DIR, "precision_parts_annual_report_2025.md")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Written annual report to {report_path}")

    # Generate payment grid CSV
    csv_path, grid = generate_payment_grid_csv()
    print(f"Written payment grid to {csv_path}")

    # Summary
    print("\nGenerated files:")
    print(f"  - {report_path}")
    print(f"  - {csv_path}")
    print(f"\nPayment grid contains {len(grid)} categories")
    print(
        "Key evidence: Consultant payments (800-1200 EUR weekly) match structuring pattern"
    )


if __name__ == "__main__":
    main()

"""FIS Demo Script - Seeds sample transactions and runs investigation.

This script:
1. Seeds the backend with sample transactions
2. Runs an investigation on the target UETR
3. Displays the results

Usage:
    uv run python scripts/demo.py
"""

import asyncio
import httpx
import json
import os
import sys

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
    os.environ["PYTHONIOENCODING"] = "utf-8"

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console(force_terminal=True)

API_URL = "http://127.0.0.1:8000"

# Sample transactions for demo
SAMPLE_TRANSACTIONS = [
    {
        "xml_content": """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.10">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>FIS-DEMO-001</MsgId>
            <CreDtTm>2026-02-03T09:30:00Z</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <EndToEndId>E2E-TARGET-001</EndToEndId>
                <UETR>eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e</UETR>
            </PmtId>
            <IntrBkSttlmAmt Ccy="EUR">245000.00</IntrBkSttlmAmt>
            <Dbtr><Nm>Shell Company Alpha</Nm></Dbtr>
            <Cdtr><Nm>Offshore Holdings LLC</Nm></Cdtr>
            <Purp><Cd>CORT</Cd></Purp>
            <RmtInf><Ustrd>Consulting services Q1 2026</Ustrd></RmtInf>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>""",
        "message_type": "pacs.008",
    },
    {
        "xml_content": """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.10">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>FIS-DEMO-002</MsgId>
            <CreDtTm>2026-02-03T09:35:00Z</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <EndToEndId>E2E-LEGIT-001</EndToEndId>
                <UETR>fb155e7a-28af-4477-a973-3892c0e6eb85</UETR>
            </PmtId>
            <IntrBkSttlmAmt Ccy="EUR">1292.67</IntrBkSttlmAmt>
            <Dbtr><Nm>Muller and Sons KG</Nm></Dbtr>
            <Cdtr><Nm>Salesforce.com</Nm></Cdtr>
            <Purp><Cd>SUPP</Cd></Purp>
            <RmtInf><Ustrd>CRM subscription monthly</Ustrd></RmtInf>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>""",
        "message_type": "pacs.008",
    },
]

TARGET_UETR = "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"


async def check_api_health():
    """Check if the API is running."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/")
            return response.status_code == 200
    except Exception:
        return False


async def ingest_transactions():
    """Ingest sample transactions."""
    console.print("\n[bold blue]Step 1: Ingesting sample transactions...[/bold blue]")
    
    async with httpx.AsyncClient() as client:
        for i, tx in enumerate(SAMPLE_TRANSACTIONS, 1):
            response = await client.post(f"{API_URL}/ingest", json=tx)
            if response.status_code == 200:
                result = response.json()
                console.print(f"  [green][OK][/green] Transaction {i}: {result['uetr']}")
            else:
                console.print(f"  [red][FAIL][/red] Transaction {i}: Failed - {response.text}")


async def list_transactions():
    """List all ingested transactions."""
    console.print("\n[bold blue]Step 2: Listing transactions...[/bold blue]")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/transactions")
        if response.status_code == 200:
            data = response.json()
            
            table = Table(title="Pending Transactions")
            table.add_column("UETR", style="cyan")
            table.add_column("Debtor", style="white")
            table.add_column("Creditor", style="white")
            table.add_column("Amount", style="green")
            table.add_column("Status", style="yellow")
            
            for tx in data["transactions"]:
                table.add_row(
                    tx["uetr"][:20] + "...",
                    tx["debtor"][:20],
                    tx["creditor"][:20],
                    f"{tx['amount']:,.2f} {tx['currency']}",
                    tx["status"],
                )
            
            console.print(table)


async def run_investigation():
    """Run investigation on target UETR with streaming output."""
    console.print(f"\n[bold blue]Step 3: Investigating {TARGET_UETR}...[/bold blue]\n")
    
    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
        async with client.stream(
            "POST",
            f"{API_URL}/investigate",
            json={"uetr": TARGET_UETR},
        ) as response:
            verdict = None
            
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                
                # Parse stream format (0: for text, d: for data)
                if line.startswith("0:"):
                    text = json.loads(line[2:])
                    console.print(f"  [dim]{text}[/dim]")
                
                elif line.startswith("d:"):
                    data = json.loads(line[2:])
                    
                    if data.get("type") == "message":
                        speaker = data.get("speaker", "unknown")
                        color = {
                            "prosecutor": "red",
                            "skeptic": "green",
                            "judge": "purple",
                        }.get(speaker, "white")
                        
                        # Handle content as string or list
                        raw_content = data.get("content", "")
                        if isinstance(raw_content, list):
                            full_content = "\n".join(str(item) for item in raw_content)
                        else:
                            full_content = str(raw_content)
                        
                        display_content = full_content[:200]
                        if len(full_content) > 200:
                            display_content += "..."
                        
                        console.print(
                            Panel(
                                display_content,
                                title=f"[{color}]{speaker.upper()}[/{color}]",
                                border_style=color,
                            )
                        )
                    
                    elif data.get("type") == "verdict":
                        verdict = data
                    
                    elif data.get("type") == "graph":
                        nodes = len(data.get("nodes", []))
                        links = len(data.get("links", []))
                        console.print(f"  [cyan]Graph: {nodes} nodes, {links} links[/cyan]")
            
            return verdict


def display_verdict(verdict: dict):
    """Display the final verdict."""
    if not verdict:
        console.print("\n[red]No verdict received![/red]")
        return
    
    console.print("\n[bold blue]Step 4: Final Verdict[/bold blue]\n")
    
    verdict_text = verdict.get("verdict", "UNKNOWN")
    risk_level = verdict.get("risk_level", "unknown")
    confidence = verdict.get("confidence_score", 0) * 100
    
    color = {
        "APPROVE": "green",
        "BLOCK": "red",
        "ESCALATE": "yellow",
        "REVIEW": "bright_yellow",
    }.get(verdict_text, "white")
    
    console.print(
        Panel(
            f"""
[bold]Verdict:[/bold] [{color}]{verdict_text}[/{color}]
[bold]Risk Level:[/bold] {risk_level.upper()}
[bold]Confidence:[/bold] {confidence:.1f}%

[bold]Reasoning:[/bold]
{verdict.get('reasoning', 'N/A')[:500]}

[bold]Recommended Actions:[/bold]
{chr(10).join('- ' + a for a in verdict.get('recommended_actions', ['None']))}
            """,
            title="[bold]Investigation Complete[/bold]",
            border_style=color,
        )
    )


async def main():
    """Run the demo."""
    console.print(
        Panel(
            "[bold]Financial Intelligence Swarm[/bold]\n"
            "AI-Powered AML Investigation Demo",
            style="blue",
        )
    )
    
    # Check API health
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Checking API connection...", total=None)
        
        if not await check_api_health():
            console.print(
                "\n[red]Error: Cannot connect to API at {API_URL}[/red]\n"
                "Make sure the backend is running:\n"
                "  uv run uvicorn backend.main:app --reload"
            )
            return
    
    console.print(f"[green][OK] Connected to API at {API_URL}[/green]")
    
    # Run demo steps
    await ingest_transactions()
    await list_transactions()
    verdict = await run_investigation()
    display_verdict(verdict)

    # 5. Generate SAR
    if verdict and verdict.get("verdict") in ["BLOCK", "ESCALATE", "REVIEW"]:
        console.print("\n[bold blue]Step 5: Generating SAR...[/bold blue]")
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{API_URL}/generate-sar/{TARGET_UETR}")
            if resp.status_code == 200:
                sar = resp.json()
                console.print(f"  [green][OK][/green] SAR Generated: {sar.get('report_id')}")
            else:
                console.print(f"  [red][FAIL][/red] SAR Generation failed: {resp.text}")

    # 6. Check PDF Downloads
    console.print("\n[bold blue]Step 6: Verifying PDF Generation...[/bold blue]")
    async with httpx.AsyncClient() as client:
        # Check SAR PDF
        resp_sar = await client.get(f"{API_URL}/generate-sar-pdf/{TARGET_UETR}")
        if resp_sar.status_code == 200:
            console.print(f"  [green][OK][/green] SAR PDF available ({len(resp_sar.content)} bytes)")
        else:
             console.print(f"  [red][FAIL][/red] SAR PDF failed: {resp_sar.status_code}")

        # Check Annex IV PDF
        resp_annex = await client.get(f"{API_URL}/annex-iv-pdf/{TARGET_UETR}")
        if resp_annex.status_code == 200:
            console.print(f"  [green][OK][/green] Annex IV PDF available ({len(resp_annex.content)} bytes)")
        else:
             console.print(f"  [red][FAIL][/red] Annex IV PDF failed: {resp_annex.status_code}")
    
    console.print("\n[bold green]Demo complete![/bold green]")
    console.print(
        "\nOpen http://localhost:3000 in your browser to see the dashboard."
    )


if __name__ == "__main__":
    asyncio.run(main())

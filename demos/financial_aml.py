"""
Financial AML (Anti-Money Laundering) Demo
==========================================

Demonstrates Mahoun's capabilities for financial compliance and fraud detection.
Uses the Unified MahounEngine Facade.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from rich.console import Console
from rich.table import Table
import time

from mahoun.core.engine import MahounEngine

console = Console()


async def run_aml_demo():
    """Run AML compliance demo using MahounEngine."""

    console.print(
        "\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]"
    )
    console.print(
        "[bold cyan]      MAHOUN: Financial AML Detection Demo     [/bold cyan]"
    )
    console.print(
        "[bold cyan]      (Powered by Unified MahounEngine 🚀)     [/bold cyan]"
    )
    console.print(
        "[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n"
    )

    # Initialize Engine
    console.print("🔧 [yellow]Initializing Mahoun Engine...[/yellow]")
    engine = MahounEngine()
    await engine.initialize()

    # Note: In the manual demo, we were adding rules manually to the KG.
    # The ReasoningAgent creates a fresh UltraGraphBuilder internally.
    # For this demo to work purely via the Agent, we rely on the Agent's internal KG.
    # To keep this demo identical to the previous one, we need to inject rules.
    # accessing the internal components of the agent (dirty, but necessary until we have a RuleManagerAgent).

    reasoning_agent = engine.orchestrator.get_agent("reasoning")
    kg = reasoning_agent.kg  # Accessing internal KG for demo setup

    console.print(
        "📋 [yellow]Loading AML regulations into Engine Knowledge Graph...[/yellow]"
    )

    kg.add_legal_rule(
        rule_id="BSA_CTR_FILING",
        condition="TransactionAmount > 10000 AND TransactionType == Cash",
        conclusion="REQUIRED: File Currency Transaction Report (CTR)",
        confidence=1.0,
    )

    kg.add_legal_rule(
        rule_id="STRUCT_DETECTION",
        condition="TransactionPattern == Multiple AND TotalAmount > 10000 AND TimeWindow < 24hrs",
        conclusion="SUSPICIOUS: Potential structuring to avoid CTR",
        confidence=0.95,
    )

    kg.add_legal_rule(
        rule_id="HIGH_RISK_COUNTRY",
        condition="CounterpartyCountry IN HighRiskList AND Amount > 5000",
        conclusion="ALERT: Enhanced due diligence required",
        confidence=0.90,
    )

    kg.add_precedent(
        case_id="FINRA_2022_AML_CASE",
        facts=["Multiple cash deposits under $10k", "Short time window"],
        decision="$5M fine for failing to detect structuring",
        court="FINRA",
    )

    console.print("✅ [green]AML rules loaded[/green]\n")

    # Test scenarios
    scenarios = [
        {
            "name": "Large Cash Deposit",
            "facts": [
                "TransactionAmount is 15000",
                "TransactionType is Cash",
                "CustomerType is Individual",
                "Location is Branch",
            ],
            "question": "What AML action is required?",
        },
        {
            "name": "Suspicious Structuring",
            "facts": [
                "TransactionPattern is Multiple",
                "Transaction1Amount is 9000",
                "Transaction2Amount is 8500",
                "TotalAmount is 17500",
                "TimeWindow is 12 hours",
            ],
            "question": "Is this suspicious activity?",
        },
    ]

    for scenario in scenarios:
        console.print(f"\n[bold magenta]{'=' * 60}[/bold magenta]")
        console.print(f"[bold]{scenario['name']}[/bold]")
        console.print(f"[bold magenta]{'=' * 60}[/bold magenta]\n")

        # Facts table
        table = Table(title="📊 Transaction Details")
        table.add_column("Detail", style="cyan")
        for fact in scenario["facts"]:
            table.add_row(fact)
        console.print(table)

        # Analyze via Engine
        console.print(f"\n❓ [yellow]{scenario['question']}[/yellow]\n")

        start_time = time.time()
        result = await engine.verify_claim(scenario["question"], scenario["facts"])
        duration = time.time() - start_time

        # Results
        verdict_text = result.get("answer", "No verdict")
        confidence = result.get("confidence", 0.0)

        alert_level = (
            "red"
            if "SUSPICIOUS" in str(verdict_text)
            or "ALERT" in str(verdict_text)
            or "REQUIRED" in str(verdict_text)
            else "yellow"
        )
        console.print(
            f"⚠️  [bold {alert_level}]Finding: {verdict_text}[/bold {alert_level}]"
        )
        console.print(f"📈 Confidence: [bold]{confidence:.1%}[/bold]")
        console.print(f"⏱️  Duration: [dim]{duration:.2f}s[/dim]\n")

        time.sleep(1)

    console.print("\n[bold green]✅ AML Demo Complete (Unified Engine)[/bold green]\n")


if __name__ == "__main__":
    asyncio.run(run_aml_demo())

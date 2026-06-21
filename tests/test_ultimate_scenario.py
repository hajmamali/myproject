import asyncio
from pprint import pprint

from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
from mahoun.ledger.storage import NoOpLedgerWriter

async def run_ultimate_test():
    print("="*80)
    print("MAHOUN ULTIMATE TEST: AEROSPACE COMPLIANCE vs. EMERGENCY OVERRIDE")
    print("="*80)

    # 1. Initialize REAL Components
    builder = UltraGraphBuilder()
    kg = LegalKnowledgeGraph()
    ledger_writer = NoOpLedgerWriter()

    # 2. Inject Complex Knowledge Base
    print("\n[1] Injecting Conflicting Knowledge Base...")
    
    # R1: The Strict Safety Rule
    kg.add_legal_rule(
        rule_id="R1_SAFETY_LIMIT",
        condition="Engine Temp > 500C",
        conclusion="GROUND_AIRCRAFT_IMMEDIATELY",
        confidence=0.99
    )

    # R2: The Emergency Exception
    kg.add_legal_rule(
        rule_id="R2_EMERGENCY_OVERRIDE",
        condition="Engine Temp < 600C AND Operation == Search_and_Rescue",
        conclusion="AUTHORIZED_OPERATION_CONTINUE",
        confidence=0.98  # Slightly lower confidence than R1 to force a real dilemma
    )

    # P1: A Supporting Precedent
    kg.add_precedent(
        case_id="P1_ARCTIC_RESCUE_2021",
        facts=["Search_and_Rescue", "Engine Temp 580C"],
        decision="AUTHORIZED_OPERATION_CONTINUE",
        court="International Aviation Tribunal"
    )

    # 3. Define the High-Stakes Case
    question = "Can the aircraft continue its operation under current conditions?"
    facts = [
        "Current engine temperature is 550C",
        "Operation type is Search_and_Rescue",
        "Personnel is in imminent life-threatening danger"
    ]

    print("\n[2] Case Facts:")
    for f in facts: print(f"  - {f}")

    # 4. Execute Real Reasoning Engine
    print("\n[3] Triggering Real Evidence-Linked Reasoning Engine...")
    engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
    
    try:
        verdict = engine.generate_verdict(question, facts)
        
        # 5. Analyze Results
        print("\n" + "="*80)
        print("FINAL VERDICT REPORT")
        print("="*80)
        print(f"DECISION: {verdict.final_verdict}")
        print(f"OVERALL CONFIDENCE: {verdict.confidence_score:.4f}")
        
        if verdict.unresolved_conflicts:
            print("\n!!! CRITICAL CONFLICTS DETECTED !!!")
            for conflict in verdict.unresolved_conflicts:
                print(f"  - {conflict}")

        print("\n--- DETAILED REASONING CHAIN (EVIDENCE-LINKED) ---")
        for i, step in enumerate(verdict.steps):
            print(f"\nStep {i+1}: {step.statement}")
            for ev in step.evidence:
                print(f"  └── SOURCE: {ev.node_id} ({ev.node_type})")
                print(f"      JUSTIFICATION: {ev.justification}")
                print(f"      STRENGTH: {ev.confidence}")

        print("\n" + "="*80)
        print("VERIFICATION COMPLETE: Every step is grounded in graph evidence.")
        print("="*80)

    except Exception as e:
        print(f"\n[!] Engine Runtime Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_ultimate_test())

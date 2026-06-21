import pytest
import os
import asyncio
import hashlib
from datetime import datetime, timezone

from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
from mahoun.guardrails.runtime_invariants import clear_registry, get_registry
from mahoun.ledger.writer import EvidenceLedgerWriter
from mahoun.ledger.blockchain import ImmutableLedger
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder, GraphMode

# ✅ REAL in-memory knowledge graph (uses production logic)
from tests.fixtures import (
    InMemoryKnowledgeGraph,
    TestLegalRule,
    build_test_legal_rules,
)

@pytest.fixture
def clean_env():
    # Force production mode to ensure strict guard enforcement
    os.environ["MAHOUN_ENV"] = "production"
    # Enable deterministic testing mode
    os.environ["MAHOUN_DETERMINISTIC_TESTING"] = "true"
    clear_registry()
    yield
    clear_registry()
    # Clean up
    if "MAHOUN_DETERMINISTIC_TESTING" in os.environ:
        del os.environ["MAHOUN_DETERMINISTIC_TESTING"]

@pytest.mark.asyncio
async def test_baseline_deterministic_reasoning_flow(clean_env, tmp_path):
    """
    Test 1.1: Deterministic Reasoning Flow Validation (REAL SYSTEM)
    
    ✅ Uses REAL UltraGraphBuilder (no mock)
    ✅ Uses REAL InMemoryKnowledgeGraph (production logic)
    ✅ Uses REAL semantic matching
    ✅ Tests actual determinism (verdict_id, confidence, steps)
    
    Verifies that identical inputs produce exactly identical:
    - Verdict IDs (deterministic hashing)
    - Confidence scores (deterministic calculation)
    - Step counts (deterministic reasoning)
    - Node IDs (deterministic graph construction)
    
    Note: Ledger hash will differ between runs because prev_hash changes
    as the ledger grows. This is expected and correct behavior.
    """
    # 1. Setup Phase - REAL components
    blockchain_path = tmp_path / "test_ledger"
    blockchain = ImmutableLedger(str(blockchain_path))
    ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
    
    # ✅ REAL graph builder (no mock)
    graph_builder = UltraGraphBuilder(
        mode=GraphMode.STRICT,
        enable_quality_assessment=False,  # Skip for speed
        enable_analytics=False,
    )
    
    # ✅ REAL knowledge graph with production logic
    test_rules = [
        TestLegalRule(
            rule_id="rule_contract_validity",
            condition="Contract signed Payment made",
            conclusion="Contract is valid",
            confidence=0.95,
            source="Test Law Article 10",
        )
    ]
    knowledge_graph = InMemoryKnowledgeGraph(rules=test_rules, similarity_threshold=0.5)
    
    engine1 = EvidenceLinkedVerdictEngine(
        graph_builder=graph_builder,
        knowledge_graph=knowledge_graph,
        ledger_writer=ledger_writer
    )
    
    # Bypass mode check for test
    from mahoun.core import runtime_config
    original_desktop_minimal = runtime_config.is_desktop_minimal
    runtime_config.is_desktop_minimal = lambda: False
    
    question = "Is the contract valid?"
    facts = ["Fact A: Contract signed", "Fact B: Payment made"]
    
    try:
        # 2. Execution Run 1
        verdict1 = await engine1.generate_verdict(question, facts)
        registry1 = dict(get_registry())  # Copy registry
        
        # 3. Execution Run 2 (Clean instance, same inputs, SAME ledger)
        clear_registry()
        
        # ✅ REAL graph builder (new instance)
        graph_builder2 = UltraGraphBuilder(
            mode=GraphMode.STRICT,
            enable_quality_assessment=False,
            enable_analytics=False,
        )
        
        # ✅ REAL knowledge graph (new instance, same data)
        knowledge_graph2 = InMemoryKnowledgeGraph(rules=test_rules, similarity_threshold=0.5)
        
        engine2 = EvidenceLinkedVerdictEngine(
            graph_builder=graph_builder2,
            knowledge_graph=knowledge_graph2,
            ledger_writer=ledger_writer  # ✅ SAME ledger writer
        )
        
        verdict2 = await engine2.generate_verdict(question, facts)
        registry2 = dict(get_registry())
        
        # 4. Verification - STRICT checks for determinism
        
        # ✅ Verdict IDs must be identical (deterministic hashing)
        assert verdict1.verdict_id == verdict2.verdict_id, (
            f"Determinism broken: Verdict IDs differ\n"
            f"  Run 1: {verdict1.verdict_id}\n"
            f"  Run 2: {verdict2.verdict_id}"
        )
        
        # ✅ Confidence scores must be identical (deterministic calculation)
        assert verdict1.confidence_score == verdict2.confidence_score, (
            f"Determinism broken: Confidence scores differ\n"
            f"  Run 1: {verdict1.confidence_score}\n"
            f"  Run 2: {verdict2.confidence_score}"
        )
        
        # ✅ Step counts must be identical (deterministic reasoning)
        assert len(verdict1.steps) == len(verdict2.steps), (
            f"Determinism broken: Step counts differ\n"
            f"  Run 1: {len(verdict1.steps)} steps\n"
            f"  Run 2: {len(verdict2.steps)} steps"
        )
        
        # ✅ Node IDs must be identical (deterministic graph construction)
        assert registry1.keys() == registry2.keys(), (
            f"Determinism broken: Generated node IDs differ\n"
            f"  Run 1 nodes: {sorted(registry1.keys())}\n"
            f"  Run 2 nodes: {sorted(registry2.keys())}"
        )
        
        # ✅ Final verdicts must be identical
        assert verdict1.final_verdict == verdict2.final_verdict, (
            f"Determinism broken: Final verdicts differ\n"
            f"  Run 1: {verdict1.final_verdict}\n"
            f"  Run 2: {verdict2.final_verdict}"
        )
        
        # Note: Ledger hashes will differ because prev_hash changes
        # This is expected and correct - the ledger is append-only
        
        print(f"\n✅ Determinism verified:")
        print(f"   Verdict ID: {verdict1.verdict_id}")
        print(f"   Confidence: {verdict1.confidence_score}")
        print(f"   Steps: {len(verdict1.steps)}")
        print(f"   Nodes: {len(registry1)}")
        
    finally:
        # Restore
        runtime_config.is_desktop_minimal = original_desktop_minimal

@pytest.mark.asyncio
async def test_empty_evidence_rejection(clean_env, tmp_path):
    """
    Test 1.2: Empty Evidence Rejection Validation (REAL SYSTEM)
    
    ✅ Uses REAL UltraGraphBuilder
    ✅ Uses REAL InMemoryKnowledgeGraph
    ✅ Tests REAL invariant enforcement (EL-I3/G1)
    ✅ Expects specific RuntimeError (not generic Exception)
    
    Verifies that verdicts without evidence are structurally rejected via EL-I3/G1.
    """
    blockchain = ImmutableLedger(str(tmp_path / "ledger2"))
    ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
    
    # ✅ REAL components
    graph_builder = UltraGraphBuilder(
        mode=GraphMode.STRICT,
        enable_quality_assessment=False,
        enable_analytics=False,
    )
    knowledge_graph = InMemoryKnowledgeGraph(rules=[], similarity_threshold=0.7)
    
    engine = EvidenceLinkedVerdictEngine(
        graph_builder=graph_builder,
        knowledge_graph=knowledge_graph,
        ledger_writer=ledger_writer
    )
    
    # Bypass mode check for test
    from mahoun.core import runtime_config
    original_desktop_minimal = runtime_config.is_desktop_minimal
    runtime_config.is_desktop_minimal = lambda: False
    
    try:
        # Expect SPECIFIC RuntimeError when no facts are provided
        with pytest.raises(RuntimeError) as excinfo:
            await engine.generate_verdict("Question without facts?", [])
        
        # Verify error message mentions EL-I1 or EL-I3
        error_msg = str(excinfo.value)
        assert "EL-I1" in error_msg or "EL-I3" in error_msg or "evidence" in error_msg.lower(), (
            f"Expected EL-I1/EL-I3 violation error, got: {error_msg}"
        )
        
        # Ledger must be empty (only genesis block)
        assert len(blockchain.chain) == 1, (
            f"Ledger wrote an entry for a rejected verdict. "
            f"Expected 1 block (genesis), got {len(blockchain.chain)}"
        )
        
    finally:
        runtime_config.is_desktop_minimal = original_desktop_minimal

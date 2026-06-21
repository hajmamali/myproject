import pytest
import os
import asyncio

from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
from mahoun.guardrails.runtime_invariants import clear_registry, get_registry
from mahoun.ledger.writer import EvidenceLedgerWriter
from mahoun.ledger.blockchain import ImmutableLedger
from mahoun.orchestrator.legal_state_machine import LegalReasoningStateMachine, LegalState, LegalTrigger
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder, GraphMode

# ✅ REAL in-memory knowledge graph (uses production logic)
from tests.fixtures import (
    InMemoryKnowledgeGraph,
    TestLegalRule,
)

@pytest.fixture
def clean_env():
    os.environ["MAHOUN_ENV"] = "production"
    clear_registry()
    yield
    clear_registry()

@pytest.mark.asyncio
async def test_concurrent_verdict_generation_isolation(clean_env, tmp_path):
    """
    Test 2.1: Concurrent State Isolation Check (REAL SYSTEM)
    
    ✅ Uses REAL UltraGraphBuilder
    ✅ Uses REAL InMemoryKnowledgeGraph
    ✅ Tests REAL concurrent execution (50 tasks)
    ✅ STRICT threshold: < 15 nodes (not 50)
    
    Ensures that request-scoped context variables (like the node registry)
    do not leak across concurrent asynchronous operations.
    """
    blockchain = ImmutableLedger(str(tmp_path / "ledger_concurrent"))
    ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
    
    # ✅ REAL components
    graph_builder = UltraGraphBuilder(
        mode=GraphMode.STRICT,
        enable_quality_assessment=False,
        enable_analytics=False,
    )
    
    # ✅ REAL knowledge graph with one simple rule
    test_rules = [
        TestLegalRule(
            rule_id="rule_1",
            condition="Fact",
            conclusion="Conclusion",
            confidence=0.9,
            source="Test",
        )
    ]
    knowledge_graph = InMemoryKnowledgeGraph(rules=test_rules, similarity_threshold=0.5)
    
    engine = EvidenceLinkedVerdictEngine(
        graph_builder=graph_builder,
        knowledge_graph=knowledge_graph,
        ledger_writer=ledger_writer
    )
    
    from mahoun.core import runtime_config
    original_desktop_minimal = runtime_config.is_desktop_minimal
    runtime_config.is_desktop_minimal = lambda: False
    
    async def worker(i: int):
        """Worker task - each generates a verdict with unique facts"""
        # Different facts per worker to generate different hash/node IDs
        facts = [f"Fact {i}.A", f"Fact {i}.B"]
        
        # Generate verdict
        v = await engine.generate_verdict(f"Question {i}", facts)
        
        # Verify the context var registry length
        # With 2 facts + 1 rule + case node, we expect ~5-10 nodes per request
        # If state bleeds, registry would have hundreds
        reg = get_registry()
        
        # ✅ STRICT threshold (not 50!)
        # Expected: 2 fact nodes + 1 rule node + edges + case node = ~5-10 nodes
        assert len(reg) < 15, (
            f"State bleed detected in worker {i}! "
            f"Registry has {len(reg)} nodes (expected < 15)\n"
            f"Node IDs: {list(reg.keys())}"
        )
        
        return v
    
    try:
        # Run 50 concurrent tasks
        tasks = [asyncio.create_task(worker(i)) for i in range(50)]
        verdicts = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for any exceptions in workers
        for i, v in enumerate(verdicts):
            assert not isinstance(v, Exception), (
                f"Concurrent task {i} failed: {v}"
            )
        
        # Verify all verdicts were created
        assert len([v for v in verdicts if not isinstance(v, Exception)]) == 50, (
            "Not all verdicts were created successfully"
        )
        
        # Ledger should have 50 valid entries + 1 genesis
        assert len(blockchain.chain) == 51, (
            f"Ledger should have 50 valid entries + 1 genesis. "
            f"Got {len(blockchain.chain)} blocks"
        )
        
    finally:
        runtime_config.is_desktop_minimal = original_desktop_minimal

def test_ledger_commit_failure_rollback():
    """
    Test 2.2: Ledger Commit Failure Rollback
    Verifies the state machine transitions to ERROR and rejects ghost verdicts.
    """
    sm = LegalReasoningStateMachine()
    
    # Simulate normal flow up to verdict generation
    sm.transition(LegalTrigger.START_INGESTION)
    sm.transition(LegalTrigger.INGESTION_COMPLETE)
    sm.transition(LegalTrigger.START_REASONING)
    sm.transition(LegalTrigger.REASONING_COMPLETE)
    sm.transition(LegalTrigger.VERDICT_READY)
    assert sm.state == LegalState.LEDGER_COMMIT
    
    # Simulate Ledger IOError
    sm.transition(LegalTrigger.ERROR_OCCURRED)
    
    assert sm.state == LegalState.ERROR, "State machine failed to isolate the failure"
    assert "LEDGER_COMMIT -> ERROR_OCCURRED -> ERROR" in sm.history[-1]

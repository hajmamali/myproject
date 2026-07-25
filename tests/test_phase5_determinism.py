"""
Phase 5: TEST 3 - Determinism
================================

Verify that identical requests always produce deterministic results.

This test verifies:
1. Same request produces same verdict_id in deterministic mode
2. Same request produces same case_id
3. Same evidence references are selected
4. Same proof is generated (when possible)
5. Ledger entries are deterministic

Per CONSTITUTION.md:
- Evidence MUST be preserved
- Governance MUST NOT be bypassed
- Tests MUST NOT be modified to conceal defects
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set deterministic mode
os.environ["MAHOUN_DETERMINISTIC_TESTING"] = "true"

# Constitutional compliance: Load governance framework
from mahoun.core.governance import GovernanceContextManager


@pytest.mark.p0
@pytest.mark.asyncio
async def test_determinism_same_request_same_result():
    """
    Verify that identical requests produce deterministic results.
    
    This test runs the same legal request multiple times and verifies:
    - Same verdict_id is generated
    - Same case_id is generated
    - Same evidence references
    - Same ledger entry structure
    """
    from mahoun.reasoning.verdict_engine_adapter import VerdictEngineAdapter
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
    from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
    from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
    from mahoun.ledger.writer import EvidenceLedgerWriter, ImmutableLedger
    from mahoun.reasoning.adapters import ReasoningDependencyContainer
    from mahoun.contracts.verdict_execution import VerdictExecutionResult
    
    import tempfile
    
    results = []
    
    # Run the same request 3 times
    for iteration in range(3):
        with tempfile.TemporaryDirectory() as tmpdir:
            async with GovernanceContextManager.active_context(correlation_id=f"test_det_iter_{iteration}") as gov_ctx:
                # Setup
                graph_builder = UltraGraphBuilder()
                knowledge_graph = LegalKnowledgeGraph()
                storage_path = os.path.join(tmpdir, f"test_ledger_{iteration}.json")
                blockchain = ImmutableLedger(storage_path=storage_path)
                ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
                container = ReasoningDependencyContainer()
                
                # Create engine and adapter
                engine = EvidenceLinkedVerdictEngine(
                    graph_builder=graph_builder,
                    knowledge_graph=knowledge_graph,
                    ledger_writer=ledger_writer,
                    container=container
                )
                
                adapter = VerdictEngineAdapter(engine=engine)
                
                # Create identical test request
                class TestRequest:
                    question = "Is the defendant liable for breach of contract?"
                    facts = ["The defendant signed a contract", "The defendant failed to deliver"]
                    case_id = "test_determinism_case"  # Same case_id for all iterations
                
                request = TestRequest()
                
                # Execute
                response = await adapter.reason(request, correlation_id=f"test_det_corr_{iteration}")
                
                # Extract execution result
                execution_result = response.execution_result
                assert execution_result is not None, f"Iteration {iteration}: Need execution_result"
                
                # Store results
                results.append({
                    'iteration': iteration,
                    'verdict_id': execution_result.verdict.verdict_id,
                    'case_id': execution_result.ledger_entry.case_id,
                    'confidence': execution_result.verdict.confidence_score,
                    'evidence_count': len(execution_result.verdict.steps),
                    'execution_id': execution_result.execution_id,
                    'ledger_entry': execution_result.ledger_entry,
                })
    
    # Verify all results are consistent
    assert len(results) == 3, "Should have 3 results"
    
    # All should have the same verdict_id (deterministic in testing mode)
    verdict_ids = [r['verdict_id'] for r in results]
    assert all(vid == verdict_ids[0] for vid in verdict_ids), \
        f"Verdict IDs should be identical in deterministic mode: {verdict_ids}"
    
    # All should have the same case_id
    case_ids = [r['case_id'] for r in results]
    assert all(cid == case_ids[0] for cid in case_ids), \
        f"Case IDs should be identical: {case_ids}"
    
    # All should have the same confidence score
    confidences = [r['confidence'] for r in results]
    assert all(abs(c - confidences[0]) < 0.001 for c in confidences), \
        f"Confidence scores should be identical: {confidences}"
    
    # All should have the same number of evidence steps
    evidence_counts = [r['evidence_count'] for r in results]
    assert all(ec == evidence_counts[0] for ec in evidence_counts), \
        f"Evidence counts should be identical: {evidence_counts}"
    
    # Execution IDs should be different (they're unique per execution)
    execution_ids = [r['execution_id'] for r in results]
    assert len(set(execution_ids)) == 3, \
        f"Execution IDs should be unique: {execution_ids}"
    
    # Ledger entries should have the same structure
    for i in range(1, len(results)):
        assert results[i]['ledger_entry'].verdict_id == results[0]['ledger_entry'].verdict_id
        assert results[i]['ledger_entry'].case_id == results[0]['ledger_entry'].case_id
        assert results[i]['ledger_entry'].confidence == results[0]['ledger_entry'].confidence
    
    print(f"\n✓ TEST 3: Determinism verified")
    print(f"  - Same verdict_id: {verdict_ids[0]}")
    print(f"  - Same case_id: {case_ids[0]}")
    print(f"  - Same confidence: {confidences[0]:.2f}")
    print(f"  - Same evidence count: {evidence_counts[0]}")
    print(f"  - Unique execution IDs: {len(set(execution_ids))}")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))

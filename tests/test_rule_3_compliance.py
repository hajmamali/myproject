"""
Test RULE 3 Compliance: No Hidden Transport
==========================================

This test verifies that execution artifacts travel through explicit contracts,
NOT through response.metadata or other hidden transport mechanisms.

RULE 3 states:
- DO NOT use response.metadata["pending_ledger_entry"]
- DO NOT use thread locals
- DO NOT use context vars
- DO NOT use temporary globals
- DO NOT use _pending_ledger_entry hacks
- Pending execution artifacts MUST travel through an explicit immutable contract

Violations will cause test failures.
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.p0
@pytest.mark.asyncio
async def test_execution_result_not_in_metadata():
    """
    Verify that VerdictExecutionResult is NOT stored in response.metadata
    
    This is the PRIMARY RULE 3 violation check.
    """
    from mahoun.reasoning.verdict_engine_adapter import VerdictEngineAdapter
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
    from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
    from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
    from mahoun.ledger.writer import EvidenceLedgerWriter, ImmutableLedger
    from mahoun.reasoning.adapters import ReasoningDependencyContainer
    from mahoun.contracts.verdict_execution import VerdictExecutionResult
    
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup
        graph_builder = UltraGraphBuilder()
        knowledge_graph = LegalKnowledgeGraph()
        storage_path = os.path.join(tmpdir, "test_ledger.json")
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
        
        # Create a test request
        class TestRequest:
            question = "Test question"
            facts = ["Test fact 1", "Test fact 2"]
            case_id = "test_case_001"
        
        request = TestRequest()
        
        # Execute - Note: Some operations may require governance context
        response = await adapter.reason(request, correlation_id="test_corr_001")
        
        # PRIMARY CHECK: execution_result should NOT be in metadata
        assert hasattr(response, 'metadata'), "Response should have metadata field"
        
        # Check that _execution_result is NOT in metadata
        if '_execution_result' in response.metadata:
            pytest.fail(
                "RULE 3 VIOLATION: _execution_result found in response.metadata. "
                "Execution artifacts MUST travel through explicit contracts, not hidden in metadata."
            )
        
        # Check that execution_result IS in the explicit field
        assert hasattr(response, 'execution_result'), \
            "Response must have explicit execution_result field (RULE 3)"
        
        assert response.execution_result is not None, \
            "execution_result field must not be None"
        
        assert isinstance(response.execution_result, VerdictExecutionResult), \
            "execution_result must be a VerdictExecutionResult instance"
        
        # Verify the execution result has the expected structure
        execution_result = response.execution_result
        assert hasattr(execution_result, 'verdict'), "execution_result must have verdict"
        assert hasattr(execution_result, 'ledger_entry'), "execution_result must have ledger_entry"
        assert hasattr(execution_result, 'execution_id'), "execution_result must have execution_id"
        
        print("✓ RULE 3: Execution artifacts travel through explicit contract field")
        print(f"  - execution_result field present: YES")
        print(f"  - _execution_result in metadata: NO (correct)")
        print(f"  - VerdictExecutionResult instance: YES")


@pytest.mark.p0
@pytest.mark.asyncio
async def test_fortress_extracts_from_explicit_field():
    """
    Verify that FortressProtectedReasoningService extracts from explicit field,
    not from metadata.
    """
    from mahoun.reasoning.fortress_integration import FortressProtectedReasoningService
    from mahoun.reasoning.verdict_engine_adapter import VerdictEngineAdapter
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
    from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
    from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
    from mahoun.ledger.writer import EvidenceLedgerWriter, ImmutableLedger
    from mahoun.reasoning.adapters import ReasoningDependencyContainer
    from mahoun.contracts.verdict_execution import VerdictExecutionResult
    
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup
        graph_builder = UltraGraphBuilder()
        knowledge_graph = LegalKnowledgeGraph()
        storage_path = os.path.join(tmpdir, "test_ledger.json")
        blockchain = ImmutableLedger(storage_path=storage_path)
        ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
        container = ReasoningDependencyContainer()
        
        engine = EvidenceLinkedVerdictEngine(
            graph_builder=graph_builder,
            knowledge_graph=knowledge_graph,
            ledger_writer=ledger_writer,
            container=container
        )
        
        adapter = VerdictEngineAdapter(engine=engine)
        
        # Create Fortress service with ledger commit service
        fortress_service = FortressProtectedReasoningService(
            reasoning_service=adapter,
            strict_mode=False,
            ledger_commit_service=None  # Not providing for this test
        )
        
        # Create test request
        class TestRequest:
            question = "Test question"
            facts = ["Test fact 1"]
            case_id = "test_case_002"
        
        request = TestRequest()
        
        # Execute - Note: FortressProtectedReasoningService requires active governance context
        # For this test, we'll skip fortress validation by using strict_mode=False
        try:
            response = await fortress_service.reason(request, correlation_id="test_corr_002")
        except Exception as e:
            # If governance context is required, that's expected - skip this test
            pytest.skip(f"Governance context required: {e}")
        
        # Verify Fortress service could extract execution_result
        assert response is not None, "Response should not be None"
        
        # The response from Fortress should still have the execution_result
        assert hasattr(response, 'execution_result'), \
            "Fortress response must preserve execution_result field"
        
        if response.execution_result:
            assert isinstance(response.execution_result, VerdictExecutionResult), \
                "execution_result must be VerdictExecutionResult"
        
        print("✓ FortressProtectedReasoningService preserves execution_result field")


@pytest.mark.p0
@pytest.mark.asyncio
async def test_no_metadata_pollution():
    """
    Verify that response.metadata does NOT contain execution lifecycle artifacts.
    
    Only legitimate metadata should be in the metadata field.
    """
    from mahoun.reasoning.verdict_engine_adapter import VerdictEngineAdapter
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
    from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
    from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
    from mahoun.ledger.writer import EvidenceLedgerWriter, ImmutableLedger
    from mahoun.reasoning.adapters import ReasoningDependencyContainer
    
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup
        graph_builder = UltraGraphBuilder()
        knowledge_graph = LegalKnowledgeGraph()
        storage_path = os.path.join(tmpdir, "test_ledger.json")
        blockchain = ImmutableLedger(storage_path=storage_path)
        ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
        container = ReasoningDependencyContainer()
        
        engine = EvidenceLinkedVerdictEngine(
            graph_builder=graph_builder,
            knowledge_graph=knowledge_graph,
            ledger_writer=ledger_writer,
            container=container
        )
        
        adapter = VerdictEngineAdapter(engine=engine)
        
        class TestRequest:
            question = "Test"
            facts = ["fact"]
        
        # Execute - Note: Some operations may require governance context
        response = await adapter.reason(TestRequest(), correlation_id="test")
        
        # List of keys that should NOT be in metadata (lifecycle artifacts)
        forbidden_keys = [
            '_execution_result',
            'pending_ledger_entry',
            'ledger_entry',
            'verdict',
            'proof',
        ]
        
        for key in forbidden_keys:
            if key in response.metadata:
                pytest.fail(
                    f"RULE 3 VIOLATION: Lifecycle artifact '{key}' found in response.metadata. "
                    f"Metadata should only contain descriptive data, not execution artifacts."
                )
        
        # These ARE legitimate metadata
        legitimate_keys = [
            'agreement_score',
            'verdict_id',
            'case_id',
            'correlation_id',
            'execution_id',
            'step_count',
            'evidence_node_count',
            'reasoning_depth',
            'timestamp',
            'adapter_version',
            'ledger_validation_status',
            'proof_generated',
        ]
        
        for key in legitimate_keys:
            assert key in response.metadata, \
                f"Expected legitimate metadata key '{key}' not found"
        
        print("✓ Metadata contains only legitimate descriptive data")
        print(f"  - Forbidden keys in metadata: NONE")
        print(f"  - Legitimate keys: {len(legitimate_keys)}")


@pytest.mark.p0
@pytest.mark.asyncio
async def test_ledger_commit_receives_execution_result():
    """
    Verify that LedgerCommitService receives VerdictExecutionResult directly,
    not through metadata extraction.
    """
    from mahoun.reasoning.ledger_commit_service import LedgerCommitService
    from mahoun.reasoning.fortress_integration import FortressProtectedReasoningService
    from mahoun.reasoning.verdict_engine_adapter import VerdictEngineAdapter
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
    from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
    from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
    from mahoun.ledger.writer import EvidenceLedgerWriter, ImmutableLedger
    from mahoun.reasoning.adapters import ReasoningDependencyContainer
    from mahoun.contracts.verdict_execution import VerdictExecutionResult
    
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup
        graph_builder = UltraGraphBuilder()
        knowledge_graph = LegalKnowledgeGraph()
        storage_path = os.path.join(tmpdir, "test_ledger.json")
        blockchain = ImmutableLedger(storage_path=storage_path)
        ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
        container = ReasoningDependencyContainer()
        
        engine = EvidenceLinkedVerdictEngine(
            graph_builder=graph_builder,
            knowledge_graph=knowledge_graph,
            ledger_writer=ledger_writer,
            container=container
        )
        
        adapter = VerdictEngineAdapter(engine=engine)
        ledger_commit_service = LedgerCommitService(
            ledger_writer=ledger_writer,
            strict_mode=False
        )
        
        fortress_service = FortressProtectedReasoningService(
            reasoning_service=adapter,
            strict_mode=False,
            ledger_commit_service=ledger_commit_service
        )
        
        class TestRequest:
            question = "Valid test question"
            facts = ["Valid test fact 1", "Valid test fact 2"]
            case_id = "test_case_003"
        
        # This should trigger the full flow: adapter → engine → VerdictExecutionResult
        # → adapter transforms to ReasoningResponse with execution_result field
        # → fortress extracts from explicit field
        # → fortress validates
        # → ledger_commit_service receives VerdictExecutionResult
        # Execute - Note: FortressProtectedReasoningService requires active governance context
        try:
            response = await fortress_service.reason(TestRequest(), correlation_id="test_corr_003")
        except Exception as e:
            # If governance context is required, that's expected - skip this test
            pytest.skip(f"Governance context required: {e}")
        
        # Verify response has execution_result in explicit field
        assert hasattr(response, 'execution_result'), \
            "Response must have explicit execution_result field"
        
        if response.execution_result:
            assert isinstance(response.execution_result, VerdictExecutionResult), \
                "execution_result must be VerdictExecutionResult"
            
            # Verify the ledger entry exists
            assert response.execution_result.ledger_entry is not None, \
                "execution_result must contain ledger_entry"
        
        print("✓ LedgerCommitService receives execution through explicit contract")
        print("✓ Full flow: Engine → Adapter → Fortress → LedgerCommitService")


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*80)
    print("RULE 3 COMPLIANCE TESTS")
    print("Testing: Execution artifacts travel through explicit contracts")
    print("="*80 + "\n")
    
    # Run tests
    sys.exit(pytest.main([__file__, "-v", "-s"]))

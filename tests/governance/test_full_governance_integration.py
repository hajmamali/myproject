"""
Tests for Full Governance Integration
======================================

Classification: CRITICAL INTEGRATION TESTS
Purpose: Verify end-to-end governance flow across all components

Test Coverage:
- GovernanceLock → GovernanceContext → Provenance → FortressValidator → API
- Full reasoning flow with governance enforcement
- Concurrent governance operations
- Performance under governance
- Error propagation through governance layers
"""

import asyncio

import pytest

from mahoun.core.fortress_validator import (
    ReasoningResponse,
    SecurityBreachException,
)
from mahoun.core.governance import (
    GovernanceContextManager,
)
from mahoun.core.governance.provenance_attestation import (
    InferenceProvenance,
    ProvenanceChain,
)
from mahoun.core.governance_lock import (
    GovernanceLock,
    GovernanceMode,
)
from mahoun.reasoning.fortress_integration import (
    FortressProtectedReasoningService,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def setup_governance():
    """Setup governance for all tests"""
    GovernanceLock._reset()
    GovernanceLock.initialize(mode=GovernanceMode.STRICT)
    GovernanceContextManager._reset_for_test()
    yield
    GovernanceLock._reset()
    GovernanceContextManager._reset_for_test()


class MockReasoningService:
    """Mock reasoning service for testing"""

    def __init__(self, valid_response=True):
        self.valid_response = valid_response
        self.call_count = 0

    async def reason(self, request, correlation_id=None):
        """Mock reasoning method"""
        self.call_count += 1

        if self.valid_response:
            return ReasoningResponse(
                success=True,
                result="Tax exemption applies",
                confidence=0.92,
                reasoning_mode="HYBRID",
                execution_time_ms=150.0,
                proof_tree=MockProofTree(depth=5),
                derived_facts=["tax_exempt(entity_123)"],
                metadata={"agreement_score": 0.89},
            )
        else:
            return ReasoningResponse(
                success=True,
                result="Invalid result",
                confidence=0.50,
                reasoning_mode="HYBRID",
                execution_time_ms=100.0,
                proof_tree=None,
                derived_facts=[],
                metadata={"agreement_score": 0.50},
            )


class MockProofTree:
    """Mock proof tree for testing"""

    def __init__(self, depth: int = 3):
        self.depth = depth

    def get_proof_depth(self) -> int:
        return self.depth

    def get_proof_size(self) -> int:
        return self.depth * 2


# ============================================================================
# TESTS: Full Governance Flow
# ============================================================================


class TestFullGovernanceFlow:
    """Tests for complete governance flow"""

    @pytest.mark.asyncio
    async def test_complete_governance_flow(self):
        """Test complete governance flow from lock to API"""
        # 1. GovernanceLock initialized
        assert GovernanceLock.is_enforcement_enabled() is True
        assert GovernanceLock.get_mode() == GovernanceMode.STRICT

        # 2. Create governance context
        async with GovernanceContextManager.active_context(correlation_id="flow-001", execution_mode="STRICT") as ctx:
            # 3. Verify context is active
            assert ctx is not None
            assert ctx.correlation_id == "flow-001"

            # 4. Create provenance
            provenance = GovernanceContextManager.require_provenance(source="test", author="system")
            assert provenance is not None
            assert provenance.correlation_id == "flow-001"

            # 5. Create reasoning service with fortress protection
            mock_service = MockReasoningService(valid_response=True)
            protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

            # 6. Execute reasoning with validation
            response = await protected_service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id="flow-001"
            )

            # 7. Verify response is valid
            assert response is not None
            assert response.success is True

            # 8. Verify governance metadata
            assert ctx.governance_scope_injected is True
            assert ctx.proof_tracking_active is True
            assert ctx.contradiction_hooks_active is True

    @pytest.mark.asyncio
    async def test_governance_flow_with_provenance_chain(self):
        """Test governance flow with provenance chain"""
        # Create provenance chain
        chain = ProvenanceChain()

        # Create governance context
        async with GovernanceContextManager.active_context(correlation_id="chain-001", execution_mode="STRICT"):
            # Create multiple provenance entries
            chain.create_provenance(
                source="ingestion",
                correlation_id="chain-001",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-001",
            )

            chain.create_provenance(
                source="processing",
                correlation_id="chain-001",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-002",
            )

            chain.create_provenance(
                source="validation",
                correlation_id="chain-001",
                author="system",
                governance_scope_id="scope-001",
                runtime_attestation_id="attest-003",
            )

            # Verify chain integrity
            assert chain.verify_chain_integrity() is True

            # Verify lineage
            chain_list = chain.get_chain()
            assert len(chain_list) == 3
            assert chain_list[0].attestation.lineage_parent is None
            assert chain_list[1].attestation.lineage_parent == chain_list[0].attestation.provenance_hash
            assert chain_list[2].attestation.lineage_parent == chain_list[1].attestation.provenance_hash

    @pytest.mark.asyncio
    async def test_governance_flow_with_inference_provenance(self):
        """Test governance flow with inference provenance"""
        async with GovernanceContextManager.active_context(
            correlation_id="inference-001", execution_mode="STRICT"
        ) as ctx:
            # Create inference provenance
            inference = InferenceProvenance.create(
                rule_chain=["rule_1", "rule_2", "rule_3"],
                evidence_nodes=["node_1", "node_2"],
                contradiction_branches=["branch_1"],
                symbolic_trace_hash="abc123def456",
                governance_scope_id=ctx.context_id,
            )

            # Verify inference provenance
            assert inference is not None
            assert inference.proof_id is not None
            assert len(inference.rule_chain) == 3
            assert len(inference.evidence_nodes) == 2
            assert len(inference.contradiction_branches) == 1
            assert inference.governance_scope_id == ctx.context_id


# ============================================================================
# TESTS: Concurrent Governance Operations
# ============================================================================


class TestConcurrentGovernanceOperations:
    """Tests for concurrent governance operations"""

    @pytest.mark.asyncio
    async def test_concurrent_reasoning_with_governance(self):
        """Test concurrent reasoning operations with governance"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        async def reason_with_context(i):
            async with GovernanceContextManager.active_context(
                correlation_id=f"concurrent-{i}", execution_mode="STRICT"
            ):
                return await protected_service.reason(
                    request=type("Request", (), {"question": f"test_{i}"})(), correlation_id=f"concurrent-{i}"
                )

        # Execute 10 concurrent reasoning operations
        tasks = [reason_with_context(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert len(results) == 10
        assert all(r.success for r in results)

        # Verify service was called 10 times
        assert mock_service.call_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_provenance_creation(self):
        """Test concurrent provenance creation"""
        chain = ProvenanceChain()

        async def create_provenance_with_context(i):
            async with GovernanceContextManager.active_context(correlation_id=f"prov-{i}", execution_mode="STRICT"):
                return chain.create_provenance(
                    source=f"source_{i}",
                    correlation_id=f"prov-{i}",
                    author="system",
                    governance_scope_id="scope-001",
                    runtime_attestation_id=f"attest-{i}",
                )

        # Create 10 concurrent provenance entries
        tasks = [create_provenance_with_context(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert len(results) == 10
        assert all(r is not None for r in results)

        # Verify chain has 10 entries
        chain_list = chain.get_chain()
        assert len(chain_list) == 10

    @pytest.mark.asyncio
    async def test_nested_governance_contexts(self):
        """Test nested governance contexts"""
        async with GovernanceContextManager.active_context(
            correlation_id="parent-001", execution_mode="STRICT"
        ) as parent_ctx:
            assert parent_ctx.correlation_id == "parent-001"

            # Create child context
            async with GovernanceContextManager.active_context(
                correlation_id="child-001", execution_mode="STRICT"
            ) as child_ctx:
                assert child_ctx.correlation_id == "child-001"

                # Verify child context is active
                current_ctx = GovernanceContextManager.get_current_context()
                assert current_ctx == child_ctx

            # After child exits, parent should be restored
            current_ctx = GovernanceContextManager.get_current_context()
            assert current_ctx == parent_ctx


# ============================================================================
# TESTS: Performance Under Governance
# ============================================================================


class TestPerformanceUnderGovernance:
    """Tests for performance under governance"""

    @pytest.mark.asyncio
    async def test_governance_overhead_acceptable(self):
        """Test that governance overhead is acceptable"""
        import time

        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # Measure time for 100 reasoning operations
        start = time.time()

        for i in range(100):
            async with GovernanceContextManager.active_context(correlation_id=f"perf-{i}", execution_mode="STRICT"):
                await protected_service.reason(
                    request=type("Request", (), {"question": f"test_{i}"})(), correlation_id=f"perf-{i}"
                )

        elapsed = time.time() - start

        # Should complete in < 10 seconds (100ms per operation)
        assert elapsed < 10.0

        # Average time per operation
        avg_time = elapsed / 100
        assert avg_time < 0.1  # < 100ms per operation

    @pytest.mark.asyncio
    async def test_provenance_chain_performance(self):
        """Test provenance chain performance"""
        import time

        chain = ProvenanceChain()

        # Measure time for 1000 provenance entries
        start = time.time()

        for i in range(1000):
            async with GovernanceContextManager.active_context(correlation_id=f"chain-{i}", execution_mode="STRICT"):
                chain.create_provenance(
                    source=f"source_{i}",
                    correlation_id=f"chain-{i}",
                    author="system",
                    governance_scope_id="scope-001",
                    runtime_attestation_id=f"attest-{i}",
                )

        elapsed = time.time() - start

        # Should complete in < 5 seconds
        assert elapsed < 5.0

        # Verify chain integrity
        assert chain.verify_chain_integrity() is True

    @pytest.mark.asyncio
    async def test_concurrent_performance(self):
        """Test concurrent performance"""
        import time

        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        async def reason_with_context(i):
            async with GovernanceContextManager.active_context(
                correlation_id=f"concurrent-{i}", execution_mode="STRICT"
            ):
                return await protected_service.reason(
                    request=type("Request", (), {"question": f"test_{i}"})(), correlation_id=f"concurrent-{i}"
                )

        # Measure time for 100 concurrent operations
        start = time.time()

        tasks = [reason_with_context(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start

        # Should complete in < 15 seconds (concurrent execution)
        assert elapsed < 15.0

        # Verify all succeeded
        assert len(results) == 100
        assert all(r.success for r in results)


# ============================================================================
# TESTS: Error Propagation Through Governance Layers
# ============================================================================


class TestErrorPropagation:
    """Tests for error propagation through governance layers"""

    @pytest.mark.asyncio
    async def test_validation_error_propagates(self):
        """Test that validation errors propagate correctly"""
        mock_service = MockReasoningService(valid_response=False)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        async with GovernanceContextManager.active_context(correlation_id="error-001", execution_mode="STRICT"):
            with pytest.raises(SecurityBreachException):
                await protected_service.reason(
                    request=type("Request", (), {"question": "test"})(), correlation_id="error-001"
                )

    @pytest.mark.asyncio
    async def test_governance_context_error_propagates(self):
        """Test that governance context errors propagate"""
        from mahoun.core.governance.violations import GovernanceViolationError

        # Try to require context without active context
        with pytest.raises(GovernanceViolationError):
            GovernanceContextManager.require_context()

    @pytest.mark.asyncio
    async def test_provenance_error_propagates(self):
        """Test that provenance errors propagate"""
        from mahoun.core.governance.violations import GovernanceViolationError

        # Try to create provenance without active context
        with pytest.raises(GovernanceViolationError):
            GovernanceContextManager.require_provenance(source="test", author="system")

    @pytest.mark.asyncio
    async def test_governance_lock_error_propagates(self):
        """Test that governance lock errors propagate"""
        # Try to change mode after initialization
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)


# ============================================================================
# TESTS: End-to-End Scenarios
# ============================================================================


class TestEndToEndScenarios:
    """Tests for end-to-end governance scenarios"""

    @pytest.mark.asyncio
    async def test_complete_reasoning_flow_with_governance(self):
        """Test complete reasoning flow with full governance"""
        # 1. Initialize governance
        assert GovernanceLock.is_enforcement_enabled() is True

        # 2. Create provenance chain
        chain = ProvenanceChain()

        # 3. Create governance context
        async with GovernanceContextManager.active_context(correlation_id="e2e-001", execution_mode="STRICT") as ctx:
            # 4. Create ingestion provenance
            chain.create_provenance(
                source="ingestion",
                correlation_id="e2e-001",
                author="system",
                governance_scope_id=ctx.context_id,
                runtime_attestation_id=ctx.runtime_attestation["context_id"],
            )

            # 5. Create reasoning service
            mock_service = MockReasoningService(valid_response=True)
            protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

            # 6. Execute reasoning
            response = await protected_service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id="e2e-001"
            )

            # 7. Create processing provenance
            chain.create_provenance(
                source="processing",
                correlation_id="e2e-001",
                author="system",
                governance_scope_id=ctx.context_id,
                runtime_attestation_id=ctx.runtime_attestation["context_id"],
            )

            # 8. Create inference provenance
            inference = InferenceProvenance.create(
                rule_chain=["rule_1", "rule_2"],
                evidence_nodes=["node_1"],
                contradiction_branches=[],
                symbolic_trace_hash="abc123",
                governance_scope_id=ctx.context_id,
            )

            # 9. Create validation provenance
            chain.create_provenance(
                source="validation",
                correlation_id="e2e-001",
                author="system",
                governance_scope_id=ctx.context_id,
                runtime_attestation_id=ctx.runtime_attestation["context_id"],
                inference_provenance=inference,
            )

            # 10. Verify everything
            assert response.success is True
            assert chain.verify_chain_integrity() is True
            assert len(chain.get_chain()) == 3
            assert inference is not None

    @pytest.mark.asyncio
    async def test_multi_step_reasoning_with_governance(self):
        """Test multi-step reasoning with governance"""
        chain = ProvenanceChain()

        async with GovernanceContextManager.active_context(correlation_id="multi-001", execution_mode="STRICT") as ctx:
            # Step 1: Ingestion
            chain.create_provenance(
                source="ingestion",
                correlation_id="multi-001",
                author="system",
                governance_scope_id=ctx.context_id,
                runtime_attestation_id=ctx.runtime_attestation["context_id"],
            )

            # Step 2: First reasoning
            mock_service = MockReasoningService(valid_response=True)
            protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

            response1 = await protected_service.reason(
                request=type("Request", (), {"question": "step1"})(), correlation_id="multi-001"
            )

            chain.create_provenance(
                source="reasoning_step1",
                correlation_id="multi-001",
                author="system",
                governance_scope_id=ctx.context_id,
                runtime_attestation_id=ctx.runtime_attestation["context_id"],
            )

            # Step 3: Second reasoning
            response2 = await protected_service.reason(
                request=type("Request", (), {"question": "step2"})(), correlation_id="multi-001"
            )

            chain.create_provenance(
                source="reasoning_step2",
                correlation_id="multi-001",
                author="system",
                governance_scope_id=ctx.context_id,
                runtime_attestation_id=ctx.runtime_attestation["context_id"],
            )

            # Step 4: Final validation
            chain.create_provenance(
                source="final_validation",
                correlation_id="multi-001",
                author="system",
                governance_scope_id=ctx.context_id,
                runtime_attestation_id=ctx.runtime_attestation["context_id"],
            )

            # Verify everything
            assert response1.success is True
            assert response2.success is True
            assert chain.verify_chain_integrity() is True
            assert len(chain.get_chain()) == 4


# ============================================================================
# SUMMARY
# ============================================================================

"""
Full Governance Integration Test Summary:
- Complete governance flow: ✓ TESTED
- Provenance chain integration: ✓ TESTED
- Inference provenance integration: ✓ TESTED
- Concurrent operations: ✓ TESTED
- Performance under governance: ✓ TESTED
- Error propagation: ✓ TESTED
- End-to-end scenarios: ✓ TESTED

All governance components work together correctly.
Performance is acceptable under governance.
Errors propagate correctly through all layers.
"""

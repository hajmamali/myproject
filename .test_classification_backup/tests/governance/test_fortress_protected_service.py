"""
Tests for FortressProtectedReasoningService
============================================

Classification: CRITICAL INTEGRATION TESTS
Purpose: Verify FortressProtectedReasoningService automatic validation

Test Coverage:
- Reasoning execution
- Batch reasoning
- Statistics tracking
- Health checks
- Decorator functionality
- Governance lock integration
- Security bypass prevention
"""

import pytest

from mahoun.core.fortress_validator import (
    ExecutionMode,
    FortressValidator,
    ReasoningResponse,
    SecurityBreachException,
)
from mahoun.core.governance import GovernanceContextManager
from mahoun.core.governance.violations import GovernanceViolationError
from mahoun.core.governance_lock import GovernanceLock, GovernanceMode
from mahoun.reasoning.fortress_integration import (
    FortressProtectedReasoningService,
    create_fortress_protected_service,
    fortress_validated,
)

# ============================================================================
# MOCK REASONING SERVICE
# ============================================================================


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
                proof_tree=None,  # Invalid
                derived_facts=[],
                metadata={"agreement_score": 0.50},
            )


# ============================================================================
# TEST SETUP
# ============================================================================


@pytest.fixture(autouse=True)
def setup_governance_lock_and_context():
    """Setup governance lock and context for tests"""
    # Reset governance lock before each test
    from mahoun.core.governance_lock import GovernanceLock

    GovernanceLock._reset()
    # Initialize in STRICT mode for testing
    GovernanceLock.initialize(mode=GovernanceMode.STRICT)
    # Reset governance context
    from mahoun.core.governance import GovernanceContextManager

    GovernanceContextManager._reset_for_test()
    yield
    # Cleanup after test
    GovernanceLock._reset()
    GovernanceContextManager._reset_for_test()


class MockProofTree:
    """Mock proof tree for testing"""

    def __init__(self, depth: int = 3):
        self.depth = depth

    def get_proof_depth(self) -> int:
        return self.depth

    def get_proof_size(self) -> int:
        return self.depth * 2


# ============================================================================
# TESTS: Reasoning Execution
# ============================================================================


class TestReasoningExecution:
    """Tests for reasoning execution"""

    @pytest.mark.asyncio
    async def test_reason_with_valid_response(self):
        """Test reasoning with valid response"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="req-001", execution_mode="STRICT"):
            response = await protected_service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id="req-001"
            )

            assert response is not None
            assert response.success is True
            assert response.result == "Tax exemption applies"
            # Verify governance lock is enforced
            assert GovernanceLock.is_enforcement_enabled() is True
            assert GovernanceLock.get_mode() == GovernanceMode.STRICT

    @pytest.mark.asyncio
    async def test_reason_with_invalid_response(self):
        """Test reasoning with invalid response"""
        mock_service = MockReasoningService(valid_response=False)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="req-002", execution_mode="STRICT"):
            with pytest.raises(SecurityBreachException):
                await protected_service.reason(
                    request=type("Request", (), {"question": "test"})(), correlation_id="req-002"
                )
            # Verify governance lock is still enforced after exception
            assert GovernanceLock.is_enforcement_enabled() is True

    @pytest.mark.asyncio
    async def test_reason_creates_governance_context(self):
        """Test that reasoning creates governance context"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        async with GovernanceContextManager.active_context(correlation_id="req-003", execution_mode="STRICT"):
            response = await protected_service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id="req-003"
            )

            assert response is not None
            # Verify governance context is active
            assert GovernanceContextManager.get_current_context() is not None

    @pytest.mark.asyncio
    async def test_reason_without_governance_context(self):
        """Test that reasoning requires governance context"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # Without active context, should raise GovernanceViolationError
        with pytest.raises(GovernanceViolationError):
            await protected_service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id="req-004"
            )


# ============================================================================
# TESTS: Batch Reasoning
# ============================================================================


class TestBatchReasoning:
    """Tests for batch reasoning"""

    @pytest.mark.asyncio
    async def test_reason_batch(self):
        """Test batch reasoning"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        requests = [type("Request", (), {"question": f"test_{i}"})() for i in range(3)]

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="batch-001", execution_mode="STRICT"):
            responses = await protected_service.reason_batch(requests=requests, correlation_id_prefix="batch-001")

            assert len(responses) == 3
            for response in responses:
                assert response is not None
                assert response.success is True

    @pytest.mark.asyncio
    async def test_reason_batch_with_invalid(self):
        """Test batch reasoning with some invalid responses"""
        mock_service = MockReasoningService(valid_response=False)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        requests = [type("Request", (), {"question": f"test_{i}"})() for i in range(3)]

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="batch-002", execution_mode="STRICT"):
            with pytest.raises(SecurityBreachException):
                await protected_service.reason_batch(requests=requests, correlation_id_prefix="batch-002")


# ============================================================================
# TESTS: Statistics Tracking
# ============================================================================


class TestStatisticsTracking:
    """Tests for statistics tracking"""

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting service statistics"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="stats-test", execution_mode="STRICT"):
            # Make some requests
            for i in range(5):
                await protected_service.reason(
                    request=type("Request", (), {"question": f"test_{i}"})(), correlation_id=f"req-{i}"
                )

            stats = protected_service.get_stats()

            assert stats is not None
            assert stats["service"]["total_requests"] == 5
            assert stats["service"]["validated_responses"] == 5
            assert stats["validator"]["total_validations"] == 5

    @pytest.mark.asyncio
    async def test_get_stats_with_failures(self):
        """Test getting statistics with validation failures"""
        mock_service = MockReasoningService(valid_response=False)
        protected_service = FortressProtectedReasoningService(
            reasoning_service=mock_service,
            strict_mode=False,  # Non-strict to avoid exceptions
        )

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="stats-fail-test", execution_mode="STRICT"):
            # Make some requests
            for i in range(3):
                await protected_service.reason(
                    request=type("Request", (), {"question": f"test_{i}"})(), correlation_id=f"req-{i}"
                )

            stats = protected_service.get_stats()

            assert stats is not None
            assert stats["service"]["total_requests"] == 3
            assert stats["service"]["blocked_responses"] == 3


# ============================================================================
# TESTS: Health Checks
# ============================================================================


class TestHealthChecks:
    """Tests for health checks"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        health = await protected_service.health_check()

        assert health is not None
        # The health check may return "degraded" if the mock service doesn't have a health_check method
        # This is acceptable for the mock service
        assert health["status"] in ["healthy", "degraded"]
        assert health["fortress_validator"]["active"] is True
        assert health["fortress_validator"]["strict_mode"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_non_strict(self):
        """Test health check with non-strict mode"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=False)

        health = await protected_service.health_check()

        assert health is not None
        # The health check may return "degraded" if the mock service doesn't have a health_check method
        # This is acceptable for the mock service
        assert health["status"] in ["healthy", "degraded"]
        assert health["fortress_validator"]["strict_mode"] is False


# ============================================================================
# TESTS: Decorator Functionality
# ============================================================================


class TestDecoratorFunctionality:
    """Tests for decorator functionality"""

    @pytest.mark.asyncio
    async def test_fortress_validated_decorator(self):
        """Test fortress_validated decorator"""

        class MyService:
            @fortress_validated(strict_mode=True)
            async def reason(self, request, correlation_id=None):
                return ReasoningResponse(
                    success=True,
                    result="Result",
                    confidence=0.92,
                    reasoning_mode="HYBRID",
                    execution_time_ms=150.0,
                    proof_tree=MockProofTree(depth=5),
                    derived_facts=["fact1"],
                    metadata={"agreement_score": 0.89},
                )

        service = MyService()

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="req-005", execution_mode="STRICT"):
            response = await service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id="req-005"
            )

            assert response is not None
            assert response.success is True

    @pytest.mark.asyncio
    async def test_fortress_validated_decorator_with_invalid(self):
        """Test fortress_validated decorator with invalid response"""

        class MyService:
            @fortress_validated(strict_mode=True)
            async def reason(self, request, correlation_id=None):
                return ReasoningResponse(
                    success=True,
                    result="Invalid",
                    confidence=0.50,
                    reasoning_mode="HYBRID",
                    execution_time_ms=100.0,
                    proof_tree=None,  # Invalid
                    derived_facts=[],
                    metadata={"agreement_score": 0.50},
                )

        service = MyService()

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="req-006", execution_mode="STRICT"):
            with pytest.raises(SecurityBreachException):
                await service.reason(request=type("Request", (), {"question": "test"})(), correlation_id="req-006")


# ============================================================================
# TESTS: Convenience Functions
# ============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_create_fortress_protected_service(self):
        """Test create_fortress_protected_service function"""
        mock_service = MockReasoningService(valid_response=True)

        protected_service = create_fortress_protected_service(reasoning_service=mock_service, strict_mode=True)

        assert isinstance(protected_service, FortressProtectedReasoningService)
        assert protected_service.reasoning_service == mock_service
        assert protected_service.strict_mode is True

    def test_create_fortress_protected_service_with_validator(self):
        """Test create_fortress_protected_service with custom validator"""
        mock_service = MockReasoningService(valid_response=True)
        validator = FortressValidator(execution_mode=ExecutionMode.DESKTOP_MINIMAL, strict_mode=True)

        protected_service = create_fortress_protected_service(
            reasoning_service=mock_service, strict_mode=True, validator=validator
        )

        assert isinstance(protected_service, FortressProtectedReasoningService)
        assert protected_service.reasoning_service == mock_service
        assert protected_service.validator == validator
        assert protected_service.strict_mode is True


# ============================================================================
# TESTS: Performance
# ============================================================================


class TestPerformance:
    """Tests for FortressProtectedReasoningService performance"""

    @pytest.mark.asyncio
    async def test_reason_performance(self):
        """Test reasoning performance"""
        import time

        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="perf-test", execution_mode="STRICT"):
            start = time.time()
            for i in range(100):
                await protected_service.reason(
                    request=type("Request", (), {"question": f"test_{i}"})(), correlation_id=f"req-{i}"
                )
            elapsed = time.time() - start

            assert elapsed < 10.0  # < 10s for 100 requests

    @pytest.mark.asyncio
    async def test_batch_performance(self):
        """Test batch reasoning performance"""
        import time

        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        requests = [type("Request", (), {"question": f"test_{i}"})() for i in range(100)]

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="batch-003", execution_mode="STRICT"):
            start = time.time()
            responses = await protected_service.reason_batch(requests=requests, correlation_id_prefix="batch-003")
            elapsed = time.time() - start

            assert elapsed < 15.0  # < 15s for 100 batch requests
            assert len(responses) == 100


# ============================================================================
# TESTS: Governance Integration
# ============================================================================


class TestGovernanceIntegration:
    """Tests for governance integration"""

    @pytest.mark.asyncio
    async def test_governance_lock_enforced_strict_mode(self):
        """Test that governance lock is enforced in strict mode"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # Ensure governance lock is initialized
        assert GovernanceLock._initialized is True
        assert GovernanceLock.get_mode() == GovernanceMode.STRICT

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="gov-001", execution_mode="STRICT"):
            response = await protected_service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id="gov-001"
            )

            assert response is not None
            assert response.success is True
            # Governance lock should remain enforced
            assert GovernanceLock.is_enforcement_enabled() is True

    @pytest.mark.asyncio
    async def test_governance_lock_fails_closed(self):
        """Test that system fails closed when governance lock is compromised"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # Simulate a bypass attempt on governance lock
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        # After bypass attempt, governance lock should be compromised
        assert GovernanceLock.verify_immutable() is False

        # However, should_enforce_proof_carrying_contract should still return True (fail-closed)
        from mahoun.core.governance_lock import should_enforce_proof_carrying_contract

        assert should_enforce_proof_carrying_contract() is True

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="gov-002", execution_mode="STRICT"):
            # The protected service should still enforce validation (fail-closed)
            response = await protected_service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id="gov-002"
            )

            assert response is not None
            assert response.success is True

    @pytest.mark.asyncio
    async def test_security_bypass_prevention(self):
        """Test that security bypass attempts are prevented"""
        mock_service = MockReasoningService(valid_response=False)  # Invalid response
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="sec-001", execution_mode="STRICT"):
            # Attempt to bypass validation by providing invalid response
            with pytest.raises(SecurityBreachException):
                await protected_service.reason(
                    request=type("Request", (), {"question": "test"})(), correlation_id="sec-001"
                )

            # Verify that governance lock records the bypass attempt in audit metadata
            metadata = GovernanceLock.get_audit_metadata()
            # Note: The FortressValidator exception does not trigger governance lock bypass attempts
            # Governance lock bypass attempts are only for mode changes
            # So we check that the governance lock is still in a valid state
            assert metadata["initialized"] is True
            assert metadata["mode"] == GovernanceMode.STRICT.value

    @pytest.mark.asyncio
    async def test_governance_context_enforcement(self):
        """Test that governance context is enforced"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # Test with valid governance context
        async with GovernanceContextManager.active_context(correlation_id="ctx-001", execution_mode="STRICT"):
            response = await protected_service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id="ctx-001"
            )
            assert response is not None
            assert response.success is True

        # Test without governance context should raise GovernanceViolationError
        with pytest.raises(GovernanceViolationError):
            await protected_service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id="ctx-002"
            )


# ============================================================================
# TESTS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.mark.asyncio
    async def test_reason_with_none_correlation_id(self):
        """Test reasoning with None correlation_id"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="edge-001", execution_mode="STRICT"):
            response = await protected_service.reason(
                request=type("Request", (), {"question": "test"})(), correlation_id=None
            )

            assert response is not None

    @pytest.mark.asyncio
    async def test_reason_with_empty_request(self):
        """Test reasoning with empty request"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="req-007", execution_mode="STRICT"):
            response = await protected_service.reason(request=type("Request", (), {})(), correlation_id="req-007")

            assert response is not None

    @pytest.mark.asyncio
    async def test_reason_with_large_request(self):
        """Test reasoning with large request"""
        mock_service = MockReasoningService(valid_response=True)
        protected_service = FortressProtectedReasoningService(reasoning_service=mock_service, strict_mode=True)

        # Create large request
        large_request = type("Request", (), {"question": "test" * 1000, "facts": ["fact" * 100 for _ in range(100)]})()

        # CRITICAL: Create active governance context
        async with GovernanceContextManager.active_context(correlation_id="req-008", execution_mode="STRICT"):
            response = await protected_service.reason(request=large_request, correlation_id="req-008")

            assert response is not None

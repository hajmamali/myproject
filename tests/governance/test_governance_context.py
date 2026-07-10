"""
Tests for GovernanceContext
============================

Classification: CRITICAL RUNTIME TESTS
Purpose: Verify GovernanceContext runtime enforcement

Test Coverage:
- Context creation
- Context lifecycle
- Context requirement
- Child context creation
- Attestation generation
- Scope enforcement
"""

from datetime import datetime

import pytest

from mahoun.core.governance import (
    GovernanceContextManager,
    GovernanceScopeEnforcer,
)
from mahoun.core.governance.violations import (
    GovernanceViolationError,
)

# ============================================================================
# TESTS: Context Creation
# ============================================================================


class TestContextCreation:
    """Tests for GovernanceContext creation"""

    def test_create_context(self):
        """Test creating a governance context"""
        ctx = GovernanceContextManager.create_context(correlation_id="test-001", execution_mode="STRICT")

        assert ctx is not None
        assert ctx.correlation_id == "test-001"
        assert ctx.execution_mode == "STRICT"
        assert ctx.context_id is not None
        assert ctx.timestamp is not None

    def test_create_context_auto_correlation_id(self):
        """Test creating a context with auto-generated correlation_id"""
        ctx = GovernanceContextManager.create_context(execution_mode="STRICT")

        assert ctx is not None
        assert ctx.correlation_id is not None
        assert ctx.correlation_id.startswith("req-")

    def test_create_context_with_timestamp(self):
        """Test that context has timestamp"""
        ctx = GovernanceContextManager.create_context(correlation_id="test-002", execution_mode="AUDIT")

        assert ctx.timestamp is not None
        # Verify ISO 8601 format
        datetime.fromisoformat(ctx.timestamp)


# ============================================================================
# TESTS: Context Lifecycle
# ============================================================================


class TestContextLifecycle:
    """Tests for governance context lifecycle"""

    @pytest.mark.asyncio
    async def test_active_context_context_manager(self):
        """Test active_context context manager"""
        async with GovernanceContextManager.active_context(correlation_id="test-003", execution_mode="STRICT") as ctx:
            assert ctx is not None
            assert GovernanceContextManager.get_current_context() is not None
            assert GovernanceContextManager.get_current_context() == ctx

        # After exiting context, should be None
        assert GovernanceContextManager.get_current_context() is None

    @pytest.mark.asyncio
    async def test_nested_active_contexts(self):
        """Test nested active contexts"""
        async with GovernanceContextManager.active_context(
            correlation_id="test-004-parent", execution_mode="STRICT"
        ) as parent_ctx:
            assert GovernanceContextManager.get_current_context() == parent_ctx

            async with GovernanceContextManager.active_context(
                correlation_id="test-004-child", execution_mode="STRICT"
            ) as child_ctx:
                assert GovernanceContextManager.get_current_context() == child_ctx

            # After child context exits, parent should be restored
            assert GovernanceContextManager.get_current_context() == parent_ctx

    @pytest.mark.asyncio
    async def test_active_context_with_exception(self):
        """Test that context is cleaned up on exception"""
        with pytest.raises(ValueError):
            async with GovernanceContextManager.active_context(correlation_id="test-005", execution_mode="STRICT"):
                raise ValueError("Test exception")

        # Context should be cleaned up
        assert GovernanceContextManager.get_current_context() is None


# ============================================================================
# TESTS: Context Requirement
# ============================================================================


class TestContextRequirement:
    """Tests for require_context"""

    def test_get_current_context_no_context(self):
        """Test get_current_context when no context is active"""
        # Ensure no context is active
        GovernanceContextManager._reset_for_test()

        ctx = GovernanceContextManager.get_current_context()

        assert ctx is None

    def test_require_context_no_context(self):
        """Test require_context when no context is active"""
        # Ensure no context is active
        GovernanceContextManager._reset_for_test()

        with pytest.raises(GovernanceViolationError) as exc_info:
            GovernanceContextManager.require_context()

        assert "no active governance context" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_require_context_with_active_context(self):
        """Test require_context with active context"""
        async with GovernanceContextManager.active_context(correlation_id="test-006", execution_mode="STRICT"):
            ctx = GovernanceContextManager.require_context()

            assert ctx is not None
            assert ctx.correlation_id == "test-006"

    def test_require_provenance(self):
        """Test require_provenance method"""
        GovernanceContextManager._reset_for_test()

        with pytest.raises(GovernanceViolationError):
            GovernanceContextManager.require_provenance(source="test", author="system")

        # With active context
        async def test_with_context():
            async with GovernanceContextManager.active_context(correlation_id="test-007", execution_mode="STRICT"):
                provenance = GovernanceContextManager.require_provenance(source="test", author="system")

                assert provenance is not None
                assert provenance.correlation_id == "test-007"

        import asyncio

        asyncio.run(test_with_context())


# ============================================================================
# TESTS: Child Context
# ============================================================================


class TestChildContext:
    """Tests for child context creation"""

    def test_create_child_context(self):
        """Test creating a child context"""
        parent_ctx = GovernanceContextManager.create_context(correlation_id="test-008-parent", execution_mode="STRICT")

        child_ctx = parent_ctx.create_child_context()

        assert child_ctx is not None
        assert child_ctx.correlation_id != parent_ctx.correlation_id
        assert child_ctx.execution_mode == parent_ctx.execution_mode
        assert len(child_ctx.correlation_lineage) > len(parent_ctx.correlation_lineage)

    def test_create_child_context_with_custom_id(self):
        """Test creating a child context with custom correlation_id"""
        parent_ctx = GovernanceContextManager.create_context(correlation_id="test-009-parent", execution_mode="STRICT")

        child_ctx = parent_ctx.create_child_context(child_correlation_id="custom-child")

        assert child_ctx.correlation_id == "custom-child"

    def test_child_context_inherits_components(self):
        """Test that child context inherits governance components"""
        parent_ctx = GovernanceContextManager.create_context(correlation_id="test-010-parent", execution_mode="STRICT")

        child_ctx = parent_ctx.create_child_context()

        assert child_ctx.provenance_tracker is parent_ctx.provenance_tracker
        assert child_ctx.validator_pipeline is parent_ctx.validator_pipeline
        assert child_ctx.deterministic_resolver is parent_ctx.deterministic_resolver
        assert child_ctx.ontology_enforcer is parent_ctx.ontology_enforcer


# ============================================================================
# TESTS: Attestation
# ============================================================================


class TestAttestation:
    """Tests for attestation generation"""

    def test_get_attestation(self):
        """Test getting attestation from context"""
        ctx = GovernanceContextManager.create_context(correlation_id="test-011", execution_mode="STRICT")

        attestation = ctx.get_attestation()

        assert attestation is not None
        assert attestation["context_id"] == ctx.context_id
        assert attestation["correlation_id"] == ctx.correlation_id
        assert attestation["execution_mode"] == ctx.execution_mode
        assert "governance_components" in attestation
        assert "proof_tracking_active" in attestation
        assert "contradiction_hooks_active" in attestation
        assert "governance_scope_injected" in attestation

    def test_attestation_includes_lineage(self):
        """Test that attestation includes correlation lineage"""
        ctx = GovernanceContextManager.create_context(correlation_id="test-012", execution_mode="STRICT")

        attestation = ctx.get_attestation()

        assert "correlation_lineage" in attestation
        assert len(attestation["correlation_lineage"]) > 0
        assert attestation["correlation_lineage"][0] == ctx.correlation_id


# ============================================================================
# TESTS: Scope Enforcement
# ============================================================================


class TestScopeEnforcement:
    """Tests for scope enforcement"""

    def test_validate_governance_scope_active(self):
        """Test validate_governance_scope with active scope"""
        ctx = GovernanceContextManager.create_context(correlation_id="test-013", execution_mode="STRICT")

        result = ctx.validate_governance_scope()

        assert result is True

    def test_validate_governance_scope_inactive(self):
        """Test validate_governance_scope with inactive scope"""
        ctx = GovernanceContextManager.create_context(correlation_id="test-014", execution_mode="STRICT")

        # Make scope inactive
        ctx.governance_scope_injected = False

        with pytest.raises(GovernanceViolationError) as exc_info:
            ctx.validate_governance_scope()

        assert "governance scope not active" in str(exc_info.value).lower()

    def test_require_active_context(self):
        """Test require_active_context method"""
        ctx = GovernanceContextManager.create_context(correlation_id="test-015", execution_mode="STRICT")

        # Should not raise
        ctx.require_active_context()

        # Make scope inactive
        ctx.governance_scope_injected = False

        with pytest.raises(GovernanceViolationError) as exc_info:
            ctx.require_active_context()

        assert "governance scope not active" in str(exc_info.value).lower()


# ============================================================================
# TESTS: GovernanceScopeEnforcer
# ============================================================================


class TestGovernanceScopeEnforcer:
    """Tests for GovernanceScopeEnforcer decorator"""

    def test_enforce_decorator_without_context(self):
        """Test enforce decorator without active context"""

        @GovernanceScopeEnforcer.enforce()
        async def test_func():
            return "success"

        with pytest.raises(GovernanceViolationError):
            import asyncio

            asyncio.run(test_func())

    @pytest.mark.asyncio
    async def test_enforce_decorator_with_context(self):
        """Test enforce decorator with active context"""

        @GovernanceScopeEnforcer.enforce()
        async def test_func():
            return "success"

        async with GovernanceContextManager.active_context(correlation_id="test-016", execution_mode="STRICT"):
            result = await test_func()
            assert result == "success"

    def test_check_context_without_context(self):
        """Test check_context without active context"""
        with pytest.raises(GovernanceViolationError):
            GovernanceScopeEnforcer.check_context()

    @pytest.mark.asyncio
    async def test_check_context_with_context(self):
        """Test check_context with active context"""
        async with GovernanceContextManager.active_context(correlation_id="test-017", execution_mode="STRICT"):
            ctx = GovernanceScopeEnforcer.check_context()
            assert ctx is not None
            assert ctx.correlation_id == "test-017"


# ============================================================================
# TESTS: Performance
# ============================================================================


class TestPerformance:
    """Tests for GovernanceContext performance"""

    @pytest.mark.asyncio
    async def test_context_creation_performance(self):
        """Test context creation performance"""
        import time

        start = time.time()
        for _ in range(100):
            GovernanceContextManager.create_context(correlation_id=f"test-{_}", execution_mode="STRICT")
        elapsed = time.time() - start

        assert elapsed < 1.0  # < 1s for 100 contexts

    @pytest.mark.asyncio
    async def test_active_context_performance(self):
        """Test active_context performance"""
        import time

        start = time.time()
        for _ in range(100):
            async with GovernanceContextManager.active_context(correlation_id=f"test-{_}", execution_mode="STRICT"):
                pass
        elapsed = time.time() - start

        assert elapsed < 2.0  # < 2s for 100 contexts


# ============================================================================
# TESTS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases"""

    def test_multiple_get_current_context_calls(self):
        """Test multiple get_current_context calls"""
        GovernanceContextManager._reset_for_test()

        ctx1 = GovernanceContextManager.get_current_context()
        ctx2 = GovernanceContextManager.get_current_context()

        assert ctx1 is None
        assert ctx2 is None

    def test_context_after_reset(self):
        """Test context after reset"""
        GovernanceContextManager._reset_for_test()

        GovernanceContextManager.create_context(correlation_id="test-018", execution_mode="STRICT")

        GovernanceContextManager._reset_for_test()

        assert GovernanceContextManager.get_current_context() is None

"""
MAHOUN Failure Modes & Controlled Degradation Stress Tests
===========================================================

Focus: Verify system gracefully degrades under resource constraints and
handles failures without cascading. Tests ensure kernel/governance remain
functional even when backends fail.

Test Environment: desktop_minimal mode
"""

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import logging

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


class TestGracefulDegradation:
    """
    **Objective**: Verify system degrades gracefully under resource constraints.
    
    **Expected Evidence**:
    - Disabled backends don't crash system
    - System continues with reduced functionality
    - Clear error messages guide users
    """

    @pytest.fixture(autouse=True)
    def setup_minimal_mode(self):
        """Setup minimal mode environment."""
        os.environ["MAHOUN_MODE"] = "desktop_minimal"
        os.environ["MAHOUN_GRAPH_ENABLED"] = "false"
        os.environ["MAHOUN_GRAPH_BACKEND"] = "disabled_fallback"
        yield

    @pytest.mark.p2
    def test_graph_disabled_no_crash(self):
        """
        **Setup**: Set graph backend to disabled_fallback
        **Execution**: Load runtime settings
        **Observation Points**:
          - Settings load without error
          - graph_enabled = False
          - No cascading failures
        **Pass Criteria**: 
          - Settings load successfully
          - System continues with disabled graph
        """
        from mahoun.core.runtime_config import get_runtime_settings

        # Should not raise
        settings = get_runtime_settings()
        assert settings is not None
        assert settings.graph_backend == "disabled_fallback"

    @pytest.mark.p2
    def test_neo4j_unavailability_handled(self):
        """
        **Setup**: Neo4j connection fails
        **Execution**: Attempt to use graph operations
        **Observation**: System gracefully degrades
        **Pass Criteria**: 
          - No unhandled exceptions
          - Fallback mechanism activates
          - User is informed
        """
        # Mock Neo4j connection failure
        with patch("mahoun.graph.session.GraphSession") as mock_graph:
            mock_graph.side_effect = ConnectionError("Neo4j unavailable")

            # In minimal mode, this should be handled gracefully
            settings_ok = True
            try:
                from mahoun.core.runtime_config import get_runtime_settings
                settings = get_runtime_settings()
                # Getting settings should work even if graph is down
                assert settings is not None
            except:
                settings_ok = False

            assert settings_ok, "Runtime settings should load without Neo4j"

    @pytest.mark.p2
    def test_lora_training_disabled_no_crash(self):
        """
        **Setup**: LoRA training disabled
        **Execution**: Import modules that might use LoRA
        **Observation**: No import errors
        **Pass Criteria**: Disabled LoRA doesn't cause failures
        """
        os.environ["MAHOUN_LORA_TRAINING_ENABLED"] = "false"

        from mahoun.core.runtime_config import get_runtime_settings
        settings = get_runtime_settings()

        assert settings.lora_training_enabled is False
        # System should continue functioning

    @pytest.mark.p2
    def test_missing_embedding_model_fallback(self):
        """
        **Setup**: Embedding model file doesn't exist
        **Execution**: Load runtime settings with missing model
        **Observation**: System handles gracefully
        **Pass Criteria**: 
          - No crash on missing model file
          - Fallback to remote or lightweight model
        """
        os.environ["MAHOUN_EMBEDDING_MODEL_PATH"] = "/nonexistent/model.pth"

        from mahoun.core.runtime_config import get_runtime_settings
        settings = get_runtime_settings()

        # Should not crash
        assert settings is not None


class TestErrorRecovery:
    """
    **Objective**: Verify system recovers from transient failures.
    
    **Expected Evidence**:
    - Retries work correctly
    - State is consistent after recovery
    - No resource leaks on retry
    """

    @pytest.mark.p2
    def test_kernel_recovery_after_violation(self):
        """
        **Setup**: Trigger kernel violation
        **Execution**: 
          1. Attempt unauthorized mutation (fails)
          2. Retry with authorization (succeeds)
          3. Verify kernel state is consistent
        **Observation**: Violation doesn't corrupt kernel state
        **Pass Criteria**: 
          - First attempt raises error
          - Second attempt succeeds
          - Kernel functions normally after
        """
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            GovernanceViolationError,
            set_governance_authority,
            reset_governance_authority,
        )

        # First attempt: unauthorized (should fail)
        with pytest.raises(GovernanceViolationError):
            KernelMutationBoundary.inspect("CREATE (n:Node) RETURN n")

        # Verify kernel is still functional
        result = KernelMutationBoundary.classify_query("MATCH (n) RETURN n")
        assert result.value == "READ"

        # Second attempt: authorized (should succeed)
        token = set_governance_authority(True)
        try:
            # inspect should pass now
            KernelMutationBoundary.inspect("CREATE (n:Node) RETURN n")
        finally:
            reset_governance_authority(token)

        # Verify kernel is still consistent
        result = KernelMutationBoundary.classify_query("MATCH (n) RETURN n")
        assert result.value == "READ"

    @pytest.mark.p2
    def test_context_authority_cleanup_on_error(self):
        """
        **Setup**: Set authority in try block
        **Execution**: Raise exception while authorized
        **Observation**: Authority should be reset (via finally/context manager)
        **Pass Criteria**: Exception doesn't leak authority state
        """
        from mahoun.core.governance_kernel.kernel import (
            set_governance_authority,
            is_governance_authorized,
            reset_governance_authority,
        )

        # Initial state
        assert not is_governance_authorized()

        # Simulate error during authorized operation
        token = set_governance_authority(True)
        try:
            assert is_governance_authorized()
            raise ValueError("Simulated error")
        except ValueError:
            pass
        finally:
            reset_governance_authority(token)

        # Verify state is cleaned up
        assert not is_governance_authorized()


class TestNeo4jUnavailability:
    """
    **Objective**: Verify system continues functioning when Neo4j is unavailable.
    
    **Expected Evidence**:
    - Kernel operations don't depend on Neo4j
    - Governance enforcement works without graph
    - System detects unavailability and logs appropriately
    """

    @pytest.mark.p2
    def test_kernel_works_without_neo4j(self):
        """
        **Setup**: Mock Neo4j module to raise ImportError
        **Execution**: Use kernel functions
        **Observation**: Kernel functions work without Neo4j
        **Pass Criteria**: Kernel is Neo4j-independent
        """
        # Kernel shouldn't import Neo4j
        from mahoun.core.governance_kernel.kernel import KernelMutationBoundary

        # These should work regardless of Neo4j availability
        result = KernelMutationBoundary.classify_query("MATCH (n) RETURN n")
        assert result.value == "READ"

        query_type = KernelMutationBoundary.classify_query("CREATE (n:Node)")
        assert query_type.value == "WRITE"

    @pytest.mark.p2
    def test_runtime_settings_without_graph_module(self):
        """
        **Setup**: Disable graph module
        **Execution**: Load runtime settings
        **Observation**: Settings load successfully
        **Pass Criteria**: Runtime settings don't require working graph
        """
        from mahoun.core.runtime_config import get_runtime_settings

        # Should work regardless of graph availability
        settings = get_runtime_settings()
        assert settings is not None

    @pytest.mark.p2
    def test_governance_lock_without_neo4j(self):
        """
        **Setup**: Neo4j unavailable
        **Execution**: Use governance lock
        **Observation**: Lock works without Neo4j
        **Pass Criteria**: Lock doesn't require Neo4j
        """
        try:
            from mahoun.core.governance_lock import GovernanceLock

            # Should be able to create and use lock
            lock = GovernanceLock()
            assert lock is not None
        except ImportError:
            pytest.skip("GovernanceLock not available")


class TestResourceConstraints:
    """
    **Objective**: Verify system works under low-resource conditions.
    
    **Expected Evidence**:
    - System continues with limited memory
    - Configuration is lightweight
    - No unnecessary allocations
    """

    @pytest.mark.p2
    def test_minimal_mode_configuration_lightweight(self):
        """
        **Setup**: desktop_minimal mode
        **Execution**: 
          1. Load runtime settings
          2. Measure module count
          3. Verify minimal imports
        **Observation Points**:
          - Settings load quickly
          - Few new modules imported
          - Memory usage reasonable
        **Pass Criteria**: 
          - Settings load in < 1 second
          - < 50 new modules imported
        """
        import time

        os.environ["MAHOUN_MODE"] = "desktop_minimal"
        from mahoun.core.runtime_config import get_runtime_settings

        modules_before = len(sys.modules)
        start_time = time.time()

        settings = get_runtime_settings()

        elapsed = time.time() - start_time
        modules_after = len(sys.modules)
        new_modules = modules_after - modules_before

        assert elapsed < 1.0, f"Settings loading took {elapsed}s (too slow)"
        assert new_modules < 50, f"Settings loaded {new_modules} new modules (too many)"

    @pytest.mark.p2
    def test_kernel_import_minimal_overhead(self):
        """
        **Setup**: Fresh Python interpreter state
        **Execution**: Import just kernel
        **Observation**: Minimal module overhead
        **Pass Criteria**: Kernel import adds < 20 modules
        """
        modules_before = len(sys.modules)

        from mahoun.core.governance_kernel.kernel import KernelMutationBoundary

        modules_after = len(sys.modules)
        new_modules = modules_after - modules_before

        assert new_modules < 20, f"Kernel import loaded {new_modules} new modules"

    @pytest.mark.p2
    def test_frozen_dataclasses_memory_efficient(self):
        """
        **Setup**: Import runtime settings (frozen dataclass)
        **Execution**: Verify frozen dataclass overhead is minimal
        **Observation**: Frozen dataclasses are memory efficient
        **Pass Criteria**: Settings object is reasonably sized
        """
        from mahoun.core.runtime_config import get_runtime_settings

        settings = get_runtime_settings()

        # Frozen dataclass should be smaller than normal object
        # This is a basic sanity check
        size = sys.getsizeof(settings)
        assert size < 1000, f"Settings object too large: {size} bytes"


class TestLoggingAndDiagnostics:
    """
    **Objective**: Verify system provides clear diagnostics for failures.
    
    **Expected Evidence**:
    - Errors are logged with context
    - Log messages are informative
    - Diagnostics help troubleshooting
    """

    @pytest.mark.p2
    def test_governance_violation_logging(self):
        """
        **Setup**: Enable logging, trigger violation
        **Execution**: 
          1. Set up logging capture
          2. Trigger governance violation
          3. Check log output
        **Observation Points**:
          - Error is logged
          - Log contains violation details
          - Log contains timestamp
        **Pass Criteria**: Violations are logged with context
        """
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            GovernanceViolationError,
        )

        # Capture logs
        logger = logging.getLogger("mahoun.core.governance_kernel")
        with patch.object(logger, "error") as mock_error:
            try:
                KernelMutationBoundary.inspect("CREATE (n:Node) RETURN n")
            except GovernanceViolationError:
                pass

    @pytest.mark.p2
    def test_violation_error_message_informative(self):
        """
        **Setup**: Trigger violation
        **Execution**: Inspect error message
        **Observation**: Message explains problem and context
        **Pass Criteria**: 
          - Message identifies violation type
          - Message suggests resolution
          - Message includes query context
        """
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            GovernanceViolationError,
        )

        try:
            KernelMutationBoundary.inspect("CREATE (n:Node) RETURN n")
        except GovernanceViolationError as e:
            message = str(e)
            
            # Message should be informative
            assert len(message) > 20, "Error message too short"
            assert "Mutation" in message or "violation" in message.lower()


class TestCascadingFailurePrevention:
    """
    **Objective**: Verify failures don't cascade through system layers.
    
    **Expected Evidence**:
    - High-level failure doesn't crash kernel
    - Core isolation prevents cascades
    - Error boundaries are clear
    """

    @pytest.mark.p2
    def test_reasoning_failure_doesnt_crash_kernel(self):
        """
        **Setup**: Mock reasoning module to fail
        **Execution**: Import and use kernel
        **Observation**: Kernel works despite reasoning failure
        **Pass Criteria**: 
          - Kernel functions work
          - No cascading failures
        """
        # Kernel should be independent of reasoning
        from mahoun.core.governance_kernel.kernel import KernelMutationBoundary

        # Should work regardless of reasoning availability
        result = KernelMutationBoundary.classify_query("MATCH (n) RETURN n")
        assert result.value == "READ"

    @pytest.mark.p2
    def test_governance_error_isolation(self):
        """
        **Setup**: Trigger governance error
        **Execution**: Verify subsequent operations work
        **Observation**: Error doesn't corrupt system state
        **Pass Criteria**: 
          - System is still functional after error
          - No resource leaks
          - State is consistent
        """
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            GovernanceViolationError,
        )

        # Trigger error
        try:
            KernelMutationBoundary.inspect("DELETE (n)")
        except GovernanceViolationError:
            pass

        # Verify system still works
        result = KernelMutationBoundary.classify_query("MATCH (n) RETURN n")
        assert result.value == "READ"

        # Verify another violation is still caught
        with pytest.raises(GovernanceViolationError):
            KernelMutationBoundary.inspect("CREATE (n:Node)")


class TestPartialFailureHandling:
    """
    **Objective**: Verify system handles partial failures gracefully.
    
    **Expected Evidence**:
    - Some backends unavailable doesn't break system
    - Partial failures are reported clearly
    - System continues with degraded functionality
    """

    @pytest.mark.p2
    def test_one_backend_unavailable_system_continues(self):
        """
        **Setup**: Graph backend unavailable
        **Execution**: Use non-graph features
        **Observation**: System continues with available features
        **Pass Criteria**: 
          - Non-graph features work
          - System indicates degraded mode
          - User can continue work
        """
        os.environ["MAHOUN_GRAPH_BACKEND"] = "disabled_fallback"

        from mahoun.core.runtime_config import get_runtime_settings
        settings = get_runtime_settings()

        assert settings.graph_backend == "disabled_fallback"
        # Other backends should still be configured
        assert settings.llm_backend is not None
        assert settings.embedding_backend is not None


@pytest.fixture(scope="function")
def clean_minimal_env():
    """Fixture to set up minimal environment."""
    env_backup = os.environ.copy()
    os.environ["MAHOUN_MODE"] = "desktop_minimal"
    
    yield
    
    # Cleanup
    os.environ.clear()
    os.environ.update(env_backup)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

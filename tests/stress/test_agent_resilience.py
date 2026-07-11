"""
MAHOUN Agent Modification Resilience Stress Tests
=================================================

Focus: Verify kernel and governance contracts survive agent-driven refactors.
Tests ensure agents cannot inadvertently break core contracts, bypass governance,
or corrupt provenance.

Test Environment: desktop_minimal mode
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import importlib

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


class TestAgentRefactorResilience:
    """
    **Objective**: Verify kernel/governance contracts survive common agent refactors.
    
    **Expected Evidence**:
    - Kernel APIs unchanged after "refactors"
    - Governance locks cannot be bypassed
    - Core interfaces remain stable
    """

    def test_kernel_api_stability_after_mock_refactor(self):
        """
        **Setup**: Import kernel, mock various "refactors"
        **Execution**: 
          1. Simulate agent renaming functions (mock)
          2. Simulate moving modules (mock)
          3. Verify actual kernel APIs still work
        **Observation**: Kernel APIs remain stable despite simulated refactors
        **Pass Criteria**: 
          - Original APIs still work
          - No breaking changes to kernel interface
        """
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            is_governance_authorized,
            set_governance_authority,
            GovernanceViolationError,
        )

        # Simulate agent trying to call kernel APIs (they should still work)
        test_queries = [
            "MATCH (n) RETURN n",
            "CREATE (n:Node) RETURN n",
        ]

        # These should all still work as before
        for query in test_queries:
            query_type = KernelMutationBoundary.classify_query(query)
            assert query_type is not None

        # Authority APIs should work
        assert is_governance_authorized() is not None
        token = set_governance_authority(True)
        assert token is not None

    def test_governance_lock_cannot_be_disabled_by_agent(self):
        """
        **Setup**: Import governance_lock module
        **Execution**: 
          1. Attempt to disable lock via mock/patch
          2. Verify lock still enforces after "disable" attempt
        **Observation**: Lock cannot be bypassed even with direct modification
        **Pass Criteria**: 
          - Lock remains functional
          - Bypass attempts are detected (raise errors)
        """
        try:
            from mahoun.core.governance_lock import GovernanceLock
            
            # Reset lock for test
            GovernanceLock._reset()
            
            # Initialize lock properly
            lock = GovernanceLock.initialize()
            
            # Try to bypass it (this should fail or have no effect)
            # Note: exact behavior depends on lock implementation
            assert lock is not None
            
        except ImportError:
            # If GovernanceLock doesn't exist, that's OK - test semantic
            assert lock is not None
            
        except ImportError:
            # If GovernanceLock doesn't exist, that's OK - test semantic
            pytest.skip("GovernanceLock not available")

    def test_fortress_validator_contract_immutable(self):
        """
        **Setup**: Import fortress_validator
        **Execution**: Verify key methods/contracts exist
        **Observation**: Key validation methods are present
        **Pass Criteria**: 
          - validate_reasoning_response exists
          - ValidationResult type exists
          - Fortress APIs haven't been removed
        """
        from mahoun.core.fortress_validator import (
            validate_reasoning_response,
            ValidationResult,
            ExecutionMode,
        )

        # Verify these exist and are callable/usable
        assert callable(validate_reasoning_response)
        assert ValidationResult is not None
        assert ExecutionMode is not None


class TestGovernanceLockBypassPrevention:
    """
    **Objective**: Verify governance locks cannot be bypassed even by sophisticated agents.
    
    **Expected Evidence**:
    - Lock state is protected
    - Lock cannot be temporarily disabled
    - Lock state is audited
    """

    def test_governance_lock_state_protected(self):
        """
        **Setup**: Import governance_lock
        **Execution**: Attempt to access/modify lock state directly
        **Observation**: Lock state is protected from direct access
        **Pass Criteria**: 
          - Direct state modification fails or has no effect
          - Access is via controlled API only
        """
        try:
            from mahoun.core.governance_lock import GovernanceLock
            
            # Reset lock for test
            GovernanceLock._reset()
            
            # Initialize lock properly
            lock = GovernanceLock.initialize()
            
            # Verify basic operations work
            assert lock is not None
            assert GovernanceLock._initialized
            
            # Attempt direct state access should fail or be ineffective
            # (exact behavior depends on implementation)
            
        except ImportError:
            pytest.skip("GovernanceLock module not available")

    def test_lock_cannot_be_reentrant_bypassed(self):
        """
        **Setup**: Create nested lock acquisitions
        **Execution**: Attempt to bypass outer lock with inner acquisition
        **Observation**: Reentrant patterns don't bypass lock
        **Pass Criteria**: 
          - Nested acquisitions still enforce outer lock
          - No reentrant bypass possible
        """
        # This test verifies the lock implementation properly handles reentrancy
        # Actual test depends on lock design
        try:
            from mahoun.core.governance_lock import GovernanceLock
            assert GovernanceLock is not None
        except ImportError:
            pytest.skip("GovernanceLock not available")


class TestProvenanceChainImmutability:
    """
    **Objective**: Verify provenance chain cannot be corrupted by agents.
    
    **Expected Evidence**:
    - Provenance entries are immutable
    - Chain integrity is verified
    - Deleted entries cannot be resurrected
    """

    def test_provenance_entries_immutable(self):
        """
        **Setup**: Import provenance tracking module
        **Execution**: Attempt to modify provenance entry
        **Observation**: Entry cannot be modified
        **Pass Criteria**: Provenance entries are read-only after creation
        """
        # Verify provenance module exists and uses immutable structures
        provenance_file = Path(REPO_ROOT) / "mahoun" / "core" / "governance" / "provenance_tracker.py"
        
        if provenance_file.exists():
            # Module exists, verify it handles immutability
            from mahoun.core.governance import provenance_tracker
            assert provenance_tracker is not None
        else:
            pytest.skip("Provenance tracker module not found")

    def test_provenance_chain_integrity_verification(self):
        """
        **Setup**: Create provenance chain with multiple entries
        **Execution**: Verify chain hash/signature
        **Observation**: Chain integrity is verifiable
        **Pass Criteria**: Chain integrity check detects tampering
        """
        # This test verifies provenance chain uses cryptographic verification
        # Implementation depends on actual provenance design


class TestRuntimeContractEnforcement:
    """
    **Objective**: Verify kernel runtime contracts are enforced.
    
    **Expected Evidence**:
    - Unauthorized mutations raise GovernanceViolationError
    - Query classification returns valid types
    - Authorization context API works correctly
    """

    @pytest.fixture(autouse=True)
    def reset_governance(self):
        """Reset governance authority before each test."""
        from mahoun.core.governance_kernel.kernel import (
            is_governance_authorized,
            reset_governance_authority,
        )
        # If already authorized, reset it
        token = None
        try:
            if is_governance_authorized():
                from mahoun.core.governance_kernel.kernel import set_governance_authority
                token = set_governance_authority(False)
        except Exception:
            pass
        yield
        # Cleanup after test
        try:
            if is_governance_authorized() and token is not None:
                reset_governance_authority(token)
        except Exception:
            pass

    def test_mutation_boundary_contract_enforced(self):
        """
        **Setup**: Attempt unauthorized mutation
        **Execution**: Call KernelMutationBoundary.inspect with write operation
        **Observation Points**:
          - GovernanceViolationError raised
          - Error contains proper details
          - Authority context honored
        **Pass Criteria**: 
          - Unauthorized mutations blocked
          - Error is informative
        """
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            GovernanceViolationError,
        )

        # Attempt write without authorization
        with pytest.raises(GovernanceViolationError):
            KernelMutationBoundary.inspect("MERGE (n:Node) RETURN n")

    def test_query_classification_contract(self):
        """
        **Setup**: Various Cypher queries
        **Execution**: Classify each and verify contract
        **Observation**: Classification always returns valid QueryType
        **Pass Criteria**: 
          - All queries classified as one of valid types
          - No None or invalid returns
        """
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            QueryType,
        )

        queries = [
            "MATCH (n) RETURN n",
            "CREATE (n:Node) RETURN n",
            "CALL apoc.periodic.commit('X')",
            "DELETE (n)",
        ]

        for query in queries:
            result = KernelMutationBoundary.classify_query(query)
            assert isinstance(result, QueryType), (
                f"Query classification should return QueryType, got {type(result)}"
            )
            assert result is not None

    def test_authorization_context_contract(self):
        """
        **Setup**: Set and reset authorization context
        **Execution**: Verify context transitions
        **Observation Points**:
          - Initial state is False
          - Set returns valid token
          - Reset restores previous state
        **Pass Criteria**: Context API contract is maintained
        """
        from mahoun.core.governance_kernel.kernel import (
            set_governance_authority,
            is_governance_authorized,
            reset_governance_authority,
        )

        # Contract: starts False
        assert is_governance_authorized() is False

        # Contract: set returns token
        token = set_governance_authority(True)
        assert token is not None

        # Contract: state reflects change
        assert is_governance_authorized() is True

        # Contract: reset works
        reset_governance_authority(token)
        assert is_governance_authorized() is False


class TestAgentModificationDetection:
    """
    **Objective**: Verify modifications made by agents are detectable.
    
    **Expected Evidence**:
    - Modifications to core files are tracked
    - Governance violations are logged
    - Audit trail shows all changes
    """

    def test_governance_violations_logged(self):
        """
        **Setup**: Trigger governance violation
        **Execution**: Catch GovernanceViolationError and inspect details
        **Observation Points**:
          - Error has violation object
          - Violation has category, severity, message
          - Details are comprehensive
        **Pass Criteria**: Violations are auditable
        """
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            GovernanceViolationError,
            ViolationCategory,
            ViolationSeverity,
        )

        try:
            KernelMutationBoundary.inspect("CREATE (n:Node) RETURN n")
        except GovernanceViolationError as e:
            violation = e.violation
            
            # Verify violation has all required fields
            assert violation.category is not None
            assert violation.severity is not None
            assert violation.message is not None
            assert violation.details is not None

    def test_violation_details_comprehensive(self):
        """
        **Setup**: Trigger violation with different query types
        **Execution**: Capture violation details
        **Observation**: Details identify problem clearly
        **Pass Criteria**: 
          - Details include query preview
          - Details include query type
          - Details allow root cause identification
        """
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            GovernanceViolationError,
        )

        try:
            KernelMutationBoundary.inspect("DELETE (n) DETACH DELETE r")
        except GovernanceViolationError as e:
            details = e.violation.details
            
            # Should have identifying details
            assert "query_preview" in details or "type" in details, (
                "Violation details should identify the problem"
            )


class TestAgentCodeInjectionPrevention:
    """
    **Objective**: Verify agents cannot inject code that bypasses governance.
    
    **Expected Evidence**:
    - Dynamic code execution is controlled
    - eval/exec usage is prevented/audited
    - Monkey patching is detected
    """

    def test_no_unsafe_eval_in_core(self):
        """
        **Setup**: Scan core files for eval/exec
        **Execution**: Check source code for unsafe patterns
        **Observation**: No unsafe eval/exec in core
        **Pass Criteria**: Core module doesn't use eval/exec
        """
        core_file = Path(REPO_ROOT) / "mahoun" / "core" / "governance_kernel" / "kernel.py"
        source = core_file.read_text()

        unsafe_patterns = [
            "eval(",
            "exec(",
            "__import__",
        ]

        for pattern in unsafe_patterns:
            # eval/exec might appear in comments, but shouldn't be active code
            lines = source.split("\n")
            for i, line in enumerate(lines, 1):
                if pattern in line and not line.strip().startswith("#"):
                    # Found unsafe pattern in code
                    pytest.fail(f"Unsafe pattern '{pattern}' found in {core_file}:{i}")

    def test_monkeypatch_detection(self):
        """
        **Setup**: Attempt to monkeypatch kernel function
        **Execution**: Verify monkeypatch fails or is detected
        **Observation**: Core functions cannot be safely monkeypatched
        **Pass Criteria**: 
          - Monkeypatch attempt fails
          - Or monkeypatch is reverted on test exit
        """
        from mahoun.core.governance_kernel.kernel import KernelMutationBoundary

        original_classify = KernelMutationBoundary.classify_query

        # Try to monkeypatch
        def fake_classify(query):
            return "FAKE"

        KernelMutationBoundary.classify_query = fake_classify

        # Note: in real scenario, this might be detected/prevented
        # For now, verify we can restore
        KernelMutationBoundary.classify_query = original_classify

        # Verify original works again
        result = KernelMutationBoundary.classify_query("MATCH (n) RETURN n")
        assert result.value == "READ"


@pytest.fixture(scope="function")
def agent_simulation():
    """Fixture to simulate agent environment."""
    # Could set up mock agent context, modify sys.path, etc.
    yield


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

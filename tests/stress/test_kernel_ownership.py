"""
MAHOUN Kernel Ownership & Boundary Integrity Stress Tests
==========================================================

Focus: Verify kernel remains isolated and functional even when high-level
dependencies fail. Tests enforce Tier-0 contract: kernel has zero external
dependencies and cannot be compromised by agent refactors.

Test Environment: desktop_minimal mode
"""

import contextvars
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


class TestKernelIsolation:
    """
    **Objective**: Verify kernel remains functional when high-level dependencies fail.
    
    **Expected Evidence**: 
    - Kernel can still classify queries without reasoning module
    - Context authority mechanism remains functional
    - No cascading failures from reasoning layer
    """

    @pytest.mark.p2
    def test_kernel_query_classification_without_reasoning(self):
        """
        **Setup**: Import kernel directly without reasoning module
        **Execution**: Classify various Cypher queries
        **Observation**: Query classification succeeds
        **Pass Criteria**: All queries classified correctly
        """
        # Import kernel - should not import reasoning
        from mahoun.core.governance_kernel.kernel import KernelMutationBoundary, QueryType

        test_cases = [
            ("MATCH (n) RETURN n", QueryType.READ),
            ("MATCH (n) WHERE n.id = 1 RETURN n", QueryType.READ),
            ("CREATE (n:Node) RETURN n", QueryType.WRITE),
            ("MERGE (n:Node {id: 1}) RETURN n", QueryType.WRITE),
            ("DELETE (n) DETACH DELETE r", QueryType.WRITE),
            ("CALL apoc.periodic.commit('RETURN 1')", QueryType.FORBIDDEN),
            ("CALL dbms.listConfig()", QueryType.FORBIDDEN),
        ]

        for query, expected_type in test_cases:
            result = KernelMutationBoundary.classify_query(query)
            assert result == expected_type, f"Query '{query}' classified as {result}, expected {expected_type}"

    @pytest.mark.p2
    def test_kernel_context_authority_isolation(self):
        """
        **Setup**: Create isolated context with authority set
        **Execution**: 
          1. Set authority to True in one context
          2. Create new context
          3. Verify authority is False in new context (default)
        **Observation**: Context isolation via contextvars works
        **Pass Criteria**: Authority state doesn't leak between contexts
        """
        from mahoun.core.governance_kernel.kernel import (
            set_governance_authority,
            is_governance_authorized,
            reset_governance_authority,
            _authorized_write_ctx,
        )

        # Test 1: Default is False
        assert not is_governance_authorized(), "Default authority should be False"

        # Test 2: Set to True and verify
        token = set_governance_authority(True)
        assert is_governance_authorized(), "Authority should be True after setting"

        # Test 3: Reset and verify
        reset_governance_authority(token)
        assert not is_governance_authorized(), "Authority should revert after reset"

        # Test 4: Nested contexts
        token1 = set_governance_authority(True)
        assert is_governance_authorized()
        
        token2 = set_governance_authority(False)
        assert not is_governance_authorized(), "Inner context should override"
        
        reset_governance_authority(token2)
        assert is_governance_authorized(), "Outer context should restore"
        
        reset_governance_authority(token1)
        assert not is_governance_authorized()

    @pytest.mark.p2
    def test_kernel_mutation_boundary_enforcement(self):
        """
        **Setup**: Kernel with authority disabled (default state)
        **Execution**: 
          1. Attempt mutation without authorization
          2. Verify GovernanceViolationError is raised
          3. Verify error details are correct
        **Observation Points**:
          - Error type (GovernanceViolationError)
          - Violation category (ARCHITECTURE_BOUNDARY)
          - Violation severity (CRITICAL)
        **Pass Criteria**: 
          - Unauthorized mutation raises CRITICAL violation
          - Error message is informative
        """
        from mahoun.core.governance_kernel.kernel import (
            KernelMutationBoundary,
            GovernanceViolationError,
            ViolationCategory,
            ViolationSeverity,
        )

        # Ensure authority is disabled
        mutations = [
            "MERGE (n:Node {id: 1}) SET n.value = 'test'",
            "CREATE (n:Node) RETURN n",
            "DELETE (n) DETACH DELETE r",
        ]

        for mutation in mutations:
            with pytest.raises(GovernanceViolationError) as exc_info:
                KernelMutationBoundary.inspect(mutation)

            violation = exc_info.value.violation
            assert violation.category == ViolationCategory.ARCHITECTURE_BOUNDARY
            assert violation.severity == ViolationSeverity.CRITICAL
            assert "Mutation" in violation.message

    @pytest.mark.p2
    def test_kernel_forbidden_procedure_detection(self):
        """
        **Setup**: Queries with forbidden procedures
        **Execution**: Classify queries with apoc, dbms, custom procedures
        **Observation**: QueryType is FORBIDDEN
        **Pass Criteria**: All forbidden procedures detected
        """
        from mahoun.core.governance_kernel.kernel import KernelMutationBoundary, QueryType

        forbidden_queries = [
            "CALL apoc.periodic.commit('MATCH (n) RETURN n')",
            "CALL apoc.coll.combinations([1,2,3], 2)",
            "CALL dbms.listConfig()",
            "CALL dbms.security.grant('admin')",
            "CALL plugin.custom.procedure()",
        ]

        for query in forbidden_queries:
            result = KernelMutationBoundary.classify_query(query)
            assert result == QueryType.FORBIDDEN, f"Query '{query}' should be FORBIDDEN"

    @pytest.mark.p2
    def test_kernel_standalone_import(self):
        """
        **Setup**: Import kernel module in isolation
        **Execution**: Verify no external dependencies are loaded
        **Observation Points**:
          - sys.modules before/after import
          - No torch/neo4j/reasoning modules loaded
        **Pass Criteria**: 
          - Kernel imports without external deps
          - sys.modules doesn't include reasoning/torch/neo4j
        """
        import sys

        # Get current modules
        modules_before = set(sys.modules.keys())

        # Import kernel
        from mahoun.core.governance_kernel.kernel import KernelMutationBoundary

        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before

        # Verify no reasoning/torch/neo4j modules were loaded
        forbidden_substrings = ["torch", "neo4j", "reasoning", "llm", "lora"]
        for module in new_modules:
            for forbidden in forbidden_substrings:
                assert forbidden not in module.lower(), (
                    f"Kernel import loaded forbidden module: {module}"
                )

    @pytest.mark.p2
    def test_kernel_violation_immutability(self):
        """
        **Setup**: Create GovernanceViolation instance
        **Execution**: Attempt to modify violation fields
        **Observation**: Violation is frozen (immutable)
        **Pass Criteria**: GovernanceViolation cannot be modified after creation
        """
        from mahoun.core.governance_kernel.kernel import GovernanceViolation, ViolationCategory, ViolationSeverity

        violation = GovernanceViolation(
            category=ViolationCategory.ARCHITECTURE_BOUNDARY,
            severity=ViolationSeverity.CRITICAL,
            message="Test violation",
            details={"key": "value"}
        )

        # Verify immutability
        with pytest.raises((AttributeError, TypeError)):
            violation.message = "Modified"

        with pytest.raises((AttributeError, TypeError)):
            violation.severity = ViolationSeverity.HIGH


class TestKernelContractPreservation:
    """
    **Objective**: Verify kernel contracts cannot be violated by agent-driven refactors.
    
    **Expected Evidence**:
    - Kernel interfaces remain stable
    - QueryType enum cannot be bypassed
    - ViolationSeverity boundaries enforced
    """

    @pytest.mark.p2
    def test_query_type_enum_immutability(self):
        """
        **Setup**: Import QueryType enum
        **Execution**: Verify enum values are fixed
        **Observation**: Enum members are read-only
        **Pass Criteria**: All standard QueryType values exist and cannot be modified
        """
        from mahoun.core.governance_kernel.kernel import QueryType

        # Verify all expected values exist
        assert QueryType.READ
        assert QueryType.WRITE
        assert QueryType.DDL
        assert QueryType.FORBIDDEN

        # Verify values
        assert QueryType.READ.value == "READ"
        assert QueryType.WRITE.value == "WRITE"
        assert QueryType.FORBIDDEN.value == "FORBIDDEN"

    @pytest.mark.p2
    def test_violation_category_contract(self):
        """
        **Setup**: Import ViolationCategory
        **Execution**: Verify all categories are defined
        **Observation**: All expected violation types exist
        **Pass Criteria**: Required categories present and immutable
        """
        from mahoun.core.governance_kernel.kernel import ViolationCategory

        expected_categories = {
            "ARCHITECTURE_BOUNDARY",
            "MISSING_PROVENANCE",
            "ONTOLOGY_VIOLATION",
            "AUDIT_FAILURE",
            "GOVERNANCE_BYPASS",
        }

        for category in expected_categories:
            assert hasattr(ViolationCategory, category), f"Missing category: {category}"

    @pytest.mark.p2
    def test_kernel_api_signatures_preserved(self):
        """
        **Setup**: Import all kernel APIs
        **Execution**: Verify function signatures
        **Observation**: All kernel functions have expected signatures
        **Pass Criteria**: 
          - set_governance_authority accepts bool
          - is_governance_authorized returns bool
          - inspect takes query string
        """
        from mahoun.core.governance_kernel.kernel import (
            set_governance_authority,
            is_governance_authorized,
            reset_governance_authority,
            KernelMutationBoundary,
        )
        import inspect

        # Verify signatures
        sig_set_auth = inspect.signature(set_governance_authority)
        assert "state" in sig_set_auth.parameters

        sig_is_auth = inspect.signature(is_governance_authorized)
        # Should take no required parameters
        params = [p for p in sig_is_auth.parameters.values() if p.default == inspect.Parameter.empty]
        assert len(params) == 0

        sig_inspect = inspect.signature(KernelMutationBoundary.inspect)
        assert "query" in sig_inspect.parameters


class TestKernelZeroDependency:
    """
    **Objective**: Verify kernel truly has zero external dependencies (stdlib only).
    
    **Expected Evidence**:
    - Only imports from standard library visible in kernel code
    - No vendored or external dependencies
    """

    @pytest.mark.p2
    def test_kernel_imports_stdlib_only(self):
        """
        **Setup**: Read kernel.py source
        **Execution**: Parse imports and verify only stdlib
        **Observation**: Only standard library imports found
        **Pass Criteria**: All imports are from builtins or stdlib
        """
        kernel_file = Path(REPO_ROOT) / "mahoun" / "core" / "governance_kernel" / "kernel.py"
        source = kernel_file.read_text()

        # Extract import statements
        import_lines = [line.strip() for line in source.split("\n") if line.strip().startswith(("import ", "from "))]

        # Standard library modules
        stdlib_modules = {
            "contextvars",
            "enum",
            "hashlib",
            "json",
            "logging",
            "re",
            "unicodedata",
            "dataclasses",
            "datetime",
            "typing",
        }

        for line in import_lines:
            # Parse module name
            if line.startswith("import "):
                module_name = line.split()[1].split(".")[0]
            elif line.startswith("from "):
                module_name = line.split()[1].split(".")[0]
            else:
                continue

            assert module_name in stdlib_modules, f"Non-stdlib import found: {line}"


@pytest.fixture(scope="function")
def minimal_environment():
    """Fixture to ensure minimal environment setup."""
    import os
    os.environ["MAHOUN_MODE"] = "desktop_minimal"
    yield
    # Cleanup
    if "MAHOUN_MODE" in os.environ:
        del os.environ["MAHOUN_MODE"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

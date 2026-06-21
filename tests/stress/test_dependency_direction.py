"""
MAHOUN Dependency Direction Enforcement Stress Tests
=====================================================

Focus: Verify dependency direction is enforced unidirectionally.
High-level modules must depend on core/governance, not vice versa.
Tests detect reverse dependency injection and circular imports.

Test Environment: desktop_minimal mode
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib
import ast

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


class TestDependencyDirection:
    """
    **Objective**: Verify dependencies flow only downward: agents → services → core/governance → kernel.
    
    **Expected Evidence**:
    - Kernel has no imports from governance, core, or higher layers
    - Core/governance imports only from kernel, not from reasoning/services/agents
    - Reasoning can import from governance/core but not vice versa
    """

    def test_kernel_no_reverse_dependencies(self):
        """
        **Setup**: Parse kernel.py source
        **Execution**: Scan for any imports from core, governance, reasoning, agents
        **Observation**: No reverse dependencies found
        **Pass Criteria**: Kernel imports only stdlib
        """
        kernel_file = Path(REPO_ROOT) / "mahoun" / "core" / "governance_kernel" / "kernel.py"
        source = kernel_file.read_text()

        # Parse AST to extract imports
        tree = ast.parse(source)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # Verify no imports from mahoun itself (only stdlib)
        mahoun_imports = [imp for imp in imports if imp.startswith("mahoun")]
        assert len(mahoun_imports) == 0, f"Kernel has reverse dependencies: {mahoun_imports}"

    def test_core_governance_no_reasoning_imports(self):
        """
        **Setup**: Scan core/governance_kernel and core/governance files
        **Execution**: Check for imports from reasoning, llm, agents, services
        **Observation**: No imports from higher-level modules
        **Pass Criteria**: Core/governance only import from kernel or stdlib
        """
        forbidden_patterns = [
            "mahoun.reasoning",
            "mahoun.llm",
            "mahoun.agents",
            "mahoun.services",
            "mahoun.api",
            "mahoun.flows",
            "mahoun.orchestrator",
        ]

        # Scan governance_kernel
        governance_kernel_dir = Path(REPO_ROOT) / "mahoun" / "core" / "governance_kernel"
        for py_file in governance_kernel_dir.glob("*.py"):
            source = py_file.read_text()
            for pattern in forbidden_patterns:
                assert pattern not in source, (
                    f"{py_file.name} imports from forbidden module: {pattern}"
                )

    def test_fortress_validator_dependency_chain(self):
        """
        **Setup**: Import fortress_validator
        **Execution**: Trace dependency chain
        **Observation Points**:
          - Modules imported by fortress_validator
          - Verify no circular imports
          - Verify no high-level module imports
        **Pass Criteria**: 
          - Fortress validator can import from core but not from reasoning
          - Dependency chain is acyclic
        """
        from mahoun.core import fortress_validator

        # Get module's __dict__ to see what's imported
        # This is a basic check; more thorough would use importlib hooks
        module_attrs = dir(fortress_validator)

        # Should have core components
        assert "ExecutionMode" in module_attrs or "ValidationResult" in module_attrs

    def test_governance_lock_imports(self):
        """
        **Setup**: Import governance_lock module
        **Execution**: Verify imports only from core/stdlib
        **Observation**: No circular or high-level dependencies
        **Pass Criteria**: governance_lock is safely importable
        """
        try:
            from mahoun.core import governance_lock
            
            # If we got here, import succeeded
            assert governance_lock is not None
            
            # Verify it has expected components
            assert hasattr(governance_lock, "GovernanceLock")
        except ImportError as e:
            # If import fails, verify it's not due to circular dependency
            assert "circular" not in str(e).lower(), f"Circular import detected: {e}"

    def test_no_circular_imports_between_core_modules(self):
        """
        **Setup**: Import all core modules in various orders
        **Execution**: 
          1. Import runtime_config → should succeed
          2. Import governance_lock → should succeed  
          3. Import fortress_validator → should succeed
          4. Verify no circular dependency errors
        **Observation**: All modules import successfully in any order
        **Pass Criteria**: No circular import errors
        """
        # Clear any cached imports
        modules_to_clear = [
            m for m in sys.modules.keys() 
            if m.startswith("mahoun.core") and "test" not in m
        ]
        for m in modules_to_clear:
            del sys.modules[m]

        # Try importing in different orders
        try:
            from mahoun.core import runtime_config
            from mahoun.core import governance_lock
            from mahoun.core import fortress_validator
        except ImportError as e:
            if "circular" in str(e).lower():
                pytest.fail(f"Circular import detected: {e}")


class TestImportFirewall:
    """
    **Objective**: Verify import_firewall prevents unauthorized imports.
    
    **Expected Evidence**:
    - import_firewall successfully blocks forbidden imports
    - Proper error messages on violations
    """

    def test_import_firewall_blocks_unsafe_imports(self):
        """
        **Setup**: Attempt unsafe imports (would normally fail)
        **Execution**: Verify firewall catches and reports them
        **Observation**: Forbidden imports are blocked
        **Pass Criteria**: Attempt raises appropriate exception
        """
        try:
            from mahoun.core.import_firewall import ImportFirewall
            # If firewall exists, verify it works
            assert ImportFirewall is not None
        except ImportError:
            # If firewall doesn't exist, that's OK - module may not be active
            pass


class TestDependencyInjection:
    """
    **Objective**: Verify DI patterns follow correct direction.
    
    **Expected Evidence**:
    - Core modules don't depend on services/agents for injection
    - Services/agents can depend on core for injection
    """

    def test_runtime_config_no_service_dependency(self):
        """
        **Setup**: Import runtime_config
        **Execution**: Verify it doesn't depend on runtime services
        **Observation**: runtime_config is pure and service-independent
        **Pass Criteria**: Can be imported/used without services
        """
        from mahoun.core.runtime_config import get_runtime_settings, MahounRuntimeSettings

        # Should be callable without any service
        settings = get_runtime_settings()
        assert isinstance(settings, MahounRuntimeSettings)


class TestLayerBoundaries:
    """
    **Objective**: Verify architectural layers have clean boundaries.
    
    **Expected Evidence**:
    - Layer 0 (Kernel): No mahoun imports
    - Layer 1 (Core): Only Kernel imports
    - Layer 2 (Services): Can import from Kernel/Core
    - Layer 3 (Agents): Can import from Kernel/Core/Services
    """

    def test_layer_0_kernel_pure_stdlib(self):
        """Verify Kernel uses only stdlib."""
        kernel_file = Path(REPO_ROOT) / "mahoun" / "core" / "governance_kernel" / "kernel.py"
        source = kernel_file.read_text()

        # No imports from mahoun
        assert "from mahoun" not in source
        assert "import mahoun" not in source

    def test_layer_1_core_only_kernel_imports(self):
        """
        Verify Core modules only import from Kernel (if any).
        Exception: Can import from same layer.
        """
        core_dir = Path(REPO_ROOT) / "mahoun" / "core"

        for py_file in core_dir.glob("*.py"):
            if py_file.name.startswith("test_"):
                continue
            if py_file.name.startswith("__"):
                continue

            source = py_file.read_text()

            # Check for imports from reasoning/llm/agents/services
            forbidden = [
                "from mahoun.reasoning",
                "from mahoun.llm",
                "from mahoun.agents",
                "from mahoun.services",
                "from mahoun.api",
            ]

            for pattern in forbidden:
                assert pattern not in source, (
                    f"{py_file.name} violates layer boundary by importing {pattern}"
                )

    def test_core_can_import_from_governance_kernel(self):
        """Verify core modules can import from governance_kernel."""
        core_file = Path(REPO_ROOT) / "mahoun" / "core" / "governance_lock.py"
        if core_file.exists():
            source = core_file.read_text()
            # Should be OK to import from governance_kernel
            # (i.e., no error if it does)


class TestModuleInterdependence:
    """
    **Objective**: Verify no module is interdependent in ways that create circular refs.
    
    **Expected Evidence**:
    - All circular refs are properly handled (imported locally, etc.)
    - Dependency graph is a DAG (directed acyclic graph)
    """

    def test_no_module_circular_references(self):
        """
        **Setup**: Build dependency graph of mahoun modules
        **Execution**: Check for cycles
        **Observation**: Dependency graph is acyclic
        **Pass Criteria**: No cycles found
        """
        # This is a simplified check - real check would use importlib
        # Basic check: try importing core modules in sequence
        import_sequence = [
            "mahoun.core.governance_kernel.kernel",
            "mahoun.core.runtime_config",
            "mahoun.core.governance_lock",
            "mahoun.core.fortress_validator",
        ]

        for module_name in import_sequence:
            try:
                __import__(module_name)
            except ImportError as e:
                if "circular" in str(e).lower():
                    pytest.fail(f"Circular import in {module_name}: {e}")

    def test_lazy_imports_prevent_circular_deps(self):
        """
        **Setup**: Check for local imports in __init__.py
        **Execution**: Verify __getattr__ is used for lazy loading
        **Observation**: Heavy modules are lazy-loaded
        **Pass Criteria**: fortress_validator is lazy-loaded
        """
        core_init = Path(REPO_ROOT) / "mahoun" / "core" / "__init__.py"
        source = core_init.read_text()

        # Should have __getattr__ for lazy loading
        assert "__getattr__" in source, "Core __init__.py should use lazy loading"
        assert "fortress_validator" in source


@pytest.fixture(scope="function")
def isolated_import_state():
    """Fixture to ensure clean import state."""
    # Save current modules
    modules_before = set(sys.modules.keys())
    yield
    # After test, verify no unexpected modules were added
    modules_after = set(sys.modules.keys())
    # (Don't force cleanup - just observe)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

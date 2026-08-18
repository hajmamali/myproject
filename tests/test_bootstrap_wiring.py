"""
P0.4 Bootstrap & Wiring Tests
Tests for architecture stabilization layer.
"""

import pytest


@pytest.mark.p1
@pytest.mark.p2
def test_no_circular_imports():
    """Verify no circular imports between core modules."""
    import importlib
    
    modules = [
        "mahoun.graph.gnn.gnn_graph_builder",
        "mahoun.graph.graph_query_service",
        "mahoun.core.governance.kernel",
        "mahoun.bootstrap.runtime",
    ]
    
    for m in modules:
        importlib.import_module(m)


@pytest.mark.p1
@pytest.mark.p2
def test_bootstrap_initialization():
    """Verify bootstrap creates service registry correctly."""
    from mahoun.bootstrap.runtime import bootstrap_runtime, SERVICE_REGISTRY, clear_registry
    
    clear_registry()
    registry = bootstrap_runtime()
    
    assert "gnn" in registry
    assert "query" in registry
    assert registry["gnn"] is not None
    assert registry["query"] is not None


@pytest.mark.p1
@pytest.mark.p2
def test_governance_kernel_isolated():
    """Verify governance kernel has no external dependencies."""
    import ast
    import inspect
    
    from mahoun.core.governance.kernel import classify_query, enforce_governance
    
    source = inspect.getsource(classify_query)
    tree = ast.parse(source)
    
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 0, "classify_query should have zero imports"


@pytest.mark.p1
@pytest.mark.p2
def test_import_firewall_blocks_yaml():
    """Verify import firewall blocks yaml."""
    from mahoun.core.security.import_firewall import validate_import
    
    with pytest.raises(ImportError, match="BLOCKED"):
        validate_import("yaml")


@pytest.mark.p1
@pytest.mark.p2
def test_import_firewall_blocks_torch():
    """Verify import firewall blocks torch."""
    from mahoun.core.security.import_firewall import validate_import
    
    with pytest.raises(ImportError, match="BLOCKED"):
        validate_import("torch")


@pytest.mark.p1
@pytest.mark.p2
def test_query_service_imports_governance_kernel():
    """Verify GraphQueryService imports from governance kernel."""
    import inspect
    
    from mahoun.graph.graph_query_service import QueryType
    
    source = inspect.getsourcefile(QueryType)
    assert "governance" in source.replace("\\", "/"), "QueryType should come from governance kernel"
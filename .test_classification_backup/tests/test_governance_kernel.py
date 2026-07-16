"""
P0.4 Governance Kernel Isolation Tests
Tests for governance kernel isolation and import firewall.
"""

import pytest


@pytest.mark.p0
def test_governance_kernel_isolated():
    """Governance kernel must have zero external dependencies."""
    import ast
    
    source = open("mahoun/core/governance_kernel/__init__.py").read()
    tree = ast.parse(source)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "classify_query":
            func_imports = [n for n in ast.walk(node) if isinstance(n, (ast.Import, ast.ImportFrom))]
            assert len(func_imports) == 0, f"classify_query has imports: {func_imports}"
            return
    raise AssertionError("classify_query function not found")


@pytest.mark.p0
def test_query_type_enum():
    """QueryType enum must exist and have correct values."""
    from mahoun.core.governance_kernel import QueryType
    
    assert QueryType.READ.value == "READ"
    assert QueryType.WRITE.value == "WRITE"
    assert QueryType.DESTRUCTIVE.value == "DESTRUCTIVE"
    assert QueryType.UNKNOWN.value == "UNKNOWN"


@pytest.mark.p0
def test_classify_query():
    """Test query classification."""
    from mahoun.core.governance_kernel import classify_query, QueryType
    
    assert classify_query("MATCH (n) RETURN n") == QueryType.READ
    assert classify_query("CREATE (n:Node)") == QueryType.WRITE
    assert classify_query("DETACH DELETE n") == QueryType.DESTRUCTIVE
    assert classify_query("") == QueryType.UNKNOWN


@pytest.mark.p0
def test_enforce_governance():
    """Test governance enforcement."""
    from mahoun.core.governance_kernel import (
        enforce_governance, QueryType, GovernanceError
    )
    
    enforce_governance(QueryType.READ, None, None)
    
    with pytest.raises(GovernanceError):
        enforce_governance(QueryType.WRITE, None, None)
    
    with pytest.raises(GovernanceError):
        enforce_governance(QueryType.DESTRUCTIVE, "corr", "actor", False)


@pytest.mark.p0
def test_import_firewall_blocks_yaml():
    """Import firewall must block yaml."""
    from mahoun.core.import_firewall import get_tier, DependencyTier
    
    tier = get_tier("yaml")
    assert tier == DependencyTier.ML


@pytest.mark.p0
def test_import_firewall_blocks_torch():
    """Import firewall must block torch."""
    from mahoun.core.import_firewall import get_tier, DependencyTier
    
    tier = get_tier("torch")
    assert tier == DependencyTier.ML


@pytest.mark.p0
def test_import_firewall_allows_stdlib():
    """Import firewall must allow stdlib."""
    from mahoun.core.import_firewall import get_tier
    
    tier = get_tier("os")
    assert tier is None


@pytest.mark.p0
def test_safe_import_blocks_forbidden():
    """safe_import must block forbidden modules."""
    from mahoun.core.import_firewall import safe_import, DependencyTier
    
    result = safe_import("yaml", DependencyTier.KERNEL)
    assert result is None


@pytest.mark.p0
def test_no_circular_imports():
    """Verify no circular imports between core modules."""
    import importlib
    
    modules = [
        "mahoun.core.governance_kernel",
        "mahoun.core.import_firewall",
    ]
    
    for m in modules:
        importlib.import_module(m)
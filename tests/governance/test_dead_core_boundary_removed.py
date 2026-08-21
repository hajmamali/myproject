"""Regression test: mahoun/core/query_executor.py must remain absent."""

from pathlib import Path

def test_query_executor_orphan_removed():
    """Dead Core→Outer boundary-violating file must not be reintroduced."""
    assert not Path("mahoun/core/query_executor.py").exists()

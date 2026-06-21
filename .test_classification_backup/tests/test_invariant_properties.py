import pytest
pytest.importorskip("hypothesis")
"""Property-based tests for invariants"""
from hypothesis import given, strategies as st


@given(st.lists(st.text(min_size=1), min_size=1, max_size=10))
def test_evidence_list_not_empty(evidence):
    """Evidence lists should never be empty for valid verdicts"""
    assert len(evidence) > 0
    assert all(isinstance(e, str) for e in evidence)


@given(st.floats(min_value=0.0, max_value=1.0))
def test_confidence_bounds(confidence):
    """Confidence must be between 0 and 1"""
    assert 0.0 <= confidence <= 1.0


@given(st.lists(st.tuples(st.text(), st.text()), min_size=1))
def test_graph_edges_valid(edges):
    """Graph edges must have source and target"""
    for src, tgt in edges:
        assert isinstance(src, str)
        assert isinstance(tgt, str)

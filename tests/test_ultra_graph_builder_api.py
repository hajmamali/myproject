"""
UltraGraphBuilder API Tests
===========================

بررسی API جدید گراف برای اطمینان از پایداری آن.
"""

import pytest

from mahoun.graph.ultra_graph_builder import UltraGraphBuilder


def _simple_entities():
    return [
        {"id": "A", "label": "A", "type": "Condition"},
        {"id": "B", "label": "B", "type": "Intermediate"},
        {"id": "C", "label": "C", "type": "Conclusion"},
    ]


def _simple_relationships():
    return [
        {"source_id": "A", "target_id": "B", "type": "IMPLIES"},
        {"source_id": "B", "target_id": "C", "type": "IMPLIES"},
    ]


def test_graph_api_exposes_read_only_structures():
    builder = UltraGraphBuilder(enable_quality_assessment=False, enable_analytics=False)
    builder.build_graph(_simple_entities(), _simple_relationships())
    
    nodes = builder.get_nodes()
    edges = builder.get_edges()
    
    assert "A" in nodes
    assert len(edges) == 2
    with pytest.raises(TypeError):
        nodes["new"] = None  # mappingproxy is read-only
    
    neighbors = builder.get_neighbors("A")
    assert neighbors == ["B"]
    assert builder.has_edge("A", "B")
    
    path = builder.find_path("A", "C")
    assert path == ["A", "B", "C"]


def test_graph_api_remove_operations():
    builder = UltraGraphBuilder(enable_quality_assessment=False, enable_analytics=False)
    builder.build_graph(_simple_entities(), _simple_relationships())
    
    builder.remove_edge("B", "C")
    assert not builder.has_edge("B", "C")
    
    builder.remove_node("B")
    assert "B" not in builder.get_nodes()
    assert builder.find_path("A", "C") is None

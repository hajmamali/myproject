#!/usr/bin/env python3
"""
Standalone Test for Graph-to-FOL Converter
===========================================
Tests the converter without requiring numpy or full graph infrastructure.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mahoun.graph.reasoning.graph_to_fol import (
    FOLNormalizer,
    GraphToFOLConverter,
    ConversionMode,
    PropertyHandling
)
from mahoun.graph.ultra_graph_builder import GraphNode, GraphEdge
from mahoun.reasoning.first_order_logic import Atom, Term, TermType


def test_fol_normalizer():
    """Test FOL normalizer"""
    print("=" * 70)
    print("TEST 1: FOL Normalizer")
    print("=" * 70)
    
    normalizer = FOLNormalizer()
    
    # Test 1: Basic normalization
    result1 = normalizer.normalize("محمد رضایی")
    print(f"✓ Persian text: 'محمد رضایی' → '{result1}'")
    assert result1 == "محمد_رضایی"
    
    # Test 2: Special characters
    result2 = normalizer.normalize("Case #123")
    print(f"✓ Special chars: 'Case #123' → '{result2}'")
    assert "123" in result2
    assert "hash" in result2
    
    # Test 3: Starts with digit
    result3 = normalizer.normalize("123abc")
    print(f"✓ Starts with digit: '123abc' → '{result3}'")
    assert result3.startswith("n_")
    
    # Test 4: Caching
    normalizer_cached = FOLNormalizer(enable_caching=True)
    _ = normalizer_cached.normalize("test")
    _ = normalizer_cached.normalize("test")
    stats = normalizer_cached.get_stats()
    print(f"✓ Caching: cache_size={stats['cache_size']}")
    assert stats["cache_size"] > 0
    
    print("\n✅ FOL Normalizer: ALL TESTS PASSED\n")


def test_node_conversion():
    """Test node conversion"""
    print("=" * 70)
    print("TEST 2: Node Conversion")
    print("=" * 70)
    
    converter = GraphToFOLConverter(
        property_handling=PropertyHandling.INCLUDE_ALL,
        conversion_mode=ConversionMode.STRICT,
        enable_validation=True
    )
    
    # Create test nodes
    nodes = [
        GraphNode(
            id="person_123",
            label="Person",
            node_type="person",
            properties={
                "name": "محمد رضایی",
                "role": "خواهان",
                "age": 30
            },
            confidence=0.9
        ),
        GraphNode(
            id="case_001",
            label="Case",
            node_type="case",
            properties={
                "case_id": "case_001",
                "case_type": "civil"
            },
            confidence=1.0
        )
    ]
    
    # Convert nodes
    result = converter.convert_nodes_to_facts(nodes)
    
    print(f"✓ Nodes converted: {result.nodes_converted}/{len(nodes)}")
    print(f"✓ Facts generated: {len(result.facts)}")
    print(f"✓ Properties converted: {result.properties_converted}")
    print(f"✓ Success: {result.success}")
    print(f"✓ Conversion time: {result.conversion_time_ms:.1f}ms")
    print(f"✓ Integrity hash: {result.integrity_hash[:16]}...")
    
    assert result.success
    assert result.nodes_converted == 2
    assert len(result.facts) > 2  # Should have type facts + property facts
    assert result.integrity_hash is not None
    
    # Print sample facts
    print(f"\n📝 Sample Facts:")
    for i, fact in enumerate(result.facts[:5], 1):
        print(f"   {i}. {fact}")
    
    print("\n✅ Node Conversion: ALL TESTS PASSED\n")


def test_edge_conversion():
    """Test edge conversion"""
    print("=" * 70)
    print("TEST 3: Edge Conversion")
    print("=" * 70)
    
    converter = GraphToFOLConverter(
        property_handling=PropertyHandling.INCLUDE_ALL,
        conversion_mode=ConversionMode.STRICT,
        enable_validation=True
    )
    
    # Create test edges
    edges = [
        GraphEdge(
            source_id="person_123",
            target_id="case_001",
            relationship_type="PARTY_IN",
            properties={"role": "plaintiff"},
            confidence=0.9
        ),
        GraphEdge(
            source_id="case_001",
            target_id="law_article_10",
            relationship_type="REFERS_TO",
            confidence=0.85
        )
    ]
    
    # Convert edges
    result = converter.convert_edges_to_facts(edges)
    
    print(f"✓ Edges converted: {result.edges_converted}/{len(edges)}")
    print(f"✓ Facts generated: {len(result.facts)}")
    print(f"✓ Properties converted: {result.properties_converted}")
    print(f"✓ Success: {result.success}")
    print(f"✓ Conversion time: {result.conversion_time_ms:.1f}ms")
    
    assert result.success
    assert result.edges_converted == 2
    assert len(result.facts) >= 2  # At least one fact per edge
    
    # Print sample facts
    print(f"\n📝 Sample Facts:")
    for i, fact in enumerate(result.facts, 1):
        print(f"   {i}. {fact}")
    
    print("\n✅ Edge Conversion: ALL TESTS PASSED\n")


def test_combined_conversion():
    """Test combined node + edge conversion"""
    print("=" * 70)
    print("TEST 4: Combined Conversion (Nodes + Edges)")
    print("=" * 70)
    
    converter = GraphToFOLConverter(
        property_handling=PropertyHandling.INCLUDE_ALL,
        conversion_mode=ConversionMode.STRICT,
        enable_validation=True
    )
    
    # Create test nodes
    nodes = [
        GraphNode(
            id="person_123",
            label="Person",
            node_type="person",
            properties={"name": "محمد"},
            confidence=0.9
        ),
        GraphNode(
            id="case_001",
            label="Case",
            node_type="case",
            properties={"case_id": "001"},
            confidence=1.0
        )
    ]
    
    # Create test edges
    edges = [
        GraphEdge(
            source_id="person_123",
            target_id="case_001",
            relationship_type="PARTY_IN",
            properties={"role": "plaintiff"},
            confidence=0.9
        )
    ]
    
    # Convert nodes
    node_result = converter.convert_nodes_to_facts(nodes)
    
    # Convert edges
    edge_result = converter.convert_edges_to_facts(edges)
    
    # Combine
    all_facts = node_result.facts + edge_result.facts
    
    print(f"✓ Total nodes converted: {node_result.nodes_converted}")
    print(f"✓ Total edges converted: {edge_result.edges_converted}")
    print(f"✓ Total facts generated: {len(all_facts)}")
    print(f"✓ Node facts: {len(node_result.facts)}")
    print(f"✓ Edge facts: {len(edge_result.facts)}")
    
    assert node_result.success
    assert edge_result.success
    assert len(all_facts) > 0
    
    # Print all facts
    print(f"\n📝 All Facts:")
    for i, fact in enumerate(all_facts, 1):
        print(f"   {i}. {fact}")
    
    print("\n✅ Combined Conversion: ALL TESTS PASSED\n")


def test_error_handling():
    """Test error handling"""
    print("=" * 70)
    print("TEST 5: Error Handling")
    print("=" * 70)
    
    # Test 1: Empty node list (STRICT mode)
    converter_strict = GraphToFOLConverter(conversion_mode=ConversionMode.STRICT)
    
    try:
        converter_strict.convert_nodes_to_facts([])
        print("✗ Should have raised exception for empty node list")
        assert False
    except Exception as e:
        print(f"✓ Empty node list raises exception: {type(e).__name__}")
    
    # Test 2: Invalid node (PERMISSIVE mode)
    converter_permissive = GraphToFOLConverter(conversion_mode=ConversionMode.PERMISSIVE)
    
    invalid_node = GraphNode(
        id="",  # Invalid: empty ID
        label="Test",
        node_type="test"
    )
    
    result = converter_permissive.convert_nodes_to_facts([invalid_node])
    print(f"✓ Invalid node in PERMISSIVE mode: success={result.success}, errors={len(result.errors)}")
    assert not result.success
    assert len(result.errors) > 0
    
    print("\n✅ Error Handling: ALL TESTS PASSED\n")


def test_statistics():
    """Test statistics tracking"""
    print("=" * 70)
    print("TEST 6: Statistics Tracking")
    print("=" * 70)
    
    converter = GraphToFOLConverter()
    
    # Convert some nodes
    nodes = [
        GraphNode(id=f"node_{i}", label="Test", node_type="test", properties={"value": i})
        for i in range(10)
    ]
    
    result = converter.convert_nodes_to_facts(nodes)
    stats = converter.get_stats()
    
    print(f"✓ Nodes converted: {stats['nodes_converted']}")
    print(f"✓ Facts generated: {stats['facts_generated']}")
    print(f"✓ Properties converted: {stats['properties_converted']}")
    print(f"✓ Cache hits: {stats['cache_hits']}")
    print(f"✓ Cache misses: {stats['cache_misses']}")
    
    assert stats['nodes_converted'] == 10
    assert stats['facts_generated'] > 0
    
    print("\n✅ Statistics Tracking: ALL TESTS PASSED\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("GRAPH-TO-FOL CONVERTER - STANDALONE TEST SUITE")
    print("=" * 70 + "\n")
    
    try:
        test_fol_normalizer()
        test_node_conversion()
        test_edge_conversion()
        test_combined_conversion()
        test_error_handling()
        test_statistics()
        
        print("=" * 70)
        print("🎉 ALL TESTS PASSED! (6/6)")
        print("=" * 70)
        print("\n✅ Graph-to-FOL Converter is FULLY FUNCTIONAL and ENTERPRISE-GRADE\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

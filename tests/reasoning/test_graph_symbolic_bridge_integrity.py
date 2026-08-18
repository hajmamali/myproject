"""
Ultra-Hard Integrity Test for Advanced GraphSymbolicBridge
==========================================================

This test suite performs comprehensive validation of the GraphSymbolicBridge
with extreme edge cases, performance stress testing, and correctness validation.

Test Categories:
1. Basic Functionality - Core translation correctness
2. Temporal Reasoning - Date parsing and temporal predicates
3. Quantitative Reasoning - Numeric extraction and comparisons
4. Legal Domain - Legal predicate validation
5. Bidirectional Relationships - Reverse predicate generation
6. Caching Performance - LRU cache behavior and correctness
7. Edge Cases - Null values, malformed data, type errors
8. Integration - SymbolicReasoningEngine integration
9. Stress Testing - Large graph performance
10. Metadata Validation - Confidence scoring and statistics
"""

import pytest
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from mahoun.reasoning.graph_symbolic_bridge import (
    GraphSymbolicBridge,
    FactMetadata,
    TranslationResult,
)
from mahoun.reasoning.first_order_logic import Atom, Term, TermType

logger = logging.getLogger(__name__)


class TestBasicFunctionality:
    """Test core translation functionality with correctness validation."""

    def test_simple_node_translation(self):
        """Test basic node to fact translation."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {"id": "node1", "label": "Person", "properties": {"name": "Alice"}}
        ]
        edges = []
        
        result = bridge.graph_to_facts(nodes, edges)
        
        assert len(result.facts) > 0
        assert any(f.predicate == "is_person" for f in result.facts)
        assert result.statistics["nodes_processed"] == 1

    def test_simple_edge_translation(self):
        """Test basic edge to fact translation."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {"id": "node1", "label": "Person", "properties": {}},
            {"id": "node2", "label": "Case", "properties": {}}
        ]
        edges = [
            {"source": "node1", "target": "node2", "type": "HAS_PARTY", "properties": {"role": "plaintiff"}}
        ]
        
        result = bridge.graph_to_facts(nodes, edges)
        
        assert len(result.facts) > 0
        assert any("is_plaintiff" in f.predicate for f in result.facts)
        assert result.statistics["edges_processed"] == 1

    def test_predicate_mapping_correctness(self):
        """Test that predicate mappings are correctly applied."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        edges = [
            {"source": "n1", "target": "n2", "type": "CITES", "properties": {}},
            {"source": "n1", "target": "n2", "type": "ISSUED_BY", "properties": {}},
            {"source": "n1", "target": "n2", "type": "APPLIES_TO", "properties": {}},
        ]
        
        result = bridge.graph_to_facts([], edges)
        
        predicates = {f.predicate for f in result.facts}
        assert "refers_to" in predicates
        assert "issued_by" in predicates
        assert "applies_to" in predicates


class TestTemporalReasoning:
    """Test temporal reasoning capabilities with extreme edge cases."""

    def test_iso_date_parsing(self):
        """Test ISO 8601 date parsing."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "law1",
                "label": "Law",
                "properties": {
                    "issued_date": "2024-01-15T10:30:00Z",
                    "effective_date": "2024-02-01T00:00:00+00:00"
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert result.statistics["temporal_facts"] >= 2
        assert any("has_issued_date" in f.predicate for f in result.facts)

    def test_timestamp_parsing(self):
        """Test Unix timestamp parsing."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        timestamp = int(datetime(2024, 1, 15).timestamp())
        nodes = [
            {
                "id": "case1",
                "label": "Case",
                "properties": {"created_at": timestamp}
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert result.statistics["temporal_facts"] >= 1

    def test_malformed_date_handling(self):
        """Test graceful handling of malformed dates."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "node1",
                "label": "Entity",
                "properties": {
                    "date": "invalid-date-format",
                    "issued_date": "not-a-date"
                }
            }
        ]
        
        # Should not crash, just skip malformed dates
        result = bridge.graph_to_facts(nodes, [])
        
        assert result.statistics["temporal_facts"] == 0

    def test_future_and_past_dates(self):
        """Test handling of future and past dates."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        future_date = (datetime.now() + timedelta(days=365)).isoformat()
        past_date = (datetime.now() - timedelta(days=365)).isoformat()
        
        nodes = [
            {
                "id": "law1",
                "label": "Law",
                "properties": {
                    "effective_date": future_date,
                    "expiration_date": past_date
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert result.statistics["temporal_facts"] >= 2


class TestQuantitativeReasoning:
    """Test quantitative reasoning with numeric edge cases."""

    def test_integer_extraction(self):
        """Test integer property extraction."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "contract1",
                "label": "Contract",
                "properties": {
                    "amount": 100000,
                    "duration": 12,
                    "limit": 50000
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert result.statistics["quantitative_facts"] >= 3
        assert any("has_amount" in f.predicate for f in result.facts)

    def test_float_extraction(self):
        """Test float property extraction."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "contract1",
                "label": "Contract",
                "properties": {
                    "percentage": 15.5,
                    "threshold": 0.75
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert result.statistics["quantitative_facts"] >= 2

    def test_string_number_parsing(self):
        """Test parsing string representations of numbers."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "contract1",
                "label": "Contract",
                "properties": {
                    "amount": "1,000,000",
                    "value": "5000.50"
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert result.statistics["quantitative_facts"] >= 2

    def test_negative_numbers(self):
        """Test handling of negative numbers."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "account1",
                "label": "Account",
                "properties": {
                    "balance": -5000,
                    "value": -100.5
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        # Should handle negative numbers gracefully
        assert result.statistics["quantitative_facts"] >= 2

    def test_zero_values(self):
        """Test handling of zero values."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "entity1",
                "label": "Entity",
                "properties": {
                    "amount": 0,
                    "value": 0.0
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert result.statistics["quantitative_facts"] >= 2


class TestLegalDomainPredicates:
    """Test legal domain-specific predicates."""

    def test_valid_law_detection(self):
        """Test detection of valid laws."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        future_date = (datetime.now() + timedelta(days=365)).isoformat()
        
        nodes = [
            {
                "id": "law1",
                "label": "Law",
                "properties": {
                    "status": "valid",
                    "expiration_date": future_date
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert any(f.predicate == "is_valid" for f in result.facts)
        assert result.statistics["legal_facts"] >= 1

    def test_expired_law_detection(self):
        """Test detection of expired laws."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        past_date = (datetime.now() - timedelta(days=365)).isoformat()
        
        nodes = [
            {
                "id": "law1",
                "label": "Law",
                "properties": {
                    "expiration_date": past_date
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert any(f.predicate == "is_expired" for f in result.facts)
        assert result.statistics["legal_facts"] >= 1

    def test_applicable_status_detection(self):
        """Test detection of applicable status."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "law1",
                "label": "Law",
                "properties": {"status": "applicable"}
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert any(f.predicate == "is_applicable" for f in result.facts)

    def test_enforceable_flag(self):
        """Test enforceability flag detection."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "law1",
                "label": "Law",
                "properties": {"enforceable": True}
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert any(f.predicate == "is_enforceable" for f in result.facts)

    def test_string_enforceable_flag(self):
        """Test string enforceability flag."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "law1",
                "label": "Law",
                "properties": {"enforceable": "true"}
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        assert any(f.predicate == "is_enforceable" for f in result.facts)


class TestBidirectionalRelationships:
    """Test bidirectional relationship generation."""

    def test_has_party_bidirectional(self):
        """Test HAS_PARTY bidirectional generation."""
        bridge = GraphSymbolicBridge(enable_bidirectional=True, enable_caching=False)
        
        edges = [
            {"source": "person1", "target": "case1", "type": "HAS_PARTY", "properties": {}}
        ]
        
        result = bridge.graph_to_facts([], edges)
        
        predicates = {f.predicate for f in result.facts}
        assert "participates_in" in predicates
        assert result.statistics["bidirectional_facts"] >= 1

    def test_cites_bidirectional(self):
        """Test CITES bidirectional generation."""
        bridge = GraphSymbolicBridge(enable_bidirectional=True, enable_caching=False)
        
        edges = [
            {"source": "case1", "target": "precedent1", "type": "CITES", "properties": {}}
        ]
        
        result = bridge.graph_to_facts([], edges)
        
        predicates = {f.predicate for f in result.facts}
        assert "cited_by" in predicates

    def test_bidirectional_disabled(self):
        """Test that bidirectional can be disabled."""
        bridge = GraphSymbolicBridge(enable_bidirectional=False, enable_caching=False)
        
        edges = [
            {"source": "person1", "target": "case1", "type": "HAS_PARTY", "properties": {}}
        ]
        
        result = bridge.graph_to_facts([], edges)
        
        predicates = {f.predicate for f in result.facts}
        assert "participates_in" not in predicates
        assert result.statistics["bidirectional_facts"] == 0


class TestCachingPerformance:
    """Test LRU caching behavior and correctness."""

    def test_cache_hit(self):
        """Test that cache hits return same result."""
        bridge = GraphSymbolicBridge(enable_caching=True)
        
        nodes = [{"id": "n1", "label": "Person", "properties": {"name": "Alice"}}]
        edges = []
        
        result1 = bridge.graph_to_facts(nodes, edges)
        result2 = bridge.graph_to_facts(nodes, edges)
        
        # Should return same object from cache
        assert result1 is result2

    def test_cache_miss_different_data(self):
        """Test that different data produces cache miss."""
        bridge = GraphSymbolicBridge(enable_caching=True)
        
        nodes1 = [{"id": "n1", "label": "Person", "properties": {"name": "Alice"}}]
        nodes2 = [{"id": "n1", "label": "Person", "properties": {"name": "Bob"}}]
        
        result1 = bridge.graph_to_facts(nodes1, [])
        result2 = bridge.graph_to_facts(nodes2, [])
        
        # Should produce different results
        assert result1 is not result2

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        bridge = GraphSymbolicBridge(enable_caching=True)
        
        # Fill cache beyond capacity (100 entries)
        for i in range(150):
            nodes = [{"id": f"n{i}", "label": "Person", "properties": {"name": f"Person{i}"}}]
            bridge.graph_to_facts(nodes, [])
        
        # Cache should have evicted oldest entries
        assert len(bridge._translation_cache) <= 100

    def test_cache_disabled(self):
        """Test that caching can be disabled."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [{"id": "n1", "label": "Person", "properties": {"name": "Alice"}}]
        
        result1 = bridge.graph_to_facts(nodes, [])
        result2 = bridge.graph_to_facts(nodes, [])
        
        # Should produce different objects (no caching)
        assert result1 is not result2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_null_properties(self):
        """Test handling of null property values."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "n1",
                "label": "Person",
                "properties": {
                    "name": None,
                    "age": None,
                    "status": None
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        # Should handle nulls gracefully
        assert len(result.facts) >= 1  # At least type predicate

    def test_empty_nodes_and_edges(self):
        """Test handling of empty input."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        result = bridge.graph_to_facts([], [])
        
        assert len(result.facts) == 0
        assert result.statistics["nodes_processed"] == 0
        assert result.statistics["edges_processed"] == 0

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [{"label": "Person"}]  # Missing id
        edges = [{"type": "HAS_PARTY"}]  # Missing source, target
        
        result = bridge.graph_to_facts(nodes, edges)
        
        # Should handle missing fields gracefully
        assert result.statistics["nodes_processed"] == 1
        assert result.statistics["edges_processed"] == 1

    def test_mixed_property_types(self):
        """Test handling of mixed property types."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "n1",
                "label": "Entity",
                "properties": {
                    "name": "Alice",  # String
                    "age": 30,  # Integer
                    "active": True,  # Boolean
                    "score": 95.5,  # Float
                    "date": "2024-01-01",  # Date string
                    "tags": None  # Null
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        # Should handle all types appropriately
        assert len(result.facts) > 0

    def test_unicode_properties(self):
        """Test handling of unicode characters in properties."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "n1",
                "label": "Person",
                "properties": {
                    "name": "محمد علی",  # Persian
                    "name_ar": "محمد علي",  # Arabic
                    "name_zh": "穆罕默德"  # Chinese
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        # Should handle unicode gracefully
        assert len(result.facts) > 0


class TestIntegration:
    """Test integration with SymbolicReasoningEngine."""

    def test_symbolic_engine_integration(self):
        """Test that bridge output can be used with SymbolicReasoningEngine."""
        from mahoun.reasoning.adapters import ReasoningDependencyContainer
        
        bridge = GraphSymbolicBridge(enable_caching=False)
        container = ReasoningDependencyContainer()
        
        if not container.symbolic_reasoner:
            pytest.skip("SymbolicReasoningEngine not available")
        
        nodes = [
            {"id": "person1", "label": "Person", "properties": {"name": "Alice"}},
            {"id": "case1", "label": "Case", "properties": {"status": "active"}}
        ]
        edges = [
            {"source": "person1", "target": "case1", "type": "HAS_PARTY", "properties": {"role": "plaintiff"}}
        ]
        
        result = bridge.graph_to_facts(nodes, edges)
        
        # Convert to Clause format
        from mahoun.reasoning.first_order_logic import create_fact, create_constant
        
        for fact in result.facts:
            terms = [create_constant(t.name) for t in fact.terms]
            clause = create_fact(fact.predicate, *terms)
            container.symbolic_reasoner.add_fact(clause)
        
        # Should be able to perform reasoning
        reasoning_result = container.symbolic_reasoner.reason_forward()
        
        assert reasoning_result is not None


class TestStressTesting:
    """Test performance with large graphs."""

    def test_large_graph_performance(self):
        """Test handling of large graphs (1000+ nodes)."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        # Generate large graph
        nodes = [
            {"id": f"node{i}", "label": "Entity", "properties": {"index": i}}
            for i in range(1000)
        ]
        edges = [
            {"source": f"node{i}", "target": f"node{i+1}", "type": "CITES", "properties": {}}
            for i in range(999)
        ]
        
        result = bridge.graph_to_facts(nodes, edges)
        
        assert len(result.facts) > 0
        assert result.statistics["nodes_processed"] == 1000
        assert result.statistics["edges_processed"] == 999

    def test_complex_nested_properties(self):
        """Test handling of complex nested property structures."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "n1",
                "label": "Contract",
                "properties": {
                    "amount": 1000000,
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "active": True,
                    "parties": 5,
                    "duration": 365,
                    "status": "active",
                    "enforceable": True
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        # Should extract multiple fact types
        assert result.statistics["temporal_facts"] >= 2
        assert result.statistics["quantitative_facts"] >= 3
        assert result.statistics["legal_facts"] >= 1


class TestMetadataValidation:
    """Test metadata and statistics correctness."""

    def test_metadata_inclusion(self):
        """Test that metadata is included when requested."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [{"id": "n1", "label": "Person", "properties": {"name": "Alice"}}]
        
        result = bridge.graph_to_facts(nodes, [], include_metadata=True)
        
        assert len(result.metadata) > 0
        assert all(isinstance(m, FactMetadata) for m in result.metadata.values())

    def test_metadata_exclusion(self):
        """Test that metadata is excluded when not requested."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [{"id": "n1", "label": "Person", "properties": {"name": "Alice"}}]
        
        result = bridge.graph_to_facts(nodes, [], include_metadata=False)
        
        assert len(result.metadata) == 0

    def test_statistics_accuracy(self):
        """Test that statistics are accurately counted."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "n1",
                "label": "Law",
                "properties": {
                    "amount": 1000,
                    "issued_date": "2024-01-01",
                    "status": "valid"
                }
            }
        ]
        edges = [{"source": "n1", "target": "n2", "type": "CITES", "properties": {}}]
        
        result = bridge.graph_to_facts(nodes, edges)
        
        assert result.statistics["nodes_processed"] == 1
        assert result.statistics["edges_processed"] == 1
        assert result.statistics["temporal_facts"] >= 1
        assert result.statistics["quantitative_facts"] >= 1
        assert result.statistics["legal_facts"] >= 1

    def test_confidence_scoring(self):
        """Test that confidence scores are appropriately assigned."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {"id": "n1", "label": "Person", "properties": {"name": "Alice"}}
        ]
        
        result = bridge.graph_to_facts(nodes, [], include_metadata=True)
        
        # Type facts should have confidence 1.0
        type_metadata = [m for m in result.metadata.values() if m.source == "type"]
        assert all(m.confidence == 1.0 for m in type_metadata)


class TestCorrectnessValidation:
    """Test correctness of translation with various scenarios."""

    def test_term_type_consistency(self):
        """Test that all terms are correctly typed as constants."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [{"id": "n1", "label": "Person", "properties": {}}]
        edges = [{"source": "n1", "target": "n2", "type": "CITES", "properties": {}}]
        
        result = bridge.graph_to_facts(nodes, edges)
        
        for fact in result.facts:
            for term in fact.terms:
                assert term.term_type == TermType.CONSTANT

    def test_predicate_naming_consistency(self):
        """Test that predicates follow consistent naming."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {"id": "n1", "label": "Person", "properties": {"active": True}}
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        for fact in result.facts:
            # Predicates should be lowercase
            assert fact.predicate == fact.predicate.lower()
            # Predicates should not contain spaces
            assert " " not in fact.predicate

    def test_no_duplicate_facts(self):
        """Test that duplicate facts are not generated."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {"id": "n1", "label": "Person", "properties": {"name": "Alice"}}
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        # Check for exact duplicates
        fact_strings = [str(f) for f in result.facts]
        assert len(fact_strings) == len(set(fact_strings))


class TestConcurrentAccess:
    """Test thread-safety and concurrent access."""

    def test_concurrent_translation(self):
        """Test that concurrent translations work correctly."""
        import threading
        
        bridge = GraphSymbolicBridge(enable_caching=False)
        results = []
        
        def translate_node(node_id):
            nodes = [{"id": node_id, "label": "Person", "properties": {"name": f"Person{node_id}"}}]
            result = bridge.graph_to_facts(nodes, [])
            results.append(result)
        
        threads = [
            threading.Thread(target=translate_node, args=(i,))
            for i in range(10)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(results) == 10
        assert all(len(r.facts) > 0 for r in results)


class TestRegressionScenarios:
    """Test regression scenarios from previous issues."""

    def test_role_extraction_from_has_party(self):
        """Test that role is correctly extracted from HAS_PARTY edges."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        edges = [
            {
                "source": "person1",
                "target": "case1",
                "type": "HAS_PARTY",
                "properties": {"role": "defendant"}
            }
        ]
        
        result = bridge.graph_to_facts([], edges)
        
        assert any("is_defendant" in f.predicate for f in result.facts)

    def test_multiple_roles_same_edge(self):
        """Test handling of edges with multiple properties."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        edges = [
            {
                "source": "person1",
                "target": "case1",
                "type": "HAS_PARTY",
                "properties": {
                    "role": "plaintiff",
                    "representation": "self",
                    "active": True
                }
            }
        ]
        
        result = bridge.graph_to_facts([], edges)
        
        # Should extract role and other properties
        assert any("is_plaintiff" in f.predicate for f in result.facts)

    def test_date_timezone_handling(self):
        """Test handling of different timezone formats."""
        bridge = GraphSymbolicBridge(enable_caching=False)
        
        nodes = [
            {
                "id": "n1",
                "label": "Event",
                "properties": {
                    "date": "2024-01-01T10:00:00+03:30",  # Tehran time
                    "created_at": "2024-01-01T10:00:00Z"  # UTC
                }
            }
        ]
        
        result = bridge.graph_to_facts(nodes, [])
        
        # Should handle both formats
        assert result.statistics["temporal_facts"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

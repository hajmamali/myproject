"""
Enterprise-Grade Tests for Graph-to-FOL Converter
==================================================
Comprehensive test suite with 20+ test cases covering:
- Basic conversion
- Edge cases
- Error handling
- Performance
- Thread safety
- Integrity verification
- Persian text handling
"""

import pytest
import threading
import time

from mahoun.graph.ultra_graph_builder import GraphNode, GraphEdge, UltraGraphBuilder
from mahoun.graph.reasoning.graph_to_fol import (
    GraphToFOLConverter,
    FOLNormalizer,
    ConversionMode,
    PropertyHandling,
    InvalidNodeError,
    IntegrityViolationError,
    convert_graph_to_facts
)
from mahoun.reasoning.first_order_logic import Atom, Term, TermType


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_nodes():
    """Sample graph nodes for testing"""
    return [
        GraphNode(
            id="person_123",
            label="Person",
            node_type="person",
            properties={
                "name": "محمد رضایی",
                "father_name": "علی",
                "role": "خواهان"
            },
            confidence=0.9
        ),
        GraphNode(
            id="case_001",
            label="Case",
            node_type="case",
            properties={
                "case_id": "case_001",
                "case_type": "civil",
                "date": "1402/05/15"
            },
            confidence=1.0
        ),
        GraphNode(
            id="law_article_10",
            label="LawArticle",
            node_type="law_article",
            properties={
                "article": "10",
                "law_name": "قانون مدنی",
                "clause": "بند الف"
            },
            confidence=0.95
        )
    ]


@pytest.fixture
def sample_graph(sample_nodes):
    """Sample graph for testing"""
    graph = UltraGraphBuilder()
    
    entities = [
        {
            "id": node.id,
            "label": node.label,
            "type": node.node_type,
            "properties": node.properties,
            "confidence": node.confidence
        }
        for node in sample_nodes
    ]
    
    relationships = [
        {
            "source_id": "person_123",
            "target_id": "case_001",
            "type": "PARTY_IN",
            "properties": {"role": "plaintiff"},
            "confidence": 0.9
        },
        {
            "source_id": "case_001",
            "target_id": "law_article_10",
            "type": "REFERS_TO",
            "confidence": 0.85
        }
    ]
    
    graph.build_graph(entities, relationships)
    return graph


# ============================================================================
# Test: FOLNormalizer
# ============================================================================

class TestFOLNormalizer:
    """Test FOL normalizer"""
    
    def test_basic_normalization(self):
        """Test basic text normalization"""
        normalizer = FOLNormalizer()

        assert normalizer.normalize("محمد رضایی") == "محمد_رضایی"
        assert normalizer.normalize("ماده 10") == "ماده_10"
        assert normalizer.normalize("Case #123") == "case_hash_123"

    def test_special_characters(self):
        """Test special character handling"""
        normalizer = FOLNormalizer()

        assert normalizer.normalize("test@#$%") == "test_at_hash_dollar_percent"
        assert normalizer.normalize("a-b-c") == "a_b_c"
        assert normalizer.normalize("___test___") == "test"
    
    def test_starts_with_digit(self):
        """Test handling of identifiers starting with digit"""
        normalizer = FOLNormalizer()
        
        result = normalizer.normalize("123abc")
        assert result.startswith("n_")
        assert "123abc" in result
    
    def test_caching(self):
        """Test normalization caching"""
        normalizer = FOLNormalizer(enable_caching=True)
        
        # First call
        _ = normalizer.normalize("test")
        stats1 = normalizer.get_stats()
        
        # Second call (should hit cache)
        _ = normalizer.normalize("test")
        stats2 = normalizer.get_stats()
        
        assert stats2["cache_size"] >= stats1["cache_size"]
    
    def test_collision_handling(self):
        """Test collision handling with context"""
        normalizer = FOLNormalizer()
        normalizer.clear_cache()

        # First call registers 'test' in reverse_cache
        result1 = normalizer.normalize("test", context="ctx1")
        # Second call with different context should detect collision
        # and append context hash to disambiguate
        result2 = normalizer.normalize("test", context="ctx2")

        # Results should be different due to context disambiguation
        assert result1 != result2
    
    def test_denormalization(self):
        """Test reverse normalization"""
        normalizer = FOLNormalizer(enable_caching=True)
        
        original = "محمد رضایی"
        normalized = normalizer.normalize(original)
        denormalized = normalizer.denormalize(normalized)
        
        assert denormalized == original


# ============================================================================
# Test: GraphToFOLConverter - Basic Conversion
# ============================================================================

class TestBasicConversion:
    """Test basic conversion functionality"""
    
    def test_convert_single_node(self, sample_nodes):
        """Test converting a single node"""
        converter = GraphToFOLConverter()
        
        result = converter.convert_nodes_to_facts([sample_nodes[0]])
        
        assert result.success
        assert len(result.facts) > 0
        assert result.nodes_converted == 1
        
        # Check type fact exists
        type_facts = [f for f in result.facts if f.predicate == "person"]
        assert len(type_facts) == 1
    
    def test_convert_multiple_nodes(self, sample_nodes):
        """Test converting multiple nodes"""
        converter = GraphToFOLConverter()
        
        result = converter.convert_nodes_to_facts(sample_nodes)
        
        assert result.success
        assert result.nodes_converted == len(sample_nodes)
        assert len(result.facts) > len(sample_nodes)  # Should have property facts too
    
    def test_property_conversion(self, sample_nodes):
        """Test property conversion"""
        converter = GraphToFOLConverter(
            property_handling=PropertyHandling.INCLUDE_ALL
        )
        
        result = converter.convert_nodes_to_facts([sample_nodes[0]])
        
        # Check property facts
        property_facts = [f for f in result.facts if f.predicate.startswith("has_")]
        assert len(property_facts) > 0
        assert result.properties_converted > 0

    def test_exclude_properties(self, sample_nodes):
        """Test excluding properties"""
        converter = GraphToFOLConverter(
            property_handling=PropertyHandling.EXCLUDE_ALL
        )

        result = converter.convert_nodes_to_facts([sample_nodes[0]])

        # Should only have type fact
        property_facts = [f for f in result.facts if f.predicate.startswith("has_")]
        assert len(property_facts) == 0
    
    def test_persian_text_handling(self, sample_nodes):
        """Test Persian text handling"""
        converter = GraphToFOLConverter()
        
        result = converter.convert_nodes_to_facts([sample_nodes[0]])
        
        # Check that Persian text is properly normalized
        facts_str = [str(f) for f in result.facts]
        combined = " ".join(facts_str)
        
        # Should contain normalized Persian text
        assert "محمد" in combined or "محمد_رضایی" in combined


# ============================================================================
# Test: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling"""
    
    def test_empty_node_list(self):
        """Test handling of empty node list"""
        converter = GraphToFOLConverter(
            conversion_mode=ConversionMode.STRICT
        )
        
        with pytest.raises(Exception):
            converter.convert_nodes_to_facts([])
    
    def test_invalid_node_strict_mode(self):
        """Test invalid node in strict mode"""
        converter = GraphToFOLConverter(
            conversion_mode=ConversionMode.STRICT
        )
        
        invalid_node = GraphNode(
            id="",  # Invalid: empty ID
            label="Test",
            node_type="test"
        )
        
        with pytest.raises(InvalidNodeError):
            converter.convert_nodes_to_facts([invalid_node])
    
    def test_invalid_node_permissive_mode(self):
        """Test invalid node in permissive mode"""
        converter = GraphToFOLConverter(
            conversion_mode=ConversionMode.PERMISSIVE
        )
        
        invalid_node = GraphNode(
            id="",  # Invalid: empty ID
            label="Test",
            node_type="test"
        )
        
        result = converter.convert_nodes_to_facts([invalid_node])
        
        # Should not raise, but should have errors
        assert not result.success
        assert len(result.errors) > 0
    
    def test_duplicate_nodes(self, sample_nodes):
        """Test handling of duplicate nodes"""
        converter = GraphToFOLConverter(
            conversion_mode=ConversionMode.PERMISSIVE
        )
        
        # Convert same nodes twice
        result1 = converter.convert_nodes_to_facts([sample_nodes[0]])
        result2 = converter.convert_nodes_to_facts([sample_nodes[0]])
        
        # Second conversion should detect duplicate
        assert len(result2.warnings) > 0


# ============================================================================
# Test: Integrity Verification
# ============================================================================

class TestIntegrityVerification:
    """Test integrity verification"""
    
    def test_integrity_hash_generation(self, sample_nodes):
        """Test integrity hash generation"""
        converter = GraphToFOLConverter(enable_validation=True)
        
        result = converter.convert_nodes_to_facts(sample_nodes)
        
        assert result.integrity_hash is not None
        assert len(result.integrity_hash) == 64  # SHA-256
        assert result.verified
    
    def test_integrity_verification_success(self, sample_nodes):
        """Test successful integrity verification"""
        converter = GraphToFOLConverter(enable_validation=True)
        
        result = converter.convert_nodes_to_facts(sample_nodes)
        
        # Verify integrity
        is_valid = converter.verify_conversion_integrity(result)
        assert is_valid
    
    def test_integrity_verification_failure(self, sample_nodes):
        """Test integrity verification failure"""
        converter = GraphToFOLConverter(enable_validation=True)
        
        result = converter.convert_nodes_to_facts(sample_nodes)
        
        # Tamper with facts
        result.facts.append(Atom("tampered", (Term("test", TermType.CONSTANT),)))
        
        # Verification should fail
        with pytest.raises(IntegrityViolationError):
            converter.verify_conversion_integrity(result)


# ============================================================================
# Test: Performance
# ============================================================================

class TestPerformance:
    """Test performance characteristics"""
    
    def test_large_graph_conversion(self):
        """Test conversion of large graph"""
        # Create large graph
        nodes = [
            GraphNode(
                id=f"node_{i}",
                label="TestNode",
                node_type="test",
                properties={"index": i, "name": f"Node {i}"}
            )
            for i in range(1000)
        ]
        
        converter = GraphToFOLConverter()
        
        start_time = time.time()
        result = converter.convert_nodes_to_facts(nodes)
        elapsed = time.time() - start_time
        
        assert result.success
        assert result.nodes_converted == 1000
        assert elapsed < 5.0  # Should complete in < 5 seconds
        
        print(f"\n⏱️  Converted 1000 nodes in {elapsed:.2f}s")
        print(f"   Throughput: {1000/elapsed:.0f} nodes/sec")
    
    def test_caching_performance(self, sample_nodes):
        """Test caching performance improvement"""
        converter = GraphToFOLConverter(enable_caching=True)
        
        # First conversion (cache miss)
        start1 = time.time()
        _ = converter.convert_nodes_to_facts(sample_nodes)
        time1 = time.time() - start1
        
        # Reset seen nodes but keep cache
        converter._seen_nodes.clear()
        
        # Second conversion (cache hit)
        start2 = time.time()
        _ = converter.convert_nodes_to_facts(sample_nodes)
        time2 = time.time() - start2
        
        # Second should be faster or equal
        assert time2 <= time1 * 1.5  # Allow 50% margin for timing variance
        assert converter.stats["cache_hits"] > 0
        
        print(f"\n⚡ Cache speedup: {time1/time2:.1f}x")


# ============================================================================
# Test: Thread Safety
# ============================================================================

class TestThreadSafety:
    """Test thread safety"""
    
    def test_concurrent_conversion(self, sample_nodes):
        """Test concurrent conversions"""
        results = []
        errors = []

        def convert_thread():
            try:
                converter = GraphToFOLConverter(
                    conversion_mode=ConversionMode.PERMISSIVE
                )
                result = converter.convert_nodes_to_facts(sample_nodes)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Run 10 concurrent conversions
        threads = [threading.Thread(target=convert_thread) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All should succeed
        assert len(errors) == 0
        assert len(results) == 10

        # All should produce same facts (determinism)
        first_facts = set(str(f) for f in results[0].facts)
        for result in results[1:]:
            result_facts = set(str(f) for f in result.facts)
            assert first_facts == result_facts


# ============================================================================
# Test: Audit Trail
# ============================================================================

class TestAuditTrail:
    """Test audit trail functionality"""
    
    def test_audit_trail_generation(self, sample_nodes):
        """Test audit trail generation"""
        converter = GraphToFOLConverter(enable_audit_trail=True)
        
        result = converter.convert_nodes_to_facts(sample_nodes)
        
        audit_trail = converter.get_audit_trail()
        
        assert len(audit_trail) == len(sample_nodes)
        
        for trace in audit_trail:
            assert trace.source_type == "node"
            assert trace.source_id is not None
            assert len(trace.facts_generated) > 0
            assert trace.conversion_hash is not None


# ============================================================================
# Test: Convenience Functions
# ============================================================================

class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_convert_graph_to_facts(self, sample_graph):
        """Test convert_graph_to_facts convenience function"""
        result = convert_graph_to_facts(sample_graph)
        
        assert result.success
        assert len(result.facts) > 0
        assert result.nodes_converted > 0
        assert result.edges_converted > 0


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

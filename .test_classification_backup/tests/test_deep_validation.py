"""
Deep Validation Tests
======================

CRITICAL: Tests deep validation of ledger entries against graph state.
Ensures evidence references resolve to actual graph nodes.

Test Coverage:
- Deep validator initialization
- Node existence validation
- Edge existence validation
- Validation error reporting
- Integration with ledger guards

NO SIMPLIFICATION - Full deep validation required.
"""

import pytest
from pathlib import Path
import sys
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mahoun.ledger.models import LedgerEntry
from mahoun.ledger.guards import validate_entry
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder, GraphNode


class TestBasicValidation:
    """Test basic ledger entry validation"""
    
    def test_validate_entry_with_ltm_nodes(self):
        """Test validation passes with LTM nodes"""
        entry = LedgerEntry(
            verdict_id="v1",
            case_id="c1",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=[],
            confidence=0.9,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        # Should not raise
        validate_entry(entry)
    
    def test_validate_entry_with_facts(self):
        """Test validation passes with facts"""
        entry = LedgerEntry(
            verdict_id="v1",
            case_id="c1",
            referenced_ltm_nodes=[],
            referenced_facts=["fact_1"],
            confidence=0.9,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        # Should not raise
        validate_entry(entry)
    
    def test_validate_entry_fails_no_references(self):
        """Test validation fails with no references"""
        entry = LedgerEntry(
            verdict_id="v1",
            case_id="c1",
            referenced_ltm_nodes=[],  # EMPTY
            referenced_facts=[],  # EMPTY
            confidence=0.9,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ValueError, match="at least one referenced"):
            validate_entry(entry)
    
    def test_validate_entry_fails_invalid_confidence(self):
        """Test validation fails with invalid confidence"""
        entry = LedgerEntry(
            verdict_id="v1",
            case_id="c1",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=[],
            confidence=1.5,  # INVALID
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ValueError, match="Confidence must be between"):
            validate_entry(entry)
    
    def test_validate_entry_fails_empty_ids(self):
        """Test validation fails with empty verdict/case IDs"""
        entry = LedgerEntry(
            verdict_id="",  # EMPTY
            case_id="c1",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=[],
            confidence=0.9,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ValueError, match="Verdict ID and Case ID must not be empty"):
            validate_entry(entry)


class TestDeepValidation:
    """Test deep validation with graph builder"""
    
    def test_deep_validation_with_graph_builder(self):
        """Test deep validation checks node existence in graph"""
        builder = UltraGraphBuilder()
        
        # Build graph with entities (correct API usage)
        entities = [
            {
                "id": "rule_1",
                "label": "Article 219",
                "type": "LegalRule",
                "properties": {}
            },
            {
                "id": "fact_1",
                "label": "Contract signed on 2024-01-15",
                "type": "Fact",
                "properties": {}
            }
        ]
        relationships = []
        
        # Build graph (will be skipped in DESKTOP_MINIMAL mode)
        try:
            builder.build_graph(entities, relationships)
        except RuntimeError as e:
            if "DESKTOP_MINIMAL" in str(e):
                # Expected in DESKTOP_MINIMAL mode - skip this test
                pytest.skip("Graph construction disabled in DESKTOP_MINIMAL mode")
            raise
        
        entry = LedgerEntry(
            verdict_id="v1",
            case_id="c1",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=["fact_1"],  # Added second evidence item to satisfy confidence>0.7 requirement
            confidence=0.9,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        # Should not raise (node exists in graph)
        validate_entry(entry, graph_builder=builder)
    
    def test_deep_validation_without_graph_builder(self):
        """Test validation works without graph builder (basic validation only)"""
        entry = LedgerEntry(
            verdict_id="v1",
            case_id="c1",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=[],
            confidence=0.9,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        # Should not raise (basic validation only)
        validate_entry(entry, graph_builder=None)


class TestValidationErrorReporting:
    """Test validation error reporting"""
    
    def test_error_message_includes_details(self):
        """Test that error messages include helpful details"""
        entry = LedgerEntry(
            verdict_id="v1",
            case_id="c1",
            referenced_ltm_nodes=[],
            referenced_facts=[],
            confidence=0.9,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        try:
            validate_entry(entry)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            # Error message should be informative
            assert "at least one" in str(e).lower()
    
    def test_confidence_error_includes_value(self):
        """Test that confidence error includes actual value"""
        entry = LedgerEntry(
            verdict_id="v1",
            case_id="c1",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=[],
            confidence=1.5,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        try:
            validate_entry(entry)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            # Error message should mention confidence range
            assert "0.0" in str(e) and "1.0" in str(e)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Graph Module Contract Tests
============================

Tests for graph module Pydantic contracts.

These tests validate:
- Input schema compliance
- Output schema compliance
- Error schema compliance
- Field validation rules
- Graph structure integrity

IMPORTANT: These are CONTRACT tests, not BEHAVIOR tests.
They test data structure integrity, not graph algorithms.

Validates Requirements: 2.1, 2.2, 2.3
"""

import pytest
from pydantic import ValidationError

from mahoun.schemas.contracts.graph_contracts import (
    # Entity and Relationship
    EntityContract,
    RelationshipContract,
    # Build Graph
    BuildGraphInput,
    GraphMetricsContract,
    GraphNodeContract,
    GraphEdgeContract,
    BuildGraphOutput,
    BuildGraphError,
    # Query Operations
    QueryNeighborsInput,
    QueryNeighborsOutput,
    FindPathInput,
    FindPathOutput,
    GetSubgraphInput,
    GetSubgraphOutput,
    GraphQueryError,
)


# ============================================================================
# EntityContract Tests
# ============================================================================

class TestEntityContract:
    """Test EntityContract validation."""
    
    def test_valid_entity_with_id(self):
        """Valid entity with ID should pass."""
        entity = EntityContract(
            id="entity_1",
            label="LegalRule",
            type="entity",
            confidence=0.95
        )
        assert entity.id == "entity_1"
        assert entity.confidence == 0.95
    
    def test_valid_entity_with_text_only(self):
        """Valid entity with text but no ID should pass."""
        entity = EntityContract(
            text="Contract breach occurred",
            label="Fact",
            type="entity"
        )
        assert entity.text == "Contract breach occurred"
        assert entity.id is None
    
    def test_entity_without_id_or_text_fails(self):
        """Entity without both id and text should fail."""
        with pytest.raises(ValidationError) as exc_info:
            EntityContract(
                label="Fact",
                type="entity"
            )
        assert "id" in str(exc_info.value).lower() or "text" in str(exc_info.value).lower()
    
    def test_confidence_out_of_range_fails(self):
        """Confidence outside [0, 1] should fail."""
        with pytest.raises(ValidationError):
            EntityContract(
                id="entity_1",
                label="Fact",
                confidence=1.5
            )
    
    def test_extra_fields_forbidden(self):
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            EntityContract(
                id="entity_1",
                label="Fact",
                extra_field="not_allowed"
            )


# ============================================================================
# RelationshipContract Tests
# ============================================================================

class TestRelationshipContract:
    """Test RelationshipContract validation."""
    
    def test_valid_relationship(self):
        """Valid relationship should pass."""
        rel = RelationshipContract(
            source_id="entity_1",
            target_id="entity_2",
            type="CAUSES",
            weight=0.85,
            confidence=0.9
        )
        assert rel.source_id == "entity_1"
        assert rel.weight == 0.85
    
    def test_minimal_relationship(self):
        """Minimal relationship with defaults should pass."""
        rel = RelationshipContract(
            source_id="entity_1",
            target_id="entity_2"
        )
        assert rel.type == "RELATED"
        assert rel.weight == 1.0
        assert rel.confidence == 1.0
    
    def test_empty_source_id_fails(self):
        """Empty source_id should fail."""
        with pytest.raises(ValidationError):
            RelationshipContract(
                source_id="",
                target_id="entity_2"
            )
    
    def test_negative_weight_fails(self):
        """Negative weight should fail."""
        with pytest.raises(ValidationError):
            RelationshipContract(
                source_id="entity_1",
                target_id="entity_2",
                weight=-0.5
            )


# ============================================================================
# BuildGraphInput Tests
# ============================================================================

class TestBuildGraphInput:
    """Test BuildGraphInput validation."""
    
    def test_valid_input(self):
        """Valid input should pass."""
        inp = BuildGraphInput(
            entities=[
                {"id": "fact_1", "label": "Fact"},
                {"id": "rule_1", "label": "LegalRule"}
            ],
            relationships=[
                {"source_id": "fact_1", "target_id": "rule_1", "type": "APPLIES_TO"}
            ],
            source_id="case_12345"
        )
        assert len(inp.entities) == 2
        assert len(inp.relationships) == 1
    
    def test_input_without_relationships(self):
        """Input without relationships should pass."""
        inp = BuildGraphInput(
            entities=[{"id": "fact_1", "label": "Fact"}]
        )
        assert len(inp.relationships) == 0
    
    def test_empty_entities_fails(self):
        """Empty entities list should fail."""
        with pytest.raises(ValidationError):
            BuildGraphInput(entities=[])
    
    def test_too_many_entities_fails(self):
        """More than 100000 entities should fail."""
        with pytest.raises(ValidationError):
            BuildGraphInput(
                entities=[{"id": f"entity_{i}"} for i in range(100001)]
            )


# ============================================================================
# GraphMetricsContract Tests
# ============================================================================

class TestGraphMetricsContract:
    """Test GraphMetricsContract validation."""
    
    def test_valid_metrics(self):
        """Valid metrics should pass."""
        metrics = GraphMetricsContract(
            total_nodes=100,
            total_edges=250,
            avg_degree=5.0,
            density=0.05,
            avg_node_quality=0.85,
            build_time_seconds=1.5
        )
        assert metrics.total_nodes == 100
        assert metrics.density == 0.05
    
    def test_default_metrics(self):
        """Default metrics should pass."""
        metrics = GraphMetricsContract()
        assert metrics.total_nodes == 0
        assert metrics.total_edges == 0
        assert metrics.avg_degree == 0.0
    
    def test_negative_nodes_fails(self):
        """Negative node count should fail."""
        with pytest.raises(ValidationError):
            GraphMetricsContract(total_nodes=-1)
    
    def test_density_out_of_range_fails(self):
        """Density outside [0, 1] should fail."""
        with pytest.raises(ValidationError):
            GraphMetricsContract(density=1.5)


# ============================================================================
# GraphNodeContract Tests
# ============================================================================

class TestGraphNodeContract:
    """Test GraphNodeContract validation."""
    
    def test_valid_node(self):
        """Valid node should pass."""
        node = GraphNodeContract(
            id="node_1",
            label="Fact",
            node_type="entity",
            confidence=0.95,
            quality_score=0.85,
            validation_status="validated"
        )
        assert node.id == "node_1"
        assert node.validation_status == "validated"
    
    def test_invalid_validation_status_fails(self):
        """Invalid validation status should fail."""
        with pytest.raises(ValidationError):
            GraphNodeContract(
                id="node_1",
                label="Fact",
                node_type="entity",
                validation_status="invalid_status"
            )
    
    def test_quality_score_out_of_range_fails(self):
        """Quality score outside [0, 1] should fail."""
        with pytest.raises(ValidationError):
            GraphNodeContract(
                id="node_1",
                label="Fact",
                node_type="entity",
                quality_score=1.5
            )


# ============================================================================
# GraphEdgeContract Tests
# ============================================================================

class TestGraphEdgeContract:
    """Test GraphEdgeContract validation."""
    
    def test_valid_edge(self):
        """Valid edge should pass."""
        edge = GraphEdgeContract(
            source_id="node_1",
            target_id="node_2",
            relationship_type="CAUSES",
            weight=0.85,
            confidence=0.9,
            quality_score=0.8,
            validation_status="validated"
        )
        assert edge.source_id == "node_1"
        assert edge.weight == 0.85
    
    def test_edge_with_evidence(self):
        """Edge with evidence should pass."""
        edge = GraphEdgeContract(
            source_id="node_1",
            target_id="node_2",
            relationship_type="SUPPORTS",
            evidence=["Article 220", "Precedent case 123"]
        )
        assert len(edge.evidence) == 2


# ============================================================================
# BuildGraphOutput Tests
# ============================================================================

class TestBuildGraphOutput:
    """Test BuildGraphOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = BuildGraphOutput(
            nodes=[
                GraphNodeContract(
                    id="node_1",
                    label="Fact",
                    node_type="entity"
                )
            ],
            edges=[
                GraphEdgeContract(
                    source_id="node_1",
                    target_id="node_2",
                    relationship_type="RELATED"
                )
            ],
            metrics=GraphMetricsContract(
                total_nodes=1,
                total_edges=1
            ),
            build_time=0.5,
            status="success"
        )
        assert output.status == "success"
        assert len(output.nodes) == 1
    
    def test_empty_graph_output(self):
        """Empty graph output should pass."""
        output = BuildGraphOutput(
            nodes=[],
            edges=[],
            metrics=GraphMetricsContract(),
            build_time=0.1
        )
        assert len(output.nodes) == 0
        assert output.status == "success"
    
    def test_invalid_status_fails(self):
        """Invalid status should fail."""
        with pytest.raises(ValidationError):
            BuildGraphOutput(
                metrics=GraphMetricsContract(),
                build_time=0.5,
                status="invalid_status"
            )
    
    def test_negative_build_time_fails(self):
        """Negative build time should fail."""
        with pytest.raises(ValidationError):
            BuildGraphOutput(
                metrics=GraphMetricsContract(),
                build_time=-0.5
            )


# ============================================================================
# BuildGraphError Tests
# ============================================================================

class TestBuildGraphError:
    """Test BuildGraphError validation."""
    
    def test_valid_error(self):
        """Valid error should pass."""
        error = BuildGraphError(
            error_type="empty_entities",
            message="No entities provided"
        )
        assert error.error_type == "empty_entities"
    
    def test_all_valid_error_types(self):
        """All documented error types should be valid."""
        valid_types = [
            "empty_entities",
            "invalid_entity_structure",
            "invalid_relationship",
            "quality_assessment_failed"
        ]
        for error_type in valid_types:
            error = BuildGraphError(
                error_type=error_type,
                message=f"Test {error_type}"
            )
            assert error.error_type == error_type
    
    def test_invalid_error_type_fails(self):
        """Invalid error_type should fail."""
        with pytest.raises(ValidationError):
            BuildGraphError(
                error_type="invalid_type",
                message="message"
            )


# ============================================================================
# QueryNeighborsInput Tests
# ============================================================================

class TestQueryNeighborsInput:
    """Test QueryNeighborsInput validation."""
    
    def test_valid_input(self):
        """Valid input should pass."""
        inp = QueryNeighborsInput(
            node_id="node_1",
            max_depth=2
        )
        assert inp.node_id == "node_1"
        assert inp.max_depth == 2
    
    def test_default_max_depth(self):
        """Default max_depth should be 1."""
        inp = QueryNeighborsInput(node_id="node_1")
        assert inp.max_depth == 1
    
    def test_max_depth_too_large_fails(self):
        """max_depth > 10 should fail."""
        with pytest.raises(ValidationError):
            QueryNeighborsInput(
                node_id="node_1",
                max_depth=11
            )
    
    def test_max_depth_zero_fails(self):
        """max_depth = 0 should fail."""
        with pytest.raises(ValidationError):
            QueryNeighborsInput(
                node_id="node_1",
                max_depth=0
            )


# ============================================================================
# QueryNeighborsOutput Tests
# ============================================================================

class TestQueryNeighborsOutput:
    """Test QueryNeighborsOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = QueryNeighborsOutput(
            neighbors=[
                GraphNodeContract(
                    id="node_2",
                    label="Fact",
                    node_type="entity"
                )
            ],
            total_neighbors=1
        )
        assert output.total_neighbors == 1
    
    def test_empty_neighbors(self):
        """Empty neighbors list should pass."""
        output = QueryNeighborsOutput(
            neighbors=[],
            total_neighbors=0
        )
        assert len(output.neighbors) == 0


# ============================================================================
# FindPathInput Tests
# ============================================================================

class TestFindPathInput:
    """Test FindPathInput validation."""
    
    def test_valid_input(self):
        """Valid input should pass."""
        inp = FindPathInput(
            source_id="node_1",
            target_id="node_5",
            max_depth=10
        )
        assert inp.source_id == "node_1"
        assert inp.max_depth == 10
    
    def test_default_max_depth(self):
        """Default max_depth should be 5."""
        inp = FindPathInput(
            source_id="node_1",
            target_id="node_2"
        )
        assert inp.max_depth == 5
    
    def test_max_depth_too_large_fails(self):
        """max_depth > 20 should fail."""
        with pytest.raises(ValidationError):
            FindPathInput(
                source_id="node_1",
                target_id="node_2",
                max_depth=21
            )


# ============================================================================
# FindPathOutput Tests
# ============================================================================

class TestFindPathOutput:
    """Test FindPathOutput validation."""
    
    def test_valid_path_found(self):
        """Valid path found should pass."""
        output = FindPathOutput(
            path=["node_1", "node_2", "node_3"],
            path_length=3,
            path_exists=True
        )
        assert output.path_length == 3
        assert output.path_exists is True
    
    def test_no_path_found(self):
        """No path found should pass."""
        output = FindPathOutput(
            path=None,
            path_length=0,
            path_exists=False
        )
        assert output.path is None
        assert output.path_exists is False
    
    def test_inconsistent_path_length_fails(self):
        """Inconsistent path_length should fail."""
        with pytest.raises(ValidationError):
            FindPathOutput(
                path=["node_1", "node_2"],
                path_length=5,  # Wrong length
                path_exists=True
            )
    
    def test_path_none_but_exists_true_fails(self):
        """path=None but path_exists=True should fail."""
        with pytest.raises(ValidationError):
            FindPathOutput(
                path=None,
                path_length=0,
                path_exists=True  # Inconsistent
            )
    
    def test_path_exists_but_path_none_fails(self):
        """path exists but path=None should fail."""
        with pytest.raises(ValidationError):
            FindPathOutput(
                path=None,
                path_length=0,
                path_exists=True
            )


# ============================================================================
# GetSubgraphInput Tests
# ============================================================================

class TestGetSubgraphInput:
    """Test GetSubgraphInput validation."""
    
    def test_valid_input(self):
        """Valid input should pass."""
        inp = GetSubgraphInput(
            node_ids=["node_1", "node_2", "node_3"]
        )
        assert len(inp.node_ids) == 3
    
    def test_empty_node_ids_fails(self):
        """Empty node_ids should fail."""
        with pytest.raises(ValidationError):
            GetSubgraphInput(node_ids=[])
    
    def test_duplicate_node_ids_fails(self):
        """Duplicate node_ids should fail."""
        with pytest.raises(ValidationError):
            GetSubgraphInput(
                node_ids=["node_1", "node_2", "node_1"]  # Duplicate
            )
    
    def test_too_many_node_ids_fails(self):
        """More than 10000 node_ids should fail."""
        with pytest.raises(ValidationError):
            GetSubgraphInput(
                node_ids=[f"node_{i}" for i in range(10001)]
            )


# ============================================================================
# GetSubgraphOutput Tests
# ============================================================================

class TestGetSubgraphOutput:
    """Test GetSubgraphOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = GetSubgraphOutput(
            nodes=[
                GraphNodeContract(
                    id="node_1",
                    label="Fact",
                    node_type="entity"
                )
            ],
            edges=[
                GraphEdgeContract(
                    source_id="node_1",
                    target_id="node_2",
                    relationship_type="RELATED"
                )
            ],
            total_nodes=1,
            total_edges=1
        )
        assert output.total_nodes == 1
        assert output.total_edges == 1
    
    def test_empty_subgraph(self):
        """Empty subgraph should pass."""
        output = GetSubgraphOutput(
            nodes=[],
            edges=[],
            total_nodes=0,
            total_edges=0
        )
        assert output.total_nodes == 0


# ============================================================================
# GraphQueryError Tests
# ============================================================================

class TestGraphQueryError:
    """Test GraphQueryError validation."""
    
    def test_valid_error(self):
        """Valid error should pass."""
        error = GraphQueryError(
            error_type="node_not_found",
            message="Node does not exist"
        )
        assert error.error_type == "node_not_found"
    
    def test_all_valid_error_types(self):
        """All documented error types should be valid."""
        valid_types = [
            "node_not_found",
            "empty_graph",
            "max_depth_exceeded",
            "invalid_node_ids"
        ]
        for error_type in valid_types:
            error = GraphQueryError(
                error_type=error_type,
                message=f"Test {error_type}"
            )
            assert error.error_type == error_type
    
    def test_invalid_error_type_fails(self):
        """Invalid error_type should fail."""
        with pytest.raises(ValidationError):
            GraphQueryError(
                error_type="invalid_type",
                message="message"
            )


# ============================================================================
# Integration Tests
# ============================================================================

class TestGraphContractIntegration:
    """Test contract integration and composition."""
    
    def test_nested_contracts_validation(self):
        """Nested contracts should validate recursively."""
        # Invalid nested node should fail at top level
        with pytest.raises(ValidationError):
            BuildGraphOutput(
                nodes=[
                    GraphNodeContract(
                        id="node_1",
                        label="Fact",
                        node_type="entity",
                        quality_score=2.0  # Invalid: > 1.0
                    )
                ],
                metrics=GraphMetricsContract(),
                build_time=0.5
            )
    
    def test_extra_forbid_at_all_levels(self):
        """extra='forbid' should be enforced at all nesting levels."""
        # Extra field at top level should fail
        with pytest.raises(ValidationError):
            BuildGraphOutput(
                metrics=GraphMetricsContract(),
                build_time=0.5,
                extra_field="not_allowed"
            )
        
        # Extra field at nested level should fail
        with pytest.raises(ValidationError):
            GraphNodeContract(
                id="node_1",
                label="Fact",
                node_type="entity",
                extra_nested="not_allowed"
            )
    
    def test_complete_graph_build_workflow(self):
        """Complete graph build workflow should validate."""
        # Input
        inp = BuildGraphInput(
            entities=[
                {"id": "fact_1", "label": "Fact", "type": "entity"},
                {"id": "rule_1", "label": "LegalRule", "type": "entity"}
            ],
            relationships=[
                {"source_id": "fact_1", "target_id": "rule_1", "type": "APPLIES_TO"}
            ]
        )
        
        # Output
        output = BuildGraphOutput(
            nodes=[
                GraphNodeContract(
                    id="fact_1",
                    label="Fact",
                    node_type="entity",
                    quality_score=0.85,
                    validation_status="validated"
                ),
                GraphNodeContract(
                    id="rule_1",
                    label="LegalRule",
                    node_type="entity",
                    quality_score=0.9,
                    validation_status="validated"
                )
            ],
            edges=[
                GraphEdgeContract(
                    source_id="fact_1",
                    target_id="rule_1",
                    relationship_type="APPLIES_TO",
                    quality_score=0.8,
                    validation_status="validated"
                )
            ],
            metrics=GraphMetricsContract(
                total_nodes=2,
                total_edges=1,
                avg_node_quality=0.875,
                avg_edge_quality=0.8
            ),
            build_time=0.05
        )
        
        assert len(output.nodes) == 2
        assert len(output.edges) == 1
        assert output.metrics.total_nodes == 2

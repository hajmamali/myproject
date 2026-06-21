"""
Graph Module Contracts
=======================

Formal contracts for the graph module's public interfaces.

These contracts define:
- Input validation rules for graph operations
- Output structure guarantees
- Error conditions and types
- Graph quality metrics

All contracts use `extra="forbid"` to ensure clean data structures.

Validates Requirements: 2.1, 2.2, 2.3
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ============================================================================
# UltraGraphBuilder Contracts
# ============================================================================

class EntityContract(BaseModel):
    """
    Contract for entity input to graph builder.
    
    Validates: Requirement 2.1 - Entity structure
    """
    id: Optional[str] = Field(
        None,
        max_length=500,
        description="Entity identifier (auto-generated if None)"
    )
    text: Optional[str] = Field(
        None,
        min_length=1,
        max_length=10000,
        description="Entity text (used as ID if id is None)"
    )
    label: str = Field(
        default="UNKNOWN",
        min_length=1,
        max_length=100,
        description="Entity label/category"
    )
    type: str = Field(
        default="entity",
        min_length=1,
        max_length=50,
        description="Entity type"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional entity properties"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Entity extraction confidence"
    )
    
    @model_validator(mode='after')
    def validate_id_or_text(self) -> 'EntityContract':
        """Ensure either id or text is provided."""
        if not self.id and not self.text:
            raise ValueError("Either 'id' or 'text' must be provided")
        return self
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "entity_contract_breach",
                "label": "LegalConcept",
                "type": "entity",
                "properties": {"domain": "contract_law"},
                "confidence": 0.95
            }
        }
    )


class RelationshipContract(BaseModel):
    """
    Contract for relationship input to graph builder.
    
    Validates: Requirement 2.1 - Relationship structure
    """
    source_id: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Source entity ID"
    )
    target_id: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Target entity ID"
    )
    type: str = Field(
        default="RELATED",
        min_length=1,
        max_length=100,
        description="Relationship type"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional relationship properties"
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Relationship weight/strength"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relationship extraction confidence"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Supporting evidence for relationship"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "source_id": "entity_1",
                "target_id": "entity_2",
                "type": "CAUSES",
                "weight": 0.85,
                "confidence": 0.9,
                "evidence": ["Article 220 Civil Code"]
            }
        }
    )


class BuildGraphInput(BaseModel):
    """
    Input contract for UltraGraphBuilder.build_graph()
    
    Validates: Requirement 2.1 - Graph construction input
    """
    entities: List[Dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="List of entities to add to graph"
    )
    relationships: List[Dict[str, Any]] = Field(
        default_factory=list,
        max_length=500000,
        description="List of relationships between entities"
    )
    source_id: Optional[str] = Field(
        None,
        max_length=200,
        description="Source document/dataset identifier"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "entities": [
                    {"id": "fact_1", "label": "Fact", "type": "entity"},
                    {"id": "rule_1", "label": "LegalRule", "type": "entity"}
                ],
                "relationships": [
                    {"source_id": "fact_1", "target_id": "rule_1", "type": "APPLIES_TO"}
                ],
                "source_id": "case_12345"
            }
        }
    )


class GraphMetricsContract(BaseModel):
    """
    Contract for graph quality and performance metrics.
    
    Validates: Requirement 2.2 - Graph metrics structure
    """
    total_nodes: int = Field(
        default=0,
        ge=0,
        description="Total number of nodes in graph"
    )
    total_edges: int = Field(
        default=0,
        ge=0,
        description="Total number of edges in graph"
    )
    avg_degree: float = Field(
        default=0.0,
        ge=0.0,
        description="Average node degree"
    )
    clustering_coefficient: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Graph clustering coefficient"
    )
    density: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Graph density"
    )
    avg_node_quality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average node quality score"
    )
    avg_edge_quality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average edge quality score"
    )
    validation_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Percentage of validated elements"
    )
    build_time_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Graph build time in seconds"
    )
    memory_usage_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="Memory usage in megabytes"
    )
    query_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Average query latency in milliseconds"
    )
    
    model_config = ConfigDict(extra="forbid")


class GraphNodeContract(BaseModel):
    """
    Contract for graph node structure.
    
    Validates: Requirement 2.2 - Node output structure
    """
    id: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Node identifier"
    )
    label: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Node label"
    )
    node_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Node type"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Node properties"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Node confidence score"
    )
    quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Node quality score"
    )
    validation_status: str = Field(
        default="pending",
        pattern="^(pending|validated|failed)$",
        description="Node validation status"
    )
    
    model_config = ConfigDict(extra="forbid")


class GraphEdgeContract(BaseModel):
    """
    Contract for graph edge structure.
    
    Validates: Requirement 2.2 - Edge output structure
    """
    source_id: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Source node ID"
    )
    target_id: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Target node ID"
    )
    relationship_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Relationship type"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Edge properties"
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Edge weight"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Edge confidence score"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Supporting evidence"
    )
    quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Edge quality score"
    )
    validation_status: str = Field(
        default="pending",
        pattern="^(pending|validated|failed)$",
        description="Edge validation status"
    )
    
    model_config = ConfigDict(extra="forbid")


class BuildGraphOutput(BaseModel):
    """
    Output contract for UltraGraphBuilder.build_graph()
    
    Validates: Requirement 2.2 - Graph construction output
    """
    nodes: List[GraphNodeContract] = Field(
        default_factory=list,
        description="Graph nodes created/updated"
    )
    edges: List[GraphEdgeContract] = Field(
        default_factory=list,
        description="Graph edges created"
    )
    metrics: GraphMetricsContract = Field(
        ...,
        description="Graph quality and performance metrics"
    )
    build_time: float = Field(
        ...,
        ge=0.0,
        description="Total build time in seconds"
    )
    status: str = Field(
        default="success",
        pattern="^(success|skipped|partial)$",
        description="Build status"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "nodes": [
                    {
                        "id": "fact_1",
                        "label": "Fact",
                        "node_type": "entity",
                        "confidence": 1.0,
                        "quality_score": 0.85,
                        "validation_status": "validated"
                    }
                ],
                "edges": [
                    {
                        "source_id": "fact_1",
                        "target_id": "rule_1",
                        "relationship_type": "APPLIES_TO",
                        "weight": 1.0,
                        "confidence": 0.9,
                        "quality_score": 0.8,
                        "validation_status": "validated"
                    }
                ],
                "metrics": {
                    "total_nodes": 2,
                    "total_edges": 1,
                    "avg_degree": 1.0,
                    "density": 0.5,
                    "build_time_seconds": 0.05
                },
                "build_time": 0.05,
                "status": "success"
            }
        }
    )


class BuildGraphError(BaseModel):
    """
    Error contract for UltraGraphBuilder.build_graph() failures.
    
    Validates: Requirement 2.3 - Error handling
    
    Failure Modes:
    - empty_entities: No entities provided
    - invalid_entity_structure: Entity missing required fields
    - invalid_relationship: Relationship references non-existent nodes
    - quality_assessment_failed: Quality assessment failed
    """
    error_type: str = Field(
        ...,
        pattern="^(empty_entities|invalid_entity_structure|invalid_relationship|quality_assessment_failed)$",
        description="Error type identifier"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context"
    )
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Graph Query Contracts
# ============================================================================

class QueryNeighborsInput(BaseModel):
    """
    Input contract for UltraGraphBuilder.query_neighbors()
    
    Validates: Requirement 2.1 - Neighbor query input
    """
    node_id: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Node ID to query neighbors for"
    )
    max_depth: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Maximum traversal depth"
    )
    
    model_config = ConfigDict(extra="forbid")


class QueryNeighborsOutput(BaseModel):
    """
    Output contract for UltraGraphBuilder.query_neighbors()
    
    Validates: Requirement 2.2 - Neighbor query output
    """
    neighbors: List[GraphNodeContract] = Field(
        default_factory=list,
        description="List of neighbor nodes"
    )
    total_neighbors: int = Field(
        ...,
        ge=0,
        description="Total number of neighbors found"
    )
    
    model_config = ConfigDict(extra="forbid")


class FindPathInput(BaseModel):
    """
    Input contract for UltraGraphBuilder.find_path()
    
    Validates: Requirement 2.1 - Path finding input
    """
    source_id: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Source node ID"
    )
    target_id: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Target node ID"
    )
    max_depth: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum path length"
    )
    
    model_config = ConfigDict(extra="forbid")


class FindPathOutput(BaseModel):
    """
    Output contract for UltraGraphBuilder.find_path()
    
    Validates: Requirement 2.2 - Path finding output
    """
    path: Optional[List[str]] = Field(
        None,
        description="Shortest path as list of node IDs (None if no path found)"
    )
    path_length: int = Field(
        default=0,
        ge=0,
        description="Length of path (0 if no path found)"
    )
    path_exists: bool = Field(
        ...,
        description="Whether a path was found"
    )
    
    @model_validator(mode='after')
    def validate_path_consistency(self) -> 'FindPathOutput':
        """Ensure path fields are consistent."""
        if self.path is None:
            if self.path_length != 0:
                raise ValueError("path_length must be 0 when path is None")
            if self.path_exists:
                raise ValueError("path_exists must be False when path is None")
        else:
            if self.path_length != len(self.path):
                raise ValueError("path_length must match length of path")
            if not self.path_exists:
                raise ValueError("path_exists must be True when path is not None")
        return self
    
    model_config = ConfigDict(extra="forbid")


class GetSubgraphInput(BaseModel):
    """
    Input contract for UltraGraphBuilder.get_subgraph()
    
    Validates: Requirement 2.1 - Subgraph extraction input
    """
    node_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="List of node IDs to include in subgraph"
    )
    
    @field_validator('node_ids')
    @classmethod
    def validate_unique_node_ids(cls, v: List[str]) -> List[str]:
        """Ensure node IDs are unique."""
        if len(v) != len(set(v)):
            raise ValueError("node_ids must be unique")
        return v
    
    model_config = ConfigDict(extra="forbid")


class GetSubgraphOutput(BaseModel):
    """
    Output contract for UltraGraphBuilder.get_subgraph()
    
    Validates: Requirement 2.2 - Subgraph extraction output
    """
    nodes: List[GraphNodeContract] = Field(
        default_factory=list,
        description="Nodes in subgraph"
    )
    edges: List[GraphEdgeContract] = Field(
        default_factory=list,
        description="Edges in subgraph"
    )
    total_nodes: int = Field(
        ...,
        ge=0,
        description="Total nodes in subgraph"
    )
    total_edges: int = Field(
        ...,
        ge=0,
        description="Total edges in subgraph"
    )
    
    model_config = ConfigDict(extra="forbid")


class GraphQueryError(BaseModel):
    """
    Error contract for graph query failures.
    
    Validates: Requirement 2.3 - Error handling
    
    Failure Modes:
    - node_not_found: Requested node does not exist
    - empty_graph: Graph is empty
    - max_depth_exceeded: Query exceeded maximum depth
    - invalid_node_ids: Invalid node IDs provided
    """
    error_type: str = Field(
        ...,
        pattern="^(node_not_found|empty_graph|max_depth_exceeded|invalid_node_ids)$",
        description="Error type identifier"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context"
    )
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Entity and Relationship
    "EntityContract",
    "RelationshipContract",
    # Build Graph
    "BuildGraphInput",
    "GraphMetricsContract",
    "GraphNodeContract",
    "GraphEdgeContract",
    "BuildGraphOutput",
    "BuildGraphError",
    # Query Operations
    "QueryNeighborsInput",
    "QueryNeighborsOutput",
    "FindPathInput",
    "FindPathOutput",
    "GetSubgraphInput",
    "GetSubgraphOutput",
    "GraphQueryError",
]

"""
Advanced Protocol Definitions for MAHOUN Platform
==================================================

Protocol definitions for advanced features:
- Uncertainty estimation
- Ontology validation
- Ultra Graph-RAG

These protocols define the contract boundaries for integrating
sophisticated ML/AI capabilities into the verdict engine.

Classification: CORE BOUNDARY / INTEGRATION CONTRACT
"""

from typing import Protocol, runtime_checkable, Dict, Any, Optional, List, Tuple
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# Uncertainty Estimation Protocol
# ============================================================================


@dataclass(frozen=True)
class UncertaintyEstimate:
    """
    Immutable uncertainty estimate result.
    
    Decomposes total uncertainty into epistemic (model) and aleatoric (data)
    components for risk-aware decision making.
    
    Invariants:
    - All uncertainty values in [0.0, 1.0]
    - total_uncertainty >= max(epistemic_uncertainty, aleatoric_uncertainty)
    - confidence = 1.0 - total_uncertainty
    """
    epistemic_uncertainty: float  # Model uncertainty (reducible with more data/training)
    aleatoric_uncertainty: float  # Data uncertainty (inherent noise, irreducible)
    total_uncertainty: float      # Combined uncertainty
    confidence: float             # 1 - total_uncertainty
    method: str                   # Estimation method used
    metadata: Dict[str, Any]      # Additional context
    
    def __post_init__(self):
        """Validate invariants."""
        for name, value in [
            ("epistemic_uncertainty", self.epistemic_uncertainty),
            ("aleatoric_uncertainty", self.aleatoric_uncertainty),
            ("total_uncertainty", self.total_uncertainty),
            ("confidence", self.confidence),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0.0, 1.0], got {value}")
        
        # Confidence should be 1 - total
        expected_confidence = 1.0 - self.total_uncertainty
        if abs(self.confidence - expected_confidence) > 1e-6:
            raise ValueError(
                f"confidence ({self.confidence}) must equal 1 - total_uncertainty "
                f"({expected_confidence})"
            )
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if confidence exceeds threshold."""
        return self.confidence >= threshold
    
    def is_low_uncertainty(self, threshold: float = 0.2) -> bool:
        """Check if total uncertainty is below threshold."""
        return self.total_uncertainty <= threshold


@runtime_checkable
class UncertaintyServiceProtocol(Protocol):
    """
    Protocol for uncertainty estimation.
    
    Implementations must:
    - Be stateless or thread-safe
    - Return deterministic results for deterministic inputs
    - Decompose uncertainty into epistemic + aleatoric
    - Handle edge cases (single prediction, no ensemble)
    """
    
    @abstractmethod
    def estimate(
        self,
        predictions: List[float],
        *,
        labels: Optional[List[int]] = None,
        method: str = "ensemble",
        **kwargs: Any
    ) -> UncertaintyEstimate:
        """
        Estimate uncertainty from model predictions.
        
        Args:
            predictions: List of predictions (can be single model repeated or ensemble)
            labels: Optional ground truth labels for calibration
            method: Estimation method ("ensemble", "calibration", "combined")
            **kwargs: Method-specific parameters
        
        Returns:
            UncertaintyEstimate with epistemic/aleatoric decomposition
        
        Raises:
            ValueError: If predictions empty or invalid method
        """
        ...
    
    @abstractmethod
    def calibrate(
        self,
        predictions: List[float],
        labels: List[int],
        **kwargs: Any
    ) -> Any:
        """
        Calibrate uncertainty estimator on labeled data.
        
        Args:
            predictions: Model predictions
            labels: Ground truth labels
            **kwargs: Calibration parameters
        
        Returns:
            Calibration result (implementation-specific)
        """
        ...


# ============================================================================
# Ontology Validation Protocol
# ============================================================================


@dataclass(frozen=True)
class OntologyValidationResult:
    """
    Result of ontology validation.
    
    Attributes:
        is_valid: Whether validation passed
        violations: List of violation messages (empty if valid)
        validated_relationships: Number of relationships validated
        schema_version: Ontology schema version used
        metadata: Additional context
    """
    is_valid: bool
    violations: List[str]
    validated_relationships: int
    schema_version: str
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate invariants."""
        if not isinstance(self.violations, list):
            raise TypeError("violations must be a list")
        if self.is_valid and self.violations:
            raise ValueError("is_valid=True but violations is non-empty")
        if not self.is_valid and not self.violations:
            raise ValueError("is_valid=False but violations is empty")
        if self.validated_relationships < 0:
            raise ValueError("validated_relationships must be >= 0")


@runtime_checkable
class OntologyGateProtocol(Protocol):
    """
    Protocol for ontology validation at schema level.
    
    Extends runtime OntologyEnforcer with schema-level validation:
    - Pre-write validation of entire graph structures
    - Schema drift detection
    - Cross-domain consistency checks
    
    Implementations must:
    - Be stateless or thread-safe
    - Validate against authoritative ontology definition
    - Fail-closed on unknown relationships
    - Provide actionable error messages
    """
    
    @abstractmethod
    def validate_schema(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        *,
        strict: bool = True
    ) -> OntologyValidationResult:
        """
        Validate graph structure against ontology schema.
        
        Args:
            nodes: List of node dicts with 'type' key
            relationships: List of relationship dicts with 'type', 'source_type', 'target_type'
            strict: If True, fail on any violation; if False, collect all violations
        
        Returns:
            OntologyValidationResult with validation status
        
        Raises:
            ValueError: If nodes/relationships have invalid structure
        """
        ...
    
    @abstractmethod
    def validate_relationship(
        self,
        source_type: str,
        relationship_type: str,
        target_type: str,
        *,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Validate single relationship (runtime check).
        
        Args:
            source_type: Source node type
            relationship_type: Relationship type
            target_type: Target node type
            correlation_id: Optional correlation ID for tracing
        
        Raises:
            GovernanceViolationError: If relationship violates ontology
        """
        ...
    
    @abstractmethod
    def get_schema_version(self) -> str:
        """Get ontology schema version."""
        ...


# ============================================================================
# Ultra Graph-RAG Protocol
# ============================================================================


@dataclass(frozen=True)
class GraphReasoningPath:
    """
    A reasoning path through the knowledge graph.
    
    Represents multi-hop traversal with attention scores and causal links.
    """
    nodes: List[str]           # Node IDs in path
    edges: List[str]           # Edge types
    scores: List[float]        # Attention scores per hop
    total_score: float         # Aggregate path score
    reasoning_type: str        # "shortest_path", "attention_flow", "causal", etc.
    metadata: Dict[str, Any]   # Path-specific context
    
    def __post_init__(self):
        """Validate invariants."""
        if len(self.nodes) != len(self.edges) + 1:
            raise ValueError("Path must have len(nodes) = len(edges) + 1")
        if len(self.scores) != len(self.edges):
            raise ValueError("Must have one score per edge")
        if not all(0.0 <= s <= 1.0 for s in self.scores):
            raise ValueError("All scores must be in [0.0, 1.0]")


@dataclass(frozen=True)
class UltraRAGResult:
    """
    Result from Ultra Graph-RAG retrieval.
    
    Extends basic RAG with:
    - Multi-hop reasoning paths
    - Causal inference links
    - Explainable attention scores
    - Quantum-inspired scoring
    """
    query: str
    retrieved_documents: List[Dict[str, Any]]  # Basic RAG results
    reasoning_paths: List[GraphReasoningPath]  # Graph reasoning paths
    causal_links: List[Tuple[str, str, float]]  # (cause, effect, strength)
    explainability: Dict[str, Any]  # Attention maps, feature importance
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate invariants."""
        if not self.query or not self.query.strip():
            raise ValueError("query cannot be empty")
        if not isinstance(self.retrieved_documents, list):
            raise TypeError("retrieved_documents must be a list")


@runtime_checkable
class UltraRAGProtocol(Protocol):
    """
    Protocol for Ultra Graph-RAG with advanced reasoning.
    
    Extends basic RAG with:
    - Multi-hop graph traversal
    - Causal inference
    - Quantum-inspired scoring
    - Explainable AI
    
    Implementations must:
    - Be stateless or thread-safe
    - Gracefully degrade if graph unavailable
    - Provide explainability metadata
    - Support configurable reasoning strategies
    """
    
    @abstractmethod
    async def retrieve_with_reasoning(
        self,
        query: str,
        *,
        top_k: int = 10,
        reasoning_strategy: str = "attention_flow",
        enable_causal: bool = True,
        max_hops: int = 3,
        **kwargs: Any
    ) -> UltraRAGResult:
        """
        Retrieve documents with graph-based reasoning.
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            reasoning_strategy: "shortest_path", "attention_flow", "causal", etc.
            enable_causal: Whether to compute causal links
            max_hops: Maximum graph traversal depth
            **kwargs: Strategy-specific parameters
        
        Returns:
            UltraRAGResult with documents + reasoning paths
        
        Raises:
            ValueError: If query empty or invalid strategy
        """
        ...
    
    @abstractmethod
    def explain(self, result: UltraRAGResult) -> Dict[str, Any]:
        """
        Generate human-readable explanation of reasoning.
        
        Args:
            result: UltraRAGResult to explain
        
        Returns:
            Dict with explanation text, attention maps, feature importance
        """
        ...


# ============================================================================
# Helper Functions
# ============================================================================


def is_uncertainty_service(obj: Any) -> bool:
    """Check if object implements UncertaintyServiceProtocol."""
    return isinstance(obj, UncertaintyServiceProtocol)


def is_ontology_gate(obj: Any) -> bool:
    """Check if object implements OntologyGateProtocol."""
    return isinstance(obj, OntologyGateProtocol)


def is_ultra_rag(obj: Any) -> bool:
    """Check if object implements UltraRAGProtocol."""
    return isinstance(obj, UltraRAGProtocol)


__all__ = [
    # Uncertainty
    "UncertaintyEstimate",
    "UncertaintyServiceProtocol",
    "is_uncertainty_service",
    # Ontology
    "OntologyValidationResult",
    "OntologyGateProtocol",
    "is_ontology_gate",
    # Ultra RAG
    "GraphReasoningPath",
    "UltraRAGResult",
    "UltraRAGProtocol",
    "is_ultra_rag",
]

"""
MAHOUN Core Models
==================

Central data models used across the MAHOUN Enterprise system.
These models provide type-safe data structures for reasoning,
uncertainty estimation, and legal document processing.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================================
# Cryptographic Models
# ============================================================================
# 
# NOTE: CryptographicProof has been moved to mahoun/crypto/proof_system.py
# to maintain single source of truth and avoid architectural drift.
# 
# Import from: mahoun.crypto.proof_system.CryptographicProof
# ============================================================================


# ============================================================================
# Legal Document Models
# ============================================================================


class LegalDocType(str, Enum):
    """Legal document types"""

    LAW = "law"
    VERDICT = "verdict"
    REGULATION = "regulation"
    ARTICLE = "article"
    CONTRACT = "contract"
    OPINION = "opinion"
    OTHER = "other"


class LegalDocument(BaseModel):
    """Core legal document model"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique document identifier")
    text: str = Field(..., description="Full document text content")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    doc_type: Optional[LegalDocType] = None
    title: Optional[str] = None
    source_file: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None

    @field_validator("id", "text")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("String field cannot be empty")
        return v


class LegalEntity(BaseModel):
    """Legal entity (person, organization, court, etc.)"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    entity_type: str = Field(..., min_length=1)  # person, organization, court, law
    role: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Reasoning Models
# ============================================================================


class ReasoningStep(BaseModel):
    """Single step in chain of thought reasoning"""

    model_config = ConfigDict(extra="forbid")

    step: str = Field(..., min_length=1)
    reasoning: str = Field(..., min_length=1)
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)


class CausalRelation(BaseModel):
    """Causal relationship between facts"""

    model_config = ConfigDict(extra="forbid")

    cause: str = Field(..., min_length=1)
    effect: str = Field(..., min_length=1)
    strength: float = Field(..., ge=0.0, le=1.0)
    explanation: str = Field(..., min_length=1)


class ReasoningResult(BaseModel):
    """Complete reasoning result"""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    context: str = Field(..., min_length=1)
    facts: List[str] = Field(default_factory=list)
    reasoning_chain: List[ReasoningStep] = Field(default_factory=list)
    causal_chain: List[CausalRelation] = Field(default_factory=list)
    primary_cause: Optional[CausalRelation] = None
    final_answer: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_evidence: List[str] = Field(default_factory=list)
    evidence_strength: str = Field(..., min_length=1)
    visited_nodes: List[str] = Field(default_factory=list)
    graph_edges_used: List[Tuple[str, str]] = Field(default_factory=list)
    used_rule_ids: List[str] = Field(default_factory=list)
    limitations: Optional[str] = None
    graph_dependency_proof: Optional[Any] = None  # CryptographicProof from mahoun.crypto.proof_system
    reasoning_depth: str = "deep"

    def to_trace_json(self) -> Dict[str, Any]:
        """Structured trace for auditing."""
        # Using model_dump for Pydantic V2
        data = self.model_dump()
        return {
            "final_answer": data["final_answer"],
            "confidence": data["confidence"],
            "visited_nodes": data["visited_nodes"],
            "graph_edges_used": [list(edge) for edge in data["graph_edges_used"]],
            "used_rule_ids": data["used_rule_ids"],
            "supporting_evidence": data["supporting_evidence"],
            "causal_chain": data["causal_chain"],
            "graph_dependency_proof": data["graph_dependency_proof"],
            "limitations": data["limitations"],
            "evidence_strength": data["evidence_strength"],
            "reasoning_depth": data["reasoning_depth"],
        }


# ============================================================================
# Uncertainty Models
# ============================================================================


class UncertaintyEstimate(BaseModel):
    """Uncertainty estimation result"""

    model_config = ConfigDict(extra="forbid")

    epistemic: float = Field(0.0, ge=0.0)  # Model uncertainty (reducible)
    aleatoric: float = Field(0.0, ge=0.0)  # Data uncertainty (irreducible)
    total: float = Field(0.0, ge=0.0)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    method: str = "ensemble"
    details: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        if self.total == 0.0:
            self.total = self.epistemic + self.aleatoric


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Legal Documents
    "LegalDocType",
    "LegalDocument",
    "LegalEntity",
    # Reasoning
    "ReasoningStep",
    "CausalRelation",
    "ReasoningResult",
    # Uncertainty
    "UncertaintyEstimate",
]

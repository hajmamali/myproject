"""
Contract Schemas for Core Module

This module defines formal input/output contracts for the core module's public interfaces.
All contracts are Pydantic models with validation rules.

Module: mahoun.core
Responsibility: Core utilities, settings, runtime configuration, and base models
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


# ============================================================================
# Runtime Configuration Contracts
# ============================================================================

class RuntimeMode(str, Enum):
    """Runtime mode enumeration."""
    DESKTOP_MINIMAL = "desktop-minimal"
    ENTERPRISE_GRAPH = "enterprise-graph"
    PRODUCTION = "production"


class RuntimeSettingsOutput(BaseModel):
    """
    Contract for get_runtime_settings() output.
    
    Validates: Runtime settings structure
    """
    mode: RuntimeMode = Field(..., description="Current runtime mode")
    skip_graph: bool = Field(..., description="Whether to skip graph operations")
    skip_lora_training: bool = Field(..., description="Whether to skip LoRA training")
    graph_config: Dict[str, Any] = Field(default_factory=dict, description="Graph configuration")
    
    model_config = ConfigDict(frozen=True)


class BooleanOutput(BaseModel):
    """
    Contract for boolean query functions output.
    
    Used by: is_desktop_minimal(), should_skip_graph(), etc.
    """
    result: bool = Field(..., description="Boolean result")
    
    model_config = ConfigDict(frozen=True)


class GraphConfigOutput(BaseModel):
    """
    Contract for get_graph_config() output.
    
    Validates: Graph configuration structure
    """
    enable_quality_assessment: bool = Field(default=True)
    enable_analytics: bool = Field(default=True)
    enable_real_time_updates: bool = Field(default=False)
    batch_size: int = Field(default=100, ge=1, le=10000)
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Core Models Contracts
# ============================================================================

class LegalDocTypeContract(str, Enum):
    """Contract for LegalDocType enum."""
    VERDICT = "VERDICT"
    CONTRACT = "CONTRACT"
    STATUTE = "STATUTE"
    REGULATION = "REGULATION"
    PRECEDENT = "PRECEDENT"
    OTHER = "OTHER"


class LegalDocumentInput(BaseModel):
    """
    Contract for LegalDocument creation input.
    
    Validates: Document creation parameters
    """
    doc_id: str = Field(..., min_length=1, max_length=255, description="Unique document ID")
    doc_type: LegalDocTypeContract = Field(..., description="Document type")
    title: str = Field(..., min_length=1, max_length=1000, description="Document title")
    content: str = Field(..., min_length=1, description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('doc_id')
    @classmethod
    def validate_doc_id(cls, v: str) -> str:
        """Validate document ID format."""
        if not v.strip():
            raise ValueError("doc_id cannot be empty or whitespace")
        return v.strip()
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title format."""
        if not v.strip():
            raise ValueError("title cannot be empty or whitespace")
        return v.strip()


class LegalDocumentOutput(BaseModel):
    """
    Contract for LegalDocument output.
    
    Validates: Complete document structure
    """
    doc_id: str = Field(..., min_length=1, description="Document ID")
    doc_type: LegalDocTypeContract = Field(..., description="Document type")
    title: str = Field(..., min_length=1, description="Document title")
    content: str = Field(..., min_length=1, description="Document content")
    metadata: Dict[str, Any] = Field(..., description="Metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(frozen=True)


class LegalEntityInput(BaseModel):
    """
    Contract for LegalEntity creation input.
    
    Validates: Entity creation parameters
    """
    entity_id: str = Field(..., min_length=1, max_length=255, description="Unique entity ID")
    entity_type: str = Field(..., min_length=1, max_length=100, description="Entity type")
    name: str = Field(..., min_length=1, max_length=500, description="Entity name")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity properties")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    
    @field_validator('entity_id')
    @classmethod
    def validate_entity_id(cls, v: str) -> str:
        """Validate entity ID format."""
        if not v.strip():
            raise ValueError("entity_id cannot be empty or whitespace")
        return v.strip()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name format."""
        if not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()


class LegalEntityOutput(BaseModel):
    """
    Contract for LegalEntity output.
    
    Validates: Complete entity structure
    """
    entity_id: str = Field(..., min_length=1, description="Entity ID")
    entity_type: str = Field(..., min_length=1, description="Entity type")
    name: str = Field(..., min_length=1, description="Entity name")
    properties: Dict[str, Any] = Field(..., description="Properties")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence")
    
    model_config = ConfigDict(frozen=True)


class ReasoningStepContract(BaseModel):
    """
    Contract for ReasoningStep model.
    
    Validates: Single reasoning step structure
    """
    step: str = Field(..., min_length=1, description="Step description")
    reasoning: str = Field(..., min_length=1, description="Reasoning explanation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Step confidence")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence")
    
    @field_validator('step')
    @classmethod
    def validate_step(cls, v: str) -> str:
        """Validate step format."""
        if not v.strip():
            raise ValueError("step cannot be empty or whitespace")
        return v.strip()
    
    @field_validator('reasoning')
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        """Validate reasoning format."""
        if not v.strip():
            raise ValueError("reasoning cannot be empty or whitespace")
        return v.strip()
    
    model_config = ConfigDict(frozen=True)


class CausalRelationContract(BaseModel):
    """
    Contract for CausalRelation model.
    
    Validates: Causal relationship structure
    """
    cause: str = Field(..., min_length=1, description="Cause description")
    effect: str = Field(..., min_length=1, description="Effect description")
    strength: float = Field(..., ge=0.0, le=1.0, description="Relationship strength")
    explanation: str = Field(default="", description="Explanation of relationship")
    
    @field_validator('cause')
    @classmethod
    def validate_cause(cls, v: str) -> str:
        """Validate cause format."""
        if not v.strip():
            raise ValueError("cause cannot be empty or whitespace")
        return v.strip()
    
    @field_validator('effect')
    @classmethod
    def validate_effect(cls, v: str) -> str:
        """Validate effect format."""
        if not v.strip():
            raise ValueError("effect cannot be empty or whitespace")
        return v.strip()
    
    model_config = ConfigDict(frozen=True)


class ReasoningResultContract(BaseModel):
    """
    Contract for ReasoningResult model.
    
    Validates: Complete reasoning result structure
    """
    question: str = Field(..., min_length=1, description="Original question")
    context: str = Field(default="", description="Context provided")
    facts: List[str] = Field(default_factory=list, description="Input facts")
    reasoning_chain: List[ReasoningStepContract] = Field(..., min_length=1, description="Reasoning steps")
    causal_chain: List[CausalRelationContract] = Field(default_factory=list, description="Causal relationships")
    primary_cause: Optional[str] = Field(default=None, description="Primary cause identified")
    final_answer: str = Field(..., min_length=1, description="Final conclusion")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    supporting_evidence: List[str] = Field(default_factory=list, description="Supporting evidence")
    evidence_strength: float = Field(default=0.0, ge=0.0, le=1.0, description="Evidence strength")
    visited_nodes: List[str] = Field(default_factory=list, description="Graph nodes visited")
    graph_edges_used: List[str] = Field(default_factory=list, description="Graph edges used")
    used_rule_ids: List[str] = Field(default_factory=list, description="Rules applied")
    limitations: Optional[str] = Field(default=None, description="Reasoning limitations")
    graph_dependency_proof: bool = Field(default=False, description="Whether graph was used")
    reasoning_depth: int = Field(default=0, ge=0, description="Reasoning depth")
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate question format."""
        if not v.strip():
            raise ValueError("question cannot be empty or whitespace")
        return v.strip()
    
    @field_validator('final_answer')
    @classmethod
    def validate_final_answer(cls, v: str) -> str:
        """Validate final answer format."""
        if not v.strip():
            raise ValueError("final_answer cannot be empty or whitespace")
        return v.strip()
    
    model_config = ConfigDict(frozen=True)


class UncertaintyEstimateContract(BaseModel):
    """
    Contract for UncertaintyEstimate model.
    
    Validates: Uncertainty quantification structure
    """
    mean: float = Field(..., description="Mean estimate")
    variance: float = Field(..., ge=0.0, description="Variance (must be non-negative)")
    confidence_interval: tuple[float, float] = Field(..., description="Confidence interval (lower, upper)")
    method: str = Field(..., min_length=1, description="Estimation method used")
    
    @field_validator('confidence_interval')
    @classmethod
    def validate_confidence_interval(cls, v: tuple[float, float]) -> tuple[float, float]:
        """Validate confidence interval."""
        if len(v) != 2:
            raise ValueError("confidence_interval must have exactly 2 elements")
        if v[0] > v[1]:
            raise ValueError("confidence_interval lower bound must be <= upper bound")
        return v
    
    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate method format."""
        if not v.strip():
            raise ValueError("method cannot be empty or whitespace")
        return v.strip()
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Error Contracts
# ============================================================================

class CoreModuleError(BaseModel):
    """
    Contract for core module errors.
    
    Error Types:
    - ValidationError: Invalid input parameters
    - ConfigurationError: Invalid runtime configuration
    - StateError: Invalid system state
    """
    error_type: str = Field(..., pattern="^(ValidationError|ConfigurationError|StateError)$")
    message: str = Field(..., min_length=1, description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    recoverable: bool = Field(default=True, description="Whether error is recoverable")
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Contract Registry
# ============================================================================

__all__ = [
    # Runtime Configuration
    "RuntimeMode",
    "RuntimeSettingsOutput",
    "BooleanOutput",
    "GraphConfigOutput",
    
    # Core Models
    "LegalDocTypeContract",
    "LegalDocumentInput",
    "LegalDocumentOutput",
    "LegalEntityInput",
    "LegalEntityOutput",
    "ReasoningStepContract",
    "CausalRelationContract",
    "ReasoningResultContract",
    "UncertaintyEstimateContract",
    
    # Errors
    "CoreModuleError",
]

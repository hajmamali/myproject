"""
Reasoning Module Contracts
===========================

Formal contracts for the reasoning module's public interfaces.

These contracts define:
- Input validation rules
- Output structure guarantees
- Error conditions and types
- Invariant enforcement points

All contracts use `extra="forbid"` to ensure clean data structures.

Validates Requirements: 2.1, 2.2, 2.3
"""

from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ============================================================================
# EvidenceLinkedVerdictEngine Contracts
# ============================================================================

class EvidenceReferenceContract(BaseModel):
    """
    Contract for evidence reference linking verdict to graph.
    
    Validates: Requirement 2.1 - Evidence linking
    Enforces: G2 (Evidence references must resolve)
    """
    node_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Graph node identifier"
    )
    node_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Node type (Fact, LegalRule, LegalPrecedent)"
    )
    edge_id: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional edge identifier"
    )
    justification: str = Field(
        default="",
        max_length=2000,
        description="Human-readable justification"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this evidence"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "node_id": "rule_contract_breach",
                "node_type": "LegalRule",
                "edge_id": "edge_123",
                "justification": "Rule applies to contract violation",
                "confidence": 0.95
            }
        }
    )


class VerdictStepContract(BaseModel):
    """
    Contract for single reasoning step in verdict chain.
    
    Validates: Requirement 2.1 - Reasoning steps
    Enforces: G1 (Every step must have evidence)
    """
    statement: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Reasoning statement"
    )
    evidence: List[EvidenceReferenceContract] = Field(
        ...,
        min_length=1,
        description="Evidence supporting this step (G1: must have at least one)"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "statement": "طرف متخلف موظف به جبران خسارت است",
                "evidence": [
                    {
                        "node_id": "rule_contract_breach",
                        "node_type": "LegalRule",
                        "justification": "Article 220 Civil Code",
                        "confidence": 0.95
                    }
                ]
            }
        }
    )


class GenerateVerdictInput(BaseModel):
    """
    Input contract for EvidenceLinkedVerdictEngine.generate_verdict()
    
    Validates: Requirement 2.1 - Input validation
    Enforces: EL-I7 (Privacy preservation - only fact IDs, no values)
    """
    question: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Legal question to answer"
    )
    facts: List[Any] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Case facts (strings or dicts with 'id' field)"
    )
    
    @field_validator('facts')
    @classmethod
    def validate_facts_structure(cls, v: List[Any]) -> List[Any]:
        """Ensure facts have proper structure for privacy filtering."""
        for i, fact in enumerate(v):
            if isinstance(fact, dict):
                if 'id' not in fact:
                    raise ValueError(f"Fact at index {i} must have 'id' field")
            elif not isinstance(fact, str):
                raise ValueError(f"Fact at index {i} must be string or dict")
        return v
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "question": "آیا طرف متخلف مسئول جبران خسارت است؟",
                "facts": [
                    "عدم انجام تعهدات قراردادی",
                    "خسارت مالی وارد شده"
                ]
            }
        }
    )


class GenerateVerdictOutput(BaseModel):
    """
    Output contract for EvidenceLinkedVerdictEngine.generate_verdict()
    
    Validates: Requirement 2.2 - Output structure
    Enforces: G4 (Unresolved conflicts → UNDETERMINED verdict)
    """
    final_verdict: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Final verdict text"
    )
    steps: List[VerdictStepContract] = Field(
        ...,
        min_length=1,
        description="Reasoning steps with evidence links"
    )
    unresolved_conflicts: List[str] = Field(
        default_factory=list,
        description="List of unresolved contradictions"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence score"
    )
    
    @model_validator(mode='after')
    def validate_undetermined_verdict(self) -> 'GenerateVerdictOutput':
        """
        Enforce G4: If unresolved conflicts exist, verdict must be UNDETERMINED.
        """
        if self.unresolved_conflicts and len(self.unresolved_conflicts) > 0:
            if 'UNDETERMINED' not in self.final_verdict.upper() and 'نامشخص' not in self.final_verdict:
                raise ValueError(
                    "G4 Violation: Verdict must be UNDETERMINED when unresolved conflicts exist"
                )
        return self
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "final_verdict": "طرف متخلف موظف به جبران خسارت است",
                "steps": [
                    {
                        "statement": "عدم انجام تعهدات قراردادی",
                        "evidence": [
                            {
                                "node_id": "fact_0",
                                "node_type": "Fact",
                                "confidence": 1.0
                            }
                        ]
                    }
                ],
                "unresolved_conflicts": [],
                "confidence_score": 0.92
            }
        }
    )


class GenerateVerdictError(BaseModel):
    """
    Error contract for EvidenceLinkedVerdictEngine.generate_verdict() failures.
    
    Validates: Requirement 2.3 - Error handling
    
    Failure Modes:
    - privacy_violation: Sensitive facts detected (EL-I7)
    - ledger_write_failure: Ledger write failed (EL-I3)
    - insufficient_evidence: Not enough evidence to generate verdict
    - empty_facts: No facts provided
    """
    error_type: str = Field(
        ...,
        pattern="^(privacy_violation|ledger_write_failure|insufficient_evidence|empty_facts)$",
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
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "error_type": "privacy_violation",
                "message": "Sensitive facts detected in input",
                "details": {
                    "sensitive_fact_ids": ["fact_3"],
                    "sensitive_types": ["PERSONAL_ID"]
                }
            }
        }
    )


# ============================================================================
# ChainOfThoughtReasoner Contracts
# ============================================================================

class ReasonInput(BaseModel):
    """
    Input contract for ChainOfThoughtReasoner.reason()
    
    Validates: Requirement 2.1 - Input validation
    """
    question: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Legal question"
    )
    context: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="Context text"
    )
    facts: List[str] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Extracted facts"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "question": "آیا قرارداد معتبر است؟",
                "context": "متن کامل پرونده...",
                "facts": ["توافق طرفین", "امضای قرارداد"]
            }
        }
    )


class ReasoningStepContract(BaseModel):
    """
    Contract for single reasoning step.
    
    Validates: Requirement 2.2 - Reasoning step structure
    """
    step: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Step identifier (e.g., 'question_analysis')"
    )
    reasoning: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Reasoning explanation"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Step confidence"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Supporting evidence"
    )
    
    model_config = ConfigDict(extra="forbid")


class ReasonOutput(BaseModel):
    """
    Output contract for ChainOfThoughtReasoner.reason()
    
    Validates: Requirement 2.2 - Output structure
    """
    answer: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Final answer"
    )
    reasoning_chain: List[ReasoningStepContract] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Chain of reasoning steps"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence"
    )
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Supporting evidence list"
    )
    graph_edges_used: List[Tuple[str, str]] = Field(
        default_factory=list,
        description="Graph edges traversed"
    )
    reachable_nodes: List[str] = Field(
        default_factory=list,
        description="Nodes reachable from facts"
    )
    graph_paths_used: List[List[str]] = Field(
        default_factory=list,
        description="Paths found in graph"
    )
    used_rule_ids: List[str] = Field(
        default_factory=list,
        description="Rules applied"
    )
    graph_dependency_proof: bool = Field(
        default=False,
        description="Whether graph was used for reasoning"
    )
    limitations: Optional[str] = Field(
        None,
        max_length=500,
        description="Reasoning limitations (e.g., 'graph_missing_or_empty')"
    )
    contradictions_detected: bool = Field(
        default=False,
        description="Whether contradictions were found"
    )
    rule_applications: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Metadata for each applied rule"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "answer": "قرارداد معتبر است",
                "reasoning_chain": [
                    {
                        "step": "question_analysis",
                        "reasoning": "سوال از نوع validity تشخیص داده شد",
                        "confidence": 0.8,
                        "evidence": []
                    }
                ],
                "confidence": 0.85,
                "supporting_evidence": ["ماده 190 قانون مدنی"],
                "graph_edges_used": [],
                "reachable_nodes": ["fact_0", "fact_1"],
                "graph_paths_used": [],
                "used_rule_ids": ["contract_validity"],
                "graph_dependency_proof": True,
                "limitations": None,
                "contradictions_detected": False,
                "rule_applications": []
            }
        }
    )


class ReasonError(BaseModel):
    """
    Error contract for ChainOfThoughtReasoner.reason() failures.
    
    Validates: Requirement 2.3 - Error handling
    
    Failure Modes:
    - no_rules_found: No applicable rules found
    - no_precedents_found: No similar precedents found
    - graph_unavailable: Graph not available or empty
    - contradictions_unresolved: Contradictions cannot be resolved
    """
    error_type: str = Field(
        ...,
        pattern="^(no_rules_found|no_precedents_found|graph_unavailable|contradictions_unresolved)$",
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
# DeepLegalReasoningEngine Contracts
# ============================================================================

class DeepReasonInput(BaseModel):
    """
    Input contract for DeepLegalReasoningEngine.deep_reason()
    
    Validates: Requirement 2.1 - Input validation
    """
    question: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Legal question"
    )
    context: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="Context text"
    )
    facts: Optional[List[str]] = Field(
        None,
        max_length=1000,
        description="Optional extracted facts (auto-extracted if None)"
    )
    
    model_config = ConfigDict(extra="forbid")


class CausalRelationContract(BaseModel):
    """
    Contract for causal relationship.
    
    Validates: Requirement 2.2 - Causal relation structure
    """
    cause: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Cause fact"
    )
    effect: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Effect fact"
    )
    strength: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Causal relationship strength"
    )
    explanation: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Explanation of causal link"
    )
    
    model_config = ConfigDict(extra="forbid")


class DeepReasonOutput(BaseModel):
    """
    Output contract for DeepLegalReasoningEngine.deep_reason()
    
    Validates: Requirement 2.2 - Output structure
    """
    question: str = Field(..., description="Original question")
    context: str = Field(..., description="Original context")
    facts: List[str] = Field(..., description="Facts used")
    reasoning_chain: List[ReasoningStepContract] = Field(
        ...,
        min_length=1,
        description="Chain of thought steps"
    )
    causal_chain: List[CausalRelationContract] = Field(
        default_factory=list,
        description="Causal relationships"
    )
    primary_cause: Optional[CausalRelationContract] = Field(
        None,
        description="Primary causal relationship"
    )
    final_answer: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Final synthesized answer"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence"
    )
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Supporting evidence"
    )
    evidence_strength: str = Field(
        ...,
        pattern="^(قوی|متوسط|ضعیف)$",
        description="Evidence strength assessment"
    )
    visited_nodes: List[str] = Field(
        default_factory=list,
        description="Graph nodes visited"
    )
    graph_edges_used: List[Tuple[str, str]] = Field(
        default_factory=list,
        description="Graph edges used"
    )
    used_rule_ids: List[str] = Field(
        default_factory=list,
        description="Rules applied"
    )
    limitations: Optional[str] = Field(
        None,
        max_length=500,
        description="Reasoning limitations"
    )
    graph_dependency_proof: bool = Field(
        default=False,
        description="Graph dependency proof"
    )
    reasoning_depth: str = Field(
        default="deep",
        pattern="^(shallow|medium|deep)$",
        description="Reasoning depth level"
    )
    
    model_config = ConfigDict(extra="forbid")


class DeepReasonError(BaseModel):
    """
    Error contract for DeepLegalReasoningEngine.deep_reason() failures.
    
    Validates: Requirement 2.3 - Error handling
    
    Failure Modes:
    - insufficient_context: Context too short or empty
    - fact_extraction_failed: Could not extract facts from context
    - reasoning_failed: Reasoning process failed
    - causal_inference_failed: Causal inference failed
    """
    error_type: str = Field(
        ...,
        pattern="^(insufficient_context|fact_extraction_failed|reasoning_failed|causal_inference_failed)$",
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
    # EvidenceLinkedVerdictEngine
    "EvidenceReferenceContract",
    "VerdictStepContract",
    "GenerateVerdictInput",
    "GenerateVerdictOutput",
    "GenerateVerdictError",
    # ChainOfThoughtReasoner
    "ReasonInput",
    "ReasoningStepContract",
    "ReasonOutput",
    "ReasonError",
    # DeepLegalReasoningEngine
    "DeepReasonInput",
    "CausalRelationContract",
    "DeepReasonOutput",
    "DeepReasonError",
]

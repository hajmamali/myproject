"""
Reasoning Module Contract Tests
================================

Tests for reasoning module Pydantic contracts.

These tests validate:
- Input schema compliance
- Output schema compliance
- Error schema compliance
- Field validation rules
- Invariant enforcement (G1, G2, G4, EL-I7)

IMPORTANT: These are CONTRACT tests, not BEHAVIOR tests.
They test data structure integrity, not reasoning logic.

Validates Requirements: 2.1, 2.2, 2.3
"""

import pytest
from pydantic import ValidationError
from typing import List, Dict, Any

from mahoun.schemas.contracts.reasoning_contracts import (
    # EvidenceLinkedVerdictEngine
    EvidenceReferenceContract,
    VerdictStepContract,
    GenerateVerdictInput,
    GenerateVerdictOutput,
    GenerateVerdictError,
    # ChainOfThoughtReasoner
    ReasonInput,
    ReasoningStepContract,
    ReasonOutput,
    ReasonError,
    # DeepLegalReasoningEngine
    DeepReasonInput,
    CausalRelationContract,
    DeepReasonOutput,
    DeepReasonError,
)


# ============================================================================
# EvidenceReferenceContract Tests
# ============================================================================

class TestEvidenceReferenceContract:
    """Test EvidenceReferenceContract validation."""
    
    def test_valid_evidence_reference(self):
        """Valid evidence reference should pass."""
        ref = EvidenceReferenceContract(
            node_id="rule_123",
            node_type="LegalRule",
            edge_id="edge_456",
            justification="Article 220 Civil Code",
            confidence=0.95
        )
        assert ref.node_id == "rule_123"
        assert ref.node_type == "LegalRule"
        assert ref.confidence == 0.95
    
    def test_minimal_evidence_reference(self):
        """Minimal evidence reference (no edge_id, no justification) should pass."""
        ref = EvidenceReferenceContract(
            node_id="fact_0",
            node_type="Fact",
            confidence=1.0
        )
        assert ref.node_id == "fact_0"
        assert ref.edge_id is None
        assert ref.justification == ""
    
    def test_empty_node_id_fails(self):
        """Empty node_id should fail."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceReferenceContract(
                node_id="",
                node_type="Fact",
                confidence=0.8
            )
        assert "node_id" in str(exc_info.value)
    
    def test_confidence_out_of_range_fails(self):
        """Confidence outside [0, 1] should fail."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceReferenceContract(
                node_id="rule_123",
                node_type="LegalRule",
                confidence=1.5
            )
        assert "confidence" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            EvidenceReferenceContract(
                node_id="rule_123",
                node_type="LegalRule",
                confidence=-0.1
            )
        assert "confidence" in str(exc_info.value)
    
    def test_extra_fields_forbidden(self):
        """Extra fields should be rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceReferenceContract(
                node_id="rule_123",
                node_type="LegalRule",
                confidence=0.9,
                extra_field="not_allowed"
            )
        assert "extra_field" in str(exc_info.value).lower()


# ============================================================================
# VerdictStepContract Tests
# ============================================================================

class TestVerdictStepContract:
    """Test VerdictStepContract validation (enforces G1)."""
    
    def test_valid_verdict_step(self):
        """Valid verdict step with evidence should pass."""
        step = VerdictStepContract(
            statement="طرف متخلف موظف به جبران خسارت است",
            evidence=[
                EvidenceReferenceContract(
                    node_id="rule_contract_breach",
                    node_type="LegalRule",
                    confidence=0.95
                )
            ]
        )
        assert len(step.evidence) == 1
        assert step.evidence[0].node_id == "rule_contract_breach"
    
    def test_empty_statement_fails(self):
        """Empty statement should fail."""
        with pytest.raises(ValidationError) as exc_info:
            VerdictStepContract(
                statement="",
                evidence=[
                    EvidenceReferenceContract(
                        node_id="rule_123",
                        node_type="LegalRule",
                        confidence=0.9
                    )
                ]
            )
        assert "statement" in str(exc_info.value)
    
    def test_empty_evidence_fails_g1(self):
        """Empty evidence list should fail (G1: every step must have evidence)."""
        with pytest.raises(ValidationError) as exc_info:
            VerdictStepContract(
                statement="Some reasoning step",
                evidence=[]
            )
        assert "evidence" in str(exc_info.value)
    
    def test_multiple_evidence_references(self):
        """Multiple evidence references should pass."""
        step = VerdictStepContract(
            statement="Combined reasoning",
            evidence=[
                EvidenceReferenceContract(
                    node_id="rule_1",
                    node_type="LegalRule",
                    confidence=0.9
                ),
                EvidenceReferenceContract(
                    node_id="precedent_1",
                    node_type="LegalPrecedent",
                    confidence=0.85
                )
            ]
        )
        assert len(step.evidence) == 2


# ============================================================================
# GenerateVerdictInput Tests
# ============================================================================

class TestGenerateVerdictInput:
    """Test GenerateVerdictInput validation (enforces EL-I7)."""
    
    def test_valid_input_with_string_facts(self):
        """Valid input with string facts should pass."""
        inp = GenerateVerdictInput(
            question="آیا طرف متخلف مسئول است؟",
            facts=["عدم انجام تعهدات", "خسارت مالی"]
        )
        assert len(inp.facts) == 2
        assert isinstance(inp.facts[0], str)
    
    def test_valid_input_with_dict_facts(self):
        """Valid input with dict facts (with 'id' field) should pass."""
        inp = GenerateVerdictInput(
            question="آیا قرارداد معتبر است؟",
            facts=[
                {"id": "fact_0", "text": "توافق طرفین"},
                {"id": "fact_1", "text": "امضای قرارداد"}
            ]
        )
        assert len(inp.facts) == 2
        assert inp.facts[0]["id"] == "fact_0"
    
    def test_empty_question_fails(self):
        """Empty question should fail."""
        with pytest.raises(ValidationError) as exc_info:
            GenerateVerdictInput(
                question="",
                facts=["fact1"]
            )
        assert "question" in str(exc_info.value)
    
    def test_empty_facts_fails(self):
        """Empty facts list should fail."""
        with pytest.raises(ValidationError) as exc_info:
            GenerateVerdictInput(
                question="سوال قانونی",
                facts=[]
            )
        assert "facts" in str(exc_info.value)
    
    def test_dict_fact_without_id_fails(self):
        """Dict fact without 'id' field should fail (EL-I7)."""
        with pytest.raises(ValidationError) as exc_info:
            GenerateVerdictInput(
                question="سوال قانونی",
                facts=[
                    {"text": "fact without id"}
                ]
            )
        assert "id" in str(exc_info.value).lower()
    
    def test_invalid_fact_type_fails(self):
        """Fact with invalid type (not str or dict) should fail."""
        with pytest.raises(ValidationError) as exc_info:
            GenerateVerdictInput(
                question="سوال قانونی",
                facts=[123, 456]  # Invalid: integers
            )
        assert "must be string or dict" in str(exc_info.value).lower()
    
    def test_too_many_facts_fails(self):
        """More than 1000 facts should fail."""
        with pytest.raises(ValidationError) as exc_info:
            GenerateVerdictInput(
                question="سوال قانونی",
                facts=[f"fact_{i}" for i in range(1001)]
            )
        assert "facts" in str(exc_info.value)


# ============================================================================
# GenerateVerdictOutput Tests
# ============================================================================

class TestGenerateVerdictOutput:
    """Test GenerateVerdictOutput validation (enforces G4)."""
    
    def test_valid_output_no_conflicts(self):
        """Valid output without conflicts should pass."""
        output = GenerateVerdictOutput(
            final_verdict="طرف متخلف موظف به جبران خسارت است",
            steps=[
                VerdictStepContract(
                    statement="عدم انجام تعهدات",
                    evidence=[
                        EvidenceReferenceContract(
                            node_id="fact_0",
                            node_type="Fact",
                            confidence=1.0
                        )
                    ]
                )
            ],
            unresolved_conflicts=[],
            confidence_score=0.92
        )
        assert output.confidence_score == 0.92
        assert len(output.unresolved_conflicts) == 0
    
    def test_valid_output_with_undetermined_verdict(self):
        """Output with conflicts and UNDETERMINED verdict should pass (G4)."""
        output = GenerateVerdictOutput(
            final_verdict="UNDETERMINED: تناقض در شواهد",
            steps=[
                VerdictStepContract(
                    statement="شواهد متناقض",
                    evidence=[
                        EvidenceReferenceContract(
                            node_id="rule_1",
                            node_type="LegalRule",
                            confidence=0.8
                        )
                    ]
                )
            ],
            unresolved_conflicts=["تناقض بین ماده 190 و 220"],
            confidence_score=0.5
        )
        assert len(output.unresolved_conflicts) == 1
        assert "UNDETERMINED" in output.final_verdict
    
    def test_conflicts_without_undetermined_verdict_fails_g4(self):
        """Conflicts without UNDETERMINED verdict should fail (G4)."""
        with pytest.raises(ValidationError) as exc_info:
            GenerateVerdictOutput(
                final_verdict="طرف متخلف مسئول است",  # No UNDETERMINED
                steps=[
                    VerdictStepContract(
                        statement="reasoning",
                        evidence=[
                            EvidenceReferenceContract(
                                node_id="rule_1",
                                node_type="LegalRule",
                                confidence=0.8
                            )
                        ]
                    )
                ],
                unresolved_conflicts=["conflict exists"],  # Conflicts present
                confidence_score=0.7
            )
        assert "G4" in str(exc_info.value) or "UNDETERMINED" in str(exc_info.value)
    
    def test_empty_steps_fails(self):
        """Empty steps list should fail."""
        with pytest.raises(ValidationError) as exc_info:
            GenerateVerdictOutput(
                final_verdict="verdict",
                steps=[],
                confidence_score=0.8
            )
        assert "steps" in str(exc_info.value)
    
    def test_confidence_out_of_range_fails(self):
        """Confidence outside [0, 1] should fail."""
        with pytest.raises(ValidationError) as exc_info:
            GenerateVerdictOutput(
                final_verdict="verdict",
                steps=[
                    VerdictStepContract(
                        statement="step",
                        evidence=[
                            EvidenceReferenceContract(
                                node_id="rule_1",
                                node_type="LegalRule",
                                confidence=0.9
                            )
                        ]
                    )
                ],
                confidence_score=1.5
            )
        assert "confidence_score" in str(exc_info.value)


# ============================================================================
# GenerateVerdictError Tests
# ============================================================================

class TestGenerateVerdictError:
    """Test GenerateVerdictError validation."""
    
    def test_valid_privacy_violation_error(self):
        """Valid privacy violation error should pass."""
        error = GenerateVerdictError(
            error_type="privacy_violation",
            message="Sensitive facts detected",
            details={
                "sensitive_fact_ids": ["fact_3"],
                "sensitive_types": ["PERSONAL_ID"]
            }
        )
        assert error.error_type == "privacy_violation"
        assert error.details is not None
    
    def test_valid_error_without_details(self):
        """Valid error without details should pass."""
        error = GenerateVerdictError(
            error_type="insufficient_evidence",
            message="Not enough evidence"
        )
        assert error.details is None
    
    def test_invalid_error_type_fails(self):
        """Invalid error_type should fail."""
        with pytest.raises(ValidationError) as exc_info:
            GenerateVerdictError(
                error_type="invalid_error_type",
                message="Some error"
            )
        assert "error_type" in str(exc_info.value)
    
    def test_all_valid_error_types(self):
        """All documented error types should be valid."""
        valid_types = [
            "privacy_violation",
            "ledger_write_failure",
            "insufficient_evidence",
            "empty_facts"
        ]
        for error_type in valid_types:
            error = GenerateVerdictError(
                error_type=error_type,
                message=f"Test {error_type}"
            )
            assert error.error_type == error_type


# ============================================================================
# ReasonInput Tests
# ============================================================================

class TestReasonInput:
    """Test ReasonInput validation."""
    
    def test_valid_input(self):
        """Valid input should pass."""
        inp = ReasonInput(
            question="آیا قرارداد معتبر است؟",
            context="متن کامل پرونده...",
            facts=["توافق طرفین", "امضای قرارداد"]
        )
        assert len(inp.facts) == 2
    
    def test_empty_question_fails(self):
        """Empty question should fail."""
        with pytest.raises(ValidationError):
            ReasonInput(
                question="",
                context="context",
                facts=["fact1"]
            )
    
    def test_empty_context_fails(self):
        """Empty context should fail."""
        with pytest.raises(ValidationError):
            ReasonInput(
                question="question",
                context="",
                facts=["fact1"]
            )
    
    def test_empty_facts_fails(self):
        """Empty facts list should fail."""
        with pytest.raises(ValidationError):
            ReasonInput(
                question="question",
                context="context",
                facts=[]
            )


# ============================================================================
# ReasoningStepContract Tests
# ============================================================================

class TestReasoningStepContract:
    """Test ReasoningStepContract validation."""
    
    def test_valid_step(self):
        """Valid reasoning step should pass."""
        step = ReasoningStepContract(
            step="question_analysis",
            reasoning="سوال از نوع validity تشخیص داده شد",
            confidence=0.8,
            evidence=["ماده 190"]
        )
        assert step.step == "question_analysis"
        assert step.confidence == 0.8
    
    def test_step_without_evidence(self):
        """Step without evidence should pass (evidence is optional)."""
        step = ReasoningStepContract(
            step="initial_analysis",
            reasoning="تحلیل اولیه",
            confidence=0.7
        )
        assert len(step.evidence) == 0
    
    def test_confidence_out_of_range_fails(self):
        """Confidence outside [0, 1] should fail."""
        with pytest.raises(ValidationError):
            ReasoningStepContract(
                step="step1",
                reasoning="reasoning",
                confidence=2.0
            )


# ============================================================================
# ReasonOutput Tests
# ============================================================================

class TestReasonOutput:
    """Test ReasonOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = ReasonOutput(
            answer="قرارداد معتبر است",
            reasoning_chain=[
                ReasoningStepContract(
                    step="question_analysis",
                    reasoning="تحلیل سوال",
                    confidence=0.8
                )
            ],
            confidence=0.85,
            supporting_evidence=["ماده 190"],
            graph_dependency_proof=True
        )
        assert output.confidence == 0.85
        assert output.graph_dependency_proof is True
    
    def test_empty_reasoning_chain_fails(self):
        """Empty reasoning chain should fail."""
        with pytest.raises(ValidationError):
            ReasonOutput(
                answer="answer",
                reasoning_chain=[],
                confidence=0.8
            )
    
    def test_too_many_steps_fails(self):
        """More than 20 reasoning steps should fail."""
        with pytest.raises(ValidationError):
            ReasonOutput(
                answer="answer",
                reasoning_chain=[
                    ReasoningStepContract(
                        step=f"step_{i}",
                        reasoning="reasoning",
                        confidence=0.8
                    )
                    for i in range(21)
                ],
                confidence=0.8
            )
    
    def test_all_optional_fields_default(self):
        """All optional fields should have defaults."""
        output = ReasonOutput(
            answer="answer",
            reasoning_chain=[
                ReasoningStepContract(
                    step="step1",
                    reasoning="reasoning",
                    confidence=0.8
                )
            ],
            confidence=0.85
        )
        assert output.supporting_evidence == []
        assert output.graph_edges_used == []
        assert output.reachable_nodes == []
        assert output.graph_paths_used == []
        assert output.used_rule_ids == []
        assert output.graph_dependency_proof is False
        assert output.limitations is None
        assert output.contradictions_detected is False
        assert output.rule_applications == []


# ============================================================================
# ReasonError Tests
# ============================================================================

class TestReasonError:
    """Test ReasonError validation."""
    
    def test_valid_error(self):
        """Valid error should pass."""
        error = ReasonError(
            error_type="no_rules_found",
            message="No applicable rules found"
        )
        assert error.error_type == "no_rules_found"
    
    def test_all_valid_error_types(self):
        """All documented error types should be valid."""
        valid_types = [
            "no_rules_found",
            "no_precedents_found",
            "graph_unavailable",
            "contradictions_unresolved"
        ]
        for error_type in valid_types:
            error = ReasonError(
                error_type=error_type,
                message=f"Test {error_type}"
            )
            assert error.error_type == error_type
    
    def test_invalid_error_type_fails(self):
        """Invalid error_type should fail."""
        with pytest.raises(ValidationError):
            ReasonError(
                error_type="invalid_type",
                message="message"
            )


# ============================================================================
# DeepReasonInput Tests
# ============================================================================

class TestDeepReasonInput:
    """Test DeepReasonInput validation."""
    
    def test_valid_input_with_facts(self):
        """Valid input with facts should pass."""
        inp = DeepReasonInput(
            question="سوال قانونی",
            context="متن پرونده",
            facts=["fact1", "fact2"]
        )
        assert len(inp.facts) == 2
    
    def test_valid_input_without_facts(self):
        """Valid input without facts (auto-extract) should pass."""
        inp = DeepReasonInput(
            question="سوال قانونی",
            context="متن پرونده"
        )
        assert inp.facts is None
    
    def test_empty_question_fails(self):
        """Empty question should fail."""
        with pytest.raises(ValidationError):
            DeepReasonInput(
                question="",
                context="context"
            )


# ============================================================================
# CausalRelationContract Tests
# ============================================================================

class TestCausalRelationContract:
    """Test CausalRelationContract validation."""
    
    def test_valid_causal_relation(self):
        """Valid causal relation should pass."""
        relation = CausalRelationContract(
            cause="عدم انجام تعهدات",
            effect="خسارت مالی",
            strength=0.85,
            explanation="عدم انجام تعهدات منجر به خسارت شد"
        )
        assert relation.strength == 0.85
    
    def test_strength_out_of_range_fails(self):
        """Strength outside [0, 1] should fail."""
        with pytest.raises(ValidationError):
            CausalRelationContract(
                cause="cause",
                effect="effect",
                strength=1.5,
                explanation="explanation"
            )


# ============================================================================
# DeepReasonOutput Tests
# ============================================================================

class TestDeepReasonOutput:
    """Test DeepReasonOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = DeepReasonOutput(
            question="سوال",
            context="متن",
            facts=["fact1"],
            reasoning_chain=[
                ReasoningStepContract(
                    step="step1",
                    reasoning="reasoning",
                    confidence=0.8
                )
            ],
            final_answer="پاسخ نهایی",
            confidence=0.85,
            evidence_strength="قوی"
        )
        assert output.confidence == 0.85
        assert output.evidence_strength == "قوی"
    
    def test_invalid_evidence_strength_fails(self):
        """Invalid evidence_strength should fail."""
        with pytest.raises(ValidationError):
            DeepReasonOutput(
                question="سوال",
                context="متن",
                facts=["fact1"],
                reasoning_chain=[
                    ReasoningStepContract(
                        step="step1",
                        reasoning="reasoning",
                        confidence=0.8
                    )
                ],
                final_answer="پاسخ",
                confidence=0.85,
                evidence_strength="invalid"  # Must be قوی, متوسط, or ضعیف
            )
    
    def test_invalid_reasoning_depth_fails(self):
        """Invalid reasoning_depth should fail."""
        with pytest.raises(ValidationError):
            DeepReasonOutput(
                question="سوال",
                context="متن",
                facts=["fact1"],
                reasoning_chain=[
                    ReasoningStepContract(
                        step="step1",
                        reasoning="reasoning",
                        confidence=0.8
                    )
                ],
                final_answer="پاسخ",
                confidence=0.85,
                evidence_strength="قوی",
                reasoning_depth="invalid"  # Must be shallow, medium, or deep
            )


# ============================================================================
# DeepReasonError Tests
# ============================================================================

class TestDeepReasonError:
    """Test DeepReasonError validation."""
    
    def test_valid_error(self):
        """Valid error should pass."""
        error = DeepReasonError(
            error_type="insufficient_context",
            message="Context too short"
        )
        assert error.error_type == "insufficient_context"
    
    def test_all_valid_error_types(self):
        """All documented error types should be valid."""
        valid_types = [
            "insufficient_context",
            "fact_extraction_failed",
            "reasoning_failed",
            "causal_inference_failed"
        ]
        for error_type in valid_types:
            error = DeepReasonError(
                error_type=error_type,
                message=f"Test {error_type}"
            )
            assert error.error_type == error_type
    
    def test_invalid_error_type_fails(self):
        """Invalid error_type should fail."""
        with pytest.raises(ValidationError):
            DeepReasonError(
                error_type="invalid_type",
                message="message"
            )


# ============================================================================
# Integration Tests
# ============================================================================

class TestContractIntegration:
    """Test contract integration and composition."""
    
    def test_nested_contracts_validation(self):
        """Nested contracts should validate recursively."""
        # Invalid nested evidence should fail at top level
        with pytest.raises(ValidationError):
            GenerateVerdictOutput(
                final_verdict="verdict",
                steps=[
                    VerdictStepContract(
                        statement="step",
                        evidence=[
                            EvidenceReferenceContract(
                                node_id="rule_1",
                                node_type="LegalRule",
                                confidence=2.0  # Invalid: > 1.0
                            )
                        ]
                    )
                ],
                confidence_score=0.8
            )
    
    def test_g1_and_g4_enforcement_together(self):
        """G1 (evidence required) and G4 (conflicts → UNDETERMINED) should work together."""
        # Valid: Has evidence (G1) and UNDETERMINED with conflicts (G4)
        output = GenerateVerdictOutput(
            final_verdict="UNDETERMINED",
            steps=[
                VerdictStepContract(
                    statement="step with evidence",
                    evidence=[
                        EvidenceReferenceContract(
                            node_id="rule_1",
                            node_type="LegalRule",
                            confidence=0.8
                        )
                    ]
                )
            ],
            unresolved_conflicts=["conflict1"],
            confidence_score=0.5
        )
        assert len(output.steps[0].evidence) >= 1  # G1
        assert "UNDETERMINED" in output.final_verdict  # G4
    
    def test_extra_forbid_at_all_levels(self):
        """extra='forbid' should be enforced at all nesting levels."""
        # Extra field at top level should fail
        with pytest.raises(ValidationError):
            GenerateVerdictOutput(
                final_verdict="verdict",
                steps=[
                    VerdictStepContract(
                        statement="step",
                        evidence=[
                            EvidenceReferenceContract(
                                node_id="rule_1",
                                node_type="LegalRule",
                                confidence=0.9
                            )
                        ]
                    )
                ],
                confidence_score=0.8,
                extra_field="not_allowed"
            )
        
        # Extra field at nested level should fail
        with pytest.raises(ValidationError):
            VerdictStepContract(
                statement="step",
                evidence=[
                    EvidenceReferenceContract(
                        node_id="rule_1",
                        node_type="LegalRule",
                        confidence=0.9,
                        extra_nested="not_allowed"
                    )
                ]
            )

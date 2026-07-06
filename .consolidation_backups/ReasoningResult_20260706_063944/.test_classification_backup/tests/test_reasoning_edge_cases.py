"""Edge case tests for reasoning components"""
import pytest
from mahoun.core.models import ReasoningStep, ReasoningResult, CausalRelation


def test_empty_reasoning_chain():
    """Empty reasoning chain should be allowed"""
    result = ReasoningResult(
        question="Q", context="C", facts=["F"],
        reasoning_chain=[], causal_chain=[],
        primary_cause=None, final_answer="A",
        confidence=0.5, supporting_evidence=["E"],
        evidence_strength="weak"
    )
    assert len(result.reasoning_chain) == 0


def test_confidence_bounds_low():
    """Confidence at 0.0 should be valid"""
    step = ReasoningStep(step="1", reasoning="test", confidence=0.0)
    assert step.confidence == 0.0


def test_confidence_bounds_high():
    """Confidence at 1.0 should be valid"""
    step = ReasoningStep(step="1", reasoning="test", confidence=1.0)
    assert step.confidence == 1.0


def test_empty_evidence():
    """Empty evidence list should be allowed"""
    step = ReasoningStep(step="1", reasoning="test", evidence=[])
    assert step.evidence == []


def test_empty_facts():
    """Empty facts list should be allowed"""
    result = ReasoningResult(
        question="Q", context="C", facts=[],
        reasoning_chain=[], causal_chain=[],
        primary_cause=None, final_answer="A",
        confidence=0.5, supporting_evidence=[],
        evidence_strength="none"
    )
    assert result.facts == []


def test_empty_question():
    """Empty question string should be allowed"""
    result = ReasoningResult(
        question="", context="C", facts=["F"],
        reasoning_chain=[], causal_chain=[],
        primary_cause=None, final_answer="A",
        confidence=0.5, supporting_evidence=["E"],
        evidence_strength="weak"
    )
    assert result.question == ""

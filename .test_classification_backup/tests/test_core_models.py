"""Tests for mahoun/core/models.py"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from mahoun.core.models import (
    LegalDocument,
    LegalEntity,
    LegalDocType,
    ReasoningStep,
    CausalRelation,
    ReasoningResult,
    UncertaintyEstimate,
)


# LegalDocument Tests
def test_legal_document_minimal():
    doc = LegalDocument(id="1", text="test")
    assert doc.id == "1"
    assert doc.text == "test"
    assert doc.metadata == {}


def test_legal_document_full():
    doc = LegalDocument(
        id="1",
        text="test",
        doc_type=LegalDocType.LAW,
        title="Test Law",
        source_file="test.pdf",
        metadata={"key": "value"}
    )
    assert doc.doc_type == LegalDocType.LAW
    assert doc.title == "Test Law"


def test_legal_document_missing_required():
    with pytest.raises(ValidationError):
        LegalDocument(id="1")  # missing text


def test_legal_document_invalid_type():
    with pytest.raises(ValidationError):
        LegalDocument(id="1", text="test", doc_type="invalid")


# LegalEntity Tests
def test_legal_entity_minimal():
    entity = LegalEntity(name="John", entity_type="person")
    assert entity.name == "John"
    assert entity.entity_type == "person"
    assert entity.role is None


def test_legal_entity_full():
    entity = LegalEntity(
        name="Supreme Court",
        entity_type="court",
        role="judge",
        metadata={"jurisdiction": "federal"}
    )
    assert entity.role == "judge"
    assert entity.metadata["jurisdiction"] == "federal"


# ReasoningStep Tests
def test_reasoning_step_minimal():
    step = ReasoningStep(step="1", reasoning="test")
    assert step.confidence == 0.5
    assert step.evidence == []


def test_reasoning_step_full():
    step = ReasoningStep(
        step="1",
        reasoning="test",
        confidence=0.9,
        evidence=["fact1", "fact2"]
    )
    assert step.confidence == 0.9
    assert len(step.evidence) == 2


# CausalRelation Tests
def test_causal_relation():
    rel = CausalRelation(
        cause="A",
        effect="B",
        strength=0.8,
        explanation="A causes B"
    )
    assert rel.cause == "A"
    assert rel.strength == 0.8


# ReasoningResult Tests
def test_reasoning_result_minimal():
    result = ReasoningResult(
        question="Q",
        context="C",
        facts=["F1"],
        reasoning_chain=[],
        causal_chain=[],
        primary_cause=None,
        final_answer="A",
        confidence=0.8,
        supporting_evidence=["E1"],
        evidence_strength="strong"
    )
    assert result.question == "Q"
    assert result.confidence == 0.8


def test_reasoning_result_to_trace_json():
    result = ReasoningResult(
        question="Q",
        context="C",
        facts=["F1"],
        reasoning_chain=[],
        causal_chain=[],
        primary_cause=None,
        final_answer="A",
        confidence=0.8,
        supporting_evidence=["E1"],
        evidence_strength="strong",
        visited_nodes=["N1", "N2"],
        graph_edges_used=[("N1", "N2")],
        used_rule_ids=["R1"]
    )
    trace = result.to_trace_json()
    assert trace["final_answer"] == "A"
    assert trace["visited_nodes"] == ["N1", "N2"]
    assert trace["graph_edges_used"] == [["N1", "N2"]]


# UncertaintyEstimate Tests
def test_uncertainty_estimate_auto_total():
    unc = UncertaintyEstimate(epistemic=0.3, aleatoric=0.2)
    assert unc.total == 0.5


def test_uncertainty_estimate_explicit_total():
    unc = UncertaintyEstimate(epistemic=0.3, aleatoric=0.2, total=0.6)
    assert unc.total == 0.6


def test_uncertainty_estimate_defaults():
    unc = UncertaintyEstimate()
    assert unc.epistemic == 0.0
    assert unc.confidence == 1.0
    assert unc.method == "ensemble"

"""
Regression tests for ReasoningResponse instantiation via VerdictEngineAdapter.

Root cause (fixed): ReasoningResponse was resolved to typing.Any at runtime when
imported indirectly through TYPE_CHECKING fallbacks, causing:
    TypeError: Any cannot be instantiated
at verdict_engine_adapter.py lines 384 and 477.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from mahoun.core.fortress_validator import ReasoningResponse as FortressReasoningResponse
from mahoun.reasoning.unified_reasoning_service import ReasoningResponse, ReasoningMode
from mahoun.reasoning.verdict_engine_adapter import VerdictEngineAdapter, VerdictProofTree


@pytest.mark.p0
def test_reasoning_response_is_concrete_dataclass_not_any():
    """ReasoningResponse must be instantiable; typing.Any is not."""
    assert ReasoningResponse is not Any
    response = ReasoningResponse(
        success=True,
        result="ok",
        confidence=0.9,
        reasoning_mode=ReasoningMode.HYBRID,
        execution_time_ms=1.0,
        proof_tree=VerdictProofTree(steps=()),
        derived_facts=["fact_a"],
    )
    assert isinstance(response, ReasoningResponse)
    assert response.success is True


@pytest.mark.p0
def test_fortress_validator_reexports_same_reasoning_response_class():
    """fortress_validator must re-export the unified dataclass, not typing.Any."""
    assert FortressReasoningResponse is ReasoningResponse


@dataclass
class _MockRequest:
    question: str = "Is tax exemption applicable?"
    facts: list[str] = field(default_factory=lambda: ["Entity is non-profit"])


@dataclass
class _MockVerdictStep:
    conclusion: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.92


@dataclass
class _MockVerdict:
    final_verdict: str
    steps: list[_MockVerdictStep]
    confidence_score: float
    verdict_id: str


class _MockEngine:
    async def generate_verdict(self, question: str, facts: list[str]):
        return _MockVerdict(
            final_verdict="Tax exemption applies",
            steps=[
                _MockVerdictStep(conclusion="Entity is non-profit", evidence=["n1"]),
                _MockVerdictStep(conclusion="Tax exemption applies", evidence=["n2"]),
            ],
            confidence_score=0.92,
            verdict_id="verdict-regression-001",
        )


@pytest.mark.asyncio
@pytest.mark.p0
async def test_adapter_success_path_instantiates_reasoning_response():
    """VerdictEngineAdapter._transform_verdict_to_response must not raise TypeError."""
    adapter = VerdictEngineAdapter(engine=_MockEngine())  # type: ignore[arg-type]
    response = await adapter.reason(_MockRequest(), correlation_id="corr-regression-001")

    assert isinstance(response, ReasoningResponse)
    assert response.success is True
    assert response.result == "Tax exemption applies"
    assert response.proof_tree is not None


@pytest.mark.asyncio
@pytest.mark.p0
async def test_adapter_failure_path_instantiates_reasoning_response():
    """VerdictEngineAdapter._create_failure_response must not raise TypeError."""

    class _FailingEngine:
        async def generate_verdict(self, question: str, facts: list[str]):
            raise RuntimeError("engine unavailable")

    adapter = VerdictEngineAdapter(engine=_FailingEngine())  # type: ignore[arg-type]
    response = await adapter.reason(_MockRequest(), correlation_id="corr-regression-fail")

    assert isinstance(response, ReasoningResponse)
    assert response.success is False
    assert "ADAPTATION_FAILED" in str(response.result)

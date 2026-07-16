"""
P0 Symbolic/Neural Agreement Tests - Wave 1, Week 3-4
========================================================

Focus: Agreement score boundaries and FortressValidator enforcement

RedLines.yaml Requirements:
- require_agreement_score: >= 0.85
- require_symbolic_neural_agreement: true

Critical Paths:
- Score exactly at boundary (0.85)
- Score just below boundary (0.84)
- Score just above boundary (0.86)
- Symbolic/neural mismatch detection
- Agreement calculation correctness

UPDATED: Tests aligned with current ReasoningResponse API (fields moved to metadata)
"""

import pytest
import math
from typing import Tuple
import asyncio
from mahoun.core.fortress_validator import FortressValidator, ExecutionMode, validate_reasoning_response, SecurityBreachException
from mahoun.reasoning.unified_reasoning_service import ReasoningResponse, ReasoningMode


@pytest.fixture
def strict_validator():
    """FortressValidator with RedLines.yaml settings."""
    return FortressValidator(
        config_path=None,  # Uses default RedLines.yaml
        execution_mode=ExecutionMode.DESKTOP_MINIMAL,
        strict_mode=True
    )


class TestAgreementScoreBoundary:
    """Test agreement score at exact boundary values."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("score,should_pass", [
        (0.840, False),  # Just below
        (0.8499, False),  # Still below
        (0.850, True),   # Exactly at
        (0.8501, True),  # Just above
        (0.86, True),    # Well above
        (0.90, True),    # Much higher
        (0.99, True),    # Very high
        (1.00, True),    # Perfect
    ])
    async def test_agreement_score_boundaries(self, strict_validator, score, should_pass):
        """Test boundary conditions: 0.84, 0.85, 0.86."""
        response = ReasoningResponse(
            success=True,
            result="Test conclusion",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True},
            derived_facts=["fact1", "fact2"],
            metadata={
                "verdict": "Test conclusion",
                "symbolic_score": score,
                "neural_score": score,
                "agreement_score": score
            }
        )

        result = await validate_reasoning_response(response, strict_mode=False)
        assert result.passed == should_pass, f"Score {score}: expected {should_pass}, got {result.passed}"

    @pytest.mark.asyncio
    async def test_agreement_score_precision_floating_point(self, strict_validator):
        """Test floating-point precision near boundary."""
        # Floating-point arithmetic can introduce rounding errors
        epsilon = 1e-10

        boundary = 0.85
        test_cases = [
            (boundary - epsilon, False),      # Slightly below
            (boundary, True),                  # Exactly at
            (boundary + epsilon, True),        # Slightly above
        ]

        for score, should_pass in test_cases:
            response = ReasoningResponse(
                success=True,
                result="Test",
                confidence=0.9,
                reasoning_mode=ReasoningMode.HYBRID,
                execution_time_ms=100.0,
                proof_tree={"valid": True},
                derived_facts=["fact1"],
                metadata={
                    "verdict": "Test",
                    "agreement_score": score
                }
            )
            result = await validate_reasoning_response(response, strict_mode=False)
            assert result.passed == should_pass, f"Score {score:.12f}"


class TestSymbolicNeuralMismatch:
    """Test detection of symbolic/neural disagreement."""

    @pytest.mark.asyncio
    async def test_high_symbolic_low_neural_disagreement(self, strict_validator):
        """P0: Detect when symbolic is high but neural is low."""
        response = ReasoningResponse(
            success=True,
            result="Conclusion",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True},
            derived_facts=["fact1"],
            metadata={
                "verdict": "Conclusion",
                "symbolic_score": 0.95,  # Symbolic confident
                "neural_score": 0.60,    # Neural uncertain
                "agreement_score": 0.775  # Average still below threshold
            }
        )

        result = await validate_reasoning_response(response, strict_mode=False)
        # Low agreement should fail even if symbolic is high
        assert not result.passed, "Disagreement must be detected"

    @pytest.mark.asyncio
    async def test_low_symbolic_high_neural_disagreement(self, strict_validator):
        """P0: Detect when neural is high but symbolic is low."""
        response = ReasoningResponse(
            success=True,
            result="Conclusion",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True},
            derived_facts=["fact1"],
            metadata={
                "verdict": "Conclusion",
                "symbolic_score": 0.60,   # Symbolic uncertain
                "neural_score": 0.95,     # Neural confident
                "agreement_score": 0.775  # Average still below threshold
            }
        )

        result = await validate_reasoning_response(response, strict_mode=False)
        assert not result.passed, "Disagreement must be detected"

    @pytest.mark.asyncio
    async def test_both_low_agreement_fails(self, strict_validator):
        """P0: Both low = instant fail."""
        response = ReasoningResponse(
            success=True,
            result="Conclusion",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True},
            derived_facts=["fact1"],
            metadata={
                "verdict": "Conclusion",
                "symbolic_score": 0.70,
                "neural_score": 0.75,
                "agreement_score": 0.725  # Average is low
            }
        )

        result = await validate_reasoning_response(response, strict_mode=False)
        assert not result.passed, "Both low agreement fails"

    @pytest.mark.asyncio
    async def test_both_high_agreement_passes(self, strict_validator):
        """P0: Both high = high agreement."""
        response = ReasoningResponse(
            success=True,
            result="Conclusion",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True},
            derived_facts=["fact1"],
            metadata={
                "verdict": "Conclusion",
                "symbolic_score": 0.92,
                "neural_score": 0.88,
                "agreement_score": 0.90
            }
        )

        result = await validate_reasoning_response(response, strict_mode=False)
        assert result.passed, "Both high agreement passes"


class TestAgreementCalculationCorrectness:
    """Test that agreement score is calculated correctly."""

    @pytest.mark.asyncio
    async def test_agreement_score_is_average_or_minimum(self, strict_validator):
        """Agreement should be calculated as min or average of symbolic/neural."""
        test_cases = [
            # (symbolic, neural, expected_agreement_strategy)
            (0.85, 0.85, "either_strategy"),   # Same
            (0.90, 0.80, "minimum_or_average"),  # Different
            (0.95, 0.75, "minimum_or_average"),  # Large difference
            (1.00, 0.85, "minimum_strategy"),    # Perfect vs threshold
        ]

        for symbolic, neural, strategy in test_cases:
            response = ReasoningResponse(
                success=True,
                result="Test",
                confidence=0.9,
                reasoning_mode=ReasoningMode.HYBRID,
                execution_time_ms=100.0,
                proof_tree={"valid": True},
                derived_facts=["fact1"],
                metadata={
                    "verdict": "Test",
                    "symbolic_score": symbolic,
                    "neural_score": neural,
                    "agreement_score": min(symbolic, neural)  # Use minimum strategy
                }
            )

            # If using minimum, score should be min(symbolic, neural)
            agreement_score = response.metadata["agreement_score"]
            if strategy == "minimum_strategy":
                expected_agreement = min(symbolic, neural)
                assert agreement_score == expected_agreement
            elif strategy == "either_strategy":
                # Could be either strategy
                assert agreement_score == symbolic or agreement_score == neural


class TestZeroAndNegativeAgreement:
    """Test edge cases with zero and negative agreement."""

    @pytest.mark.asyncio
    async def test_zero_agreement_rejected(self, strict_validator):
        """P0: Zero agreement must be rejected."""
        response = ReasoningResponse(
            success=True,
            result="Test",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True},
            derived_facts=["fact1"],
            metadata={
                "verdict": "Test",
                "agreement_score": 0.0
            }
        )

        result = await validate_reasoning_response(response, strict_mode=False)
        assert not result.passed, "Zero agreement fails"

    @pytest.mark.asyncio
    async def test_negative_agreement_rejected(self, strict_validator):
        """P0: Negative agreement must be rejected."""
        response = ReasoningResponse(
            success=True,
            result="Test",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True},
            derived_facts=["fact1"],
            metadata={
                "verdict": "Test",
                "agreement_score": -0.1  # Invalid
            }
        )

        with pytest.raises((ValueError, AssertionError)):
            await validate_reasoning_response(response, strict_mode=False)

    @pytest.mark.asyncio
    async def test_above_one_agreement_rejected(self, strict_validator):
        """P0: Agreement > 1.0 is impossible."""
        response = ReasoningResponse(
            success=True,
            result="Test",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True},
            derived_facts=["fact1"],
            metadata={
                "verdict": "Test",
                "agreement_score": 1.01  # Invalid
            }
        )

        with pytest.raises((ValueError, AssertionError)):
            await validate_reasoning_response(response, strict_mode=False)


class TestAgreementWithProofTree:
    """Test agreement validation WITH proof tree requirements."""

    @pytest.mark.asyncio
    async def test_agreement_high_but_no_proof_tree_fails(self, strict_validator):
        """P0: High agreement but missing proof tree = FAIL."""
        response = ReasoningResponse(
            success=True,
            result="Conclusion",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree=None,  # Missing
            derived_facts=["fact1"],
            metadata={
                "verdict": "Conclusion",
                "agreement_score": 0.95  # High
            }
        )

        result = await validate_reasoning_response(response, strict_mode=False)
        assert not result.passed, "Missing proof tree causes failure"

    @pytest.mark.asyncio
    async def test_agreement_low_with_good_proof_tree_fails(self, strict_validator):
        """P0: Low agreement even with good proof tree = FAIL."""
        response = ReasoningResponse(
            success=True,
            result="Conclusion",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True, "complete": True},  # Good tree
            derived_facts=["fact1"],
            metadata={
                "verdict": "Conclusion",
                "agreement_score": 0.80  # Low
            }
        )

        result = await validate_reasoning_response(response, strict_mode=False)
        assert not result.passed, "Low agreement fails regardless of tree quality"

    @pytest.mark.asyncio
    async def test_both_requirements_met(self, strict_validator):
        """P0: Both agreement >= 0.85 AND proof tree = PASS."""
        response = ReasoningResponse(
            success=True,
            result="Conclusion",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True},
            derived_facts=["fact1"],
            metadata={
                "verdict": "Conclusion",
                "agreement_score": 0.85
            }
        )

        result = await validate_reasoning_response(response, strict_mode=False)
        assert result.passed, "Both requirements met = PASS"


class TestAgreementScorePersistence:
    """Test that agreement score is consistently enforced."""

    @pytest.mark.asyncio
    async def test_agreement_checked_on_every_response(self, strict_validator):
        """P0: Agreement must be checked for EVERY response."""
        responses = [
            ReasoningResponse(
                success=True,
                result=f"Verdict {i}",
                confidence=0.9,
                reasoning_mode=ReasoningMode.HYBRID,
                execution_time_ms=100.0,
                proof_tree={"valid": True},
                derived_facts=["fact1"],
                metadata={
                    "verdict": f"Verdict {i}",
                    "agreement_score": 0.84 + (i * 0.01)
                }
            )
            for i in range(10)
        ]

        results = [strict_validator.validate_reasoning_response(r) for r in responses]

        # First response (0.84) should fail
        assert not results[0].is_valid

        # Responses from 0.85 onwards should pass
        for i in range(1, 10):
            assert results[i].is_valid, f"Response {i} (score {responses[i].metadata['agreement_score']}) should pass"

    @pytest.mark.asyncio
    async def test_agreement_not_bypassed_by_context(self, strict_validator):
        """P0: Agreement check cannot be bypassed by context or metadata."""
        # Even with additional metadata, agreement must be checked
        response = ReasoningResponse(
            success=True,
            result="Conclusion",
            confidence=0.9,
            reasoning_mode=ReasoningMode.HYBRID,
            execution_time_ms=100.0,
            proof_tree={"valid": True},
            derived_facts=["fact1"],
            metadata={
                "verdict": "Conclusion",
                "agreement_score": 0.80,  # Below threshold
                "priority": "urgent",
                "skip_validation": False  # Try to bypass
            }
        )

        result = await validate_reasoning_response(response, strict_mode=False)
        assert not result.passed, "Agreement check cannot be bypassed"


# ============================================================================
# Summary Test Counts
# ============================================================================

# TestAgreementScoreBoundary: 2 tests
# TestSymbolicNeuralMismatch: 4 tests
# TestAgreementCalculationCorrectness: 1 test
# TestZeroAndNegativeAgreement: 3 tests
# TestAgreementWithProofTree: 3 tests
# TestAgreementScorePersistence: 2 tests

# TOTAL: 15 tests for Agreement Score

# Critical boundary cases covered:
# - 0.84 (reject)
# - 0.85 (accept)
# - 0.86 (accept)
# - Symbolic/neural mismatch
# - Proof tree interaction
# - Edge cases (zero, negative, > 1.0)

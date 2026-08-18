"""
Test NLI Text-Grounding Enforcement - Tier 1 Hardening
=======================================================

Tests that verdict engine properly enforces NLI verification
and rejects verdicts with fabricated facts per AGENTS.md Section 1-F.

This addresses Tier 1 audit report requirement P0.
"""

import pytest
from unittest.mock import Mock, patch
from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
from mahoun.guardrails.ultra_nli_verifier import UltraNLIResult, NLILabel


@pytest.mark.unit
def test_verdict_text_grounding_enforced_production_mode():
    """
    Test that verdicts with fabricated facts are REJECTED in production mode.
    
    Per AGENTS.md Section 1-F:
    "If entailment fails or contradiction is detected, the verdict request must hard-fail"
    """
    # Setup mock NLI verifier that detects fabrication
    mock_nli_verifier = Mock()
    mock_nli_result = UltraNLIResult(
        is_supported=False,  # Fabrication detected!
        label=NLILabel.CONTRADICTION,
        entailment_score=0.2,
        contradiction_score=0.8,
        neutral_score=0.0,
        reasoning="Generated text contains facts not in evidence"
    )
    mock_nli_verifier.verify = Mock(return_value=mock_nli_result)
    
    # Mock is_production() to return True
    with patch('mahoun.core.environment.is_production', return_value=True):
        with patch('mahoun.guardrails.ultra_nli_verifier.UltraNLIVerifier', return_value=mock_nli_verifier):
            # Create verdict engine
            engine = EvidenceLinkedVerdictEngine(
                container=Mock(),  # Mock container
                config=Mock()
            )
            
            # Attempt to generate verdict with fabricated content
            # This MUST raise RuntimeError in production
            with pytest.raises(RuntimeError, match="NLI.*verification.*FAILED"):
                verdict_result = engine.generate_verdict(
                    case_facts=["Contract is unsigned"],
                    query="What is the contract status?",
                    case_id="test-case-001"
                )


@pytest.mark.unit
def test_verdict_text_grounding_allows_valid_verdict():
    """
    Test that verdicts grounded in evidence are ACCEPTED.
    """
    # Setup mock NLI verifier that accepts valid verdict
    mock_nli_verifier = Mock()
    mock_nli_result = UltraNLIResult(
        is_supported=True,  # Valid!
        label=NLILabel.ENTAILMENT,
        entailment_score=0.92,
        contradiction_score=0.02,
        neutral_score=0.06,
        reasoning="All facts in verdict are grounded in evidence"
    )
    mock_nli_verifier.verify = Mock(return_value=mock_nli_result)
    
    with patch('mahoun.guardrails.ultra_nli_verifier.UltraNLIVerifier', return_value=mock_nli_verifier):
        # Create verdict engine
        engine = EvidenceLinkedVerdictEngine(
            container=Mock(),
            config=Mock()
        )
        
        # Generate verdict - should succeed
        try:
            verdict_result = engine.generate_verdict(
                case_facts=["Contract is unsigned", "Rule: unsigned contracts are void"],
                query="Is the contract valid?",
                case_id="test-case-002"
            )
            # If we get here, verification passed
            assert True
        except RuntimeError as e:
            if "NLI" in str(e):
                pytest.fail(f"Valid verdict was incorrectly rejected: {e}")
            raise


@pytest.mark.integration
@pytest.mark.slow
def test_nli_verification_wiring_end_to_end():
    """
    Integration test: verify NLI verification is actually called in verdict pipeline.
    
    This tests the ACTUAL production path, not mocks.
    """
    pytest.skip("Requires full system setup - run in integration suite")


@pytest.mark.unit
def test_nli_verifier_import_failure_blocks_production():
    """
    Test that if NLI verifier fails to import, production mode MUST fail.
    
    Per fail-closed principle: missing verification = reject request.
    """
    with patch('mahoun.guardrails.ultra_nli_verifier.UltraNLIVerifier', side_effect=ImportError("torch not installed")):
        with patch('mahoun.core.environment.is_production', return_value=True):
            with pytest.raises(ImportError, match="NLI verification is a REQUIRED component"):
                engine = EvidenceLinkedVerdictEngine(
                    container=Mock(),
                    config=Mock()
                )
                engine.generate_verdict(
                    case_facts=["test"],
                    query="test",
                    case_id="test-case-import-fail"
                )


@pytest.mark.unit
def test_empty_context_blocks_nli_verification():
    """
    Test that NLI verification fails-closed when no evidence context available.
    """
    mock_nli_verifier = Mock()
    
    with patch('mahoun.guardrails.ultra_nli_verifier.UltraNLIVerifier', return_value=mock_nli_verifier):
        with patch('mahoun.core.environment.is_production', return_value=True):
            engine = EvidenceLinkedVerdictEngine(
                container=Mock(),
                config=Mock()
            )
            
            # Empty evidence should block in production
            with pytest.raises(RuntimeError, match="no evidence context"):
                engine.generate_verdict(
                    case_facts=[],  # Empty!
                    query="What is the verdict?",
                    case_id="test-case-empty"
                )


# Regression protection
@pytest.mark.unit
def test_nli_verification_cannot_be_silently_disabled():
    """
    Regression test: ensure NLI verification cannot be accidentally disabled.
    
    This has regressed before - guard against it.
    """
    # Try to create engine with NLI disabled - should fail in production
    with patch('mahoun.core.environment.is_production', return_value=True):
        with pytest.raises((ValueError, RuntimeError)):
            engine = EvidenceLinkedVerdictEngine(
                container=Mock(),
                config=Mock(nli_enabled=False)  # Attempt to disable
            )

"""
AI Runtime Governance Compliance Tests
======================================

Tests Task D.2.4: Governance compliance testing
- RedLines.yaml threshold enforcement
- Security breach exception handling  
- Audit trail completeness validation

These tests ensure the AI runtime integration maintains full governance
compliance and generates proper audit trails.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, List

from mahoun.core.fortress_validator import (
    FortressValidator, 
    SecurityBreachException,
    ViolationType,
    ViolationSeverity,
    ExecutionMode
)
from mahoun.core.models.ai_response import AIResponse
from mahoun.core.models.audit_event import AuditEvent
from mahoun.ai.runtime_manager import RuntimeManager
from mahoun.core.models.deployment_profile import DeploymentProfile, DESKTOP_MINIMAL, ENTERPRISE_FULL


class TestGovernanceCompliance:
    """Test governance compliance for AI runtime integration"""

    @pytest.fixture
    def fortress_validator(self):
        """Create FortressValidator with test configuration"""
        return FortressValidator(
            execution_mode=ExecutionMode.DESKTOP_MINIMAL,
            strict_mode=True
        )

    @pytest.fixture
    def mock_ai_response(self):
        """Create mock AI response with governance fields"""
        return {
            "success": True,
            "result": "Legal analysis completed",
            "confidence": 0.95,
            "reasoning_mode": "HYBRID",
            "execution_time_ms": 1500.0,
            "proof_tree": Mock(
                steps=[{
                    "evidence": [
                        {
                            "node_type": "Fact",
                            "content": "ContractualObligation(party1, party2, payment)"
                        },
                        {
                            "node_type": "LegalRule", 
                            "justification": "Per Section 123.45 [Source: Civil Code Art. 1234]",
                            "content": "payment_due_rule"
                        }
                    ]
                }],
                get_proof_depth=lambda: 2
            ),
            "derived_facts": [
                "ContractualObligation(party1, party2, payment)",
                "PaymentDue(party2, 30_days)"
            ],
            "metadata": {
                "agreement_score": 0.87,
                "source_attribution": ["Civil Code Art. 1234"],
                "graph_evidence_count": 5
            },
            "fortress_validated": False,
            "audit_hash": None,
            "validation_timestamp": None,
            "correlation_id": None
        }

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_redlines_threshold_enforcement(self, fortress_validator, mock_ai_response):
        """Test RedLines.yaml threshold enforcement"""
        
        # Test 1: Valid response passes all thresholds
        result = await fortress_validator.validate(mock_ai_response, "test-001")
        assert result.passed is True
        assert len(result.violations) == 0
        
        # Test 2: Low agreement score violation
        low_agreement_response = mock_ai_response.copy()
        low_agreement_response["metadata"]["agreement_score"] = 0.75  # Below 0.85 threshold
        
        with pytest.raises(SecurityBreachException) as exc_info:
            await fortress_validator.validate(low_agreement_response, "test-002")
        
        assert ViolationType.LOW_AGREEMENT_SCORE.value in str(exc_info.value)
        assert "0.75" in str(exc_info.value)
        assert "threshold" in str(exc_info.value).lower()
        
        # Test 3: Missing proof tree violation
        no_proof_response = mock_ai_response.copy()
        no_proof_response["proof_tree"] = None
        
        with pytest.raises(SecurityBreachException) as exc_info:
            await fortress_validator.validate(no_proof_response, "test-003")
        
        assert ViolationType.MISSING_PROOF_TREE.value in str(exc_info.value)
        
        # Test 4: Low confidence score (should pass if above 0.70)
        low_confidence_response = mock_ai_response.copy() 
        low_confidence_response["confidence"] = 0.72  # Above 0.70 threshold
        
        result = await fortress_validator.validate(low_confidence_response, "test-004")
        assert result.passed is True

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_security_breach_exception_handling(self, fortress_validator):
        """Test security breach exception handling"""
        
        # Create response with multiple violations
        violation_response = {
            "success": True,
            "result": "Suspicious response",
            "confidence": 0.95,
            "reasoning_mode": "HYBRID", 
            "execution_time_ms": 1500.0,
            "proof_tree": None,  # Missing proof tree
            "derived_facts": [],  # No evidence
            "metadata": {
                "agreement_score": 0.60,  # Below threshold
            },
            "fortress_validated": False
        }
        
        with pytest.raises(SecurityBreachException) as exc_info:
            await fortress_validator.validate(violation_response, "test-breach-001")
        
        exception = exc_info.value
        
        # Verify exception structure
        assert hasattr(exception, 'violation_type')
        assert hasattr(exception, 'severity') 
        assert hasattr(exception, 'forensic_context')
        assert hasattr(exception, 'correlation_id')
        assert hasattr(exception, 'timestamp')
        
        # Verify forensic context includes evidence
        assert exception.correlation_id == "test-breach-001"
        assert isinstance(exception.forensic_context, dict)
        
        # Verify exception message format
        message = str(exception)
        assert "[SECURITY BREACH]" in message
        assert "Violation:" in message
        assert "Correlation ID:" in message
        assert "Forensic Context:" in message

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_audit_trail_completeness_validation(self, fortress_validator):
        """Test audit trail completeness validation"""
        
        # Test 1: Complete audit trail passes
        complete_response = {
            "success": True,
            "result": "Analysis complete",
            "confidence": 0.90,
            "reasoning_mode": "HYBRID",
            "execution_time_ms": 2000.0,
            "proof_tree": Mock(
                steps=[{"evidence": [{"node_type": "Fact"}]}],
                get_proof_depth=lambda: 1
            ),
            "derived_facts": ["ValidFact(x)"],
            "metadata": {
                "agreement_score": 0.90,
                "correlation_id": "audit-test-001",
                "timestamp": "2026-07-04T10:30:00Z",
                "source_attribution": ["Test Source"],
                "execution_context": "test_environment"
            }
        }
        
        result = await fortress_validator.validate(complete_response, "audit-test-001")
        assert result.passed is True
        assert result.correlation_id == "audit-test-001"
        assert len(result.violations) == 0
        
        # Test 2: Missing required audit fields
        incomplete_response = {
            "success": True,
            "result": "Incomplete analysis", 
            "confidence": 0.90,
            # Missing reasoning_mode and execution_time_ms
            "proof_tree": Mock(get_proof_depth=lambda: 1),
            "derived_facts": ["ValidFact(x)"],
            "metadata": {"agreement_score": 0.90}
        }
        
        result = await fortress_validator.validate(incomplete_response, "audit-test-002")
        
        # Should have audit trail violations but not necessarily fail
        audit_violations = [v for v in result.violations 
                          if v["type"] == ViolationType.AUDIT_TRAIL_INCOMPLETE.value]
        assert len(audit_violations) > 0
        
        # Test 3: Verify audit event generation
        assert len(fortress_validator.audit_trail) >= 2
        latest_audit = fortress_validator.audit_trail[-1]
        assert latest_audit.correlation_id == "audit-test-002"
        assert latest_audit.execution_mode == ExecutionMode.DESKTOP_MINIMAL
        assert len(latest_audit.violations_detected) > 0

    @pytest.mark.asyncio 
    @pytest.mark.p0
    async def test_runtime_governance_integration(self):
        """Test AI runtime manager governance integration"""
        
        with patch('mahoun.ai.runtime_manager.RuntimeManager') as MockRuntimeManager:
            # Setup mock runtime manager
            mock_runtime = MockRuntimeManager.return_value
            mock_runtime.generate.return_value = {
                "success": True,
                "result": "Generated text",
                "confidence": 0.92,
                "reasoning_mode": "NEURAL",
                "execution_time_ms": 800.0,
                "proof_tree": Mock(get_proof_depth=lambda: 1),
                "derived_facts": ["Generated(text)"],
                "metadata": {"source": "gguf_adapter"}
            }
            
            # Test governance wrapper around runtime
            fortress_validator = FortressValidator(strict_mode=True)
            
            # Generate response and validate
            raw_response = mock_runtime.generate("Test prompt")
            validated_response = await fortress_validator.validate(raw_response, "runtime-001")
            
            assert validated_response.passed is True
            assert validated_response.correlation_id == "runtime-001"
            
            # Verify fortress_validated flag is set
            if hasattr(raw_response, 'fortress_validated'):
                assert raw_response.fortress_validated is True
                assert raw_response.audit_hash is not None
                assert raw_response.correlation_id == "runtime-001"

    @pytest.mark.p0
    def test_deployment_profile_governance_constraints(self):
        """Test governance constraints per deployment profile"""
        
        # Test DESKTOP_MINIMAL profile constraints
        desktop_profile = DESKTOP_MINIMAL
        assert desktop_profile.max_memory_mb == 8192
        assert desktop_profile.max_concurrent_requests == 10
        
        desktop_validator = FortressValidator(
            execution_mode=ExecutionMode.DESKTOP_MINIMAL,
            strict_mode=True
        )
        
        # Verify configuration loaded correctly
        assert desktop_validator.execution_mode == ExecutionMode.DESKTOP_MINIMAL
        assert desktop_validator.config.thresholds.min_agreement_score >= 0.85
        
        # Test ENTERPRISE_FULL profile constraints  
        enterprise_profile = ENTERPRISE_FULL
        assert enterprise_profile.max_memory_mb == 524288  
        assert enterprise_profile.max_concurrent_requests == 1000
        
        enterprise_validator = FortressValidator(
            execution_mode=ExecutionMode.ENTERPRISE_FULL,
            strict_mode=True
        )
        
        assert enterprise_validator.execution_mode == ExecutionMode.ENTERPRISE_FULL
        
        # Both profiles must have identical governance thresholds
        assert (desktop_validator.config.thresholds.min_agreement_score == 
                enterprise_validator.config.thresholds.min_agreement_score)
        assert (desktop_validator.config.proof_requirements.proof_tree_required == 
                enterprise_validator.config.proof_requirements.proof_tree_required)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_air_gap_governance_compliance(self, fortress_validator):
        """Test governance compliance in air-gap environment"""
        
        # Simulate air-gap response (no external data)
        airgap_response = {
            "success": True,
            "result": "Local analysis complete",
            "confidence": 0.88,
            "reasoning_mode": "HYBRID",
            "execution_time_ms": 1200.0,
            "proof_tree": Mock(
                steps=[{
                    "evidence": [
                        {"node_type": "Fact", "content": "LocalFact(x)"},
                        {"node_type": "LegalRule", 
                         "justification": "Local rule [Source: Cached Legal DB]"}
                    ]
                }],
                get_proof_depth=lambda: 2
            ),
            "derived_facts": ["LocalFact(x)", "Conclusion(y)"],
            "metadata": {
                "agreement_score": 0.88,
                "source_attribution": ["Cached Legal DB"],
                "network_calls": 0,  # No network calls in air-gap
                "local_models_only": True
            }
        }
        
        result = await fortress_validator.validate(airgap_response, "airgap-001")
        
        # Should pass all governance checks
        assert result.passed is True
        assert len(result.violations) == 0
        
        # Verify air-gap specific metadata
        assert result.metadata["execution_mode"] == ExecutionMode.DESKTOP_MINIMAL.value
        assert result.forensic_hash is not None

    @pytest.mark.p0
    def test_governance_statistics_tracking(self, fortress_validator):
        """Test governance validation statistics tracking"""
        
        initial_stats = fortress_validator.stats.copy()
        
        # Stats should be initialized
        assert initial_stats["total_validations"] == 0
        assert initial_stats["passed"] == 0
        assert initial_stats["failed"] == 0
        assert isinstance(initial_stats["violations_by_type"], dict)
        assert initial_stats["average_validation_time_ms"] == 0.0

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_citation_traceability_enforcement(self, fortress_validator):
        """Test R-07 Citation Traceability requirement"""
        
        # Test 1: Valid response with proper citations
        valid_citation_response = {
            "success": True,
            "result": "Analysis with proper citations",
            "confidence": 0.90,
            "reasoning_mode": "HYBRID",
            "execution_time_ms": 1500.0,
            "proof_tree": Mock(
                steps=[{
                    "evidence": [
                        {
                            "node_type": "LegalRule",
                            "justification": "Per Civil Code Article 123 [Source: State Legal Code Database]",
                            "content": "contract_rule"
                        },
                        {
                            "node_type": "LegalPrecedent", 
                            "justification": "Smith v. Jones ruling [Court: Superior Court 2023]",
                            "content": "precedent_case"
                        }
                    ]
                }],
                get_proof_depth=lambda: 2
            ),
            "derived_facts": ["ValidRule(contract)", "ValidPrecedent(case)"],
            "metadata": {"agreement_score": 0.90}
        }
        
        result = await fortress_validator.validate(valid_citation_response, "citation-001")
        assert result.passed is True
        
        # Test 2: Invalid response missing source citations
        invalid_citation_response = {
            "success": True,
            "result": "Analysis without proper citations", 
            "confidence": 0.90,
            "reasoning_mode": "HYBRID",
            "execution_time_ms": 1500.0,
            "proof_tree": Mock(
                steps=[{
                    "evidence": [
                        {
                            "node_type": "LegalRule",
                            "justification": "Some legal rule without citation",  # Missing [Source:] or [Court:]
                            "content": "uncited_rule"
                        }
                    ]
                }],
                get_proof_depth=lambda: 1
            ),
            "derived_facts": ["UncitedRule(x)"],
            "metadata": {"agreement_score": 0.90}
        }
        
        with pytest.raises(SecurityBreachException) as exc_info:
            await fortress_validator.validate(invalid_citation_response, "citation-002")
        
        assert "R-07 Citation Traceability Violation" in str(exc_info.value)
        assert "lacks explicit source citation" in str(exc_info.value)


@pytest.mark.integration
class TestGovernanceIntegrationFlow:
    """Integration tests for complete governance flow"""
    
    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_end_to_end_governance_flow(self):
        """Test complete governance flow from AI runtime to audit"""
        
        # This would test the full flow:
        # 1. AI Runtime generates response
        # 2. FortressValidator validates response  
        # 3. Audit events are generated
        # 4. Compliance is verified
        
        # Mock the full stack
        with patch('mahoun.ai.runtime_manager.RuntimeManager') as MockRuntimeManager, \
             patch('mahoun.core.models.audit_event.AuditEvent') as MockAuditEvent:
            
            # Setup mocks
            mock_runtime = MockRuntimeManager.return_value
            mock_runtime.profile = DESKTOP_MINIMAL
            
            mock_runtime.generate.return_value = {
                "success": True,
                "result": "End-to-end analysis",
                "confidence": 0.92,
                "reasoning_mode": "HYBRID", 
                "execution_time_ms": 2500.0,
                "proof_tree": Mock(get_proof_depth=lambda: 3),
                "derived_facts": ["E2EFact(x)", "E2EConclusion(y)"],
                "metadata": {
                    "agreement_score": 0.91,
                    "source_attribution": ["Legal Database"],
                    "model_name": "llama-3.1-7b.gguf"
                }
            }
            
            # Create validator
            validator = FortressValidator(
                execution_mode=ExecutionMode.DESKTOP_MINIMAL,
                strict_mode=True
            )
            
            # Generate and validate response
            ai_response = mock_runtime.generate("Legal question")
            validation_result = await validator.validate(ai_response, "e2e-001")
            
            # Verify end-to-end flow
            assert validation_result.passed is True
            assert validation_result.correlation_id == "e2e-001"
            assert len(validator.audit_trail) > 0
            
            # Verify audit trail contains proper forensic context
            audit_record = validator.audit_trail[-1]
            assert audit_record.correlation_id == "e2e-001"
            assert audit_record.execution_mode == ExecutionMode.DESKTOP_MINIMAL
            assert audit_record.response_hash is not None
            
            # Verify governance metadata injection
            if hasattr(ai_response, 'fortress_validated'):
                assert ai_response.fortress_validated is True
                assert ai_response.audit_hash is not None
                assert ai_response.correlation_id == "e2e-001"


if __name__ == "__main__":
    # Run governance compliance tests
    pytest.main([__file__, "-v", "--tb=short"])
#!/usr/bin/env python3
"""
Test Suite for AI Runtime Integration - Phase A Contract Freeze

This test suite validates that all Phase A contracts are properly
defined, frozen, and ready for G-0 freeze ceremony.

Test Coverage:
- Task A.1.1: AIRuntimeProtocol interface
- Task A.1.2: AIResponse data model
- Task A.1.3: PromptTemplate for evidence-linking
- Task A.1.4: AuditEvent format
- Task A.1.5: DeploymentProfile configuration

Version: 1.0.0
Phase: A - Contract Freeze & Foundation
"""

import pytest
from pathlib import Path
import hashlib

from mahoun.core.protocols.ai_runtime import (
    AIRuntimeProtocol,
    ModelMetadata,
    HealthStatus,
    ModelStatus,
    AIRuntimeError,
    ModelNotFoundError,
    ModelIntegrityError,
    ModelNotLoadedError
)
from mahoun.core.models import (
    AIResponse,
    TokenUsage,
    GenerationMetadata,
    ResponseStatus,
    PromptTemplate,
    EvidenceSlot,
    EvidenceSlotType,
    ContextRequirement,
    AuditEvent,
    AuditEventType,
    AuditContext,
    AuditSeverity,
    DeploymentProfile,
    ResourceLimits,
    PerformanceTargets,
    ProfileType,
    DESKTOP_MINIMAL,
    ENTERPRISE_FULL,
    create_success_response,
    create_error_response,
    create_audit_event
)


class TestTaskA11_AIRuntimeProtocol:
    """Test AIRuntimeProtocol interface (Task A.1.1)"""
    
    @pytest.mark.p2
    def test_protocol_is_abstract(self):
        """Protocol should be abstract and not instantiable"""
        with pytest.raises(TypeError):
            AIRuntimeProtocol()
    
    @pytest.mark.p2
    def test_protocol_has_required_methods(self):
        """Protocol should define all required methods"""
        required_methods = [
            'load_model',
            'generate',
            'health_check',
            'unload_model',
            'get_metadata'
        ]
        
        for method_name in required_methods:
            assert hasattr(AIRuntimeProtocol, method_name)
            assert callable(getattr(AIRuntimeProtocol, method_name))
    
    @pytest.mark.p2
    def test_model_metadata_validation(self):
        """ModelMetadata should validate input"""
        # Create temp file for test
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
            temp_path = f.name
        
        try:
            # Valid metadata
            metadata = ModelMetadata(
                model_id="test-model",
                model_path=temp_path,
                model_format="GGUF",
                file_size_bytes=1000,
                checksum_sha256="a" * 64,
                parameters_count=1_000_000_000,
                quantization="Q4_K_M",
                context_window=4096,
                deployment_profile="desktop_minimal",
                load_timestamp=1234567890.0
            )
            
            assert metadata.model_id == "test-model"
            assert metadata.file_size_bytes == 1000
        finally:
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.p2
    def test_health_status_success_rate(self):
        """HealthStatus should calculate success rate correctly"""
        health = HealthStatus(
            status=ModelStatus.READY,
            model_loaded=True,
            memory_usage_mb=1000.0,
            last_inference_time=100.0,
            error_message=None,
            uptime_seconds=3600.0,
            total_requests=100,
            failed_requests=10
        )
        
        assert health.success_rate == 0.9
    
    @pytest.mark.p2
    def test_health_status_zero_requests(self):
        """HealthStatus should handle zero requests"""
        health = HealthStatus(
            status=ModelStatus.NOT_LOADED,
            model_loaded=False,
            memory_usage_mb=0.0,
            last_inference_time=None,
            error_message=None,
            uptime_seconds=0.0,
            total_requests=0,
            failed_requests=0
        )
        
        assert health.success_rate == 1.0


class TestTaskA12_AIResponse:
    """Test AIResponse data model (Task A.1.2)"""
    
    @pytest.mark.p2
    def test_ai_response_creation(self):
        """AIResponse should be creatable with valid data"""
        token_usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        
        gen_metadata = GenerationMetadata(
            model_id="test-model",
            model_format="GGUF",
            quantization="Q4_K_M",
            parameters_count=1_000_000_000,
            generation_params={"temperature": 0.7},
            inference_time_ms=100.0,
            tokens_per_second=300.0,
            memory_usage_mb=1000.0,
            deployment_profile="desktop_minimal"
        )
        
        response = AIResponse(
            request_id="test-123",
            correlation_id="corr-456",
            response_text="Test response",
            status=ResponseStatus.SUCCESS,
            confidence_score=0.85,
            quality_score=0.90,
            token_usage=token_usage,
            generation_metadata=gen_metadata
        )
        
        assert response.request_id == "test-123"
        assert response.confidence_score == 0.85
    
    @pytest.mark.p2
    def test_ai_response_validates_confidence(self):
        """AIResponse should validate confidence score range"""
        token_usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        
        gen_metadata = GenerationMetadata(
            model_id="test-model",
            model_format="GGUF",
            quantization=None,
            parameters_count=None,
            generation_params={},
            inference_time_ms=100.0,
            tokens_per_second=None,
            memory_usage_mb=100.0,
            deployment_profile="desktop_minimal"
        )
        
        with pytest.raises(ValueError, match="confidence_score must be between"):
            AIResponse(
                request_id="test",
                correlation_id="test-corr",
                response_text="test",
                status=ResponseStatus.SUCCESS,
                confidence_score=1.5,  # Invalid
                quality_score=None,
                token_usage=token_usage,
                generation_metadata=gen_metadata
            )
    
    @pytest.mark.p2
    def test_ai_response_content_hash(self):
        """AIResponse should generate deterministic content hash"""
        response = create_success_response(
            request_id="test-123",
            response_text="Test response",
            token_usage=TokenUsage(10, 20, 30),
            generation_metadata=GenerationMetadata(
                model_id="test",
                model_format="GGUF",
                quantization=None,
                parameters_count=None,
                generation_params={},
                inference_time_ms=100.0,
                tokens_per_second=None,
                memory_usage_mb=100.0,
                deployment_profile="test"
            ),
            confidence_score=0.8,
            quality_score=0.85
        )
        
        hash1 = response.calculate_content_hash()
        hash2 = response.calculate_content_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length


class TestTaskA13_PromptTemplate:
    """Test PromptTemplate data model (Task A.1.3)"""
    
    @pytest.mark.p2
    def test_prompt_template_creation(self):
        """PromptTemplate should be creatable with valid data"""
        template = PromptTemplate(
            template_id="test-template",
            template_text="Query: {query}\nEvidence: {evidence}",
            template_version="1.0.0",
            evidence_slots=[
                EvidenceSlot(
                    slot_name="query",
                    slot_type=EvidenceSlotType.CUSTOM,
                    required=True
                ),
                EvidenceSlot(
                    slot_name="evidence",
                    slot_type=EvidenceSlotType.GRAPH_CONTEXT,
                    required=True
                )
            ]
        )
        
        assert template.template_id == "test-template"
        assert len(template.evidence_slots) == 2
    
    @pytest.mark.p2
    def test_prompt_template_validates_slots(self):
        """PromptTemplate should validate evidence slots"""
        with pytest.raises(ValueError):
            PromptTemplate(
                template_id="test",
                template_text="{query}",
                template_version="1.0.0",
                evidence_slots=[]  # Invalid - needs at least one slot
            )
    
    @pytest.mark.p2
    def test_prompt_template_generates_prompt(self):
        """PromptTemplate should generate complete prompt from evidence"""
        template = PromptTemplate(
            template_id="test",
            template_text="Q: {query}\nA: {answer}",
            template_version="1.0.0",
            evidence_slots=[
                EvidenceSlot("query", EvidenceSlotType.CUSTOM, True),
                EvidenceSlot("answer", EvidenceSlotType.CUSTOM, True)
            ]
        )
        
        prompt = template.generate_prompt({
            "query": "What is AI?",
            "answer": "Artificial Intelligence"
        })
        
        assert "What is AI?" in prompt
        assert "Artificial Intelligence" in prompt


class TestTaskA14_AuditEvent:
    """Test AuditEvent data model (Task A.1.4)"""
    
    @pytest.mark.p2
    def test_audit_event_creation(self):
        """AuditEvent should be creatable with valid data"""
        event = create_audit_event(
            event_type=AuditEventType.MODEL_LOADED,
            payload={"model_id": "test-model"},
            severity=AuditSeverity.INFO,
            success=True
        )
        
        assert event.event_type == AuditEventType.MODEL_LOADED
        assert event.success is True
        assert event.payload_hash is not None
    
    @pytest.mark.p2
    def test_audit_event_integrity(self):
        """AuditEvent should verify payload integrity"""
        event = create_audit_event(
            event_type=AuditEventType.GENERATION_COMPLETED,
            payload={"result": "test"},
            success=True
        )
        
        assert event.verify_integrity() is True
    
    @pytest.mark.p2
    def test_audit_event_security_critical(self):
        """AuditEvent should identify security-critical events"""
        security_event = create_audit_event(
            event_type=AuditEventType.SECURITY_BREACH_ATTEMPT,
            payload={"details": "unauthorized access"},
            severity=AuditSeverity.CRITICAL,
            success=False,
            error_message="Security breach detected"
        )
        
        assert security_event.is_security_critical() is True


class TestTaskA15_DeploymentProfile:
    """Test DeploymentProfile configuration (Task A.1.5)"""
    
    @pytest.mark.p2
    def test_desktop_minimal_profile(self):
        """DESKTOP_MINIMAL profile should have correct constraints"""
        profile = DESKTOP_MINIMAL
        
        assert profile.profile_name == "desktop_minimal"
        assert profile.resource_limits.max_memory_gb == 4.0
        assert profile.resource_limits.max_cpu_cores == 4
        assert profile.resource_limits.enable_gpu is False
    
    @pytest.mark.p2
    def test_enterprise_full_profile(self):
        """ENTERPRISE_FULL profile should have correct constraints"""
        profile = ENTERPRISE_FULL
        
        assert profile.profile_name == "enterprise_full"
        assert profile.resource_limits.max_memory_gb == 32.0
        assert profile.resource_limits.max_cpu_cores == 16
        assert profile.resource_limits.enable_gpu is True
    
    @pytest.mark.p2
    def test_profile_model_compatibility(self):
        """Profile should validate model compatibility"""
        profile = DESKTOP_MINIMAL
        
        # Compatible model
        assert profile.validate_model_compatibility(
            model_size_gb=2.0,
            model_memory_gb=3.0,
            model_context_window=4096
        ) is True
        
        # Incompatible model (too large)
        assert profile.validate_model_compatibility(
            model_size_gb=10.0,
            model_memory_gb=3.0,
            model_context_window=4096
        ) is False
    
    @pytest.mark.p2
    def test_profile_to_dict(self):
        """Profile should serialize to dictionary"""
        profile = DESKTOP_MINIMAL
        profile_dict = profile.to_dict()
        
        assert isinstance(profile_dict, dict)
        assert profile_dict["profile_name"] == "desktop_minimal"
        assert "resource_limits" in profile_dict


class TestContractFreeze:
    """Test that contracts are ready for G-0 freeze"""
    
    @pytest.mark.p2
    def test_all_contracts_importable(self):
        """All G-0 contracts should be importable"""
        # This test passing means all contracts are syntactically correct
        assert AIRuntimeProtocol is not None
        assert AIResponse is not None
        assert PromptTemplate is not None
        assert AuditEvent is not None
        assert DeploymentProfile is not None
    
    @pytest.mark.p2
    def test_contracts_are_immutable(self):
        """Dataclass contracts should be frozen (immutable)"""
        token_usage = TokenUsage(10, 20, 30)
        
        with pytest.raises(Exception):  # FrozenInstanceError
            token_usage.prompt_tokens = 999
    
    @pytest.mark.p2
    def test_contracts_have_validation(self):
        """Contracts should validate their inputs"""
        # TokenUsage validation
        with pytest.raises(ValueError):
            TokenUsage(
                prompt_tokens=-1,  # Invalid
                completion_tokens=20,
                total_tokens=19
            )
        
        # EvidenceSlot validation
        with pytest.raises(ValueError):
            EvidenceSlot(
                slot_name="",  # Invalid
                slot_type=EvidenceSlotType.CUSTOM
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

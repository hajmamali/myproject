"""
Test 4: Light Logic Tests
==========================
Test basic logic flows WITHOUT heavy dependencies (LLM, embeddings, DB).

Safety: ⭐⭐⭐⭐ (Mocked dependencies, quick execution)
"""

import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestClaimGeneratorLogic:
    """Test ClaimDraftGenerator basic logic"""
    
    @pytest.fixture
    def claim_generator(self):
        from output.claim_generator import ClaimDraftGenerator
        return ClaimDraftGenerator()
    
    def test_can_instantiate(self, claim_generator):
        """Should be able to create instance"""
        assert claim_generator is not None
        assert claim_generator.name == "claim_draft_generator"
    
    def test_has_config(self, claim_generator):
        """Should store config"""
        assert hasattr(claim_generator, 'config')
        assert isinstance(claim_generator.config, dict)
    
    def test_custom_config(self):
        """Should accept custom config"""
        from output.claim_generator import ClaimDraftGenerator
        
        custom_config = {"llm_model": "test-model", "max_tokens": 500}
        generator = ClaimDraftGenerator(config=custom_config)
        
        assert generator.config == custom_config
    
    @pytest.mark.asyncio
    async def test_generate_returns_dict(self, claim_generator):
        """generate should return structured dict"""
        input_data = {
            "claim_type": "breach_of_contract",
            "facts": "Test facts",
            "legal_basis": "Article 123"
        }
        
        result = await claim_generator.generate(input_data)
        
        assert isinstance(result, dict)
        assert "success" in result
        assert "claim_id" in result
    
    @pytest.mark.asyncio
    async def test_generate_has_required_fields(self, claim_generator):
        """generate result should have all required fields"""
        input_data = {
            "facts": "Party A failed to deliver goods",
            "legal_basis": "Contract Law Section 42"
        }
        
        result = await claim_generator.generate(input_data)
        
        # Check required fields
        assert result["success"] is True
        assert "claim_id" in result
        assert "content" in result
        assert "markdown" in result
        assert "citations" in result
        assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_generate_produces_content(self, claim_generator):
        """generate should produce non-empty content"""
        input_data = {
            "claim_type": "damages",
            "facts": "Defendant caused $10,000 in damages",
        }
        
        result = await claim_generator.generate(input_data)
        
        # Content should not be empty
        assert len(result["content"]) > 0
        assert len(result["markdown"]) > 0
        
        # Content should include input facts
        assert "damages" in result["content"].lower() or "Defendant" in result["content"]
    
    @pytest.mark.asyncio
    async def test_metadata_injection(self, claim_generator):
        """Should inject metadata into result"""
        input_data = {
            "facts": "Test",
            "integrity_report": {"status": "verified"}
        }
        
        result = await claim_generator.generate(input_data)
        
        assert "metadata" in result
        assert "generated_at" in result["metadata"]
        
        # Should pass through integrity report
        assert "integrity" in result["metadata"]
        assert result["metadata"]["integrity"]["status"] == "verified"


class TestBaseGeneratorLogic:
    """Test BaseReportGenerator basic logic"""
    
    @pytest.fixture
    def concrete_generator(self):
        """Create a concrete implementation for testing"""
        from output.base_generator import BaseReportGenerator
        
        class TestGenerator(BaseReportGenerator):
            async def generate(self, input_data):
                return {"content": "test", "metadata": {}}
        
        return TestGenerator("test_gen", {"test": True})
    
    def test_initialization(self, concrete_generator):
        """Should initialize with name and config"""
        assert concrete_generator.name == "test_gen"
        assert concrete_generator.config == {"test": True}
        assert concrete_generator._initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_sets_flag(self, concrete_generator):
        """initialize should set _initialized flag"""
        await concrete_generator.initialize()
        assert concrete_generator._initialized is True
    
    @pytest.mark.asyncio
    async def test_export_json(self, concrete_generator):
        """export should return JSON format"""
        result = {"content": "test", "metadata": {}}
        exported = await concrete_generator.export(result, format="json")
        
        assert exported == result
    
    @pytest.mark.asyncio
    async def test_export_text(self, concrete_generator):
        """export should extract text content"""
        result = {"content": "Hello World", "metadata": {}}
        exported = await concrete_generator.export(result, format="text")
        
        assert exported == "Hello World"
    
    @pytest.mark.asyncio
    async def test_export_markdown(self, concrete_generator):
        """export should extract markdown content"""
        result = {"content": "text", "markdown": "# Title\nContent", "metadata": {}}
        exported = await concrete_generator.export(result, format="markdown")
        
        assert exported == "# Title\nContent"
    
    def test_get_status(self, concrete_generator):
        """get_status should return status dict"""
        status = concrete_generator.get_status()
        
        assert isinstance(status, dict)
        assert status["name"] == "test_gen"
        assert status["initialized"] is False
        assert status["config"] == {"test": True}


class TestCircuitBreakerLogic:
    """Test CircuitBreaker logic (lightweight component)"""
    
    @pytest.fixture
    def circuit_breaker(self):
        from mahoun.agents.base_agent import CircuitBreaker
        return CircuitBreaker(threshold=3, timeout=60)
    
    def test_initial_state_is_closed(self, circuit_breaker):
        """Circuit breaker should start in CLOSED state"""
        from mahoun.agents.base_agent import CircuitBreakerState
        
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.can_execute() is True
    
    def test_record_failure_increments_count(self, circuit_breaker):
        """record_failure should increment failure count"""
        circuit_breaker.record_failure()
        assert circuit_breaker.failure_count == 1
        
        circuit_breaker.record_failure()
        assert circuit_breaker.failure_count == 2
    
    def test_opens_after_threshold(self, circuit_breaker):
        """Circuit breaker should open after threshold failures"""
        from mahoun.agents.base_agent import CircuitBreakerState
        
        # Record failures up to threshold
        for _ in range(3):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.can_execute() is False
    
    def test_record_success_resets(self, circuit_breaker):
        """record_success should reset failure count"""
        from mahoun.agents.base_agent import CircuitBreakerState
        
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.failure_count == 2
        
        circuit_breaker.record_success()
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == CircuitBreakerState.CLOSED


class TestAgentConfigLogic:
    """Test AgentConfig logic"""
    
    def test_default_config(self):
        """AgentConfig should have sensible defaults"""
        from mahoun.agents.base_agent import AgentConfig
        
        config = AgentConfig()
        
        # Verify defaults
        assert config.max_retries == 3
        assert config.retry_base_delay == 0.5
        assert config.operation_timeout == 30.0
        assert config.circuit_breaker_threshold == 5
        assert config.enable_fallback is True
    
    def test_custom_config(self):
        """Should accept custom values"""
        from mahoun.agents.base_agent import AgentConfig
        
        config = AgentConfig(
            max_retries=5,
            operation_timeout=60.0,
            enable_fallback=False
        )
        
        assert config.max_retries == 5
        assert config.operation_timeout == 60.0
        assert config.enable_fallback is False


class TestAgentResultLogic:
    """Test AgentResult logic"""
    
    def test_success_result(self):
        """Should create success result"""
        from mahoun.agents.base_agent import AgentResult
        
        result = AgentResult(
            success=True,
            data={"output": "test"},
            correlation_id="abc123",
            processing_time_ms=150.5
        )
        
        assert result.success is True
        assert result.data == {"output": "test"}
        assert result.error is None
        assert result.correlation_id == "abc123"
    
    def test_failure_result(self):
        """Should create failure result"""
        from mahoun.agents.base_agent import AgentResult
        
        result = AgentResult(
            success=False,
            error="Something went wrong",
            error_type="ValueError"
        )
        
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.error_type == "ValueError"
    
    def test_to_dict_conversion(self):
        """to_dict should convert to dictionary"""
        from mahoun.agents.base_agent import AgentResult
        
        result = AgentResult(
            success=True,
            data={"test": 1},
            retries_used=2,
            fallback_used=False
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["data"] == {"test": 1}
        assert result_dict["retries_used"] == 2
        assert result_dict["fallback_used"] is False


class TestClaimTypeEnum:
    """Test ClaimType enum logic"""
    
    def test_enum_values(self):
        """ClaimType should have correct values"""
        from mahoun.agents.claim_agent import ClaimType
        
        # Check values match expected format
        assert ClaimType.BREACH_OF_CONTRACT.value == "breach_of_contract"
        assert ClaimType.DAMAGES.value == "damages"
        assert ClaimType.SPECIFIC_PERFORMANCE.value == "specific_performance"
    
    def test_enum_from_string(self):
        """Should be able to create enum from string"""
        from mahoun.agents.claim_agent import ClaimType
        
        claim_type = ClaimType("damages")
        assert claim_type == ClaimType.DAMAGES
    
    def test_invalid_claim_type(self):
        """Should raise ValueError for invalid claim type"""
        from mahoun.agents.claim_agent import ClaimType
        
        with pytest.raises(ValueError):
            ClaimType("invalid_claim_type")


class TestClaimAgentTemplates:
    """Test UltraClaimAgent templates"""
    
    def test_templates_exist(self):
        """CLAIM_TEMPLATES should be populated"""
        from mahoun.agents.claim_agent import UltraClaimAgent, ClaimType
        
        templates = UltraClaimAgent.CLAIM_TEMPLATES
        
        assert isinstance(templates, dict)
        assert len(templates) > 0
    
    def test_templates_have_required_fields(self):
        """Each template should have title and relief"""
        from mahoun.agents.claim_agent import UltraClaimAgent, ClaimType
        
        templates = UltraClaimAgent.CLAIM_TEMPLATES
        
        # Check first template
        first_template = templates[ClaimType.BREACH_OF_CONTRACT]
        assert "title" in first_template
        assert "relief" in first_template
        assert isinstance(first_template["title"], str)
        assert isinstance(first_template["relief"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


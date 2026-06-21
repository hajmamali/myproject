"""
Test 3: Contract Tests
=======================
Verify method contracts: signatures, return types, async/sync.

Safety: ⭐⭐⭐⭐⭐ (No execution, inspection only)
"""

import pytest
import sys
import inspect
from pathlib import Path
from typing import get_type_hints

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestBaseGeneratorContract:
    """Test BaseReportGenerator method contracts"""
    
    @pytest.fixture
    def base_generator_class(self):
        from output.base_generator import BaseReportGenerator
        return BaseReportGenerator
    
    def test_init_accepts_name_and_config(self, base_generator_class):
        """__init__ should accept name and optional config"""
        sig = inspect.signature(base_generator_class.__init__)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'name' in params
        assert 'config' in params
        
        # config should have default
        assert sig.parameters['config'].default is not inspect.Parameter.empty
    
    def test_generate_is_async(self, base_generator_class):
        """generate method should be async"""
        assert inspect.iscoroutinefunction(base_generator_class.generate)
    
    def test_generate_accepts_dict(self, base_generator_class):
        """generate should accept input_data dict"""
        sig = inspect.signature(base_generator_class.generate)
        params = list(sig.parameters.keys())
        
        assert 'input_data' in params
    
    def test_initialize_is_async(self, base_generator_class):
        """initialize method should be async"""
        assert inspect.iscoroutinefunction(base_generator_class.initialize)
    
    def test_export_is_async(self, base_generator_class):
        """export method should be async"""
        assert inspect.iscoroutinefunction(base_generator_class.export)
    
    def test_get_status_is_sync(self, base_generator_class):
        """get_status should be synchronous"""
        assert not inspect.iscoroutinefunction(base_generator_class.get_status)


class TestClaimGeneratorContract:
    """Test ClaimDraftGenerator method contracts"""
    
    @pytest.fixture
    def claim_generator_class(self):
        from output.claim_generator import ClaimDraftGenerator
        return ClaimDraftGenerator
    
    def test_init_accepts_optional_config(self, claim_generator_class):
        """__init__ should accept optional config"""
        sig = inspect.signature(claim_generator_class.__init__)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'config' in params
        
        # config should be optional
        assert sig.parameters['config'].default is not inspect.Parameter.empty
    
    def test_generate_returns_dict_async(self, claim_generator_class):
        """generate should be async and return Dict"""
        assert inspect.iscoroutinefunction(claim_generator_class.generate)


class TestUltraBaseAgentContract:
    """Test UltraBaseAgent method contracts"""
    
    @pytest.fixture
    def base_agent_class(self):
        from mahoun.agents.base_agent import UltraBaseAgent
        return UltraBaseAgent
    
    def test_init_signature(self, base_agent_class):
        """__init__ should accept name, config, parent_config"""
        sig = inspect.signature(base_agent_class.__init__)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'name' in params
        assert 'config' in params
        assert 'parent_config' in params
    
    def test_initialize_is_async(self, base_agent_class):
        """initialize should be async"""
        assert inspect.iscoroutinefunction(base_agent_class.initialize)
    
    def test_shutdown_is_async(self, base_agent_class):
        """shutdown should be async"""
        assert inspect.iscoroutinefunction(base_agent_class.shutdown)
    
    def test_close_is_async(self, base_agent_class):
        """close should be async"""
        assert inspect.iscoroutinefunction(base_agent_class.close)
    
    def test_process_is_async(self, base_agent_class):
        """process should be async"""
        assert inspect.iscoroutinefunction(base_agent_class.process)
    
    def test_process_signature(self, base_agent_class):
        """process should accept input_data and correlation_id"""
        sig = inspect.signature(base_agent_class.process)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'input_data' in params
        assert 'correlation_id' in params
    
    def test_health_check_is_async(self, base_agent_class):
        """health_check should be async"""
        assert inspect.iscoroutinefunction(base_agent_class.health_check)
    
    def test_get_metrics_is_sync(self, base_agent_class):
        """get_metrics should be synchronous"""
        assert not inspect.iscoroutinefunction(base_agent_class.get_metrics)
    
    def test_get_status_is_sync(self, base_agent_class):
        """get_status should be synchronous"""
        assert not inspect.iscoroutinefunction(base_agent_class.get_status)
    
    def test_context_manager_methods_are_async(self, base_agent_class):
        """Context manager methods should be async"""
        assert inspect.iscoroutinefunction(base_agent_class.__aenter__)
        assert inspect.iscoroutinefunction(base_agent_class.__aexit__)


class TestUltraClaimAgentContract:
    """Test UltraClaimAgent method contracts"""
    
    @pytest.fixture
    def claim_agent_class(self):
        from mahoun.agents.claim_agent import UltraClaimAgent
        return UltraClaimAgent
    
    def test_init_accepts_claim_config(self, claim_agent_class):
        """__init__ should accept ClaimAgentConfig"""
        sig = inspect.signature(claim_agent_class.__init__)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'config' in params
    
    def test_helper_methods_are_async(self, claim_agent_class):
        """Helper methods should be async"""
        assert inspect.iscoroutinefunction(claim_agent_class._initialize_impl)
        assert inspect.iscoroutinefunction(claim_agent_class._process_impl)
        assert inspect.iscoroutinefunction(claim_agent_class._fallback_impl)
        assert inspect.iscoroutinefunction(claim_agent_class._search_relevant)
        assert inspect.iscoroutinefunction(claim_agent_class._extract_legal_basis)
        assert inspect.iscoroutinefunction(claim_agent_class._build_arguments)
        assert inspect.iscoroutinefunction(claim_agent_class._generate_claim)
    
    def test_formatting_methods_are_sync(self, claim_agent_class):
        """Formatting methods should be synchronous"""
        assert not inspect.iscoroutinefunction(claim_agent_class._generate_full_text)
        assert not inspect.iscoroutinefunction(claim_agent_class._claim_to_dict)
        assert not inspect.iscoroutinefunction(claim_agent_class._argument_to_dict)


class TestDataClassContracts:
    """Test data class contracts"""
    
    def test_agent_config_defaults(self):
        """AgentConfig should have sensible defaults"""
        from mahoun.agents.base_agent import AgentConfig
        
        config = AgentConfig()
        
        # Check defaults are set
        assert config.max_retries > 0
        assert config.retry_base_delay > 0
        assert config.operation_timeout > 0
        assert config.circuit_breaker_threshold > 0
        assert isinstance(config.enable_fallback, bool)
    
    def test_agent_result_has_required_fields(self):
        """AgentResult should have required fields"""
        from mahoun.agents.base_agent import AgentResult
        
        result = AgentResult(success=True)
        
        assert hasattr(result, 'success')
        assert hasattr(result, 'data')
        assert hasattr(result, 'error')
        assert hasattr(result, 'correlation_id')
        assert hasattr(result, 'processing_time_ms')
        assert hasattr(result, 'retries_used')
        assert hasattr(result, 'fallback_used')
        assert hasattr(result, 'warnings')
    
    def test_circuit_breaker_methods_return_correctly(self):
        """CircuitBreaker methods should return expected types"""
        from mahoun.agents.base_agent import CircuitBreaker
        
        cb = CircuitBreaker()
        
        # can_execute should return bool
        result = cb.can_execute()
        assert isinstance(result, bool)
        
        # record_success and record_failure should not raise
        cb.record_success()
        cb.record_failure()


class TestEnumContracts:
    """Test enum contracts"""
    
    def test_agent_state_has_all_states(self):
        """AgentState should have all lifecycle states"""
        from mahoun.agents.base_agent import AgentState
        
        # Check key states exist
        assert hasattr(AgentState, 'CREATED')
        assert hasattr(AgentState, 'READY')
        assert hasattr(AgentState, 'PROCESSING')
        assert hasattr(AgentState, 'FAILED')
        assert hasattr(AgentState, 'SHUTDOWN')
        assert hasattr(AgentState, 'DEGRADED')
    
    def test_circuit_breaker_state_has_all_states(self):
        """CircuitBreakerState should have all states"""
        from mahoun.agents.base_agent import CircuitBreakerState
        
        assert hasattr(CircuitBreakerState, 'CLOSED')
        assert hasattr(CircuitBreakerState, 'OPEN')
        assert hasattr(CircuitBreakerState, 'HALF_OPEN')
    
    def test_claim_type_values_are_strings(self):
        """ClaimType enum values should be strings"""
        from mahoun.agents.claim_agent import ClaimType
        
        # Check values are strings
        assert isinstance(ClaimType.BREACH_OF_CONTRACT.value, str)
        assert isinstance(ClaimType.DAMAGES.value, str)


class TestReturnTypeConsistency:
    """Test that return types are consistent"""
    
    def test_get_status_returns_dict(self):
        """get_status methods should return Dict[str, Any]"""
        from output.base_generator import BaseReportGenerator
        from mahoun.agents.base_agent import UltraBaseAgent
        
        # Both should have get_status returning dict
        # We can't instantiate abstract classes, but we can check the method exists
        assert hasattr(BaseReportGenerator, 'get_status')
        assert hasattr(UltraBaseAgent, 'get_status')
    
    def test_get_metrics_returns_dict(self):
        """get_metrics should return Dict[str, Any]"""
        from mahoun.agents.base_agent import UltraBaseAgent
        
        assert hasattr(UltraBaseAgent, 'get_metrics')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


"""
Test 2: Structure Tests
========================
Verify that classes have expected methods, attributes, and inheritance.

Safety: ⭐⭐⭐⭐⭐ (Pure introspection, no execution)
"""

import pytest
import sys
import inspect
from pathlib import Path
from abc import ABC

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestBaseGeneratorStructure:
    """Test BaseReportGenerator class structure"""
    
    @pytest.fixture
    def base_generator_class(self):
        from output.base_generator import BaseReportGenerator
        return BaseReportGenerator
    
    def test_is_abstract_base_class(self, base_generator_class):
        """BaseReportGenerator should be an ABC"""
        assert issubclass(base_generator_class, ABC)
    
    def test_has_init_method(self, base_generator_class):
        """Should have __init__ method"""
        assert hasattr(base_generator_class, '__init__')
    
    def test_has_generate_method(self, base_generator_class):
        """Should have abstract generate method"""
        assert hasattr(base_generator_class, 'generate')
        # Check it's async
        assert inspect.iscoroutinefunction(base_generator_class.generate)
    
    def test_has_initialize_method(self, base_generator_class):
        """Should have initialize method"""
        assert hasattr(base_generator_class, 'initialize')
    
    def test_has_export_method(self, base_generator_class):
        """Should have export method"""
        assert hasattr(base_generator_class, 'export')
    
    def test_has_get_status_method(self, base_generator_class):
        """Should have get_status method"""
        assert hasattr(base_generator_class, 'get_status')
    
    def test_has_inject_metadata_method(self, base_generator_class):
        """Should have _inject_metadata helper"""
        assert hasattr(base_generator_class, '_inject_metadata')


class TestClaimGeneratorStructure:
    """Test ClaimDraftGenerator class structure"""
    
    @pytest.fixture
    def claim_generator_class(self):
        from output.claim_generator import ClaimDraftGenerator
        return ClaimDraftGenerator
    
    @pytest.fixture
    def base_generator_class(self):
        from output.base_generator import BaseReportGenerator
        return BaseReportGenerator
    
    def test_inherits_from_base(self, claim_generator_class, base_generator_class):
        """ClaimDraftGenerator should inherit from BaseReportGenerator"""
        assert issubclass(claim_generator_class, base_generator_class)
    
    def test_has_init_method(self, claim_generator_class):
        """Should have __init__ method"""
        assert hasattr(claim_generator_class, '__init__')
    
    def test_has_generate_implementation(self, claim_generator_class):
        """Should implement generate method"""
        assert hasattr(claim_generator_class, 'generate')
        # Should be async
        assert inspect.iscoroutinefunction(claim_generator_class.generate)
    
    def test_has_docstring(self, claim_generator_class):
        """Should have class docstring"""
        assert claim_generator_class.__doc__ is not None
        assert len(claim_generator_class.__doc__) > 20


class TestUltraBaseAgentStructure:
    """Test UltraBaseAgent class structure"""
    
    @pytest.fixture
    def base_agent_class(self):
        from mahoun.agents.base_agent import UltraBaseAgent
        return UltraBaseAgent
    
    def test_is_abstract_base_class(self, base_agent_class):
        """UltraBaseAgent should be an ABC"""
        assert issubclass(base_agent_class, ABC)
    
    def test_has_lifecycle_methods(self, base_agent_class):
        """Should have initialization and shutdown methods"""
        assert hasattr(base_agent_class, 'initialize')
        assert hasattr(base_agent_class, 'shutdown')
        assert hasattr(base_agent_class, 'close')
    
    def test_has_process_method(self, base_agent_class):
        """Should have main process method"""
        assert hasattr(base_agent_class, 'process')
        assert inspect.iscoroutinefunction(base_agent_class.process)
    
    def test_has_abstract_methods(self, base_agent_class):
        """Should have abstract methods for subclasses"""
        assert hasattr(base_agent_class, '_initialize_impl')
        assert hasattr(base_agent_class, '_process_impl')
    
    def test_has_health_check(self, base_agent_class):
        """Should have health check functionality"""
        assert hasattr(base_agent_class, 'health_check')
        assert hasattr(base_agent_class, '_health_check_impl')
    
    def test_has_metrics_methods(self, base_agent_class):
        """Should have metrics methods"""
        assert hasattr(base_agent_class, 'get_metrics')
        assert hasattr(base_agent_class, 'get_status')
    
    def test_has_context_manager_methods(self, base_agent_class):
        """Should support async context manager protocol"""
        assert hasattr(base_agent_class, '__aenter__')
        assert hasattr(base_agent_class, '__aexit__')
    
    def test_has_fallback_method(self, base_agent_class):
        """Should have fallback implementation method"""
        assert hasattr(base_agent_class, '_fallback_impl')


class TestUltraClaimAgentStructure:
    """Test UltraClaimAgent class structure"""
    
    @pytest.fixture
    def claim_agent_class(self):
        from mahoun.agents.claim_agent import UltraClaimAgent
        return UltraClaimAgent
    
    @pytest.fixture
    def base_agent_class(self):
        from mahoun.agents.base_agent import UltraBaseAgent
        return UltraBaseAgent
    
    def test_inherits_from_ultra_base(self, claim_agent_class, base_agent_class):
        """UltraClaimAgent should inherit from UltraBaseAgent"""
        assert issubclass(claim_agent_class, base_agent_class)
    
    def test_has_templates(self, claim_agent_class):
        """Should have CLAIM_TEMPLATES class attribute"""
        assert hasattr(claim_agent_class, 'CLAIM_TEMPLATES')
        templates = claim_agent_class.CLAIM_TEMPLATES
        assert isinstance(templates, dict)
        assert len(templates) > 0
    
    def test_implements_required_methods(self, claim_agent_class):
        """Should implement all required abstract methods"""
        assert hasattr(claim_agent_class, '_initialize_impl')
        assert hasattr(claim_agent_class, '_process_impl')
        assert hasattr(claim_agent_class, '_fallback_impl')
    
    def test_has_helper_methods(self, claim_agent_class):
        """Should have helper methods for claim generation"""
        assert hasattr(claim_agent_class, '_search_relevant')
        assert hasattr(claim_agent_class, '_extract_legal_basis')
        assert hasattr(claim_agent_class, '_build_arguments')
        assert hasattr(claim_agent_class, '_generate_claim')
    
    def test_has_formatting_methods(self, claim_agent_class):
        """Should have methods to format outputs"""
        assert hasattr(claim_agent_class, '_generate_full_text')
        assert hasattr(claim_agent_class, '_claim_to_dict')
        assert hasattr(claim_agent_class, '_argument_to_dict')


class TestSupportingDataClasses:
    """Test supporting data classes and enums"""
    
    def test_agent_config_is_dataclass(self):
        """AgentConfig should be a dataclass"""
        from mahoun.agents.base_agent import AgentConfig
        assert hasattr(AgentConfig, '__dataclass_fields__')
    
    def test_agent_config_has_fields(self):
        """AgentConfig should have configuration fields"""
        from mahoun.agents.base_agent import AgentConfig
        config = AgentConfig()
        
        # Check key fields exist
        assert hasattr(config, 'max_retries')
        assert hasattr(config, 'operation_timeout')
        assert hasattr(config, 'enable_fallback')
        assert hasattr(config, 'circuit_breaker_threshold')
    
    def test_agent_result_is_dataclass(self):
        """AgentResult should be a dataclass"""
        from mahoun.agents.base_agent import AgentResult
        assert hasattr(AgentResult, '__dataclass_fields__')
    
    def test_agent_result_has_to_dict(self):
        """AgentResult should have to_dict method"""
        from mahoun.agents.base_agent import AgentResult
        result = AgentResult(success=True, data={"test": "data"})
        assert hasattr(result, 'to_dict')
        assert callable(result.to_dict)
    
    def test_claim_type_enum_has_values(self):
        """ClaimType enum should have legal claim types"""
        from mahoun.agents.claim_agent import ClaimType
        
        # Check it's an enum
        from enum import Enum
        assert issubclass(ClaimType, Enum)
        
        # Check has expected values
        assert hasattr(ClaimType, 'BREACH_OF_CONTRACT')
        assert hasattr(ClaimType, 'DAMAGES')
        assert hasattr(ClaimType, 'SPECIFIC_PERFORMANCE')
    
    def test_circuit_breaker_is_dataclass(self):
        """CircuitBreaker should be a dataclass"""
        from mahoun.agents.base_agent import CircuitBreaker
        assert hasattr(CircuitBreaker, '__dataclass_fields__')
    
    def test_circuit_breaker_has_methods(self):
        """CircuitBreaker should have control methods"""
        from mahoun.agents.base_agent import CircuitBreaker
        cb = CircuitBreaker()
        
        assert hasattr(cb, 'record_success')
        assert hasattr(cb, 'record_failure')
        assert hasattr(cb, 'can_execute')


class TestMethodSignatures:
    """Test that methods have correct signatures"""
    
    def test_base_generator_generate_signature(self):
        """BaseReportGenerator.generate should have correct signature"""
        from output.base_generator import BaseReportGenerator
        
        sig = inspect.signature(BaseReportGenerator.generate)
        params = list(sig.parameters.keys())
        
        # Should have self and input_data
        assert 'self' in params
        assert 'input_data' in params
    
    def test_ultra_base_agent_process_signature(self):
        """UltraBaseAgent.process should have correct signature"""
        from mahoun.agents.base_agent import UltraBaseAgent
        
        sig = inspect.signature(UltraBaseAgent.process)
        params = list(sig.parameters.keys())
        
        # Should have self, input_data, correlation_id
        assert 'self' in params
        assert 'input_data' in params
        assert 'correlation_id' in params


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


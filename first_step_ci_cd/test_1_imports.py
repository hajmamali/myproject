"""
Test 1: Import Integrity Tests
================================
Verify that modules can be imported and are not empty placeholders.

Safety: ⭐⭐⭐⭐⭐ (No resources used)
"""

import pytest
import sys
import importlib
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestCoreImports:
    """Test that core modules import successfully"""
    
    def test_import_base_generator(self):
        """BaseReportGenerator should import without errors"""
        from output.base_generator import BaseReportGenerator
        assert BaseReportGenerator is not None
        assert hasattr(BaseReportGenerator, 'generate')
    
    def test_import_claim_generator(self):
        """ClaimDraftGenerator should import without errors"""
        from output.claim_generator import ClaimDraftGenerator
        assert ClaimDraftGenerator is not None
    
    def test_import_base_agent(self):
        """UltraBaseAgent should import without errors"""
        from mahoun.agents.base_agent import UltraBaseAgent
        assert UltraBaseAgent is not None
    
    def test_import_claim_agent(self):
        """UltraClaimAgent should import without errors"""
        from mahoun.agents.claim_agent import UltraClaimAgent
        assert UltraClaimAgent is not None


class TestModuleCompleteness:
    """Test that imported modules have expected content"""
    
    def test_base_generator_has_classes(self):
        """base_generator module should have BaseReportGenerator class"""
        import output.base_generator as module
        
        # Check module has content
        assert hasattr(module, 'BaseReportGenerator')
        assert hasattr(module, 'ABC')
        
        # Check it's a real class, not a placeholder
        assert hasattr(module.BaseReportGenerator, 'generate')
        assert hasattr(module.BaseReportGenerator, '__init__')
    
    def test_claim_generator_has_classes(self):
        """claim_generator module should have ClaimDraftGenerator class"""
        import output.claim_generator as module
        
        assert hasattr(module, 'ClaimDraftGenerator')
        assert hasattr(module, 'BaseReportGenerator')
        
        # Check inheritance
        from output.base_generator import BaseReportGenerator
        assert issubclass(module.ClaimDraftGenerator, BaseReportGenerator)
    
    def test_base_agent_has_classes(self):
        """base_agent module should have UltraBaseAgent and related classes"""
        import mahoun.agents.base_agent as module
        
        # Main class
        assert hasattr(module, 'UltraBaseAgent')
        
        # Supporting classes
        assert hasattr(module, 'AgentConfig')
        assert hasattr(module, 'AgentResult')
        assert hasattr(module, 'AgentState')
        assert hasattr(module, 'CircuitBreaker')
        assert hasattr(module, 'CircuitBreakerState')
    
    def test_claim_agent_has_classes(self):
        """claim_agent module should have UltraClaimAgent and supporting types"""
        import mahoun.agents.claim_agent as module
        
        # Main class
        assert hasattr(module, 'UltraClaimAgent')
        
        # Supporting types
        assert hasattr(module, 'ClaimType')
        assert hasattr(module, 'ClaimAgentConfig')
        assert hasattr(module, 'ClaimArgument')
        assert hasattr(module, 'GeneratedClaim')


class TestImportDependencies:
    """Test that dependencies are importable"""
    
    def test_pydantic_available(self):
        """Pydantic should be available"""
        try:
            import pydantic
            assert pydantic is not None
        except ImportError:
            pytest.skip("Pydantic not installed")
    
    def test_typing_available(self):
        """Typing module should be available"""
        from typing import Dict, Any, Optional, List
        assert Dict is not None
        assert Any is not None
        assert Optional is not None
        assert List is not None
    
    def test_asyncio_available(self):
        """Asyncio should be available"""
        import asyncio
        assert asyncio is not None
    
    def test_dataclasses_available(self):
        """Dataclasses should be available"""
        from dataclasses import dataclass, field
        assert dataclass is not None
        assert field is not None
    
    def test_enum_available(self):
        """Enum should be available"""
        from enum import Enum
        assert Enum is not None


class TestNoCircularImports:
    """Test that imports don't create circular dependencies"""
    
    def test_output_modules_no_circular_import(self):
        """Output modules should not have circular imports"""
        # This will raise ImportError if there's a circular dependency
        from output.base_generator import BaseReportGenerator
        from output.claim_generator import ClaimDraftGenerator
        
        # If we got here, no circular import
        assert True
    
    def test_agent_modules_no_circular_import(self):
        """Agent modules should not have circular imports"""
        from mahoun.agents.base_agent import UltraBaseAgent
        from mahoun.agents.claim_agent import UltraClaimAgent
        
        # If we got here, no circular import
        assert True


class TestModuleMetadata:
    """Test that modules have proper metadata"""
    
    def test_base_generator_has_imports(self):
        """base_generator should have necessary imports"""
        import output.base_generator as module
        # Check it has essential imports
        assert hasattr(module, 'BaseReportGenerator')
        assert hasattr(module, 'datetime')
    
    def test_claim_agent_has_docstring(self):
        """claim_agent module should have documentation"""
        import mahoun.agents.claim_agent as module
        assert module.__doc__ is not None
        assert len(module.__doc__) > 50  # Has substantial documentation
    
    def test_base_agent_has_docstring(self):
        """base_agent module should have documentation"""
        import mahoun.agents.base_agent as module
        assert module.__doc__ is not None
        assert len(module.__doc__) > 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


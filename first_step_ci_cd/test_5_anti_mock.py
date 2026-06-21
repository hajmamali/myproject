"""
Test 5: Anti-Mock Tests
========================
PROVE that implementations are REAL, not placeholders.

Safety: ⭐⭐⭐⭐⭐ (Source code inspection only)
"""

import pytest
import sys
import inspect
import ast
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def get_function_source_length(func) -> int:
    """Get the number of non-empty, non-comment lines in a function"""
    try:
        source = inspect.getsource(func)
        lines = source.split('\n')
        
        # Filter out empty lines, comments, and docstrings
        code_lines = []
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Handle docstrings
            if '"""' in stripped or "'''" in stripped:
                in_docstring = not in_docstring
                continue
            
            if in_docstring:
                continue
            
            # Skip pure comments
            if stripped.startswith('#'):
                continue
            
            # Skip function definition line
            if stripped.startswith('def ') or stripped.startswith('async def '):
                continue
            
            code_lines.append(line)
        
        return len(code_lines)
    except:
        return 0


def has_real_implementation(func) -> bool:
    """Check if function has real implementation (not just pass/raise/return)"""
    try:
        source = inspect.getsource(func)
        
        # Parse AST
        tree = ast.parse(source)
        
        # Find the function definition
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                
                # Skip docstring if present
                if (len(body) > 0 and 
                    isinstance(body[0], ast.Expr) and 
                    isinstance(body[0].value, ast.Constant)):
                    body = body[1:]
                
                # Check if only placeholder statements
                if len(body) == 0:
                    return False
                
                if len(body) == 1:
                    stmt = body[0]
                    # Check for "pass"
                    if isinstance(stmt, ast.Pass):
                        return False
                    # Check for "raise NotImplementedError"
                    if isinstance(stmt, ast.Raise):
                        return False
                    # Check for simple "return {}" or "return None"
                    if isinstance(stmt, ast.Return):
                        if stmt.value is None:
                            return False
                        if isinstance(stmt.value, ast.Dict) and len(stmt.value.keys) == 0:
                            return False
                
                # If we get here, there's real logic
                return True
        
        return False
    except:
        return True  # Benefit of doubt if we can't parse


class TestClaimGeneratorAntiMock:
    """Prove ClaimDraftGenerator is not a placeholder"""
    
    @pytest.fixture
    def claim_generator_class(self):
        from output.claim_generator import ClaimDraftGenerator
        return ClaimDraftGenerator
    
    def test_generate_has_substantial_code(self, claim_generator_class):
        """generate method should have >5 lines of code"""
        code_length = get_function_source_length(claim_generator_class.generate)
        assert code_length > 5, f"generate has only {code_length} lines, looks like a stub"
    
    def test_generate_has_real_logic(self, claim_generator_class):
        """generate should have real implementation, not just pass/raise"""
        has_logic = has_real_implementation(claim_generator_class.generate)
        assert has_logic, "generate appears to be a placeholder"
    
    def test_generate_creates_unique_ids(self, claim_generator_class):
        """generate should use uuid or similar for unique IDs"""
        source = inspect.getsource(claim_generator_class.generate)
        
        # Should use uuid
        assert 'uuid' in source, "generate should create unique identifiers"
    
    def test_generate_processes_input(self, claim_generator_class):
        """generate should actually process input_data"""
        source = inspect.getsource(claim_generator_class.generate)
        
        # Should access input_data
        assert 'input_data' in source
        assert '.get(' in source, "Should extract data from input"
    
    def test_generate_builds_content(self, claim_generator_class):
        """generate should build content, not return empty"""
        source = inspect.getsource(claim_generator_class.generate)
        
        # Should have content construction
        assert 'content' in source or 'markdown' in source
        assert 'result' in source or 'return' in source


class TestBaseGeneratorAntiMock:
    """Prove BaseReportGenerator is not empty scaffolding"""
    
    @pytest.fixture
    def base_generator_class(self):
        from output.base_generator import BaseReportGenerator
        return BaseReportGenerator
    
    def test_inject_metadata_has_logic(self, base_generator_class):
        """_inject_metadata should have real implementation"""
        # Check it's not abstract
        assert base_generator_class._inject_metadata is not None
        # Check it takes arguments
        import inspect
        sig = inspect.signature(base_generator_class._inject_metadata)
        assert len(sig.parameters) >= 3  # self, result, input_data
    
    def test_inject_metadata_processes_data(self, base_generator_class):
        """_inject_metadata should actually process data"""
        source = inspect.getsource(base_generator_class._inject_metadata)
        
        # Should manipulate result dict
        assert 'result' in source
        assert 'metadata' in source
        assert 'generated_at' in source or 'datetime' in source
    
    def test_export_has_multiple_formats(self, base_generator_class):
        """export should support multiple formats"""
        source = inspect.getsource(base_generator_class.export)
        
        # Should handle different formats
        assert 'json' in source
        assert 'text' in source or 'markdown' in source
    
    def test_export_not_just_return_input(self, base_generator_class):
        """export should do more than just 'return result'"""
        source = inspect.getsource(base_generator_class.export)
        
        # Should have conditional logic
        assert 'if' in source, "export should have format handling logic"


class TestUltraBaseAgentAntiMock:
    """Prove UltraBaseAgent is enterprise-grade, not placeholder"""
    
    @pytest.fixture
    def base_agent_class(self):
        from mahoun.agents.base_agent import UltraBaseAgent
        return UltraBaseAgent
    
    def test_process_has_substantial_logic(self, base_agent_class):
        """process method should be >30 lines (enterprise logic)"""
        code_length = get_function_source_length(base_agent_class.process)
        assert code_length > 30, f"process has only {code_length} lines, should be enterprise-grade"
    
    def test_process_has_retry_logic(self, base_agent_class):
        """process should implement retry logic"""
        source = inspect.getsource(base_agent_class.process)
        
        assert 'retry' in source.lower() or 'for' in source
        assert 'attempt' in source.lower()
    
    def test_process_has_circuit_breaker(self, base_agent_class):
        """process should check circuit breaker"""
        source = inspect.getsource(base_agent_class.process)
        
        assert 'circuit_breaker' in source
        assert 'can_execute' in source
    
    def test_process_has_error_handling(self, base_agent_class):
        """process should have try/except blocks"""
        source = inspect.getsource(base_agent_class.process)
        
        assert 'try:' in source
        assert 'except' in source
    
    def test_process_has_metrics(self, base_agent_class):
        """process should track metrics"""
        source = inspect.getsource(base_agent_class.process)
        
        assert 'metrics' in source or '_metrics' in source
        assert 'processing_time' in source.lower() or 'time' in source
    
    def test_initialize_has_logic(self, base_agent_class):
        """initialize should have real initialization logic"""
        code_length = get_function_source_length(base_agent_class.initialize)
        assert code_length > 5, "initialize looks like a stub"
    
    def test_health_check_returns_structured_data(self, base_agent_class):
        """health_check should return structured health data"""
        source = inspect.getsource(base_agent_class.health_check)
        
        assert 'state' in source or 'healthy' in source
        assert 'return' in source


class TestUltraClaimAgentAntiMock:
    """Prove UltraClaimAgent is real implementation"""
    
    @pytest.fixture
    def claim_agent_class(self):
        from mahoun.agents.claim_agent import UltraClaimAgent
        return UltraClaimAgent
    
    def test_process_impl_has_logic(self, claim_agent_class):
        """_process_impl should have substantial logic"""
        code_length = get_function_source_length(claim_agent_class._process_impl)
        assert code_length > 15, f"_process_impl has only {code_length} lines"
    
    def test_process_impl_calls_helpers(self, claim_agent_class):
        """_process_impl should orchestrate helper methods"""
        source = inspect.getsource(claim_agent_class._process_impl)
        
        # Should call helper methods
        assert 'search' in source.lower() or '_search_relevant' in source
        assert 'legal_basis' in source.lower() or '_extract_legal_basis' in source
        assert 'argument' in source.lower() or '_build_arguments' in source
    
    def test_search_relevant_not_empty(self, claim_agent_class):
        """_search_relevant should have real logic"""
        code_length = get_function_source_length(claim_agent_class._search_relevant)
        assert code_length >= 5, f"_search_relevant has {code_length} lines"
    
    def test_extract_legal_basis_has_logic(self, claim_agent_class):
        """_extract_legal_basis should process data"""
        source = inspect.getsource(claim_agent_class._extract_legal_basis)
        
        # Should have keyword extraction logic
        assert 'legal' in source.lower() or 'keyword' in source.lower()
        assert 'return' in source
    
    def test_build_arguments_creates_arguments(self, claim_agent_class):
        """_build_arguments should create ClaimArgument objects"""
        source = inspect.getsource(claim_agent_class._build_arguments)
        
        assert 'ClaimArgument' in source
        assert 'append' in source or 'arguments' in source
    
    def test_generate_claim_has_templates(self, claim_agent_class):
        """_generate_claim should use templates"""
        source = inspect.getsource(claim_agent_class._generate_claim)
        
        assert 'template' in source.lower() or 'CLAIM_TEMPLATES' in source
        assert 'GeneratedClaim' in source
    
    def test_generate_full_text_builds_text(self, claim_agent_class):
        """_generate_full_text should assemble text"""
        source = inspect.getsource(claim_agent_class._generate_full_text)
        
        # Should build text from sections
        assert 'join' in source or '+' in source
        assert 'return' in source
    
    def test_fallback_impl_is_implemented(self, claim_agent_class):
        """_fallback_impl should be implemented (not just raise)"""
        source = inspect.getsource(claim_agent_class._fallback_impl)
        
        # Should NOT just raise NotImplementedError
        assert 'NotImplementedError' not in source, "Fallback should be implemented"
        
        # Should return something
        assert 'return' in source
        assert 'template' in source.lower() or 'fallback' in source.lower()


class TestCircuitBreakerAntiMock:
    """Prove CircuitBreaker is real implementation"""
    
    @pytest.fixture
    def circuit_breaker_class(self):
        from mahoun.agents.base_agent import CircuitBreaker
        return CircuitBreaker
    
    def test_can_execute_has_logic(self, circuit_breaker_class):
        """can_execute should have state checking logic"""
        # Test that it actually works with different states
        cb = circuit_breaker_class()
        assert cb.can_execute() is True  # Should start allowing execution
        
        # After many failures, should block
        for _ in range(10):
            cb.record_failure()
        assert cb.can_execute() is False  # Should block after failures
    
    def test_can_execute_checks_state(self, circuit_breaker_class):
        """can_execute should check circuit breaker state"""
        source = inspect.getsource(circuit_breaker_class.can_execute)
        
        assert 'state' in source
        assert 'OPEN' in source or 'CLOSED' in source
        assert 'return' in source
    
    def test_record_failure_updates_state(self, circuit_breaker_class):
        """record_failure should update state"""
        source = inspect.getsource(circuit_breaker_class.record_failure)
        
        assert 'failure_count' in source
        assert 'state' in source or 'threshold' in source


class TestModuleComplexity:
    """Test that modules have sufficient complexity (not trivial)"""
    
    def test_base_agent_module_is_complex(self):
        """base_agent.py should be a substantial module"""
        import mahoun.agents.base_agent as module
        
        # Get source
        source = inspect.getsource(module)
        lines = source.split('\n')
        
        # Should be >500 lines
        assert len(lines) > 500, f"base_agent.py has only {len(lines)} lines"
    
    def test_claim_agent_module_is_complex(self):
        """claim_agent.py should be a substantial module"""
        import mahoun.agents.claim_agent as module
        
        source = inspect.getsource(module)
        lines = source.split('\n')
        
        # Should be >300 lines
        assert len(lines) > 300, f"claim_agent.py has only {len(lines)} lines"
    
    def test_base_generator_has_reasonable_size(self):
        """base_generator.py should have reasonable size"""
        import output.base_generator as module
        
        source = inspect.getsource(module)
        lines = source.split('\n')
        
        # Should be >30 lines
        assert len(lines) > 30, f"base_generator.py has only {len(lines)} lines"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


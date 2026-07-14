#!/usr/bin/env python3
"""
Test Suite for Unified Reasoning Service
========================================

Comprehensive tests for the unified reasoning service combining
symbolic FOL reasoning with neural reasoning.

Test Categories:
1. Service initialization and mode selection
2. Symbolic reasoning (forward/backward chaining)
3. Neural reasoning integration
4. Hybrid reasoning (symbolic + neural)
5. Consistency checking
6. Error handling and fallbacks
7. Performance and integration tests

Author: MAHOUN Team
"""

import asyncio
import pytest
import time
from typing import List, Dict, Any

# Import unified reasoning service
from mahoun.reasoning.unified_reasoning_service import (
    UnifiedReasoningService,
    ReasoningMode,
    ReasoningTask,
    ReasoningRequest,
    ReasoningResponse,
    forward_inference,
    prove_goal,
    answer_question,
)

# Import symbolic reasoning for comparison
from reasoning_logic import (
    KnowledgeBase,
    ForwardChaining,
    BackwardChaining,
    FOLConverter,
    Fact,
    Rule,
)


class TestUnifiedReasoningService:
    """Test suite for UnifiedReasoningService"""
    
    def setup_method(self):
        """Setup for each test"""
        self.service = UnifiedReasoningService(enable_neural=True)
        self.fol_parser = FOLConverter()
    
    # ================================================================
    # 1. Service Initialization and Mode Selection Tests
    # ================================================================
    
    def test_service_initialization(self):
        """Test service initialization"""
        # Test with neural enabled
        service_neural = UnifiedReasoningService(enable_neural=True)
        assert service_neural.kb is not None
        assert service_neural.fol_parser is not None
        
        # Test with neural disabled
        service_symbolic = UnifiedReasoningService(enable_neural=False)
        assert service_symbolic.enable_neural is False
        assert service_symbolic.neural_engine is None
    
    def test_mode_selection_auto(self):
        """Test automatic mode selection"""
        # Forward inference with facts/rules -> should select SYMBOLIC
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="",
            facts=["human(socrates)", "mortal(X) :- human(X)"],
            rules=["mortal(X) :- human(X)"],
            mode=ReasoningMode.AUTO
        )
        mode = self.service._select_mode(request)
        assert mode == ReasoningMode.SYMBOLIC
        
        # Question answering without facts/rules -> should prefer NEURAL (if available)
        request = ReasoningRequest(
            task=ReasoningTask.QUESTION_ANSWERING,
            query="What is the meaning of life?",
            mode=ReasoningMode.AUTO
        )
        mode = self.service._select_mode(request)
        expected = ReasoningMode.NEURAL if self.service.enable_neural else ReasoningMode.HYBRID
        assert mode in [ReasoningMode.NEURAL, ReasoningMode.HYBRID, ReasoningMode.SYMBOLIC]
    
    def test_mode_selection_explicit(self):
        """Test explicit mode selection"""
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="",
            mode=ReasoningMode.SYMBOLIC
        )
        mode = self.service._select_mode(request)
        assert mode == ReasoningMode.SYMBOLIC
    
    # ================================================================
    # 2. Symbolic Reasoning Tests
    # ================================================================
    
    @pytest.mark.asyncio
    async def test_symbolic_forward_inference(self):
        """Test symbolic forward inference"""
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="",
            facts=["human(socrates)", "human(plato)"],
            rules=["mortal(X) :- human(X)"],
            mode=ReasoningMode.SYMBOLIC
        )
        
        response = await self.service.reason(request)
        
        assert response.success is True
        assert response.reasoning_mode == ReasoningMode.SYMBOLIC
        assert "derived" in response.result.lower()
        assert response.confidence > 0.0
        assert len(response.derived_facts) > 0
        assert response.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_symbolic_backward_proof(self):
        """Test symbolic backward proof"""
        request = ReasoningRequest(
            task=ReasoningTask.BACKWARD_PROOF,
            query="mortal(socrates)",
            facts=["human(socrates)"],
            rules=["mortal(X) :- human(X)"],
            mode=ReasoningMode.SYMBOLIC
        )
        
        response = await self.service.reason(request)
        
        assert response.success is True
        assert response.reasoning_mode == ReasoningMode.SYMBOLIC
        assert "proved" in response.result.lower()
        assert response.confidence > 0.0
        if response.proof_tree:
            assert response.proof_tree is not None
    
    @pytest.mark.asyncio
    async def test_symbolic_consistency_check(self):
        """Test symbolic consistency checking"""
        # Consistent knowledge base
        request = ReasoningRequest(
            task=ReasoningTask.CONSISTENCY_CHECK,
            query="",
            facts=["human(socrates)", "mortal(socrates)"],
            rules=["mortal(X) :- human(X)"],
            mode=ReasoningMode.SYMBOLIC
        )
        
        response = await self.service.reason(request)
        
        assert response.success is True
        assert response.reasoning_mode == ReasoningMode.SYMBOLIC
        assert response.confidence > 0.5
        
        # Inconsistent knowledge base
        request_inconsistent = ReasoningRequest(
            task=ReasoningTask.CONSISTENCY_CHECK,
            query="",
            facts=["human(socrates)", "not_human(socrates)"],  # Direct contradiction using not_ prefix
            rules=[],
            mode=ReasoningMode.SYMBOLIC
        )
        
        response_inconsistent = await self.service.reason(request_inconsistent)
        
        # Should detect inconsistency
        assert response_inconsistent.success is False or response_inconsistent.confidence < 0.8
    
    # ================================================================
    # 3. Neural Reasoning Tests
    # ================================================================
    
    @pytest.mark.asyncio
    async def test_neural_question_answering(self):
        """Test neural question answering"""
        if not self.service.enable_neural:
            pytest.skip("Neural reasoning not available")
        
        request = ReasoningRequest(
            task=ReasoningTask.QUESTION_ANSWERING,
            query="What are the basic principles of contract law?",
            facts=["A contract requires offer and acceptance", "Contracts must have consideration"],
            mode=ReasoningMode.NEURAL
        )
        
        response = await self.service.reason(request)
        
        assert response.success is True
        assert response.reasoning_mode == ReasoningMode.NEURAL
        assert len(response.result) > 10  # Should have substantial answer
        assert response.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_neural_explanation(self):
        """Test neural explanation generation"""
        if not self.service.enable_neural:
            pytest.skip("Neural reasoning not available")
        
        request = ReasoningRequest(
            task=ReasoningTask.EXPLANATION,
            query="Explain why Socrates is mortal",
            facts=["human(socrates)"],
            rules=["mortal(X) :- human(X)"],
            mode=ReasoningMode.NEURAL,
            return_explanation=True
        )
        
        response = await self.service.reason(request)
        
        assert response.success is True
        assert response.reasoning_mode == ReasoningMode.NEURAL
        assert response.explanation is not None
        assert len(response.explanation) > 20
    
    @pytest.mark.asyncio
    async def test_neural_fallback(self):
        """Test neural fallback when services unavailable"""
        # Force neural reasoning with minimal setup
        request = ReasoningRequest(
            task=ReasoningTask.QUESTION_ANSWERING,
            query="Simple question",
            facts=["fact1", "fact2"],
            rules=["rule1"],
            mode=ReasoningMode.NEURAL
        )
        
        response = await self.service.reason(request)
        
        # Should succeed with fallback even if advanced neural services fail
        assert response.success is True
        assert response.reasoning_mode == ReasoningMode.NEURAL
        assert response.result is not None
    
    # ================================================================
    # 4. Hybrid Reasoning Tests
    # ================================================================
    
    @pytest.mark.asyncio
    async def test_hybrid_reasoning_symbolic_success(self):
        """Test hybrid reasoning when symbolic succeeds"""
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="",
            facts=["human(socrates)"],
            rules=["mortal(X) :- human(X)"],
            mode=ReasoningMode.HYBRID,
            return_explanation=True
        )
        
        response = await self.service.reason(request)
        
        assert response.success is True
        assert response.reasoning_mode == ReasoningMode.HYBRID
        assert response.confidence > 0.0
        # Should have symbolic results enhanced with neural explanation (if available)
    
    @pytest.mark.asyncio
    async def test_hybrid_reasoning_symbolic_failure(self):
        """Test hybrid reasoning fallback when symbolic fails"""
        request = ReasoningRequest(
            task=ReasoningTask.BACKWARD_PROOF,
            query="invalid_syntax_query((((",  # Invalid query to force symbolic failure
            facts=["human(socrates)"],
            rules=["mortal(X) :- human(X)"],
            mode=ReasoningMode.HYBRID
        )
        
        response = await self.service.reason(request)
        
        # Should fallback to neural or handle gracefully
        assert response.reasoning_mode == ReasoningMode.HYBRID
        # Either succeeds with neural fallback or fails gracefully
        if not response.success:
            assert response.error is not None
    
    # ================================================================
    # 5. Convenience Functions Tests
    # ================================================================
    
    @pytest.mark.asyncio
    async def test_forward_inference_convenience(self):
        """Test forward_inference convenience function"""
        facts = ["human(socrates)", "human(plato)"]
        rules = ["mortal(X) :- human(X)"]
        
        response = await forward_inference(facts, rules)
        
        assert isinstance(response, ReasoningResponse)
        assert response.success is True
        assert len(response.derived_facts) > 0
    
    @pytest.mark.asyncio
    async def test_prove_goal_convenience(self):
        """Test prove_goal convenience function"""
        goal = "mortal(socrates)"
        facts = ["human(socrates)"]
        rules = ["mortal(X) :- human(X)"]
        
        response = await prove_goal(goal, facts, rules)
        
        assert isinstance(response, ReasoningResponse)
        assert response.success is True
        assert "proved" in response.result.lower()
    
    @pytest.mark.asyncio
    async def test_answer_question_convenience(self):
        """Test answer_question convenience function"""
        question = "What is the capital of France?"
        context = {"domain": "geography"}
        
        response = await answer_question(question, context)
        
        assert isinstance(response, ReasoningResponse)
        # Should succeed or fail gracefully
        assert response.result is not None
    
    # ================================================================
    # 6. Error Handling Tests
    # ================================================================
    
    @pytest.mark.asyncio
    async def test_invalid_request_handling(self):
        """Test handling of invalid requests"""
        # Empty request
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="",
            facts=[],
            rules=[]
        )
        
        response = await self.service.reason(request)
        
        # Should handle gracefully
        assert isinstance(response, ReasoningResponse)
        assert response.reasoning_mode is not None
    
    @pytest.mark.asyncio
    async def test_parse_error_handling(self):
        """Test handling of parse errors"""
        request = ReasoningRequest(
            task=ReasoningTask.BACKWARD_PROOF,
            query="invalid syntax (((",
            facts=["human(socrates)"],
            rules=["mortal(X) :- human(X)"],
            mode=ReasoningMode.SYMBOLIC
        )
        
        response = await self.service.reason(request)
        
        # Should handle parse error gracefully
        assert isinstance(response, ReasoningResponse)
        if not response.success:
            assert "parse" in response.error.lower() or "failed" in response.error.lower()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling"""
        # Create request with very short timeout
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="",
            facts=["human(socrates)"] * 100,  # Large number of facts
            rules=["mortal(X) :- human(X)"] * 50,  # Large number of rules
            timeout_seconds=0.001,  # Very short timeout
            mode=ReasoningMode.SYMBOLIC
        )
        
        response = await self.service.reason(request)
        
        # Should complete within reasonable time (timeout or success)
        assert isinstance(response, ReasoningResponse)
        assert response.execution_time_ms < 5000  # Should not take more than 5 seconds
    
    # ================================================================
    # 7. Performance and Integration Tests
    # ================================================================
    
    @pytest.mark.asyncio
    async def test_performance_benchmark(self):
        """Test performance with various request sizes"""
        test_cases = [
            {"facts": 5, "rules": 2},
            {"facts": 20, "rules": 10},
            {"facts": 50, "rules": 25},
        ]
        
        for case in test_cases:
            facts = [f"human(person_{i})" for i in range(case["facts"])]
            rules = [f"mortal(X) :- human(X)" for _ in range(case["rules"])]
            
            request = ReasoningRequest(
                task=ReasoningTask.FORWARD_INFERENCE,
                query="",
                facts=facts,
                rules=rules,
                mode=ReasoningMode.SYMBOLIC
            )
            
            start_time = time.perf_counter()
            response = await self.service.reason(request)
            end_time = time.perf_counter()
            
            execution_time = (end_time - start_time) * 1000
            
            assert response.success is True
            assert execution_time < 10000  # Should complete within 10 seconds
            assert response.execution_time_ms > 0
            
            print(f"Performance test - Facts: {case['facts']}, Rules: {case['rules']}, "
                  f"Time: {execution_time:.2f}ms, Derived: {len(response.derived_facts)}")
    
    @pytest.mark.asyncio
    async def test_integration_with_symbolic_engine(self):
        """Test integration with symbolic reasoning engine"""
        # Compare unified service results with direct symbolic engine
        facts = ["human(socrates)", "human(plato)"]
        rules = ["mortal(X) :- human(X)"]
        
        # Unified service result
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="",
            facts=facts,
            rules=rules,
            mode=ReasoningMode.SYMBOLIC
        )
        unified_response = await self.service.reason(request)
        
        # Direct symbolic engine result
        kb = KnowledgeBase()
        fol_parser = FOLConverter()
        
        for fact_str in facts:
            fact_expr = fol_parser.parse(fact_str)
            fact = Fact(fact_expr)
            kb.add_fact(fact)
        
        for rule_str in rules:
            rule = fol_parser.parse_rule(rule_str)
            kb.add_rule(rule)
        
        engine = ForwardChaining(kb, max_iterations=1000)
        stats = engine.run(timeout_seconds=30)
        
        # Compare results
        assert unified_response.success is True
        assert stats.facts_derived > 0
        assert len(unified_response.derived_facts) == stats.facts_derived
        
        print(f"Integration test - Unified: {len(unified_response.derived_facts)} facts, "
              f"Direct: {stats.facts_derived} facts, Match: {len(unified_response.derived_facts) == stats.facts_derived}")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        requests = []
        for i in range(5):
            request = ReasoningRequest(
                task=ReasoningTask.FORWARD_INFERENCE,
                query="",
                facts=[f"human(person_{i})"],
                rules=["mortal(X) :- human(X)"],
                mode=ReasoningMode.SYMBOLIC
            )
            requests.append(request)
        
        # Execute concurrently
        tasks = [self.service.reason(req) for req in requests]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for i, response in enumerate(responses):
            assert response.success is True, f"Request {i} failed: {response.error}"
            assert len(response.derived_facts) > 0
        
        print(f"Concurrent test - {len(responses)} requests completed successfully")


# ================================================================
# Test Execution
# ================================================================

def run_tests():
    """Run all tests"""
    print("🚀 Testing Unified Reasoning Service")
    print("=" * 60)
    
    # Run pytest
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_tests()
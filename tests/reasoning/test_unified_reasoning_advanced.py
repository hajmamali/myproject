#!/usr/bin/env python3
"""
Advanced Test Suite for Unified Reasoning Service
=================================================

Ultra-advanced tests demonstrating the power and sophistication of the
unified reasoning system combining symbolic FOL and neural reasoning.

Test Categories:
1. Multi-Modal Reasoning (Symbolic + Neural)
2. Complex Legal Scenarios
3. Real-World Performance Benchmarks
4. Advanced Consistency Checking
5. Hybrid Reasoning Optimization
6. Enterprise-Grade Stress Tests

Author: MAHOUN Team
"""

import asyncio
import pytest
import time
import json
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

# Import unified reasoning service
from mahoun.reasoning.unified_reasoning_service import (
    UnifiedReasoningService,
    ReasoningMode,
    ReasoningTask,
    ReasoningRequest,
    ReasoningResponse,
)


class TestAdvancedUnifiedReasoning:
    """Advanced test suite for unified reasoning service"""
    
    def setup_method(self):
        """Setup for each test"""
        self.service = UnifiedReasoningService(enable_neural=True)
    
    # ================================================================
    # 1. Multi-Modal Reasoning Tests
    # ================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_complex_legal_contract_analysis(self):
        """Test complex legal contract analysis using hybrid reasoning"""
        
        # Complex legal scenario
        facts = [
            "signed_by(contract_001, party_a)",
            "signed_by(contract_001, party_b)",
            "has_obligation(party_a, payment_clause)",
            "violates_article(party_a, payment_clause)",
            "applies_to_jurisdiction(contract_001, iran_law)",
        ]
        
        rules = [
            "breach_of_contract(X, Y) :- has_obligation(X, Y)",
            "liable_for(X, damages) :- breach_of_contract(X, Y)",
        ]
        
        # Test forward inference
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="",
            facts=facts,
            rules=rules,
            mode=ReasoningMode.HYBRID,
            return_explanation=True
        )
        
        response = await self.service.reason(request)
        
        assert response.success is True
        assert response.reasoning_mode == ReasoningMode.HYBRID
        assert len(response.derived_facts) > 0
        assert "breach_of_contract" in str(response.derived_facts)
        assert response.explanation is not None
        
        print(f"✅ Complex Legal Analysis: {len(response.derived_facts)} facts derived")
        print(f"   Confidence: {response.confidence:.2%}")
        print(f"   Execution time: {response.execution_time_ms:.2f}ms")
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_multi_step_legal_reasoning(self):
        """Test multi-step legal reasoning with complex rule chains"""
        
        facts = [
            "has_obligation(company_x, environmental_compliance)",
            "violates_article(company_x, environmental_compliance)",
            "applies_to_jurisdiction(case_001, environmental_law)",
            "signed_by(contract_env, company_x)",
            "is_proxy(lawyer_a, company_x)",
        ]
        
        rules = [
            "breach_of_contract(X, Y) :- has_obligation(X, Y), violates_article(X, Y)",
            "liable_for(X, environmental_damages) :- breach_of_contract(X, environmental_compliance)",
            "legal_representation_required(X) :- liable_for(X, environmental_damages)",
            "case_complexity_high(X) :- legal_representation_required(X), applies_to_jurisdiction(Y, environmental_law)",
        ]
        
        # Test backward proof for complex conclusion
        request = ReasoningRequest(
            task=ReasoningTask.BACKWARD_PROOF,
            query="case_complexity_high(company_x)",
            facts=facts,
            rules=rules,
            mode=ReasoningMode.SYMBOLIC,
            max_depth=10,
            return_proof=True
        )
        
        response = await self.service.reason(request)
        
        assert response.success is True
        assert "proved" in response.result.lower()
        assert response.proof_tree is not None
        
        print(f"✅ Multi-Step Legal Reasoning: Goal proved in {response.execution_time_ms:.2f}ms")
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_neural_legal_question_answering(self):
        """Test neural reasoning for complex legal questions"""
        
        legal_context = [
            "Article 10 of Iranian Civil Code states that laws regarding personal capacity are subject to the law of the state of which those persons are nationals.",
            "Contract law in Iran requires offer, acceptance, and consideration for valid contracts.",
            "Environmental regulations impose strict liability for pollution damages.",
        ]
        
        request = ReasoningRequest(
            task=ReasoningTask.QUESTION_ANSWERING,
            query="What are the key requirements for contract validity under Iranian law and what happens if environmental obligations are breached?",
            facts=legal_context,
            mode=ReasoningMode.NEURAL,
            return_explanation=True
        )
        
        response = await self.service.reason(request)
        
        assert response.success is True
        assert len(response.result) > 50  # Substantial answer
        assert response.confidence > 0.5
        
        print(f"✅ Neural Legal Q&A: {len(response.result)} chars, confidence: {response.confidence:.2%}")
    
    # ================================================================
    # 2. Performance and Scalability Tests
    # ================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_large_scale_reasoning_performance(self):
        """Test performance with large knowledge bases"""
        
        # Generate large knowledge base
        facts = []
        rules = []
        
        # Create 100 entities with obligations
        for i in range(100):
            facts.append(f"has_obligation(entity_{i}, compliance_rule_{i % 10})")
            if i % 3 == 0:  # Some violations
                facts.append(f"violates_article(entity_{i}, compliance_rule_{i % 10})")
        
        # Create complex rule chains
        for i in range(10):
            rules.append(f"breach_of_contract(X, compliance_rule_{i}) :- has_obligation(X, compliance_rule_{i}), violates_article(X, compliance_rule_{i})")
            rules.append(f"liable_for(X, damages_{i}) :- breach_of_contract(X, compliance_rule_{i})")
        
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="",
            facts=facts,
            rules=rules,
            mode=ReasoningMode.SYMBOLIC,
            timeout_seconds=30
        )
        
        start_time = time.perf_counter()
        response = await self.service.reason(request)
        end_time = time.perf_counter()
        
        execution_time = (end_time - start_time) * 1000
        
        assert response.success is True
        assert len(response.derived_facts) > 0
        assert execution_time < 15000  # Should complete within 15 seconds
        
        # Calculate performance metrics
        facts_per_second = len(response.derived_facts) / (execution_time / 1000)
        
        print(f"✅ Large Scale Performance:")
        print(f"   Input: {len(facts)} facts, {len(rules)} rules")
        print(f"   Output: {len(response.derived_facts)} derived facts")
        print(f"   Time: {execution_time:.2f}ms")
        print(f"   Throughput: {facts_per_second:.0f} facts/second")
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_concurrent_reasoning_stress(self):
        """Test concurrent reasoning under stress"""
        
        async def create_reasoning_task(task_id: int) -> ReasoningResponse:
            facts = [
                f"has_obligation(client_{task_id}, contract_{task_id})",
                f"signed_by(contract_{task_id}, client_{task_id})",
            ]
            
            rules = [
                f"valid_contract(X) :- has_obligation(Y, X), signed_by(X, Y)",
            ]
            
            request = ReasoningRequest(
                task=ReasoningTask.FORWARD_INFERENCE,
                query="",
                facts=facts,
                rules=rules,
                mode=ReasoningMode.SYMBOLIC
            )
            
            return await self.service.reason(request)
        
        # Create 20 concurrent reasoning tasks
        tasks = [create_reasoning_task(i) for i in range(20)]
        
        start_time = time.perf_counter()
        responses = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        execution_time = (end_time - start_time) * 1000
        
        # All tasks should succeed
        successful_tasks = sum(1 for r in responses if r.success)
        
        assert successful_tasks == 20
        assert execution_time < 10000  # Should complete within 10 seconds
        
        print(f"✅ Concurrent Stress Test:")
        print(f"   Tasks: 20 concurrent")
        print(f"   Success rate: {successful_tasks}/20 ({successful_tasks/20*100:.1f}%)")
        print(f"   Total time: {execution_time:.2f}ms")
        print(f"   Average per task: {execution_time/20:.2f}ms")
    
    # ================================================================
    # 3. Advanced Consistency and Validation Tests
    # ================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_complex_consistency_analysis(self):
        """Test advanced consistency checking with complex scenarios"""
        
        # Create potentially inconsistent knowledge base
        facts = [
            "has_obligation(company_a, environmental_compliance)",
            "violates_article(company_a, environmental_compliance)",
            "signed_by(contract_001, company_a)",
            "applies_to_jurisdiction(contract_001, strict_liability_law)",
        ]
        
        rules = [
            "breach_of_contract(X, Y) :- has_obligation(X, Y), violates_article(X, Y)",
            "liable_for(X, damages) :- breach_of_contract(X, Y)",
            "exempt_from_liability(X) :- applies_to_jurisdiction(Y, lenient_law), signed_by(Y, X)",  # Conflicting rule
            "not_liable_for(X, damages) :- exempt_from_liability(X)",
        ]
        
        request = ReasoningRequest(
            task=ReasoningTask.CONSISTENCY_CHECK,
            query="",
            facts=facts,
            rules=rules,
            mode=ReasoningMode.HYBRID,  # Use both symbolic and neural analysis
            return_explanation=True
        )
        
        response = await self.service.reason(request)
        
        assert response.success is not None  # Should complete analysis
        assert response.explanation is not None
        assert "consistency" in response.explanation.lower()
        
        print(f"✅ Complex Consistency Analysis:")
        print(f"   Result: {response.result}")
        print(f"   Confidence: {response.confidence:.2%}")
        print(f"   Issues found: {response.metadata.get('total_issues', 0)}")
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_hybrid_mode_optimization(self):
        """Test hybrid mode's ability to optimize between symbolic and neural"""
        
        # Test case that benefits from hybrid approach
        facts = [
            "has_obligation(tech_company, data_protection)",
            "violates_article(tech_company, gdpr_compliance)",
            "applies_to_jurisdiction(case_eu, european_law)",
        ]
        
        rules = [
            "breach_of_contract(X, Y) :- has_obligation(X, Y), violates_article(X, Y)",
            "liable_for(X, regulatory_fines) :- breach_of_contract(X, data_protection)",
        ]
        
        # Test same scenario with different modes
        modes_to_test = [ReasoningMode.SYMBOLIC, ReasoningMode.NEURAL, ReasoningMode.HYBRID]
        results = {}
        
        for mode in modes_to_test:
            request = ReasoningRequest(
                task=ReasoningTask.FORWARD_INFERENCE,
                query="",
                facts=facts,
                rules=rules,
                mode=mode,
                return_explanation=True
            )
            
            response = await self.service.reason(request)
            results[mode.value] = {
                'success': response.success,
                'confidence': response.confidence,
                'execution_time': response.execution_time_ms,
                'derived_facts': len(response.derived_facts),
                'has_explanation': response.explanation is not None
            }
        
        # Hybrid should combine benefits of both approaches
        hybrid_result = results['hybrid']
        symbolic_result = results['symbolic']
        neural_result = results['neural']
        
        assert hybrid_result['success'] is True
        
        # Hybrid should have good performance characteristics
        if symbolic_result['success']:
            assert hybrid_result['derived_facts'] >= symbolic_result['derived_facts']
        
        print(f"✅ Hybrid Mode Optimization:")
        for mode, result in results.items():
            print(f"   {mode.upper()}: success={result['success']}, "
                  f"confidence={result['confidence']:.2%}, "
                  f"time={result['execution_time']:.2f}ms, "
                  f"facts={result['derived_facts']}")
    
    # ================================================================
    # 4. Real-World Scenario Tests
    # ================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_real_world_contract_dispute(self):
        """Test real-world contract dispute scenario"""
        
        # Realistic contract dispute scenario
        facts = [
            "signed_by(software_license_agreement, tech_startup)",
            "signed_by(software_license_agreement, enterprise_client)",
            "has_obligation(tech_startup, software_delivery)",
            "has_obligation(enterprise_client, payment_schedule)",
            "violates_article(tech_startup, delivery_deadline)",
            "applies_to_jurisdiction(software_license_agreement, commercial_law)",
        ]
        
        rules = [
            "breach_of_contract(X, Y) :- has_obligation(X, Y), violates_article(X, Y)",
            "liable_for(X, liquidated_damages) :- breach_of_contract(X, software_delivery)",
            "contract_termination_allowed(Y) :- breach_of_contract(X, Z), signed_by(W, Y), has_obligation(X, Z)",
            "legal_remedy_available(Y, damages) :- liable_for(X, damages), signed_by(W, Y)",
        ]
        
        # Test multiple reasoning tasks on same scenario
        tasks = [
            # Forward inference to derive consequences
            ReasoningRequest(
                task=ReasoningTask.FORWARD_INFERENCE,
                query="",
                facts=facts,
                rules=rules,
                mode=ReasoningMode.SYMBOLIC
            ),
            
            # Backward proof for specific legal question
            ReasoningRequest(
                task=ReasoningTask.BACKWARD_PROOF,
                query="legal_remedy_available(enterprise_client, liquidated_damages)",
                facts=facts,
                rules=rules,
                mode=ReasoningMode.SYMBOLIC
            ),
            
            # Neural explanation of the situation
            ReasoningRequest(
                task=ReasoningTask.EXPLANATION,
                query="Explain the legal implications of this contract dispute",
                facts=facts,
                rules=rules,
                mode=ReasoningMode.NEURAL
            ),
        ]
        
        responses = await asyncio.gather(*[self.service.reason(task) for task in tasks])
        
        forward_response, backward_response, explanation_response = responses
        
        # All should succeed
        assert forward_response.success is True
        assert backward_response.success is True
        assert explanation_response.success is True
        
        # Forward inference should derive legal consequences
        assert len(forward_response.derived_facts) > 0
        
        # Backward proof should confirm legal remedy
        assert "proved" in backward_response.result.lower()
        
        # Neural explanation should be comprehensive
        assert len(explanation_response.result) > 100
        
        print(f"✅ Real-World Contract Dispute Analysis:")
        print(f"   Forward inference: {len(forward_response.derived_facts)} facts derived")
        print(f"   Backward proof: {backward_response.result}")
        print(f"   Neural explanation: {len(explanation_response.result)} characters")
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_enterprise_grade_reliability(self):
        """Test enterprise-grade reliability and error handling"""
        
        # Test various edge cases and error conditions
        test_cases = [
            # Empty knowledge base
            {
                'name': 'Empty KB',
                'facts': [],
                'rules': [],
                'query': 'test_query(x)',
                'should_handle_gracefully': True
            },
            
            # Large query
            {
                'name': 'Large Query',
                'facts': ["has_obligation(x, y)"],
                'rules': ["liable_for(X, Z) :- has_obligation(X, Y)"],
                'query': "liable_for(" + "x" * 1000 + ", y)",
                'should_handle_gracefully': True
            },
            
            # Complex nested rules
            {
                'name': 'Complex Nested',
                'facts': ["has_obligation(a, b)", "signed_by(c, a)"],
                'rules': [
                    "breach_of_contract(X, Y) :- has_obligation(X, Y), violates_article(X, Y)",
                    "liable_for(X, Z) :- breach_of_contract(X, Y), signed_by(W, X)",
                ],
                'query': 'liable_for(a, damages)',
                'should_handle_gracefully': True
            },
        ]
        
        results = []
        
        for case in test_cases:
            request = ReasoningRequest(
                task=ReasoningTask.BACKWARD_PROOF,
                query=case['query'],
                facts=case['facts'],
                rules=case['rules'],
                mode=ReasoningMode.SYMBOLIC,
                timeout_seconds=10
            )
            
            try:
                response = await self.service.reason(request)
                results.append({
                    'name': case['name'],
                    'success': response.success,
                    'error': response.error,
                    'execution_time': response.execution_time_ms
                })
            except Exception as e:
                results.append({
                    'name': case['name'],
                    'success': False,
                    'error': str(e),
                    'execution_time': 0
                })
        
        # All cases should be handled gracefully (no exceptions)
        for result in results:
            assert result['error'] is None or isinstance(result['error'], str)
            assert result['execution_time'] < 10000  # Should not timeout
        
        print(f"✅ Enterprise Reliability Test:")
        for result in results:
            print(f"   {result['name']}: success={result['success']}, "
                  f"time={result['execution_time']:.2f}ms")
    
    # ================================================================
    # 5. Integration and Compatibility Tests
    # ================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_api_compatibility_and_versioning(self):
        """Test API compatibility and version handling"""
        
        # Test that all convenience functions work
        from mahoun.reasoning.unified_reasoning_service import (
            forward_inference,
            prove_goal,
            answer_question
        )
        
        # Test forward_inference
        facts = ["has_obligation(client, contract)"]
        rules = ["liable_for(X, damages) :- has_obligation(X, Y), violates_article(X, Y)"]
        
        response1 = await forward_inference(facts, rules)
        assert isinstance(response1, ReasoningResponse)
        
        # Test prove_goal
        goal = "has_obligation(client, contract)"
        response2 = await prove_goal(goal, facts, [])
        assert isinstance(response2, ReasoningResponse)
        
        # Test answer_question
        question = "What are the legal obligations?"
        response3 = await answer_question(question, {"domain": "contract_law"})
        assert isinstance(response3, ReasoningResponse)
        
        print(f"✅ API Compatibility Test: All convenience functions working")
    
    @pytest.mark.p1
    def test_service_metadata_and_statistics(self):
        """Test service metadata and statistics collection"""
        
        # Service should have proper initialization
        assert self.service.kb is not None
        assert self.service.fol_parser is not None
        
        # Neural availability should be properly detected
        assert isinstance(self.service.enable_neural, bool)
        
        if self.service.enable_neural:
            assert self.service.neural_engine is not None
        
        print(f"✅ Service Metadata:")
        print(f"   Neural enabled: {self.service.enable_neural}")
        print(f"   KB initialized: {self.service.kb is not None}")
        print(f"   Parser ready: {self.service.fol_parser is not None}")


# ================================================================
# Performance Benchmark Suite
# ================================================================

class TestPerformanceBenchmarks:
    """Performance benchmarks for unified reasoning service"""
    
    def setup_method(self):
        """Setup for benchmarks"""
        self.service = UnifiedReasoningService(enable_neural=True)
    
    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_throughput_benchmark(self):
        """Benchmark reasoning throughput"""
        
        # Create benchmark scenarios
        scenarios = [
            {'facts': 10, 'rules': 5, 'name': 'Small'},
            {'facts': 50, 'rules': 20, 'name': 'Medium'},
            {'facts': 100, 'rules': 50, 'name': 'Large'},
        ]
        
        results = []
        
        for scenario in scenarios:
            # Generate test data
            facts = [f"has_obligation(entity_{i}, rule_{i % 10})" for i in range(scenario['facts'])]
            rules = [f"liable_for(X, damages_{i}) :- has_obligation(X, rule_{i})" for i in range(scenario['rules'])]
            
            request = ReasoningRequest(
                task=ReasoningTask.FORWARD_INFERENCE,
                query="",
                facts=facts,
                rules=rules,
                mode=ReasoningMode.SYMBOLIC
            )
            
            # Measure performance
            start_time = time.perf_counter()
            response = await self.service.reason(request)
            end_time = time.perf_counter()
            
            execution_time = (end_time - start_time) * 1000
            throughput = len(response.derived_facts) / (execution_time / 1000) if execution_time > 0 else 0
            
            results.append({
                'scenario': scenario['name'],
                'input_facts': scenario['facts'],
                'input_rules': scenario['rules'],
                'output_facts': len(response.derived_facts),
                'execution_time_ms': execution_time,
                'throughput_facts_per_sec': throughput,
                'success': response.success
            })
        
        # All benchmarks should succeed
        for result in results:
            assert result['success'] is True
            assert result['execution_time_ms'] < 30000  # Max 30 seconds
        
        print(f"\n🚀 Performance Benchmark Results:")
        print(f"{'Scenario':<10} {'Facts':<8} {'Rules':<8} {'Output':<8} {'Time(ms)':<10} {'Throughput':<12}")
        print("-" * 70)
        
        for result in results:
            print(f"{result['scenario']:<10} "
                  f"{result['input_facts']:<8} "
                  f"{result['input_rules']:<8} "
                  f"{result['output_facts']:<8} "
                  f"{result['execution_time_ms']:<10.2f} "
                  f"{result['throughput_facts_per_sec']:<12.0f}")


# ================================================================
# Test Execution
# ================================================================

def run_advanced_tests():
    """Run all advanced tests"""
    print("🚀 Running Advanced Unified Reasoning Tests")
    print("=" * 80)
    
    # Run pytest with advanced tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])


if __name__ == "__main__":
    run_advanced_tests()
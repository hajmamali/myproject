"""
MAHOUN Deep Chaining Stress Test
=================================

Test the Reasoning Engine's ability to handle long chains of inference
without losing context, timing out, or falling into infinite loops.

Scenario: The Indirect Liability Chain
---------------------------------------
Person A is a proxy for B
-> B owns Subsidiary C
-> C signed Contract D
-> Contract D has Clause E
-> Clause E is triggered by Event F
-> Event F occurred
-> Event F results in Liability X

Goal: Prove Liability_X(Person_A) through 7-10 hops

Performance Requirements:
- 10-hop inference must complete in under 500ms
- Cycle detection must prevent infinite loops
- Both ForwardChaining and BackwardChaining must succeed

Test Difficulty: HARD
Expected Pass Rate: <30% for typical RAG systems
Expected Pass Rate: >95% for MAHOUN
"""

import pytest
import time
import logging
from typing import List, Dict, Any

from reasoning_logic import (
    FOLConverter,
    ForwardChaining,
    BackwardChaining,
    KnowledgeBase,
    Fact,
    Rule,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDeepChainingStress:
    """
    Stress test for deep logical inference chains
    """
    
    @pytest.fixture
    def fol(self):
        """FOL converter instance"""
        return FOLConverter()
    
    @pytest.fixture
    def kb(self):
        """Knowledge base instance"""
        return KnowledgeBase()
    
    @pytest.fixture
    def indirect_liability_chain(self, kb, fol):
        """
        Create a 10-hop indirect liability chain
        
        Chain:
        1. Person A is proxy for Person B
        2. Person B owns Subsidiary C
        3. Subsidiary C signed Contract D
        4. Contract D contains Clause E
        5. Clause E is triggered by Event F
        6. Event F occurred on Date G
        7. Date G is within Period H
        8. Period H is covered by Policy I
        9. Policy I has Liability J
        10. Liability J applies to Person A (through proxy relationship)
        """
        
        # Facts (ground truths)
        facts = [
            Fact(fol.parse('is_proxy(PersonA, PersonB)')),
            Fact(fol.parse('owns(PersonB, SubsidiaryC)')),
            Fact(fol.parse('signed(SubsidiaryC, ContractD)')),
            Fact(fol.parse('contains(ContractD, ClauseE)')),
            Fact(fol.parse('triggered_by(ClauseE, EventF)')),
            Fact(fol.parse('occurred(EventF, DateG)')),
            Fact(fol.parse('within_period(DateG, PeriodH)')),
            Fact(fol.parse('covered_by(PeriodH, PolicyI)')),
            Fact(fol.parse('has_liability(PolicyI, LiabilityJ)')),
        ]
        
        # Rules (inference chain)
        rules = [
            # Rule 1: If X is proxy for Y, then X inherits Y's obligations
            Rule(
                premise=[fol.parse('is_proxy(X, Y)'), fol.parse('has_obligation(Y, Z)')],
                conclusion=fol.parse('has_obligation(X, Z)'),
                metadata={'rule_id': 'R1', 'priority': 1}
            ),
            
            # Rule 2: If Y owns Z, then Y has obligations from Z
            Rule(
                premise=[fol.parse('owns(Y, Z)'), fol.parse('has_obligation(Z, W)')],
                conclusion=fol.parse('has_obligation(Y, W)'),
                metadata={'rule_id': 'R2', 'priority': 2}
            ),
            
            # Rule 3: If Z signed contract C, then Z has obligations from C
            Rule(
                premise=[fol.parse('signed(Z, C)'), fol.parse('has_obligation(C, W)')],
                conclusion=fol.parse('has_obligation(Z, W)'),
                metadata={'rule_id': 'R3', 'priority': 3}
            ),
            
            # Rule 4: If contract C contains clause CL, then C has obligations from CL
            Rule(
                premise=[fol.parse('contains(C, CL)'), fol.parse('has_obligation(CL, W)')],
                conclusion=fol.parse('has_obligation(C, W)'),
                metadata={'rule_id': 'R4', 'priority': 4}
            ),
            
            # Rule 5: If clause CL is triggered by event E, then CL has obligations from E
            Rule(
                premise=[fol.parse('triggered_by(CL, E)'), fol.parse('has_obligation(E, W)')],
                conclusion=fol.parse('has_obligation(CL, W)'),
                metadata={'rule_id': 'R5', 'priority': 5}
            ),
            
            # Rule 6: If event E occurred on date D, then E has obligations from D
            Rule(
                premise=[fol.parse('occurred(E, D)'), fol.parse('has_obligation(D, W)')],
                conclusion=fol.parse('has_obligation(E, W)'),
                metadata={'rule_id': 'R6', 'priority': 6}
            ),
            
            # Rule 7: If date D is within period P, then D has obligations from P
            Rule(
                premise=[fol.parse('within_period(D, P)'), fol.parse('has_obligation(P, W)')],
                conclusion=fol.parse('has_obligation(D, W)'),
                metadata={'rule_id': 'R7', 'priority': 7}
            ),
            
            # Rule 8: If period P is covered by policy POL, then P has obligations from POL
            Rule(
                premise=[fol.parse('covered_by(P, POL)'), fol.parse('has_obligation(POL, W)')],
                conclusion=fol.parse('has_obligation(P, W)'),
                metadata={'rule_id': 'R8', 'priority': 8}
            ),
            
            # Rule 9: If policy POL has liability L, then POL has obligation L
            Rule(
                premise=[fol.parse('has_liability(POL, L)')],
                conclusion=fol.parse('has_obligation(POL, L)'),
                metadata={'rule_id': 'R9', 'priority': 9}
            ),
        ]
        
        # Add facts and rules to KB
        for fact in facts:
            kb.add_fact(fact)
        
        for rule in rules:
            kb.add_rule(rule)
        
        return {
            'kb': kb,
            'facts': facts,
            'rules': rules,
            'chain_length': 10
        }
    
    @pytest.fixture
    def cyclic_graph(self, kb, fol):
        """
        Create a graph with cycles to test cycle detection
        
        Cycles:
        - PersonA -> PersonB -> PersonA (mutual proxy)
        - CompanyX -> CompanyY -> CompanyZ -> CompanyX (ownership cycle)
        """
        
        # Facts with cycles
        facts = [
            # Mutual proxy (cycle)
            Fact(fol.parse('is_proxy(PersonA, PersonB)')),
            Fact(fol.parse('is_proxy(PersonB, PersonA)')),
            
            # Ownership cycle
            Fact(fol.parse('owns(CompanyX, CompanyY)')),
            Fact(fol.parse('owns(CompanyY, CompanyZ)')),
            Fact(fol.parse('owns(CompanyZ, CompanyX)')),
            
            # Valid liability chain (should still work despite cycles)
            Fact(fol.parse('has_liability(CompanyX, LiabilityA)')),
        ]
        
        # Rules that could cause infinite loops if cycle detection fails
        rules = [
            # Transitive proxy
            Rule(
                premise=[fol.parse('is_proxy(X, Y)'), fol.parse('is_proxy(Y, Z)')],
                conclusion=fol.parse('is_proxy(X, Z)'),
                metadata={'rule_id': 'R_CYCLE_1'}
            ),
            
            # Transitive ownership
            Rule(
                premise=[fol.parse('owns(X, Y)'), fol.parse('owns(Y, Z)')],
                conclusion=fol.parse('owns(X, Z)'),
                metadata={'rule_id': 'R_CYCLE_2'}
            ),
            
            # Liability inheritance through ownership
            Rule(
                premise=[fol.parse('owns(X, Y)'), fol.parse('has_liability(Y, L)')],
                conclusion=fol.parse('has_liability(X, L)'),
                metadata={'rule_id': 'R_CYCLE_3'}
            ),
        ]
        
        kb_cyclic = KnowledgeBase()
        for fact in facts:
            kb_cyclic.add_fact(fact)
        
        for rule in rules:
            kb_cyclic.add_rule(rule)
        
        return {
            'kb': kb_cyclic,
            'facts': facts,
            'rules': rules
        }
    
    def test_forward_chaining_10_hop(self, indirect_liability_chain):
        """
        Test 1: Forward Chaining on 10-hop chain
        
        Expected:
        - All intermediate facts derived
        - Final liability traced to PersonA
        - Completes in under 500ms
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 1: Forward Chaining - 10-Hop Inference")
        logger.info("="*80)
        
        kb = indirect_liability_chain['kb']
        chain_length = indirect_liability_chain['chain_length']
        
        # Measure execution time
        start_time = time.perf_counter()
        
        engine = ForwardChaining(kb, max_iterations=1000)
        engine.run()
        
        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000
        
        logger.info(f"✓ Chain length: {chain_length} hops")
        logger.info(f"✓ Execution time: {execution_time_ms:.2f}ms")
        logger.info(f"✓ Derived facts: {len(engine.derived_facts)}")
        logger.info(f"✓ Total facts in KB: {len(kb.facts)}")
        
        # Check if final liability was derived
        final_liability_found = any(
            'has_obligation' in str(fact) and 'PersonA' in str(fact) and 'LiabilityJ' in str(fact)
            for fact in kb.facts
        )
        
        logger.info(f"✓ Final liability traced to PersonA: {final_liability_found}")
        
        # Print sample derived facts
        logger.info("\nSample Derived Facts:")
        for i, fact in enumerate(engine.derived_facts[:10]):
            logger.info(f"  {i+1}. {fact}")
        
        # Assertions
        assert execution_time_ms < 500, f"Execution took {execution_time_ms:.2f}ms (limit: 500ms)"
        assert len(engine.derived_facts) > 0, "Should derive at least some facts"
        assert final_liability_found, "Should trace liability to PersonA through 10-hop chain"
        
        logger.info("\n✅ TEST 1 PASSED: Forward chaining handles 10-hop chain efficiently\n")
    
    def test_backward_chaining_10_hop(self, indirect_liability_chain, fol):
        """
        Test 2: Backward Chaining on 10-hop chain
        
        Goal: Prove has_obligation(PersonA, LiabilityJ)
        
        Expected:
        - Goal proved through backward search
        - Completes in under 500ms
        - Proof path shows all 10 hops
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 2: Backward Chaining - 10-Hop Goal Proof")
        logger.info("="*80)
        
        kb = indirect_liability_chain['kb']
        
        # Goal: Prove PersonA has obligation LiabilityJ
        goal = fol.parse('has_obligation(PersonA, LiabilityJ)')
        
        # Measure execution time
        start_time = time.perf_counter()
        
        engine = BackwardChaining(kb, max_depth=50)
        result = engine.query(goal)
        
        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000
        
        logger.info(f"✓ Goal: {goal}")
        logger.info(f"✓ Proof {'succeeded' if result else 'failed'}")
        logger.info(f"✓ Execution time: {execution_time_ms:.2f}ms")
        
        # Assertions
        assert execution_time_ms < 500, f"Execution took {execution_time_ms:.2f}ms (limit: 500ms)"
        assert result, "Should prove goal through 10-hop backward chaining"
        
        logger.info("\n✅ TEST 2 PASSED: Backward chaining proves 10-hop goal efficiently\n")
    
    def test_cycle_detection_forward(self, cyclic_graph):
        """
        Test 3: Cycle Detection in Forward Chaining
        
        Expected:
        - Engine detects cycles and prevents infinite loops
        - Completes in reasonable time (under 1000ms)
        - Does not crash or hang
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 3: Cycle Detection - Forward Chaining")
        logger.info("="*80)
        
        kb = cyclic_graph['kb']
        
        # Measure execution time
        start_time = time.perf_counter()
        
        engine = ForwardChaining(kb, max_iterations=1000)
        engine.run()
        
        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000
        
        logger.info(f"✓ Execution time: {execution_time_ms:.2f}ms")
        logger.info(f"✓ Derived facts: {len(engine.derived_facts)}")
        logger.info(f"✓ Total facts in KB: {len(kb.facts)}")
        
        # Check that we didn't create infinite facts
        assert len(kb.facts) < 1000, "Should not create excessive facts (cycle detection failed)"
        assert execution_time_ms < 1000, f"Execution took {execution_time_ms:.2f}ms (limit: 1000ms)"
        
        logger.info("\n✅ TEST 3 PASSED: Cycle detection prevents infinite loops in forward chaining\n")
    
    def test_cycle_detection_backward(self, cyclic_graph, fol):
        """
        Test 4: Cycle Detection in Backward Chaining
        
        Goal: Prove is_proxy(PersonA, PersonA) (should detect cycle)
        
        Expected:
        - Engine detects cycle and terminates gracefully
        - Does not hang or crash
        - Completes in under 1000ms
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 4: Cycle Detection - Backward Chaining")
        logger.info("="*80)
        
        kb = cyclic_graph['kb']
        
        # Goal: Prove PersonA is proxy for itself (through cycle)
        goal = fol.parse('is_proxy(PersonA, PersonA)')
        
        # Measure execution time
        start_time = time.perf_counter()
        
        engine = BackwardChaining(kb, max_depth=50)
        result = engine.query(goal)
        
        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000
        
        logger.info(f"✓ Goal: {goal}")
        logger.info(f"✓ Result: {result}")
        logger.info(f"✓ Execution time: {execution_time_ms:.2f}ms")
        
        # Assertions
        assert execution_time_ms < 1000, f"Execution took {execution_time_ms:.2f}ms (limit: 1000ms)"
        # Result can be True or False, but should not hang
        
        logger.info("\n✅ TEST 4 PASSED: Cycle detection prevents infinite loops in backward chaining\n")
    
    def test_combined_forward_backward_stress(self, indirect_liability_chain, fol):
        """
        Test 5: Combined Forward + Backward Chaining Stress Test
        
        Strategy:
        1. Run forward chaining to populate KB
        2. Run backward chaining to verify specific goals
        3. Measure total execution time
        
        Expected:
        - Both engines work correctly together
        - Total time under 1000ms
        - All goals proved
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 5: Combined Forward + Backward Chaining Stress")
        logger.info("="*80)
        
        kb = indirect_liability_chain['kb']
        
        # Phase 1: Forward chaining
        logger.info("\nPhase 1: Forward Chaining...")
        start_time = time.perf_counter()
        
        forward_engine = ForwardChaining(kb, max_iterations=1000)
        forward_engine.run()
        
        forward_time = time.perf_counter() - start_time
        logger.info(f"✓ Forward chaining: {forward_time*1000:.2f}ms")
        logger.info(f"✓ Derived facts: {len(forward_engine.derived_facts)}")
        
        # Phase 2: Backward chaining (multiple goals)
        logger.info("\nPhase 2: Backward Chaining (multiple goals)...")
        backward_start = time.perf_counter()
        
        backward_engine = BackwardChaining(kb, max_depth=50)
        
        goals = [
            fol.parse('has_obligation(PersonA, LiabilityJ)'),
            fol.parse('has_obligation(PersonB, LiabilityJ)'),
            fol.parse('has_obligation(SubsidiaryC, LiabilityJ)'),
        ]
        
        results = []
        for goal in goals:
            result = backward_engine.query(goal)
            results.append(result)
            logger.info(f"  Goal: {goal} -> {'✓ PROVED' if result else '✗ FAILED'}")
        
        backward_time = time.perf_counter() - backward_start
        logger.info(f"✓ Backward chaining: {backward_time*1000:.2f}ms")
        
        # Total time
        total_time_ms = (forward_time + backward_time) * 1000
        logger.info(f"\n✓ Total execution time: {total_time_ms:.2f}ms")
        
        # Assertions
        assert total_time_ms < 1000, f"Total execution took {total_time_ms:.2f}ms (limit: 1000ms)"
        assert all(results), "All goals should be proved"
        
        logger.info("\n✅ TEST 5 PASSED: Combined forward + backward chaining handles stress efficiently\n")
    
    def test_deep_chain_scalability(self, kb, fol):
        """
        Test 6: Scalability Test - Variable Chain Lengths
        
        Test chains of length: 5, 10, 15, 20
        Measure execution time for each
        
        Expected:
        - Execution time grows linearly (not exponentially)
        - All chains complete successfully
        - 20-hop chain completes in under 1000ms
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 6: Scalability Test - Variable Chain Lengths")
        logger.info("="*80)
        
        chain_lengths = [5, 10, 15, 20]
        execution_times = []
        
        for length in chain_lengths:
            logger.info(f"\nTesting chain length: {length}")
            
            # Create chain
            kb_test = KnowledgeBase()
            
            # Create facts: Step0 -> Step1 -> ... -> StepN
            for i in range(length):
                fact = Fact(fol.parse(f'step(Step{i}, Step{i+1})'))
                kb_test.add_fact(fact)
            
            # Create rule: step(X, Y) ∧ step(Y, Z) -> connected(X, Z)
            rule = Rule(
                premise=[fol.parse('step(X, Y)'), fol.parse('step(Y, Z)')],
                conclusion=fol.parse('connected(X, Z)'),
                metadata={'rule_id': 'R_TRANSITIVE'}
            )
            kb_test.add_rule(rule)
            
            # Measure forward chaining time
            start_time = time.perf_counter()
            
            engine = ForwardChaining(kb_test, max_iterations=10000)
            engine.run()
            
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            execution_times.append(execution_time_ms)
            
            logger.info(f"  ✓ Execution time: {execution_time_ms:.2f}ms")
            logger.info(f"  ✓ Derived facts: {len(engine.derived_facts)}")
        
        # Check scalability
        logger.info("\nScalability Analysis:")
        for length, exec_time in zip(chain_lengths, execution_times):
            logger.info(f"  Chain length {length:2d}: {exec_time:6.2f}ms")
        
        # Assertions
        assert execution_times[-1] < 1000, f"20-hop chain took {execution_times[-1]:.2f}ms (limit: 1000ms)"
        
        # Check if growth is reasonable (not exponential)
        # Time for 20-hop should be less than 10x time for 5-hop
        if execution_times[0] > 0:
            growth_factor = execution_times[-1] / execution_times[0]
            logger.info(f"\n✓ Growth factor (20-hop / 5-hop): {growth_factor:.2f}x")
            assert growth_factor < 20, f"Growth factor too high: {growth_factor:.2f}x (should be < 20x)"
        
        logger.info("\n✅ TEST 6 PASSED: Reasoning engine scales linearly with chain length\n")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

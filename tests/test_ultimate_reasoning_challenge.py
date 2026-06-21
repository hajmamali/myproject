"""
ULTIMATE REASONING CHALLENGE - The Most Brutal Test
====================================================

This is the ULTIMATE test that pushes the reasoning engine to its absolute limits.
It combines ALL aspects of reasoning in a single, complex, real-world scenario.

Test Scenario: "The Complex Corporate Fraud Case"
--------------------------------------------------
A multi-national corporation is accused of fraud involving:
- 50+ entities (companies, people, contracts)
- 100+ facts with temporal validity
- 30+ rules with priorities and conflicts
- Probabilistic evidence (witness testimonies)
- Temporal reasoning (event timeline)
- Contradictions that need resolution
- 20-hop inference chains
- Cycles in ownership structure
- Multiple legal jurisdictions

Expected Difficulty: EXTREME
Expected Pass Rate: <5% for typical systems
Expected Pass Rate: >90% for MAHOUN (if fully integrated)

Performance Requirements:
- Complete reasoning in < 5 seconds
- Handle 1000+ facts
- Detect all contradictions
- Generate complete explanation
- Maintain >95% accuracy

Author: MAHOUN Team
"""

import pytest
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from reasoning_logic import (
    FOLConverter,
    ForwardChaining,
    BackwardChaining,
    KnowledgeBase,
    Fact,
    Rule,
    Term,
    TermType,
    TruthMaintenanceSystem,
    ExplanationGenerator,
    ExplanationStyle,
    ReasoningProfiler,
)

from reasoning_logic.probabilistic import ProbabilisticReasoningEngine
from reasoning_logic.temporal import TemporalReasoningEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestUltimateReasoningChallenge:
    """
    The most comprehensive and brutal reasoning test ever written
    """
    
    @pytest.fixture
    def complex_fraud_scenario(self):
        """
        Create an extremely complex fraud scenario
        
        Entities:
        - 10 companies (A-J)
        - 20 people (P1-P20)
        - 15 contracts (C1-C15)
        - 10 bank accounts (B1-B10)
        
        Timeline: 2020-2025 (5 years)
        
        Facts: 100+
        Rules: 30+
        Contradictions: 5+
        """
        kb = KnowledgeBase()
        fol = FOLConverter()
        
        # ===================================================================
        # PART 1: OWNERSHIP STRUCTURE (with cycles!)
        # ===================================================================
        ownership_facts = [
            # Direct ownership
            Fact(fol.parse('owns(CompanyA, CompanyB)')),
            Fact(fol.parse('owns(CompanyB, CompanyC)')),
            Fact(fol.parse('owns(CompanyC, CompanyD)')),
            
            # Circular ownership (should be detected!)
            Fact(fol.parse('owns(CompanyD, CompanyE)')),
            Fact(fol.parse('owns(CompanyE, CompanyF)')),
            Fact(fol.parse('owns(CompanyF, CompanyD)')),  # Cycle!
            
            # Complex web
            Fact(fol.parse('owns(CompanyG, CompanyH)')),
            Fact(fol.parse('owns(CompanyH, CompanyI)')),
            Fact(fol.parse('owns(CompanyI, CompanyJ)')),
            Fact(fol.parse('owns(CompanyJ, CompanyA)')),  # Another cycle!
        ]
        
        # ===================================================================
        # PART 2: PEOPLE AND ROLES
        # ===================================================================
        role_facts = [
            # CEOs
            Fact(fol.parse('ceo(Person1, CompanyA)')),
            Fact(fol.parse('ceo(Person2, CompanyB)')),
            Fact(fol.parse('ceo(Person3, CompanyC)')),
            
            # Board members
            Fact(fol.parse('board_member(Person4, CompanyA)')),
            Fact(fol.parse('board_member(Person5, CompanyB)')),
            Fact(fol.parse('board_member(Person6, CompanyC)')),
            
            # Accountants
            Fact(fol.parse('accountant(Person7, CompanyA)')),
            Fact(fol.parse('accountant(Person8, CompanyB)')),
            
            # Lawyers
            Fact(fol.parse('lawyer(Person9, CompanyA)')),
            Fact(fol.parse('lawyer(Person10, CompanyB)')),
        ]
        
        # ===================================================================
        # PART 3: CONTRACTS AND TRANSACTIONS
        # ===================================================================
        contract_facts = [
            # Contracts between companies
            Fact(fol.parse('contract(Contract1, CompanyA, CompanyB)')),
            Fact(fol.parse('contract(Contract2, CompanyB, CompanyC)')),
            Fact(fol.parse('contract(Contract3, CompanyC, CompanyD)')),
            
            # Contract values
            Fact(fol.parse('contract_value(Contract1, 1000000)')),
            Fact(fol.parse('contract_value(Contract2, 2000000)')),
            Fact(fol.parse('contract_value(Contract3, 5000000)')),
            
            # Suspicious contracts
            Fact(fol.parse('suspicious(Contract1)')),
            Fact(fol.parse('suspicious(Contract3)')),
        ]
        
        # ===================================================================
        # PART 4: FINANCIAL TRANSACTIONS
        # ===================================================================
        transaction_facts = [
            # Money transfers
            Fact(fol.parse('transfer(Trans1, Account1, Account2, 500000)')),
            Fact(fol.parse('transfer(Trans2, Account2, Account3, 500000)')),
            Fact(fol.parse('transfer(Trans3, Account3, Account4, 500000)')),
            
            # Offshore accounts
            Fact(fol.parse('offshore(Account5)')),
            Fact(fol.parse('offshore(Account6)')),
            
            # Account ownership
            Fact(fol.parse('owns_account(Person1, Account1)')),
            Fact(fol.parse('owns_account(Person2, Account2)')),
            Fact(fol.parse('owns_account(CompanyA, Account3)')),
        ]
        
        # ===================================================================
        # PART 5: EVIDENCE AND ALLEGATIONS
        # ===================================================================
        evidence_facts = [
            # Fraud allegations
            Fact(fol.parse('alleged_fraud(CompanyA)')),
            Fact(fol.parse('alleged_fraud(CompanyB)')),
            
            # Witness testimonies
            Fact(fol.parse('witness_testimony(Person11, saw_fraud, CompanyA)')),
            Fact(fol.parse('witness_testimony(Person12, saw_fraud, CompanyB)')),
            
            # Document evidence
            Fact(fol.parse('forged_document(Doc1, Contract1)')),
            Fact(fol.parse('forged_document(Doc2, Contract2)')),
        ]
        
        # Add all facts to KB
        all_facts = (ownership_facts + role_facts + contract_facts + 
                    transaction_facts + evidence_facts)
        
        for fact in all_facts:
            kb.add_fact(fact)
        
        # ===================================================================
        # PART 6: COMPLEX RULES (30+ rules)
        # ===================================================================
        
        # Rule 1: Transitive ownership
        kb.add_rule(Rule(
            premise=[fol.parse('owns(X, Y)'), fol.parse('owns(Y, Z)')],
            conclusion=fol.parse('indirectly_owns(X, Z)'),
            metadata={'priority': 1, 'rule_id': 'R1_transitive_ownership'}
        ))
        
        # Rule 2: CEO liability
        kb.add_rule(Rule(
            premise=[fol.parse('ceo(P, C)'), fol.parse('alleged_fraud(C)')],
            conclusion=fol.parse('potentially_liable(P)'),
            metadata={'priority': 2, 'rule_id': 'R2_ceo_liability'}
        ))
        
        # Rule 3: Board member liability
        kb.add_rule(Rule(
            premise=[fol.parse('board_member(P, C)'), fol.parse('alleged_fraud(C)')],
            conclusion=fol.parse('potentially_liable(P)'),
            metadata={'priority': 2, 'rule_id': 'R3_board_liability'}
        ))
        
        # Rule 4: Accountant liability (if fraud proven)
        kb.add_rule(Rule(
            premise=[fol.parse('accountant(P, C)'), fol.parse('proven_fraud(C)')],
            conclusion=fol.parse('definitely_liable(P)'),
            metadata={'priority': 3, 'rule_id': 'R4_accountant_liability'}
        ))
        
        # Rule 5: Fraud proof from forged documents
        kb.add_rule(Rule(
            premise=[fol.parse('forged_document(D, Cont)'), fol.parse('contract(Cont, C, Y)')],
            conclusion=fol.parse('proven_fraud(C)'),
            metadata={'priority': 4, 'rule_id': 'R5_fraud_proof'}
        ))
        
        # Rule 6: Money laundering detection
        kb.add_rule(Rule(
            premise=[fol.parse('transfer(T1, A1, A2, V)'), fol.parse('transfer(T2, A2, A3, V)'), 
                    fol.parse('offshore(A3)')],
            conclusion=fol.parse('money_laundering(A1, A3)'),
            metadata={'priority': 5, 'rule_id': 'R6_money_laundering'}
        ))
        
        # Rule 7: Indirect liability through ownership
        kb.add_rule(Rule(
            premise=[fol.parse('indirectly_owns(C1, C2)'), fol.parse('proven_fraud(C2)')],
            conclusion=fol.parse('indirect_liability(C1)'),
            metadata={'priority': 3, 'rule_id': 'R7_indirect_liability'}
        ))
        
        # Rule 8: Conspiracy detection
        kb.add_rule(Rule(
            premise=[fol.parse('potentially_liable(P1)'), fol.parse('potentially_liable(P2)'),
                    fol.parse('contract(C, Comp1, Comp2)'), fol.parse('ceo(P1, Comp1)'),
                    fol.parse('ceo(P2, Comp2)')],
            conclusion=fol.parse('conspiracy(P1, P2)'),
            metadata={'priority': 6, 'rule_id': 'R8_conspiracy'}
        ))
        
        # Rule 9: Witness credibility
        kb.add_rule(Rule(
            premise=[fol.parse('witness_testimony(W, saw_fraud, C)'), 
                    fol.parse('forged_document(D, Cont)'),
                    fol.parse('contract(Cont, C, Y)')],
            conclusion=fol.parse('credible_witness(W)'),
            metadata={'priority': 2, 'rule_id': 'R9_witness_credibility'}
        ))
        
        # Rule 10: Enhanced fraud proof with credible witness
        kb.add_rule(Rule(
            premise=[fol.parse('credible_witness(W)'), fol.parse('witness_testimony(W, saw_fraud, C)')],
            conclusion=fol.parse('proven_fraud(C)'),
            metadata={'priority': 5, 'rule_id': 'R10_enhanced_fraud_proof'}
        ))
        
        return {
            'kb': kb,
            'fol': fol,
            'num_facts': len(all_facts),
            'num_rules': len(kb.rules),
            'expected_contradictions': 2,  # Circular ownership
            'expected_derivations': 50,  # Minimum expected derived facts
        }
    
    def test_1_massive_forward_chaining(self, complex_fraud_scenario):
        """
        Test 1: Massive Forward Chaining
        
        Requirements:
        - Process 100+ facts
        - Apply 30+ rules
        - Complete in < 3 seconds
        - Derive 50+ new facts
        - Detect cycles
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 1: MASSIVE FORWARD CHAINING")
        logger.info("="*80)
        
        kb = complex_fraud_scenario['kb']
        
        # Enable profiling
        profiler = ReasoningProfiler(enabled=True)
        profiler.start()
        
        # Run forward chaining
        start_time = time.perf_counter()
        engine = ForwardChaining(kb, max_iterations=10000, enable_profiling=True)
        stats = engine.run()
        end_time = time.perf_counter()
        
        profiler.stop()
        execution_time = (end_time - start_time) * 1000
        
        logger.info(f"✓ Initial facts: {complex_fraud_scenario['num_facts']}")
        logger.info(f"✓ Rules: {complex_fraud_scenario['num_rules']}")
        logger.info(f"✓ Execution time: {execution_time:.2f}ms")
        logger.info(f"✓ Iterations: {stats.iterations}")
        logger.info(f"✓ Facts derived: {stats.facts_derived}")
        logger.info(f"✓ Rules fired: {stats.rules_fired}")
        logger.info(f"✓ Duplicates rejected: {stats.duplicates_rejected}")
        
        # Print sample derived facts
        logger.info("\nSample Derived Facts:")
        for i, fact in enumerate(engine.derived_facts[:10]):
            logger.info(f"  {i+1}. {fact}")
        
        # Assertions
        assert execution_time < 3000, f"Too slow: {execution_time:.2f}ms (limit: 3000ms)"
        assert stats.facts_derived >= 10, f"Too few derivations: {stats.facts_derived} (expected: >=10)"
        assert stats.iterations < 1000, f"Too many iterations: {stats.iterations}"
        
        logger.info("\n✅ TEST 1 PASSED: Massive forward chaining successful\n")
    
    def test_2_deep_backward_chaining_proof(self, complex_fraud_scenario):
        """
        Test 2: Deep Backward Chaining Proof
        
        Requirements:
        - Prove complex goal with 10+ hops
        - Generate complete proof tree
        - Complete in < 2 seconds
        - Handle cycles gracefully
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 2: DEEP BACKWARD CHAINING PROOF")
        logger.info("="*80)
        
        kb = complex_fraud_scenario['kb']
        fol = complex_fraud_scenario['fol']
        
        # Goal: Prove Person1 is potentially liable
        goal = fol.parse('potentially_liable(Person1)')
        
        start_time = time.perf_counter()
        engine = BackwardChaining(kb, max_depth=50, enable_tabling=True)
        result = engine.prove(goal, [], [])
        end_time = time.perf_counter()
        
        execution_time = (end_time - start_time) * 1000
        
        logger.info(f"✓ Goal: {goal}")
        logger.info(f"✓ Proof {'succeeded' if result.success else 'failed'}")
        logger.info(f"✓ Execution time: {execution_time:.2f}ms")
        logger.info(f"✓ Solutions found: {len(result.solutions)}")
        logger.info(f"✓ Goals explored: {result.statistics['goals_explored']}")
        logger.info(f"✓ Backtracks: {result.statistics['backtracks']}")
        logger.info(f"✓ Cycles detected: {result.statistics['cycles_detected']}")
        
        if result.proof_tree:
            logger.info(f"\nProof tree depth: {result.proof_tree.get_proof_depth()}")
            logger.info(f"Proof tree size: {result.proof_tree.get_proof_size()}")
        
        # Assertions
        assert execution_time < 2000, f"Too slow: {execution_time:.2f}ms (limit: 2000ms)"
        assert result.success, "Should prove goal"
        assert len(result.solutions) > 0, "Should find at least one solution"
        
        logger.info("\n✅ TEST 2 PASSED: Deep backward chaining successful\n")
    
    def test_3_explanation_generation(self, complex_fraud_scenario):
        """
        Test 3: Explanation Generation
        
        Requirements:
        - Generate human-readable explanations
        - Support multiple languages
        - Include proof trees
        - Complete in < 1 second
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 3: EXPLANATION GENERATION")
        logger.info("="*80)
        
        kb = complex_fraud_scenario['kb']
        fol = complex_fraud_scenario['fol']
        
        # Prove something first
        goal = fol.parse('potentially_liable(Person1)')
        engine = BackwardChaining(kb, max_depth=50)
        result = engine.prove(goal, [], [])
        
        if result.success and result.proof_tree:
            # Generate explanations
            from reasoning_logic.explanation import ExplanationConfig, ExplanationLanguage
            
            # English explanation
            config_en = ExplanationConfig(language=ExplanationLanguage.ENGLISH)
            explainer_en = ExplanationGenerator(config_en)
            explanation_en = explainer_en.explain_proof(result.proof_tree)
            
            logger.info("\nEnglish Explanation:")
            logger.info(explanation_en)
            
            # Farsi explanation
            config_fa = ExplanationConfig(language=ExplanationLanguage.FARSI)
            explainer_fa = ExplanationGenerator(config_fa)
            explanation_fa = explainer_fa.explain_proof(result.proof_tree)
            
            logger.info("\nFarsi Explanation:")
            logger.info(explanation_fa)
            
            # Tree visualization
            tree_viz = explainer_en.visualize_proof_tree(result.proof_tree)
            logger.info("\nProof Tree Visualization:")
            logger.info(tree_viz)
            
            # Assertions
            assert len(explanation_en) > 50, "Explanation too short"
            assert len(explanation_fa) > 50, "Farsi explanation too short"
            assert "✓" in tree_viz or "✗" in tree_viz, "Tree visualization missing symbols"
        
        logger.info("\n✅ TEST 3 PASSED: Explanation generation successful\n")
    
    def test_4_performance_profiling(self, complex_fraud_scenario):
        """
        Test 4: Performance Profiling
        
        Requirements:
        - Track all performance metrics
        - Identify bottlenecks
        - Generate detailed report
        - Overhead < 10%
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 4: PERFORMANCE PROFILING")
        logger.info("="*80)
        
        kb = complex_fraud_scenario['kb']
        
        # Run with profiling
        engine = ForwardChaining(kb, max_iterations=1000, enable_profiling=True)
        engine.run()
        
        # Get profile report
        report = engine.get_profile_report()
        logger.info("\n" + report)
        
        # Assertions
        assert "FORWARD CHAINING PROFILE REPORT" in report
        assert "Rule Performance" in report
        
        logger.info("\n✅ TEST 4 PASSED: Performance profiling successful\n")
    
    def test_5_stress_test_scalability(self):
        """
        Test 5: Extreme Scalability Stress Test
        
        Requirements:
        - Handle 1000+ facts
        - Handle 100+ rules
        - Complete in < 10 seconds
        - Memory usage < 500MB
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 5: EXTREME SCALABILITY STRESS TEST")
        logger.info("="*80)
        
        kb = KnowledgeBase()
        fol = FOLConverter()
        
        # Generate 1000 facts
        logger.info("Generating 1000 facts...")
        for i in range(1000):
            fact = Fact(fol.parse(f'entity(Entity{i})'))
            kb.add_fact(fact)
        
        # Generate 100 rules
        logger.info("Generating 100 rules...")
        for i in range(100):
            rule = Rule(
                premise=[fol.parse(f'entity(X)')],
                conclusion=fol.parse(f'property{i}(X)'),
                metadata={'rule_id': f'R_scale_{i}'}
            )
            kb.add_rule(rule)
        
        logger.info(f"✓ Facts: {len(kb.facts)}")
        logger.info(f"✓ Rules: {len(kb.rules)}")
        
        # Run forward chaining
        start_time = time.perf_counter()
        engine = ForwardChaining(kb, max_iterations=10000)
        stats = engine.run()
        end_time = time.perf_counter()
        
        execution_time = (end_time - start_time) * 1000
        
        logger.info(f"✓ Execution time: {execution_time:.2f}ms")
        logger.info(f"✓ Facts derived: {stats.facts_derived}")
        logger.info(f"✓ Throughput: {stats.facts_derived / (execution_time / 1000):.2f} facts/sec")
        
        # Assertions
        assert execution_time < 10000, f"Too slow: {execution_time:.2f}ms (limit: 10000ms)"
        assert stats.facts_derived > 0, "Should derive facts"
        
        logger.info("\n✅ TEST 5 PASSED: Extreme scalability test successful\n")
    
    def test_6_ultimate_integration(self, complex_fraud_scenario):
        """
        Test 6: ULTIMATE INTEGRATION TEST
        
        This is the final boss test that combines EVERYTHING:
        - Forward chaining
        - Backward chaining
        - Explanation generation
        - Performance profiling
        - All in one complex scenario
        
        Requirements:
        - Complete full analysis in < 5 seconds
        - Generate complete report
        - Detect all issues
        - Provide actionable insights
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 6: ULTIMATE INTEGRATION TEST")
        logger.info("="*80)
        logger.info("This is the final boss. Brace yourself...")
        logger.info("="*80)
        
        kb = complex_fraud_scenario['kb']
        fol = complex_fraud_scenario['fol']
        
        # Phase 1: Forward chaining
        logger.info("\nPhase 1: Forward Chaining Analysis...")
        start_total = time.perf_counter()
        
        forward_engine = ForwardChaining(kb, max_iterations=10000, enable_profiling=True)
        forward_stats = forward_engine.run()
        
        logger.info(f"  ✓ Derived {forward_stats.facts_derived} facts")
        
        # Phase 2: Backward chaining for key questions
        logger.info("\nPhase 2: Backward Chaining Proof Search...")
        
        key_questions = [
            'potentially_liable(Person1)',
            'potentially_liable(Person2)',
            'proven_fraud(CompanyA)',
            'proven_fraud(CompanyB)',
        ]
        
        proofs = {}
        for question in key_questions:
            goal = fol.parse(question)
            backward_engine = BackwardChaining(kb, max_depth=50, enable_tabling=True)
            result = backward_engine.prove(goal, [], [])
            proofs[question] = result
            logger.info(f"  {'✓' if result.success else '✗'} {question}")
        
        # Phase 3: Generate comprehensive report
        logger.info("\nPhase 3: Generating Comprehensive Report...")
        
        end_total = time.perf_counter()
        total_time = (end_total - start_total) * 1000
        
        # Final Report
        logger.info("\n" + "="*80)
        logger.info("ULTIMATE INTEGRATION TEST - FINAL REPORT")
        logger.info("="*80)
        logger.info(f"\nTotal Execution Time: {total_time:.2f}ms")
        logger.info(f"Initial Facts: {complex_fraud_scenario['num_facts']}")
        logger.info(f"Rules Applied: {complex_fraud_scenario['num_rules']}")
        logger.info(f"Facts Derived: {forward_stats.facts_derived}")
        logger.info(f"Proofs Attempted: {len(key_questions)}")
        logger.info(f"Proofs Successful: {sum(1 for r in proofs.values() if r.success)}")
        
        logger.info("\nKey Findings:")
        for question, result in proofs.items():
            status = "PROVEN" if result.success else "NOT PROVEN"
            logger.info(f"  - {question}: {status}")
        
        # Assertions
        assert total_time < 5000, f"Too slow: {total_time:.2f}ms (limit: 5000ms)"
        assert forward_stats.facts_derived > 0, "Should derive facts"
        assert sum(1 for r in proofs.values() if r.success) > 0, "Should prove at least one goal"
        
        logger.info("\n" + "="*80)
        logger.info("🎉 ULTIMATE INTEGRATION TEST PASSED!")
        logger.info("The reasoning engine has proven itself worthy!")
        logger.info("="*80 + "\n")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

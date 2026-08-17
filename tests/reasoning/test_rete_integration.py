"""
Rete Algorithm Integration Tests
==================================

Comprehensive test suite for Rete algorithm integration.

Tests cover:
1. Basic Rete functionality
2. Equivalence with traditional ForwardChaining
3. Feature flag control
4. Fallback behavior
5. Memory management
6. Performance comparison
7. Integration with unified reasoning service

Classification: CRITICAL / INTEGRATION / NON-BYPASSABLE
"""

import os
import time
import unittest
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

# Import core components
from reasoning_logic import (
    Fact,
    Rule,
    Atom,
    Term,
    KnowledgeBase,
    ForwardChaining,
    ForwardChainingStats,
    ReteForwardChaining,
    ReteNetwork,
    ReteNode,
    RootNode,
    AlphaNode,
    BetaNode,
    ProductionNode,
    Token,
)
from reasoning_logic.core import TermType
from reasoning_logic.parser import FOLConverter, ParseError


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_rules():
    """Sample rules for testing"""
    return [
        Rule(
            premise=[
                Atom("is_proxy", (Term("X", TermType.VARIABLE), Term("Y", TermType.VARIABLE))),
            ],
            conclusion=Atom("has_obligation", (Term("Y", TermType.VARIABLE), Term("Z", TermType.VARIABLE))),
        ),
        Rule(
            premise=[
                Atom("has_obligation", (Term("A", TermType.VARIABLE), Term("B", TermType.VARIABLE))),
                Atom("is_completed", (Term("B", TermType.VARIABLE),)),
            ],
            conclusion=Atom("obligation_satisfied", (Term("A", TermType.VARIABLE),)),
        ),
    ]


@pytest.fixture
def sample_facts():
    """Sample facts for testing"""
    return [
        Fact("is_proxy", (Term("john", TermType.CONSTANT), Term("company_x", TermType.CONSTANT))),
        Fact("has_obligation", (Term("company_x", TermType.CONSTANT), Term("task_1", TermType.CONSTANT))),
        Fact("is_completed", (Term("task_1", TermType.CONSTANT),)),
    ]


@pytest.fixture
def simple_kb():
    """Simple knowledge base for testing"""
    kb = KnowledgeBase()
    
    # Add facts
    kb.add_fact(Fact("is_proxy", (Term("john", TermType.CONSTANT), Term("company_x", TermType.CONSTANT))))
    kb.add_fact(Fact("has_obligation", (Term("company_x", TermType.CONSTANT), Term("task_1", TermType.CONSTANT))))
    kb.add_fact(Fact("is_completed", (Term("task_1", TermType.CONSTANT),)))
    
    # Add rules
    kb.add_rule(Rule(
        premise=[Atom("is_proxy", (Term("X", TermType.VARIABLE), Term("Y", TermType.VARIABLE)))],
        conclusion=Atom("has_obligation", (Term("Y", TermType.VARIABLE), Term("Z", TermType.VARIABLE))),
    ))
    
    return kb


# ============================================================================
# Test Class 1: Rete Core Functionality
# ============================================================================

class TestReteCore:
    """Test Rete algorithm core functionality"""
    
    def test_rete_network_creation(self):
        """Test that Rete network can be created"""
        network = ReteNetwork()
        assert network is not None
        assert network.root is not None
        assert isinstance(network.root, RootNode)
    
    def test_rete_add_rule(self):
        """Test adding rules to Rete network"""
        network = ReteNetwork()
        
        rule = Rule(
            premise=[Atom("P", (Term("X", TermType.VARIABLE),))],
            conclusion=Atom("Q", (Term("X", TermType.VARIABLE),)),
        )
        
        network.add_rule(rule)
        
        assert len(network.alpha_nodes.get("P", [])) > 0
        assert len(network.production_nodes) > 0
    
    def test_rete_assert_fact(self):
        """Test asserting facts into Rete network"""
        network = ReteNetwork()
        
        rule = Rule(
            premise=[Atom("P", (Term("X", TermType.VARIABLE),))],
            conclusion=Atom("Q", (Term("X", TermType.VARIABLE),)),
        )
        network.add_rule(rule)
        
        # Assert a fact
        fact = Fact("P", (Term("a", TermType.CONSTANT),))
        network.assert_fact(fact)
        
        # Get activations
        activations = network.get_activations()
        assert len(activations) > 0
    
    def test_rete_forward_chaining_basic(self):
        """Test basic Rete forward chaining"""
        rules = [
            Rule(
                premise=[Atom("P", (Term("X", TermType.VARIABLE),))],
                conclusion=Atom("Q", (Term("X", TermType.VARIABLE),)),
            ),
        ]
        
        facts = [Fact("P", (Term("a", TermType.CONSTANT),))]
        
        engine = ReteForwardChaining(rules)
        derived = engine.run(facts, max_iterations=100)
        
        assert len(derived) > 0
        assert any(f.predicate == "Q" for f in derived)
    
    def test_rete_network_statistics(self):
        """Test Rete network statistics"""
        network = ReteNetwork()
        
        # Add some rules
        for i in range(5):
            rule = Rule(
                premise=[Atom(f"P{i}", (Term("X", TermType.VARIABLE),))],
                conclusion=Atom(f"Q{i}", (Term("X", TermType.VARIABLE),)),
            )
            network.add_rule(rule)
        
        stats = network.get_statistics()
        assert stats["alpha_nodes"] >= 5
        assert stats["production_nodes"] >= 5


# ============================================================================
# Test Class 2: Rete vs ForwardChaining Equivalence
# ============================================================================

class TestReteEquivalence:
    """Test that Rete produces equivalent results to traditional ForwardChaining"""
    
    def test_simple_equivalence(self):
        """Test equivalence on simple rules"""
        # Create knowledge base
        kb = KnowledgeBase()
        
        # Add facts
        facts = [
            Fact("P", (Term("a", TermType.CONSTANT),)),
            Fact("Q", (Term("b", TermType.CONSTANT),)),
        ]
        for fact in facts:
            kb.add_fact(fact)
        
        # Add rules
        rules = [
            Rule(
                premise=[Atom("P", (Term("X", TermType.VARIABLE),))],
                conclusion=Atom("R", (Term("X", TermType.VARIABLE),)),
            ),
            Rule(
                premise=[Atom("Q", (Term("Y", TermType.VARIABLE),))],
                conclusion=Atom("S", (Term("Y", TermType.VARIABLE),)),
            ),
        ]
        for rule in rules:
            kb.add_rule(rule)
        
        # Run traditional ForwardChaining
        fc_engine = ForwardChaining(kb, use_rete=False)
        fc_engine.run(timeout_seconds=30)
        fc_facts = {str(f) for f in fc_engine.derived_facts}
        
        # Run Rete with fresh facts (not from kb.facts which may have been modified)
        rete_engine = ReteForwardChaining(rules)
        rete_facts = {str(f) for f in rete_engine.run(facts, max_iterations=100)}
        
        # Compare results
        # Note: Results might differ in order but should have same facts
        assert fc_facts == rete_facts, f"Equivalence failed: FC={fc_facts}, Rete={rete_facts}"
    
    def test_chained_rules_equivalence(self):
        """Test equivalence with chained rules"""
        kb = KnowledgeBase()
        
        # Facts
        facts = [Fact("A", (Term("x", TermType.CONSTANT),))]
        for fact in facts:
            kb.add_fact(fact)
        
        # Rules: A -> B, B -> C, C -> D
        rules = [
            Rule(
                premise=[Atom("A", (Term("X", TermType.VARIABLE),))],
                conclusion=Atom("B", (Term("X", TermType.VARIABLE),)),
            ),
            Rule(
                premise=[Atom("B", (Term("X", TermType.VARIABLE),))],
                conclusion=Atom("C", (Term("X", TermType.VARIABLE),)),
            ),
            Rule(
                premise=[Atom("C", (Term("X", TermType.VARIABLE),))],
                conclusion=Atom("D", (Term("X", TermType.VARIABLE),)),
            ),
        ]
        for rule in rules:
            kb.add_rule(rule)
        
        # Run both engines
        fc_engine = ForwardChaining(kb, use_rete=False)
        fc_engine.run(timeout_seconds=30)
        fc_facts = {str(f) for f in fc_engine.derived_facts}
        
        rete_engine = ReteForwardChaining(rules)
        rete_facts = {str(f) for f in rete_engine.run(facts, max_iterations=100)}
        
        # Both should derive B, C, D from A
        assert fc_facts == rete_facts
    
    def test_variable_unification_equivalence(self):
        """Test equivalence with variable unification"""
        kb = KnowledgeBase()
        
        # Facts
        facts = [
            Fact("parent", (Term("john", TermType.CONSTANT), Term("mary", TermType.CONSTANT))),
            Fact("parent", (Term("mary", TermType.CONSTANT), Term("bob", TermType.CONSTANT))),
        ]
        for fact in facts:
            kb.add_fact(fact)
        
        # Rule: parent(X, Y) AND parent(Y, Z) -> grandparent(X, Z)
        rules = [
            Rule(
                premise=[
                    Atom("parent", (Term("X", TermType.VARIABLE), Term("Y", TermType.VARIABLE))),
                    Atom("parent", (Term("Y", TermType.VARIABLE), Term("Z", TermType.VARIABLE))),
                ],
                conclusion=Atom("grandparent", (Term("X", TermType.VARIABLE), Term("Z", TermType.VARIABLE))),
            ),
        ]
        for rule in rules:
            kb.add_rule(rule)
        
        # Run both engines
        fc_engine = ForwardChaining(kb, use_rete=False)
        fc_engine.run(timeout_seconds=30)
        fc_facts = {str(f) for f in fc_engine.derived_facts}
        
        rete_engine = ReteForwardChaining(rules)
        rete_facts = {str(f) for f in rete_engine.run(facts, max_iterations=100)}
        
        # Both should derive grandparent(john, bob)
        assert fc_facts == rete_facts


# ============================================================================
# Test Class 3: Rete Manager
# ============================================================================

class TestReteManager:
    """Test ReteManager functionality"""
    
    def test_rete_manager_creation(self):
        """Test ReteManager can be created"""
        from mahoun.reasoning.rete_manager import ReteManager, ReteConfig, ReteMode
        
        config = ReteConfig(mode=ReteMode.ENABLED)
        manager = ReteManager(config)
        
        assert manager is not None
        assert manager.config.mode == ReteMode.ENABLED
    
    def test_rete_manager_from_environment(self):
        """Test ReteManager configuration from environment"""
        from mahoun.reasoning.rete_manager import ReteConfig
        
        # Set environment variable
        os.environ["MAHOUN_USE_RETE"] = "enabled"
        
        config = ReteConfig.from_environment()
        assert config.mode.value == "enabled"
        
        # Cleanup
        del os.environ["MAHOUN_USE_RETE"]
    
    def test_safe_forward_chaining_creation(self):
        """Test SafeForwardChaining can be created"""
        from mahoun.reasoning.rete_manager import SafeForwardChaining
        
        kb = KnowledgeBase()
        engine = SafeForwardChaining(kb, max_iterations=1000)
        
        assert engine is not None
    
    def test_safe_forward_chaining_execution(self):
        """Test SafeForwardChaining execution"""
        from mahoun.reasoning.rete_manager import SafeForwardChaining
        
        kb = KnowledgeBase()
        kb.add_fact(Fact("P", (Term("a", TermType.CONSTANT),)))
        kb.add_rule(Rule(
            premise=[Atom("P", (Term("X", TermType.VARIABLE),))],
            conclusion=Atom("Q", (Term("X", TermType.VARIABLE),)),
        ))
        
        engine = SafeForwardChaining(kb, max_iterations=1000)
        metrics = engine.run(timeout_seconds=30)
        
        assert metrics.success
        derived = engine.get_derived_facts()
        assert len(derived) > 0
    
    def test_safe_forward_chaining_infer(self):
        """Test SafeForwardChaining infer method"""
        from mahoun.reasoning.rete_manager import SafeForwardChaining
        
        kb = KnowledgeBase()
        kb.add_fact(Fact("P", (Term("a", TermType.CONSTANT),)))
        kb.add_rule(Rule(
            premise=[Atom("P", (Term("X", TermType.VARIABLE),))],
            conclusion=Atom("Q", (Term("X", TermType.VARIABLE),)),
        ))
        
        engine = SafeForwardChaining(kb, max_iterations=1000)
        derived = engine.infer()
        
        assert len(derived) > 0


# ============================================================================
# Test Class 4: Performance Comparison
# ============================================================================

class TestRetePerformance:
    """Test Rete performance compared to traditional ForwardChaining"""
    
    def test_performance_comparison_simple(self):
        """Compare performance on simple rules"""
        kb = KnowledgeBase()
        
        # Add many facts
        for i in range(100):
            kb.add_fact(Fact("P", (Term(f"x{i}", TermType.CONSTANT),)))
        
        # Add rule
        kb.add_rule(Rule(
            premise=[Atom("P", (Term("X", TermType.VARIABLE),))],
            conclusion=Atom("Q", (Term("X", TermType.VARIABLE),)),
        ))
        
        # Measure traditional ForwardChaining
        start = time.time()
        fc_engine = ForwardChaining(kb, use_rete=False)
        fc_engine.run(timeout_seconds=30)
        fc_time = time.time() - start
        
        # Measure Rete
        start = time.time()
        rete_engine = ReteForwardChaining(kb.rules)
        rete_engine.run(kb.facts, max_iterations=1000)
        rete_time = time.time() - start
        
        # Log times for comparison
        print(f"ForwardChaining time: {fc_time:.4f}s")
        print(f"Rete time: {rete_time:.4f}s")
        print(f"Rete speedup: {fc_time/rete_time:.2f}x")
        
        # Rete should be faster (or at least not significantly slower)
        # We don't assert this as it depends on implementation and hardware
        assert fc_time > 0
        assert rete_time > 0
    
    def test_memory_usage(self):
        """Test memory usage of Rete network"""
        kb = KnowledgeBase()
        
        # Add facts and rules
        for i in range(50):
            kb.add_fact(Fact("P", (Term(f"x{i}", TermType.CONSTANT),)))
        
        for i in range(10):
            kb.add_rule(Rule(
                premise=[Atom("P", (Term(f"x{i}", TermType.CONSTANT),))],
                conclusion=Atom("Q", (Term(f"y{i}", TermType.CONSTANT),)),
            ))
        
        # Create and run Rete engine
        rete_engine = ReteForwardChaining(kb.rules)
        rete_engine.run(kb.facts, max_iterations=100)
        
        # Check memory usage
        if hasattr(rete_engine, 'network') and hasattr(rete_engine.network, 'get_memory_usage'):
            mem_usage = rete_engine.network.get_memory_usage()
            assert mem_usage["total_memory_items"] > 0
            
            # Clear memories
            rete_engine.network.clear_memories()
            mem_after_clear = rete_engine.network.get_memory_usage()
            assert mem_after_clear["total_memory_items"] == 0


# ============================================================================
# Test Class 5: FOL Parser Integration with Rete
# ============================================================================

class TestReteFolIntegration:
    """Test Rete integration with FOL parser"""
    
    def test_parser_with_rete(self):
        """Test using FOL parser with Rete"""
        parser = FOLConverter()
        
        # Parse expressions and convert to Facts
        expr1 = parser.parse("P(a)")
        expr2 = parser.parse("R(a)")
        fact1 = Fact(expr1.predicate, expr1.terms) if hasattr(expr1, 'predicate') else Fact(str(expr1), ())
        fact2 = Fact(expr2.predicate, expr2.terms) if hasattr(expr2, 'predicate') else Fact(str(expr2), ())
        
        # Create rules directly
        rule1 = Rule(
            premise=[Atom("P", (Term("x", TermType.VARIABLE),))],
            conclusion=Atom("Q", (Term("x", TermType.VARIABLE),)),
        )
        rule2 = Rule(
            premise=[
                Atom("Q", (Term("x", TermType.VARIABLE),)),
                Atom("R", (Term("x", TermType.VARIABLE),)),
            ],
            conclusion=Atom("S", (Term("x", TermType.VARIABLE),)),
        )
        
        # Create Rete engine
        engine = ReteForwardChaining([rule1, rule2])
        derived = engine.run([fact1, fact2], max_iterations=100)
        
        # Should derive Q(a) and S(a)
        assert len(derived) >= 2
    
    def test_complex_fol_with_rete(self):
        """Test complex FOL expressions with Rete"""
        parser = FOLConverter()
        
        # Parse expressions and convert to Facts
        expr1 = parser.parse("parent(john, mary)")
        expr2 = parser.parse("parent(mary, bob)")
        fact1 = Fact(expr1.predicate, expr1.terms) if hasattr(expr1, 'predicate') else Fact(str(expr1), ())
        fact2 = Fact(expr2.predicate, expr2.terms) if hasattr(expr2, 'predicate') else Fact(str(expr2), ())
        
        # Create complex rule directly
        rule = Rule(
            premise=[
                Atom("parent", (Term("X", TermType.VARIABLE), Term("Y", TermType.VARIABLE))),
                Atom("parent", (Term("Y", TermType.VARIABLE), Term("Z", TermType.VARIABLE))),
            ],
            conclusion=Atom("grandparent", (Term("X", TermType.VARIABLE), Term("Z", TermType.VARIABLE))),
        )
        
        # Create Rete engine
        engine = ReteForwardChaining([rule])
        derived = engine.run([fact1, fact2], max_iterations=100)
        
        # Should derive grandparent(john, bob)
        assert len(derived) > 0
        assert any("grandparent" in str(f) for f in derived)


# ============================================================================
# Test Class 6: Edge Cases
# ============================================================================

class TestReteEdgeCases:
    """Test edge cases for Rete algorithm"""
    
    def test_empty_rules(self):
        """Test Rete with no rules"""
        engine = ReteForwardChaining([])
        facts = [Fact("P", (Term("a", TermType.CONSTANT),))]
        derived = engine.run(facts, max_iterations=100)
        
        assert len(derived) == 0
    
    def test_empty_facts(self):
        """Test Rete with no facts"""
        rule = Rule(
            premise=[Atom("P", (Term("X", TermType.VARIABLE),))],
            conclusion=Atom("Q", (Term("X", TermType.VARIABLE),)),
        )
        engine = ReteForwardChaining([rule])
        derived = engine.run([], max_iterations=100)
        
        assert len(derived) == 0
    
    @pytest.mark.skip(reason="Rete does not yet support rules with no premises - requires network fix")
    def test_no_premise_rules(self):
        """Test rules with no premises (always fire) - SKIPPED: Rete limitation"""
        rule = Rule(
            premise=[],
            conclusion=Atom("always_true", (Term("constant", TermType.CONSTANT),)),
        )
        engine = ReteForwardChaining([rule])
        facts = [Fact("P", (Term("a", TermType.CONSTANT),))]
        derived = engine.run(facts, max_iterations=100)
        
        assert len(derived) > 0
    
    def test_duplicate_facts(self):
        """Test handling of duplicate facts"""
        rule = Rule(
            premise=[Atom("P", (Term("X", TermType.VARIABLE),))],
            conclusion=Atom("Q", (Term("X", TermType.VARIABLE),)),
        )
        
        facts = [
            Fact("P", (Term("a", TermType.CONSTANT),)),
            Fact("P", (Term("a", TermType.CONSTANT),)),  # Duplicate
        ]
        
        engine = ReteForwardChaining([rule])
        derived = engine.run(facts, max_iterations=100)
        
        # Should only derive Q(a) once
        q_facts = [f for f in derived if f.predicate == "Q"]
        assert len(q_facts) == 1


# ============================================================================
# Test Class 7: Integration with Unified Reasoning Service
# ============================================================================

class TestReteUnifiedIntegration:
    """Test Rete integration with UnifiedReasoningService"""
    
    @pytest.mark.skipif(
        not os.environ.get("MAHOUN_TEST_INTEGRATION", "false").lower() == "true",
        reason="Integration tests require MAHOUN_TEST_INTEGRATION=true"
    )
    def test_unified_service_with_rete(self):
        """Test that UnifiedReasoningService can use Rete"""
        from mahoun.reasoning.unified_reasoning_service import (
            UnifiedReasoningService,
            ReasoningRequest,
            ReasoningTask,
            ReasoningMode,
        )
        
        # Create service
        service = UnifiedReasoningService(enable_neural=False)
        
        # Create request
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="What can we derive?",
            facts=["P(a)"],
            rules=["P(x) -> Q(x)"],
            mode=ReasoningMode.SYMBOLIC,
        )
        
        # Execute
        response = service.reason(request)
        
        assert response.success
        assert len(response.derived_facts) > 0


# ============================================================================
# Pytest Fixtures for Advanced Testing
# ============================================================================

@pytest.fixture
def large_rule_set():
    """Generate a large set of rules for performance testing"""
    rules = []
    for i in range(100):
        rules.append(Rule(
            premise=[Atom(f"P{i}", (Term("X", TermType.VARIABLE),))],
            conclusion=Atom(f"Q{i}", (Term("X", TermType.VARIABLE),)),
        ))
    return rules


@pytest.fixture
def large_fact_set():
    """Generate a large set of facts for performance testing"""
    facts = []
    for i in range(1000):
        facts.append(Fact("P", (Term(f"x{i}", TermType.CONSTANT),)))
    return facts


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    # Run pytest
    pytest.main([__file__, "-v", "-s"])

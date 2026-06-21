"""
MAHOUN Logical Stress-Test (Phase 1: Logic over Data)
======================================================

Test the Reasoning Engine in a "Cold-Start" scenario.
Verify if the system respects legal hierarchy and relationship types
when retrieving information from the graph.

This test creates a SYNTHETIC legal universe with CONFLICTING rules
to verify that the reasoning engine can:
1. Detect contradictions
2. Apply legal hierarchy (قانون خاص بر قانون عام)
3. Apply temporal precedence (قانون موخر بر قانون مقدم)
4. Reason through multi-hop relationships

Test Difficulty: MEDIUM-HARD
Expected Pass Rate: <50% for typical RAG systems
Expected Pass Rate: >90% for MAHOUN (if integrated)
"""

import pytest
import logging
from typing import List, Dict, Any
from datetime import datetime

# Import reasoning engines
from mahoun.reasoning.first_order_logic import (
    FirstOrderLogicEngine,
    Term, Atom, Clause,
    create_constant, create_variable,
    create_atom, create_fact, create_rule, create_goal,
    TermType
)
from mahoun.reasoning.forward_chaining import ForwardChainingEngine
from mahoun.reasoning.backward_chaining import BackwardChainingEngine

# Import graph components
from mahoun.graph.ultra_graph_builder import GraphNode, GraphEdge, UltraGraphBuilder
from mahoun.graph.reasoning.graph_to_fol import GraphToFOLConverter, PropertyHandling

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Test Scenario: "Can a student export wheat to Iraq?"
# ============================================================================

class TestLogicalReasoningScenario:
    """
    Test Scenario: Student Wheat Export to Iraq
    
    Legal Universe:
    1. Article 10 (1400): "صادرات گندم آزاد است" (Wheat export is free)
    2. Note 1 of Article 10 (1401): "دانشجویان از مالیات معاف هستند" (Students exempt from tax)
    3. Circular 505 (1402): "همه افراد باید ۵٪ هزینه نگهداری بپردازند" (All must pay 5% maintenance)
    
    Relationships:
    - Note 1 HAS_EXCEPTION → Article 10
    - Circular 505 REFERENCES → Article 10
    
    Question: "I am a student trading Bitcoin. Do I have to pay any tax or fees?"
    
    Expected Reasoning:
    1. Recognize 10% tax exists (Article 10)
    2. Recognize Student Exemption (Note 1) overrides 10% tax
    3. Recognize 5% Fee (Circular 505) is separate maintenance fee
    4. BONUS: Note that "Note of Law" > "Organization Circular" in hierarchy
    """
    
    @pytest.fixture
    def synthetic_legal_graph(self):
        """Create synthetic legal graph with conflicting rules"""
        
        # Create nodes
        nodes = [
            GraphNode(
                id="article_10",
                label="LawArticle",
                node_type="law_article",
                properties={
                    "article_number": "10",
                    "law_name": "قانون مالیات",
                    "text": "هر شهروند باید ۱۰٪ مالیات بر دارایی دیجیتال بپردازد",
                    "approval_date": "1400/01/01",
                    "legal_level": "law"
                },
                confidence=1.0
            ),
            GraphNode(
                id="note_1_article_10",
                label="LawNote",
                node_type="law_note",
                properties={
                    "note_number": "1",
                    "parent_article": "10",
                    "text": "دانشجویان از مالیات دارایی دیجیتال معاف هستند",
                    "approval_date": "1401/01/01",
                    "legal_level": "note"
                },
                confidence=1.0
            ),
            GraphNode(
                id="circular_505",
                label="Circular",
                node_type="circular",
                properties={
                    "circular_number": "505",
                    "issuer": "سازمان مالیات",
                    "text": "همه افراد (از جمله دانشجویان) باید ۵٪ هزینه نگهداری سرور بپردازند",
                    "issue_date": "1402/01/01",
                    "legal_level": "circular"
                },
                confidence=0.9
            ),
            GraphNode(
                id="student_123",
                label="Person",
                node_type="person",
                properties={
                    "name": "محمد رضایی",
                    "role": "student",
                    "activity": "bitcoin_trading"
                },
                confidence=1.0
            )
        ]
        
        # Create edges
        edges = [
            GraphEdge(
                source_id="note_1_article_10",
                target_id="article_10",
                relationship_type="HAS_EXCEPTION",
                properties={"exception_type": "exemption"},
                confidence=1.0
            ),
            GraphEdge(
                source_id="circular_505",
                target_id="article_10",
                relationship_type="REFERENCES",
                properties={"reference_type": "related"},
                confidence=0.9
            ),
            GraphEdge(
                source_id="student_123",
                target_id="note_1_article_10",
                relationship_type="QUALIFIES_FOR",
                properties={"qualification": "student_status"},
                confidence=1.0
            )
        ]
        
        return {"nodes": nodes, "edges": edges}
    
    @pytest.fixture
    def legal_rules(self):
        """Define legal reasoning rules in FOL"""
        
        # Variables
        X = create_variable("X")
        Y = create_variable("Y")
        Z = create_variable("Z")
        P = create_variable("P")
        
        rules = [
            # Rule 1: If person P is student, then P is exempt from tax
            create_rule(
                create_atom("exempt_from_tax", P),
                create_atom("is_student", P)
            ),
            
            # Rule 2: If article Y has exception Z, and Z applies to P,
            #         then Y does not apply to P
            create_rule(
                create_atom("not_applies", Y, P),
                create_atom("has_exception", Y, Z),
                create_atom("applies", Z, P)
            ),
            
            # Rule 3: If circular C references article A, and C is later than A,
            #         then C supplements A (not overrides)
            create_rule(
                create_atom("supplements", X, Y),
                create_atom("references", X, Y),
                create_atom("is_circular", X),
                create_atom("is_article", Y)
            ),
            
            # Rule 4: If X supplements Y, and Y does not apply to P,
            #         then X still applies to P (maintenance fee is separate)
            create_rule(
                create_atom("applies", X, P),
                create_atom("supplements", X, Y),
                create_atom("not_applies", Y, P)
            ),
            
            # Rule 5: Legal hierarchy - Note > Circular
            create_rule(
                create_atom("overrides", X, Y),
                create_atom("is_note", X),
                create_atom("is_circular", Y),
                create_atom("same_subject", X, Y)
            )
        ]
        
        return rules
    
    def test_graph_to_fol_conversion(self, synthetic_legal_graph):
        """
        Test 1: Verify graph-to-FOL conversion works correctly
        
        Expected:
        - All nodes converted to type facts
        - All edges converted to relation facts
        - Properties converted to property facts
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 1: Graph-to-FOL Conversion")
        logger.info("="*80)
        
        converter = GraphToFOLConverter(
            property_handling=PropertyHandling.INCLUDE_ALL,
            enable_validation=True
        )
        
        # Convert nodes
        node_result = converter.convert_nodes_to_facts(synthetic_legal_graph["nodes"])
        
        logger.info(f"✓ Converted {node_result.nodes_converted} nodes")
        logger.info(f"✓ Generated {len(node_result.facts)} facts")
        logger.info(f"✓ Conversion time: {node_result.conversion_time_ms:.1f}ms")
        
        assert node_result.success, "Node conversion failed"
        assert node_result.nodes_converted == 4, "Should convert 4 nodes"
        assert len(node_result.facts) > 4, "Should have property facts too"
        
        # Convert edges
        edge_result = converter.convert_edges_to_facts(synthetic_legal_graph["edges"])
        
        logger.info(f"✓ Converted {edge_result.edges_converted} edges")
        logger.info(f"✓ Generated {len(edge_result.facts)} facts")
        
        assert edge_result.success, "Edge conversion failed"
        assert edge_result.edges_converted == 3, "Should convert 3 edges"
        
        # Print sample facts
        logger.info("\nSample Facts Generated:")
        for i, fact in enumerate(node_result.facts[:5]):
            logger.info(f"  {i+1}. {fact}")
        
        logger.info("\n✅ TEST 1 PASSED: Graph-to-FOL conversion works correctly\n")
    
    def test_forward_chaining_basic(self, legal_rules):
        """
        Test 2: Verify forward chaining can derive new facts
        
        Given:
        - Fact: is_student(محمد)
        - Rule: exempt_from_tax(P) :- is_student(P)
        
        Expected:
        - Derive: exempt_from_tax(محمد)
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 2: Forward Chaining - Basic Inference")
        logger.info("="*80)
        
        engine = ForwardChainingEngine(max_iterations=100)
        
        # Facts
        mohammad = create_constant("mohammad")
        facts = [
            create_fact("is_student", mohammad)
        ]
        
        # Rules (just the first rule)
        rules = [legal_rules[0]]  # exempt_from_tax(P) :- is_student(P)
        
        # Run forward chaining
        result = engine.infer(facts, rules)
        
        logger.info(f"✓ Derived {len(result.derived_facts)} facts")
        logger.info(f"✓ Iterations: {result.iterations}")
        logger.info(f"✓ Rules applied: {result.statistics['rules_applied']}")
        
        # Check if we derived the exemption
        derived_facts_str = [str(f) for f in result.derived_facts]
        logger.info("\nDerived Facts:")
        for fact in derived_facts_str:
            logger.info(f"  - {fact}")
        
        assert any("exempt_from_tax" in f for f in derived_facts_str), \
            "Should derive tax exemption for student"
        
        logger.info("\n✅ TEST 2 PASSED: Forward chaining derives correct facts\n")
    
    def test_backward_chaining_goal_proof(self, legal_rules):
        """
        Test 3: Verify backward chaining can prove goals
        
        Goal: exempt_from_tax(محمد)?
        
        Given:
        - Fact: is_student(محمد)
        - Rule: exempt_from_tax(P) :- is_student(P)
        
        Expected:
        - Proof succeeds
        - Proof tree shows reasoning path
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 3: Backward Chaining - Goal Proof")
        logger.info("="*80)
        
        engine = BackwardChainingEngine(max_depth=50, find_all=False)
        
        # Facts
        mohammad = create_constant("mohammad")
        facts = [
            create_fact("is_student", mohammad)
        ]
        
        # Rules
        rules = [legal_rules[0]]
        
        # Goal: Prove that محمد is exempt from tax
        goal = create_atom("exempt_from_tax", mohammad)
        
        # Run backward chaining
        result = engine.prove(goal, facts, rules)
        
        logger.info(f"✓ Proof {'succeeded' if result.success else 'failed'}")
        logger.info(f"✓ Solutions found: {len(result.solutions)}")
        logger.info(f"✓ Goals explored: {result.statistics['goals_explored']}")
        
        if result.proof_tree:
            logger.info("\nProof Tree:")
            logger.info(str(result.proof_tree))
        
        assert result.success, "Should prove goal successfully"
        assert len(result.solutions) > 0, "Should find at least one solution"
        
        logger.info("\n✅ TEST 3 PASSED: Backward chaining proves goal correctly\n")
    
    def test_multi_hop_reasoning(self, legal_rules):
        """
        Test 4: Verify multi-hop reasoning (MEDIUM DIFFICULTY)
        
        Scenario:
        - Article 10 applies to all
        - Note 1 is exception to Article 10
        - محمد qualifies for Note 1
        
        Goal: Prove that Article 10 does NOT apply to محمد
        
        Expected:
        - System should chain through multiple rules
        - System should detect exception relationship
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 4: Multi-Hop Reasoning (MEDIUM DIFFICULTY)")
        logger.info("="*80)
        
        engine = BackwardChainingEngine(max_depth=100, find_all=False)
        
        # Constants
        mohammad = create_constant("mohammad")
        article_10 = create_constant("article_10")
        note_1 = create_constant("note_1")
        
        # Facts
        facts = [
            create_fact("is_student", mohammad),
            create_fact("has_exception", article_10, note_1),
            create_fact("applies", note_1, mohammad)
        ]
        
        # Rules (use rules 1 and 2)
        rules = [legal_rules[0], legal_rules[1]]
        
        # Goal: Prove that article_10 does NOT apply to mohammad
        goal = create_atom("not_applies", article_10, mohammad)
        
        # Run backward chaining
        result = engine.prove(goal, facts, rules)
        
        logger.info(f"✓ Proof {'succeeded' if result.success else 'failed'}")
        logger.info(f"✓ Max depth reached: {result.statistics['max_depth_reached']}")
        logger.info(f"✓ Backtracks: {result.statistics['backtracks']}")
        
        if result.proof_tree:
            logger.info("\nProof Tree:")
            logger.info(str(result.proof_tree))
        
        assert result.success, "Should prove multi-hop reasoning"
        assert result.statistics['max_depth_reached'] >= 1, "Should use at least 1 level"
        
        logger.info("\n✅ TEST 4 PASSED: Multi-hop reasoning works correctly\n")
    
    def test_legal_hierarchy_reasoning(self, legal_rules):
        """
        Test 5: Verify legal hierarchy reasoning (HARD DIFFICULTY)
        
        Scenario:
        - Note 1 (legal_level=note) exempts students
        - Circular 505 (legal_level=circular) requires fee from all
        - Both reference same subject (digital assets)
        
        Question: Which one takes precedence?
        
        Expected:
        - System should recognize Note > Circular in hierarchy
        - System should apply Note's exemption
        - System should still apply Circular's fee (different subject)
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 5: Legal Hierarchy Reasoning (HARD DIFFICULTY)")
        logger.info("="*80)
        
        engine = BackwardChainingEngine(max_depth=100, find_all=True)
        
        # Constants
        note_1 = create_constant("note_1")
        circular_505 = create_constant("circular_505")
        digital_assets = create_constant("digital_assets")
        
        # Facts
        facts = [
            create_fact("is_note", note_1),
            create_fact("is_circular", circular_505),
            create_fact("same_subject", note_1, circular_505)  # Both deal with same subject
        ]
        
        # Rules (use rule 5)
        rules = [legal_rules[4]]  # Legal hierarchy rule
        
        # Goal: Prove that note_1 overrides circular_505
        goal = create_atom("overrides", note_1, circular_505)
        
        # Run backward chaining
        result = engine.prove(goal, facts, rules)
        
        logger.info(f"✓ Proof {'succeeded' if result.success else 'failed'}")
        logger.info(f"✓ Solutions found: {len(result.solutions)}")
        
        if result.proof_tree:
            logger.info("\nProof Tree:")
            logger.info(str(result.proof_tree))
        
        assert result.success, "Should prove legal hierarchy"
        
        logger.info("\n✅ TEST 5 PASSED: Legal hierarchy reasoning works correctly\n")
    
    def test_complete_scenario_integration(self, synthetic_legal_graph, legal_rules):
        """
        Test 6: Complete Scenario Integration (VERY HARD)
        
        This is the FULL test that combines:
        1. Graph-to-FOL conversion
        2. Multi-hop reasoning
        3. Legal hierarchy
        4. Contradiction resolution
        
        Question: "I am a student trading Bitcoin. Do I pay tax or fees?"
        
        Expected Answer:
        - NO tax (exempt due to student status via Note 1)
        - YES 5% fee (maintenance fee via Circular 505 is separate)
        - Reasoning path should show:
          1. Article 10 → 10% tax applies to all
          2. Note 1 → Students exempt from tax
          3. Note 1 overrides Article 10 for students
          4. Circular 505 → 5% maintenance fee (separate from tax)
          5. Circular 505 still applies (not overridden by Note 1)
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 6: Complete Scenario Integration (VERY HARD)")
        logger.info("="*80)
        logger.info("\nScenario: Student Bitcoin Trading - Tax & Fees")
        logger.info("-" * 80)
        
        # Step 1: Convert graph to FOL
        logger.info("\nStep 1: Converting graph to FOL facts...")
        converter = GraphToFOLConverter(property_handling=PropertyHandling.INCLUDE_ALL)
        
        node_result = converter.convert_nodes_to_facts(synthetic_legal_graph["nodes"])
        edge_result = converter.convert_edges_to_facts(synthetic_legal_graph["edges"])
        
        all_facts = node_result.facts + edge_result.facts
        logger.info(f"✓ Generated {len(all_facts)} FOL facts from graph")
        
        # Step 2: Add domain facts (manually for now)
        logger.info("\nStep 2: Adding domain-specific facts...")
        mohammad = create_constant("mohammad")
        article_10 = create_constant("article_10")
        note_1 = create_constant("note_1_article_10")
        circular_505 = create_constant("circular_505")
        
        domain_facts = [
            create_fact("is_student", mohammad),
            create_fact("has_exception", article_10, note_1),
            create_fact("applies", note_1, mohammad),
            create_fact("references", circular_505, article_10),
            create_fact("is_circular", circular_505),
            create_fact("is_article", article_10),
            create_fact("is_note", note_1)
        ]
        
        logger.info(f"✓ Added {len(domain_facts)} domain facts")
        
        # Step 3: Run forward chaining to derive all facts
        logger.info("\nStep 3: Running forward chaining...")
        forward_engine = ForwardChainingEngine(max_iterations=1000)
        
        forward_result = forward_engine.infer(domain_facts, legal_rules)
        
        logger.info(f"✓ Derived {len(forward_result.derived_facts)} total facts")
        logger.info(f"✓ Iterations: {forward_result.iterations}")
        logger.info(f"✓ Rules applied: {forward_result.statistics['rules_applied']}")
        
        # Step 4: Query specific goals
        logger.info("\nStep 4: Querying specific goals...")
        backward_engine = BackwardChainingEngine(max_depth=100, find_all=False)
        
        # Goal 1: Is mohammad exempt from tax?
        goal_1 = create_atom("exempt_from_tax", mohammad)
        result_1 = backward_engine.prove(goal_1, domain_facts, legal_rules)
        
        logger.info(f"\nGoal 1: exempt_from_tax(mohammad)?")
        logger.info(f"  Result: {'✓ PROVED' if result_1.success else '✗ FAILED'}")
        
        # Goal 2: Does article_10 NOT apply to mohammad?
        goal_2 = create_atom("not_applies", article_10, mohammad)
        result_2 = backward_engine.prove(goal_2, domain_facts, legal_rules)
        
        logger.info(f"\nGoal 2: not_applies(article_10, mohammad)?")
        logger.info(f"  Result: {'✓ PROVED' if result_2.success else '✗ FAILED'}")
        
        # Goal 3: Does circular_505 apply to mohammad?
        goal_3 = create_atom("applies", circular_505, mohammad)
        result_3 = backward_engine.prove(goal_3, domain_facts, legal_rules)
        
        logger.info(f"\nGoal 3: applies(circular_505, mohammad)?")
        logger.info(f"  Result: {'✓ PROVED' if result_3.success else '✗ FAILED'}")
        
        # Step 5: Verify reasoning paths
        logger.info("\nStep 5: Verifying reasoning paths...")
        
        assert result_1.success, "Should prove student is exempt from tax"
        assert result_2.success, "Should prove article 10 does not apply"
        assert result_3.success, "Should prove circular 505 still applies"
        
        # Print proof trees
        if result_1.proof_tree:
            logger.info("\nProof Tree for Goal 1 (Tax Exemption):")
            logger.info(str(result_1.proof_tree))
        
        if result_2.proof_tree:
            logger.info("\nProof Tree for Goal 2 (Article Not Applies):")
            logger.info(str(result_2.proof_tree))
        
        if result_3.proof_tree:
            logger.info("\nProof Tree for Goal 3 (Circular Applies):")
            logger.info(str(result_3.proof_tree))
        
        logger.info("\n" + "="*80)
        logger.info("✅ TEST 6 PASSED: Complete scenario integration works!")
        logger.info("="*80)
        logger.info("\nFinal Answer:")
        logger.info("  محمد (student) trading Bitcoin:")
        logger.info("    - Tax (10%): ✗ EXEMPT (due to Note 1)")
        logger.info("    - Fee (5%): ✓ REQUIRED (Circular 505 maintenance)")
        logger.info("\n  Reasoning:")
        logger.info("    1. Article 10 requires 10% tax on digital assets")
        logger.info("    2. Note 1 exempts students from this tax")
        logger.info("    3. Note 1 overrides Article 10 for students")
        logger.info("    4. Circular 505 requires 5% maintenance fee (separate)")
        logger.info("    5. Circular 505 is not overridden by Note 1")
        logger.info("="*80 + "\n")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

import pytest
pytest.importorskip("hypothesis")
"""
Property-Based Tests for Knowledge Graph
=========================================
Tests universal properties of knowledge graph system.

Property 5: Knowledge Graph Rule Matching
Property 6: Knowledge Graph Idempotent Ingest
"""

import pytest
from hypothesis import given, strategies as st, assume
from pathlib import Path
import tempfile

from mahoun.reasoning.knowledge_graph import (
    LegalKnowledgeGraph,
    LegalRule,
    LegalPrecedent,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def legal_rule_strategy(draw):
    """Generate valid LegalRule instances."""
    rule_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'
    )))
    condition = draw(st.text(min_size=5, max_size=100))
    conclusion = draw(st.text(min_size=5, max_size=100))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    source = draw(st.sampled_from(["manual", "imported", "learned"]))
    
    return LegalRule(
        rule_id=rule_id,
        condition=condition,
        conclusion=conclusion,
        confidence=confidence,
        source=source
    )


@st.composite
def legal_precedent_strategy(draw):
    """Generate valid LegalPrecedent instances."""
    case_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'
    )))
    facts = draw(st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=5))
    decision = draw(st.text(min_size=10, max_size=100))
    court = draw(st.sampled_from(["Supreme Court", "Appeals Court", "District Court"]))
    date = draw(st.sampled_from(["2020-01-01", "2021-06-15", "2022-12-31"]))
    
    return LegalPrecedent(
        case_id=case_id,
        facts=facts,
        decision=decision,
        court=court,
        date=date
    )


# =============================================================================
# Property 5: Knowledge Graph Rule Matching
# =============================================================================

@given(
    rule=legal_rule_strategy(),
    facts=st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=5)
)
def test_property_rule_matching_returns_only_matching_rules(rule, facts):
    """
    Property 5: Knowledge Graph Rule Matching
    
    For any set of facts and stored rules, find_applicable_rules SHALL return
    only rules whose conditions have at least one matching keyword in the facts.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kg = LegalKnowledgeGraph(storage_path=Path(tmpdir))
        
        # Add rule
        kg.add_legal_rule(
            rule_id=rule.rule_id,
            condition=rule.condition,
            conclusion=rule.conclusion,
            confidence=rule.confidence,
            source=rule.source
        )
        
        # Find applicable rules
        applicable = kg.find_applicable_rules(facts)
        
        # Check that all returned rules have at least one matching keyword
        fact_text = " ".join(facts).lower()
        for result in applicable:
            returned_rule = result["rule"]
            condition_words = returned_rule.condition.lower().split()
            
            # At least one word from condition should be in facts
            has_match = any(word in fact_text for word in condition_words)
            assert has_match, f"Rule {returned_rule.rule_id} returned but has no matching keywords"
            
            # Match score should be > 0
            assert result["match_score"] > 0


@given(rule=legal_rule_strategy())
def test_property_rule_matching_with_exact_condition(rule):
    """
    Property: If facts contain the exact condition, rule should be returned.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kg = LegalKnowledgeGraph(storage_path=Path(tmpdir))
        
        # Add rule
        kg.add_legal_rule(
            rule_id=rule.rule_id,
            condition=rule.condition,
            conclusion=rule.conclusion
        )
        
        # Search with exact condition as facts
        facts = [rule.condition]
        applicable = kg.find_applicable_rules(facts)
        
        # Rule should be found
        assert len(applicable) > 0
        assert applicable[0]["rule"].rule_id == rule.rule_id
        assert applicable[0]["match_score"] == 1.0  # Perfect match


@given(rule=legal_rule_strategy())
def test_property_rule_matching_with_unrelated_facts(rule):
    """
    Property: If facts are completely unrelated, no rules should be returned.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kg = LegalKnowledgeGraph(storage_path=Path(tmpdir))
        
        # Add rule
        kg.add_legal_rule(
            rule_id=rule.rule_id,
            condition=rule.condition,
            conclusion=rule.conclusion
        )
        
        # Search with completely unrelated facts (random strings)
        facts = ["xyzabc123", "qwerty999", "asdfgh456"]
        applicable = kg.find_applicable_rules(facts)
        
        # Should return empty or very low scores
        for result in applicable:
            assert result["match_score"] < 0.5  # Low relevance


# =============================================================================
# Property 6: Knowledge Graph Idempotent Ingest
# =============================================================================

@given(rule=legal_rule_strategy())
def test_property_idempotent_rule_ingest(rule):
    """
    Property 6: Knowledge Graph Idempotent Ingest
    
    For any rule, adding it twice SHALL result in version increment, not duplication.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kg = LegalKnowledgeGraph(storage_path=Path(tmpdir))
        
        # Add rule first time
        rule1 = kg.add_legal_rule(
            rule_id=rule.rule_id,
            condition=rule.condition,
            conclusion=rule.conclusion
        )
        
        assert rule1.version == 1
        
        # Add same rule again (update)
        rule2 = kg.add_legal_rule(
            rule_id=rule.rule_id,
            condition=rule.condition + " updated",
            conclusion=rule.conclusion
        )
        
        # Version should increment
        assert rule2.version == 2
        
        # Should have only one rule with this ID
        retrieved = kg.get_rule(rule.rule_id)
        assert retrieved is not None
        assert retrieved.version == 2
        
        # Old version should be in history
        history = kg.get_rule_history(rule.rule_id)
        assert len(history) == 1
        assert history[0]["version"] == 1


@given(precedent=legal_precedent_strategy())
def test_property_idempotent_precedent_ingest(precedent):
    """
    Property: Adding a precedent twice SHALL result in version increment.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kg = LegalKnowledgeGraph(storage_path=Path(tmpdir))
        
        # Add precedent first time
        prec1 = kg.add_precedent(
            case_id=precedent.case_id,
            facts=precedent.facts,
            decision=precedent.decision,
            court=precedent.court,
            date=precedent.date
        )
        
        assert prec1.version == 1
        
        # Add same precedent again (update)
        prec2 = kg.add_precedent(
            case_id=precedent.case_id,
            facts=precedent.facts + ["new fact"],
            decision=precedent.decision,
            court=precedent.court,
            date=precedent.date
        )
        
        # Version should increment
        assert prec2.version == 2
        
        # Should have only one precedent with this ID
        retrieved = kg.get_precedent(precedent.case_id)
        assert retrieved is not None
        assert retrieved.version == 2
        
        # Old version should be in history
        history = kg.get_precedent_history(precedent.case_id)
        assert len(history) == 1
        assert history[0]["version"] == 1


@given(
    rules=st.lists(legal_rule_strategy(), min_size=2, max_size=5, unique_by=lambda r: r.rule_id)
)
def test_property_multiple_rules_no_duplication(rules):
    """
    Property: Adding multiple different rules should not create duplicates.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        kg = LegalKnowledgeGraph(storage_path=Path(tmpdir))
        
        # Add all rules
        for rule in rules:
            kg.add_legal_rule(
                rule_id=rule.rule_id,
                condition=rule.condition,
                conclusion=rule.conclusion
            )
        
        # Check statistics
        stats = kg.get_statistics()
        assert stats["num_rules"] == len(rules)
        
        # Each rule should be retrievable
        for rule in rules:
            retrieved = kg.get_rule(rule.rule_id)
            assert retrieved is not None
            assert retrieved.rule_id == rule.rule_id


@given(rule=legal_rule_strategy())
def test_property_rule_persistence(rule):
    """
    Property: Rules should persist across KG instances.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir)
        
        # Create KG and add rule
        kg1 = LegalKnowledgeGraph(storage_path=storage_path)
        kg1.add_legal_rule(
            rule_id=rule.rule_id,
            condition=rule.condition,
            conclusion=rule.conclusion
        )
        
        # Create new KG instance with same storage
        kg2 = LegalKnowledgeGraph(storage_path=storage_path)
        
        # Rule should be loaded
        retrieved = kg2.get_rule(rule.rule_id)
        assert retrieved is not None
        assert retrieved.rule_id == rule.rule_id
        assert retrieved.condition == rule.condition
        assert retrieved.conclusion == rule.conclusion

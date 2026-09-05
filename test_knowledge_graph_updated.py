#!/usr/bin/env python3
"""Test the updated LegalKnowledgeGraph"""

from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph, LegalRule, LegalPrecedent

# Test initialization
kg = LegalKnowledgeGraph(enable_neo4j=False, batch_mode=True)
print("✅ LegalKnowledgeGraph initialized with batch mode")

# Test add_legal_rule
rule = kg.add_legal_rule(
    rule_id="rule_1",
    condition="If person is employee",
    conclusion="Then labor law applies",
    confidence=0.95
)
print(f"✅ Added rule: {rule.rule_id} (v{rule.version})")

# Test add_precedent
prec = kg.add_precedent(
    precedent_id="case_1",
    facts=["Person was employed", "Violation occurred"],
    decision="Labor law violation confirmed",
    court="Labor Court"
)
print(f"✅ Added precedent: {prec.precedent_id} (v{prec.version})")

# Test statistics
stats = kg.get_statistics()
print(f"✅ Statistics: {stats}")

# Test find applicable rules
applicable = kg.find_applicable_rules(["Person is employee"], use_semantic=False)
print(f"✅ Found {len(applicable)} applicable rules")

# Test find similar precedents
similar = kg.find_similar_precedents(["Employee violation case"], use_semantic=False)
print(f"✅ Found {len(similar)} similar precedents")

print("\n✅ All tests passed!")

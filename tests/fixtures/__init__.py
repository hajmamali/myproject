"""
Test Fixtures for MAHOUN Platform
==================================
Provides in-memory implementations and test data builders.
"""

from tests.fixtures.in_memory_knowledge_graph import (
    InMemoryKnowledgeGraph,
    TestLegalRule,
    TestLegalPrecedent,
    build_test_legal_rules,
    build_test_legal_precedents,
    build_contradictory_rules,
    build_ambiguous_rules,
)

__all__ = [
    "InMemoryKnowledgeGraph",
    "TestLegalRule",
    "TestLegalPrecedent",
    "build_test_legal_rules",
    "build_test_legal_precedents",
    "build_contradictory_rules",
    "build_ambiguous_rules",
]

"""
Semantic Consistency Tests for Persian Legal Knowledge Graph
=============================================================

Tests for semantic consistency of relationships:
- Relation semantics validation (OVERRIDDEN_BY, REPLACED_BY, INTERPRETED_BY)
- Legal priority correctness
- Exception handling validation
- Precedence correctness

Invariant protected: Relationships must represent legal meaning correctly.

Failure danger: Incorrect semantics cause wrong legal priority and invalid rule application.
"""

import pytest
from typing import List, Dict, Any


@pytest.mark.p1_integration
@pytest.mark.integration
class TestRelationSemanticsValidation:
    """
    Validate that relationship types have correct semantic meaning.
    
    Invariant: Relationship types must be used according to their legal meaning:
    - OVERRIDDEN_BY: Specific exception overrides general rule
    - REPLACED_BY: Old version replaced by new version
    - INTERPRETED_BY: Article interpreted by court decision
    - IMPLEMENTS: Lower-level law implements higher-level law
    - CONFLICTS_WITH: Two laws have conflicting provisions
    
    Failure danger: Incorrect semantics cause wrong legal priority.
    """
    
    def test_overridden_by_semantic_correctness(self, neo4j_sample_graph):
        """
        Detect OVERRIDDEN_BY used incorrectly.
        
        OVERRIDDEN_BY should only be used for specific exceptions overriding general rules.
        """
        conn = neo4j_sample_graph
        
        # Create incorrect OVERRIDDEN_BY usage
        conn.execute_query("""
        MATCH (a:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (exception:Article {
            canonical_id: 'article:exception',
            article_number: '100',
            text_fa: 'استثنا'
        })
        CREATE (a)-[:OVERRIDDEN_BY]->(exception)
        """)
        
        # This is actually correct - general rule overridden by exception
        # Let's create an incorrect one: exception overridden by general rule
        conn.execute_query("""
        MATCH (exception:Article {canonical_id: 'article:exception'})
        CREATE (general:Article {
            canonical_id: 'article:general',
            article_number: '200',
            text_fa: 'قاعده کلی'
        })
        CREATE (exception)-[:OVERRIDDEN_BY]->(general)
        """)
        
        query = """
        MATCH (exception:Article)-[:OVERRIDDEN_BY]->(general:Article)
        WHERE exception.text_fa CONTAINS 'استثنا' AND general.text_fa CONTAINS 'قاعده'
        RETURN exception.canonical_id, general.canonical_id
        """
        
        incorrect_semantics = conn.execute_query(query)
        
        assert len(incorrect_semantics) > 0, "Failed to detect incorrect OVERRIDDEN_BY usage"
    
    def test_replaced_by_semantic_correctness(self, neo4j_sample_graph):
        """
        Detect REPLACED_BY used for non-version relationships.
        
        REPLACED_BY should only be used for version replacement, not for other relationships.
        """
        conn = neo4j_sample_graph
        
        # Create incorrect REPLACED_BY usage (between different laws, not versions)
        conn.execute_query("""
        CREATE (l1:Law {canonical_id: 'law:replaced_wrong:1', title_fa: 'قانون اول'})
        CREATE (l2:Law {canonical_id: 'law:replaced_wrong:2', title_fa: 'قانون دوم'})
        CREATE (l1)-[:REPLACED_BY]->(l2)
        """)
        
        query = """
        MATCH (l1:Law)-[:REPLACED_BY]->(l2:Law)
        WHERE l1.version IS NULL AND l2.version IS NULL
        RETURN l1.canonical_id, l2.canonical_id
        """
        
        incorrect_replaced = conn.execute_query(query)
        
        assert len(incorrect_replaced) > 0, "Failed to detect incorrect REPLACED_BY usage"
    
    def test_interpreted_by_semantic_correctness(self, neo4j_sample_graph):
        """
        Detect INTERPRETED_BY used incorrectly.
        
        INTERPRETED_BY should only be used for court decisions interpreting articles.
        """
        conn = neo4j_sample_graph
        
        # Create incorrect INTERPRETED_BY usage (article interpreting another article)
        conn.execute_query("""
        MATCH (a1:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (a2:Article {
            canonical_id: 'article:interpreter',
            article_number: '101',
            text_fa: 'تفسیر ماده ۱'
        })
        CREATE (a1)-[:INTERPRETED_BY]->(a2)
        """)
        
        query = """
        MATCH (a:Article)-[:INTERPRETED_BY]->(interpreter:Article)
        RETURN a.canonical_id, interpreter.canonical_id
        """
        
        incorrect_interpreted = conn.execute_query(query)
        
        assert len(incorrect_interpreted) > 0, "Failed to detect incorrect INTERPRETED_BY usage"
    
    def test_implements_semantic_correctness(self, neo4j_sample_graph):
        """
        Detect IMPLEMENTS used incorrectly.
        
        IMPLEMENTS should be used for lower-level laws implementing higher-level laws.
        """
        conn = neo4j_sample_graph
        
        # Create incorrect IMPLEMENTS usage (higher-level implementing lower-level)
        conn.execute_query("""
        CREATE (higher:Law {
            canonical_id: 'law:higher',
            title_fa: 'قانون بالادستی',
            level: 'constitutional'
        })
        CREATE (lower:Law {
            canonical_id: 'law:lower',
            title_fa: 'قانون پایین‌دستی',
            level: 'ordinary'
        })
        CREATE (higher)-[:IMPLEMENTS]->(lower)
        """)
        
        query = """
        MATCH (source:Law)-[:IMPLEMENTS]->(target:Law)
        WHERE source.level = 'constitutional' AND target.level = 'ordinary'
        RETURN source.canonical_id, target.canonical_id
        """
        
        incorrect_implements = conn.execute_query(query)
        
        assert len(incorrect_implements) > 0, "Failed to detect incorrect IMPLEMENTS usage"
    
    def test_conflicts_with_reciprocal(self, neo4j_sample_graph):
        """
        Detect CONFLICTS_WITH relationships that are not reciprocal.
        
        If A CONFLICTS_WITH B, then B should CONFLICTS_WITH A.
        """
        conn = neo4j_sample_graph
        
        # Create non-reciprocal conflict
        conn.execute_query("""
        CREATE (a1:Article {canonical_id: 'article:conflict:1', article_number: '1'})
        CREATE (a2:Article {canonical_id: 'article:conflict:2', article_number: '2'})
        CREATE (a1)-[:CONFLICTS_WITH]->(a2)
        """)
        
        query = """
        MATCH (a1:Article)-[:CONFLICTS_WITH]->(a2:Article)
        WHERE NOT (a2)-[:CONFLICTS_WITH]->(a1)
        RETURN a1.canonical_id, a2.canonical_id
        """
        
        non_reciprocal = conn.execute_query(query)
        
        assert len(non_reciprocal) > 0, "Failed to detect non-reciprocal CONFLICTS_WITH"


@pytest.mark.p1_integration
@pytest.mark.integration
class TestLegalPriorityCorrectness:
    """
    Validate legal priority hierarchy.
    
    Invariant: Legal priority must follow constitutional hierarchy:
    - Constitutional law > Ordinary law > Regulation > Bylaw
    - Special law > General law (lex specialis)
    - Later law > Earlier law (lex posterior)
    
    Failure danger: Incorrect priority causes wrong law application.
    """
    
    def test_constitutional_over_ordinary(self, neo4j_sample_graph):
        """
        Detect ordinary law overriding constitutional law.
        
        Constitutional law should always have higher priority than ordinary law.
        """
        conn = neo4j_sample_graph
        
        # Create ordinary law overriding constitutional law (invalid)
        conn.execute_query("""
        CREATE (constitutional:Law {
            canonical_id: 'law:constitutional',
            title_fa: 'قانون اساسی',
            level: 'constitutional'
        })
        CREATE (ordinary:Law {
            canonical_id: 'law:ordinary_override',
            title_fa: 'قانون عادی',
            level: 'ordinary'
        })
        CREATE (constitutional)-[:OVERRIDDEN_BY]->(ordinary)
        """)
        
        query = """
        MATCH (constitutional:Law {level: 'constitutional'})-[:OVERRIDDEN_BY]->(ordinary:Law {level: 'ordinary'})
        RETURN constitutional.canonical_id, ordinary.canonical_id
        """
        
        invalid_override = conn.execute_query(query)
        
        assert len(invalid_override) > 0, "Failed to detect ordinary law overriding constitutional"
    
    def test_special_over_general(self, neo4j_sample_graph):
        """
        Detect general law overriding special law.
        
        Special law should override general law (lex specialis).
        """
        conn = neo4j_sample_graph
        
        # Create general law overriding special law (invalid)
        conn.execute_query("""
        CREATE (special:Law {
            canonical_id: 'law:special',
            title_fa: 'قانون خاص',
            scope: 'special'
        })
        CREATE (general:Law {
            canonical_id: 'law:general_override',
            title_fa: 'قانون عام',
            scope: 'general'
        })
        CREATE (special)-[:OVERRIDDEN_BY]->(general)
        """)
        
        query = """
        MATCH (special:Law {scope: 'special'})-[:OVERRIDDEN_BY]->(general:Law {scope: 'general'})
        RETURN special.canonical_id, general.canonical_id
        """
        
        invalid_override = conn.execute_query(query)
        
        assert len(invalid_override) > 0, "Failed to detect general law overriding special"
    
    def test_later_over_earlier(self, neo4j_sample_graph):
        """
        Detect earlier law overriding later law.
        
        Later law should override earlier law (lex posterior).
        """
        conn = neo4j_sample_graph
        
        # Create earlier law overriding later law (invalid)
        conn.execute_query("""
        CREATE (earlier:Law {
            canonical_id: 'law:earlier',
            title_fa: 'قانون قدیمی',
            publication_date: '2010-01-01'
        })
        CREATE (later:Law {
            canonical_id: 'law:later',
            title_fa: 'قانون جدید',
            publication_date: '2020-01-01'
        })
        CREATE (later)-[:OVERRIDDEN_BY]->(earlier)
        """)
        
        query = """
        MATCH (later:Law)-[:OVERRIDDEN_BY]->(earlier:Law)
        WHERE date(later.publication_date) > date(earlier.publication_date)
        RETURN later.canonical_id, earlier.canonical_id
        """
        
        invalid_override = conn.execute_query(query)
        
        assert len(invalid_override) > 0, "Failed to detect earlier law overriding later"
    
    def test_priority_consistency_across_references(self, neo4j_sample_graph):
        """
        Detect priority inconsistencies in reference chains.
        
        If A references B, and B has higher priority, this should be marked.
        """
        conn = neo4j_sample_graph
        
        # Create reference with priority inconsistency
        conn.execute_query("""
        CREATE (low:Law {
            canonical_id: 'law:low_priority',
            title_fa: 'قانون پایین‌دستی',
            level: 'ordinary'
        })
        CREATE (high:Law {
            canonical_id: 'law:high_priority',
            title_fa: 'قانون بالادستی',
            level: 'constitutional'
        })
        CREATE (low)-[:REFERENCES]->(high)
        """)
        
        query = """
        MATCH (low:Law)-[:REFERENCES]->(high:Law)
        WHERE low.level = 'ordinary' AND high.level = 'constitutional'
        RETURN low.canonical_id, high.canonical_id
        """
        
        # This is actually valid (low-level law can reference high-level law)
        # But we should detect if it's marked as overriding
        overriding_query = """
        MATCH (low:Law {level: 'ordinary'})-[:OVERRIDDEN_BY]->(high:Law {level: 'constitutional'})
        RETURN low.canonical_id, high.canonical_id
        """
        
        invalid_override = conn.execute_query(overriding_query)
        
        # Should be 0 because we created REFERENCES, not OVERRIDDEN_BY
        assert len(invalid_override) == 0, "Found invalid priority override"


@pytest.mark.p1_integration
@pytest.mark.integration
class TestExceptionHandlingValidation:
    """
    Validate exception handling relationships.
    
    Invariant: Exceptions must be properly structured:
    - Exception must reference the rule it excepts
    - Exception must have exception type
    - Exception scope must be defined
    - No circular exceptions
    
    Failure danger: Incorrect exception handling causes wrong rule application.
    """
    
    def test_exception_references_rule(self, neo4j_sample_graph):
        """
        Detect exceptions that don't reference the rule they except.
        
        Every exception should have an EXCEPTS relationship to the rule.
        """
        conn = neo4j_sample_graph
        
        # Create exception without EXCEPTS relationship
        conn.execute_query("""
        CREATE (exception:Article {
            canonical_id: 'article:exception_no_ref',
            article_number: '500',
            text_fa: 'استثنا بدون ارجاع',
            is_exception: true
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.is_exception = true
        AND NOT (a)-[:EXCEPTS]->(:Article)
        RETURN a.canonical_id
        """
        
        exceptions_without_ref = conn.execute_query(query)
        
        assert len(exceptions_without_ref) > 0, "Failed to detect exception without EXCEPTS relationship"
    
    def test_exception_has_type_property(self, neo4j_sample_graph):
        """
        Detect exceptions without exception type.
        
        Exceptions should specify their type (e.g., 'temporary', 'permanent', 'conditional').
        """
        conn = neo4j_sample_graph
        
        # Create exception without type
        conn.execute_query("""
        MATCH (a:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (exception:Article {
            canonical_id: 'article:exception_no_type',
            article_number: '501',
            text_fa: 'استثنا بدون نوع'
        })
        CREATE (exception)-[:EXCEPTS]->(a)
        """)
        
        query = """
        MATCH (exception:Article)-[:EXCEPTS]->(rule:Article)
        WHERE exception.exception_type IS NULL
        RETURN exception.canonical_id
        """
        
        exceptions_without_type = conn.execute_query(query)
        
        assert len(exceptions_without_type) > 0, "Failed to detect exception without type"
    
    def test_exception_scope_defined(self, neo4j_sample_graph):
        """
        Detect exceptions without defined scope.
        
        Exceptions should specify their scope (e.g., 'specific_case', 'time_limited', 'jurisdiction').
        """
        conn = neo4j_sample_graph
        
        # Create exception without scope
        conn.execute_query("""
        MATCH (a:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (exception:Article {
            canonical_id: 'article:exception_no_scope',
            article_number: '502',
            text_fa: 'استثنا بدون دامنه'
        })
        CREATE (exception)-[:EXCEPTS]->(a)
        """)
        
        query = """
        MATCH (exception:Article)-[:EXCEPTS]->(rule:Article)
        WHERE exception.exception_scope IS NULL
        RETURN exception.canonical_id
        """
        
        exceptions_without_scope = conn.execute_query(query)
        
        assert len(exceptions_without_scope) > 0, "Failed to detect exception without scope"
    
    def test_no_circular_exceptions(self, neo4j_sample_graph):
        """
        Detect circular exception relationships (A excepts B, B excepts A).
        
        Circular exceptions create logical contradictions.
        """
        conn = neo4j_sample_graph
        
        # Create circular exception
        conn.execute_query("""
        CREATE (a1:Article {canonical_id: 'article:circle_exc:a', article_number: '600'})
        CREATE (a2:Article {canonical_id: 'article:circle_exc:b', article_number: '601'})
        CREATE (a1)-[:EXCEPTS]->(a2)
        CREATE (a2)-[:EXCEPTS]->(a1)
        """)
        
        query = """
        MATCH (a1:Article)-[:EXCEPTS]->(a2:Article)-[:EXCEPTS]->(a1)
        RETURN a1.canonical_id, a2.canonical_id
        """
        
        circular_exceptions = conn.execute_query(query)
        
        assert len(circular_exceptions) > 0, "Failed to detect circular exceptions"


@pytest.mark.p1_integration
@pytest.mark.integration
class TestPrecedenceCorrectness:
    """
    Validate precedence relationships.
    
    Invariant: Precedence must be logically consistent:
    - Precedence should not create cycles
    - Transitive precedence should be respected
    - Precedence should match legal hierarchy
    
    Failure danger: Incorrect precedence causes wrong rule ordering.
    """
    
    def test_precedence_no_cycles(self, neo4j_sample_graph):
        """
        Detect cycles in precedence relationships.
        
        A > B > C > A is invalid.
        """
        conn = neo4j_sample_graph
        
        # Create precedence cycle
        conn.execute_query("""
        CREATE (a1:Article {canonical_id: 'article:prec:a', article_number: '700'})
        CREATE (a2:Article {canonical_id: 'article:prec:b', article_number: '701'})
        CREATE (a3:Article {canonical_id: 'article:prec:c', article_number: '702'})
        CREATE (a1)-[:PRECEDES]->(a2)
        CREATE (a2)-[:PRECEDES]->(a3)
        CREATE (a3)-[:PRECEDES]->(a1)
        """)
        
        query = """
        MATCH path = (a:Article)-[:PRECEDES*]->(a)
        WHERE length(path) > 0
        RETURN count(DISTINCT a) as cycle_count
        """
        
        cycle_count = conn.execute_query(query)[0]["cycle_count"]
        
        assert cycle_count > 0, "Failed to detect precedence cycles"
    
    def test_transitive_precedence_respected(self, neo4j_sample_graph):
        """
        Detect violations of transitive precedence.
        
        If A > B and B > C, then A should > C.
        """
        conn = neo4j_sample_graph
        
        # Create transitive precedence violation
        conn.execute_query("""
        CREATE (a:Article {canonical_id: 'article:trans:a', article_number: '800'})
        CREATE (b:Article {canonical_id: 'article:trans:b', article_number: '801'})
        CREATE (c:Article {canonical_id: 'article:trans:c', article_number: '802'})
        CREATE (a)-[:PRECEDES]->(b)
        CREATE (b)-[:PRECEDES]->(c)
        """)
        
        # Check if A precedes C (should be true)
        query = """
        MATCH (a:Article {canonical_id: 'article:trans:a'})-[:PRECEDES*]->(c:Article {canonical_id: 'article:trans:c'})
        RETURN count(*) as count
        """
        
        transitive_count = conn.execute_query(query)[0]["count"]
        
        assert transitive_count > 0, "Transitive precedence not respected"
    
    def test_precedence_matches_hierarchy(self, neo4j_sample_graph):
        """
        Detect precedence that violates legal hierarchy.
        
        Lower-level law should not precede higher-level law.
        """
        conn = neo4j_sample_graph
        
        # Create hierarchy-violating precedence
        conn.execute_query("""
        CREATE (ordinary:Law {
            canonical_id: 'law:prec_ordinary',
            title_fa: 'قانون عادی',
            level: 'ordinary'
        })
        CREATE (constitutional:Law {
            canonical_id: 'law:prec_constitutional',
            title_fa: 'قانون اساسی',
            level: 'constitutional'
        })
        CREATE (ordinary)-[:PRECEDES]->(constitutional)
        """)
        
        query = """
        MATCH (ordinary:Law {level: 'ordinary'})-[:PRECEDES]->(constitutional:Law {level: 'constitutional'})
        RETURN ordinary.canonical_id, constitutional.canonical_id
        """
        
        invalid_precedence = conn.execute_query(query)
        
        assert len(invalid_precedence) > 0, "Failed to detect precedence violating hierarchy"
    
    def test_precedence_consistency_with_status(self, neo4j_sample_graph):
        """
        Detect precedence relationships with inconsistent status.
        
        Repealed law should not precede active law.
        """
        conn = neo4j_sample_graph
        
        # Create precedence with inconsistent status
        conn.execute_query("""
        CREATE (repealed:Law {
            canonical_id: 'law:prec_repealed',
            title_fa: 'قانون ملغی',
            status: 'repealed'
        })
        CREATE (active:Law {
            canonical_id: 'law:prec_active',
            title_fa: 'قانون فعال',
            status: 'active'
        })
        CREATE (repealed)-[:PRECEDES]->(active)
        """)
        
        query = """
        MATCH (repealed:Law {status: 'repealed'})-[:PRECEDES]->(active:Law {status: 'active'})
        RETURN repealed.canonical_id, active.canonical_id
        """
        
        inconsistent_precedence = conn.execute_query(query)
        
        assert len(inconsistent_precedence) > 0, "Failed to detect precedence with inconsistent status"

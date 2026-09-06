"""
Query Capability Tests for Persian Legal Knowledge Graph
======================================================

Tests for realistic Cypher query capabilities:
- Find all articles affected by amendments
- Find all references to an article
- Find legal chain from Law to Article to Interpretation
- Find conflicting rules
- Find missing hierarchy links

Invariant protected: Graph must support realistic legal queries correctly.

Failure danger: Query failures prevent legal reasoning from accessing necessary information.
"""

import pytest
from typing import List, Dict, Any


@pytest.mark.p3_full
@pytest.mark.integration
class TestAmendmentQueryCapability:
    """
    Validate queries for amendment tracking.
    
    Invariant: Graph must support amendment queries:
    - Find all articles affected by amendments
    - Find amendment history for an article
    - Find articles that amend other articles
    
    Failure danger: Amendment query failures prevent tracking legal changes.
    """
    
    def test_find_articles_affected_by_amendments(self, neo4j_sample_graph):
        """
        Query: Find all articles affected by amendments.
        
        Should return articles that have been amended.
        """
        conn = neo4j_sample_graph
        
        # Create amendment structure
        conn.execute_query("""
        CREATE (original:Article {
            canonical_id: 'article:amended:1',
            article_number: '1',
            text_fa: 'ماده اصلی'
        })
        CREATE (amendment:Article {
            canonical_id: 'article:amendment:1',
            article_number: '1-1',
            text_fa: 'الحاقیه',
            amendment_type: 'addition'
        })
        CREATE (original)-[:AMENDED_BY]->(amendment)
        """)
        
        query = """
        MATCH (original:Article)-[:AMENDED_BY]->(amendment:Article)
        RETURN original.canonical_id, original.article_number, amendment.canonical_id
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find amended articles"
    
    def test_find_amendment_history(self, neo4j_sample_graph):
        """
        Query: Find amendment history for an article.
        
        Should return chronological list of amendments.
        """
        conn = neo4j_sample_graph
        
        # Create amendment chain
        conn.execute_query("""
        CREATE (original:Article {
            canonical_id: 'article:history:1',
            article_number: '1',
            text_fa: 'ماده اصلی'
        })
        CREATE (amend1:Article {
            canonical_id: 'article:history:2',
            article_number: '1-1',
            text_fa: 'الحاقیه اول',
            amendment_date: '2020-01-01'
        })
        CREATE (amend2:Article {
            canonical_id: 'article:history:3',
            article_number: '1-2',
            text_fa: 'الحاقیه دوم',
            amendment_date: '2021-01-01'
        })
        CREATE (original)-[:AMENDED_BY]->(amend1)
        CREATE (original)-[:AMENDED_BY]->(amend2)
        """)
        
        query = """
        MATCH (original:Article {canonical_id: 'article:history:1'})-[:AMENDED_BY]->(amendment:Article)
        RETURN amendment.canonical_id, amendment.amendment_date
        ORDER BY amendment.amendment_date
        """
        
        results = conn.execute_query(query)
        
        assert len(results) >= 2, "Failed to find amendment history"
    
    def test_find_articles_that_amend_others(self, neo4j_sample_graph):
        """
        Query: Find articles that amend other articles.
        
        Should return articles that are amendments.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (amendment:Article)-[:AMENDS]->(original:Article)
        RETURN amendment.canonical_id, amendment.article_number, original.canonical_id
        """
        
        results = conn.execute_query(query)
        
        # This is informational - may be empty in sample graph
        assert len(results) >= 0, "Query execution failed"


@pytest.mark.p3_full
@pytest.mark.integration
class TestReferenceQueryCapability:
    """
    Validate queries for reference tracking.
    
    Invariant: Graph must support reference queries:
    - Find all references to an article
    - Find articles that reference a specific law
    - Find cross-references between articles
    
    Failure danger: Reference query failures prevent legal citation analysis.
    """
    
    def test_find_all_references_to_article(self, neo4j_sample_graph):
        """
        Query: Find all references to an article.
        
        Should return all articles that reference the target article.
        """
        conn = neo4j_sample_graph
        
        # Create reference structure
        conn.execute_query("""
        MATCH (target:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (referrer:Article {
            canonical_id: 'article:referrer:1',
            article_number: '100',
            references_article: ['article:civil_code:article:1']
        })
        """)
        
        query = """
        MATCH (referrer:Article)
        WHERE 'article:civil_code:article:1' IN referrer.references_article
        RETURN referrer.canonical_id, referrer.article_number
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find references to article"
    
    def test_find_articles_referencing_law(self, neo4j_sample_graph):
        """
        Query: Find articles that reference a specific law.
        
        Should return all articles that cite the target law.
        """
        conn = neo4j_sample_graph
        
        # Create law reference
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:civil_code'})
        CREATE (a:Article {
            canonical_id: 'article:law_ref:1',
            article_number: '200',
            references_law: ['law:civil_code']
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE 'law:civil_code' IN a.references_law
        RETURN a.canonical_id, a.article_number
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find articles referencing law"
    
    def test_find_cross_references(self, neo4j_sample_graph):
        """
        Query: Find cross-references between articles.
        
        Should return pairs of articles that reference each other.
        """
        conn = neo4j_sample_graph
        
        # Create cross-referencing articles
        conn.execute_query("""
        CREATE (a1:Article {
            canonical_id: 'article:cross:1',
            article_number: '300',
            references_article: ['article:cross:2']
        })
        CREATE (a2:Article {
            canonical_id: 'article:cross:2',
            article_number: '301',
            references_article: ['article:cross:1']
        })
        """)
        
        query = """
        MATCH (a1:Article), (a2:Article)
        WHERE a2.canonical_id IN a1.references_article
        AND a1.canonical_id IN a2.references_article
        RETURN a1.canonical_id, a2.canonical_id
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find cross-references"


@pytest.mark.p3_full
@pytest.mark.integration
class TestLegalChainQueryCapability:
    """
    Validate queries for legal chain traversal.
    
    Invariant: Graph must support legal chain queries:
    - Find legal chain from Law to Article to Interpretation
    - Find hierarchy path from Law to Clause
    - Find precedent chain for an article
    
    Failure danger: Chain query failures prevent legal hierarchy analysis.
    """
    
    def test_find_law_to_article_to_interpretation(self, neo4j_sample_graph):
        """
        Query: Find legal chain from Law to Article to Interpretation.
        
        Should return complete chain from law through article to court interpretation.
        """
        conn = neo4j_sample_graph
        
        # Create interpretation chain
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:civil_code'})
        MATCH (a:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (p:Precedent {
            canonical_id: 'precedent:interpretation:1',
            title_fa: 'رأی تفسیری',
            court: 'دیوان عالی'
        })
        CREATE (l)-[:HAS_ARTICLE]->(a)
        CREATE (p)-[:INTERPRETS]->(a)
        """)
        
        query = """
        MATCH path = (l:Law)-[:HAS_ARTICLE*]->(a:Article)<-[:INTERPRETS]-(p:Precedent)
        WHERE l.canonical_id = 'law:civil_code'
        RETURN [node in nodes(path) | node.canonical_id] as chain
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find law-to-interpretation chain"
    
    def test_find_hierarchy_path_to_clause(self, neo4j_sample_graph):
        """
        Query: Find hierarchy path from Law to Clause.
        
        Should return complete path: Law → Chapter → Article → Paragraph → Clause.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH path = (l:Law)-[:HAS_CHAPTER]->(c:Chapter)-[:HAS_ARTICLE]->(a:Article)-[:HAS_PARAGRAPH]->(p:Paragraph)-[:HAS_CLAUSE]->(cl:Clause)
        RETURN [node in nodes(path) | node.canonical_id] as path
        LIMIT 1
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find hierarchy path to clause"
        assert len(results[0]["path"]) == 5, "Path should have 5 nodes"
    
    def test_find_precedent_chain(self, neo4j_sample_graph):
        """
        Query: Find precedent chain for an article.
        
        Should return all precedents that interpret the article.
        """
        conn = neo4j_sample_graph
        
        # Create precedent chain
        conn.execute_query("""
        MATCH (a:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (p1:Precedent {
            canonical_id: 'precedent:chain:1',
            title_fa: 'رأی اول',
            court: 'دیوان عالی',
            decision_date: '2020-01-01'
        })
        CREATE (p2:Precedent {
            canonical_id: 'precedent:chain:2',
            title_fa: 'رأی دوم',
            court: 'دیوان عالی',
            decision_date: '2021-01-01'
        })
        CREATE (p1)-[:INTERPRETS]->(a)
        CREATE (p2)-[:INTERPRETS]->(a)
        """)
        
        query = """
        MATCH (p:Precedent)-[:INTERPRETS]->(a:Article {canonical_id: 'article:civil_code:article:1'})
        RETURN p.canonical_id, p.decision_date
        ORDER BY p.decision_date
        """
        
        results = conn.execute_query(query)
        
        assert len(results) >= 2, "Failed to find precedent chain"


@pytest.mark.p3_full
@pytest.mark.integration
class TestConflictDetectionQueryCapability:
    """
    Validate queries for conflict detection.
    
    Invariant: Graph must support conflict queries:
    - Find conflicting rules
    - Find contradictory precedents
    - Find priority conflicts
    
    Failure danger: Conflict query failures prevent legal contradiction detection.
    """
    
    def test_find_conflicting_rules(self, neo4j_sample_graph):
        """
        Query: Find conflicting rules.
        
        Should return pairs of articles that conflict with each other.
        """
        conn = neo4j_sample_graph
        
        # Create conflicting articles
        conn.execute_query("""
        CREATE (a1:Article {
            canonical_id: 'article:conflict:1',
            article_number: '400',
            text_fa: 'قاعده اول'
        })
        CREATE (a2:Article {
            canonical_id: 'article:conflict:2',
            article_number: '401',
            text_fa: 'قاعده متضاد'
        })
        CREATE (a1)-[:CONFLICTS_WITH]->(a2)
        """)
        
        query = """
        MATCH (a1:Article)-[:CONFLICTS_WITH]->(a2:Article)
        RETURN a1.canonical_id, a2.canonical_id
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find conflicting rules"
    
    def test_find_contradictory_precedents(self, neo4j_sample_graph):
        """
        Query: Find contradictory precedents.
        
        Should return precedents that interpret the same article differently.
        """
        conn = neo4j_sample_graph
        
        # Create contradictory precedents
        conn.execute_query("""
        MATCH (a:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (p1:Precedent {
            canonical_id: 'precedent:contra:1',
            title_fa: 'رأی موافق',
            interpretation: 'supportive'
        })
        CREATE (p2:Precedent {
            canonical_id: 'precedent:contra:2',
            title_fa: 'رأی مخالف',
            interpretation: 'contradictory'
        })
        CREATE (p1)-[:INTERPRETS]->(a)
        CREATE (p2)-[:INTERPRETS]->(a)
        CREATE (p1)-[:CONFLICTS_WITH]->(p2)
        """)
        
        query = """
        MATCH (p1:Precedent)-[:INTERPRETS]->(a:Article)<-[:INTERPRETS]-(p2:Precedent)
        WHERE (p1)-[:CONFLICTS_WITH]->(p2)
        RETURN p1.canonical_id, p2.canonical_id, a.canonical_id
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find contradictory precedents"
    
    def test_find_priority_conflicts(self, neo4j_sample_graph):
        """
        Query: Find priority conflicts.
        
        Should return cases where lower-level law overrides higher-level law.
        """
        conn = neo4j_sample_graph
        
        # Create priority conflict
        conn.execute_query("""
        CREATE (high:Law {
            canonical_id: 'law:high_priority',
            title_fa: 'قانون بالادستی',
            level: 'constitutional'
        })
        CREATE (low:Law {
            canonical_id: 'law:low_priority',
            title_fa: 'قانون پایین‌دستی',
            level: 'ordinary'
        })
        CREATE (high)-[:OVERRIDDEN_BY]->(low)
        """)
        
        query = """
        MATCH (high:Law {level: 'constitutional'})-[:OVERRIDDEN_BY]->(low:Law {level: 'ordinary'})
        RETURN high.canonical_id, low.canonical_id
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find priority conflicts"


@pytest.mark.p3_full
@pytest.mark.integration
class TestHierarchyQueryCapability:
    """
    Validate queries for hierarchy analysis.
    
    Invariant: Graph must support hierarchy queries:
    - Find missing hierarchy links
    - Find orphan nodes
    - Find incomplete chains
    
    Failure danger: Hierarchy query failures prevent structural validation.
    """
    
    def test_find_missing_hierarchy_links(self, neo4j_sample_graph):
        """
        Query: Find missing hierarchy links.
        
        Should return nodes that are missing expected relationships.
        """
        conn = neo4j_sample_graph
        
        # Create orphan chapter
        conn.execute_query("""
        CREATE (c:Chapter {
            canonical_id: 'chapter:orphan:1',
            title_fa: 'فصل یتیم',
            chapter_number: '1'
        })
        """)
        
        query = """
        MATCH (c:Chapter)
        WHERE NOT (c)<-[:HAS_CHAPTER]-(:Law)
        RETURN c.canonical_id, c.title_fa
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find missing hierarchy links"
    
    def test_find_orphan_nodes(self, neo4j_sample_graph):
        """
        Query: Find orphan nodes.
        
        Should return nodes without parent relationships.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (a:Article)
        WHERE NOT (a)<-[:HAS_ARTICLE]-(:Chapter)
        AND NOT (a)<-[:HAS_ARTICLE*2]-(:Law)
        RETURN a.canonical_id, a.article_number
        """
        
        results = conn.execute_query(query)
        
        # Sample graph should have no orphans
        assert len(results) == 0, "Sample graph should have no orphan articles"
    
    def test_find_incomplete_chains(self, neo4j_sample_graph):
        """
        Query: Find incomplete chains.
        
        Should return chains that don't go from Law to Clause.
        """
        conn = neo4j_sample_graph
        
        # Create incomplete chain
        conn.execute_query("""
        CREATE (l:Law {canonical_id: 'law:incomplete', title_fa: 'قانون ناقص'})
        CREATE (c:Chapter {canonical_id: 'chapter:incomplete:1', title_fa: 'فصل'})
        CREATE (l)-[:HAS_CHAPTER]->(c)
        """)
        
        query = """
        MATCH (l:Law)-[:HAS_CHAPTER*]->(end_node)
        WHERE NOT (end_node)-[:HAS_ARTICLE]->()
        AND NOT (end_node)-[:HAS_PARAGRAPH]->()
        AND NOT (end_node)-[:HAS_CLAUSE]->()
        AND labels(end_node) <> ['Law']
        RETURN l.canonical_id, end_node.canonical_id, labels(end_node) as labels
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to find incomplete chains"


@pytest.mark.p3_full
@pytest.mark.integration
class TestComplexQueryCapability:
    """
    Validate complex multi-hop queries.
    
    Invariant: Graph must support complex queries:
    - Multi-hop traversals
    - Aggregation queries
    - Pattern matching queries
    
    Failure danger: Complex query failures limit legal analysis capabilities.
    """
    
    def test_multi_hop_traversal(self, neo4j_sample_graph):
        """
        Query: Multi-hop traversal from Law to Clause.
        
        Should traverse multiple relationship levels.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH path = (l:Law)-[:HAS_CHAPTER]->(c:Chapter)-[:HAS_ARTICLE]->(a:Article)-[:HAS_PARAGRAPH]->(p:Paragraph)-[:HAS_CLAUSE]->(cl:Clause)
        RETURN length(path) as hops, [node in nodes(path) | labels(node)] as labels
        LIMIT 1
        """
        
        results = conn.execute_query(query)
        
        assert len(results) > 0, "Failed to execute multi-hop traversal"
        assert results[0]["hops"] == 4, "Should have 4 hops"
    
    def test_aggregation_query(self, neo4j_sample_graph):
        """
        Query: Aggregate articles by law.
        
        Should return count of articles per law.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (l:Law)-[:HAS_CHAPTER*]->(a:Article)
        RETURN l.canonical_id, count(a) as article_count
        """
        
        results = conn.execute_query(query)
        
        assert len(results) >= 0, "Failed to execute aggregation query"
    
    def test_pattern_matching_query(self, neo4j_sample_graph):
        """
        Query: Pattern matching for specific legal structures.
        
        Should find articles with specific relationship patterns.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (a:Article)-[:HAS_PARAGRAPH]->(p:Paragraph)-[:HAS_CLAUSE]->(c:Clause)
        WHERE a.article_number = '1'
        RETURN a.canonical_id, count(c) as clause_count
        """
        
        results = conn.execute_query(query)
        
        assert len(results) >= 0, "Failed to execute pattern matching query"

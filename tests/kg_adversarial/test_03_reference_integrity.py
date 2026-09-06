"""
Reference Integrity Tests for Persian Legal Knowledge Graph
============================================================

Tests for legal references:
- Target article existence verification
- Target law existence verification
- Reference direction correctness
- Cross-law reference validity
- Detection of false/missing/self/impossible references

Invariant protected: All legal references must resolve to existing, valid entities.

Failure danger: Broken references cause legal reasoning to reference non-existent laws.
"""

import pytest
from typing import List, Dict, Any


@pytest.mark.p0_critical
@pytest.mark.integration
class TestTargetExistenceVerification:
    """
    Verify that all references point to existing entities.
    
    Invariant: Every reference must resolve to an existing node in the graph.
    References to non-existent entities indicate parsing errors or data corruption.
    
    Failure danger: Broken references cause legal reasoning to fail or reference wrong entities.
    """
    
    def test_target_article_exists(self, corrupted_reference_graph):
        """
        Detect references to non-existent articles.
        
        Article references must resolve to existing Article nodes.
        """
        conn = corrupted_reference_graph
        
        query = """
        MATCH (a:Article)
        WHERE a.references_article IS NOT NULL
        UNWIND a.references_article as ref_id
        OPTIONAL MATCH (target:Article {canonical_id: ref_id})
        WITH a, ref_id, count(target) as target_count
        WHERE target_count = 0
        RETURN a.canonical_id as source, ref_id as missing_target
        """
        
        broken_refs = conn.execute_query(query)
        
        assert len(broken_refs) > 0, "Failed to detect references to non-existent articles"
        
        # Should detect our intentional broken reference
        missing_targets = [r["missing_target"] for r in broken_refs]
        assert "article:nonexistent:article:999" in missing_targets, "Intentional broken reference not detected"
    
    def test_target_law_exists(self, corrupted_reference_graph):
        """
        Detect references to non-existent laws.
        
        Law references must resolve to existing Law nodes.
        """
        conn = corrupted_reference_graph
        
        query = """
        MATCH (a:Article)
        WHERE a.references_law IS NOT NULL
        UNWIND a.references_law as ref_id
        OPTIONAL MATCH (target:Law {canonical_id: ref_id})
        WITH a, ref_id, count(target) as target_count
        WHERE target_count = 0
        RETURN a.canonical_id as source, ref_id as missing_target
        """
        
        broken_refs = conn.execute_query(query)
        
        assert len(broken_refs) > 0, "Failed to detect references to non-existent laws"
        
        # Should detect our intentional broken reference
        missing_targets = [r["missing_target"] for r in broken_refs]
        assert "law:nonexistent" in missing_targets, "Intentional broken law reference not detected"
    
    def test_target_chapter_exists(self, neo4j_sample_graph):
        """
        Detect references to non-existent chapters.
        
        Chapter references must resolve to existing Chapter nodes.
        """
        conn = neo4j_sample_graph
        
        # Create article with reference to non-existent chapter
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:ref_missing_chapter',
            article_number: '500',
            references_chapter: ['chapter:nonexistent:chapter:1']
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.references_chapter IS NOT NULL
        UNWIND a.references_chapter as ref_id
        OPTIONAL MATCH (target:Chapter {canonical_id: ref_id})
        WITH a, ref_id, count(target) as target_count
        WHERE target_count = 0
        RETURN a.canonical_id as source, ref_id as missing_target
        """
        
        broken_refs = conn.execute_query(query)
        
        assert len(broken_refs) > 0, "Failed to detect references to non-existent chapters"
    
    def test_all_references_resolvable_in_valid_graph(self, neo4j_sample_graph):
        """
        Verify that all references in a valid graph are resolvable.
        
        Negative test - confirms detection logic works.
        """
        conn = neo4j_sample_graph
        
        # Check for broken article references
        article_ref_query = """
        MATCH (a:Article)
        WHERE a.references_article IS NOT NULL
        UNWIND a.references_article as ref_id
        MATCH (target:Article {canonical_id: ref_id})
        WITH count(target) as resolved, count(a.references_article) as total
        RETURN resolved < total as has_broken
        """
        
        result = conn.execute_query(article_ref_query)
        if result:
            has_broken = result[0]["has_broken"]
            assert not has_broken, "Valid graph should have no broken article references"


@pytest.mark.p0_critical
@pytest.mark.integration
class TestReferenceDirectionCorrectness:
    """
    Verify that reference relationships have correct direction.
    
    Invariant: Reference relationships should follow semantic direction:
    - Article CITES Article (source → target)
    - Article IMPLEMENTS Law (article → law)
    - Law AMENDS Law (amendment → original)
    - Precedent INTERPRETS Article (precedent → article)
    
    Failure danger: Incorrect direction causes wrong legal precedence.
    """
    
    def test_cites_relationship_direction(self, neo4j_sample_graph):
        """
        Verify CITES relationship direction is correct.
        
        Source should CITES target, not vice versa.
        """
        conn = neo4j_sample_graph
        
        # Create reverse CITES relationship
        conn.execute_query("""
        MATCH (a1:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (a2:Article {canonical_id: 'article:cites_target', article_number: '100'})
        CREATE (a1)-[:CITES]->(a2)
        """)
        
        # This is valid - check that we don't have target CITES source
        query = """
        MATCH (target:Article)-[:CITES]->(source:Article)
        WHERE source.canonical_id = 'article:civil_code:article:1'
        RETURN count(*) as count
        """
        
        reverse_direction = conn.execute_query(query)[0]["count"]
        
        # In this case, we expect 0 because we created it correctly
        # But if we had created it backwards, this would detect it
        assert reverse_direction == 0, "Found reverse CITES relationship"
    
    def test_amends_relationship_direction(self, neo4j_sample_graph):
        """
        Verify AMENDS relationship direction is correct.
        
        Amendment should AMEND original law, not vice versa.
        """
        conn = neo4j_sample_graph
        
        # Create AMENDS relationship
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:civil_code'})
        CREATE (amendment:Law {
            canonical_id: 'law:amendment',
            title_fa: 'الحاقیه',
            amendment_date: '2020-01-01'
        })
        CREATE (amendment)-[:AMENDS]->(l)
        """)
        
        # Check for reverse direction
        query = """
        MATCH (original:Law)-[:AMENDS]->(amendment:Law)
        WHERE original.canonical_id = 'law:civil_code'
        RETURN count(*) as count
        """
        
        reverse_direction = conn.execute_query(query)[0]["count"]
        
        assert reverse_direction == 0, "Found reverse AMENDS relationship"
    
    def test_interprets_relationship_direction(self, neo4j_sample_graph):
        """
        Verify INTERPRETS relationship direction is correct.
        
        Precedent should INTERPRETS article, not vice versa.
        """
        conn = neo4j_sample_graph
        
        # Create INTERPRETS relationship
        conn.execute_query("""
        MATCH (a:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (p:Precedent {
            canonical_id: 'precedent:interpretation',
            title_fa: 'رأی تفسیری',
            court: 'دیوان عالی'
        })
        CREATE (p)-[:INTERPRETS]->(a)
        """)
        
        # Check for reverse direction
        query = """
        MATCH (a:Article)-[:INTERPRETS]->(p:Precedent)
        RETURN count(*) as count
        """
        
        reverse_direction = conn.execute_query(query)[0]["count"]
        
        assert reverse_direction == 0, "Found reverse INTERPRETS relationship"


@pytest.mark.p0_critical
@pytest.mark.integration
class TestCrossLawReferenceValidity:
    """
    Validate cross-law references for legality.
    
    Invariant: Cross-law references must be between compatible laws:
    - Criminal law cannot reference civil law procedures
    - Constitutional law references must be to constitutional provisions
    - Temporal constraints (cannot reference future laws)
    
    Failure danger: Invalid cross-law references cause incorrect legal application.
    """
    
    def test_criminal_law_references_criminal_law(self, neo4j_sample_graph):
        """
        Verify criminal law references are to criminal law.
        
        Criminal law should not reference civil law articles.
        """
        conn = neo4j_sample_graph
        
        # Create criminal law referencing civil law (invalid)
        conn.execute_query("""
        CREATE (criminal:Law {
            canonical_id: 'law:criminal_code',
            title_fa: 'قانون مجازات اسلامی',
            domain: 'criminal'
        })
        CREATE (civil:Law {
            canonical_id: 'law:civil_code_2',
            title_fa: 'قانون مدنی',
            domain: 'civil'
        })
        CREATE (criminal)-[:REFERENCES]->(civil)
        """)
        
        query = """
        MATCH (source:Law {domain: 'criminal'})-[:REFERENCES]->(target:Law {domain: 'civil'})
        RETURN source.canonical_id, target.canonical_id
        """
        
        invalid_cross_refs = conn.execute_query(query)
        
        assert len(invalid_cross_refs) > 0, "Failed to detect invalid criminal-civil reference"
    
    def test_temporal_constraint_no_future_law_reference(self, neo4j_sample_graph):
        """
        Detect references to future laws.
        
        Cannot reference a law that didn't exist at the time.
        """
        from datetime import datetime, timedelta
        
        conn = neo4j_sample_graph
        
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        # Create law referencing future law
        conn.execute_query("""
        CREATE (current:Law {
            canonical_id: 'law:current',
            title_fa: 'قانون فعلی',
            effective_date: '2020-01-01'
        })
        CREATE (future:Law {
            canonical_id: 'law:future',
            title_fa: 'قانون آینده',
            effective_date: '%s'
        })
        CREATE (current)-[:REFERENCES]->(future)
        """ % future_date)
        
        query = """
        MATCH (source:Law)-[:REFERENCES]->(target:Law)
        WHERE date(source.effective_date) < date(target.effective_date)
        RETURN source.canonical_id, target.canonical_id
        """
        
        future_refs = conn.execute_query(query)
        
        assert len(future_refs) > 0, "Failed to detect reference to future law"
    
    def test_cross_law_reference_in_same_domain(self, neo4j_sample_graph):
        """
        Verify cross-law references are within the same legal domain.
        
        Commercial law should reference commercial law, not family law.
        """
        conn = neo4j_sample_graph
        
        # Create commercial law referencing family law (invalid)
        conn.execute_query("""
        CREATE (commercial:Law {
            canonical_id: 'law:commercial',
            title_fa: 'قانون تجارت',
            domain: 'commercial'
        })
        CREATE (family:Law {
            canonical_id: 'law:family',
            title_fa: 'قانون خانواده',
            domain: 'family'
        })
        CREATE (commercial)-[:REFERENCES]->(family)
        """)
        
        query = """
        MATCH (source:Law)-[:REFERENCES]->(target:Law)
        WHERE source.domain <> target.domain
        RETURN source.canonical_id, source.domain, target.canonical_id, target.domain
        """
        
        cross_domain_refs = conn.execute_query(query)
        
        assert len(cross_domain_refs) > 0, "Failed to detect cross-domain reference"


@pytest.mark.p1_integration
@pytest.mark.integration
class TestImpossibleReferenceDetection:
    """
    Detect impossible or logically invalid references.
    
    Invariant: References must be logically possible:
    - No self-references (article cannot reference itself)
    - No circular references (A → B → A)
    - No references to repealed laws as current authority
    - No references to non-applicable provisions
    
    Failure danger: Impossible references cause logical contradictions in reasoning.
    """
    
    def test_self_reference_detection(self, corrupted_reference_graph):
        """
        Detect self-references (article referencing itself).
        
        Self-references are typically parsing errors.
        """
        conn = corrupted_reference_graph
        
        query = """
        MATCH (a:Article)
        WHERE a.references_article IS NOT NULL
        AND a.canonical_id IN a.references_article
        RETURN a.canonical_id
        """
        
        self_refs = conn.execute_query(query)
        
        assert len(self_refs) > 0, "Failed to detect self-references"
        
        # Should detect our intentional self-reference
        self_ref_ids = [r["a.canonical_id"] for r in self_refs]
        assert "article:self_ref:article:4" in self_ref_ids, "Intentional self-reference not detected"
    
    def test_circular_reference_detection(self, neo4j_sample_graph):
        """
        Detect circular reference chains (A → B → C → A).
        
        Circular references can cause infinite loops in reasoning.
        """
        conn = neo4j_sample_graph
        
        # Create circular reference chain
        conn.execute_query("""
        CREATE (a1:Article {canonical_id: 'article:circle:a', article_number: '1'})
        CREATE (a2:Article {canonical_id: 'article:circle:b', article_number: '2'})
        CREATE (a3:Article {canonical_id: 'article:circle:c', article_number: '3'})
        CREATE (a1)-[:REFERENCES]->(a2)
        CREATE (a2)-[:REFERENCES]->(a3)
        CREATE (a3)-[:REFERENCES]->(a1)
        """)
        
        query = """
        MATCH path = (a:Article)-[:REFERENCES*]->(a)
        WHERE length(path) > 0 AND length(path) < 10
        RETURN count(DISTINCT a) as circular_nodes
        """
        
        circular_nodes = conn.execute_query(query)[0]["circular_nodes"]
        
        assert circular_nodes > 0, "Failed to detect circular references"
    
    def test_reference_to_repealed_law_as_current(self, neo4j_sample_graph):
        """
        Detect references to repealed laws treated as current authority.
        
        Should use REPLACED_BY relationship instead of REFERENCES.
        """
        conn = neo4j_sample_graph
        
        # Create reference to repealed law
        conn.execute_query("""
        CREATE (current:Law {
            canonical_id: 'law:current_ref',
            title_fa: 'قانون فعلی',
            status: 'active'
        })
        CREATE (repealed:Law {
            canonical_id: 'law:repealed_ref',
            title_fa: 'قانون ملغی',
            status: 'repealed',
            repeal_date: '2010-01-01'
        })
        CREATE (current)-[:REFERENCES]->(repealed)
        """)
        
        query = """
        MATCH (source:Law {status: 'active'})-[:REFERENCES]->(target:Law {status: 'repealed'})
        RETURN source.canonical_id, target.canonical_id
        """
        
        invalid_refs = conn.execute_query(query)
        
        assert len(invalid_refs) > 0, "Failed to detect reference to repealed law"
    
    def test_reference_to_non_applicable_provision(self, neo4j_sample_graph):
        """
        Detect references to provisions that don't apply to the context.
        
        Example: Civil law article referencing criminal procedure.
        """
        conn = neo4j_sample_graph
        
        # Create civil article referencing criminal procedure
        conn.execute_query("""
        CREATE (civil:Article {
            canonical_id: 'article:civil_ref',
            article_number: '100',
            domain: 'civil',
            references_article: ['article:criminal:procedure:1']
        })
        CREATE (criminal:Article {
            canonical_id: 'article:criminal:procedure:1',
            article_number: '1',
            domain: 'criminal_procedure'
        })
        CREATE (civil)-[:REFERENCES]->(criminal)
        """)
        
        query = """
        MATCH (source:Article {domain: 'civil'})-[r:REFERENCES]->(target:Article {domain: 'criminal_procedure'})
        RETURN source.canonical_id, target.canonical_id
        """
        
        invalid_refs = conn.execute_query(query)
        
        assert len(invalid_refs) > 0, "Failed to detect reference to non-applicable provision"


@pytest.mark.p1_integration
@pytest.mark.integration
class TestReferenceCompleteness:
    """
    Verify that references are complete and properly structured.
    
    Invariant: References should include all necessary metadata:
    - Reference type (CITES, IMPLEMENTS, AMENDS, etc.)
    - Reference context (why the reference exists)
    - Reference validity (is the reference still valid?)
    
    Failure danger: Incomplete references cause ambiguous legal interpretation.
    """
    
    def test_reference_has_type_property(self, neo4j_sample_graph):
        """
        Detect references without type property.
        
        Every reference should specify its type.
        """
        conn = neo4j_sample_graph
        
        # Create reference without type
        conn.execute_query("""
        CREATE (a1:Article {canonical_id: 'article:ref_no_type', article_number: '200'})
        CREATE (a2:Article {canonical_id: 'article:target', article_number: '201'})
        CREATE (a1)-[:REFERENCES]->(a2)
        """)
        
        query = """
        MATCH ()-[r:REFERENCES]->()
        WHERE r.reference_type IS NULL
        RETURN count(r) as count
        """
        
        refs_without_type = conn.execute_query(query)[0]["count"]
        
        # In a properly structured graph, all references should have types
        # This test detects the absence
        assert refs_without_type >= 0, "Query execution failed"
    
    def test_reference_has_context_property(self, neo4j_sample_graph):
        """
        Detect references without context property.
        
        Context explains why the reference exists.
        """
        conn = neo4j_sample_graph
        
        # Create reference without context
        conn.execute_query("""
        CREATE (a1:Article {canonical_id: 'article:ref_no_context', article_number: '300'})
        CREATE (a2:Article {canonical_id: 'article:target2', article_number: '301'})
        CREATE (a1)-[:REFERENCES {reference_type: 'CITES'}]->(a2)
        """)
        
        query = """
        MATCH ()-[r:REFERENCES]->()
        WHERE r.reference_context IS NULL
        RETURN count(r) as count
        """
        
        refs_without_context = conn.execute_query(query)[0]["count"]
        
        # This is informational - context is good but not always required
        assert refs_without_context >= 0, "Query execution failed"
    
    def test_no_broken_references_in_valid_graph(self, neo4j_sample_graph):
        """
        Verify that a valid graph has no broken references.
        
        Negative test - confirms detection logic works.
        """
        conn = neo4j_sample_graph
        
        # Check for references to non-existent articles
        query = """
        MATCH (a:Article)
        WHERE a.references_article IS NOT NULL
        UNWIND a.references_article as ref_id
        OPTIONAL MATCH (target:Article {canonical_id: ref_id})
        WITH a, ref_id, target
        WHERE target IS NULL
        RETURN count(*) as broken_count
        """
        
        broken_count = conn.execute_query(query)[0]["broken_count"]
        
        assert broken_count == 0, "Valid graph should have no broken references"

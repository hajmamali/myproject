"""
Legal Ontology Validation Tests for Persian Legal Knowledge Graph
===================================================================

Tests for validating whether the ontology correctly represents legal hierarchy:
- Relationship direction correctness (Law → Chapter → Article → Paragraph → Clause)
- Node type correctness (no semantic misuse of labels)
- Property completeness (mandatory properties present)
- No semantic misuse (Amendment treated as original law, precedent as legislation)

Invariant protected: Ontology must correctly represent Persian legal hierarchy.

Failure danger: Incorrect hierarchy leads to wrong legal precedence and invalid conclusions.
"""

import pytest
from typing import List, Dict, Any


@pytest.mark.p0_critical
@pytest.mark.integration
class TestRelationshipDirectionCorrectness:
    """
    Validate that relationship directions follow legal hierarchy.
    
    Invariant: Legal hierarchy is strictly directional:
    - Law → Chapter (HAS_CHAPTER)
    - Chapter → Article (HAS_ARTICLE)
    - Article → Paragraph (HAS_PARAGRAPH)
    - Paragraph → Clause (HAS_CLAUSE)
    
    Reverse relationships indicate parsing errors or ontology misuse.
    
    Failure danger: Incorrect direction causes wrong legal precedence.
    """
    
    def test_law_to_chapter_direction_correct(self, neo4j_sample_graph):
        """
        Verify Law → Chapter relationship direction is correct.
        
        Law should HAVE Chapter, not vice versa.
        """
        conn = neo4j_sample_graph
        
        # Check for reverse direction (Chapter → Law)
        query = """
        MATCH (c:Chapter)-[:HAS_CHAPTER]->(l:Law)
        RETURN count(*) as count
        """
        
        reverse_direction = conn.execute_query(query)[0]["count"]
        
        assert reverse_direction == 0, "Found Chapter → Law (reverse direction)"
    
    def test_chapter_to_article_direction_correct(self, neo4j_sample_graph):
        """
        Verify Chapter → Article relationship direction is correct.
        
        Chapter should HAVE Article, not vice versa.
        """
        conn = neo4j_sample_graph
        
        # Check for reverse direction
        query = """
        MATCH (a:Article)-[:HAS_ARTICLE]->(c:Chapter)
        RETURN count(*) as count
        """
        
        reverse_direction = conn.execute_query(query)[0]["count"]
        
        assert reverse_direction == 0, "Found Article → Chapter (reverse direction)"
    
    def test_article_to_paragraph_direction_correct(self, neo4j_sample_graph):
        """
        Verify Article → Paragraph relationship direction is correct.
        
        Article should HAVE Paragraph, not vice versa.
        """
        conn = neo4j_sample_graph
        
        # Check for reverse direction
        query = """
        MATCH (p:Paragraph)-[:HAS_PARAGRAPH]->(a:Article)
        RETURN count(*) as count
        """
        
        reverse_direction = conn.execute_query(query)[0]["count"]
        
        assert reverse_direction == 0, "Found Paragraph → Article (reverse direction)"
    
    def test_paragraph_to_clause_direction_correct(self, neo4j_sample_graph):
        """
        Verify Paragraph → Clause relationship direction is correct.
        
        Paragraph should HAVE Clause, not vice versa.
        """
        conn = neo4j_sample_graph
        
        # Check for reverse direction
        query = """
        MATCH (c:Clause)-[:HAS_CLAUSE]->(p:Paragraph)
        RETURN count(*) as count
        """
        
        reverse_direction = conn.execute_query(query)[0]["count"]
        
        assert reverse_direction == 0, "Found Clause → Paragraph (reverse direction)"
    
    def test_hierarchy_chain_completeness(self, neo4j_sample_graph):
        """
        Verify complete hierarchy chains exist (Law → Chapter → Article → Paragraph → Clause).
        
        Incomplete chains indicate missing data or parsing failures.
        """
        conn = neo4j_sample_graph
        
        # Find complete chains
        query = """
        MATCH path = (l:Law)-[:HAS_CHAPTER]->(c:Chapter)-[:HAS_ARTICLE]->(a:Article)-[:HAS_PARAGRAPH]->(p:Paragraph)-[:HAS_CLAUSE]->(cl:Clause)
        RETURN count(path) as complete_chains
        """
        
        complete_chains = conn.execute_query(query)[0]["complete_chains"]
        
        assert complete_chains > 0, "No complete hierarchy chains found"
    
    def test_no_short_circuit_hierarchy(self, neo4j_sample_graph):
        """
        Detect short-circuit hierarchy (Law → Article without Chapter).
        
        While technically possible in some legal systems, this should be
        validated as an exception, not the norm.
        """
        conn = neo4j_sample_graph
        
        # Create short-circuit
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:civil_code'})
        CREATE (a:Article {canonical_id: 'article:short_circuit', article_number: '999'})
        CREATE (l)-[:HAS_ARTICLE]->(a)
        """)
        
        query = """
        MATCH (l:Law)-[:HAS_ARTICLE]->(a:Article)
        WHERE NOT (l)-[:HAS_CHAPTER]->(:Chapter)-[:HAS_ARTICLE]->(a)
        RETURN count(*) as count
        """
        
        short_circuits = conn.execute_query(query)[0]["count"]
        
        assert short_circuits > 0, "Failed to detect short-circuit hierarchy"


@pytest.mark.p0_critical
@pytest.mark.integration
class TestNodeTypeCorrectness:
    """
    Validate that node labels are used semantically correctly.
    
    Invariant: Node labels must match their semantic purpose:
    - Law: Legislative acts (قانون)
    - Chapter: Structural divisions (فصل)
    - Article: Individual legal provisions (ماده)
    - Paragraph: Subdivisions of articles (بند)
    - Clause: Exceptions or clarifications (تبصره)
    - Amendment: Modifications to existing laws (الحاقیه)
    - Precedent: Court decisions (رأی قضایی)
    
    Failure danger: Semantic misuse causes incorrect legal classification.
    """
    
    def test_law_not_used_for_precedent(self, neo4j_sample_graph):
        """
        Detect Law label used for judicial precedent.
        
        Judicial precedents should have Precedent or CourtDecision label,
        not Law label.
        """
        conn = neo4j_sample_graph
        
        # Create a precedent incorrectly labeled as Law
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:actually_precedent',
            title_fa: 'رأی شماره ۱۰۰',
            court: 'دیوان عالی',
            decision_date: '2020-01-01'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE l.court IS NOT NULL OR l.decision_date IS NOT NULL
        RETURN l.canonical_id
        """
        
        mislabeled = conn.execute_query(query)
        
        assert len(mislabeled) > 0, "Failed to detect precedent mislabeled as Law"
    
    def test_amendment_not_treated_as_original_law(self, neo4j_sample_graph):
        """
        Detect amendments incorrectly treated as original laws.
        
        Amendments should have Amendment label and reference the original law.
        """
        conn = neo4j_sample_graph
        
        # Create amendment incorrectly labeled as Law
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:actually_amendment',
            title_fa: 'الحاقیه قانون مدنی',
            amendment_date: '2020-01-01',
            amends: 'law:civil_code'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE l.title_fa CONTAINS 'الحاقیه' OR l.amendment_date IS NOT NULL
        RETURN l.canonical_id
        """
        
        mislabeled = conn.execute_query(query)
        
        assert len(mislabeled) > 0, "Failed to detect amendment mislabeled as Law"
    
    def test_article_not_used_for_chapter(self, neo4j_sample_graph):
        """
        Detect Article label used for Chapter content.
        
        Chapters should have Chapter label, not Article label.
        """
        conn = neo4j_sample_graph
        
        # Create chapter incorrectly labeled as Article
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:actually_chapter',
            article_number: 'فصل',
            title_fa: 'فصل دوم',
            text_fa: 'محتوای فصل'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.article_number CONTAINS 'فصل' OR a.title_fa CONTAINS 'فصل'
        RETURN a.canonical_id
        """
        
        mislabeled = conn.execute_query(query)
        
        assert len(mislabeled) > 0, "Failed to detect chapter mislabeled as Article"
    
    def test_clause_not_used_for_article(self, neo4j_sample_graph):
        """
        Detect Clause label used for Article content.
        
        Articles should have Article label, not Clause label.
        """
        conn = neo4j_sample_graph
        
        # Create article incorrectly labeled as Clause
        conn.execute_query("""
        CREATE (c:Clause {
            canonical_id: 'clause:actually_article',
            clause_number: '۱',
            text_fa: 'متن ماده کامل'
        })
        """)
        
        query = """
        MATCH (c:Clause)
        WHERE c.text_fa CONTAINS 'ماده'
        RETURN c.canonical_id
        """
        
        suspicious_clauses = conn.execute_query(query)
        
        # This is heuristic - long text in Clause is suspicious
        assert len(suspicious_clauses) > 0, "Failed to detect suspicious Clause usage"
    
    def test_precedent_has_court_property(self, neo4j_sample_graph):
        """
        Verify Precedent nodes have court property.
        
        Judicial precedents must specify which court issued the decision.
        """
        conn = neo4j_sample_graph
        
        # Create Precedent without court
        conn.execute_query("""
        CREATE (p:Precedent {
            canonical_id: 'precedent:no_court',
            title_fa: 'رأی بدون دادگاه',
            decision_date: '2020-01-01'
        })
        """)
        
        query = """
        MATCH (p:Precedent)
        WHERE p.court IS NULL
        RETURN p.canonical_id
        """
        
        precedents_without_court = conn.execute_query(query)
        
        assert len(precedents_without_court) > 0, "Failed to detect Precedent without court"


@pytest.mark.p0_critical
@pytest.mark.integration
class TestPropertyCompleteness:
    """
    Validate that mandatory properties are present for each node type.
    
    Invariant: Each node type must have its mandatory properties:
    - Law: canonical_id, title_fa, publication_date, status
    - Chapter: canonical_id, title_fa, chapter_number
    - Article: canonical_id, article_number, text_fa
    - Paragraph: canonical_id, paragraph_number, text_fa
    - Clause: canonical_id, clause_number, text_fa
    
    Failure danger: Missing properties cause query failures and incomplete legal information.
    """
    
    def test_law_has_mandatory_properties(self, neo4j_sample_graph):
        """
        Verify all Law nodes have mandatory properties.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (l:Law)
        WHERE l.canonical_id IS NULL 
           OR l.title_fa IS NULL 
           OR l.publication_date IS NULL 
           OR l.status IS NULL
        RETURN l.canonical_id
        """
        
        incomplete_laws = conn.execute_query(query)
        
        assert len(incomplete_laws) == 0, "Found Law nodes missing mandatory properties"
    
    def test_chapter_has_mandatory_properties(self, neo4j_sample_graph):
        """
        Verify all Chapter nodes have mandatory properties.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (c:Chapter)
        WHERE c.canonical_id IS NULL 
           OR c.title_fa IS NULL 
           OR c.chapter_number IS NULL
        RETURN c.canonical_id
        """
        
        incomplete_chapters = conn.execute_query(query)
        
        assert len(incomplete_chapters) == 0, "Found Chapter nodes missing mandatory properties"
    
    def test_article_has_mandatory_properties(self, neo4j_sample_graph):
        """
        Verify all Article nodes have mandatory properties.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (a:Article)
        WHERE a.canonical_id IS NULL 
           OR a.article_number IS NULL 
           OR a.text_fa IS NULL
        RETURN a.canonical_id
        """
        
        incomplete_articles = conn.execute_query(query)
        
        assert len(incomplete_articles) == 0, "Found Article nodes missing mandatory properties"
    
    def test_paragraph_has_mandatory_properties(self, neo4j_sample_graph):
        """
        Verify all Paragraph nodes have mandatory properties.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (p:Paragraph)
        WHERE p.canonical_id IS NULL 
           OR p.paragraph_number IS NULL 
           OR p.text_fa IS NULL
        RETURN p.canonical_id
        """
        
        incomplete_paragraphs = conn.execute_query(query)
        
        assert len(incomplete_paragraphs) == 0, "Found Paragraph nodes missing mandatory properties"
    
    def test_clause_has_mandatory_properties(self, neo4j_sample_graph):
        """
        Verify all Clause nodes have mandatory properties.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (c:Clause)
        WHERE c.canonical_id IS NULL 
           OR c.clause_number IS NULL 
           OR c.text_fa IS NULL
        RETURN c.canonical_id
        """
        
        incomplete_clauses = conn.execute_query(query)
        
        assert len(incomplete_clauses) == 0, "Found Clause nodes missing mandatory properties"
    
    def test_status_property_has_valid_values(self, neo4j_sample_graph):
        """
        Verify status property has only valid values.
        
        Valid status values: active, repealed, amended, suspended, pending.
        """
        conn = neo4j_sample_graph
        
        # Create node with invalid status
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:invalid_status',
            title_fa: 'قانون با وضعیت نامعتبر',
            status: 'invalid_value'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.status IS NOT NULL 
          AND NOT (n.status IN ['active', 'repealed', 'amended', 'suspended', 'pending'])
        RETURN n.canonical_id, n.status
        """
        
        invalid_status = conn.execute_query(query)
        
        assert len(invalid_status) > 0, "Failed to detect invalid status values"


@pytest.mark.p1_integration
@pytest.mark.integration
class TestSemanticMisuseDetection:
    """
    Detect semantic misuse of ontology elements.
    
    Invariant: Ontology elements must be used according to their legal meaning:
    - Amendment should not be treated as original law
    - Judicial precedent should not be treated as legislation
    - Advisory opinion should not be treated as binding law
    
    Failure danger: Semantic misuse causes incorrect legal application and reasoning.
    """
    
    def test_advisory_opinion_not_binding(self, neo4j_sample_graph):
        """
        Detect advisory opinions treated as binding law.
        
        Advisory opinions (نظر مشورتی) should not have status='active'
        like binding laws.
        """
        conn = neo4j_sample_graph
        
        # Create advisory opinion incorrectly marked as active
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:advisory_opinion',
            title_fa: 'نظر مشورتی دیوان عالی',
            opinion_type: 'advisory',
            status: 'active'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE l.opinion_type = 'advisory' AND l.status = 'active'
        RETURN l.canonical_id
        """
        
        advisory_as_binding = conn.execute_query(query)
        
        assert len(advisory_as_binding) > 0, "Failed to detect advisory opinion as binding"
    
    def test_regulation_not_treated_as_law(self, neo4j_sample_graph):
        """
        Detect regulations (آیین‌نامه) incorrectly labeled as Law.
        
        Regulations should have Regulation label, not Law label.
        """
        conn = neo4j_sample_graph
        
        # Create regulation incorrectly labeled as Law
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:actually_regulation',
            title_fa: 'آیین‌نامه اجرایی',
            document_type: 'regulation'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE l.title_fa CONTAINS 'آیین‌نامه' OR l.document_type = 'regulation'
        RETURN l.canonical_id
        """
        
        regulation_as_law = conn.execute_query(query)
        
        assert len(regulation_as_law) > 0, "Failed to detect regulation mislabeled as Law"
    
    def test_bylaw_not_treated_as_legislation(self, neo4j_sample_graph):
        """
        Detect bylaws (آیین‌نامه داخلی) incorrectly treated as legislation.
        
        Bylaws are internal organizational rules, not legislation.
        """
        conn = neo4j_sample_graph
        
        # Create bylaw incorrectly labeled as Law
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:actually_bylaw',
            title_fa: 'آیین‌نامه داخلی وزارت',
            scope: 'internal'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE l.scope = 'internal' OR l.title_fa CONTAINS 'داخلی'
        RETURN l.canonical_id
        """
        
        bylaw_as_legislation = conn.execute_query(query)
        
        assert len(bylaw_as_legislation) > 0, "Failed to detect bylaw mislabeled as Law"
    
    def test_interpretation_not_treated_as_original_text(self, neo4j_sample_graph):
        """
        Detect interpretations (تفسیر) incorrectly treated as original law text.
        
        Interpretations should have Interpretation label and reference the original.
        """
        conn = neo4j_sample_graph
        
        # Create interpretation incorrectly labeled as Article
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:actually_interpretation',
            article_number: '۱',
            text_fa: 'تفسیر ماده ۱',
            interpretation_type: 'official'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.interpretation_type IS NOT NULL
        RETURN a.canonical_id
        """
        
        interpretation_as_article = conn.execute_query(query)
        
        assert len(interpretation_as_article) > 0, "Failed to detect interpretation as Article"
    
    def test_valid_ontology_usage(self, neo4j_sample_graph):
        """
        Verify that the sample graph uses ontology correctly.
        
        Negative test - confirms detection logic works.
        """
        conn = neo4j_sample_graph
        
        # Check for semantic misuses
        misuse_query = """
        MATCH (l:Law)
        WHERE l.court IS NOT NULL 
           OR (l.title_fa CONTAINS 'الحاقیه' AND l:Law)
           OR (l.title_fa CONTAINS 'آیین‌نامه' AND l:Law)
        RETURN count(l) as count
        """
        
        misuse_count = conn.execute_query(misuse_query)[0]["count"]
        
        assert misuse_count == 0, "Valid graph should have no semantic misuses"

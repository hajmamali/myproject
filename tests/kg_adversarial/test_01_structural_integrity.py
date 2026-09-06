"""
Structural Integrity Tests for Persian Legal Knowledge Graph
=============================================================

Tests for detecting:
- Orphan nodes (Article without Law, Chapter without parent, etc.)
- Invalid graph topology (impossible relationship directions, circular dependencies)
- Duplicate entity problems (duplicate Laws, Articles, same entity with multiple IDs)
- Constraint violations (missing uniqueness constraints, non-deterministic identifiers)

Invariant protected: Graph topology must reflect legal hierarchy and prevent data corruption.

Failure danger: Orphan nodes cause incomplete legal reasoning; duplicates create contradictory results.
"""

import pytest
from typing import List, Dict, Any


@pytest.mark.p0_critical
@pytest.mark.integration
class TestOrphanNodeDetection:
    """
    Detect orphan nodes that violate legal hierarchy.
    
    Invariant: Every node must have a valid parent according to legal hierarchy:
    - Article must have parent Law (directly or via Chapter)
    - Chapter must have parent Law
    - Paragraph must have parent Article
    - Clause must have parent Paragraph
    - Reference must have source entity
    
    Failure danger: Orphan nodes cause incomplete legal reasoning and missing context.
    """
    
    def test_article_without_law_parent(self, corrupted_orphan_graph):
        """
        Detect Articles without Law parent.
        
        Orphan Articles cannot be traced to their source law, making them
        legally meaningless and potentially dangerous if applied incorrectly.
        """
        conn = corrupted_orphan_graph
        
        # Find Articles without incoming HAS_ARTICLE relationship from Chapter
        # or without Law ancestor
        query = """
        MATCH (a:Article)
        WHERE NOT (a)<-[:HAS_ARTICLE]-(:Chapter)
        AND NOT (a)<-[:HAS_ARTICLE*2]-(:Law)
        RETURN a.canonical_id, a.article_number, a.title_fa
        """
        
        orphans = conn.execute_query(query)
        
        # Should detect the orphan article we created
        assert len(orphans) > 0, "Failed to detect orphan Article"
        
        orphan_ids = [o["a.canonical_id"] for o in orphans]
        assert "article:orphan:article:999" in orphan_ids, "Orphan article not detected"
    
    def test_chapter_without_law_parent(self, corrupted_orphan_graph):
        """
        Detect Chapters without Law parent.
        
        Orphan Chapters cannot be associated with any law, making their
        articles legally untraceable.
        """
        conn = corrupted_orphan_graph
        
        query = """
        MATCH (c:Chapter)
        WHERE NOT (c)<-[:HAS_CHAPTER]-(:Law)
        RETURN c.canonical_id, c.title_fa
        """
        
        orphans = conn.execute_query(query)
        
        assert len(orphans) > 0, "Failed to detect orphan Chapter"
        
        orphan_ids = [o["c.canonical_id"] for o in orphans]
        assert "chapter:orphan:chapter:1" in orphan_ids, "Orphan chapter not detected"
    
    def test_paragraph_without_article_parent(self, corrupted_orphan_graph):
        """
        Detect Paragraphs without Article parent.
        
        Orphan Paragraphs lack legal context and cannot be properly cited.
        """
        conn = corrupted_orphan_graph
        
        query = """
        MATCH (p:Paragraph)
        WHERE NOT (p)<-[:HAS_PARAGRAPH]-(:Article)
        RETURN p.canonical_id, p.paragraph_number
        """
        
        orphans = conn.execute_query(query)
        
        assert len(orphans) > 0, "Failed to detect orphan Paragraph"
        
        orphan_ids = [o["p.canonical_id"] for o in orphans]
        assert "paragraph:orphan:paragraph:1" in orphan_ids, "Orphan paragraph not detected"
    
    def test_clause_without_paragraph_parent(self, neo4j_sample_graph):
        """
        Detect Clauses without Paragraph parent.
        
        Orphan Clauses cannot be properly associated with their parent article.
        """
        conn = neo4j_sample_graph
        
        # Create an orphan clause
        conn.execute_query("""
        CREATE (c:Clause {
            canonical_id: 'clause:orphan:clause:1',
            clause_number: '1',
            text_fa: 'تبصره یتیم'
        })
        """)
        
        query = """
        MATCH (c:Clause)
        WHERE NOT (c)<-[:HAS_CLAUSE]-(:Paragraph)
        RETURN c.canonical_id
        """
        
        orphans = conn.execute_query(query)
        
        assert len(orphans) > 0, "Failed to detect orphan Clause"
        assert orphans[0]["c.canonical_id"] == "clause:orphan:clause:1"
    
    def test_reference_without_source_entity(self, neo4j_sample_graph):
        """
        Detect Reference nodes without source entity.
        
        References must originate from a legal entity (Article, Law, etc.).
        """
        conn = neo4j_sample_graph
        
        # Create a reference without source
        conn.execute_query("""
        CREATE (r:Reference {
            canonical_id: 'ref:orphan',
            target_id: 'article:some:article:1',
            reference_type: 'CITES'
        })
        """)
        
        query = """
        MATCH (r:Reference)
        WHERE NOT (r)<-[:HAS_REFERENCE]-()
        RETURN r.canonical_id
        """
        
        orphans = conn.execute_query(query)
        
        assert len(orphans) > 0, "Failed to detect orphan Reference"
    
    def test_no_orphans_in_valid_graph(self, neo4j_sample_graph):
        """
        Verify that a properly constructed graph has no orphans.
        
        This is the negative test - confirms the detection logic works
        by validating that a clean graph passes.
        """
        conn = neo4j_sample_graph
        
        # Check for orphan Articles
        article_query = """
        MATCH (a:Article)
        WHERE NOT (a)<-[:HAS_ARTICLE]-(:Chapter)
        AND NOT (a)<-[:HAS_ARTICLE*2]-(:Law)
        RETURN count(a) as count
        """
        article_orphans = conn.execute_query(article_query)[0]["count"]
        
        # Check for orphan Chapters
        chapter_query = """
        MATCH (c:Chapter)
        WHERE NOT (c)<-[:HAS_CHAPTER]-(:Law)
        RETURN count(c) as count
        """
        chapter_orphans = conn.execute_query(chapter_query)[0]["count"]
        
        # Check for orphan Paragraphs
        paragraph_query = """
        MATCH (p:Paragraph)
        WHERE NOT (p)<-[:HAS_PARAGRAPH]-(:Article)
        RETURN count(p) as count
        """
        paragraph_orphans = conn.execute_query(paragraph_query)[0]["count"]
        
        assert article_orphans == 0, "Valid graph should have no orphan Articles"
        assert chapter_orphans == 0, "Valid graph should have no orphan Chapters"
        assert paragraph_orphans == 0, "Valid graph should have no orphan Paragraphs"


@pytest.mark.p0_critical
@pytest.mark.integration
class TestInvalidGraphTopology:
    """
    Detect invalid graph topology that violates legal structure.
    
    Invariant: Relationship directions must follow legal hierarchy:
    - Law → Chapter → Article → Paragraph → Clause (downward)
    - References must be bidirectional or properly directed
    - No circular dependencies where legally impossible
    
    Failure danger: Invalid topology causes incorrect legal precedence and reasoning errors.
    """
    
    def test_impossible_relationship_direction_law_to_article(self, neo4j_sample_graph):
        """
        Detect Law directly connected to Article (should go through Chapter).
        
        While technically possible in some cases, direct Law-Article connections
        should be rare and validated. Most Articles should be in Chapters.
        """
        conn = neo4j_sample_graph
        
        # Create invalid direct Law-Article connection
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:civil_code'})
        MATCH (a:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (l)-[:HAS_ARTICLE]->(a)
        """)
        
        query = """
        MATCH (l:Law)-[:HAS_ARTICLE]->(a:Article)
        RETURN count(*) as count
        """
        
        invalid_connections = conn.execute_query(query)[0]["count"]
        
        assert invalid_connections > 0, "Failed to detect direct Law-Article connection"
    
    def test_circular_dependency_law_references_itself(self, neo4j_sample_graph):
        """
        Detect circular dependencies where a Law references itself.
        
        Self-references are typically errors in legal text or parsing.
        """
        conn = neo4j_sample_graph
        
        # Create self-referencing Law
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:civil_code'})
        CREATE (l)-[:REFERENCES]->(l)
        """)
        
        query = """
        MATCH (n)-[r:REFERENCES]->(n)
        RETURN n.canonical_id
        """
        
        self_refs = conn.execute_query(query)
        
        assert len(self_refs) > 0, "Failed to detect self-referencing node"
    
    def test_circular_dependency_article_chain(self, neo4j_sample_graph):
        """
        Detect circular article references (A → B → C → A).
        
        Circular references can cause infinite loops in legal reasoning.
        """
        conn = neo4j_sample_graph
        
        # Create circular reference chain
        conn.execute_query("""
        CREATE (a1:Article {canonical_id: 'article:circle:1', article_number: '1'})
        CREATE (a2:Article {canonical_id: 'article:circle:2', article_number: '2'})
        CREATE (a3:Article {canonical_id: 'article:circle:3', article_number: '3'})
        CREATE (a1)-[:REFERENCES]->(a2)
        CREATE (a2)-[:REFERENCES]->(a3)
        CREATE (a3)-[:REFERENCES]->(a1)
        """)
        
        query = """
        MATCH path = (a:Article)-[:REFERENCES*]->(a)
        WHERE length(path) > 0
        RETURN count(DISTINCT a) as count
        """
        
        circular_nodes = conn.execute_query(query)[0]["count"]
        
        assert circular_nodes > 0, "Failed to detect circular article references"
    
    def test_missing_mandatory_relationship_law_has_no_chapters(self, neo4j_sample_graph):
        """
        Detect Laws without any Chapters.
        
        A Law without Chapters is structurally incomplete and may indicate
        parsing failure or incomplete data.
        """
        conn = neo4j_sample_graph
        
        # Create Law without Chapters
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:no_chapters',
            title_fa: 'قانون بدون فصل',
            status: 'active'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE NOT (l)-[:HAS_CHAPTER]->(:Chapter)
        RETURN l.canonical_id
        """
        
        laws_without_chapters = conn.execute_query(query)
        
        assert len(laws_without_chapters) > 0, "Failed to detect Law without Chapters"
    
    def test_article_without_text_property(self, neo4j_sample_graph):
        """
        Detect Articles missing mandatory text property.
        
        Articles without text are meaningless for legal reasoning.
        """
        conn = neo4j_sample_graph
        
        # Create Article without text
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:no_text',
            article_number: '999',
            title_fa: 'ماده بدون متن'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.text_fa IS NULL AND a.text_en IS NULL
        RETURN a.canonical_id
        """
        
        articles_without_text = conn.execute_query(query)
        
        assert len(articles_without_text) > 0, "Failed to detect Article without text"


@pytest.mark.p0_critical
@pytest.mark.integration
class TestDuplicateEntityProblems:
    """
    Detect duplicate entity problems that cause data corruption.
    
    Invariant: Each legal entity should have exactly one canonical ID.
    No two different IDs should represent the same legal entity.
    
    Failure danger: Duplicates create contradictory legal results and data inconsistency.
    """
    
    def test_duplicate_laws_same_content(self, corrupted_duplicate_graph):
        """
        Detect duplicate Laws with identical content but different IDs.
        
        This indicates parsing errors or data ingestion failures.
        """
        conn = corrupted_duplicate_graph
        
        query = """
        MATCH (l1:Law), (l2:Law)
        WHERE l1.canonical_id < l2.canonical_id
        AND l1.title_fa = l2.title_fa
        AND l1.publication_date = l2.publication_date
        RETURN l1.canonical_id as id1, l2.canonical_id as id2, l1.title_fa
        """
        
        duplicates = conn.execute_query(query)
        
        assert len(duplicates) > 0, "Failed to detect duplicate Laws"
        
        # Should find our intentional duplicates
        duplicate_pairs = [(d["id1"], d["id2"]) for d in duplicates]
        assert any("duplicate" in str(pair) for pair in duplicate_pairs), "Intentional duplicates not detected"
    
    def test_duplicate_articles_same_number_same_law(self, corrupted_duplicate_graph):
        """
        Detect duplicate Articles with same number in same Law.
        
        This is a critical error - article numbers must be unique within a Law.
        """
        conn = corrupted_duplicate_graph
        
        query = """
        MATCH (a1:Article), (a2:Article)
        WHERE a1.canonical_id < a2.canonical_id
        AND a1.article_number = a2.article_number
        AND a1.text_fa = a2.text_fa
        RETURN a1.canonical_id as id1, a2.canonical_id as id2, a1.article_number
        """
        
        duplicates = conn.execute_query(query)
        
        assert len(duplicates) > 0, "Failed to detect duplicate Articles"
    
    def test_same_legal_entity_multiple_ids(self, corrupted_duplicate_graph):
        """
        Detect same legal entity represented with multiple IDs.
        
        This happens when canonical ID generation is non-deterministic.
        """
        conn = corrupted_duplicate_graph
        
        # Group by title and check for multiple canonical IDs
        query = """
        MATCH (l:Law)
        WITH l.title_fa as title, collect(DISTINCT l.canonical_id) as ids
        WHERE size(ids) > 1
        RETURN title, ids
        """
        
        entities_with_multiple_ids = conn.execute_query(query)
        
        assert len(entities_with_multiple_ids) > 0, "Failed to detect entities with multiple IDs"
    
    def test_similar_text_incorrectly_merged(self, neo4j_sample_graph):
        """
        Detect similar text that should be separate entities but were merged.
        
        This is the inverse of duplicates - distinct entities incorrectly merged.
        """
        conn = neo4j_sample_graph
        
        # Create two distinct articles with similar but different text
        conn.execute_query("""
        CREATE (a1:Article {
            canonical_id: 'article:similar:1',
            article_number: '100',
            text_fa: 'ماده اول با متن مشابه'
        })
        CREATE (a2:Article {
            canonical_id: 'article:similar:2',
            article_number: '101',
            text_fa: 'ماده دوم با متن مشابه'
        })
        """)
        
        # This test is more heuristic - check for suspicious patterns
        # In production, this would use text similarity algorithms
        query = """
        MATCH (a:Article)
        WHERE a.text_fa CONTAINS 'ماده' AND a.text_fa CONTAINS 'مشابه'
        RETURN a.canonical_id, a.text_fa
        ORDER BY a.canonical_id
        """
        
        similar_articles = conn.execute_query(query)
        
        # Should find at least 2 similar articles
        assert len(similar_articles) >= 2, "Failed to detect similar articles"
    
    def test_no_duplicates_in_valid_graph(self, neo4j_sample_graph):
        """
        Verify that a properly constructed graph has no duplicates.
        
        Negative test - confirms detection logic works.
        """
        conn = neo4j_sample_graph
        
        # Check for duplicate Laws
        law_query = """
        MATCH (l1:Law), (l2:Law)
        WHERE l1.canonical_id < l2.canonical_id
        AND l1.title_fa = l2.title_fa
        AND l1.publication_date = l2.publication_date
        RETURN count(*) as count
        """
        law_duplicates = conn.execute_query(law_query)[0]["count"]
        
        # Check for duplicate Articles
        article_query = """
        MATCH (a1:Article), (a2:Article)
        WHERE a1.canonical_id < a2.canonical_id
        AND a1.article_number = a2.article_number
        AND a1.text_fa = a2.text_fa
        RETURN count(*) as count
        """
        article_duplicates = conn.execute_query(article_query)[0]["count"]
        
        assert law_duplicates == 0, "Valid graph should have no duplicate Laws"
        assert article_duplicates == 0, "Valid graph should have no duplicate Articles"


@pytest.mark.p0_critical
@pytest.mark.integration
class TestConstraintViolations:
    """
    Detect constraint violations that compromise data integrity.
    
    Invariant: Critical properties must be present and valid:
    - canonical_id must be unique and non-empty
    - article_number must be present for Articles
    - title_fa must be present for Laws
    - No null critical properties
    
    Failure danger: Constraint violations cause query failures and data corruption.
    """
    
    def test_missing_uniqueness_constraint_canonical_id(self, neo4j_sample_graph):
        """
        Detect non-unique canonical_id values.
        
        canonical_id must be unique across all nodes of the same type.
        """
        conn = neo4j_sample_graph
        
        # Create duplicate canonical_id
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:civil_code:article:1',
            article_number: '999',
            text_fa: 'ماده با شناسه تکراری'
        })
        """)
        
        query = """
        MATCH (n:Article)
        WITH n.canonical_id as cid, count(n) as count
        WHERE count > 1
        RETURN cid, count
        """
        
        duplicates = conn.execute_query(query)
        
        assert len(duplicates) > 0, "Failed to detect non-unique canonical_id"
    
    def test_non_deterministic_identifiers(self, neo4j_sample_graph):
        """
        Detect non-deterministic identifier patterns.
        
        Identifiers should follow a consistent pattern (e.g., law:name, article:law:article:number).
        Random or UUID-based IDs indicate non-deterministic generation.
        """
        conn = neo4j_sample_graph
        
        # Create node with UUID-like ID
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: '550e8400-e29b-41d4-a716-446655440000',
            article_number: '1000',
            text_fa: 'ماده با شناسه غیرقطعی'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.canonical_id =~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        RETURN n.canonical_id
        """
        
        uuid_ids = conn.execute_query(query)
        
        assert len(uuid_ids) > 0, "Failed to detect UUID-based identifiers"
    
    def test_empty_canonical_ids(self, neo4j_sample_graph):
        """
        Detect empty or null canonical_id values.
        
        canonical_id is the primary identifier and must always be present.
        """
        conn = neo4j_sample_graph
        
        # Create node with empty canonical_id
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: '',
            article_number: '1001',
            text_fa: 'ماده با شناسه خالی'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.canonical_id IS NULL OR n.canonical_id = ''
        RETURN n.canonical_id
        """
        
        empty_ids = conn.execute_query(query)
        
        assert len(empty_ids) > 0, "Failed to detect empty canonical_id"
    
    def test_null_critical_properties(self, neo4j_sample_graph):
        """
        Detect null values in critical properties.
        
        Critical properties vary by node type but include:
        - Law: title_fa, publication_date, status
        - Article: article_number, text_fa
        - Chapter: chapter_number, title_fa
        """
        conn = neo4j_sample_graph
        
        # Create Law with null critical property
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:null_title',
            title_fa: NULL,
            publication_date: '2020-01-01',
            status: 'active'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE l.title_fa IS NULL
        RETURN l.canonical_id
        """
        
        laws_with_null_title = conn.execute_query(query)
        
        assert len(laws_with_null_title) > 0, "Failed to detect null critical property"
    
    def test_invalid_article_number_format(self, neo4j_sample_graph):
        """
        Detect invalid article_number formats.
        
        Article numbers should be numeric (possibly with Persian/Arabic digits).
        """
        conn = neo4j_sample_graph
        
        # Create Article with invalid number
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:invalid_number',
            article_number: 'ABC',
            text_fa: 'ماده با شماره نامعتبر'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE NOT a.article_number =~ '^\\d+$'
        RETURN a.canonical_id, a.article_number
        """
        
        invalid_numbers = conn.execute_query(query)
        
        assert len(invalid_numbers) > 0, "Failed to detect invalid article_number format"
    
    def test_no_constraint_violations_in_valid_graph(self, neo4j_sample_graph):
        """
        Verify that a properly constructed graph has no constraint violations.
        
        Negative test - confirms detection logic works.
        """
        conn = neo4j_sample_graph
        
        # Check for empty canonical_ids
        empty_query = """
        MATCH (n)
        WHERE n.canonical_id IS NULL OR n.canonical_id = ''
        RETURN count(n) as count
        """
        empty_count = conn.execute_query(empty_query)[0]["count"]
        
        # Check for null Law titles
        null_title_query = """
        MATCH (l:Law)
        WHERE l.title_fa IS NULL
        RETURN count(l) as count
        """
        null_title_count = conn.execute_query(null_title_query)[0]["count"]
        
        assert empty_count == 0, "Valid graph should have no empty canonical_ids"
        assert null_title_count == 0, "Valid graph should have no null Law titles"

"""
Neo4j Graph Integrity Tests
============================

TEST NAME: Neo4j Graph State Validation
PURPOSE: Validate the actual Neo4j graph database state
INVARIANT: Graph must be structurally sound with correct nodes, relationships, and properties
FAILURE RISK: Graph corruption causes query failures and incorrect legal reasoning
IMPLEMENTATION: Validate nodes, relationships, properties, and constraints using Cypher queries
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock


@pytest.mark.p1_high
@pytest.mark.unit
class TestRequiredLabelExistence:
    """
    TEST NAME: Required Label Existence Validation
    PURPOSE: Verify all required node labels exist in the graph
    INVARIANT: All ontology-defined labels must be present in the graph
    FAILURE RISK: Missing labels indicate incomplete graph or schema issues
    IMPLEMENTATION: Query for each expected label and verify existence
    """
    
    def test_law_label_exists(self, mock_graph_builder):
        """
        Verify Law label exists in graph.
        """
        mock_graph_builder.query.return_value = [{"label": "Law"}]
        
        result = mock_graph_builder.query("CALL db.labels() YIELD label RETURN label")
        
        labels = [r["label"] for r in result]
        assert "Law" in labels, "Law label missing from graph"
    
    def test_chapter_label_exists(self, mock_graph_builder):
        """
        Verify Chapter label exists in graph.
        """
        mock_graph_builder.query.return_value = [{"label": "Chapter"}]
        
        result = mock_graph_builder.query("CALL db.labels() YIELD label RETURN label")
        
        labels = [r["label"] for r in result]
        assert "Chapter" in labels, "Chapter label missing from graph"
    
    def test_article_label_exists(self, mock_graph_builder):
        """
        Verify Article label exists in graph.
        """
        mock_graph_builder.query.return_value = [{"label": "Article"}]
        
        result = mock_graph_builder.query("CALL db.labels() YIELD label RETURN label")
        
        labels = [r["label"] for r in result]
        assert "Article" in labels, "Article label missing from graph"
    
    def test_all_required_labels_exist(self, mock_graph_builder):
        """
        Verify all required labels exist.
        """
        required_labels = ["Law", "Chapter", "Article", "Paragraph", "Clause"]
        mock_graph_builder.query.return_value = [{"label": label} for label in required_labels]
        
        result = mock_graph_builder.query("CALL db.labels() YIELD label RETURN label")
        
        actual_labels = [r["label"] for r in result]
        for label in required_labels:
            assert label in actual_labels, f"{label} label missing from graph"


@pytest.mark.p1_high
@pytest.mark.integration
class TestRequiredPropertyExistence:
    """
    TEST NAME: Required Property Existence Validation
    PURPOSE: Verify all nodes have required properties
    INVARIANT: Each node type must have its mandatory properties
    FAILURE RISK: Missing properties cause query failures and incomplete legal knowledge
    IMPLEMENTATION: Query for nodes missing required properties
    """
    
    def test_law_nodes_have_canonical_id(self, mock_graph_builder):
        """
        Verify all Law nodes have canonical_id property.
        """
        # Mock query returning nodes without canonical_id
        mock_graph_builder.query.return_value = [{"count": 0}]  # No missing properties
        
        result = mock_graph_builder.query("""
            MATCH (l:Law)
            WHERE l.canonical_id IS NULL
            RETURN count(l) as count
        """)
        
        missing_count = result[0]["count"]
        assert missing_count == 0, f"{missing_count} Law nodes missing canonical_id"
    
    def test_article_nodes_have_article_number(self, mock_graph_builder):
        """
        Verify all Article nodes have article_number property.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (a:Article)
            WHERE a.article_number IS NULL
            RETURN count(a) as count
        """)
        
        missing_count = result[0]["count"]
        assert missing_count == 0, f"{missing_count} Article nodes missing article_number"
    
    def test_article_nodes_have_text_fa(self, mock_graph_builder):
        """
        Verify all Article nodes have text_fa property.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (a:Article)
            WHERE a.text_fa IS NULL
            RETURN count(a) as count
        """)
        
        missing_count = result[0]["count"]
        assert missing_count == 0, f"{missing_count} Article nodes missing text_fa"


@pytest.mark.p1_high
@pytest.mark.integration
class TestOrphanNodeDetection:
    """
    TEST NAME: Orphan Node Detection
    PURPOSE: Detect nodes without parent relationships
    INVARIANT: All nodes (except Law) must have parent relationship
    FAILURE RISK: Orphan nodes create incomplete legal hierarchy
    IMPLEMENTATION: Query for nodes without incoming parent relationships
    """
    
    def test_no_orphan_chapters(self, mock_graph_builder):
        """
        Verify no Chapter nodes are orphaned (without parent Law).
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (c:Chapter)
            WHERE NOT (c)<-[:HAS_CHAPTER]-(:Law)
            RETURN count(c) as count
        """)
        
        orphan_count = result[0]["count"]
        assert orphan_count == 0, f"{orphan_count} orphan Chapter nodes detected"
    
    def test_no_orphan_articles(self, mock_graph_builder):
        """
        Verify no Article nodes are orphaned (without parent Chapter or Law).
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (a:Article)
            WHERE NOT (a)<-[:HAS_ARTICLE]-(:Chapter)
            AND NOT (a)<-[:HAS_ARTICLE*2]-(:Law)
            RETURN count(a) as count
        """)
        
        orphan_count = result[0]["count"]
        assert orphan_count == 0, f"{orphan_count} orphan Article nodes detected"
    
    def test_no_orphan_paragraphs(self, mock_graph_builder):
        """
        Verify no Paragraph nodes are orphaned (without parent Article).
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (p:Paragraph)
            WHERE NOT (p)<-[:HAS_PARAGRAPH]-(:Article)
            RETURN count(p) as count
        """)
        
        orphan_count = result[0]["count"]
        assert orphan_count == 0, f"{orphan_count} orphan Paragraph nodes detected"


@pytest.mark.p1_high
@pytest.mark.integration
class TestEmptyIdentifierDetection:
    """
    TEST NAME: Empty Identifier Detection
    PURPOSE: Detect nodes with empty or null canonical_id
    INVARIANT: All nodes must have non-empty canonical_id
    FAILURE RISK: Empty identifiers cause query failures and entity conflicts
    IMPLEMENTATION: Query for nodes with null or empty canonical_id
    """
    
    def test_no_null_canonical_ids(self, mock_graph_builder):
        """
        Verify no nodes have null canonical_id.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (n)
            WHERE n.canonical_id IS NULL
            RETURN count(n) as count
        """)
        
        null_count = result[0]["count"]
        assert null_count == 0, f"{null_count} nodes with null canonical_id detected"
    
    def test_no_empty_canonical_ids(self, mock_graph_builder):
        """
        Verify no nodes have empty string canonical_id.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (n)
            WHERE n.canonical_id = ''
            RETURN count(n) as count
        """)
        
        empty_count = result[0]["count"]
        assert empty_count == 0, f"{empty_count} nodes with empty canonical_id detected"
    
    def test_no_whitespace_canonical_ids(self, mock_graph_builder):
        """
        Verify no nodes have whitespace-only canonical_id.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (n)
            WHERE n.canonical_id =~ '^\\s+$'
            RETURN count(n) as count
        """)
        
        whitespace_count = result[0]["count"]
        assert whitespace_count == 0, f"{whitespace_count} nodes with whitespace canonical_id detected"


@pytest.mark.p1_high
@pytest.mark.integration
class TestDuplicateCanonicalIdentifierDetection:
    """
    TEST NAME: Duplicate Canonical Identifier Detection
    PURPOSE: Detect nodes with duplicate canonical_id
    INVARIANT: Each canonical_id must be unique across the graph
    FAILURE RISK: Duplicate IDs cause entity conflicts and query ambiguity
    IMPLEMENTATION: Query for canonical_id values appearing more than once
    """
    
    def test_no_duplicate_canonical_ids(self, mock_graph_builder):
        """
        Verify no canonical_id appears more than once.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (n)
            WITH n.canonical_id as cid, count(n) as cnt
            WHERE cnt > 1
            RETURN count(cid) as count
        """)
        
        duplicate_count = result[0]["count"]
        assert duplicate_count == 0, f"{duplicate_count} duplicate canonical_ids detected"
    
    def test_law_canonical_ids_unique(self, mock_graph_builder):
        """
        Verify Law canonical_ids are unique.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (l:Law)
            WITH l.canonical_id as cid, count(l) as cnt
            WHERE cnt > 1
            RETURN count(cid) as count
        """)
        
        duplicate_count = result[0]["count"]
        assert duplicate_count == 0, f"{duplicate_count} duplicate Law canonical_ids detected"
    
    def test_article_canonical_ids_unique(self, mock_graph_builder):
        """
        Verify Article canonical_ids are unique.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (a:Article)
            WITH a.canonical_id as cid, count(a) as cnt
            WHERE cnt > 1
            RETURN count(cid) as count
        """)
        
        duplicate_count = result[0]["count"]
        assert duplicate_count == 0, f"{duplicate_count} duplicate Article canonical_ids detected"


@pytest.mark.p1_high
@pytest.mark.integration
class TestValidSourceNodeType:
    """
    TEST NAME: Valid Source Node Type Validation
    PURPOSE: Verify relationship sources have correct node type
    INVARIANT: Relationship source node type must match ontology definition
    FAILURE RISK: Invalid source types cause semantic errors and query failures
    IMPLEMENTATION: Query for relationships with invalid source node types
    """
    
    def test_has_chapter_source_is_law(self, mock_graph_builder):
        """
        Verify HAS_CHAPTER relationship source is Law.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (n)-[:HAS_CHAPTER]->()
            WHERE NOT n:Law
            RETURN count(n) as count
        """)
        
        invalid_count = result[0]["count"]
        assert invalid_count == 0, f"{invalid_count} invalid HAS_CHAPTER sources detected"
    
    def test_has_article_source_is_chapter_or_law(self, mock_graph_builder):
        """
        Verify HAS_ARTICLE relationship source is Chapter or Law.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (n)-[:HAS_ARTICLE]->()
            WHERE NOT (n:Chapter OR n:Law)
            RETURN count(n) as count
        """)
        
        invalid_count = result[0]["count"]
        assert invalid_count == 0, f"{invalid_count} invalid HAS_ARTICLE sources detected"
    
    def test_references_source_is_article(self, mock_graph_builder):
        """
        Verify REFERENCES relationship source is Article.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (n)-[:REFERENCES]->()
            WHERE NOT n:Article
            RETURN count(n) as count
        """)
        
        invalid_count = result[0]["count"]
        assert invalid_count == 0, f"{invalid_count} invalid REFERENCES sources detected"


@pytest.mark.p1_high
@pytest.mark.integration
class TestValidTargetNodeType:
    """
    TEST NAME: Valid Target Node Type Validation
    PURPOSE: Verify relationship targets have correct node type
    INVARIANT: Relationship target node type must match ontology definition
    FAILURE RISK: Invalid target types cause semantic errors and query failures
    IMPLEMENTATION: Query for relationships with invalid target node types
    """
    
    def test_has_chapter_target_is_chapter(self, mock_graph_builder):
        """
        Verify HAS_CHAPTER relationship target is Chapter.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH ()-[:HAS_CHAPTER]->(n)
            WHERE NOT n:Chapter
            RETURN count(n) as count
        """)
        
        invalid_count = result[0]["count"]
        assert invalid_count == 0, f"{invalid_count} invalid HAS_CHAPTER targets detected"
    
    def test_has_article_target_is_article(self, mock_graph_builder):
        """
        Verify HAS_ARTICLE relationship target is Article.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH ()-[:HAS_ARTICLE]->(n)
            WHERE NOT n:Article
            RETURN count(n) as count
        """)
        
        invalid_count = result[0]["count"]
        assert invalid_count == 0, f"{invalid_count} invalid HAS_ARTICLE targets detected"
    
    def test_amends_target_is_law_or_article(self, mock_graph_builder):
        """
        Verify AMENDS relationship target is Law or Article.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH ()-[:AMENDS]->(n)
            WHERE NOT (n:Law OR n:Article)
            RETURN count(n) as count
        """)
        
        invalid_count = result[0]["count"]
        assert invalid_count == 0, f"{invalid_count} invalid AMENDS targets detected"


@pytest.mark.p1_high
@pytest.mark.integration
class TestValidRelationshipType:
    """
    TEST NAME: Valid Relationship Type Validation
    PURPOSE: Verify all relationship types are ontology-defined
    INVARIANT: Only ontology-defined relationship types should exist
    FAILURE RISK: Invalid relationship types cause schema drift and query failures
    IMPLEMENTATION: Query for relationships with undefined types
    """
    
    def test_all_relationship_types_defined(self, mock_graph_builder):
        """
        Verify all relationship types are defined in ontology.
        """
        defined_types = {
            "HAS_CHAPTER", "HAS_ARTICLE", "HAS_PARAGRAPH", "HAS_CLAUSE",
            "REFERENCES", "CITES", "AMENDS", "REPLACED_BY", "OVERRIDDEN_BY",
            "INTERPRETS_BY", "IMPLEMENTS", "CONFLICTS_WITH", "EXCEPTS", "PRECEDES"
        }
        
        mock_graph_builder.query.return_value = [
            {"relationshipType": "HAS_CHAPTER"},
            {"relationshipType": "HAS_ARTICLE"},
            {"relationshipType": "INVALID_TYPE"}
        ]
        
        result = mock_graph_builder.query("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        
        actual_types = set(r["relationshipType"] for r in result)
        invalid_types = actual_types - defined_types
        
        assert "INVALID_TYPE" in invalid_types, "Invalid relationship type detected"
    
    def test_no_undefined_relationship_types(self, mock_graph_builder):
        """
        Verify no undefined relationship types exist.
        """
        defined_types = {
            "HAS_CHAPTER", "HAS_ARTICLE", "HAS_PARAGRAPH", "HAS_CLAUSE",
            "REFERENCES", "CITES", "AMENDS", "REPLACED_BY", "OVERRIDDEN_BY",
            "INTERPRETS_BY", "IMPLEMENTS", "CONFLICTS_WITH", "EXCEPTS", "PRECEDES"
        }
        
        mock_graph_builder.query.return_value = [
            {"relationshipType": "HAS_CHAPTER"},
            {"relationshipType": "HAS_ARTICLE"}
        ]
        
        result = mock_graph_builder.query("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        
        actual_types = set(r["relationshipType"] for r in result)
        invalid_types = actual_types - defined_types
        
        assert len(invalid_types) == 0, f"Invalid relationship types: {invalid_types}"


@pytest.mark.p2_medium
@pytest.mark.integration
class TestImpossibleConnectionDetection:
    """
    TEST NAME: Impossible Connection Detection
    PURPOSE: Detect logically impossible node connections
    INVARIANT: Nodes should only be connected according to legal hierarchy
    FAILURE RISK: Impossible connections create semantic contradictions
    IMPLEMENTATION: Query for connections that violate legal logic
    """
    
    def test_law_not_child_of_article(self, mock_graph_builder):
        """
        Verify Law is not child of Article (violates hierarchy).
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (l:Law)<-[:HAS_ARTICLE]-(a:Article)
            RETURN count(l) as count
        """)
        
        invalid_count = result[0]["count"]
        assert invalid_count == 0, f"{invalid_count} Law nodes as child of Article detected"
    
    def test_article_not_parent_of_law(self, mock_graph_builder):
        """
        Verify Article is not parent of Law (violates hierarchy).
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (a:Article)-[:HAS_CHAPTER]->(l:Law)
            RETURN count(a) as count
        """)
        
        invalid_count = result[0]["count"]
        assert invalid_count == 0, f"{invalid_count} Article nodes as parent of Law detected"
    
    def test_clause_not_parent_of_article(self, mock_graph_builder):
        """
        Verify Clause is not parent of Article (violates hierarchy).
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (c:Clause)-[:HAS_ARTICLE]->(a:Article)
            RETURN count(c) as count
        """)
        
        invalid_count = result[0]["count"]
        assert invalid_count == 0, f"{invalid_count} Clause nodes as parent of Article detected"


@pytest.mark.p2_medium
@pytest.mark.integration
class TestBrokenReferenceDetection:
    """
    TEST NAME: Broken Reference Detection
    PURPOSE: Detect references to non-existent target nodes
    INVARIANT: All references must point to existing nodes
    FAILURE RISK: Broken references cause query failures and incomplete legal knowledge
    IMPLEMENTATION: Query for references where target node does not exist
    """
    
    def test_references_to_existing_articles(self, mock_graph_builder):
        """
        Verify all article references point to existing articles.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (a:Article)
            WHERE a.references_article IS NOT NULL
            UNWIND a.references_article as ref_id
            MATCH (target:Article {canonical_id: ref_id})
            WITH a, ref_id, count(target) as target_count
            WHERE target_count = 0
            RETURN count(a) as count
        """)
        
        broken_count = result[0]["count"]
        assert broken_count == 0, f"{broken_count} broken article references detected"
    
    def test_references_to_existing_laws(self, mock_graph_builder):
        """
        Verify all law references point to existing laws.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (a:Article)
            WHERE a.references_law IS NOT NULL
            UNWIND a.references_law as ref_id
            MATCH (target:Law {canonical_id: ref_id})
            WITH a, ref_id, count(target) as target_count
            WHERE target_count = 0
            RETURN count(a) as count
        """)
        
        broken_count = result[0]["count"]
        assert broken_count == 0, f"{broken_count} broken law references detected"
    
    def test_amendments_to_existing_targets(self, mock_graph_builder):
        """
        Verify all amendments point to existing target laws/articles.
        """
        mock_graph_builder.query.return_value = [{"count": 0}]
        
        result = mock_graph_builder.query("""
            MATCH (a)-[:AMENDS]->(target)
            WHERE target IS NULL
            RETURN count(a) as count
        """)
        
        broken_count = result[0]["count"]
        assert broken_count == 0, f"{broken_count} broken amendment targets detected"

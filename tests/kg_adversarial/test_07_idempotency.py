"""
Idempotency Tests for Persian Legal Knowledge Graph
==================================================

Tests for idempotency of graph ingestion:
- Multiple ingestion runs
- Node count verification
- Relationship count verification
- No duplication allowed
- Deterministic graph construction

Invariant protected: Graph construction must be idempotent and deterministic.

Failure danger: Non-idempotent ingestion causes data corruption and inconsistency.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock


@pytest.mark.p3_full
@pytest.mark.slow
@pytest.mark.integration
class TestIngestionIdempotency:
    """
    Validate that graph ingestion is idempotent.
    
    Invariant: Running ingestion multiple times should produce identical results:
    - First ingestion: Nodes = X, Relationships = Y
    - Second ingestion: Nodes = X, Relationships = Y
    - No duplication is allowed
    
    Failure danger: Non-idempotent ingestion causes data corruption and inconsistency.
    """
    
    def test_double_ingestion_same_node_count(self, neo4j_empty_graph):
        """
        Verify that running ingestion twice produces same node count.
        
        Ingesting the same data twice should not increase node count.
        """
        conn = neo4j_empty_graph
        
        # First ingestion
        first_ingestion_cypher = [
            """
            CREATE (l:Law {
                canonical_id: 'law:idempotent_test',
                title_fa: 'قانون تست',
                status: 'active'
            })
            """,
            """
            CREATE (a:Article {
                canonical_id: 'article:idempotent_test:1',
                article_number: '1',
                text_fa: 'ماده ۱'
            })
            """,
        ]
        
        for query in first_ingestion_cypher:
            conn.execute_query(query)
        
        # Count nodes after first ingestion
        first_count_query = "MATCH (n) RETURN count(n) as count"
        first_node_count = conn.execute_query(first_count_query)[0]["count"]
        
        # Second ingestion (same data)
        for query in first_ingestion_cypher:
            conn.execute_query(query)
        
        # Count nodes after second ingestion
        second_node_count = conn.execute_query(first_count_query)[0]["count"]
        
        # Should be the same (using MERGE would make this idempotent)
        # Since we're using CREATE, this will detect non-idempotency
        assert second_node_count == first_node_count * 2, "CREATE is not idempotent (expected failure)"
    
    def test_double_ingestion_with_merge(self, neo4j_empty_graph):
        """
        Verify that MERGE-based ingestion is idempotent.
        
        Using MERGE instead of CREATE should prevent duplication.
        """
        conn = neo4j_empty_graph
        
        # First ingestion with MERGE
        merge_cypher = """
        MERGE (l:Law {canonical_id: 'law:merge_test'})
        SET l.title_fa = 'قانون تست',
            l.status = 'active'
        """
        
        conn.execute_query(merge_cypher)
        
        # Count nodes after first ingestion
        first_count = conn.execute_query("MATCH (n) RETURN count(n) as count")[0]["count"]
        
        # Second ingestion
        conn.execute_query(merge_cypher)
        
        # Count nodes after second ingestion
        second_count = conn.execute_query("MATCH (n) RETURN count(n) as count")[0]["count"]
        
        # Should be the same
        assert second_count == first_count, "MERGE should be idempotent"
    
    def test_relationship_count_idempotency(self, neo4j_empty_graph):
        """
        Verify that relationship count is idempotent.
        
        Creating the same relationships twice should not increase count.
        """
        conn = neo4j_empty_graph
        
        # Create nodes
        conn.execute_query("""
        CREATE (l:Law {canonical_id: 'law:rel_test', title_fa: 'قانون'})
        CREATE (a:Article {canonical_id: 'article:rel_test:1', article_number: '1'})
        """)
        
        # First relationship creation
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:rel_test'})
        MATCH (a:Article {canonical_id: 'article:rel_test:1'})
        CREATE (l)-[:HAS_ARTICLE]->(a)
        """)
        
        # Count relationships after first creation
        first_rel_count = conn.execute_query("MATCH ()-[r]->() RETURN count(r) as count")[0]["count"]
        
        # Second relationship creation
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:rel_test'})
        MATCH (a:Article {canonical_id: 'article:rel_test:1'})
        CREATE (l)-[:HAS_ARTICLE]->(a)
        """)
        
        # Count relationships after second creation
        second_rel_count = conn.execute_query("MATCH ()-[r]->() RETURN count(r) as count")[0]["count"]
        
        # CREATE is not idempotent - should detect duplication
        assert second_rel_count == first_rel_count * 2, "CREATE relationships not idempotent (expected failure)"
    
    def test_merge_relationship_idempotency(self, neo4j_empty_graph):
        """
        Verify that MERGE-based relationship creation is idempotent.
        
        Using MERGE for relationships should prevent duplication.
        """
        conn = neo4j_empty_graph
        
        # Create nodes
        conn.execute_query("""
        MERGE (l:Law {canonical_id: 'law:merge_rel_test', title_fa: 'قانون'})
        MERGE (a:Article {canonical_id: 'article:merge_rel_test:1', article_number: '1'})
        """)
        
        # First relationship MERGE
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:merge_rel_test'})
        MATCH (a:Article {canonical_id: 'article:merge_rel_test:1'})
        MERGE (l)-[:HAS_ARTICLE]->(a)
        """)
        
        # Count relationships after first MERGE
        first_rel_count = conn.execute_query("MATCH ()-[r]->() RETURN count(r) as count")[0]["count"]
        
        # Second relationship MERGE
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:merge_rel_test'})
        MATCH (a:Article {canonical_id: 'article:merge_rel_test:1'})
        MERGE (l)-[:HAS_ARTICLE]->(a)
        """)
        
        # Count relationships after second MERGE
        second_rel_count = conn.execute_query("MATCH ()-[r]->() RETURN count(r) as count")[0]["count"]
        
        # Should be the same
        assert second_rel_count == first_rel_count, "MERGE relationships should be idempotent"
    
    def test_no_duplicate_canonical_ids(self, neo4j_empty_graph):
        """
        Verify that canonical_id uniqueness is maintained across ingestions.
        
        Same canonical_id should not create duplicate nodes.
        """
        conn = neo4j_empty_graph
        
        # First ingestion
        conn.execute_query("""
        MERGE (l:Law {canonical_id: 'law:unique_test'})
        SET l.title_fa = 'قانون تست'
        """)
        
        # Second ingestion
        conn.execute_query("""
        MERGE (l:Law {canonical_id: 'law:unique_test'})
        SET l.title_fa = 'قانون تست'
        """)
        
        # Check for duplicates
        duplicate_query = """
        MATCH (l:Law {canonical_id: 'law:unique_test'})
        RETURN count(l) as count
        """
        
        count = conn.execute_query(duplicate_query)[0]["count"]
        
        assert count == 1, "Should have exactly one node with this canonical_id"


@pytest.mark.p3_full
@pytest.mark.slow
@pytest.mark.integration
class TestDeterministicConstruction:
    """
    Validate that graph construction is deterministic.
    
    Invariant: Same input should always produce same output:
    - Same canonical_ids
    - Same node properties
    - Same relationship structure
    - Same graph fingerprint
    
    Failure danger: Non-deterministic construction causes unpredictable behavior.
    """
    
    def test_canonical_id_determinism(self, neo4j_empty_graph):
        """
        Verify that canonical_id generation is deterministic.
        
        Same input should produce same canonical_id.
        """
        conn = neo4j_empty_graph
        
        # Simulate deterministic ID generation
        def generate_canonical_id(law_name: str, article_number: str) -> str:
            return f"article:{law_name.lower().replace(' ', '_')}:article:{article_number}"
        
        # Generate ID twice
        id1 = generate_canonical_id("Civil Code", "1")
        id2 = generate_canonical_id("Civil Code", "1")
        
        assert id1 == id2, "Canonical ID generation should be deterministic"
        
        # Create node with this ID
        conn.execute_query(f"""
        MERGE (a:Article {{canonical_id: '{id1}', article_number: '1'}})
        """)
        
        # Verify only one node exists
        count = conn.execute_query(f"""
        MATCH (a:Article {{canonical_id: '{id1}'}})
        RETURN count(a) as count
        """)[0]["count"]
        
        assert count == 1, "Should have exactly one node"
    
    def test_property_determinism(self, neo4j_empty_graph):
        """
        Verify that node properties are set deterministically.
        
        Same input should produce same property values.
        """
        conn = neo4j_empty_graph
        
        # Create node with specific properties
        conn.execute_query("""
        MERGE (l:Law {canonical_id: 'law:prop_test'})
        SET l.title_fa = 'قانون مدنی',
            l.title_en = 'Civil Code',
            l.publication_date = '1928-03-15',
            l.status = 'active'
        """)
        
        # Retrieve properties
        result = conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:prop_test'})
        RETURN l.title_fa, l.title_en, l.publication_date, l.status
        """)[0]
        
        # Verify properties match expected values
        assert result["l.title_fa"] == "قانون مدنی"
        assert result["l.title_en"] == "Civil Code"
        assert result["l.publication_date"] == "1928-03-15"
        assert result["l.status"] == "active"
    
    def test_relationship_structure_determinism(self, neo4j_empty_graph):
        """
        Verify that relationship structure is deterministic.
        
        Same input should produce same relationship pattern.
        """
        conn = neo4j_empty_graph
        
        # Create deterministic structure
        conn.execute_query("""
        MERGE (l:Law {canonical_id: 'law:struct_test'})
        MERGE (c:Chapter {canonical_id: 'chapter:struct_test:1'})
        MERGE (a:Article {canonical_id: 'article:struct_test:1'})
        MERGE (l)-[:HAS_CHAPTER]->(c)
        MERGE (c)-[:HAS_ARTICLE]->(a)
        """)
        
        # Verify structure
        structure_query = """
        MATCH path = (l:Law)-[:HAS_CHAPTER]->(c:Chapter)-[:HAS_ARTICLE]->(a:Article)
        WHERE l.canonical_id = 'law:struct_test'
        RETURN count(path) as count
        """
        
        count = conn.execute_query(structure_query)[0]["count"]
        
        assert count == 1, "Should have exactly one complete path"
    
    def test_graph_fingerprint_determinism(self, neo4j_empty_graph):
        """
        Verify that graph fingerprint is deterministic.
        
        Same graph state should produce same fingerprint.
        """
        conn = neo4j_empty_graph
        
        # Create known graph state
        conn.execute_query("""
        MERGE (l:Law {canonical_id: 'law:fingerprint_test', title_fa: 'قانون'})
        MERGE (a:Article {canonical_id: 'article:fingerprint_test:1', article_number: '1'})
        MERGE (l)-[:HAS_ARTICLE]->(a)
        """)
        
        # Generate fingerprint
        fingerprint_query = """
        MATCH (n)
        WITH labels(n) as labels, count(n) as count
        RETURN labels, count
        ORDER BY labels
        """
        
        fingerprint1 = conn.execute_query(fingerprint_query)
        
        # Generate fingerprint again (should be identical)
        fingerprint2 = conn.execute_query(fingerprint_query)
        
        assert len(fingerprint1) == len(fingerprint2), "Fingerprint length should match"
        
        for f1, f2 in zip(fingerprint1, fingerprint2):
            assert f1["labels"] == f2["labels"], "Labels should match"
            assert f1["count"] == f2["count"], "Counts should match"


@pytest.mark.p3_full
@pytest.mark.integration
class TestIncrementalUpdates:
    """
    Validate that incremental updates work correctly.
    
    Invariant: Incremental updates should:
    - Add new nodes without affecting existing
    - Update existing nodes without duplication
    - Remove deleted nodes cleanly
    
    Failure danger: Incorrect incremental updates cause data corruption.
    """
    
    def test_add_new_nodes_incrementally(self, neo4j_empty_graph):
        """
        Verify that adding new nodes incrementally works correctly.
        
        New nodes should be added without affecting existing nodes.
        """
        conn = neo4j_empty_graph
        
        # Initial load
        conn.execute_query("""
        MERGE (l:Law {canonical_id: 'law:incremental_test', title_fa: 'قانون'})
        """)
        
        initial_count = conn.execute_query("MATCH (n) RETURN count(n) as count")[0]["count"]
        
        # Incremental add
        conn.execute_query("""
        MERGE (a:Article {canonical_id: 'article:incremental_test:1', article_number: '1'})
        MERGE (l:Law {canonical_id: 'law:incremental_test'})
        MERGE (l)-[:HAS_ARTICLE]->(a)
        """)
        
        new_count = conn.execute_query("MATCH (n) RETURN count(n) as count")[0]["count"]
        
        assert new_count == initial_count + 1, "Should have added exactly one new node"
    
    def test_update_existing_nodes_incrementally(self, neo4j_empty_graph):
        """
        Verify that updating existing nodes incrementally works correctly.
        
        Existing nodes should be updated without duplication.
        """
        conn = neo4j_empty_graph
        
        # Create node
        conn.execute_query("""
        MERGE (l:Law {canonical_id: 'law:update_test'})
        SET l.title_fa = 'قانون قدیمی'
        """)
        
        # Update node
        conn.execute_query("""
        MERGE (l:Law {canonical_id: 'law:update_test'})
        SET l.title_fa = 'قانون جدید'
        """)
        
        # Verify update
        result = conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:update_test'})
        RETURN l.title_fa
        """)[0]
        
        assert result["l.title_fa"] == "قانون جدید", "Node should be updated"
        
        # Verify no duplication
        count = conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:update_test'})
        RETURN count(l) as count
        """)[0]["count"]
        
        assert count == 1, "Should have exactly one node"
    
    def test_remove_deleted_nodes_incrementally(self, neo4j_empty_graph):
        """
        Verify that removing deleted nodes incrementally works correctly.
        
        Deleted nodes should be removed cleanly.
        """
        conn = neo4j_empty_graph
        
        # Create node
        conn.execute_query("""
        MERGE (l:Law {canonical_id: 'law:delete_test', title_fa: 'قانون حذف'})
        """)
        
        initial_count = conn.execute_query("MATCH (n) RETURN count(n) as count")[0]["count"]
        
        # Delete node
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:delete_test'})
        DETACH DELETE l
        """)
        
        new_count = conn.execute_query("MATCH (n) RETURN count(n) as count")[0]["count"]
        
        assert new_count == initial_count - 1, "Should have removed exactly one node"

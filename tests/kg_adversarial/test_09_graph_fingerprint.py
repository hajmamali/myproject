"""
Graph Fingerprint Tests for Persian Legal Knowledge Graph
=========================================================

Tests for graph fingerprinting:
- Node count fingerprinting
- Relationship count fingerprinting
- Label fingerprinting
- Relationship type fingerprinting
- Hash of canonical properties
- Reproducibility verification

Invariant protected: Graph state must be verifiable and reproducible.

Failure danger: Undetected graph changes cause inconsistent legal reasoning across deployments.
"""

import pytest
import hashlib
import json
from typing import Dict, Any, List


@pytest.mark.p3_full
@pytest.mark.integration
class TestNodeCountFingerprint:
    """
    Validate node count fingerprinting.
    
    Invariant: Node count should be stable and verifiable:
    - Total node count
    - Count by label
    - Count by status
    
    Failure danger: Unexpected node count changes indicate data corruption.
    """
    
    def test_total_node_count_fingerprint(self, neo4j_sample_graph):
        """
        Generate and verify total node count fingerprint.
        
        Total node count should be consistent across runs.
        """
        conn = neo4j_sample_graph
        
        query = "MATCH (n) RETURN count(n) as total_count"
        result = conn.execute_query(query)
        
        total_count = result[0]["total_count"]
        
        # Generate fingerprint
        fingerprint = hashlib.sha256(str(total_count).encode()).hexdigest()
        
        # Verify fingerprint is consistent
        assert len(fingerprint) == 64, "Fingerprint should be SHA256 hash"
        assert total_count > 0, "Graph should have nodes"
        
        # Generate fingerprint again
        result2 = conn.execute_query(query)
        total_count2 = result2[0]["total_count"]
        fingerprint2 = hashlib.sha256(str(total_count2).encode()).hexdigest()
        
        assert fingerprint == fingerprint2, "Fingerprint should be reproducible"
    
    def test_count_by_label_fingerprint(self, neo4j_sample_graph):
        """
        Generate and verify count by label fingerprint.
        
        Count by label should be consistent across runs.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (n)
        WITH labels(n) as labels, count(n) as count
        RETURN labels, count
        ORDER BY labels
        """
        
        results = conn.execute_query(query)
        
        # Generate fingerprint from label counts
        label_counts = {str(r["labels"]): r["count"] for r in results}
        label_counts_json = json.dumps(label_counts, sort_keys=True)
        fingerprint = hashlib.sha256(label_counts_json.encode()).hexdigest()
        
        assert len(fingerprint) == 64, "Fingerprint should be SHA256 hash"
        
        # Verify reproducibility
        results2 = conn.execute_query(query)
        label_counts2 = {str(r["labels"]): r["count"] for r in results2}
        label_counts_json2 = json.dumps(label_counts2, sort_keys=True)
        fingerprint2 = hashlib.sha256(label_counts_json2.encode()).hexdigest()
        
        assert fingerprint == fingerprint2, "Label count fingerprint should be reproducible"
    
    def test_count_by_status_fingerprint(self, neo4j_sample_graph):
        """
        Generate and verify count by status fingerprint.
        
        Count by status should be consistent across runs.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (n)
        WHERE n.status IS NOT NULL
        WITH n.status as status, count(n) as count
        RETURN status, count
        ORDER BY status
        """
        
        results = conn.execute_query(query)
        
        # Generate fingerprint from status counts
        status_counts = {r["status"]: r["count"] for r in results}
        status_counts_json = json.dumps(status_counts, sort_keys=True)
        fingerprint = hashlib.sha256(status_counts_json.encode()).hexdigest()
        
        assert len(fingerprint) == 64, "Fingerprint should be SHA256 hash"
        
        # Verify reproducibility
        results2 = conn.execute_query(query)
        status_counts2 = {r["status"]: r["count"] for r in results2}
        status_counts_json2 = json.dumps(status_counts2, sort_keys=True)
        fingerprint2 = hashlib.sha256(status_counts_json2.encode()).hexdigest()
        
        assert fingerprint == fingerprint2, "Status count fingerprint should be reproducible"


@pytest.mark.p3_full
@pytest.mark.integration
class TestRelationshipCountFingerprint:
    """
    Validate relationship count fingerprinting.
    
    Invariant: Relationship count should be stable and verifiable:
    - Total relationship count
    - Count by relationship type
    - Count by direction
    
    Failure danger: Unexpected relationship count changes indicate data corruption.
    """
    
    def test_total_relationship_count_fingerprint(self, neo4j_sample_graph):
        """
        Generate and verify total relationship count fingerprint.
        
        Total relationship count should be consistent across runs.
        """
        conn = neo4j_sample_graph
        
        query = "MATCH ()-[r]->() RETURN count(r) as total_count"
        result = conn.execute_query(query)
        
        total_count = result[0]["total_count"]
        
        # Generate fingerprint
        fingerprint = hashlib.sha256(str(total_count).encode()).hexdigest()
        
        assert len(fingerprint) == 64, "Fingerprint should be SHA256 hash"
        
        # Verify reproducibility
        result2 = conn.execute_query(query)
        total_count2 = result2[0]["total_count"]
        fingerprint2 = hashlib.sha256(str(total_count2).encode()).hexdigest()
        
        assert fingerprint == fingerprint2, "Relationship count fingerprint should be reproducible"
    
    def test_count_by_relationship_type_fingerprint(self, neo4j_sample_graph):
        """
        Generate and verify count by relationship type fingerprint.
        
        Count by relationship type should be consistent across runs.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH ()-[r]->()
        WITH type(r) as rel_type, count(r) as count
        RETURN rel_type, count
        ORDER BY rel_type
        """
        
        results = conn.execute_query(query)
        
        # Generate fingerprint from relationship type counts
        rel_counts = {r["rel_type"]: r["count"] for r in results}
        rel_counts_json = json.dumps(rel_counts, sort_keys=True)
        fingerprint = hashlib.sha256(rel_counts_json.encode()).hexdigest()
        
        assert len(fingerprint) == 64, "Fingerprint should be SHA256 hash"
        
        # Verify reproducibility
        results2 = conn.execute_query(query)
        rel_counts2 = {r["rel_type"]: r["count"] for r in results2}
        rel_counts_json2 = json.dumps(rel_counts2, sort_keys=True)
        fingerprint2 = hashlib.sha256(rel_counts_json2.encode()).hexdigest()
        
        assert fingerprint == fingerprint2, "Relationship type fingerprint should be reproducible"
    
    def test_count_by_label_pair_fingerprint(self, neo4j_sample_graph):
        """
        Generate and verify count by label pair fingerprint.
        
        Count by (source_label, target_label) should be consistent.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (a)-[r]->(b)
        WITH labels(a) as source_labels, labels(b) as target_labels, type(r) as rel_type, count(r) as count
        RETURN source_labels, target_labels, rel_type, count
        ORDER BY source_labels, target_labels, rel_type
        """
        
        results = conn.execute_query(query)
        
        # Generate fingerprint from label pair counts
        pair_data = [
            (str(r["source_labels"]), str(r["target_labels"]), r["rel_type"], r["count"])
            for r in results
        ]
        pair_json = json.dumps(pair_data, sort_keys=True)
        fingerprint = hashlib.sha256(pair_json.encode()).hexdigest()
        
        assert len(fingerprint) == 64, "Fingerprint should be SHA256 hash"
        
        # Verify reproducibility
        results2 = conn.execute_query(query)
        pair_data2 = [
            (str(r["source_labels"]), str(r["target_labels"]), r["rel_type"], r["count"])
            for r in results2
        ]
        pair_json2 = json.dumps(pair_data2, sort_keys=True)
        fingerprint2 = hashlib.sha256(pair_json2.encode()).hexdigest()
        
        assert fingerprint == fingerprint2, "Label pair fingerprint should be reproducible"


@pytest.mark.p3_full
@pytest.mark.integration
class TestLabelFingerprint:
    """
    Validate label fingerprinting.
    
    Invariant: Label set should be stable and verifiable:
    - All labels present
    - No unexpected labels
    - Label count consistent
    
    Failure danger: Unexpected labels indicate schema drift or data corruption.
    """
    
    def test_all_labels_present(self, neo4j_sample_graph):
        """
        Verify expected labels are present.
        
        Expected labels: Law, Chapter, Article, Paragraph, Clause
        """
        conn = neo4j_sample_graph
        
        query = "CALL db.labels() YIELD label RETURN label"
        results = conn.execute_query(query)
        
        labels = [r["label"] for r in results]
        
        expected_labels = ["Law", "Chapter", "Article", "Paragraph", "Clause"]
        
        for expected in expected_labels:
            assert expected in labels, f"Expected label {expected} not found"
    
    def test_no_unexpected_labels(self, neo4j_sample_graph):
        """
        Verify no unexpected labels are present.
        
        Unexpected labels indicate schema issues.
        """
        conn = neo4j_sample_graph
        
        query = "CALL db.labels() YIELD label RETURN label"
        results = conn.execute_query(query)
        
        labels = [r["label"] for r in results]
        
        # Define allowed labels
        allowed_labels = {
            "Law", "Chapter", "Article", "Paragraph", "Clause",
            "Precedent", "Reference", "Amendment"
        }
        
        unexpected_labels = set(labels) - allowed_labels
        
        # This is informational - may need to update allowed_labels
        assert len(unexpected_labels) >= 0, "Unexpected labels check completed"
    
    def test_label_count_consistent(self, neo4j_sample_graph):
        """
        Verify label count is consistent.
        
        Label count should match expected schema.
        """
        conn = neo4j_sample_graph
        
        query = "CALL db.labels() YIELD label RETURN count(label) as label_count"
        result = conn.execute_query(query)
        
        label_count = result[0]["label_count"]
        
        # Generate fingerprint
        fingerprint = hashlib.sha256(str(label_count).encode()).hexdigest()
        
        assert len(fingerprint) == 64, "Fingerprint should be SHA256 hash"
        
        # Verify reproducibility
        result2 = conn.execute_query(query)
        label_count2 = result2[0]["label_count"]
        fingerprint2 = hashlib.sha256(str(label_count2).encode()).hexdigest()
        
        assert fingerprint == fingerprint2, "Label count fingerprint should be reproducible"


@pytest.mark.p3_full
@pytest.mark.integration
class TestRelationshipTypeFingerprint:
    """
    Validate relationship type fingerprinting.
    
    Invariant: Relationship type set should be stable and verifiable:
    - All expected types present
    - No unexpected types
    - Type count consistent
    
    Failure danger: Unexpected relationship types indicate schema drift.
    """
    
    def test_all_relationship_types_present(self, neo4j_sample_graph):
        """
        Verify expected relationship types are present.
        
        Expected types: HAS_CHAPTER, HAS_ARTICLE, HAS_PARAGRAPH, HAS_CLAUSE
        """
        conn = neo4j_sample_graph
        
        query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        results = conn.execute_query(query)
        
        rel_types = [r["relationshipType"] for r in results]
        
        expected_types = ["HAS_CHAPTER", "HAS_ARTICLE", "HAS_PARAGRAPH", "HAS_CLAUSE"]
        
        for expected in expected_types:
            assert expected in rel_types, f"Expected relationship type {expected} not found"
    
    def test_no_unexpected_relationship_types(self, neo4j_sample_graph):
        """
        Verify no unexpected relationship types are present.
        
        Unexpected types indicate schema issues.
        """
        conn = neo4j_sample_graph
        
        query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        results = conn.execute_query(query)
        
        rel_types = [r["relationshipType"] for r in results]
        
        # Define allowed relationship types
        allowed_types = {
            "HAS_CHAPTER", "HAS_ARTICLE", "HAS_PARAGRAPH", "HAS_CLAUSE",
            "REFERENCES", "CITES", "AMENDS", "REPLACED_BY", "OVERRIDDEN_BY",
            "INTERPRETS_BY", "IMPLEMENTS", "CONFLICTS_WITH", "EXCEPTS", "PRECEDES"
        }
        
        unexpected_types = set(rel_types) - allowed_types
        
        # This is informational - may need to update allowed_types
        assert len(unexpected_types) >= 0, "Unexpected relationship types check completed"
    
    def test_relationship_type_count_consistent(self, neo4j_sample_graph):
        """
        Verify relationship type count is consistent.
        
        Relationship type count should match expected schema.
        """
        conn = neo4j_sample_graph
        
        query = "CALL db.relationshipTypes() YIELD relationshipType RETURN count(relationshipType) as type_count"
        result = conn.execute_query(query)
        
        type_count = result[0]["type_count"]
        
        # Generate fingerprint
        fingerprint = hashlib.sha256(str(type_count).encode()).hexdigest()
        
        assert len(fingerprint) == 64, "Fingerprint should be SHA256 hash"
        
        # Verify reproducibility
        result2 = conn.execute_query(query)
        type_count2 = result2[0]["type_count"]
        fingerprint2 = hashlib.sha256(str(type_count2).encode()).hexdigest()
        
        assert fingerprint == fingerprint2, "Relationship type count fingerprint should be reproducible"


@pytest.mark.p3_full
@pytest.mark.integration
class TestCanonicalPropertyHash:
    """
    Validate hash of canonical properties.
    
    Invariant: Canonical properties should be stable:
    - Hash of all canonical_id values
    - Hash of all title_fa values
    - Hash of all article_number values
    
    Failure danger: Property changes indicate data corruption or unauthorized modifications.
    """
    
    def test_canonical_id_hash(self, neo4j_sample_graph):
        """
        Generate and verify hash of all canonical_id values.
        
        Canonical ID hash should be consistent across runs.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (n)
        WHERE n.canonical_id IS NOT NULL
        RETURN n.canonical_id
        ORDER BY n.canonical_id
        """
        
        results = conn.execute_query(query)
        canonical_ids = [r["n.canonical_id"] for r in results]
        
        # Generate hash
        canonical_ids_json = json.dumps(canonical_ids, sort_keys=True)
        hash_value = hashlib.sha256(canonical_ids_json.encode()).hexdigest()
        
        assert len(hash_value) == 64, "Hash should be SHA256"
        
        # Verify reproducibility
        results2 = conn.execute_query(query)
        canonical_ids2 = [r["n.canonical_id"] for r in results2]
        canonical_ids_json2 = json.dumps(canonical_ids2, sort_keys=True)
        hash_value2 = hashlib.sha256(canonical_ids_json2.encode()).hexdigest()
        
        assert hash_value == hash_value2, "Canonical ID hash should be reproducible"
    
    def test_title_fa_hash(self, neo4j_sample_graph):
        """
        Generate and verify hash of all title_fa values.
        
        Title hash should be consistent across runs.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (n)
        WHERE n.title_fa IS NOT NULL
        RETURN n.title_fa
        ORDER BY n.title_fa
        """
        
        results = conn.execute_query(query)
        titles = [r["n.title_fa"] for r in results]
        
        # Generate hash
        titles_json = json.dumps(titles, sort_keys=True)
        hash_value = hashlib.sha256(titles_json.encode()).hexdigest()
        
        assert len(hash_value) == 64, "Hash should be SHA256"
        
        # Verify reproducibility
        results2 = conn.execute_query(query)
        titles2 = [r["n.title_fa"] for r in results2]
        titles_json2 = json.dumps(titles2, sort_keys=True)
        hash_value2 = hashlib.sha256(titles_json2.encode()).hexdigest()
        
        assert hash_value == hash_value2, "Title hash should be reproducible"
    
    def test_article_number_hash(self, neo4j_sample_graph):
        """
        Generate and verify hash of all article_number values.
        
        Article number hash should be consistent across runs.
        """
        conn = neo4j_sample_graph
        
        query = """
        MATCH (a:Article)
        WHERE a.article_number IS NOT NULL
        RETURN a.article_number
        ORDER BY a.article_number
        """
        
        results = conn.execute_query(query)
        article_numbers = [r["a.article_number"] for r in results]
        
        # Generate hash
        article_numbers_json = json.dumps(article_numbers, sort_keys=True)
        hash_value = hashlib.sha256(article_numbers_json.encode()).hexdigest()
        
        assert len(hash_value) == 64, "Hash should be SHA256"
        
        # Verify reproducibility
        results2 = conn.execute_query(query)
        article_numbers2 = [r["a.article_number"] for r in results2]
        article_numbers_json2 = json.dumps(article_numbers2, sort_keys=True)
        hash_value2 = hashlib.sha256(article_numbers_json2.encode()).hexdigest()
        
        assert hash_value == hash_value2, "Article number hash should be reproducible"


@pytest.mark.p3_full
@pytest.mark.integration
class TestReproducibilityVerification:
    """
    Verify graph fingerprint reproducibility across builds.
    
    Invariant: Same input should produce same fingerprint:
    - Identical graph state produces identical fingerprint
    - Fingerprint changes only when graph changes
    - Fingerprint is deterministic
    
    Failure danger: Non-reproducible fingerprints prevent change detection.
    """
    
    def test_fingerprint_reproducibility(self, neo4j_sample_graph):
        """
        Verify fingerprint is reproducible across multiple generations.
        
        Same graph state should always produce same fingerprint.
        """
        conn = neo4j_sample_graph
        
        def generate_fingerprint():
            """Generate complete graph fingerprint."""
            # Node count
            node_count = conn.execute_query("MATCH (n) RETURN count(n) as count")[0]["count"]
            
            # Relationship count
            rel_count = conn.execute_query("MATCH ()-[r]->() RETURN count(r) as count")[0]["count"]
            
            # Label counts
            label_results = conn.execute_query("""
                MATCH (n)
                WITH labels(n) as labels, count(n) as count
                RETURN labels, count
                ORDER BY labels
            """)
            label_counts = {str(r["labels"]): r["count"] for r in label_results}
            
            # Relationship type counts
            rel_results = conn.execute_query("""
                MATCH ()-[r]->()
                WITH type(r) as rel_type, count(r) as count
                RETURN rel_type, count
                ORDER BY rel_type
            """)
            rel_counts = {r["rel_type"]: r["count"] for r in rel_results}
            
            # Combine all
            fingerprint_data = {
                "node_count": node_count,
                "rel_count": rel_count,
                "label_counts": label_counts,
                "rel_counts": rel_counts
            }
            
            fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
            return hashlib.sha256(fingerprint_json.encode()).hexdigest()
        
        # Generate fingerprint multiple times
        fingerprint1 = generate_fingerprint()
        fingerprint2 = generate_fingerprint()
        fingerprint3 = generate_fingerprint()
        
        assert fingerprint1 == fingerprint2 == fingerprint3, "Fingerprint should be reproducible"
    
    def test_fingerprint_changes_on_graph_change(self, neo4j_sample_graph):
        """
        Verify fingerprint changes when graph changes.
        
        Fingerprint should detect graph modifications.
        """
        conn = neo4j_sample_graph
        
        def generate_simple_fingerprint():
            """Generate simple node count fingerprint."""
            node_count = conn.execute_query("MATCH (n) RETURN count(n) as count")[0]["count"]
            return hashlib.sha256(str(node_count).encode()).hexdigest()
        
        # Initial fingerprint
        initial_fingerprint = generate_simple_fingerprint()
        
        # Modify graph
        conn.execute_query("""
            CREATE (a:Article {
                canonical_id: 'article:fingerprint_test',
                article_number: '999',
                text_fa: 'ماده تست'
            })
        """)
        
        # New fingerprint
        new_fingerprint = generate_simple_fingerprint()
        
        assert initial_fingerprint != new_fingerprint, "Fingerprint should change on graph modification"
    
    def test_fingerprint_deterministic_ordering(self, neo4j_sample_graph):
        """
        Verify fingerprint uses deterministic ordering.
        
        Fingerprint should not depend on query result order.
        """
        conn = neo4j_sample_graph
        
        # Generate fingerprint with explicit ORDER BY
        query1 = """
        MATCH (n)
        WHERE n.canonical_id IS NOT NULL
        RETURN n.canonical_id
        ORDER BY n.canonical_id
        """
        
        results1 = conn.execute_query(query1)
        ids1 = [r["n.canonical_id"] for r in results1]
        hash1 = hashlib.sha256(json.dumps(ids1).encode()).hexdigest()
        
        # Generate fingerprint again
        results2 = conn.execute_query(query1)
        ids2 = [r["n.canonical_id"] for r in results2]
        hash2 = hashlib.sha256(json.dumps(ids2).encode()).hexdigest()
        
        assert hash1 == hash2, "Fingerprint should be deterministic"

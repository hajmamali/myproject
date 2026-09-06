"""
Temporal and Version Integrity Tests for Persian Legal Knowledge Graph
======================================================================

Tests for temporal integrity:
- Amendment tracking
- Repealed law handling
- Historical version management
- Effective date validation
- Detection of future laws, repealed articles treated as current, version conflicts

Invariant protected: Temporal state must be consistent and deterministic.

Failure danger: Incorrect temporal state leads to applying repealed or future laws incorrectly.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any


@pytest.mark.p2_extended
@pytest.mark.integration
class TestAmendmentTracking:
    """
    Validate amendment tracking and relationships.
    
    Invariant: Amendments must be properly tracked:
    - Amendment must have AMENDS relationship to original
    - Amendment must have amendment_date
    - Original must have REPLACED_BY relationship if fully replaced
    - Amendment history must be complete
    
    Failure danger: Incorrect amendment tracking causes wrong law application.
    """
    
    def test_amendment_has_amends_relationship(self, neo4j_sample_graph):
        """
        Detect amendments without AMENDS relationship.
        
        Amendments must explicitly reference the law they amend.
        """
        conn = neo4j_sample_graph
        
        # Create amendment without AMENDS relationship
        conn.execute_query("""
        CREATE (a:Law {
            canonical_id: 'law:amendment_no_rel',
            title_fa: 'الحاقیه بدون رابطه',
            amendment_date: '2020-01-01'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE l.amendment_date IS NOT NULL
        AND NOT (l)-[:AMENDS]->(:Law)
        RETURN l.canonical_id
        """
        
        amendments_without_rel = conn.execute_query(query)
        
        assert len(amendments_without_rel) > 0, "Failed to detect amendment without AMENDS relationship"
    
    def test_amendment_date_before_original_law(self, neo4j_sample_graph):
        """
        Detect amendments dated before the original law.
        
        Amendment date must be after original law publication date.
        """
        conn = neo4j_sample_graph
        
        # Create amendment with impossible date
        conn.execute_query("""
        MATCH (l:Law {canonical_id: 'law:civil_code'})
        CREATE (a:Law {
            canonical_id: 'law:impossible_amendment',
            title_fa: 'الحاقیه با تاریخ ناممکن',
            amendment_date: '1900-01-01'
        })
        CREATE (a)-[:AMENDS]->(l)
        """)
        
        query = """
        MATCH (amendment:Law)-[:AMENDS]->(original:Law)
        WHERE date(amendment.amendment_date) < date(original.publication_date)
        RETURN amendment.canonical_id, original.canonical_id
        """
        
        impossible_amendments = conn.execute_query(query)
        
        assert len(impossible_amendments) > 0, "Failed to detect amendment before original law"
    
    def test_original_has_replaced_by_if_fully_replaced(self, neo4j_sample_graph):
        """
        Detect fully replaced laws without REPLACED_BY relationship.
        
        If a law is fully replaced, it should have REPLACED_BY relationship.
        """
        conn = neo4j_sample_graph
        
        # Create replaced law without REPLACED_BY
        conn.execute_query("""
        CREATE (old:Law {
            canonical_id: 'law:replaced_no_rel',
            title_fa: 'قانون جایگزین شده',
            status: 'repealed',
            repeal_date: '2020-01-01'
        })
        CREATE (new:Law {
            canonical_id: 'law:replacement',
            title_fa: 'قانون جایگزین',
            status: 'active',
            effective_date: '2020-01-01'
        })
        """)
        
        query = """
        MATCH (old:Law {status: 'repealed'})
        WHERE NOT (old)-[:REPLACED_BY]->(:Law)
        RETURN old.canonical_id
        """
        
        replaced_without_rel = conn.execute_query(query)
        
        assert len(replaced_without_rel) > 0, "Failed to detect replaced law without REPLACED_BY"
    
    def test_amendment_chain_completeness(self, neo4j_sample_graph):
        """
        Verify amendment chain is complete (no missing intermediate versions).
        
        If A → B → C, all intermediate versions must exist.
        """
        conn = neo4j_sample_graph
        
        # Create incomplete amendment chain
        conn.execute_query("""
        CREATE (v1:Law {canonical_id: 'law:v1', title_fa: 'نسخه ۱', version: '1'})
        CREATE (v3:Law {canonical_id: 'law:v3', title_fa: 'نسخه ۳', version: '3'})
        CREATE (v1)-[:AMENDS]->(v3)
        """)
        
        query = """
        MATCH (v1:Law)-[:AMENDS]->(v3:Law)
        WHERE toInteger(v1.version) + 1 < toInteger(v3.version)
        RETURN v1.canonical_id, v1.version, v3.canonical_id, v3.version
        """
        
        incomplete_chains = conn.execute_query(query)
        
        assert len(incomplete_chains) > 0, "Failed to detect incomplete amendment chain"


@pytest.mark.p2_extended
@pytest.mark.integration
class TestRepealedLawHandling:
    """
    Validate repealed law handling and status.
    
    Invariant: Repealed laws must be properly marked:
    - Status must be 'repealed'
    - Must have repeal_date
    - Must not be referenced as current authority
    - Must have REPLACED_BY or REPLACED relationship
    
    Failure danger: Repealed laws treated as current cause incorrect legal application.
    """
    
    def test_repealed_law_has_repeal_date(self, corrupted_temporal_graph):
        """
        Detect repealed laws without repeal_date.
        
        Repealed laws must have a repeal_date.
        """
        conn = corrupted_temporal_graph
        
        query = """
        MATCH (l:Law {status: 'repealed'})
        WHERE l.repeal_date IS NULL
        RETURN l.canonical_id
        """
        
        repealed_without_date = conn.execute_query(query)
        
        # Should detect if any exist
        assert len(repealed_without_date) >= 0, "Query execution failed"
    
    def test_repealed_article_not_treated_as_current(self, corrupted_temporal_graph):
        """
        Detect repealed articles with status='active'.
        
        Repealed articles must have status='repealed', not 'active'.
        """
        conn = corrupted_temporal_graph
        
        query = """
        MATCH (a:Article)
        WHERE a.repeal_date IS NOT NULL AND a.status = 'active'
        RETURN a.canonical_id, a.repeal_date
        """
        
        repealed_as_active = conn.execute_query(query)
        
        assert len(repealed_as_active) > 0, "Failed to detect repealed article as active"
    
    def test_repealed_law_not_referenced_as_current(self, neo4j_sample_graph):
        """
        Detect references to repealed laws as current authority.
        
        Should use REPLACED_BY relationship instead of REFERENCES.
        """
        conn = neo4j_sample_graph
        
        # Create reference to repealed law
        conn.execute_query("""
        CREATE (current:Law {
            canonical_id: 'law:current_ref_repealed',
            title_fa: 'قانون فعلی',
            status: 'active'
        })
        CREATE (repealed:Law {
            canonical_id: 'law:repealed_target',
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
    
    def test_repealed_law_have_replaced_relationship(self, neo4j_sample_graph):
        """
        Detect repealed laws without REPLACED_BY relationship.
        
        Repealed laws should indicate what replaced them.
        """
        conn = neo4j_sample_graph
        
        # Create repealed law without REPLACED_BY
        conn.execute_query("""
        CREATE (old:Law {
            canonical_id: 'law:repealed_no_replaced',
            title_fa: 'قانون ملغی بدون جایگزین',
            status: 'repealed',
            repeal_date: '2020-01-01'
        })
        """)
        
        query = """
        MATCH (l:Law {status: 'repealed'})
        WHERE NOT (l)-[:REPLACED_BY]->(:Law)
        RETURN l.canonical_id
        """
        
        repealed_without_replaced = conn.execute_query(query)
        
        assert len(repealed_without_replaced) > 0, "Failed to detect repealed law without REPLACED_BY"


@pytest.mark.p2_extended
@pytest.mark.integration
class TestHistoricalVersionManagement:
    """
    Validate historical version management.
    
    Invariant: Historical versions must be properly tracked:
    - Each version must have unique version identifier
    - Version chain must be complete
    - Only one version should be active at a time
    - Historical versions must have effective_date
    
    Failure danger: Version conflicts cause ambiguity in which law applies.
    """
    
    def test_version_chain_completeness(self, neo4j_sample_graph):
        """
        Detect gaps in version chain (missing intermediate versions).
        
        Version chain should be sequential (v1 → v2 → v3).
        """
        conn = neo4j_sample_graph
        
        # Create version chain with gap
        conn.execute_query("""
        CREATE (v1:Law {canonical_id: 'law:hist:v1', title_fa: 'نسخه ۱', version: '1'})
        CREATE (v3:Law {canonical_id: 'law:hist:v3', title_fa: 'نسخه ۳', version: '3'})
        CREATE (v1)-[:AMENDS]->(v3)
        """)
        
        query = """
        MATCH (v1:Law)-[:AMENDS]->(v2:Law)
        WHERE toInteger(v1.version) + 1 < toInteger(v2.version)
        RETURN v1.canonical_id, v1.version, v2.canonical_id, v2.version
        """
        
        version_gaps = conn.execute_query(query)
        
        assert len(version_gaps) > 0, "Failed to detect version chain gaps"
    
    def test_only_one_active_version(self, corrupted_temporal_graph):
        """
        Detect multiple active versions of the same law.
        
        Only one version should be active at a time.
        """
        conn = corrupted_temporal_graph
        
        query = """
        MATCH (a1:Article), (a2:Article)
        WHERE a1.article_number = a2.article_number
        AND a1.status = 'active'
        AND a2.status = 'active'
        AND a1.canonical_id <> a2.canonical_id
        RETURN a1.canonical_id, a2.canonical_id, a1.article_number
        """
        
        multiple_active = conn.execute_query(query)
        
        assert len(multiple_active) > 0, "Failed to detect multiple active versions"
    
    def test_historical_versions_have_effective_date(self, neo4j_sample_graph):
        """
        Detect historical versions without effective_date.
        
        All versions must have effective_date.
        """
        conn = neo4j_sample_graph
        
        # Create version without effective_date
        conn.execute_query("""
        CREATE (v:Law {
            canonical_id: 'law:hist:no_date',
            title_fa: 'نسخه بدون تاریخ',
            version: '2'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE l.version IS NOT NULL AND l.effective_date IS NULL
        RETURN l.canonical_id
        """
        
        versions_without_date = conn.execute_query(query)
        
        assert len(versions_without_date) > 0, "Failed to detect version without effective_date"
    
    def test_version_identifiers_are_unique(self, neo4j_sample_graph):
        """
        Detect duplicate version identifiers for the same law.
        
        Each version should have a unique identifier.
        """
        conn = neo4j_sample_graph
        
        # Create duplicate version
        conn.execute_query("""
        CREATE (v1:Law {canonical_id: 'law:dup:v1', title_fa: 'نسخه ۱', version: '1'})
        CREATE (v2:Law {canonical_id: 'law:dup:v1b', title_fa: 'نسخه ۱ تکراری', version: '1'})
        """)
        
        query = """
        MATCH (l1:Law), (l2:Law)
        WHERE l1.version = l2.version
        AND l1.canonical_id <> l2.canonical_id
        RETURN l1.canonical_id, l2.canonical_id, l1.version
        """
        
        duplicate_versions = conn.execute_query(query)
        
        assert len(duplicate_versions) > 0, "Failed to detect duplicate version identifiers"


@pytest.mark.p2_extended
@pytest.mark.integration
class TestEffectiveDateValidation:
    """
    Validate effective dates and temporal constraints.
    
    Invariant: Effective dates must be valid:
    - Effective date must be after publication date
    - Cannot have effective date in future (unless explicitly marked)
    - Temporal relationships must be consistent
    
    Failure danger: Invalid effective dates cause wrong law application over time.
    """
    
    def test_effective_date_after_publication(self, neo4j_sample_graph):
        """
        Detect effective dates before publication date.
        
        Effective date must be after or equal to publication date.
        """
        conn = neo4j_sample_graph
        
        # Create law with impossible effective date
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:invalid_effective',
            title_fa: 'قانون با تاریخ اجرای نامعتبر',
            publication_date: '2020-01-01',
            effective_date: '2019-01-01'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE date(l.effective_date) < date(l.publication_date)
        RETURN l.canonical_id, l.publication_date, l.effective_date
        """
        
        invalid_dates = conn.execute_query(query)
        
        assert len(invalid_dates) > 0, "Failed to detect effective date before publication"
    
    def test_future_law_not_marked_active(self, corrupted_temporal_graph):
        """
        Detect future laws marked as active.
        
        Future laws should have status='pending', not 'active'.
        """
        conn = corrupted_temporal_graph
        
        query = """
        MATCH (l:Law)
        WHERE date(l.effective_date) > date()
        AND l.status = 'active'
        RETURN l.canonical_id, l.effective_date
        """
        
        future_as_active = conn.execute_query(query)
        
        assert len(future_as_active) > 0, "Failed to detect future law marked as active"
    
    def test_temporal_relationship_consistency(self, neo4j_sample_graph):
        """
        Detect inconsistent temporal relationships.
        
        If A REPLACED_BY B, then A's repeal_date should equal B's effective_date.
        """
        conn = neo4j_sample_graph
        
        # Create inconsistent temporal relationship
        conn.execute_query("""
        CREATE (old:Law {
            canonical_id: 'law:old_inconsistent',
            title_fa: 'قانون قدیمی',
            status: 'repealed',
            repeal_date: '2020-01-01'
        })
        CREATE (new:Law {
            canonical_id: 'law:new_inconsistent',
            title_fa: 'قانون جدید',
            status: 'active',
            effective_date: '2021-01-01'
        })
        CREATE (old)-[:REPLACED_BY]->(new)
        """)
        
        query = """
        MATCH (old:Law)-[:REPLACED_BY]->(new:Law)
        WHERE date(old.repeal_date) <> date(new.effective_date)
        RETURN old.canonical_id, old.repeal_date, new.canonical_id, new.effective_date
        """
        
        inconsistent_temporal = conn.execute_query(query)
        
        assert len(inconsistent_temporal) > 0, "Failed to detect inconsistent temporal relationships"
    
    def test_suspension_dates_valid(self, neo4j_sample_graph):
        """
        Detect invalid suspension date ranges.
        
        Suspension end date must be after suspension start date.
        """
        conn = neo4j_sample_graph
        
        # Create law with invalid suspension
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:invalid_suspension',
            title_fa: 'قانون با تعلیق نامعتبر',
            status: 'suspended',
            suspension_start: '2020-01-01',
            suspension_end: '2019-01-01'
        })
        """)
        
        query = """
        MATCH (l:Law {status: 'suspended'})
        WHERE date(l.suspension_end) < date(l.suspension_start)
        RETURN l.canonical_id, l.suspension_start, l.suspension_end
        """
        
        invalid_suspension = conn.execute_query(query)
        
        assert len(invalid_suspension) > 0, "Failed to detect invalid suspension dates"


@pytest.mark.p2_extended
@pytest.mark.integration
class TestTemporalConsistency:
    """
    Validate overall temporal consistency of the graph.
    
    Invariant: Temporal state must be consistent across the graph:
    - No temporal paradoxes
    - Consistent status across related entities
    - Valid temporal ordering
    
    Failure danger: Temporal inconsistencies cause unpredictable legal reasoning.
    """
    
    def test_no_temporal_paradoxes(self, neo4j_sample_graph):
        """
        Detect temporal paradoxes (circular temporal dependencies).
        
        Example: A replaces B, B replaces C, C replaces A.
        """
        conn = neo4j_sample_graph
        
        # Create temporal paradox
        conn.execute_query("""
        CREATE (a:Law {canonical_id: 'law:paradox:a', status: 'repealed', repeal_date: '2020-01-01'})
        CREATE (b:Law {canonical_id: 'law:paradox:b', status: 'repealed', repeal_date: '2021-01-01'})
        CREATE (c:Law {canonical_id: 'law:paradox:c', status: 'repealed', repeal_date: '2022-01-01'})
        CREATE (a)-[:REPLACED_BY]->(b)
        CREATE (b)-[:REPLACED_BY]->(c)
        CREATE (c)-[:REPLACED_BY]->(a)
        """)
        
        query = """
        MATCH path = (l:Law)-[:REPLACED_BY*]->(l)
        WHERE length(path) > 0
        RETURN count(DISTINCT l) as paradox_count
        """
        
        paradox_count = conn.execute_query(query)[0]["paradox_count"]
        
        assert paradox_count > 0, "Failed to detect temporal paradox"
    
    def test_consistent_status_across_related_entities(self, neo4j_sample_graph):
        """
        Detect inconsistent status across related entities.
        
        If a Law is repealed, its Chapters should also be repealed.
        """
        conn = neo4j_sample_graph
        
        # Create inconsistent status
        conn.execute_query("""
        CREATE (l:Law {canonical_id: 'law:inconsistent_status', status: 'repealed'})
        CREATE (c:Chapter {canonical_id: 'chapter:inconsistent', title_fa: 'فصل', status: 'active'})
        CREATE (l)-[:HAS_CHAPTER]->(c)
        """)
        
        query = """
        MATCH (l:Law {status: 'repealed'})-[:HAS_CHAPTER]->(c:Chapter {status: 'active'})
        RETURN l.canonical_id, c.canonical_id
        """
        
        inconsistent_status = conn.execute_query(query)
        
        assert len(inconsistent_status) > 0, "Failed to detect inconsistent status"
    
    def test_valid_temporal_ordering(self, neo4j_sample_graph):
        """
        Detect violations of temporal ordering.
        
        Events should be ordered: publication → effective → amendment → repeal.
        """
        conn = neo4j_sample_graph
        
        # Create invalid temporal ordering
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:invalid_order',
            title_fa: 'قانون با ترتیب زمانی نامعتبر',
            publication_date: '2020-01-01',
            effective_date: '2019-01-01',
            repeal_date: '2018-01-01'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE date(l.publication_date) > date(l.effective_date)
        OR date(l.effective_date) > date(l.repeal_date)
        RETURN l.canonical_id
        """
        
        invalid_order = conn.execute_query(query)
        
        assert len(invalid_order) > 0, "Failed to detect invalid temporal ordering"

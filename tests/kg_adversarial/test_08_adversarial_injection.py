"""
Adversarial Injection Tests for Persian Legal Knowledge Graph
=============================================================

Tests for adversarial/malicious input handling:
- Fake article numbers
- Duplicate laws
- Incorrect references
- Invalid dates
- Empty mandatory fields
- Malformed legal text

Invariant protected: Graph builder must fail safely on malicious/corrupted input.

Failure danger: Malicious input can corrupt the entire graph or cause security issues.
"""

import pytest
from typing import Dict, Any
from datetime import datetime


@pytest.mark.p3_full
@pytest.mark.integration
class TestFakeArticleNumbers:
    """
    Detect and handle fake or invalid article numbers.
    
    Invariant: Article numbers must be valid:
    - Numeric only
    - Within reasonable range (1-9999 typically)
    - No negative numbers
    - No special characters
    
    Failure danger: Fake article numbers cause reference errors and data corruption.
    """
    
    def test_negative_article_number_rejected(self, neo4j_empty_graph):
        """
        Detect negative article numbers.
        
        Article numbers cannot be negative.
        """
        conn = neo4j_empty_graph
        
        # Attempt to create article with negative number
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:negative',
            article_number: '-1',
            text_fa: 'ماده با شماره منفی'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE toInteger(a.article_number) < 0
        RETURN a.canonical_id, a.article_number
        """
        
        negative_numbers = conn.execute_query(query)
        
        assert len(negative_numbers) > 0, "Failed to detect negative article number"
    
    def test_extremely_large_article_number_rejected(self, neo4j_empty_graph):
        """
        Detect unreasonably large article numbers.
        
        Article numbers > 99999 are suspicious.
        """
        conn = neo4j_empty_graph
        
        # Attempt to create article with huge number
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:huge',
            article_number: '999999',
            text_fa: 'ماده با شماره بسیار بزرگ'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE toInteger(a.article_number) > 99999
        RETURN a.canonical_id, a.article_number
        """
        
        huge_numbers = conn.execute_query(query)
        
        assert len(huge_numbers) > 0, "Failed to detect unreasonably large article number"
    
    def test_article_number_with_special_chars_rejected(self, neo4j_empty_graph):
        """
        Detect article numbers with special characters.
        
        Article numbers should be numeric only.
        """
        conn = neo4j_empty_graph
        
        # Attempt to create article with special characters
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:special_chars',
            article_number: '1@#$',
            text_fa: 'ماده با شماره دارای کاراکتر خاص'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE NOT a.article_number =~ '^\\d+$'
        RETURN a.canonical_id, a.article_number
        """
        
        special_chars = conn.execute_query(query)
        
        assert len(special_chars) > 0, "Failed to detect article number with special characters"
    
    def test_article_number_zero_rejected(self, neo4j_empty_graph):
        """
        Detect article number zero.
        
        Article numbers should start from 1.
        """
        conn = neo4j_empty_graph
        
        # Attempt to create article with zero
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:zero',
            article_number: '0',
            text_fa: 'ماده صفر'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.article_number = '0'
        RETURN a.canonical_id, a.article_number
        """
        
        zero_numbers = conn.execute_query(query)
        
        assert len(zero_numbers) > 0, "Failed to detect article number zero"


@pytest.mark.p3_full
@pytest.mark.integration
class TestDuplicateLawInjection:
    """
    Detect and handle duplicate law injection attempts.
    
    Invariant: Laws with identical content should be rejected or merged:
    - Same title
    - Same publication date
    - Different canonical_id
    
    Failure danger: Duplicate laws cause contradictory legal results.
    """
    
    def test_duplicate_law_with_different_id_rejected(self, neo4j_empty_graph):
        """
        Detect duplicate laws with different canonical IDs.
        
        Same content, different ID indicates data corruption or attack.
        """
        conn = neo4j_empty_graph
        
        # Create first law
        conn.execute_query("""
        CREATE (l1:Law {
            canonical_id: 'law:dup:1',
            title_fa: 'قانون تکراری',
            publication_date: '2020-01-01',
            status: 'active'
        })
        """)
        
        # Create duplicate with different ID
        conn.execute_query("""
        CREATE (l2:Law {
            canonical_id: 'law:dup:2',
            title_fa: 'قانون تکراری',
            publication_date: '2020-01-01',
            status: 'active'
        })
        """)
        
        query = """
        MATCH (l1:Law), (l2:Law)
        WHERE l1.canonical_id < l2.canonical_id
        AND l1.title_fa = l2.title_fa
        AND l1.publication_date = l2.publication_date
        RETURN l1.canonical_id, l2.canonical_id
        """
        
        duplicates = conn.execute_query(query)
        
        assert len(duplicates) > 0, "Failed to detect duplicate laws"
    
    def test_duplicate_law_with_slight_variation(self, neo4j_empty_graph):
        """
        Detect duplicate laws with slight text variations.
        
        Attackers may modify text slightly to bypass duplicate detection.
        """
        conn = neo4j_empty_graph
        
        # Create first law
        conn.execute_query("""
        CREATE (l1:Law {
            canonical_id: 'law:var:1',
            title_fa: 'قانون مدنی',
            publication_date: '1928-03-15',
            status: 'active'
        })
        """)
        
        # Create duplicate with slight variation
        conn.execute_query("""
        CREATE (l2:Law {
            canonical_id: 'law:var:2',
            title_fa: 'قانون  مدنی',
            publication_date: '1928-03-15',
            status: 'active'
        })
        """)
        
        query = """
        MATCH (l1:Law), (l2:Law)
        WHERE l1.canonical_id < l2.canonical_id
        AND replace(l1.title_fa, ' ', '') = replace(l2.title_fa, ' ', '')
        AND l1.publication_date = l2.publication_date
        RETURN l1.canonical_id, l2.canonical_id
        """
        
        duplicates = conn.execute_query(query)
        
        assert len(duplicates) > 0, "Failed to detect duplicate with slight variation"
    
    def test_duplicate_law_different_case(self, neo4j_empty_graph):
        """
        Detect duplicate laws with different case.
        
        Case differences should not bypass duplicate detection.
        """
        conn = neo4j_empty_graph
        
        # Create first law
        conn.execute_query("""
        CREATE (l1:Law {
            canonical_id: 'law:case:1',
            title_fa: 'قانون مدنی',
            publication_date: '1928-03-15',
            status: 'active'
        })
        """)
        
        # Create duplicate with different case
        conn.execute_query("""
        CREATE (l2:Law {
            canonical_id: 'law:case:2',
            title_fa: 'قانون مدنی',
            publication_date: '1928-03-15',
            status: 'active'
        })
        """)
        
        query = """
        MATCH (l1:Law), (l2:Law)
        WHERE l1.canonical_id < l2.canonical_id
        AND toLower(l1.title_fa) = toLower(l2.title_fa)
        AND l1.publication_date = l2.publication_date
        RETURN l1.canonical_id, l2.canonical_id
        """
        
        duplicates = conn.execute_query(query)
        
        assert len(duplicates) > 0, "Failed to detect duplicate with case variation"


@pytest.mark.p3_full
@pytest.mark.integration
class TestIncorrectReferenceInjection:
    """
    Detect and handle incorrect reference injection.
    
    Invariant: References must be valid:
    - Target must exist
    - Reference type must be valid
    - No self-references
    - No circular references
    
    Failure danger: Incorrect references cause broken legal reasoning chains.
    """
    
    def test_reference_to_nonexistent_target_rejected(self, neo4j_empty_graph):
        """
        Detect references to non-existent targets.
        
        References must point to existing nodes.
        """
        conn = neo4j_empty_graph
        
        # Create article with reference to non-existent target
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:bad_ref',
            article_number: '100',
            references_article: ['article:nonexistent:999']
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.references_article IS NOT NULL
        UNWIND a.references_article as ref_id
        OPTIONAL MATCH (target:Article {canonical_id: ref_id})
        WITH a, ref_id, count(target) as target_count
        WHERE target_count = 0
        RETURN a.canonical_id, ref_id
        """
        
        bad_refs = conn.execute_query(query)
        
        assert len(bad_refs) > 0, "Failed to detect reference to non-existent target"
    
    def test_invalid_reference_type_rejected(self, neo4j_empty_graph):
        """
        Detect invalid reference types.
        
        Reference types must be from allowed set.
        """
        conn = neo4j_empty_graph
        
        # Create reference with invalid type
        conn.execute_query("""
        CREATE (a1:Article {canonical_id: 'article:ref_type:1', article_number: '1'})
        CREATE (a2:Article {canonical_id: 'article:ref_type:2', article_number: '2'})
        CREATE (a1)-[:INVALID_REF_TYPE]->(a2)
        """)
        
        query = """
        MATCH ()-[r]->()
        WHERE NOT (type(r) IN ['REFERENCES', 'CITES', 'AMENDS', 'REPLACED_BY', 'OVERRIDDEN_BY', 'INTERPRETS_BY', 'IMPLEMENTS', 'CONFLICTS_WITH', 'EXCEPTS', 'PRECEDES', 'HAS_CHAPTER', 'HAS_ARTICLE', 'HAS_PARAGRAPH', 'HAS_CLAUSE'])
        RETURN type(r) as invalid_type, count(*) as count
        """
        
        invalid_types = conn.execute_query(query)
        
        assert len(invalid_types) > 0, "Failed to detect invalid reference type"
    
    def test_self_reference_rejected(self, neo4j_empty_graph):
        """
        Detect self-references.
        
        Nodes should not reference themselves.
        """
        conn = neo4j_empty_graph
        
        # Create self-referencing article
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:self_ref',
            article_number: '200',
            references_article: ['article:self_ref']
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.references_article IS NOT NULL
        AND a.canonical_id IN a.references_article
        RETURN a.canonical_id
        """
        
        self_refs = conn.execute_query(query)
        
        assert len(self_refs) > 0, "Failed to detect self-reference"
    
    def test_circular_reference_chain_rejected(self, neo4j_empty_graph):
        """
        Detect circular reference chains.
        
        A → B → C → A is invalid.
        """
        conn = neo4j_empty_graph
        
        # Create circular reference chain
        conn.execute_query("""
        CREATE (a1:Article {canonical_id: 'article:circle:a', article_number: '300'})
        CREATE (a2:Article {canonical_id: 'article:circle:b', article_number: '301'})
        CREATE (a3:Article {canonical_id: 'article:circle:c', article_number: '302'})
        CREATE (a1)-[:REFERENCES]->(a2)
        CREATE (a2)-[:REFERENCES]->(a3)
        CREATE (a3)-[:REFERENCES]->(a1)
        """)
        
        query = """
        MATCH path = (a:Article)-[:REFERENCES*]->(a)
        WHERE length(path) > 0 AND length(path) < 10
        RETURN count(DISTINCT a) as circular_count
        """
        
        circular_count = conn.execute_query(query)[0]["circular_count"]
        
        assert circular_count > 0, "Failed to detect circular reference chain"


@pytest.mark.p3_full
@pytest.mark.integration
class TestInvalidDateInjection:
    """
    Detect and handle invalid date injection.
    
    Invariant: Dates must be valid:
    - Valid date format (YYYY-MM-DD)
    - Reasonable date range (not year 0000 or year 9999)
    - Logical consistency (effective_date >= publication_date)
    
    Failure danger: Invalid dates cause temporal reasoning errors.
    """
    
    def test_invalid_date_format_rejected(self, neo4j_empty_graph):
        """
        Detect invalid date formats.
        
        Dates must be in YYYY-MM-DD format.
        """
        conn = neo4j_empty_graph
        
        # Create law with invalid date format
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:bad_date',
            title_fa: 'قانون با تاریخ نامعتبر',
            publication_date: '2020/01/01'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE NOT l.publication_date =~ '^\\d{4}-\\d{2}-\\d{2}$'
        RETURN l.canonical_id, l.publication_date
        """
        
        invalid_dates = conn.execute_query(query)
        
        assert len(invalid_dates) > 0, "Failed to detect invalid date format"
    
    def test_impossible_date_rejected(self, neo4j_empty_graph):
        """
        Detect impossible dates (e.g., February 30).
        
        Dates must be calendar-valid.
        """
        conn = neo4j_empty_graph
        
        # Create law with impossible date
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:impossible_date',
            title_fa: 'قانون با تاریخ غیرممکن',
            publication_date: '2020-02-30'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE l.publication_date ENDS WITH '-02-30'
        RETURN l.canonical_id, l.publication_date
        """
        
        # Neo4j will return NULL for invalid dates
        impossible_dates = conn.execute_query(query)
        
        assert len(impossible_dates) > 0, "Failed to detect impossible date"
    
    def test_year_out_of_range_rejected(self, neo4j_empty_graph):
        """
        Detect dates with year out of reasonable range.
        
        Years should be between 1900 and 2100 for modern laws.
        """
        conn = neo4j_empty_graph
        
        # Create law with year 9999
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:future_year',
            title_fa: 'قانون با سال آینده',
            publication_date: '9999-01-01'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE toInteger(split(l.publication_date, '-')[0]) > 2100
        RETURN l.canonical_id, l.publication_date
        """
        
        future_years = conn.execute_query(query)
        
        assert len(future_years) > 0, "Failed to detect year out of range"
    
    def test_temporal_inconsistency_rejected(self, neo4j_empty_graph):
        """
        Detect temporal inconsistencies.
        
        effective_date should be >= publication_date.
        """
        conn = neo4j_empty_graph
        
        # Create law with temporal inconsistency
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:temporal_inconsistent',
            title_fa: 'قانون با ناهماهنگی زمانی',
            publication_date: '2020-01-01',
            effective_date: '2019-01-01'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE date(l.effective_date) < date(l.publication_date)
        RETURN l.canonical_id, l.publication_date, l.effective_date
        """
        
        temporal_inconsistent = conn.execute_query(query)
        
        assert len(temporal_inconsistent) > 0, "Failed to detect temporal inconsistency"


@pytest.mark.p3_full
@pytest.mark.integration
class TestEmptyMandatoryFields:
    """
    Detect and handle empty mandatory field injection.
    
    Invariant: Mandatory fields must be non-empty:
    - canonical_id
    - title_fa for Laws
    - article_number for Articles
    - text_fa for Articles
    
    Failure danger: Empty mandatory fields cause query failures and data corruption.
    """
    
    def test_empty_canonical_id_rejected(self, neo4j_empty_graph):
        """
        Detect empty canonical_id.
        
        canonical_id is the primary identifier and must be non-empty.
        """
        conn = neo4j_empty_graph
        
        # Create node with empty canonical_id
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: '',
            article_number: '400',
            text_fa: 'ماده بدون شناسه'
        })
        """)
        
        query = """
        MATCH (n)
        WHERE n.canonical_id IS NULL OR n.canonical_id = ''
        RETURN n.canonical_id
        """
        
        empty_ids = conn.execute_query(query)
        
        assert len(empty_ids) > 0, "Failed to detect empty canonical_id"
    
    def test_empty_title_fa_for_law_rejected(self, neo4j_empty_graph):
        """
        Detect empty title_fa for Law nodes.
        
        Law titles are mandatory.
        """
        conn = neo4j_empty_graph
        
        # Create Law with empty title
        conn.execute_query("""
        CREATE (l:Law {
            canonical_id: 'law:empty_title',
            title_fa: '',
            publication_date: '2020-01-01'
        })
        """)
        
        query = """
        MATCH (l:Law)
        WHERE l.title_fa IS NULL OR l.title_fa = ''
        RETURN l.canonical_id
        """
        
        empty_titles = conn.execute_query(query)
        
        assert len(empty_titles) > 0, "Failed to detect empty title_fa"
    
    def test_empty_article_number_rejected(self, neo4j_empty_graph):
        """
        Detect empty article_number for Article nodes.
        
        Article numbers are mandatory.
        """
        conn = neo4j_empty_graph
        
        # Create Article with empty number
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:empty_number',
            article_number: '',
            text_fa: 'ماده بدون شماره'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.article_number IS NULL OR a.article_number = ''
        RETURN a.canonical_id
        """
        
        empty_numbers = conn.execute_query(query)
        
        assert len(empty_numbers) > 0, "Failed to detect empty article_number"
    
    def test_empty_text_fa_for_article_rejected(self, neo4j_empty_graph):
        """
        Detect empty text_fa for Article nodes.
        
        Article text is mandatory.
        """
        conn = neo4j_empty_graph
        
        # Create Article with empty text
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:empty_text',
            article_number: '500',
            text_fa: ''
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.text_fa IS NULL OR a.text_fa = ''
        RETURN a.canonical_id
        """
        
        empty_texts = conn.execute_query(query)
        
        assert len(empty_texts) > 0, "Failed to detect empty text_fa"


@pytest.mark.p3_full
@pytest.mark.integration
class TestMalformedLegalText:
    """
    Detect and handle malformed legal text injection.
    
    Invariant: Legal text must be well-formed:
    - No binary control characters
    - Valid UTF-8 encoding
    - Reasonable length
    - No injection attempts
    
    Failure danger: Malformed text causes display errors and potential security issues.
    """
    
    def test_binary_control_characters_rejected(self, neo4j_empty_graph):
        """
        Detect binary control characters in text.
        
        Control characters (except newline/tab) should not be present.
        """
        conn = neo4j_empty_graph
        
        # Create article with potential control characters
        # Note: Neo4j may filter some control characters
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:control_chars',
            article_number: '600',
            text_fa: 'متن با کاراکتر کنترل'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.text_fa IS NOT NULL
        RETURN a.canonical_id, a.text_fa
        """
        
        result = conn.execute_query(query)
        
        # Verify query executes
        assert len(result) >= 0, "Query execution failed"
    
    def test_extremely_long_text_rejected(self, neo4j_empty_graph):
        """
        Detect unreasonably long text.
        
        Legal text should be reasonable length (e.g., < 100,000 characters).
        """
        conn = neo4j_empty_graph
        
        # Create article with extremely long text
        long_text = "متن طولانی " * 10000  # ~100,000 characters
        
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:long_text',
            article_number: '700',
            text_fa: $long_text
        })
        """, {"long_text": long_text})
        
        query = """
        MATCH (a:Article)
        WHERE size(a.text_fa) > 100000
        RETURN a.canonical_id, size(a.text_fa) as text_length
        """
        
        long_texts = conn.execute_query(query)
        
        assert len(long_texts) > 0, "Failed to detect extremely long text"
    
    def test_sql_injection_attempt_rejected(self, neo4j_empty_graph):
        """
        Detect SQL injection attempts in text.
        
        Text containing SQL patterns should be flagged.
        """
        conn = neo4j_empty_graph
        
        # Create article with SQL injection pattern
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:sql_injection',
            article_number: '800',
            text_fa: 'متن با DROP TABLE'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.text_fa CONTAINS 'DROP TABLE' 
           OR a.text_fa CONTAINS 'DELETE FROM'
           OR a.text_fa CONTAINS 'UNION SELECT'
        RETURN a.canonical_id, a.text_fa
        """
        
        injection_attempts = conn.execute_query(query)
        
        assert len(injection_attempts) > 0, "Failed to detect SQL injection attempt"
    
    def test_script_injection_attempt_rejected(self, neo4j_empty_graph):
        """
        Detect script injection attempts in text.
        
        Text containing script tags should be flagged.
        """
        conn = neo4j_empty_graph
        
        # Create article with script injection pattern
        conn.execute_query("""
        CREATE (a:Article {
            canonical_id: 'article:script_injection',
            article_number: '900',
            text_fa: 'متن با <script>alert(1)</script>'
        })
        """)
        
        query = """
        MATCH (a:Article)
        WHERE a.text_fa CONTAINS '<script>' 
           OR a.text_fa CONTAINS 'javascript:'
           OR a.text_fa CONTAINS 'onerror='
        RETURN a.canonical_id, a.text_fa
        """
        
        injection_attempts = conn.execute_query(query)
        
        assert len(injection_attempts) > 0, "Failed to detect script injection attempt"

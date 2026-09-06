"""
Pytest fixtures for Persian Legal Knowledge Graph adversarial tests
====================================================================

Provides Neo4j fixtures, sample data, and corrupted graph fixtures for
comprehensive adversarial testing.
"""

import os
import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator, List, Optional
from unittest.mock import Mock


class Neo4jTestConnection:
    """Small test adapter preserving both fixture access conventions."""

    def __init__(self, driver: Any, execute_query: Any) -> None:
        self.driver = driver
        self.execute_query = execute_query

    def __getitem__(self, key: str) -> Any:
        if key == "driver":
            return self.driver
        if key == "execute_query":
            return self.execute_query
        raise KeyError(key)

# =============================================================================
# Test Configuration
# =============================================================================

def pytest_configure(config):
    """Register custom pytest markers for KG adversarial tests."""
    markers = [
        "p0_critical: P0 critical path tests (structural integrity, ontology)",
        "p1_integration: P1 high-value integration tests (reference integrity, semantic consistency)",
        "p2_extended: P2 regression protection tests (temporal, data quality)",
        "p3_full: P3 optional tests (idempotency, adversarial injection, fingerprint, query)",
        "integration: Requires Neo4j connection",
        "slow: Slow to run (large data, complex operations)",
        "unit: Fast unit tests with no external dependencies",
    ]
    for marker in markers:
        config.addinivalue_line("markers", marker)


# =============================================================================
# Neo4j Connection Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def neo4j_test_config() -> Dict[str, str]:
    """
    Neo4j test configuration from environment variables.
    
    Falls back to test defaults if not set.
    """
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("DB_NEO4J_PASSWORD", "dev_neo4j_password_2026"),
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }


@pytest.fixture(scope="function")
def neo4j_empty_graph(neo4j_test_config: Dict[str, str]) -> Generator[Any, None, None]:
    """
    Empty Neo4j database for isolated tests.
    
    Clears all data before test and after test.
    Skipped if Neo4j is not available.
    
    Uses direct Neo4j driver for test setup to bypass governance inspection.
    """
    try:
        from neo4j import GraphDatabase
        
        # Direct driver connection for test purposes (bypasses governance)
        driver = GraphDatabase.driver(
            neo4j_test_config["uri"],
            auth=(neo4j_test_config["user"], neo4j_test_config["password"]),
            connection_timeout=2,
            connection_acquisition_timeout=2,
            max_transaction_retry_time=0,
        )
        
        # Verify connection
        driver.verify_connectivity()
        
        def execute_query(query: str, parameters: Dict = None) -> List[Any]:
            """Execute query with direct driver."""
            with driver.session(database=neo4j_test_config["database"]) as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        
        # Clear all data
        execute_query("MATCH (n) DETACH DELETE n")
        
        yield Neo4jTestConnection(driver, execute_query)
        
        # Cleanup: clear all data
        execute_query("MATCH (n) DETACH DELETE n")
        driver.close()
        
    except ImportError:
        pytest.fail("Neo4j driver is required for kg_adversarial integration tests")
    except Exception as e:
        pytest.fail(
            "Neo4j integration service is unavailable; refusing to skip graph-health tests "
            f"({neo4j_test_config['uri']}): {e}"
        )


@pytest.fixture(scope="function")
def neo4j_sample_graph(neo4j_empty_graph: Any) -> Generator[Any, None, None]:
    """
    Neo4j database pre-populated with sample Persian legal data.
    
    Creates a minimal valid legal hierarchy:
    - Law (قانون مدنی)
    - Chapter (فصل اول)
    - Article (ماده ۱)
    - Paragraph (بند ۱)
    - Clause (تبصره ۱)
    """
    execute_query = neo4j_empty_graph["execute_query"]
    
    # Create sample legal hierarchy
    cypher_queries = [
        # Create Law
        """
        CREATE (l:Law {
            canonical_id: 'law:civil_code',
            title_fa: 'قانون مدنی',
            title_en: 'Civil Code',
            publication_date: '1928-03-15',
            status: 'active'
        })
        """,
        
        # Create Chapter
        """
        CREATE (c:Chapter {
            canonical_id: 'chapter:civil_code:chapter:1',
            title_fa: 'فصل اول: اصول کلی',
            title_en: 'Chapter 1: General Principles',
            chapter_number: '1'
        })
        """,
        
        # Create Article
        """
        CREATE (a:Article {
            canonical_id: 'article:civil_code:article:1',
            article_number: '1',
            title_fa: 'ماده ۱',
            text_fa: 'هیچ‌کس را نمی‌توان از داشتن مالکیت خود که قانونی باشد محروم کرد.',
            text_en: 'No one may be deprived of their lawful ownership.',
            status: 'active'
        })
        """,
        
        # Create Paragraph
        """
        CREATE (p:Paragraph {
            canonical_id: 'paragraph:civil_code:article:1:paragraph:1',
            paragraph_number: '1',
            text_fa: 'مالکیت حق اعمال حاکمیت مادی بر مال است.',
            text_en: 'Ownership is the right to exercise material authority over property.'
        })
        """,
        
        # Create Clause
        """
        CREATE (cl:Clause {
            canonical_id: 'clause:civil_code:article:1:clause:1',
            clause_number: '1',
            text_fa: 'این حق شامل حق استفاده، بهره‌برداری و تصرف در مال است.',
            text_en: 'This right includes the right to use, exploit, and dispose of the property.'
        })
        """,
        
        # Create relationships
        """
        MATCH (l:Law {canonical_id: 'law:civil_code'})
        MATCH (c:Chapter {canonical_id: 'chapter:civil_code:chapter:1'})
        CREATE (l)-[:HAS_CHAPTER]->(c)
        """,
        
        """
        MATCH (c:Chapter {canonical_id: 'chapter:civil_code:chapter:1'})
        MATCH (a:Article {canonical_id: 'article:civil_code:article:1'})
        CREATE (c)-[:HAS_ARTICLE]->(a)
        """,
        
        """
        MATCH (a:Article {canonical_id: 'article:civil_code:article:1'})
        MATCH (p:Paragraph {canonical_id: 'paragraph:civil_code:article:1:paragraph:1'})
        CREATE (a)-[:HAS_PARAGRAPH]->(p)
        """,
        
        """
        MATCH (p:Paragraph {canonical_id: 'paragraph:civil_code:article:1:paragraph:1'})
        MATCH (cl:Clause {canonical_id: 'clause:civil_code:article:1:clause:1'})
        CREATE (p)-[:HAS_CLAUSE]->(cl)
        """,
    ]
    
    for query in cypher_queries:
        execute_query(query)
    
    yield neo4j_empty_graph


# =============================================================================
# Corrupted Graph Fixtures for Adversarial Testing
# =============================================================================

@pytest.fixture(scope="function")
def corrupted_orphan_graph(neo4j_empty_graph: Any) -> Generator[Any, None, None]:
    """
    Graph with intentional orphan nodes for testing orphan detection.
    
    Creates:
    - Article without Law (orphan)
    - Chapter without parent Law (orphan)
    - Paragraph without Article (orphan)
    """
    # Check if this is a mock connection (no execute_query method or is Mock)
    if hasattr(neo4j_empty_graph, 'execute_query'):
        execute_query = neo4j_empty_graph["execute_query"]
    else:
        # This is our mock connection, just return it
        yield neo4j_empty_graph
        return
    
    # Create orphans (nodes without proper parent relationships) - only if real Neo4j
    cypher_queries = [
        # Orphan Article (no Law parent)
        """
        CREATE (a:Article {
            canonical_id: 'article:orphan:article:999',
            article_number: '999',
            title_fa: 'ماده یتیم',
            text_fa: 'این ماده بدون قانون والد است.',
            status: 'active'
        })
        """,
        
        # Orphan Chapter (no Law parent)
        """
        CREATE (c:Chapter {
            canonical_id: 'chapter:orphan:chapter:1',
            title_fa: 'فصل یتیم',
            chapter_number: '1'
        })
        """,
        
        # Orphan Paragraph (no Article parent)
        """
        CREATE (p:Paragraph {
            canonical_id: 'paragraph:orphan:paragraph:1',
            paragraph_number: '1',
            text_fa: 'این بند بدون ماده والد است.'
        })
        """,
        
        # Valid Law for comparison
        """
        CREATE (l:Law {
            canonical_id: 'law:valid',
            title_fa: 'قانون معتبر',
            status: 'active'
        })
        """,
    ]
    
    for query in cypher_queries:
        execute_query(query)
    
    yield neo4j_empty_graph


@pytest.fixture(scope="function")
def corrupted_duplicate_graph(neo4j_empty_graph: Any) -> Generator[Any, None, None]:
    """
    Graph with intentional duplicate entities for testing duplicate detection.
    
    Creates:
    - Duplicate Laws (same content, different IDs)
    - Duplicate Articles (same number, different IDs)
    - Same legal entity with multiple IDs
    """
    execute_query = neo4j_empty_graph["execute_query"]
    
    cypher_queries = [
        # Duplicate Law 1
        """
        CREATE (l1:Law {
            canonical_id: 'law:duplicate:1',
            title_fa: 'قانون تکراری',
            title_en: 'Duplicate Law',
            publication_date: '2020-01-01',
            status: 'active'
        })
        """,
        
        # Duplicate Law 2 (same content, different ID)
        """
        CREATE (l2:Law {
            canonical_id: 'law:duplicate:2',
            title_fa: 'قانون تکراری',
            title_en: 'Duplicate Law',
            publication_date: '2020-01-01',
            status: 'active'
        })
        """,
        
        # Duplicate Article 1
        """
        CREATE (a1:Article {
            canonical_id: 'article:duplicate:1',
            article_number: '100',
            title_fa: 'ماده ۱۰۰',
            text_fa: 'متن تکراری',
            status: 'active'
        })
        """,
        
        # Duplicate Article 2 (same number, different ID)
        """
        CREATE (a2:Article {
            canonical_id: 'article:duplicate:2',
            article_number: '100',
            title_fa: 'ماده ۱۰۰',
            text_fa: 'متن تکراری',
            status: 'active'
        })
        """,
    ]
    
    for query in cypher_queries:
        execute_query(query)
    
    yield neo4j_empty_graph


@pytest.fixture(scope="function")
def corrupted_reference_graph(neo4j_sample_graph: Any) -> Generator[Any, None, None]:
    """
    Graph with broken references for testing reference integrity.
    
    Creates:
    - Reference to non-existent article
    - Reference to non-existent law
    - Self-reference
    - Circular reference
    """
    execute_query = neo4j_sample_graph["execute_query"]
    
    cypher_queries = [
        # Article with reference to non-existent article
        """
        CREATE (a:Article {
            canonical_id: 'article:broken_ref:article:2',
            article_number: '2',
            title_fa: 'ماده با ارجاع خراب',
            text_fa: 'این ماده به ماده ۹۹۹ ارجاع دارد که وجود ندارد.',
            references_article: ['article:nonexistent:article:999'],
            status: 'active'
        })
        """,
        
        # Article with reference to non-existent law
        """
        CREATE (a2:Article {
            canonical_id: 'article:broken_ref:article:3',
            article_number: '3',
            title_fa: 'ماده با ارجاع قانون خراب',
            text_fa: 'این ماده به قانون غیرواقعی ارجاع دارد.',
            references_law: ['law:nonexistent'],
            status: 'active'
        })
        """,
        
        # Self-reference (article references itself)
        """
        CREATE (a3:Article {
            canonical_id: 'article:self_ref:article:4',
            article_number: '4',
            title_fa: 'ماده با ارجاع به خود',
            text_fa: 'این ماده به خود ارجاع دارد.',
            references_article: ['article:self_ref:article:4'],
            status: 'active'
        })
        """,
    ]
    
    for query in cypher_queries:
        execute_query(query)
    
    yield neo4j_sample_graph


@pytest.fixture(scope="function")
def corrupted_temporal_graph(neo4j_empty_graph: Any) -> Generator[Any, None, None]:
    """
    Graph with temporal integrity issues for testing temporal validation.
    
    Creates:
    - Future law appearing as active
    - Repealed article treated as current
    - Multiple active versions without resolution
    """
    execute_query = neo4j_empty_graph["execute_query"]
    
    from datetime import datetime, timedelta
    
    future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    
    cypher_queries = [
        # Future law (should not be active)
        f"""
        CREATE (l:Law {{
            canonical_id: 'law:future',
            title_fa: 'قانون آینده',
            effective_date: '{future_date}',
            status: 'active'
        }})
        """,
        
        # Repealed article treated as current
        """
        CREATE (a:Article {
            canonical_id: 'article:repealed_but_active',
            article_number: '500',
            title_fa: 'ماده ملغی',
            text_fa: 'این ماده ملغی شده اما وضعیت فعال دارد.',
            repeal_date: '2020-01-01',
            status: 'active'
        })
        """,
        
        # Multiple active versions of same article
        """
        CREATE (a1:Article {
            canonical_id: 'article:version_conflict:v1',
            article_number: '600',
            title_fa: 'ماده نسخه ۱',
            text_fa: 'نسخه اول',
            version: '1',
            status: 'active'
        })
        """,
        
        """
        CREATE (a2:Article {
            canonical_id: 'article:version_conflict:v2',
            article_number: '600',
            title_fa: 'ماده نسخه ۲',
            text_fa: 'نسخه دوم',
            version: '2',
            status: 'active'
        })
        """,
    ]
    
    for query in cypher_queries:
        execute_query(query)
    
    yield neo4j_empty_graph


# =============================================================================
# Mock Fixtures for Unit Tests (No Neo4j Required)
# =============================================================================

@pytest.fixture(scope="function")
def mock_neo4j_connection() -> Mock:
    """
    Mock Neo4j connection for unit tests without database.
    
    Provides a mock that simulates Neo4j operations without requiring
    an actual Neo4j instance.
    """
    mock_conn = Mock()
    mock_conn.verify_connectivity.return_value = True
    mock_conn.execute_query.return_value = []
    mock_conn._raw_execute.return_value = []
    
    return mock_conn


@pytest.fixture(scope="function")
def sample_legal_data() -> Dict[str, Any]:
    """
    Sample Persian legal data for unit tests.
    
    Returns a dictionary with sample legal entities in the expected format.
    """
    return {
        "law": {
            "canonical_id": "law:civil_code",
            "title_fa": "قانون مدنی",
            "title_en": "Civil Code",
            "publication_date": "1928-03-15",
            "status": "active",
        },
        "chapter": {
            "canonical_id": "chapter:civil_code:chapter:1",
            "title_fa": "فصل اول: اصول کلی",
            "title_en": "Chapter 1: General Principles",
            "chapter_number": "1",
        },
        "article": {
            "canonical_id": "article:civil_code:article:1",
            "article_number": "1",
            "title_fa": "ماده ۱",
            "text_fa": "هیچ‌کس را نمی‌توان از داشتن مالکیت خود که قانونی باشد محروم کرد.",
            "text_en": "No one may be deprived of their lawful ownership.",
            "status": "active",
        },
    }


@pytest.fixture(scope="function")
def temp_corpus_file() -> Generator[Path, None, None]:
    """
    Temporary file for corpus data testing.
    
    Creates a temporary file that is automatically cleaned up after the test.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("قانون اساسی جمهوری اسلامی ایران\n")
        f.write("فصل اول اصول کلی\n")
        f.write("اصل اول حکومت ایران جمهوری اسلامی است.\n")
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()

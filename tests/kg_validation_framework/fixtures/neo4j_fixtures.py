"""
Neo4j Fixtures for KG Validation Framework
==========================================

Provides Neo4j connection fixtures and graph state fixtures for testing.
"""

import pytest
from typing import Dict, Any, Generator
from unittest.mock import Mock


@pytest.fixture(scope="function")
def mock_graph_builder():
    """
    Mock graph builder for unit tests.
    
    Returns a Mock object that simulates graph operations.
    """
    builder = Mock()
    builder.query.return_value = []
    builder.execute_query.return_value = []
    return builder


@pytest.fixture(scope="function")
def sample_graph_state():
    """
    Sample valid graph state for testing.
    
    Returns a dictionary representing a valid legal knowledge graph.
    """
    return {
        "nodes": {
            "law:civil_code": {
                "label": "Law",
                "properties": {
                    "canonical_id": "law:civil_code",
                    "title_fa": "قانون مدنی",
                    "publication_date": "1928-03-15",
                    "status": "active"
                }
            },
            "chapter:civil_code:1": {
                "label": "Chapter",
                "properties": {
                    "canonical_id": "chapter:civil_code:1",
                    "title_fa": "فصل اول: اصول کلی",
                    "chapter_number": "1"
                }
            },
            "article:civil_code:1": {
                "label": "Article",
                "properties": {
                    "canonical_id": "article:civil_code:1",
                    "article_number": "1",
                    "text_fa": "هرکس مالک مال خود است."
                }
            }
        },
        "relationships": [
            {
                "source": "law:civil_code",
                "target": "chapter:civil_code:1",
                "type": "HAS_CHAPTER"
            },
            {
                "source": "chapter:civil_code:1",
                "target": "article:civil_code:1",
                "type": "HAS_ARTICLE"
            }
        ]
    }


@pytest.fixture(scope="function")
def corrupted_graph_state():
    """
    Corrupted graph state for testing validation.
    
    Returns a dictionary representing a corrupted legal knowledge graph.
    """
    return {
        "nodes": {
            "law:civil_code": {
                "label": "Law",
                "properties": {
                    "canonical_id": "law:civil_code",
                    "title_fa": "قانون مدنی",
                    "publication_date": "1928-03-15",
                    "status": "active"
                }
            },
            "orphan_article": {
                "label": "Article",
                "properties": {
                    "canonical_id": "article:orphan",
                    "article_number": "999",
                    "text_fa": "ماده یتیم"
                }
            },
            "duplicate_law": {
                "label": "Law",
                "properties": {
                    "canonical_id": "law:civil_code_duplicate",
                    "title_fa": "قانون مدنی",
                    "publication_date": "1928-03-15",
                    "status": "active"
                }
            }
        },
        "relationships": [
            {
                "source": "law:civil_code",
                "target": "chapter:civil_code:1",
                "type": "HAS_CHAPTER"
            }
            # Missing: orphan_article has no parent
        ]
    }


@pytest.fixture(scope="function")
def empty_graph_state():
    """
    Empty graph state for testing.
    
    Returns a dictionary representing an empty graph.
    """
    return {
        "nodes": {},
        "relationships": []
    }

"""
Surgical Tests for mahoun/graph/neo4j/operations.py
====================================================
Target: Test ONLY pure functions (not governance-dependent operations)

Focus Areas:
1. _parse_law_article() - regex parsing
2. _generate_verdict_id() - ID generation logic
3. GraphOperations initialization
4. Helper functions (get_law_articles, get_tags, get_parties)
"""

import hashlib
import pytest
from unittest.mock import MagicMock

from mahoun.graph.neo4j.operations import (
    GraphOperations,
    _parse_law_article,
    _generate_verdict_id,
)


class TestLawArticleParsing:
    """Test _parse_law_article() regex extraction"""
    
    @pytest.mark.p2
    def test_parse_standard_article(self):
        """Parse standard Persian law article format"""
        article_str = "ماده 10 قانون مدنی"
        result = _parse_law_article(article_str)
        
        assert result["article_no"] == "10"
        assert result["code"] == "قانون مدنی"
        assert result["label"] == article_str
    
    @pytest.mark.p2
    def test_parse_article_with_spaces(self):
        """Parse article with extra spaces"""
        article_str = "ماده   25   قانون تجارت"
        result = _parse_law_article(article_str)
        
        assert result["article_no"] == "25"
        assert "قانون تجارت" in result["code"]
    
    @pytest.mark.p2
    def test_parse_article_without_number(self):
        """Parse article without number returns empty fields"""
        article_str = "قانون مدنی"
        result = _parse_law_article(article_str)
        
        assert result["article_no"] == ""
        assert result["code"] == ""
        assert result["label"] == article_str
    
    @pytest.mark.p2
    def test_parse_article_with_description(self):
        """Parse article with long description"""
        article_str = "ماده 100 قانون مدنی - حقوق اشخاص"
        result = _parse_law_article(article_str)
        
        assert result["article_no"] == "100"
        assert "قانون مدنی" in result["code"]


class TestVerdictIDGeneration:
    """Test _generate_verdict_id() logic"""
    
    @pytest.mark.p2
    def test_generate_id_from_filepath(self):
        """Generate verdict ID from _source.filepath"""
        verdict_struct = {
            "_source": {"filepath": "/path/to/verdict_001.json"},
            "case_meta": {}
        }
        
        verdict_id = _generate_verdict_id(verdict_struct)
        
        assert verdict_id == "verdict_001"
        assert not verdict_id.endswith(".json")
    
    @pytest.mark.p2
    def test_generate_id_from_case_meta(self):
        """Generate verdict ID from case_meta hash when no filepath"""
        verdict_struct = {
            "_source": {},
            "case_meta": {
                "court_level": "Supreme",
                "case_type": "Civil",
                "procedure_stage": "Final"
            }
        }
        
        verdict_id = _generate_verdict_id(verdict_struct)
        
        assert isinstance(verdict_id, str)
        assert len(verdict_id) == 16  # MD5 hash truncated
    
    @pytest.mark.p2
    def test_generate_id_deterministic(self):
        """Same case_meta produces same verdict_id"""
        verdict_struct = {
            "_source": {},
            "case_meta": {
                "court_level": "Appeal",
                "case_type": "Criminal"
            }
        }
        
        id1 = _generate_verdict_id(verdict_struct)
        id2 = _generate_verdict_id(verdict_struct)
        
        assert id1 == id2


class TestGraphOperationsInit:
    """Test GraphOperations initialization"""
    
    @pytest.mark.p2
    def test_init_with_connection(self):
        """GraphOperations initializes with provided connection"""
        mock_conn = MagicMock()
        
        ops = GraphOperations(connection=mock_conn)
        
        assert ops.conn == mock_conn
        assert ops.metrics is not None
    
    @pytest.mark.p2
    def test_init_without_connection(self):
        """GraphOperations creates connection if not provided"""
        ops = GraphOperations()
        
        assert ops.conn is not None
        assert ops.metrics is not None
    
    @pytest.mark.p2
    def test_init_with_custom_metrics(self):
        """GraphOperations accepts custom metrics"""
        from mahoun.graph.neo4j.monitoring import Neo4jMetrics
        
        mock_conn = MagicMock()
        custom_metrics = Neo4jMetrics()
        
        ops = GraphOperations(connection=mock_conn, metrics=custom_metrics)
        
        assert ops.metrics == custom_metrics


class TestReadHelperMethods:
    """Test read helper methods (get_law_articles, get_tags, etc.)"""
    
    @pytest.mark.p2
    def test_get_law_articles_return_type(self):
        """get_law_articles_for_verdict returns list of strings"""
        mock_conn = MagicMock()
        mock_conn.execute_query.return_value = [
            {"label": "ماده 10 قانون مدنی"},
            {"label": "ماده 25 قانون تجارت"}
        ]
        
        ops = GraphOperations(connection=mock_conn)
        articles = ops.get_law_articles_for_verdict("v001")
        
        assert isinstance(articles, list)
        assert all(isinstance(a, str) for a in articles)
        assert len(articles) == 2
    
    @pytest.mark.p2
    def test_get_law_articles_empty_result(self):
        """get_law_articles_for_verdict returns [] when no results"""
        mock_conn = MagicMock()
        mock_conn.execute_query.return_value = []
        
        ops = GraphOperations(connection=mock_conn)
        articles = ops.get_law_articles_for_verdict("v002")
        
        assert articles == []
    
    @pytest.mark.p2
    def test_get_tags_return_type(self):
        """get_tags_for_verdict returns list of strings"""
        mock_conn = MagicMock()
        mock_conn.execute_query.return_value = [
            {"name": "commercial"},
            {"name": "contract"}
        ]
        
        ops = GraphOperations(connection=mock_conn)
        tags = ops.get_tags_for_verdict("v003")
        
        assert isinstance(tags, list)
        assert len(tags) == 2
        assert "commercial" in tags
    
    @pytest.mark.p2
    def test_get_parties_return_type(self):
        """get_parties_for_verdict returns list of dicts"""
        mock_conn = MagicMock()
        mock_conn.execute_query.return_value = [
            {
                "display_name": "Ali Ahmadi",
                "father_name": "Hassan",
                "role": "plaintiff"
            }
        ]
        
        ops = GraphOperations(connection=mock_conn)
        parties = ops.get_parties_for_verdict("v004")
        
        assert isinstance(parties, list)
        assert len(parties) == 1
        assert parties[0]["display_name"] == "Ali Ahmadi"
        assert parties[0]["role"] == "plaintiff"
    
    @pytest.mark.p2
    def test_get_verdict_by_id_return_type(self):
        """get_verdict_by_id returns dict or None"""
        mock_conn = MagicMock()
        mock_conn.execute_query.return_value = [
            {"v": {"verdict_id": "v005", "court_level": "Supreme"}}
        ]
        
        ops = GraphOperations(connection=mock_conn)
        verdict = ops.get_verdict_by_id("v005")
        
        assert isinstance(verdict, dict)
        assert verdict["verdict_id"] == "v005"
    
    @pytest.mark.p2
    def test_get_verdict_by_id_not_found(self):
        """get_verdict_by_id returns None when not found"""
        mock_conn = MagicMock()
        mock_conn.execute_query.return_value = []
        
        ops = GraphOperations(connection=mock_conn)
        verdict = ops.get_verdict_by_id("v999")
        
        assert verdict is None

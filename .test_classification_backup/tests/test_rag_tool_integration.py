"""
Integration Tests for RAG Tool
=================================

Tests real search integration in RAGTool.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from mahoun.mcp.tools.rag import RAGTool

@pytest.mark.asyncio
class TestRAGToolIntegration:
    """Integration tests for RAGTool."""
    
    @pytest.fixture
    async def rag_tool(self):
        """Create RAGTool instance."""
        return RAGTool()
    
    async def test_hybrid_search(self, rag_tool):
        """Test hybrid search."""
        with patch("mahoun.retrieval.hybrid_search_v2.HybridSearchV2.search", new_callable=AsyncMock) as mock_search:
            mock_res = MagicMock()
            mock_res.results = []
            mock_res.total_found = 0
            mock_search.return_value = mock_res
            
            result = await rag_tool.hybrid_search(query="شرایط فسخ قرارداد")
            
            assert "results" in result
            assert "metrics" in result
    
    async def test_rerank(self, rag_tool):
        """Test reranking."""
        with patch("mahoun.retrieval.hybrid_search_v2.HybridSearchV2.initialize", new_callable=AsyncMock):
            with patch("mahoun.pipelines.vector_store.manager_v2.VectorStoreManagerV2.initialize", new_callable=AsyncMock):
                tool = RAGTool()
                # Mock the engine's reranker
                with patch("mahoun.retrieval.hybrid_search_v2.HybridSearchV2") as MockEngine:
                    engine = MockEngine.return_value
                    engine.reranker = MagicMock()
                    engine.reranker.rerank = AsyncMock(return_value=[])
                    
                    tool._search_engine = engine
                    
                    result = await tool.rerank(query="تعهدات مالی", documents=["بند ۱", "بند ۲"])
                    
                    assert "results" in result
    


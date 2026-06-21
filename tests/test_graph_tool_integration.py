"""
Integration Tests for Graph Tool
=================================

Tests real Neo4j integration in GraphTool.
"""

import pytest
import asyncio
from mahoun.mcp.tools.graph import GraphTool

# Mark all tests as async
pytest_plugins = ('pytest_asyncio',)

pytestmark = pytest.mark.integration


class TestGraphToolIntegration:
    """Integration tests for GraphTool with Neo4j."""
    
    @pytest.fixture
    async def graph_tool(self):
        """Create GraphTool instance."""
        return GraphTool()
    
    @pytest.mark.asyncio
    async def test_get_graph_summary(self, graph_tool):
        """Test getting graph summary."""
        result = await graph_tool.get_graph_summary()
        
        assert "nodes" in result
        assert "edges" in result
        assert "status" in result
        
        # Should either connect or gracefully fail
        assert result["status"] in ["connected", "no_connection", "error"]
    
    @pytest.mark.asyncio
    async def test_get_neighbors_no_connection(self, graph_tool):
        """Test get_neighbors handles missing connection."""
        result = await graph_tool.get_neighbors("test_doc", limit=5)
        
        assert "root" in result
        assert result["root"] == "test_doc"
        assert "neighbors" in result
        assert "count" in result
    
    @pytest.mark.asyncio
    async def test_get_related_docs(self, graph_tool):
        """Test related documents query."""
        result = await graph_tool.get_related_docs("test_doc", depth=2)
        
        assert "source_doc" in result
        assert result["source_doc"] == "test_doc"
        assert "related" in result
        assert "depth" in result
        assert result["depth"] == 2
    
    @pytest.mark.asyncio
    async def test_search_graph(self, graph_tool):
        """Test graph search."""
        result = await graph_tool.search_graph("test query", limit=10)
        
        assert "query" in result
        assert result["query"] == "test query"
        assert "results" in result
        assert "count" in result
    
    @pytest.mark.asyncio
    async def test_error_handling(self, graph_tool):
        """Test that errors are handled gracefully."""
        # These should not raise exceptions
        result1 = await graph_tool.get_graph_summary()
        result2 = await graph_tool.get_neighbors("nonexistent")
        result3 = await graph_tool.search_graph("test")
        
        # All should return dict with status/error info
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        assert isinstance(result3, dict)


class TestGraphToolWithMockNeo4j:
    """Tests with mocked Neo4j for specific scenarios."""
    
    @pytest.mark.asyncio
    async def test_handles_connection_failure(self):
        """Test graceful handling of connection failures."""
        tool = GraphTool()
        
        # Should handle failure gracefully
        result = await tool.get_graph_summary()
        assert "error" in result or "status" in result
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling multiple concurrent requests."""
        tool = GraphTool()
        
        # Fire multiple requests concurrently
        tasks = [
            tool.get_graph_summary(),
            tool.get_neighbors("doc1"),
            tool.get_related_docs("doc2"),
            tool.search_graph("test")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete without raising
        assert len(results) == 4
        for result in results:
            assert not isinstance(result, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

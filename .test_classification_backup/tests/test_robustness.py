"""
System Robustness Test
=======================

Verifies that the system handles failures gracefully (Connection Refused, Missing Files).
"""

import pytest
import asyncio
from mahoun.mcp.registry import TOOLS

@pytest.mark.asyncio
async def test_ingest_missing_file():
    """IngestTool should handle missing files gracefully."""
    tool = TOOLS["Ingest"]
    result = await tool.ingest_file("/non/existent/file.pdf")
    
    assert result["success"] is False
    assert "not found" in result["error"].lower() or "file" in result["error"].lower()
    print("\n✅ IngestTool handled missing file gracefully.")

@pytest.mark.asyncio
async def test_graph_connection_failure():
    """GraphTool should not crash if Neo4j is down."""
    tool = TOOLS["Graph"]
    
    # This might actually try to connect and fail, or return a mock if patched
    # In our implementation we wrapped it in try-except block in get_graph_summary
    result = await tool.get_graph_summary()
    
    # It should return a result dict (maybe with error) but NOT raise Exception
    assert isinstance(result, dict)
    if "error" in result:
        print(f"✅ GraphTool handled connection error gracefully: {result['error']}")
    else:
        print("✅ GraphTool returned summary (mock or real).")

@pytest.mark.asyncio
async def test_rag_empty_query():
    """RAGTool should handle empty/invalid queries."""
    tool = TOOLS["RAG"]
    
    # Assuming the underlying engine validates query
    result = await tool.hybrid_search("")
    
    # Should probably return empty list or error, but not crash
    assert "error" in result or len(result.get("results", [])) == 0
    print("✅ RAGTool handled empty query gracefully.")

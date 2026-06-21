"""
MCP Real Integration Test
==========================

Verifies that MCP tools correctly load and wrap the PRODUCTION engines
(IngestionPipelineV2, HybridSearchV2, Neo4jConnection).
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.integration

from mahoun.mcp.registry import TOOLS
from mahoun.pipelines.ingestion.pipeline import IngestionPipelineV2
from mahoun.retrieval.hybrid_search_v2 import HybridSearchV2

@pytest.mark.asyncio
async def test_ingest_tool_initialization():
    """Verify IngestTool loads IngestionPipelineV2."""
    tool = TOOLS["Ingest"]
    
    # Check if _get_pipeline returns the correct class instance
    # We maintain the singleton pattern, so first call initializes it
    pipeline = await tool._get_pipeline()
    
    assert isinstance(pipeline, IngestionPipelineV2)
    assert pipeline.enable_verdict_parsing is True
    print("\n✅ IngestTool correctly loaded IngestionPipelineV2.")

@pytest.mark.asyncio
async def test_rag_tool_initialization():
    """Verify RAGTool loads HybridSearchV2."""
    tool = TOOLS["RAG"]
    
    # Check engine loading
    engine = await tool._get_engine()
    
    assert isinstance(engine, HybridSearchV2)
    # Check if dense/sparse weights are set as expected
    assert engine.dense_weight == 0.7
    assert engine.sparse_weight == 0.3
    print("✅ RAGTool correctly loaded HybridSearchV2.")

@pytest.mark.asyncio
async def test_graph_tool_connection_attempt():
    """Verify GraphTool loads Neo4j components."""
    tool = TOOLS["Graph"]
    
    # We expect this to load the GraphOperations class
    # even if connection fails (which is handled gracefully)
    ops = await tool._get_ops()
    
    from mahoun.graph.neo4j.operations import GraphOperations
    assert isinstance(ops, GraphOperations)
    print("✅ GraphTool correctly loaded Neo4j GraphOperations.")

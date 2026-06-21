"""
HAJIX Comprehensive Test Suite
===============================

Runs all critical tests using standard unittest.
Mocks ALL heavy ML/Data dependencies to verify LOGIC correctness.
"""

import unittest
import asyncio
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock

# --- CRITICAL: PREVENT DB INITIALIZATION ---
os.environ["MAHOUN_MODE"] = "test"
os.environ["MAHOUN_ENABLE_POSTGRES"] = "0"
os.environ["MAHOUN_ENABLE_REDIS"] = "0"

# Stub api.database before any mahoun imports
import types
fake_db = types.ModuleType("api.database")
fake_db.postgres_pool = None
fake_db.init_postgres = AsyncMock()
fake_db.init_redis = AsyncMock()
fake_db.init_db = AsyncMock()
fake_db.close_db = AsyncMock()
sys.modules["api.database"] = fake_db

# --- MOCK ALL DEPENDENCIES ---
MOCKS = [
    "neo4j", "numpy", "nltk", "nltk.tokenize", "nltk.corpus", "nltk.stem",
    "rank_bm25", "sentence_transformers", "chromadb", "scipy", "torch",
    "pdfplumber", "docx", "transformers", "networkx", "sklearn", 
    "sklearn.metrics.pairwise", "tqdm", "pandas",
    "chromadb.config", "chromadb.utils", "docx", "fastapi", "pydantic", "httpx", "experimental"
]

for m in MOCKS:
    sys.modules[m] = MagicMock()

# Specific mock for pydantic.BaseModel to allow inheritance
class MockBaseModel:
    pass
sys.modules["pydantic"].BaseModel = MockBaseModel
def mock_field(default=None, **kwargs):
    return default
sys.modules["pydantic"].Field = mock_field
sys.modules["pydantic"].SecretStr = lambda x: x
sys.modules["pydantic"].field_validator = lambda *args, **kwargs: lambda f: f
sys.modules["pydantic"].computed_field = property
sys.modules["pydantic"].validator = lambda *args, **kwargs: lambda f: f

# -----------------------------------

# Add HAJIX to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import AFTER mocking
from mahoun.agents import AgentFactory
from mahoun.agents.dispute_agent import DisputeType
from mahoun.mcp.registry import TOOLS
from mahoun.pipelines.ingestion.pipeline import IngestionPipelineV2
from mahoun.retrieval.hybrid_search_v2 import HybridSearchV2
from mahoun.graph.neo4j.operations import GraphOperations

class TestHAJIX(unittest.TestCase):
    
    async def _cancel_pending_tasks(self):
        """Cleanup any orphaned background tasks"""
        current = asyncio.current_task()
        pending = [t for t in asyncio.all_tasks() if t is not current and not t.done()]
        if not pending:
            return
            
        for t in pending:
            t.cancel()
            
        await asyncio.gather(*pending, return_exceptions=True)

    def run_async(self, coro):
        """Helper to run async test methods and cleanup tasks"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            # Cleanup pending tasks before closing the loop
            loop.run_until_complete(self._cancel_pending_tasks())
            loop.close()

    def test_01_e2e_dispute_workflow(self):
        """
        Test: End-to-End Workflow
        Verifies: DocParser -> DisputeAgent interaction
        """
        async def scenario():
            parser_agent = await AgentFactory.create_agent("doc_parser")
            dispute_agent = await AgentFactory.create_agent("dispute")
            
            # Patched input
            sample_text = "خریدار مبلغ را پرداخت نکرد و خسارت وارد شد."
            
            # Mock ingestion success
            with patch("mahoun.pipelines.ingestion.pipeline.IngestionPipelineV2.ingest_document") as mock_ingest:
                mock_ingest.return_value = MagicMock(success=True, doc_id="doc_1")
                # Avoid initialization logic
                IngestionPipelineV2.initialize = MagicMock(return_value=None)
                
                res = await parser_agent.process({"text": sample_text})
                self.assertTrue(res.success)
            
            # Mock RAG routing result
            with patch("mahoun.rag.query_router.QueryRouter.route", new_callable=AsyncMock) as mock_route:
                mock_res = MagicMock()
                mock_res.rag_result.results = [
                    MagicMock(content="عدم پرداخت وجه توسط خریدار خسارت", doc_id="doc_1", score=0.95)
                ]
                mock_route.return_value = mock_res
                
                # Mock internal reasoning service
                dispute_agent.reasoning_service = MagicMock()
                mock_reasoning_res = MagicMock()
                mock_reasoning_res.answer = "Financial dispute detected"
                mock_reasoning_res.__str__.return_value = "Financial dispute detected"
                dispute_agent.reasoning_service.reason = AsyncMock(return_value=mock_reasoning_res)
                
                # Mock citation engine since it's used in deep_analysis
                dispute_agent.citation_engine = MagicMock()
                dispute_agent.citation_engine.extract_citations = AsyncMock(return_value=MagicMock(citations=[]))

                dispute_res = await dispute_agent.process({"query": "dispute check", "documents": ["doc_1"]})
                
                if not dispute_res.success:
                    print(f"\n❌ Dispute Agent Error: {dispute_res.error}")
                self.assertTrue(dispute_res.success)
                
                # Check classification logic matches keywords
                if dispute_res.data["disputes"]:
                    self.assertEqual(dispute_res.data["disputes"][0]["type"], DisputeType.FINANCIAL)
                
                print("\n   ✓ End-to-End Dispute Workflow Passed")
            
            # Cleanup
            await parser_agent.shutdown()
            await dispute_agent.shutdown()

        self.run_async(scenario())

    def test_02_mcp_real_integration(self):
        """
        Test: MCP Tool Wiring
        Verifies tools instantiate the correct real classes
        """
        async def check_integration():
            # Ingest Tool
            ingest_tool = TOOLS["Ingest"]
            with patch("mahoun.pipelines.ingestion.pipeline.IngestionPipelineV2.initialize", new_callable=AsyncMock):
               pipeline = await ingest_tool._get_pipeline()
               self.assertIsInstance(pipeline, IngestionPipelineV2)
            
            # RAG Tool
            rag_tool = TOOLS["RAG"]
            # Mock all initializations
            with patch("mahoun.retrieval.hybrid_search_v2.HybridSearchV2.initialize", new_callable=AsyncMock), \
                 patch("mahoun.pipelines.vector_store.manager.VectorStoreManager.initialize", new_callable=AsyncMock), \
                 patch("mahoun.retrieval.hybrid_search_v2.BM25Retriever"), \
                 patch("mahoun.retrieval.hybrid_search_v2.DenseRetriever"):
                
                engine = await rag_tool._get_engine()
                self.assertIsInstance(engine, HybridSearchV2)
                self.assertEqual(engine.dense_weight, 0.7)

            # Graph Tool
            graph_tool = TOOLS["Graph"]
            with patch("mahoun.graph.neo4j.connection.Neo4jConnection.connect", new_callable=AsyncMock):
                ops = await graph_tool._get_ops()
                self.assertIsInstance(ops, GraphOperations)
            
            print("   ✓ MCP Real Integration Check Passed")

        self.run_async(check_integration())

    def test_03_robustness(self):
        """
        Test: System Robustness
        Verifies correct error reporting instead of crashing
        """
        async def check_errors():
            # Mock ingestion failure
            with patch("mahoun.pipelines.ingestion.pipeline.IngestionPipelineV2.ingest_file", new_callable=AsyncMock) as mock_ingest:
                 mock_res = MagicMock()
                 mock_res.success = False
                 mock_res.error = "File not found"
                 mock_res.chunks_created = 0
                 mock_res.embeddings_created = 0
                 mock_res.processing_time_ms = 0
                 mock_res.avg_chunk_size = 0
                 mock_res.is_verdict = False
                 mock_res.warnings = []
                 mock_ingest.return_value = mock_res
                 # We skip initialization for test speed
                 with patch("mahoun.pipelines.ingestion.pipeline.IngestionPipelineV2.initialize", new_callable=AsyncMock):
                     res = await TOOLS["Ingest"].ingest_file("/bad/path.pdf")
                     self.assertFalse(res["success"])
            
            print("   ✓ Robustness Checks Passed")

        self.run_async(check_errors())

if __name__ == '__main__':
    unittest.main(verbosity=2)

import pytest


@pytest.mark.asyncio
@pytest.mark.p2
async def test_mutation_bypass_impossible(monkeypatch):
    from mahoun.graph.graph_query_service import (
        GovernanceError,
        GraphQueryConfig,
        Neo4jConnectionManager,
    )

    manager = Neo4jConnectionManager(GraphQueryConfig())

    def _unexpected_connection():
        raise AssertionError("Mutation governance must fail before any Neo4j connection is touched")

    monkeypatch.setattr(manager, "_get_connection", _unexpected_connection)

    with pytest.raises(GovernanceError, match="correlation_id"):
        manager.execute_query("CREATE (n:Case {id: 'c1'})")


@pytest.mark.asyncio
@pytest.mark.p2
async def test_policy_injection_mandatory():
    from mahoun.rag.hybrid_rag_service import HybridRAGResult
    from mahoun.rag.legal_aware_retrieval import LegalAwareRetrievalService
    from mahoun.core.governance.violations import MissingExecutionPolicyError

    class DummyBaseService:
        async def retrieve(self, **kwargs):
            return HybridRAGResult(
                query=kwargs["query"],
                mode_used=str(kwargs.get("mode", "AUTO")),
                results=[],
                retrieval_time_ms=0.0,
                metadata={},
            )

        def get_stats(self):
            return {}

    service = LegalAwareRetrievalService(base_service=DummyBaseService())

    with pytest.raises(MissingExecutionPolicyError):
        await service.legal_retrieve(query="policy must be explicit", legal_filter=None)


@pytest.mark.asyncio
@pytest.mark.p2
async def test_graph_path_mandatory_when_graph_mode_enabled(monkeypatch):
    from mahoun.core.exceptions import GraphResolutionFailure
    from mahoun.rag.hybrid_rag_service import HybridRAGService, RAGMode

    class DummyVectorStore:
        async def query(self, query_embedding, top_k):
            return []

    monkeypatch.setattr("mahoun.core.runtime_config.is_enterprise_graph_mode", lambda: True)

    service = HybridRAGService(
        vector_store=DummyVectorStore(),
        graph_retriever=None,
        allow_graph_degraded_mode=False,
    )

    with pytest.raises(GraphResolutionFailure):
        await service.retrieve(
            query="graph path is mandatory",
            mode=RAGMode.HYBRID_GRAPH_FIRST,
            top_k=5,
            query_embedding=[0.1, 0.2, 0.3],
        )

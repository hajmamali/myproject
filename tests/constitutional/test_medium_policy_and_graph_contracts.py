import pytest


@pytest.mark.asyncio
async def test_policy_injection_is_mandatory_at_retrieval_boundary():
    from mahoun.core.governance.violations import MissingExecutionPolicyError
    from mahoun.rag.hybrid_rag_service import HybridRAGResult
    from mahoun.rag.legal_aware_retrieval import LegalAwareRetrievalService

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
        await service.legal_retrieve(query="explicit policy required", legal_filter=None)


@pytest.mark.asyncio
async def test_graph_path_is_explicitly_required_when_enterprise_graph_mode_is_enabled(monkeypatch):
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
            query="graph mode cannot silently degrade",
            mode=RAGMode.HYBRID_GRAPH_FIRST,
            top_k=5,
            query_embedding=[0.1, 0.2, 0.3],
        )

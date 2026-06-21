"""
Tests for UltraHybridSearch
"""
import numpy as np
import pytest

from mahoun.retrieval.ultra_hybrid_search import (
    UltraHybridSearch,
    SearchConfig,
    FusionMethod,
    DiversificationMethod
)


def test_ultra_hybrid_search_without_embedding_provider_disables_dense():
    """Test that dense retriever is disabled when no embedding provider is provided."""
    config = SearchConfig(
        use_bm25=True,
        use_dense=True,  # Request dense
        use_graph=False,
        fusion_method=FusionMethod.RRF,
    )
    # No embedding provider provided
    search = UltraHybridSearch(config=config, embedding_provider=None)
    
    # Dense retriever should be None because no embedding provider
    assert search.dense_retriever is None
    # BM25 retriever should still be active
    assert search.bm25_retriever is not None


def test_ultra_hybrid_search_with_embedding_provider_creates_dense_retriever():
    """Test that dense retriever is created when embedding provider is provided."""
    # Mock embedding provider
    class MockEmbeddingProvider:
        def embed(self, texts):
            return np.random.randn(len(texts), 768).astype(np.float32)
        
        def embed_query(self, query):
            return np.random.randn(768).astype(np.float32)
    
    config = SearchConfig(
        use_bm25=False,
        use_dense=True,
        use_graph=False,
        fusion_method=FusionMethod.RRF,
    )
    provider = MockEmbeddingProvider()
    search = UltraHybridSearch(config=config, embedding_provider=provider)
    
    # Dense retriever should be active
    assert search.dense_retriever is not None
    # BM25 retriever should be None
    assert search.bm25_retriever is None


def test_ultra_hybrid_search_search_without_embedding_provider_returns_empty_dense():
    """Test that search doesn't crash when dense retriever is disabled."""
    config = SearchConfig(
        use_bm25=True,
        use_dense=True,
        use_graph=False,
        fusion_method=FusionMethod.RRF,
        final_k=3
    )
    search = UltraHybridSearch(config=config, embedding_provider=None)
    
    # Index some dummy documents
    documents = [
        {"doc_id": "doc_1", "content": "قانون مدنی"},
        {"doc_id": "doc_2", "content": "ماده 10"},
    ]
    search.index(documents)
    
    # Search should work (BM25 only) and return results
    results, metrics = search.search("قانون", top_k=2)
    assert len(results) <= 2
    # Should have used only BM25 method
    assert 'bm25' in metrics.methods_used
    assert 'dense' not in metrics.methods_used  # Dense should not be used


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
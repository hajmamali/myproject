"""
Comprehensive Tests for Persian Semantic Search
================================================

Enterprise-grade test suite for semantic search functionality.

Test Categories:
1. Basic functionality
2. Persian language support
3. Caching behavior
4. Batch operations
5. Edge cases
6. Performance benchmarks
"""

import pytest
import numpy as np
from typing import List

# Skip if sentence-transformers not available
pytest.importorskip("sentence_transformers")

from mahoun.graph.semantic_search import (
    PersianSemanticSearch,
    SemanticSearchResult,
    _SENTENCE_TRANSFORMERS_AVAILABLE
)


@pytest.fixture
def searcher(warmup_embedding_model):
    """Create semantic searcher instance with pre-warmed model"""
    return PersianSemanticSearch(cache_size=100)


@pytest.fixture
def persian_legal_texts():
    """Sample Persian legal texts"""
    return [
        "قرارداد فسخ شد به دلیل عدم پرداخت",
        "تمدید قرارداد برای یک سال دیگر",
        "اجرای قرارداد طبق شرایط توافق شده",
        "نقض شرایط قرارداد توسط طرف مقابل",
        "خسارت ناشی از تأخیر در اجرا"
    ]


class TestBasicFunctionality:
    """Test basic semantic search functionality"""
    
    def test_initialization(self):
        """Test searcher initialization"""
        searcher = PersianSemanticSearch()
        
        assert searcher.model_name == PersianSemanticSearch.DEFAULT_MODEL
        assert searcher.cache_size == 10000
        assert searcher.batch_size == 32
    
    def test_custom_model(self):
        """Test initialization with custom model"""
        searcher = PersianSemanticSearch(
            model_name="sentence-transformers/distiluse-base-multilingual-cased-v2",
            cache_size=500
        )
        
        assert "distiluse" in searcher.model_name
        assert searcher.cache_size == 500
    
    def test_lazy_loading(self):
        """Test that model is loaded lazily"""
        searcher = PersianSemanticSearch()
        
        # Model not loaded yet
        assert searcher._model is None
        
        # Access model property triggers loading
        model = searcher.model
        assert model is not None
        assert searcher._model is not None
    
    def test_embedding_dimension(self, searcher):
        """Test embedding dimension"""
        dim = searcher.embedding_dimension
        
        # Default model has 768 dimensions
        assert dim == 768


class TestEmbedding:
    """Test text embedding functionality"""
    
    def test_embed_single_text(self, searcher):
        """Test embedding single text"""
        text = "قرارداد فسخ شد"
        embedding = searcher.embed_text(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)
        assert embedding.dtype == np.float32
    
    def test_embed_empty_text(self, searcher):
        """Test embedding empty text"""
        embedding = searcher.embed_text("")
        
        # Should return zero vector
        assert isinstance(embedding, np.ndarray)
        assert np.allclose(embedding, 0.0)
    
    def test_embed_persian_text(self, searcher):
        """Test embedding Persian text"""
        persian_text = "دادگاه حکم به پرداخت خسارت داد"
        embedding = searcher.embed_text(persian_text)
        
        assert embedding.shape == (768,)
        # Embedding should be normalized (L2 norm ≈ 1)
        norm = np.linalg.norm(embedding)
        assert 0.99 <= norm <= 1.01
    
    def test_embed_batch(self, searcher, persian_legal_texts):
        """Test batch embedding"""
        embeddings = searcher.embed_batch(persian_legal_texts)
        
        assert embeddings.shape == (len(persian_legal_texts), 768)
        assert embeddings.dtype == np.float32
        
        # All embeddings should be normalized
        norms = np.linalg.norm(embeddings, axis=1)
        assert np.all((norms >= 0.99) & (norms <= 1.01))
    
    def test_embed_batch_empty_list(self, searcher):
        """Test batch embedding with empty list"""
        embeddings = searcher.embed_batch([])
        
        assert embeddings.shape == (0, 768)


class TestCaching:
    """Test embedding caching behavior"""
    
    def test_cache_hit(self, searcher):
        """Test cache hit on repeated embedding"""
        text = "قرارداد فسخ شد"
        
        # First call - cache miss
        emb1 = searcher.embed_text(text)
        stats1 = searcher.get_cache_stats()
        
        # Second call - cache hit
        emb2 = searcher.embed_text(text)
        stats2 = searcher.get_cache_stats()
        
        # Embeddings should be identical
        assert np.array_equal(emb1, emb2)
        
        # Cache hits should increase
        assert stats2["cache_hits"] > stats1["cache_hits"]
    
    def test_cache_disabled(self, searcher):
        """Test embedding without cache"""
        text = "قرارداد فسخ شد"
        
        emb1 = searcher.embed_text(text, use_cache=False)
        emb2 = searcher.embed_text(text, use_cache=False)
        
        # Embeddings should be identical (deterministic)
        assert np.allclose(emb1, emb2)
        
        # No cache hits
        stats = searcher.get_cache_stats()
        assert stats["cache_hits"] == 0
    
    def test_cache_eviction(self):
        """Test cache eviction when full"""
        # Small cache for testing
        searcher = PersianSemanticSearch(cache_size=3)
        
        texts = [f"text_{i}" for i in range(5)]
        
        # Embed all texts
        for text in texts:
            searcher.embed_text(text)
        
        # Cache should be at capacity
        stats = searcher.get_cache_stats()
        assert stats["cache_size"] == 3
    
    def test_clear_cache(self, searcher):
        """Test cache clearing"""
        searcher.embed_text("test text")
        
        stats_before = searcher.get_cache_stats()
        assert stats_before["cache_size"] > 0
        
        searcher.clear_cache()
        
        stats_after = searcher.get_cache_stats()
        assert stats_after["cache_size"] == 0
        assert stats_after["cache_hits"] == 0


class TestSemanticSimilarity:
    """Test semantic similarity search"""
    
    def test_basic_similarity(self, searcher, persian_legal_texts):
        """Test basic similarity search"""
        query = "فسخ قرارداد"
        
        results = searcher.semantic_similarity(
            query=query,
            candidates=persian_legal_texts,
            top_k=3
        )
        
        assert len(results) <= 3
        assert all(isinstance(r, SemanticSearchResult) for r in results)
        
        # Results should be sorted by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_similarity_threshold(self, searcher, persian_legal_texts):
        """Test similarity threshold filtering"""
        query = "فسخ قرارداد"
        
        # High threshold - fewer results
        results_high = searcher.semantic_similarity(
            query=query,
            candidates=persian_legal_texts,
            threshold=0.8
        )
        
        # Low threshold - more results
        results_low = searcher.semantic_similarity(
            query=query,
            candidates=persian_legal_texts,
            threshold=0.3
        )
        
        assert len(results_high) <= len(results_low)
        
        # All scores should be above threshold
        assert all(r.score >= 0.8 for r in results_high)
        assert all(r.score >= 0.3 for r in results_low)
    
    def test_similarity_with_metadata(self, searcher, persian_legal_texts):
        """Test similarity search with metadata"""
        query = "فسخ قرارداد"
        metadata = [{"id": i, "type": "legal"} for i in range(len(persian_legal_texts))]
        
        results = searcher.semantic_similarity(
            query=query,
            candidates=persian_legal_texts,
            metadata=metadata,
            top_k=2
        )
        
        assert len(results) == 2
        assert all("id" in r.metadata for r in results)
        assert all(r.metadata["type"] == "legal" for r in results)
    
    def test_similarity_empty_candidates(self, searcher):
        """Test similarity with empty candidates"""
        results = searcher.semantic_similarity(
            query="test",
            candidates=[],
            top_k=5
        )
        
        assert results == []
    
    def test_similarity_ranks(self, searcher, persian_legal_texts):
        """Test that results have correct ranks"""
        query = "فسخ قرارداد"
        
        results = searcher.semantic_similarity(
            query=query,
            candidates=persian_legal_texts,
            top_k=3
        )
        
        # Ranks should be 1, 2, 3
        ranks = [r.rank for r in results]
        assert ranks == [1, 2, 3]


class TestBatchSimilarity:
    """Test batch similarity search"""
    
    def test_batch_similarity(self, searcher, persian_legal_texts):
        """Test batch similarity search"""
        queries = [
            "فسخ قرارداد",
            "تمدید قرارداد",
            "خسارت"
        ]
        
        all_results = searcher.batch_similarity(
            queries=queries,
            candidates=persian_legal_texts,
            top_k=2
        )
        
        assert len(all_results) == len(queries)
        assert all(len(results) <= 2 for results in all_results)
    
    def test_batch_similarity_empty_queries(self, searcher, persian_legal_texts):
        """Test batch similarity with empty queries"""
        all_results = searcher.batch_similarity(
            queries=[],
            candidates=persian_legal_texts,
            top_k=2
        )
        
        assert all_results == []
    
    def test_batch_similarity_empty_candidates(self, searcher):
        """Test batch similarity with empty candidates"""
        queries = ["query1", "query2"]
        
        all_results = searcher.batch_similarity(
            queries=queries,
            candidates=[],
            top_k=2
        )
        
        assert len(all_results) == len(queries)
        assert all(results == [] for results in all_results)


@pytest.mark.usefixtures("warmup_embedding_model")
class TestPersianLanguage:
    """Test Persian language specific features"""
    
    def test_persian_similarity(self, searcher):
        """Test similarity between Persian texts"""
        query = "قرارداد فسخ شد"
        candidates = [
            "فسخ قرارداد انجام شد",  # Very similar
            "تمدید قرارداد",  # Different
            "قرارداد باطل است"  # Somewhat similar
        ]
        
        results = searcher.semantic_similarity(
            query=query,
            candidates=candidates,
            top_k=3
        )
        
        # Most similar should be first
        assert "فسخ" in results[0].text
        
        # Scores should reflect semantic similarity
        assert results[0].score > results[1].score
    
    def test_persian_arabic_similarity(self, searcher):
        """Test similarity between Persian and Arabic variants"""
        # Persian 'ی' vs Arabic 'ي'
        query = "قرارداد فسخ می‌شود"
        candidates = [
            "قرارداد فسخ مي‌شود",  # Arabic 'ي'
            "قرارداد فسخ می‌شود"   # Persian 'ی'
        ]
        
        results = searcher.semantic_similarity(
            query=query,
            candidates=candidates,
            top_k=2
        )
        
        # Both should have high similarity
        assert all(r.score > 0.9 for r in results)
    
    def test_multilingual_support(self, searcher):
        """Test multilingual support (Persian + English)"""
        query = "contract termination"
        candidates = [
            "فسخ قرارداد",  # Persian equivalent
            "contract renewal",  # Different concept
            "termination of agreement"  # Similar in English
        ]
        
        results = searcher.semantic_similarity(
            query=query,
            candidates=candidates,
            top_k=3
        )
        
        # Should find semantic similarity across languages
        assert len(results) > 0


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_very_long_text(self, searcher):
        """Test embedding very long text"""
        # 1000 words
        long_text = " ".join(["کلمه"] * 1000)
        
        embedding = searcher.embed_text(long_text)
        
        assert embedding.shape == (768,)
    
    def test_special_characters(self, searcher):
        """Test text with special characters"""
        text = "قرارداد #123 @ شرکت ABC (فسخ شد) - 2024"
        
        embedding = searcher.embed_text(text)
        
        assert embedding.shape == (768,)
    
    def test_numbers_only(self, searcher):
        """Test text with only numbers"""
        text = "123 456 789"
        
        embedding = searcher.embed_text(text)
        
        assert embedding.shape == (768,)
    
    def test_mixed_scripts(self, searcher):
        """Test text with mixed scripts"""
        text = "قرارداد Contract 合同 Vertrag"
        
        embedding = searcher.embed_text(text)
        
        assert embedding.shape == (768,)


class TestPerformance:
    """Test performance characteristics"""
    
    def test_batch_faster_than_sequential(self, searcher):
        """Test that batch embedding is faster than sequential"""
        import time
        
        texts = [f"text_{i}" for i in range(50)]
        
        # Sequential
        start = time.time()
        for text in texts:
            searcher.embed_text(text, use_cache=False)
        sequential_time = time.time() - start
        
        # Clear cache
        searcher.clear_cache()
        
        # Batch
        start = time.time()
        searcher.embed_batch(texts, use_cache=False)
        batch_time = time.time() - start
        
        # Batch should be faster (at least 2x)
        assert batch_time < sequential_time / 2
    
    def test_cache_improves_performance(self, searcher):
        """Test that cache improves performance"""
        import time
        
        text = "قرارداد فسخ شد"
        
        # First call (no cache)
        start = time.time()
        searcher.embed_text(text, use_cache=False)
        no_cache_time = time.time() - start
        
        # Second call (with cache)
        searcher.embed_text(text, use_cache=True)  # Populate cache
        start = time.time()
        searcher.embed_text(text, use_cache=True)
        cache_time = time.time() - start
        
        # Cache should be much faster (at least 10x)
        assert cache_time < no_cache_time / 10


class TestStatistics:
    """Test statistics and monitoring"""
    
    def test_cache_stats(self, searcher):
        """Test cache statistics"""
        # Embed some texts
        searcher.embed_text("text1")
        searcher.embed_text("text2")
        searcher.embed_text("text1")  # Cache hit
        
        stats = searcher.get_cache_stats()
        
        assert "cache_size" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "hit_rate" in stats
        assert "model_loaded" in stats
        
        assert stats["cache_hits"] >= 1
        assert stats["cache_misses"] >= 2
        assert 0 <= stats["hit_rate"] <= 1
    
    def test_repr(self, searcher):
        """Test string representation"""
        repr_str = repr(searcher)
        
        assert "PersianSemanticSearch" in repr_str
        assert "model=" in repr_str
        assert "cache_size=" in repr_str


@pytest.mark.skipif(
    not _SENTENCE_TRANSFORMERS_AVAILABLE,
    reason="sentence-transformers not installed"
)
class TestIntegration:
    """Integration tests with real models"""
    
    def test_end_to_end_legal_search(self, searcher):
        """Test end-to-end legal document search"""
        # Legal query
        query = "نقض شرایط قرارداد و خسارت"
        
        # Legal documents
        documents = [
            "طرف مقابل شرایط قرارداد را نقض کرد و باید خسارت پرداخت کند",
            "قرارداد به صورت کامل اجرا شد و هیچ مشکلی وجود ندارد",
            "تمدید قرارداد برای یک سال دیگر تصویب شد",
            "خسارت ناشی از تأخیر در اجرای قرارداد محاسبه شد",
            "فسخ قرارداد به دلیل عدم پرداخت انجام شد"
        ]
        
        results = searcher.semantic_similarity(
            query=query,
            candidates=documents,
            top_k=3,
            threshold=0.4
        )
        
        # Should find relevant documents
        assert len(results) > 0
        
        # Most relevant should mention both "نقض" and "خسارت"
        top_result = results[0]
        assert "نقض" in top_result.text or "خسارت" in top_result.text
        
        # Scores should be reasonable
        assert all(0.4 <= r.score <= 1.0 for r in results)

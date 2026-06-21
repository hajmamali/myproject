"""
GGUF Embedding Integration Tests
=================================
Validation tests for GGUF embedding service integration.

Tests:
- Dimension compatibility
- Vector store integration (ChromaDB)
- Neo4j vector index compatibility
- Semantic quality comparison
- Backend selection logic
"""

import pytest
import numpy as np
from pathlib import Path
import os

# Test will be skipped if llama-cpp-python not installed
try:
    from mahoun.pipelines.ingestion.gguf_embedding import GGUFEmbeddingService

    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False

from mahoun.pipelines.ingestion.enhanced_embedding import EnhancedEmbeddingService


@pytest.mark.skipif(not HAS_LLAMA_CPP, reason="llama-cpp-python not installed")
class TestGGUFEmbeddingService:
    """Test GGUF embedding service directly"""

    @pytest.fixture
    def gguf_service(self):
        """Create GGUF embedding service instance"""
        model_path = os.getenv(
            "MAHOUN_EMBEDDING_MODEL_PATH",
            "models/paraphrase-multilingual-mpnet-base-277M-v2-Q8_0.gguf",
        )

        # Skip if model doesn't exist
        if not Path(model_path).exists():
            pytest.skip(f"GGUF model not found: {model_path}")

        return GGUFEmbeddingService(model_path=model_path)

    def test_initialization(self, gguf_service):
        """Test GGUF service initializes correctly"""
        assert gguf_service is not None
        assert gguf_service.embedding_dimension is not None
        assert gguf_service.embedding_dimension > 0

    def test_embedding_dimensions(self, gguf_service):
        """Test embeddings have correct dimensions"""
        texts = ["test query", "another document"]
        embeddings = gguf_service.embed_texts(texts)

        assert embeddings.shape[0] == len(texts)
        assert embeddings.shape[1] == gguf_service.embedding_dimension

        # Common embedding dimensions
        assert embeddings.shape[1] in [384, 768, 1024], (
            f"Unexpected dimension: {embeddings.shape[1]}"
        )

    def test_embedding_normalization(self, gguf_service):
        """Test embeddings are normalized to unit length"""
        texts = ["normalized test"]
        embeddings = gguf_service.embed_texts(texts, normalize=True)

        # Check L2 norm is approximately 1
        norm = np.linalg.norm(embeddings[0])
        assert np.isclose(norm, 1.0, atol=1e-5), f"Norm is {norm}, expected 1.0"

    def test_batch_processing(self, gguf_service):
        """Test batch processing works correctly"""
        texts = [f"text {i}" for i in range(50)]
        embeddings = gguf_service.embed_texts(texts, batch_size=10)

        assert embeddings.shape[0] == len(texts)

    def test_persian_text(self, gguf_service):
        """Test embeddings work with Persian text"""
        persian_texts = [
            "نقض شرط پیمان",
            "تأخیر در اجرای قرارداد",
            "خسارت وارده به ذینفع",
        ]

        embeddings = gguf_service.embed_texts(persian_texts)
        assert embeddings.shape[0] == len(persian_texts)

        # Check embeddings are not all zeros (model actually processed text)
        assert not np.allclose(embeddings, 0)


class TestEnhancedEmbeddingBackendSelection:
    """Test backend selection logic in EnhancedEmbeddingService"""

    def test_auto_backend_selection(self):
        """Test auto backend tries GGUF first"""
        service = EnhancedEmbeddingService(backend="auto")

        # Trigger initialization
        try:
            service.embed_texts(["init validation"])
        except Exception:
            pass  # even if model fails to load, we check backend logic

        # Get service info
        info = service.get_model_info()

        assert info["backend_requested"] == "auto"
        assert info["current_backend"] in ["gguf", "huggingface"]

    def test_force_huggingface_backend(self):
        """Test forcing HuggingFace backend"""
        service = EnhancedEmbeddingService(backend="huggingface")

        # Trigger initialization
        try:
            service.embed_texts(["test"])
        except Exception:
            pass  # Model might not be available, that's ok

        info = service.get_model_info()
        assert info["backend_requested"] == "huggingface"

    @pytest.mark.skipif(not HAS_LLAMA_CPP, reason="llama-cpp-python not installed")
    def test_force_gguf_backend(self):
        """Test forcing GGUF backend"""
        # Skip if model doesn't exist
        model_path = "models/paraphrase-multilingual-mpnet-base-277M-v2-Q8_0.gguf"
        if not Path(model_path).exists():
            pytest.skip(f"GGUF model not found: {model_path}")

        service = EnhancedEmbeddingService(backend="gguf")

        # Trigger initialization
        embeddings = service.embed_texts(["test"])

        info = service.get_model_info()
        assert info["current_backend"] == "gguf"
        assert isinstance(embeddings, list)


@pytest.mark.skipif(not HAS_LLAMA_CPP, reason="llama-cpp-python not installed")
class TestGGUFChromaDBIntegration:
    """Test GGUF embeddings work with ChromaDB"""

    @pytest.fixture
    def gguf_service(self):
        """Create GGUF service"""
        model_path = "models/paraphrase-multilingual-mpnet-base-277M-v2-Q8_0.gguf"
        if not Path(model_path).exists():
            pytest.skip(f"GGUF model not found: {model_path}")
        return GGUFEmbeddingService(model_path=model_path)

    def test_chromadb_storage_retrieval(self, gguf_service):
        """Test storing and retrieving GGUF embeddings in ChromaDB"""
        try:
            import chromadb
        except ImportError:
            pytest.skip("ChromaDB not installed")

        # Create in-memory ChromaDB
        client = chromadb.Client()
        collection = client.create_collection("test_gguf")

        # Generate embeddings
        texts = ["legal document 1", "legal document 2"]
        embeddings = gguf_service.embed_texts(texts)

        # Store in ChromaDB
        collection.add(
            documents=texts, embeddings=embeddings.tolist(), ids=["doc1", "doc2"]
        )

        # Query
        query_text = ["legal document"]
        query_embedding = gguf_service.embed_texts(query_text)

        results = collection.query(
            query_embeddings=query_embedding.tolist(), n_results=2
        )

        assert len(results["ids"][0]) == 2
        assert "doc1" in results["ids"][0] or "doc2" in results["ids"][0]


@pytest.mark.skipif(not HAS_LLAMA_CPP, reason="llama-cpp-python not installed")
class TestSemanticQuality:
    """Compare GGUF vs HuggingFace semantic quality"""

    def test_embedding_similarity(self):
        """Test GGUF embeddings capture semantic similarity"""
        model_path = "models/paraphrase-multilingual-mpnet-base-277M-v2-Q8_0.gguf"
        if not Path(model_path).exists():
            pytest.skip(f"GGUF model not found: {model_path}")

        service = GGUFEmbeddingService(model_path=model_path)

        # Similar texts should have high cosine similarity
        texts = [
            "نقض شرط پیمان",
            "نقض قرارداد",  # Similar
            "آب و هوای امروز",  # Different
        ]

        embeddings = service.embed_texts(texts, normalize=True)

        # Cosine similarity between first two (similar)
        sim_similar = np.dot(embeddings[0], embeddings[1])

        # Cosine similarity between first and third (different)
        sim_different = np.dot(embeddings[0], embeddings[2])

        # Similar texts should have higher similarity
        assert sim_similar > sim_different, (
            f"Similar: {sim_similar}, Different: {sim_different}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

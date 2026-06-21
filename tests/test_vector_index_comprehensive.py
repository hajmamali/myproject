"""
Comprehensive Tests for FAISS Vector Index
===========================================

Enterprise-grade test suite for vector indexing functionality.

Test Categories:
1. Index creation and configuration
2. Vector addition and search
3. Batch operations
4. Persistence (save/load)
5. Different index types (Flat, IVF, HNSW)
6. Edge cases and error handling
7. Performance benchmarks
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil

# Skip if faiss not available
pytest.importorskip("faiss")

from mahoun.graph.vector_index import (
    FAISSVectorIndex,
    VectorSearchResult,
    _FAISS_AVAILABLE
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_vectors():
    """Generate sample vectors for testing"""
    np.random.seed(42)
    return np.random.randn(100, 768).astype('float32')


@pytest.fixture
def sample_metadata():
    """Generate sample metadata"""
    return [{"id": i, "text": f"doc_{i}"} for i in range(100)]


class TestIndexCreation:
    """Test index creation and configuration"""
    
    def test_flat_index_creation(self):
        """Test Flat index creation"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        assert index.dimension == 768
        assert index.index_type == "Flat"
        assert index.ntotal == 0
        assert index.is_trained  # Flat index doesn't need training
    
    def test_ivf_index_creation(self):
        """Test IVF index creation"""
        index = FAISSVectorIndex(
            dimension=768,
            index_type="IVF",
            nlist=50
        )
        
        assert index.dimension == 768
        assert index.index_type == "IVF"
        assert index.nlist == 50
        assert not index.is_trained  # IVF needs training
    
    def test_hnsw_index_creation(self):
        """Test HNSW index creation"""
        index = FAISSVectorIndex(dimension=768, index_type="HNSW")
        
        assert index.dimension == 768
        assert index.index_type == "HNSW"
        assert index.is_trained  # HNSW doesn't need training
    
    def test_invalid_index_type(self):
        """Test invalid index type raises error"""
        with pytest.raises(ValueError, match="Unknown index type"):
            FAISSVectorIndex(dimension=768, index_type="INVALID")
    
    def test_custom_dimension(self):
        """Test custom dimension"""
        index = FAISSVectorIndex(dimension=384)
        
        assert index.dimension == 384


class TestVectorAddition:
    """Test adding vectors to index"""
    
    def test_add_vectors_flat(self, sample_vectors, sample_metadata):
        """Test adding vectors to Flat index"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        index.add(sample_vectors, sample_metadata)
        
        assert index.ntotal == len(sample_vectors)
        assert len(index.id_to_metadata) == len(sample_vectors)
    
    def test_add_vectors_ivf(self, sample_vectors, sample_metadata):
        """Test adding vectors to IVF index"""
        index = FAISSVectorIndex(dimension=768, index_type="IVF", nlist=10)
        
        # IVF requires training
        index.train(sample_vectors)
        assert index.is_trained
        
        index.add(sample_vectors, sample_metadata)
        
        assert index.ntotal == len(sample_vectors)
    
    def test_add_without_metadata(self, sample_vectors):
        """Test adding vectors without metadata"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        index.add(sample_vectors)
        
        assert index.ntotal == len(sample_vectors)
        # Should have empty metadata
        assert all(meta == {} for meta in index.id_to_metadata.values())
    
    def test_add_incremental(self, sample_vectors, sample_metadata):
        """Test adding vectors incrementally"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        # Add first half
        half = len(sample_vectors) // 2
        index.add(sample_vectors[:half], sample_metadata[:half])
        assert index.ntotal == half
        
        # Add second half
        index.add(sample_vectors[half:], sample_metadata[half:])
        assert index.ntotal == len(sample_vectors)
    
    def test_add_wrong_dimension(self):
        """Test adding vectors with wrong dimension"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        wrong_vectors = np.random.randn(10, 384).astype('float32')
        
        with pytest.raises(ValueError, match="dimension mismatch"):
            index.add(wrong_vectors)
    
    def test_add_auto_converts_dtype(self):
        """Test that vectors are auto-converted to float32"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        # float64 vectors
        vectors_f64 = np.random.randn(10, 768).astype('float64')
        
        index.add(vectors_f64)
        
        assert index.ntotal == 10


class TestVectorSearch:
    """Test vector similarity search"""
    
    def test_basic_search(self, sample_vectors, sample_metadata):
        """Test basic vector search"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        index.add(sample_vectors, sample_metadata)
        
        # Search with first vector
        query = sample_vectors[0]
        results = index.search(query, k=5)
        
        assert len(results) == 5
        assert all(isinstance(r, VectorSearchResult) for r in results)
        
        # First result should be the query itself (distance ≈ 0)
        assert results[0].distance < 0.01
        assert results[0].metadata["id"] == 0
    
    def test_search_ranks(self, sample_vectors, sample_metadata):
        """Test that results have correct ranks"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        index.add(sample_vectors, sample_metadata)
        
        query = sample_vectors[0]
        results = index.search(query, k=3)
        
        # Ranks should be 1, 2, 3
        ranks = [r.rank for r in results]
        assert ranks == [1, 2, 3]
    
    def test_search_sorted_by_distance(self, sample_vectors, sample_metadata):
        """Test that results are sorted by distance"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        index.add(sample_vectors, sample_metadata)
        
        query = sample_vectors[0]
        results = index.search(query, k=10)
        
        # Distances should be ascending
        distances = [r.distance for r in results]
        assert distances == sorted(distances)
    
    def test_search_empty_index(self):
        """Test search on empty index"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        query = np.random.randn(768).astype('float32')
        results = index.search(query, k=5)
        
        assert results == []
    
    def test_search_k_larger_than_index(self, sample_vectors, sample_metadata):
        """Test search with k larger than index size"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        # Add only 10 vectors
        index.add(sample_vectors[:10], sample_metadata[:10])
        
        query = sample_vectors[0]
        results = index.search(query, k=100)
        
        # Should return only 10 results
        assert len(results) == 10
    
    def test_search_with_1d_query(self, sample_vectors, sample_metadata):
        """Test search with 1D query vector"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        index.add(sample_vectors, sample_metadata)
        
        # 1D query (will be reshaped internally)
        query = sample_vectors[0]  # Already 1D
        results = index.search(query, k=5)
        
        assert len(results) == 5


class TestBatchSearch:
    """Test batch vector search"""
    
    def test_batch_search(self, sample_vectors, sample_metadata):
        """Test batch search with multiple queries"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        index.add(sample_vectors, sample_metadata)
        
        # Search with first 5 vectors
        queries = sample_vectors[:5]
        all_results = index.batch_search(queries, k=3)
        
        assert len(all_results) == 5
        assert all(len(results) == 3 for results in all_results)
    
    def test_batch_search_empty_index(self):
        """Test batch search on empty index"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        queries = np.random.randn(5, 768).astype('float32')
        all_results = index.batch_search(queries, k=3)
        
        assert len(all_results) == 5
        assert all(results == [] for results in all_results)


class TestIVFIndex:
    """Test IVF-specific functionality"""
    
    def test_ivf_training(self, sample_vectors):
        """Test IVF index training"""
        index = FAISSVectorIndex(dimension=768, index_type="IVF", nlist=10)
        
        assert not index.is_trained
        
        index.train(sample_vectors)
        
        assert index.is_trained
    
    def test_ivf_auto_training_on_add(self, sample_vectors, sample_metadata):
        """Test that IVF auto-trains when adding vectors"""
        index = FAISSVectorIndex(dimension=768, index_type="IVF", nlist=10)
        
        # Add without explicit training
        index.add(sample_vectors, sample_metadata)
        
        # Should be trained automatically
        assert index.is_trained
        assert index.ntotal == len(sample_vectors)
    
    def test_ivf_nprobe_parameter(self, sample_vectors, sample_metadata):
        """Test IVF nprobe parameter affects search"""
        index = FAISSVectorIndex(
            dimension=768,
            index_type="IVF",
            nlist=10,
            nprobe=5
        )
        
        index.add(sample_vectors, sample_metadata)
        
        query = sample_vectors[0]
        results = index.search(query, k=5)
        
        assert len(results) > 0


class TestPersistence:
    """Test saving and loading index"""
    
    def test_save_and_load_flat(self, sample_vectors, sample_metadata, temp_dir):
        """Test save and load Flat index"""
        # Create and populate index
        index1 = FAISSVectorIndex(dimension=768, index_type="Flat")
        index1.add(sample_vectors, sample_metadata)
        
        # Save
        save_path = temp_dir / "index"
        index1.save(str(save_path))
        
        # Check files exist
        assert (save_path / "index.faiss").exists()
        assert (save_path / "metadata.json").exists()
        assert (save_path / "config.json").exists()
        
        # Load into new index
        index2 = FAISSVectorIndex(dimension=768, index_type="Flat")
        index2.load(str(save_path))
        
        # Verify
        assert index2.ntotal == index1.ntotal
        assert len(index2.id_to_metadata) == len(index1.id_to_metadata)
        
        # Search should give same results
        query = sample_vectors[0]
        results1 = index1.search(query, k=5)
        results2 = index2.search(query, k=5)
        
        assert len(results1) == len(results2)
        assert results1[0].vector_id == results2[0].vector_id
    
    def test_save_and_load_ivf(self, sample_vectors, sample_metadata, temp_dir):
        """Test save and load IVF index"""
        # Create and populate index
        index1 = FAISSVectorIndex(dimension=768, index_type="IVF", nlist=10)
        index1.add(sample_vectors, sample_metadata)
        
        # Save
        save_path = temp_dir / "index_ivf"
        index1.save(str(save_path))
        
        # Load
        index2 = FAISSVectorIndex(dimension=768, index_type="IVF", nlist=10)
        index2.load(str(save_path))
        
        assert index2.ntotal == index1.ntotal
        assert index2.is_trained
    
    def test_load_nonexistent_path(self):
        """Test loading from nonexistent path"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        with pytest.raises(FileNotFoundError):
            index.load("/nonexistent/path")
    
    def test_load_dimension_mismatch(self, sample_vectors, temp_dir):
        """Test loading index with dimension mismatch"""
        # Save with dimension 768
        index1 = FAISSVectorIndex(dimension=768, index_type="Flat")
        index1.add(sample_vectors)
        
        save_path = temp_dir / "index"
        index1.save(str(save_path))
        
        # Try to load with dimension 384
        index2 = FAISSVectorIndex(dimension=384, index_type="Flat")
        
        with pytest.raises(ValueError, match="Dimension mismatch"):
            index2.load(str(save_path))


class TestStatistics:
    """Test index statistics"""
    
    def test_get_stats_empty(self):
        """Test statistics on empty index"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        stats = index.get_stats()
        
        assert stats["index_type"] == "Flat"
        assert stats["dimension"] == 768
        assert stats["num_vectors"] == 0
        assert stats["is_trained"] == True
        assert stats["metadata_count"] == 0
    
    def test_get_stats_populated(self, sample_vectors, sample_metadata):
        """Test statistics on populated index"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        index.add(sample_vectors, sample_metadata)
        
        stats = index.get_stats()
        
        assert stats["num_vectors"] == len(sample_vectors)
        assert stats["metadata_count"] == len(sample_metadata)
    
    def test_get_stats_ivf(self, sample_vectors):
        """Test statistics for IVF index"""
        index = FAISSVectorIndex(dimension=768, index_type="IVF", nlist=10, nprobe=5)
        index.add(sample_vectors)
        
        stats = index.get_stats()
        
        assert stats["nlist"] == 10
        assert stats["nprobe"] == 5


class TestClearAndRemove:
    """Test clearing and removing vectors"""
    
    def test_clear_index(self, sample_vectors, sample_metadata):
        """Test clearing index"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        index.add(sample_vectors, sample_metadata)
        
        assert index.ntotal > 0
        
        index.clear()
        
        assert index.ntotal == 0
        assert len(index.id_to_metadata) == 0
    
    def test_remove_vectors(self, sample_vectors, sample_metadata):
        """Test removing vectors (metadata only)"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        index.add(sample_vectors, sample_metadata)
        
        # Remove metadata for first 10 vectors
        index.remove(list(range(10)))
        
        # Metadata should be removed
        assert 0 not in index.id_to_metadata
        assert 9 not in index.id_to_metadata
        assert 10 in index.id_to_metadata


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_single_vector(self):
        """Test with single vector"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        vector = np.random.randn(1, 768).astype('float32')
        index.add(vector)
        
        assert index.ntotal == 1
        
        results = index.search(vector[0], k=1)
        assert len(results) == 1
    
    def test_very_small_vectors(self):
        """Test with very small dimension"""
        index = FAISSVectorIndex(dimension=2, index_type="Flat")
        
        vectors = np.random.randn(10, 2).astype('float32')
        index.add(vectors)
        
        assert index.ntotal == 10
    
    def test_zero_vectors(self):
        """Test with zero vectors"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        vectors = np.zeros((10, 768), dtype='float32')
        index.add(vectors)
        
        # All vectors are identical, so search should work
        query = np.zeros(768, dtype='float32')
        results = index.search(query, k=5)
        
        assert len(results) == 5
        # All distances should be 0
        assert all(r.distance < 0.01 for r in results)


class TestRepr:
    """Test string representation"""
    
    def test_repr_flat(self):
        """Test repr for Flat index"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        repr_str = repr(index)
        
        assert "FAISSVectorIndex" in repr_str
        assert "type=Flat" in repr_str
        assert "dim=768" in repr_str
        assert "vectors=0" in repr_str
    
    def test_repr_with_vectors(self, sample_vectors):
        """Test repr with vectors"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        index.add(sample_vectors)
        
        repr_str = repr(index)
        
        assert f"vectors={len(sample_vectors)}" in repr_str


@pytest.mark.skipif(
    not _FAISS_AVAILABLE,
    reason="faiss not installed"
)
class TestIntegration:
    """Integration tests with real use cases"""
    
    def test_legal_document_search(self):
        """Test legal document vector search"""
        # Simulate document embeddings
        np.random.seed(42)
        num_docs = 1000
        doc_embeddings = np.random.randn(num_docs, 768).astype('float32')
        
        # Normalize embeddings (as would come from sentence-transformers)
        doc_embeddings = doc_embeddings / np.linalg.norm(
            doc_embeddings, axis=1, keepdims=True
        )
        
        # Metadata
        metadata = [
            {"doc_id": i, "title": f"Legal Document {i}"}
            for i in range(num_docs)
        ]
        
        # Create index
        index = FAISSVectorIndex(dimension=768, index_type="IVF", nlist=100)
        index.add(doc_embeddings, metadata)
        
        # Search
        query = doc_embeddings[0]
        results = index.search(query, k=10)
        
        assert len(results) == 10
        assert results[0].metadata["doc_id"] == 0
        
        # Distances should be small (normalized vectors)
        assert all(r.distance < 2.0 for r in results)
    
    def test_incremental_indexing(self):
        """Test incremental document indexing"""
        index = FAISSVectorIndex(dimension=768, index_type="Flat")
        
        # Add documents in batches
        for batch_idx in range(10):
            batch_size = 50
            vectors = np.random.randn(batch_size, 768).astype('float32')
            metadata = [
                {"batch": batch_idx, "doc": i}
                for i in range(batch_size)
            ]
            
            index.add(vectors, metadata)
        
        # Should have all documents
        assert index.ntotal == 500
        
        # Search should work
        query = np.random.randn(768).astype('float32')
        results = index.search(query, k=20)
        
        assert len(results) == 20

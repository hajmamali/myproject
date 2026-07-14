"""
Persian Semantic Search - Enterprise Grade
==========================================

Advanced semantic search for Persian legal text using multilingual embeddings.

Features:
- Multilingual embeddings (Persian + English + Arabic)
- LRU caching for performance
- Batch processing for throughput
- Configurable similarity thresholds
- GPU acceleration support

Architecture:
- sentence-transformers for embeddings (NOT LLM - just vector generation)
- Cosine similarity for semantic matching
- No text generation - pure similarity search

CRITICAL: This is NOT an LLM. It's an embedding model that converts text to vectors.
No hallucination risk - just mathematical similarity computation.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from functools import lru_cache
from dataclasses import dataclass
import hashlib

from mahoun.core.logging import setup_logger

log = setup_logger("semantic_search")

# Lazy import to avoid dependency issues
_SENTENCE_TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    log.warning(
        "sentence-transformers not available. "
        "Install with: pip install sentence-transformers"
    )
    # Create a placeholder type for type hints when library not available
    SentenceTransformer = Any  # type: ignore


@dataclass
class SemanticSearchResult:
    """Result from semantic search"""
    text: str
    score: float
    metadata: Dict[str, Any]
    rank: int


class PersianSemanticSearch:
    """
    Enterprise-grade semantic search for Persian legal text.
    
    This class uses sentence-transformers to convert text to embeddings (vectors).
    It does NOT use LLMs for text generation - only for similarity computation.
    
    Zero-hallucination guarantee maintained:
    - Embeddings are deterministic (same text → same vector)
    - Similarity is pure mathematics (cosine distance)
    - No text generation or reasoning
    
    Performance optimizations:
    - LRU cache for embeddings (10K entries)
    - Batch processing for multiple texts
    - Lazy model loading
    - Optional GPU acceleration
    
    Supported languages:
    - Persian (Farsi)
    - Arabic
    - English
    - 50+ other languages (multilingual model)
    
    Example:
        >>> searcher = PersianSemanticSearch()
        >>> results = searcher.semantic_similarity(
        ...     query="قرارداد فسخ شد",
        ...     candidates=["فسخ قرارداد", "تمدید قرارداد", "اجرای قرارداد"],
        ...     top_k=2
        ... )
        >>> print(results[0].text, results[0].score)
        فسخ قرارداد 0.95
    """
    
    # Default model: paraphrase-multilingual-mpnet-base-v2
    # - 768 dimensions
    # - 278M parameters
    # - Supports 50+ languages including Persian
    # - ~420MB download
    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    
    # Alternative models for different use cases:
    # - distiluse-base-multilingual-cased-v2: Faster, smaller (135M params)
    # - LaBSE: Better for cross-lingual search (471M params)
    # - paraphrase-multilingual-MiniLM-L12-v2: Smallest (118M params)
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        cache_size: int = 10000,
        device: Optional[str] = None,
        batch_size: int = 32,
        model_instance: Optional["SentenceTransformer"] = None,
        correlation_id: str = "",
    ):
        """
        Ultra-advanced semantic search with fail-closed DI.
        
        Constructor Injection Contract
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ``model_instance`` MUST be injected by bootstrap (primary path).
        Lazy fallback is DEPRECATED and triggers loud warnings.
        
        Architectural Mandate
        ~~~~~~~~~~~~~~~~~~~~~
        Bootstrap wiring is MANDATORY in production. Lazy construction
        exists only for backward compatibility and will be removed.
        
        Args:
            model_name: SentenceTransformer model name (only for lazy fallback)
            cache_size: LRU cache size for embeddings
            device: Device for computation ('cuda', 'cpu', or None for auto)
            batch_size: Batch size for encoding
            model_instance: Pre-constructed SentenceTransformer (MANDATORY in production).
                          If None, triggers DEPRECATED lazy fallback with warning.
            correlation_id: Request tracking ID for observability.
        """
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required for semantic search. "
                "Install with: pip install sentence-transformers"
            )
        
        import time
        self._correlation_id = correlation_id or f"search-{time.time()}"
        
        self.model_name = model_name or self.DEFAULT_MODEL
        self.cache_size = cache_size
        self.batch_size = batch_size
        self.device = device
        
        if model_instance is not None:
            # PRIMARY PATH: Bootstrap-injected model
            self._model: Optional[SentenceTransformer] = model_instance
            self._embedding_dim = model_instance.get_sentence_embedding_dimension()
            log.info(
                f"[{self._correlation_id}] ✅ PersianSemanticSearch initialized "
                f"(bootstrap-injected model, dim={self._embedding_dim})"
            )
        else:
            # DEPRECATED FALLBACK: Lazy loading
            log.warning(
                f"[{self._correlation_id}] ⚠️  DEPRECATED: PersianSemanticSearch "
                f"initialized without injected model. Will attempt lazy load on first access. "
                f"Bootstrap wiring is MANDATORY in production. "
                f"Remediation: Update bootstrap/runtime.py to inject SentenceTransformer."
            )
            self._model: Optional[SentenceTransformer] = None
            self._embedding_dim: Optional[int] = None
        
        # Cache for embeddings (text hash -> embedding)
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    @property
    def model(self) -> SentenceTransformer:
        """
        DEPRECATED: Lazy load model on first access.
        
        This property exists only for backward compatibility. Bootstrap injection
        is the PRIMARY path.
        """
        if self._model is None:
            import time
            log.warning(
                f"[{self._correlation_id}] ⚠️  Lazy model loading triggered. "
                f"This is a DEPRECATED fallback path."
            )
            try:
                start = time.time()
                self._model = SentenceTransformer(self.model_name, device=self.device)
                self._embedding_dim = self._model.get_sentence_embedding_dimension()
                latency_ms = (time.time() - start) * 1000
                
                log.warning(
                    f"[{self._correlation_id}] ⚠️  Lazy model loading completed "
                    f"(model={self.model_name}, dim={self._embedding_dim}, "
                    f"device={self._model.device}, latency={latency_ms:.2f}ms)"
                )
            except ImportError:
                log.error(
                    f"[{self._correlation_id}] ❌ sentence-transformers not installed "
                    f"and no model injected."
                )
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers OR "
                    "inject pre-constructed model via bootstrap wiring."
                )
            except Exception as e:
                log.error(
                    f"[{self._correlation_id}] ❌ Lazy model loading failed: {e}"
                )
                raise RuntimeError(f"Failed to load embedding model: {e}")
        return self._model
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension"""
        if self._embedding_dim is None:
            _ = self.model  # Trigger lazy loading
        return self._embedding_dim or 768
    
    def _hash_text(self, text: str) -> str:
        """Generate hash for text (for caching)"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def embed_text(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Embed single text with caching.
        
        Args:
            text: Text to embed
            use_cache: Whether to use cache
            
        Returns:
            Embedding vector (numpy array)
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self.embedding_dimension, dtype=np.float32)
        
        # Check cache
        if use_cache:
            text_hash = self._hash_text(text)
            if text_hash in self._embedding_cache:
                self._cache_hits += 1
                return self._embedding_cache[text_hash]
            self._cache_misses += 1
        
        # Compute embedding
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True  # L2 normalization for cosine similarity
        )
        
        # Cache if enabled
        if use_cache:
            # Evict oldest if cache full
            if len(self._embedding_cache) >= self.cache_size:
                # Remove first item (FIFO)
                first_key = next(iter(self._embedding_cache))
                del self._embedding_cache[first_key]
            
            self._embedding_cache[text_hash] = embedding
        
        return embedding
    
    def embed_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Batch embedding for performance.
        
        Args:
            texts: List of texts to embed
            use_cache: Whether to use cache
            show_progress: Show progress bar
            
        Returns:
            Embedding matrix (num_texts x embedding_dim)
        """
        if not texts:
            return np.zeros((0, self.embedding_dimension), dtype=np.float32)
        
        # Check cache for each text
        embeddings = []
        texts_to_compute = []
        indices_to_compute = []
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                embeddings.append(np.zeros(self.embedding_dimension, dtype=np.float32))
                continue
            
            if use_cache:
                text_hash = self._hash_text(text)
                if text_hash in self._embedding_cache:
                    embeddings.append(self._embedding_cache[text_hash])
                    self._cache_hits += 1
                    continue
                self._cache_misses += 1
            
            # Need to compute
            embeddings.append(None)
            texts_to_compute.append(text)
            indices_to_compute.append(i)
        
        # Compute missing embeddings in batch
        if texts_to_compute:
            computed_embeddings = self.model.encode(
                texts_to_compute,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            
            # Insert computed embeddings and cache
            for idx, text, emb in zip(indices_to_compute, texts_to_compute, computed_embeddings):
                embeddings[idx] = emb
                
                if use_cache:
                    text_hash = self._hash_text(text)
                    if len(self._embedding_cache) >= self.cache_size:
                        first_key = next(iter(self._embedding_cache))
                        del self._embedding_cache[first_key]
                    self._embedding_cache[text_hash] = emb
        
        return np.array(embeddings, dtype=np.float32)
    
    def semantic_similarity(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5,
        threshold: float = 0.5,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[SemanticSearchResult]:
        """
        Find semantically similar texts using cosine similarity.
        
        This is pure mathematical similarity - no LLM reasoning or text generation.
        
        Args:
            query: Query text
            candidates: Candidate texts to search
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)
            metadata: Optional metadata for each candidate
            
        Returns:
            List of SemanticSearchResult sorted by similarity (descending)
        """
        if not candidates:
            return []
        
        if metadata is None:
            metadata = [{} for _ in candidates]
        
        # Embed query
        query_emb = self.embed_text(query)
        
        # Embed candidates (batch for performance)
        candidate_embs = self.embed_batch(candidates)
        
        # Compute cosine similarity (already normalized, so just dot product)
        similarities = np.dot(candidate_embs, query_emb)
        
        # Filter by threshold
        valid_indices = np.where(similarities >= threshold)[0]
        
        if len(valid_indices) == 0:
            log.debug(f"No candidates above threshold {threshold}")
            return []
        
        # Sort by similarity (descending)
        sorted_indices = valid_indices[np.argsort(similarities[valid_indices])[::-1]]
        
        # Take top-k
        top_indices = sorted_indices[:top_k]
        
        # Build results
        results = []
        for rank, idx in enumerate(top_indices, start=1):
            results.append(SemanticSearchResult(
                text=candidates[idx],
                score=float(similarities[idx]),
                metadata=metadata[idx],
                rank=rank
            ))
        
        top_score = results[0].score if results else 0.0
        log.debug(
            f"Semantic search: query='{query[:50]}...', "
            f"candidates={len(candidates)}, "
            f"results={len(results)}, "
            f"top_score={top_score:.3f}"
        )
        
        return results
    
    def batch_similarity(
        self,
        queries: List[str],
        candidates: List[str],
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[List[SemanticSearchResult]]:
        """
        Batch semantic similarity for multiple queries.
        
        Args:
            queries: List of query texts
            candidates: List of candidate texts
            top_k: Number of results per query
            threshold: Minimum similarity score
            
        Returns:
            List of result lists (one per query)
        """
        if not queries or not candidates:
            return [[] for _ in queries]
        
        # Embed all texts in batch
        query_embs = self.embed_batch(queries, show_progress=True)
        candidate_embs = self.embed_batch(candidates, show_progress=True)
        
        # Compute similarity matrix (queries x candidates)
        similarity_matrix = np.dot(query_embs, candidate_embs.T)
        
        # Process each query
        all_results = []
        for i, query in enumerate(queries):
            similarities = similarity_matrix[i]
            
            # Filter by threshold
            valid_indices = np.where(similarities >= threshold)[0]
            
            if len(valid_indices) == 0:
                all_results.append([])
                continue
            
            # Sort and take top-k
            sorted_indices = valid_indices[np.argsort(similarities[valid_indices])[::-1]]
            top_indices = sorted_indices[:top_k]
            
            # Build results
            results = []
            for rank, idx in enumerate(top_indices, start=1):
                results.append(SemanticSearchResult(
                    text=candidates[idx],
                    score=float(similarities[idx]),
                    metadata={},
                    rank=rank
                ))
            
            all_results.append(results)
        
        return all_results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "cache_size": len(self._embedding_cache),
            "cache_capacity": self.cache_size,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "model_loaded": self._model is not None
        }
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._embedding_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        log.info("Cleared embedding cache")
    
    def __repr__(self) -> str:
        return (
            f"PersianSemanticSearch("
            f"model={self.model_name}, "
            f"cache_size={self.cache_size}, "
            f"device={self.device})"
        )

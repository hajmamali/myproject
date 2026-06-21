#!/usr/bin/env python3
"""
Embedding Provider with BGE-M3 Support
=======================================
Config-driven embedding model loading with instruction prompts
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional, Dict, Any
import torch
import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)


class EmbeddingProvider:
    """
    Ultra-advanced embedding provider with fail-closed DI.
    
    Constructor Injection Contract
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``model`` MUST be injected by bootstrap (primary path).
    Lazy fallback is DEPRECATED and triggers loud warnings.
    
    Architectural Mandate
    ~~~~~~~~~~~~~~~~~~~~~
    Bootstrap wiring is MANDATORY in production. Lazy construction
    exists only for backward compatibility and will be removed.
    
    Supports:
    - BGE-M3 with instruction prompts
    - Any SentenceTransformer model
    - L2 normalization
    - Batch processing
    """
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "auto",
        normalize_embeddings: bool = True,
        query_instruction: Optional[str] = None,
        passage_instruction: Optional[str] = None,
        batch_size: int = 64,
        max_length: int = 512,
        use_fp16: bool = True,
        model: Optional[SentenceTransformer] = None,
        correlation_id: str = "",
        **kwargs
    ):
        """
        Args:
            model_name: HuggingFace model name (only used for lazy fallback)
            device: Device (auto, cuda, cpu)
            normalize_embeddings: L2 normalize embeddings
            query_instruction: Instruction prefix for queries
            passage_instruction: Instruction prefix for passages
            batch_size: Batch size for encoding
            max_length: Max sequence length
            use_fp16: Use FP16 for faster inference
            model: Pre-constructed SentenceTransformer (MANDATORY in production).
                  If None, triggers DEPRECATED lazy fallback with warning.
            correlation_id: Request tracking ID for observability.
        """
        import time
        self._correlation_id = correlation_id or f"embed-{time.time()}"
        self.model_name = model_name
        self.normalize_embeddings = normalize_embeddings
        self.query_instruction = query_instruction or ""
        self.passage_instruction = passage_instruction or ""
        self.batch_size = batch_size
        self.max_length = max_length
        self.use_fp16 = use_fp16
        
        # Determine device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        if model is not None:
            # PRIMARY PATH: Bootstrap-injected model
            self.model = model
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            log.info(
                f"[{self._correlation_id}] ✅ EmbeddingProvider initialized "
                f"(bootstrap-injected model, dim={self.embedding_dim})"
            )
        else:
            # FAIL-CLOSED: No construction allowed outside composition root
            raise ValueError(
                "Embedding model dependency was not injected. "
                "EmbeddingProvider requires a pre-constructed SentenceTransformer "
                "instance via the `model` parameter. "
                "Construction is only permitted in bootstrap/composition root. "
                "Remediation: Update bootstrap/runtime.py to inject SentenceTransformer."
            )
    
    def encode_queries(
        self,
        queries: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Encode queries with instruction prompt
        
        Args:
            queries: List of query strings
            batch_size: Batch size (default: self.batch_size)
            show_progress: Show progress bar
            
        Returns:
            Embeddings array (N, D)
        """
        # Add instruction prefix
        if self.query_instruction:
            queries = [self.query_instruction + q for q in queries]
        
        # Encode
        embeddings = self.model.encode(
            queries,
            batch_size=batch_size or self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def encode_passages(
        self,
        passages: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Encode passages with instruction prompt
        
        Args:
            passages: List of passage strings
            batch_size: Batch size
            show_progress: Show progress bar
            
        Returns:
            Embeddings array (N, D)
        """
        # Add instruction prefix
        if self.passage_instruction:
            passages = [self.passage_instruction + p for p in passages]
        
        # Encode
        embeddings = self.model.encode(
            passages,
            batch_size=batch_size or self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def encode(
        self,
        texts: List[str],
        is_query: bool = True,
        **kwargs
    ) -> np.ndarray:
        """
        Generic encode method
        
        Args:
            texts: List of texts
            is_query: Whether texts are queries (vs passages)
            
        Returns:
            Embeddings array
        """
        if is_query:
            return self.encode_queries(texts, **kwargs)
        else:
            return self.encode_passages(texts, **kwargs)
    
    def get_embedding_dim(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "EmbeddingProvider":
        """
        Create provider from config dict
        
        Args:
            config: Configuration dictionary
            
        Returns:
            EmbeddingProvider instance
        """
        return cls(
            model_name=config.get("model_name", "BAAI/bge-m3"),
            device=config.get("device", "auto"),
            normalize_embeddings=config.get("normalize_embeddings", True),
            query_instruction=config.get("query_instruction"),
            passage_instruction=config.get("passage_instruction"),
            batch_size=config.get("batch_size", 64),
            max_length=config.get("max_length", 512),
            use_fp16=config.get("use_fp16", True)
        )


# Global instance
_provider = None

def get_embedding_provider(config: Optional[Dict] = None) -> EmbeddingProvider:
    """Get global embedding provider"""
    global _provider
    if _provider is None:
        if config is None:
            # Default config
            config = {"model_name": "BAAI/bge-m3"}
        _provider = EmbeddingProvider.from_config(config)
    return _provider

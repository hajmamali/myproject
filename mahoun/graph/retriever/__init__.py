# pipelines/retriever/__init__.py
"""
Retrieval Module
================
BGE-M3 Embedding Provider and Retrieval Components
"""

from .embedding_provider import EmbeddingProvider, get_embedding_provider

__all__ = [
    "EmbeddingProvider",
    "get_embedding_provider",
]

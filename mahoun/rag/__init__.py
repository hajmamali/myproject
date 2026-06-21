"""
RAG (Retrieval-Augmented Generation) Module
============================================

Advanced RAG systems for MAHOUN.
"""
from typing import Any, List, Optional

__version__ = "2.0.0"

# Conditional imports to avoid dependency issues in desktop_minimal mode
try:
    from .ultra_graph_rag import UltraGraphRAG
except ImportError:
    UltraGraphRAG: Optional[Any] = None
try:
    from .ultra_evaluation_system import UltraEvaluationSystem
except ImportError:
    UltraEvaluationSystem: Optional[Any] = None
try:
    from .ultra_indexing_system import UltraIndexingSystem
except ImportError:
    UltraIndexingSystem: Optional[Any] = None
try:
    from .ultra_training_system import UltraTrainingSystem
except ImportError:
    UltraTrainingSystem: Optional[Any] = None
# Always safe imports
try:
    from .hybrid_rag_service import HybridRAGService, RAGMode, create_hybrid_rag_service
    from .query_router import QueryRouter, QueryType, QueryClassification, RoutedQueryResult, route_query
    from .citation_engine import CitationEngine, Citation, CitationResult, extract_citations_from_rag
    from .indexing_pipeline import IndexingPipeline, DocumentType, IndexingResult, index_document
    __all__ = [
        "HybridRAGService",
        "RAGMode",
        "create_hybrid_rag_service",
        # Query Router
        "QueryRouter",
        "QueryType",
        "QueryClassification",
        "RoutedQueryResult",
        "route_query",
        # Citation Engine
        "CitationEngine",
        "Citation",
        "CitationResult",
        "extract_citations_from_rag",
        # Indexing Pipeline
        "IndexingPipeline",
        "DocumentType",
        "IndexingResult",
        "index_document",
    ]
except ImportError:
    __all__: List[Any] = []
# Add optional exports if available
if UltraGraphRAG:
    __all__.append("UltraGraphRAG")
if UltraEvaluationSystem:
    __all__.append("UltraEvaluationSystem")
if UltraIndexingSystem:
    __all__.append("UltraIndexingSystem")
if UltraTrainingSystem:
    __all__.append("UltraTrainingSystem")
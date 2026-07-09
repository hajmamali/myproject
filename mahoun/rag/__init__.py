"""
🔍 MAHOUN RAG Module - Smart Retrieval
=====================================

Advanced RAG (Retrieval-Augmented Generation) systems for MAHOUN.

Main Classes:
    from mahoun.rag import HybridRAGService, QueryRouter
    from mahoun.rag import CitationEngine, FaithfulnessCalculator

CANONICAL LOCATION GUIDE:
- FaithfulnessCalculator → USE ultra_evaluation_system.py (canonical)
- HybridRAGService → USE hybrid_rag_service.py  
- QueryRouter → USE query_router.py

🚨 DEPRECATED/DUPLICATE LOCATIONS (DO NOT USE):
❌ from mahoun.monitoring.legal_metrics import FaithfulnessCalculator  
❌ from mahoun.finetuning.feedback_pipeline import FaithfulnessCalculator

Version 2.0.0: Advanced RAG with graph enhancement and evaluation.
"""
# 🎯 Core RAG Services (Developer Daily Use)
from .hybrid_rag_service import HybridRAGService, RAGMode, create_hybrid_rag_service

# 🔍 Query & Retrieval
from .query_router import QueryRouter, QueryType, QueryClassification, RoutedQueryResult, route_query

# 📝 Citation & Evaluation
from .citation_engine import CitationEngine, Citation, CitationResult, extract_citations_from_rag

# 📊 RAG Evaluation (Canonical)
from .ultra_evaluation_system import (
    FaithfulnessCalculator,  # ✅ CANONICAL - use this one
    RecallCalculator,
    PrecisionCalculator, 
    NDCGCalculator,
)

# 📋 Indexing Pipeline
from .indexing_pipeline import IndexingPipeline, DocumentType, IndexingResult, index_document

__version__ = "2.0.0"

__all__ = [
    # Core RAG service
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
    # Evaluation (Canonical)
    "FaithfulnessCalculator",  # ✅ CANONICAL
    "RecallCalculator",
    "PrecisionCalculator",
    "NDCGCalculator", 
    # Indexing Pipeline
    "IndexingPipeline",
    "DocumentType",
    "IndexingResult",
    "index_document",
]
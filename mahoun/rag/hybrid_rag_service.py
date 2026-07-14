"""
Hybrid RAG Service - Multi-Mode Retrieval
==========================================

Unified RAG service supporting three operational modes:
- graph_only: Pure graph retrieval (when Neo4j available)
- text_only: Pure text retrieval (BM25 + Dense)
- hybrid_graph_first: Graph → Text fusion (DEFAULT)

Design Principles:
- Mode-aware: Automatically adapts to runtime configuration
- Graceful degradation: Falls back to text_only if graph unavailable
- Maintains existing API contracts
- Desktop-Minimal compatible
"""

import logging
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import time

from mahoun.core.runtime_config import get_runtime_settings

logger = logging.getLogger(__name__)


class RAGMode(str, Enum):
    """RAG operational modes"""
    GRAPH_ONLY = "graph_only"
    TEXT_ONLY = "text_only"
    HYBRID_GRAPH_FIRST = "hybrid_graph_first"
    AUTO = "auto"  # Automatically select based on runtime config


@dataclass
class RetrievalResult:
    """Single retrieval result"""
    doc_id: str
    content: str
    score: float
    rank: int
    source: str  # "graph", "text", or "hybrid"
    metadata: Dict[str, Any]


@dataclass
class HybridRAGResult:
    """Complete RAG retrieval result"""
    query: str
    mode_used: str
    results: List[RetrievalResult]
    retrieval_time_ms: float
    metadata: Dict[str, Any]


class HybridRAGService:
    """
    Hybrid RAG Service with multi-mode support.
    
    Usage:
        service = HybridRAGService(
            vector_store=VectorStoreManager(),
            hybrid_search=UltraHybridSearch(),
            graph_retriever=None  # Optional, for graph mode
        )
        
        # Auto mode (selects based on runtime config)
        result = await service.retrieve(
            query="سابقه دخالت ثالث چیست؟",
            mode=RAGMode.AUTO,
            top_k=10
        )
        
        # Force text-only mode
        result = await service.retrieve(
            query="قانون مدنی",
            mode=RAGMode.TEXT_ONLY,
            top_k=5
        )
    """
    
    def __init__(
        self,
        vector_store=None,
        hybrid_search=None,
        graph_retriever=None
    ):
        """
        Initialize Hybrid RAG Service.
        
        Args:
            vector_store: VectorStoreManager instance
            hybrid_search: UltraHybridSearch instance
            graph_retriever: Optional graph retriever (for graph modes)
        """
        self.vector_store = vector_store
        self.hybrid_search = hybrid_search
        self.graph_retriever = graph_retriever
        self.graph_retrieval_enabled = os.getenv(
            "MAHOUN_GRAPH_RETRIEVAL_ENABLED",
            "false"
        ).lower() in ("1", "true", "yes", "on")
        
        # Runtime settings
        self.settings = get_runtime_settings()
        
        # Determine default mode
        self.default_mode = self._determine_default_mode()
        
        # Statistics
        self.stats = {
            "total_retrievals": 0,
            "mode_usage": {
                "graph_only": 0,
                "text_only": 0,
                "hybrid_graph_first": 0
            },
            "avg_retrieval_time_ms": 0.0
        }
        
        logger.info(
            f"HybridRAGService initialized (default_mode: {self.default_mode.value})"
        )
    
    def _determine_default_mode(self) -> RAGMode:
        """Determine default mode based on runtime configuration"""
        if self.settings.graph_enabled and self.graph_retriever is not None:
            return RAGMode.HYBRID_GRAPH_FIRST
        else:
            return RAGMode.TEXT_ONLY
    
    async def retrieve(
        self,
        query: str,
        mode: RAGMode = RAGMode.AUTO,
        top_k: int = 10,
        query_embedding: Optional[List[float]] = None
    ) -> HybridRAGResult:
        """
        Retrieve relevant documents using selected mode.
        
        Args:
            query: Search query
            mode: Retrieval mode (AUTO uses default)
            top_k: Number of results to return
            query_embedding: Optional pre-computed query embedding
            
        Returns:
            HybridRAGResult with retrieved documents
        """
        start_time = time.time()
        
        # Resolve AUTO mode
        if mode == RAGMode.AUTO:
            mode = self.default_mode
        
        if mode == RAGMode.GRAPH_ONLY and not self.graph_retrieval_enabled:
            retrieval_time_ms = (time.time() - start_time) * 1000
            return HybridRAGResult(
                query=query,
                mode_used=mode.value,
                results=[],
                retrieval_time_ms=retrieval_time_ms,
                metadata={
                    "error": "Graph-only retrieval is disabled",
                    "status_code": 501
                }
            )

        logger.debug(f"Retrieving with mode: {mode.value}, top_k: {top_k}")
        
        # Route to appropriate retrieval method
        try:
            if mode == RAGMode.GRAPH_ONLY:
                results = await self._retrieve_graph_only(query, top_k)
            elif mode == RAGMode.TEXT_ONLY:
                results = await self._retrieve_text_only(query, top_k, query_embedding)
            elif mode == RAGMode.HYBRID_GRAPH_FIRST:
                results = await self._retrieve_hybrid_graph_first(query, top_k, query_embedding)
            else:
                logger.warning(f"Unknown mode {mode}, falling back to text_only")
                results = await self._retrieve_text_only(query, top_k, query_embedding)
            
            retrieval_time_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_stats(mode, retrieval_time_ms)
            
            return HybridRAGResult(
                query=query,
                mode_used=mode.value,
                results=results,
                retrieval_time_ms=retrieval_time_ms,
                metadata={
                    "top_k_requested": top_k,
                    "results_returned": len(results)
                }
            )
            
        except Exception as e:
            logger.error(f"Retrieval failed for mode {mode.value}: {e}", exc_info=True)
            
            # Fallback to text_only on error
            if mode != RAGMode.TEXT_ONLY:
                logger.warning("Falling back to text_only mode due to error")
                return await self.retrieve(query, RAGMode.TEXT_ONLY, top_k, query_embedding)
            
            # Return empty result if text_only also fails
            return HybridRAGResult(
                query=query,
                mode_used=mode.value,
                results=[],
                retrieval_time_ms=(time.time() - start_time) * 1000,
                metadata={"error": str(e)}
            )
    
    async def _retrieve_graph_only(
        self,
        query: str,
        top_k: int
    ) -> List[RetrievalResult]:
        """Pure graph retrieval"""
        if self.graph_retriever is None:
            logger.warning("Graph retriever not available, returning empty results")
            return []

        if not self.graph_retrieval_enabled:
            logger.info("Graph-only retrieval disabled by feature flag")
            return []

        try:
            if hasattr(self.graph_retriever, "retrieve"):
                return await self.graph_retriever.retrieve(query=query, top_k=top_k)
        except Exception as e:
            logger.warning(f"Graph retrieval failed: {e}")

        return []
    
    async def _retrieve_text_only(
        self,
        query: str,
        top_k: int,
        query_embedding: Optional[List[float]] = None
    ) -> List[RetrievalResult]:
        """Pure text retrieval using hybrid search (BM25 + Dense)"""
        results: List[Any] = []
        # Use hybrid search if available
        if self.hybrid_search is not None:
            try:
                search_results, metrics = self.hybrid_search.search(
                    query=query,
                    top_k=top_k,
                    query_embedding=query_embedding
                )
                
                for result in search_results:
                    results.append(RetrievalResult(
                        doc_id=result.doc_id,
                        content=result.content,
                        score=result.score,
                        rank=result.rank,
                        source="text",
                        metadata=result.metadata
                    ))
                
                logger.debug(f"Hybrid search returned {len(results)} results")
                return results
                
            except Exception as e:
                logger.error(f"Hybrid search failed: {e}")
        
        # Fallback to vector store direct query
        if self.vector_store is not None:
            try:
                # Generate embedding if not provided
                if query_embedding is None:
                    from mahoun.pipelines.embed_index import EmbeddingService
                    embedding_service = EmbeddingService()
                    embeddings = embedding_service.embed_texts([query], is_query=True)
                    if hasattr(embeddings, 'tolist'):
                        query_embedding = embeddings.tolist()[0]
                    else:
                        query_embedding = embeddings[0]
                
                # Query vector store
                vector_results = await self.vector_store.query(
                    query_embedding=query_embedding,
                    top_k=top_k
                )
                
                for rank, vr in enumerate(vector_results, 1):
                    results.append(RetrievalResult(
                        doc_id=vr.get('id', f'result_{rank}'),
                        content=vr.get('metadata', {}).get('text', ''),
                        score=vr.get('score', 0.0),
                        rank=rank,
                        source="text",
                        metadata=vr.get('metadata', {})
                    ))
                
                logger.debug(f"Vector store returned {len(results)} results")
                return results
                
            except Exception as e:
                logger.error(f"Vector store query failed: {e}")
        
        logger.warning("No text retrieval backend available")
        return []
    
    async def _retrieve_hybrid_graph_first(
        self,
        query: str,
        top_k: int,
        query_embedding: Optional[List[float]] = None
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval: Graph → Text → Fusion.
        
        Strategy:
        1. Retrieve from graph (if available)
        2. Retrieve from text
        3. Merge and re-rank
        """
        from mahoun.core.runtime_config import is_enterprise_graph_mode
        
        all_results: List[Any] = []
        # Step 1: Graph retrieval (if in enterprise_graph mode)
        if is_enterprise_graph_mode() and self.graph_retriever is not None:
            try:
                # Use GraphQueryService to find relevant nodes
                # This is a simplified query - in production, would use semantic search
                graph_query = """
                MATCH (v:Verdict)
                WHERE v.case_type CONTAINS $query OR v.content CONTAINS $query
                RETURN v.verdict_id as id, v.content as content, 0.8 as score
                LIMIT $top_k
                """
                
                graph_result = await self.graph_retriever.execute_query_async(
                    query=graph_query,
                    params={"query": query, "top_k": top_k}
                )
                
                # Convert graph results to RetrievalResult format
                for i, record in enumerate(graph_result.results[:top_k], 1):
                    all_results.append(RetrievalResult(
                        doc_id=record.get("id", f"graph_{i}"),
                        content=record.get("content", ""),
                        score=record.get("score", 0.5),
                        rank=i,
                        source="graph",
                        metadata={"from_graph": True}
                    ))
                
                logger.debug(f"Graph retrieval returned {len(all_results)} results")
            except Exception as e:
                logger.warning(f"Graph retrieval failed: {e}, falling back to text")
        
        # Step 2: Text retrieval
        text_results = await self._retrieve_text_only(query, top_k * 2, query_embedding)
        
        # Step 3: Merge and deduplicate
        seen_ids = {r.doc_id for r in all_results}
        for result in text_results:
            if result.doc_id not in seen_ids:
                result.source = "hybrid"
                all_results.append(result)
                seen_ids.add(result.doc_id)
        
        # Step 4: Re-rank by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Return top_k
        return all_results[:top_k]
    
    def _update_stats(self, mode: RAGMode, retrieval_time_ms: float):
        """Update service statistics"""
        self.stats["total_retrievals"] += 1
        self.stats["mode_usage"][mode.value] += 1
        
        n = self.stats["total_retrievals"]
        self.stats["avg_retrieval_time_ms"] = (
            (self.stats["avg_retrieval_time_ms"] * (n - 1) + retrieval_time_ms) / n
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return self.stats.copy()


# ============================================================================
# Initialization Helper
# ============================================================================

async def create_hybrid_rag_service(
    vector_store=None,
    hybrid_search=None,
    graph_retriever=None,
    embedding_service=None  # NEW: Support shared embedding service
) -> HybridRAGService:
    """
    Create and initialize Hybrid RAG Service.
    
    This helper creates components if not provided and initializes them.
    
    Args:
        vector_store: Optional VectorStoreManager
        hybrid_search: Optional UltraHybridSearch
        graph_retriever: Optional graph retriever
        embedding_service: Optional EmbeddingService (for shared instance)
        
    Returns:
        Initialized HybridRAGService
    """
    # Create vector store if needed
    if vector_store is None:
        try:
            from mahoun.pipelines.vector_store.manager import VectorStoreManager
            vector_store = VectorStoreManager()
            await vector_store.initialize()
            logger.info("Created default VectorStoreManager")
        except Exception as e:
            logger.warning(f"Could not create VectorStoreManager: {e}")
    
    # Create hybrid search if needed
    if hybrid_search is None:
        try:
            from mahoun.retrieval.ultra_hybrid_search import UltraHybridSearch, SearchConfig
            # SearchConfig accepts FusionMethod enum, construct properly
            from mahoun.retrieval.ultra_hybrid_search import FusionMethod
            config = SearchConfig(
                use_bm25=True,
                use_dense=True,
                fusion_method=FusionMethod.RRF,  # Use enum
                final_k=10
            )
            hybrid_search = UltraHybridSearch(config)
            logger.info("✅ UltraHybridSearch created")
        except Exception as e:
            logger.warning(f"Could not create UltraHybridSearch: {e}")
            hybrid_search: Optional[Any] = None
    # Create service
    service = HybridRAGService(
        vector_store=vector_store,
        hybrid_search=hybrid_search,
        graph_retriever=graph_retriever
    )
    
    return service

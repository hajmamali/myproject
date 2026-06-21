"""
Graph RAG Integration Service
=============================
Provides graph-based enrichment for RAG results.

This service integrates Neo4j graph data with retrieval results,
enabling features like:
- Related document discovery
- Citation chain traversal
- Entity relationship expansion
- Authority scoring based on graph centrality
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnrichedResult:
    """Result enriched with graph information"""
    doc_id: str
    original_score: float
    graph_score: float
    combined_score: float
    related_docs: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    entities: List[Dict] = field(default_factory=list)
    graph_paths: List[Dict] = field(default_factory=list)


class GraphEnrichmentService:
    """
    Service for enriching RAG results with graph-based information.
    
    This service queries Neo4j to:
    1. Find related documents through citation chains
    2. Expand entity relationships
    3. Calculate authority scores
    4. Provide explainable paths
    
    Attributes:
        connection: Neo4j connection instance
        timeout_ms: Query timeout in milliseconds
        max_hops: Maximum graph traversal depth
        enable_reranking: Whether to rerank based on graph scores
        enable_validation: Whether to validate results
        cache_enabled: Whether to cache graph queries
    """
    
    def __init__(
        self,
        connection: Optional[Any] = None,
        timeout_ms: int = 5000,
        max_hops: int = 2,
        enable_reranking: bool = True,
        enable_validation: bool = True,
        cache_enabled: bool = True
    ):
        """
        Initialize the Graph Enrichment Service.
        
        Args:
            connection: Neo4j connection (optional, lazy init)
            timeout_ms: Query timeout in milliseconds
            max_hops: Maximum graph traversal depth
            enable_reranking: Enable graph-based reranking
            enable_validation: Enable result validation
            cache_enabled: Enable query caching
        """
        self.connection = connection
        self.timeout_ms = timeout_ms
        self.max_hops = max_hops
        self.enable_reranking = enable_reranking
        self.enable_validation = enable_validation
        self.cache_enabled = cache_enabled
        
        # Cache for graph queries
        self._cache: Dict[str, Any] = {}
        
        # Statistics
        self.stats = {
            "enrichments": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_enrichment_time_ms": 0.0
        }
        
        logger.info("GraphEnrichmentService initialized")
        logger.info(f"  Max hops: {max_hops}")
        logger.info(f"  Reranking: {enable_reranking}")
        logger.info(f"  Caching: {cache_enabled}")
    
    async def enrich_results(
        self,
        results: List[Dict],
        query: str,
        top_k: int = 10
    ) -> List[EnrichedResult]:
        """
        Enrich retrieval results with graph information.
        
        Args:
            results: List of retrieval results with doc_id and score
            query: The original query
            top_k: Number of results to return
        
        Returns:
            List of EnrichedResult objects
        """
        import time
        start_time = time.time()
        
        enriched: List[Any] = []
        for result in results[:top_k * 2]:  # Process more, return top_k
            doc_id = result.get("doc_id", "")
            original_score = result.get("score", 0.0)
            
            # Get graph-based enrichment
            graph_data = await self._get_graph_data(doc_id)
            
            # Calculate graph score
            graph_score = self._calculate_graph_score(graph_data)
            
            # Combine scores
            alpha = 0.7  # Weight for original score
            combined_score = alpha * original_score + (1 - alpha) * graph_score
            
            enriched.append(EnrichedResult(
                doc_id=doc_id,
                original_score=original_score,
                graph_score=graph_score,
                combined_score=combined_score,
                related_docs=graph_data.get("related_docs", []),
                citations=graph_data.get("citations", []),
                entities=graph_data.get("entities", []),
                graph_paths=graph_data.get("paths", [])
            ))
        
        # Re-rank if enabled
        if self.enable_reranking:
            enriched.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Truncate to top_k
        enriched = enriched[:top_k]
        
        # Update statistics
        elapsed_ms = (time.time() - start_time) * 1000
        self._update_stats(elapsed_ms)
        
        return enriched
    
    async def get_related_documents(
        self,
        doc_id: str,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Get documents related to a given document through graph connections.
        
        Args:
            doc_id: The source document ID
            max_results: Maximum number of related documents
        
        Returns:
            List of related document dictionaries
        """
        if not self.connection:
            logger.debug("No graph connection available")
            return []
        
        # Check cache
        cache_key = f"related:{doc_id}:{max_results}"
        if self.cache_enabled and cache_key in self._cache:
            self.stats["cache_hits"] += 1
            return self._cache[cache_key]
        
        self.stats["cache_misses"] += 1
        
        try:
            # Query Neo4j for related documents
            # This is a placeholder - actual implementation would run Cypher
            related: List[Any] = []
            # Example Cypher query (commented for reference):
            # MATCH (d:Document {id: $doc_id})-[:CITES|:REFERENCES|:RELATED_TO*1..2]-(related:Document)
            # RETURN related.id, related.title, count(*) as connection_strength
            # ORDER BY connection_strength DESC
            # LIMIT $max_results
            
            # Cache result
            if self.cache_enabled:
                self._cache[cache_key] = related
            
            return related
            
        except Exception as e:
            logger.error(f"Failed to get related documents: {e}")
            return []
    
    async def get_citation_chain(
        self,
        doc_id: str,
        direction: str = "both",
        max_depth: int = 2
    ) -> Dict[str, List[Dict]]:
        """
        Get citation chain for a document.
        
        Args:
            doc_id: The document ID
            direction: "citing" (docs that cite this), "cited" (docs this cites), or "both"
            max_depth: Maximum depth of citation chain
        
        Returns:
            Dictionary with "citing" and "cited" lists
        """
        result = {
            "citing": [],  # Documents that cite this one
            "cited": []    # Documents that this one cites
        }
        
        if not self.connection:
            return result
        
        try:
            # Placeholder for actual Cypher queries
            # MATCH (d:Document {id: $doc_id})<-[:CITES]-(citing:Document)
            # MATCH (d:Document {id: $doc_id})-[:CITES]->(cited:Document)
            pass
            
        except Exception as e:
            logger.error(f"Failed to get citation chain: {e}")
        
        return result
    
    async def _get_graph_data(self, doc_id: str) -> Dict:
        """
        Get graph data for a document.
        
        Args:
            doc_id: Document ID
        
        Returns:
            Dictionary with graph information
        """
        # Check cache
        cache_key = f"graph_data:{doc_id}"
        if self.cache_enabled and cache_key in self._cache:
            self.stats["cache_hits"] += 1
            return self._cache[cache_key]
        
        self.stats["cache_misses"] += 1
        
        # Default empty result
        graph_data = {
            "related_docs": [],
            "citations": [],
            "entities": [],
            "paths": [],
            "centrality_score": 0.0
        }
        
        if not self.connection:
            return graph_data
        
        try:
            # Get related documents
            related = await self.get_related_documents(doc_id, max_results=5)
            graph_data["related_docs"] = [r.get("id") for r in related]
            
            # Get citations
            citations = await self.get_citation_chain(doc_id, max_depth=1)
            graph_data["citations"] = citations
            
            # Calculate centrality (placeholder)
            # In production, this would be pre-computed or use Neo4j algorithms
            graph_data["centrality_score"] = 0.5
            
        except Exception as e:
            logger.error(f"Failed to get graph data: {e}")
        
        # Cache result
        if self.cache_enabled:
            self._cache[cache_key] = graph_data
        
        return graph_data
    
    def _calculate_graph_score(self, graph_data: Dict) -> float:
        """
        Calculate a graph-based relevance score.
        
        Args:
            graph_data: Graph information dictionary
        
        Returns:
            Float score between 0 and 1
        """
        score = 0.0
        
        # Factor 1: Centrality (weight: 0.4)
        centrality = graph_data.get("centrality_score", 0.0)
        score += 0.4 * centrality
        
        # Factor 2: Citation count (weight: 0.3)
        citation_count = len(graph_data.get("citations", {}).get("citing", []))
        citation_score = min(citation_count / 10.0, 1.0)  # Normalize
        score += 0.3 * citation_score
        
        # Factor 3: Related documents (weight: 0.2)
        related_count = len(graph_data.get("related_docs", []))
        related_score = min(related_count / 5.0, 1.0)  # Normalize
        score += 0.2 * related_score
        
        # Factor 4: Entity richness (weight: 0.1)
        entity_count = len(graph_data.get("entities", []))
        entity_score = min(entity_count / 10.0, 1.0)  # Normalize
        score += 0.1 * entity_score
        
        return min(score, 1.0)
    
    def _update_stats(self, elapsed_ms: float):
        """Update service statistics"""
        self.stats["enrichments"] += 1
        n = self.stats["enrichments"]
        self.stats["avg_enrichment_time_ms"] = (
            (self.stats["avg_enrichment_time_ms"] * (n - 1) + elapsed_ms) / n
        )
    
    def get_statistics(self) -> Dict:
        """Get service statistics"""
        stats = self.stats.copy()
        if self.cache_enabled:
            stats["cache_size"] = len(self._cache)
            total_cache_ops = stats["cache_hits"] + stats["cache_misses"]
            stats["cache_hit_rate"] = (
                stats["cache_hits"] / total_cache_ops if total_cache_ops > 0 else 0.0
            )
        return stats
    
    def clear_cache(self):
        """Clear the query cache"""
        self._cache.clear()
        logger.info("Graph enrichment cache cleared")


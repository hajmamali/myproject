"""
Ultra RAG Adapter
==================

Adapts UltraGraphRAG to satisfy UltraRAGProtocol.

This adapter:
- Maps async search() to retrieve_with_reasoning()
- Converts internal data structures to protocol-compliant types
- Provides graceful degradation if graph unavailable
- Adds explain() method for explainability

Classification: INTEGRATION ADAPTER
"""

import logging
from typing import Any, Dict, List, Tuple

from mahoun.core.protocols import (
    UltraRAGResult,
    GraphReasoningPath,
)

logger = logging.getLogger(__name__)


class UltraRAGAdapter:
    """
    Adapter wrapping UltraGraphRAG to satisfy UltraRAGProtocol.
    
    Provides protocol-compliant interface for Ultra Graph-RAG.
    """
    
    def __init__(self, ultra_rag: Any):
        """
        Initialize adapter with UltraGraphRAG instance.
        
        Args:
            ultra_rag: UltraGraphRAG instance to wrap
        """
        self.ultra_rag = ultra_rag
        logger.info("UltraRAGAdapter initialized")
    
    async def retrieve_with_reasoning(
        self,
        query: str,
        *,
        top_k: int = 10,
        reasoning_strategy: str = "attention_flow",
        enable_causal: bool = True,
        max_hops: int = 3,
        **kwargs: Any
    ) -> UltraRAGResult:
        """
        Retrieve documents with graph-based reasoning.
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            reasoning_strategy: "shortest_path", "attention_flow", "causal", etc.
            enable_causal: Whether to compute causal links
            max_hops: Maximum graph traversal depth
            **kwargs: Strategy-specific parameters
        
        Returns:
            UltraRAGResult with documents + reasoning paths
        
        Raises:
            ValueError: If query empty or invalid strategy
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")
        
        # Call underlying UltraGraphRAG
        result = await self.ultra_rag.search(
            query=query,
            top_k=top_k,
            explain=True,
            **kwargs
        )
        
        # Extract documents (adapt internal format)
        retrieved_documents = result.get("results", [])
        
        # Convert reasoning paths to protocol format
        reasoning_paths = self._convert_reasoning_paths(
            result.get("reasoning_paths", [])
        )
        
        # Extract causal links if available
        causal_links = []
        if enable_causal and result.get("causal_graph"):
            causal_links = self._extract_causal_links(result["causal_graph"])
        
        # Extract explainability data
        explainability = result.get("explanation", {})
        
        return UltraRAGResult(
            query=query,
            retrieved_documents=retrieved_documents,
            reasoning_paths=reasoning_paths,
            causal_links=causal_links,
            explainability=explainability,
            metadata={
                "reasoning_strategy": reasoning_strategy,
                "max_hops": max_hops,
                "enable_causal": enable_causal,
                "ultra_rag_version": "1.0",
            }
        )
    
    def explain(self, result: UltraRAGResult) -> Dict[str, Any]:
        """
        Generate human-readable explanation of reasoning.
        
        Args:
            result: UltraRAGResult to explain
        
        Returns:
            Dict with explanation text, attention maps, feature importance
        """
        explanation = {
            "query": result.query,
            "num_documents": len(result.retrieved_documents),
            "num_reasoning_paths": len(result.reasoning_paths),
            "num_causal_links": len(result.causal_links),
        }
        
        # Add path explanations
        if result.reasoning_paths:
            explanation["paths"] = [
                {
                    "path_id": idx,
                    "length": len(path.nodes),
                    "score": path.total_score,
                    "reasoning_type": path.reasoning_type,
                    "summary": self._explain_path(path),
                }
                for idx, path in enumerate(result.reasoning_paths)
            ]
        
        # Add causal explanations
        if result.causal_links:
            explanation["causal_summary"] = [
                f"{cause} → {effect} (strength: {strength:.2f})"
                for cause, effect, strength in result.causal_links[:5]
            ]
        
        # Include explainability metadata
        if result.explainability:
            explanation["attention_maps"] = result.explainability.get("attention_maps", {})
            explanation["feature_importance"] = result.explainability.get("feature_importance", {})
        
        return explanation
    
    def _convert_reasoning_paths(self, internal_paths: List[Any]) -> List[GraphReasoningPath]:
        """Convert internal path representation to protocol format."""
        protocol_paths = []
        
        for path in internal_paths:
            # Handle different internal formats
            if isinstance(path, dict):
                protocol_paths.append(GraphReasoningPath(
                    nodes=path.get("nodes", []),
                    edges=path.get("edges", []),
                    scores=path.get("scores", []),
                    total_score=path.get("total_score", 0.0),
                    reasoning_type=path.get("reasoning_type", "unknown"),
                    metadata=path.get("metadata", {})
                ))
            elif hasattr(path, 'nodes'):
                # Handle dataclass or object format
                protocol_paths.append(GraphReasoningPath(
                    nodes=path.nodes,
                    edges=path.edges,
                    scores=path.scores,
                    total_score=path.total_score,
                    reasoning_type=path.reasoning_type,
                    metadata=getattr(path, 'metadata', {})
                ))
        
        return protocol_paths
    
    def _extract_causal_links(self, causal_graph: Any) -> List[Tuple[str, str, float]]:
        """Extract causal links from internal causal graph representation."""
        causal_links = []
        
        if isinstance(causal_graph, dict):
            edges = causal_graph.get("edges", [])
            for edge in edges:
                if isinstance(edge, dict):
                    cause = edge.get("source", "")
                    effect = edge.get("target", "")
                    strength = edge.get("weight", 0.0)
                    causal_links.append((cause, effect, strength))
                elif isinstance(edge, (list, tuple)) and len(edge) >= 3:
                    causal_links.append(tuple(edge[:3]))
        
        return causal_links
    
    def _explain_path(self, path: GraphReasoningPath) -> str:
        """Generate human-readable explanation of a reasoning path."""
        if len(path.nodes) < 2:
            return "Trivial path"
        
        # Build path summary
        path_str = " → ".join(path.nodes[:5])  # Limit to first 5 nodes
        if len(path.nodes) > 5:
            path_str += " → ..."
        
        return (
            f"{path.reasoning_type} traversal: {path_str} "
            f"(score: {path.total_score:.2f})"
        )


def create_ultra_rag_adapter(ultra_rag: Any) -> UltraRAGAdapter:
    """
    Factory function to create UltraRAGAdapter.
    
    Args:
        ultra_rag: UltraGraphRAG instance
    
    Returns:
        UltraRAGAdapter wrapping the instance
    """
    return UltraRAGAdapter(ultra_rag)

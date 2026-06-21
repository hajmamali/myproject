"""
Graph Module - Enterprise Graph Builder
========================================

Exports the recommended graph builder for production use.

For backward compatibility, UltraGraphBuilder is still available,
but ConcurrentGraphBuilder is recommended for production.

LAZY LOADING:
All graph builders are imported on-demand via __getattr__ to minimize import-time overhead.
"""
from typing import Any

__all__ = [
    "UltraGraphBuilder",
    "ConcurrentGraphBuilder",
    "DefaultGraphBuilder",
    "GraphNode",
    "GraphEdge",
]

_HAS_CONCURRENT_BUILDER: Any = None  # Lazy-evaluated

def __getattr__(name: str) -> Any:
    """Lazy-load graph builders on first access."""
    global _HAS_CONCURRENT_BUILDER
    
    if name == "UltraGraphBuilder":
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        return UltraGraphBuilder
    elif name == "GraphNode":
        from mahoun.graph.ultra_graph_builder import GraphNode
        return GraphNode
    elif name == "GraphEdge":
        from mahoun.graph.ultra_graph_builder import GraphEdge
        return GraphEdge
    elif name == "ConcurrentGraphBuilder":
        try:
            from mahoun.graph.concurrent_graph_builder import ConcurrentGraphBuilder
            return ConcurrentGraphBuilder
        except ImportError:
            return None
    elif name == "DefaultGraphBuilder":
        # Determine default on first access
        if _HAS_CONCURRENT_BUILDER is None:
            try:
                from mahoun.graph.concurrent_graph_builder import ConcurrentGraphBuilder
                _HAS_CONCURRENT_BUILDER = True
            except ImportError:
                _HAS_CONCURRENT_BUILDER = False
        
        if _HAS_CONCURRENT_BUILDER:
            from mahoun.graph.concurrent_graph_builder import ConcurrentGraphBuilder
            return ConcurrentGraphBuilder
        else:
            from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
            return UltraGraphBuilder
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

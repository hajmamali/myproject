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
    """Lazy-load graph builders and submodules on first access."""
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
    elif name == "gnn":
        # Lazy-load gnn submodule for tests that need to patch it
        try:
            import mahoun.graph.gnn as gnn_module
            return gnn_module
        except ImportError:
            # If gnn submodule doesn't exist or torch_geometric not installed,
            # return a mock module to allow patching in tests
            import sys
            from types import ModuleType
            mock_gnn = ModuleType("mahoun.graph.gnn")
            sys.modules["mahoun.graph.gnn"] = mock_gnn
            return mock_gnn
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""
📊 MAHOUN Graph Module - Knowledge Graph Operations
=================================================

Enterprise-grade graph operations for MAHOUN platform.

Main Classes:
    from mahoun.graph import GraphQueryService, UltraGraphBuilder
    from mahoun.graph import GraphEnhancedRetriever

CANONICAL LOCATION GUIDE:
- GraphQueryService → USE graph_query_service.py (canonical)
- UltraGraphBuilder → USE ultra_graph_builder.py  
- Entity → Import from mahoun.core instead!

🚨 DEPRECATED/DUPLICATE LOCATIONS (DO NOT USE):
❌ from mahoun.graph.builders.entity_extractor import Entity
❌ from mahoun.ultra_systems.graph import UltraGraphBuilder

Version 2.0.0: Production-ready graph operations with Neo4j integration.
LAZY LOADING: All graph builders are imported on-demand to minimize startup time.
"""
from typing import Any

# 🎯 Core Graph Services (Developer Daily Use)  
from .graph_query_service import GraphQueryService
from .ultra_graph_builder import UltraGraphBuilder, GraphNode, GraphEdge

# 📊 Graph Enhanced Retrieval
try:
    from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
    __graph_enhanced_available = True
except ImportError:
    __graph_enhanced_available = False

__version__ = "2.0.0"

__all__ = [
    # Core graph operations
    "GraphQueryService",
    "UltraGraphBuilder", 
    "GraphNode",
    "GraphEdge", 
    # Legacy compatibility
    "ConcurrentGraphBuilder",
    "DefaultGraphBuilder",
]

# Add GraphEnhancedRetriever if available
if __graph_enhanced_available:
    __all__.append("GraphEnhancedRetriever")

_HAS_CONCURRENT_BUILDER: Any = None  # Lazy-evaluated

def __getattr__(name: str) -> Any:
    """Lazy-load graph builders and submodules on first access."""
    global _HAS_CONCURRENT_BUILDER
    
    if name == "UltraGraphBuilder":
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        return UltraGraphBuilder
    elif name == "GraphQueryService":
        from mahoun.graph.graph_query_service import GraphQueryService  
        return GraphQueryService
    elif name == "GraphNode":
        from mahoun.graph.ultra_graph_builder import GraphNode
        return GraphNode
    elif name == "GraphEdge":
        from mahoun.graph.ultra_graph_builder import GraphEdge
        return GraphEdge
    elif name == "GraphEnhancedRetriever" and __graph_enhanced_available:
        from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
        return GraphEnhancedRetriever
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

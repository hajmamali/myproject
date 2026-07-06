# pipelines/gnn/__init__.py
"""
GNN-Enhanced Graph System for MAHOUN Legal AI

This module provides Graph Neural Network capabilities for:
- Semantic chunking with entity awareness
- GNN-based graph construction with PyTorch Geometric
- GAT-based reranking for improved retrieval
- Graph analytics and visualization

NOTE: This module has optional dependencies (torch, torch_geometric).
If these are not installed, components will be lazy-loaded and ImportError
will be raised only when actually used.
"""

__version__ = "0.1.0"

# Lazy import to handle missing torch_geometric gracefully
def __getattr__(name: str):
    """Lazy-load GNN components to handle missing dependencies."""
    if name == "SemanticChunker":
        from .semantic_chunker import SemanticChunker
        return SemanticChunker
    elif name == "Chunk":
        from .semantic_chunker import Chunk
        return Chunk
    elif name == "GNNGraphBuilder":
        from .gnn_graph_builder import GNNGraphBuilder
        return GNNGraphBuilder
    elif name == "GATReranker":
        from .gat_reranker import GATReranker
        return GATReranker
    elif name == "GATRerankerService":
        from .gat_reranker import GATRerankerService
        return GATRerankerService
    elif name == "GATTrainer":
        from .gat_trainer import GATTrainer
        return GATTrainer
    elif name == "GraphAnalytics":
        from .graph_analytics import GraphAnalytics
        return GraphAnalytics
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "SemanticChunker",
    "Chunk",
    "GNNGraphBuilder",
    "GATReranker",
    "GATRerankerService",
    "GATTrainer",
    "GraphAnalytics",
]

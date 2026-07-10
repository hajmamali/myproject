# pipelines/gnn/__init__.py
"""
GNN-Enhanced Graph System for MAHOUN Legal AI

This module provides Graph Neural Network capabilities for:
- Semantic chunking with entity awareness
- GNN-based graph construction with PyTorch Geometric
- GAT-based reranking for improved retrieval
- Graph analytics and visualization
"""

__version__ = "0.1.0"

# Import main components
from .semantic_chunker import SemanticChunker, Chunk
from .gnn_graph_builder import GNNGraphBuilder
from .gat_reranker import GATReranker, GATRerankerService
from .gat_trainer import GATTrainer
from .graph_analytics import GraphAnalytics

__all__ = [
    "SemanticChunker",
    "Chunk",
    "GNNGraphBuilder",
    "GATReranker",
    "GATRerankerService",
    "GATTrainer",
    "GraphAnalytics",
]

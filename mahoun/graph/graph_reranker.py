"""
Graph-based Reranker for RAG Systems
=====================================
Uses GNN for re-ranking retrieved documents based on their relationships.

Note: Requires torch and sklearn for full functionality.
Falls back to simple similarity-based reranking without torch.
"""

import numpy as np
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional torch import
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch: Optional[Any] = None
    nn: Optional[Any] = None
    F: Optional[Any] = None
    logger.info("torch not available - GraphReranker will use fallback mode")

# Optional sklearn import
try:
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    cosine_similarity: Optional[Any] = None
    logger.info("sklearn not available - using numpy for similarity")


def _numpy_cosine_similarity(embeddings: np.ndarray) -> np.ndarray:
    """Fallback cosine similarity using numpy"""
    norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / (norm + 1e-10)
    return np.dot(normalized, normalized.T)


# Base class that works without torch
class GraphRerankerBase:
    """
    Base Graph Reranker that works without torch.
    Uses simple similarity-based reranking.
    """
    
    def __init__(
        self, 
        input_dim: int = 384, 
        hidden_dim: int = 256, 
        output_dim: int = 1, 
        num_layers: int = 2
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.num_layers = num_layers
    
    def create_similarity_graph(
        self, embeddings: np.ndarray, threshold: float = 0.5
    ) -> np.ndarray:
        """Create a similarity graph from embeddings."""
        if HAS_SKLEARN:
            sim_matrix = cosine_similarity(embeddings)
        else:
            sim_matrix = _numpy_cosine_similarity(embeddings)
        
        adj_matrix = (sim_matrix >= threshold).astype(np.float32)
        np.fill_diagonal(adj_matrix, 0)
        return adj_matrix

    def create_citation_graph(self, documents: List[Dict]) -> np.ndarray:
        """Create a citation graph based on explicit references in legal documents."""
        docs = [doc.get("text", str(doc)) for doc in documents]
        n_docs = len(docs)
        adj_matrix = np.zeros((n_docs, n_docs), dtype=np.float32)

        citation_patterns = [
            r"ماده\s+(\d+)",
            r"حکم\s+شماره\s+(\d+)",
            r"دادنامه\s+شماره\s+(\d+)",
            r"ر\.?\s*\d+",
        ]

        for i, doc_i in enumerate(docs):
            for j, doc_j in enumerate(docs):
                if i != j:
                    for pattern in citation_patterns:
                        matches_i = set(re.findall(pattern, doc_i, re.IGNORECASE))
                        matches_j = set(re.findall(pattern, doc_j, re.IGNORECASE))
                        if matches_i & matches_j:
                            adj_matrix[i][j] = 1.0
                            break

        return adj_matrix
    
    def rerank(
        self,
        query: str,
        retrieved_docs: List[Dict],
        embeddings: np.ndarray,
        method: str = "similarity",
        threshold: float = 0.5,
    ) -> List[Dict]:
        """Rerank documents using similarity-based scoring (fallback mode)."""
        if len(retrieved_docs) <= 1:
            return retrieved_docs

        # Create graph
        if method == "similarity":
            adj_matrix = self.create_similarity_graph(embeddings, threshold)
        elif method == "citation":
            adj_matrix = self.create_citation_graph(retrieved_docs)
        elif method == "combined":
            sim_adj = self.create_similarity_graph(embeddings, threshold)
            cit_adj = self.create_citation_graph(retrieved_docs)
            adj_matrix = np.maximum(sim_adj, cit_adj)
        else:
            raise ValueError(f"Unknown method: {method}")

        # Simple PageRank-like scoring
        scores = self._simple_graph_score(adj_matrix)
        
        # Sort by scores
        sorted_indices = np.argsort(scores)[::-1].tolist()
        return [retrieved_docs[i] for i in sorted_indices]
    
    def _simple_graph_score(self, adj_matrix: np.ndarray) -> np.ndarray:
        """Simple degree-based scoring"""
        # Sum of connections (in-degree + out-degree)
        scores = adj_matrix.sum(axis=0) + adj_matrix.sum(axis=1)
        # Normalize
        if scores.max() > 0:
            scores = scores / scores.max()
        return scores


# Full GNN-based reranker (requires torch)
if HAS_TORCH:
    class GraphReranker(nn.Module):
        """
        Graph-based reranker for RAG systems using GNNs.
        Implements a lightweight GNN for re-ranking retrieved documents.
        """

        def __init__(
            self, 
            input_dim: int = 384, 
            hidden_dim: int = 256, 
            output_dim: int = 1, 
            num_layers: int = 2
        ):
            super(GraphReranker, self).__init__()

            self.input_dim = input_dim
            self.hidden_dim = hidden_dim
            self.output_dim = output_dim
            self.num_layers = num_layers

            # GNN layers
            self.gnn_layers = nn.ModuleList()
            self.gnn_layers.append(nn.Linear(input_dim, hidden_dim))

            for _ in range(num_layers - 1):
                self.gnn_layers.append(nn.Linear(hidden_dim, hidden_dim))

            self.output_layer = nn.Linear(hidden_dim, output_dim)
            self.activation = nn.ReLU()

        def create_similarity_graph(
            self, embeddings: np.ndarray, threshold: float = 0.5
        ) -> "torch.Tensor":
            """Create a similarity graph from embeddings."""
            if HAS_SKLEARN:
                sim_matrix = cosine_similarity(embeddings)
            else:
                sim_matrix = _numpy_cosine_similarity(embeddings)

            adj_matrix = (sim_matrix >= threshold).astype(np.float32)
            np.fill_diagonal(adj_matrix, 0)
            return torch.tensor(adj_matrix, dtype=torch.float32)

        def create_citation_graph(self, documents: List[Dict]) -> "torch.Tensor":
            """Create a citation graph based on explicit references."""
            docs = [doc.get("text", str(doc)) for doc in documents]
            n_docs = len(docs)
            adj_matrix = np.zeros((n_docs, n_docs), dtype=np.float32)

            citation_patterns = [
                r"ماده\s+(\d+)",
                r"حکم\s+شماره\s+(\d+)",
                r"دادنامه\s+شماره\s+(\d+)",
                r"ر\.?\s*\d+",
            ]

            for i, doc_i in enumerate(docs):
                for j, doc_j in enumerate(docs):
                    if i != j:
                        for pattern in citation_patterns:
                            matches_i = set(re.findall(pattern, doc_i, re.IGNORECASE))
                            matches_j = set(re.findall(pattern, doc_j, re.IGNORECASE))
                            if matches_i & matches_j:
                                adj_matrix[i][j] = 1.0
                                break

            return torch.tensor(adj_matrix, dtype=torch.float32)

        def forward(
            self, embeddings: "torch.Tensor", adj_matrix: "torch.Tensor"
        ) -> "torch.Tensor":
            """Forward pass through the GNN."""
            adj_matrix = adj_matrix + torch.eye(
                adj_matrix.size(0), dtype=adj_matrix.dtype, device=adj_matrix.device
            )

            rowsum = adj_matrix.sum(dim=1)
            d_inv_sqrt = torch.diag(torch.pow(rowsum + 1e-10, -0.5))
            adj_norm = torch.mm(torch.mm(d_inv_sqrt, adj_matrix), d_inv_sqrt)

            h = embeddings
            for layer in self.gnn_layers:
                h = layer(h)
                h = torch.mm(adj_norm, h)
                h = self.activation(h)

            scores = self.output_layer(h)
            return torch.sigmoid(scores)

        def rerank(
            self,
            query: str,
            retrieved_docs: List[Dict],
            embeddings: np.ndarray,
            method: str = "similarity",
            threshold: float = 0.5,
        ) -> List[Dict]:
            """Rerank documents using the GNN-based reranker."""
            if len(retrieved_docs) <= 1:
                return retrieved_docs

            embeddings_tensor = torch.tensor(embeddings, dtype=torch.float32)

            if method == "similarity":
                adj_matrix = self.create_similarity_graph(embeddings, threshold)
            elif method == "citation":
                adj_matrix = self.create_citation_graph(retrieved_docs)
            elif method == "combined":
                sim_adj = self.create_similarity_graph(embeddings, threshold)
                cit_adj = self.create_citation_graph(retrieved_docs)
                adj_matrix = torch.max(sim_adj, cit_adj)
            else:
                raise ValueError(f"Unknown method: {method}")

            with torch.no_grad():
                scores = self.forward(embeddings_tensor, adj_matrix)

            sorted_indices = torch.argsort(scores, dim=0, descending=True).squeeze().tolist()

            if not isinstance(sorted_indices, list):
                sorted_indices = [sorted_indices]

            return [retrieved_docs[i] for i in sorted_indices]

else:
    # Fallback when torch is not available
    GraphReranker = GraphRerankerBase


def get_reranker(input_dim: int = 384, **kwargs) -> Any:
    """
    Factory function to get the appropriate reranker.
    
    Returns GraphReranker if torch is available, otherwise GraphRerankerBase.
    """
    if HAS_TORCH:
        logger.info("Using GNN-based GraphReranker (torch available)")
        return GraphReranker(input_dim=input_dim, **kwargs)
    else:
        logger.info("Using fallback GraphRerankerBase (torch not available)")
        return GraphRerankerBase(input_dim=input_dim, **kwargs)


# Test function
def test_graph_reranker():
    """Test the graph reranker"""
    num_docs = 5
    embedding_dim = 384

    embeddings = np.random.rand(num_docs, embedding_dim).astype(np.float32)

    documents = [
        {
            "id": i,
            "title": f"Document {i}",
            "text": f"This is document {i}. ماده 123 mentioned here.",
        }
        for i in range(num_docs)
    ]

    reranker = get_reranker(input_dim=embedding_dim)
    
    query = "legal ruling about article 123"
    reranked_docs = reranker.rerank(query, documents, embeddings, method="combined")

    print(f"Reranker type: {type(reranker).__name__}")
    print(f"torch available: {HAS_TORCH}")
    print("\nReranked order:")
    for i, doc in enumerate(reranked_docs):
        print(f"  {i}: {doc['title']}")

    return reranked_docs


if __name__ == "__main__":
    test_graph_reranker()

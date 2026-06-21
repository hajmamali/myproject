"""
Document Citation Graph using GNNs
==================================
Multi-document legal reasoning with graph neural networks.

Note: Requires torch for full functionality.
"""

import numpy as np
from typing import Any, Dict, List, Optional, Tuple
import logging
import re

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
    logger.info("torch not available - DocumentCitationGraph requires torch")


def _check_torch():
    if not HAS_TORCH:
        raise RuntimeError("DocumentCitationGraph requires torch. Install with: pip install torch")


class DocumentCitationGraph:
    """
    Document citation graph component using GNNs for multi-document legal reasoning.
    Requires torch for instantiation.
    """

    def __init__(self, input_dim: int = 384, hidden_dim: int = 256, output_dim: int = 384):
        _check_torch()
        """
        Initialize the Document Citation Graph.

        Args:
            input_dim: Dimension of input embeddings
            hidden_dim: Dimension of hidden layers
            output_dim: Dimension of output embeddings
        """
        super(DocumentCitationGraph, self).__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        # GNN layers for message passing
        self.gnn_layer1 = nn.Linear(input_dim, hidden_dim)
        self.gnn_layer2 = nn.Linear(hidden_dim, output_dim)

        # Activation function
        self.activation = nn.ReLU()

    def create_citation_graph(self, documents: List[Dict]) -> Tuple[torch.Tensor, List[int]]:
        """
        Create a citation graph from legal documents.

        Args:
            documents: List of documents with text content

        Returns:
            Adjacency matrix and mapping of document indices
        """
        n_docs = len(documents)
        adj_matrix = torch.zeros((n_docs, n_docs), dtype=torch.float32)

        # Define patterns for legal citations in Persian legal texts
        citation_patterns = [
            r"دادنامه\s+شماره\s+(\d+)",  # "judgment number"
            r"حکم\s+شماره\s+(\d+)",  # "ruling number"
            r"ر\.?\s*(\d+)",  # "r." followed by number
            r"ماده\s+(\d+)",  # "article" in Persian
            r"ماده\s+(\d+)\s*و\s*(\d+)",  # "articles X and Y"
            r"ماده\s+(\d+)\s*،?\s*(\d+)",  # "articles X, Y"
        ]

        # Extract citation numbers from each document
        doc_citations: List[Any] = []
        for doc in documents:
            text = doc.get("text", str(doc))
            citations = set()

            for pattern in citation_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        # Handle patterns with multiple groups
                        for m in match:
                            if m.strip():
                                citations.add(m.strip())
                    else:
                        citations.add(match)

            doc_citations.append(citations)

        # Create adjacency matrix based on shared citations
        for i in range(n_docs):
            for j in range(n_docs):
                if i != j:
                    # Check if documents share any citations
                    shared_citations = doc_citations[i].intersection(doc_citations[j])
                    if shared_citations:
                        # Higher weight for more shared citations
                        adj_matrix[i][j] = min(len(shared_citations), 3)  # Cap at 3 for stability

        return adj_matrix, list(range(n_docs))

    def forward(self, doc_embeddings: torch.Tensor, adj_matrix: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the GNN to update document representations.

        Args:
            doc_embeddings: Document embeddings (num_docs x embedding_dim)
            adj_matrix: Adjacency matrix (num_docs x num_docs)

        Returns:
            Updated document embeddings (num_docs x output_dim)
        """
        # Add self loops to adjacency matrix
        adj_matrix = adj_matrix + torch.eye(
            adj_matrix.size(0), dtype=adj_matrix.dtype, device=adj_matrix.device
        )

        # Normalize adjacency matrix using symmetric normalization (GCN-style)
        rowsum = adj_matrix.sum(dim=1)
        d_inv_sqrt = torch.diag(torch.pow(rowsum, -0.5))
        adj_norm = torch.mm(torch.mm(d_inv_sqrt, adj_matrix), d_inv_sqrt)

        # Apply first GNN layer
        h = self.activation(self.gnn_layer1(doc_embeddings))

        # Apply graph convolution
        h = torch.mm(adj_norm, h)

        # Apply second GNN layer
        h = self.gnn_layer2(h)

        # Apply final graph convolution to get updated embeddings
        output_embeddings = torch.mm(adj_norm, h)

        return output_embeddings

    def process_documents(self, documents: List[Dict], embeddings: np.ndarray) -> np.ndarray:
        """
        Process documents using the citation graph to get updated embeddings.

        Args:
            documents: List of documents
            embeddings: Original document embeddings

        Returns:
            Updated document embeddings
        """
        if len(documents) <= 1:
            return embeddings

        # Convert embeddings to tensor
        embeddings_tensor = torch.tensor(embeddings, dtype=torch.float32)

        # Create citation graph
        adj_matrix, _ = self.create_citation_graph(documents)

        # Apply GNN to update embeddings
        updated_embeddings = self.forward(embeddings_tensor, adj_matrix)

        return updated_embeddings.detach().numpy()


# Example usage and testing function
def test_document_citation_graph():
    # Create sample legal documents
    documents = [
        {
            "id": 0,
            "title": "Document 1",
            "text": "This is a legal document discussing article 123 and judgment number 456. It references ruling 789.",
        },
        {
            "id": 1,
            "title": "Document 2",
            "text": "Another document that discusses article 123 in detail and mentions judgment 456.",
        },
        {
            "id": 2,
            "title": "Document 3",
            "text": "A third document that talks about different topics, mentioning ruling 999.",
        },
    ]

    # Create dummy embeddings
    embeddings = np.random.rand(len(documents), 384).astype(np.float32)

    # Initialize the document citation graph
    dc_graph = DocumentCitationGraph(input_dim=384, output_dim=384)

    # Process documents to get updated embeddings
    updated_embeddings = dc_graph.process_documents(documents, embeddings)

    print(f"Original embeddings shape: {embeddings.shape}")
    print(f"Updated embeddings shape: {updated_embeddings.shape}")
    print(f"Embeddings are different: {not np.allclose(embeddings, updated_embeddings)}")

    return updated_embeddings, documents


if __name__ == "__main__":
    test_document_citation_graph()

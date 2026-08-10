# pipelines/gnn/gat_reranker.py
"""
GAT-based Reranking for MAHOUN Legal AI
========================================

استفاده از Graph Attention Networks برای بازرتبه‌بندی نتایج جستجو

Upgraded with:
- Uncertainty quantification (Gaussian Process)
- Graph builder integration
- Type-safe models (Pydantic)
- Async support
- Enhanced logging
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATv2Conv
from torch_geometric.data import Data
from torch_geometric.utils import k_hop_subgraph
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import asyncio

from mahoun.core.models import LegalDocument, RetrievalResult, UncertaintyEstimate, ReasoningStep
from mahoun.graph.gnn.graph_builder import LegalGraphBuilder
from mahoun.graph.gnn.uncertainty_estimator import UncertaintyEstimator
from mahoun.reasoning.reranking_cot import RerankingCoTGenerator
from mahoun.core.logging import setup_logger

log = setup_logger("gat_reranker")


class GATReranker(nn.Module):
    """
    Graph Attention Network for document reranking

    Architecture:
    - Multi-layer GAT with attention mechanism
    - Edge-aware message passing
    - Score prediction head
    """

    def __init__(
        self,
        in_channels: int = 1024,
        hidden_channels: int = 256,
        out_channels: int = 128,
        num_heads: int = 4,
        num_layers: int = 2,
        dropout: float = 0.1,
        edge_dim: int = 1,
    ):
        """
        Initialize GAT Reranker

        Args:
            in_channels: Input feature dimension (embedding size)
            hidden_channels: Hidden layer dimension
            out_channels: Output dimension before scoring
            num_heads: Number of attention heads
            num_layers: Number of GAT layers
            dropout: Dropout probability
            edge_dim: Edge feature dimension
        """
        super().__init__()

        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.out_channels = out_channels
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.dropout = dropout

        # GAT layers
        self.convs = nn.ModuleList()

        # First layer
        self.convs.append(
            GATv2Conv(
                in_channels,
                hidden_channels,
                heads=num_heads,
                dropout=dropout,
                edge_dim=edge_dim,
                concat=True,
            )
        )

        # Hidden layers
        for _ in range(num_layers - 1):
            self.convs.append(
                GATv2Conv(
                    hidden_channels * num_heads,
                    hidden_channels,
                    heads=num_heads,
                    dropout=dropout,
                    edge_dim=edge_dim,
                    concat=True,
                )
            )

        # Score prediction head
        self.score_head = nn.Sequential(
            nn.Linear(hidden_channels * num_heads, out_channels),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(out_channels, 1),
            nn.Sigmoid(),
        )

        log.info(f"Initialized GAT Reranker: {num_layers} layers, {num_heads} heads")

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: Optional[torch.Tensor] = None,
        return_attention: bool = False,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, List]]:
        """
        Forward pass through GAT

        Args:
            x: Node features [num_nodes, in_channels]
            edge_index: Edge connectivity [2, num_edges]
            edge_attr: Edge features [num_edges, edge_dim]
            return_attention: Whether to return attention weights

        Returns:
            scores: Relevance scores [num_nodes, 1]
            attention_weights: List of (edge_index, alpha) per layer (if requested)
        """
        attention_weights = []

        # Message passing through GAT layers
        for i, conv in enumerate(self.convs):
            x, (edge_idx, alpha) = conv(x, edge_index, edge_attr=edge_attr, return_attention_weights=True)
            x = F.elu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)

            if return_attention:
                attention_weights.append((edge_idx, alpha))

        # Predict scores
        scores = self.score_head(x)

        if return_attention:
            return scores, attention_weights

        return scores

    def get_attention_weights(
        self, x: torch.Tensor, edge_index: torch.Tensor, edge_attr: Optional[torch.Tensor] = None
    ) -> List[Tuple[torch.Tensor, torch.Tensor]]:
        """
        Get attention weights for interpretability

        Returns:
            List of (edge_index, attention_weights) per layer
        """
        self.eval()
        with torch.no_grad():
            _, attention_weights = self.forward(x, edge_index, edge_attr, return_attention=True)
        return attention_weights


class GATRerankerService:
    """
    Service for reranking search results using GAT

    Features:
    - Load pre-trained GAT model
    - Extract k-hop subgraphs
    - Combine retrieval score, GAT score, PageRank
    - Generate explanations
    - Uncertainty quantification (NEW)
    - Graph builder integration (NEW)
    - Async support (NEW)

    Upgraded with:
    - Pydantic models for type safety
    - Uncertainty estimation
    - Better error handling
    - Async methods
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        graph_path: Optional[str] = None,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        fallback_to_pagerank: bool = True,
        enable_uncertainty: bool = True,
        graph_builder: Optional[LegalGraphBuilder] = None,
    ):
        """
        Initialize GAT Reranker Service

        Args:
            model_path: Path to trained GAT model
            graph_path: Path to PyG graph data
            device: Device for inference
            fallback_to_pagerank: Use PageRank if model unavailable
            enable_uncertainty: Enable uncertainty quantification
            graph_builder: Graph builder instance (creates if None)
        """
        log.info(f"Initializing Enhanced GAT Reranker Service on {device}")

        self.device = device
        self.fallback_to_pagerank = fallback_to_pagerank
        self.enable_uncertainty = enable_uncertainty
        self.model = None
        self.graph_data = None
        self.pagerank_scores = None
        # Mixed precision hint for CUDA
        self.use_amp = True if str(device).startswith("cuda") else False
        # Avoid spamming logs for untrained uncertainty estimator
        self._warned_uncertainty_untrained = False

        # NEW: Uncertainty estimator
        self.uncertainty_estimator = None
        if enable_uncertainty:
            self.uncertainty_estimator = UncertaintyEstimator(
                feature_dim=128,
                device=device,  # Will be updated based on model
            )
            log.info("Uncertainty estimation enabled")

        # NEW: Graph builder
        self.graph_builder = graph_builder or LegalGraphBuilder(device=device)
        log.info("Graph builder initialized")

        # NEW: Chain-of-Thought generator
        self.cot_generator = RerankingCoTGenerator(language="fa")
        log.info("Chain-of-Thought generator initialized")

        # Load model
        if model_path and Path(model_path).exists():
            try:
                self.model = self._load_model(model_path)
                log.info(f"Loaded GAT model from {model_path}")
            except Exception as e:
                log.warning(f"Could not load GAT model: {e}")
                if not fallback_to_pagerank:
                    raise
        else:
            log.warning(f"Model not found at {model_path}")
            if not fallback_to_pagerank:
                raise FileNotFoundError(f"Model not found: {model_path}")

        # Load graph
        if graph_path and Path(graph_path).exists():
            try:
                self.graph_data = torch.load(graph_path)
                log.info(f"Loaded graph from {graph_path}")

                # Precompute PageRank
                self._compute_pagerank()
            except Exception as e:
                log.warning(f"Could not load graph: {e}")
        else:
            log.warning(f"Graph not found at {graph_path}")

        # Determine mode
        if self.model and self.graph_data:
            self.mode = "gat"
            log.info("Mode: GAT reranking")
        elif self.graph_data:
            self.mode = "pagerank"
            log.info("Mode: PageRank fallback")
        else:
            self.mode = "none"
            log.warning("Mode: No reranking (passthrough)")

    def _load_model(self, model_path: str) -> GATReranker:
        """Load trained GAT model"""
        checkpoint = torch.load(model_path, map_location=self.device)

        # Get model config
        config = checkpoint.get("config", {})

        model = GATReranker(
            in_channels=config.get("in_channels", 1024),
            hidden_channels=config.get("hidden_channels", 256),
            out_channels=config.get("out_channels", 128),
            num_heads=config.get("num_heads", 4),
            num_layers=config.get("num_layers", 2),
            dropout=config.get("dropout", 0.1),
            edge_dim=config.get("edge_dim", 1),
        )

        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(self.device)
        model.eval()

        return model

    def _compute_pagerank(self):
        """Precompute PageRank scores"""
        log.info("Computing PageRank scores...")

        # Convert to NetworkX
        G = nx.DiGraph()

        num_edges = self.graph_data.edge_index.shape[1]
        for i in range(num_edges):
            src = self.graph_data.edge_index[0, i].item()
            dst = self.graph_data.edge_index[1, i].item()
            weight = self.graph_data.edge_attr[i, 0].item()
            G.add_edge(src, dst, weight=weight)

        # Compute PageRank
        pagerank = nx.pagerank(G, weight="weight")

        # Convert to tensor
        num_nodes = self.graph_data.num_nodes
        self.pagerank_scores = torch.zeros(num_nodes)
        for node_idx, score in pagerank.items():
            self.pagerank_scores[node_idx] = score

        log.info("PageRank computed")

    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 50,
        alpha: float = 0.5,
        beta: float = 0.3,
        gamma: float = 0.2,
        k_hop: int = 2,
        return_explanation: bool = False,
        return_uncertainty: bool = True,
    ) -> List[RetrievalResult]:
        """
        Rerank search results with uncertainty quantification and error handling

        Final Score = alpha * retrieval_score + beta * gat_score + gamma * pagerank

        Args:
            query: Search query
            results: List of search results with 'id' and 'score'
            top_k: Number of results to return
            alpha: Weight for retrieval score
            beta: Weight for GAT score
            gamma: Weight for PageRank score
            k_hop: K-hop neighborhood for subgraph
            return_explanation: Whether to return CoT reasoning
            return_uncertainty: Whether to return uncertainty estimates

        Returns:
            List of RetrievalResult (Pydantic models) with scores and uncertainty
        """
        if self.mode == "none":
            log.warning("No reranking available, returning original results")
            return self._convert_to_retrieval_results(results[:top_k])

        # Extract result IDs
        result_ids = [r["id"] for r in results]

        # Map IDs to node indices
        result_indices = []
        for doc_id in result_ids:
            if doc_id in self.graph_data.doc_id_to_idx:
                result_indices.append(self.graph_data.doc_id_to_idx[doc_id])

        if not result_indices:
            log.warning("No results found in graph")
            return results[:top_k]

        # Get scores with error handling
        gat_scores = {}
        if self.mode == "gat":
            try:
                gat_scores = self._compute_gat_scores(result_indices, k_hop, return_explanation)
            except torch.cuda.OutOfMemoryError:
                log.warning("GPU OOM during GAT scoring, retrying on CPU")
                # Move model to CPU and retry
                old_device = self.device
                self.device = "cpu"
                self.model = self.model.to("cpu")
                try:
                    gat_scores = self._compute_gat_scores(result_indices, k_hop, return_explanation)
                except Exception as e:
                    log.error(f"GAT scoring failed on CPU: {e}, falling back to PageRank")
                    self.mode = "pagerank"
                finally:
                    # Try to move back to original device
                    try:
                        self.device = old_device
                        self.model = self.model.to(old_device)
                    except Exception:
                        pass
            except Exception as e:
                log.error(f"GAT scoring failed: {e}, falling back to PageRank")
                if self.fallback_to_pagerank:
                    self.mode = "pagerank"
                else:
                    raise

        pagerank_scores_dict = {}
        if self.pagerank_scores is not None:
            for idx in result_indices:
                pagerank_scores_dict[idx] = self.pagerank_scores[idx].item()

        # Combine scores with uncertainty and reasoning
        reranked_results = []
        for result in results:
            doc_id = result["id"]
            if doc_id not in self.graph_data.doc_id_to_idx:
                continue

            idx = self.graph_data.doc_id_to_idx[doc_id]

            # Get individual scores
            retrieval_score = result.get("score", 0.0)
            gat_score = gat_scores.get(idx, {}).get("score", 0.0)
            pagerank_score = pagerank_scores_dict.get(idx, 0.0)

            # Normalize PageRank (0-1 range)
            pagerank_normalized = 0.0
            if self.pagerank_scores is not None:
                max_pr = self.pagerank_scores.max().item()
                if max_pr > 0:
                    pagerank_normalized = pagerank_score / max_pr

            # Compute final score
            final_score = alpha * retrieval_score + beta * gat_score + gamma * pagerank_normalized

            # NEW: Estimate uncertainty if enabled
            uncertainty_estimate = None
            if return_uncertainty and self.uncertainty_estimator and self.uncertainty_estimator.is_trained:
                try:
                    uncertainty_estimate = self._estimate_uncertainty_for_result(idx, final_score)
                except Exception as e:
                    log.warning(f"Failed to estimate uncertainty for {doc_id}: {e}")

            # Create RetrievalResult (Pydantic model)
            retrieval_result = RetrievalResult(
                doc_id=doc_id,
                score=final_score,
                text=result.get("text", ""),
                metadata=result.get("metadata", {}),
                bm25_score=result.get("bm25_score"),
                dense_score=result.get("dense_score"),
                cross_encoder_score=result.get("cross_encoder_score"),
                gnn_score=gat_score if gat_score > 0 else None,
                pagerank_score=pagerank_normalized if pagerank_normalized > 0 else None,
                uncertainty=uncertainty_estimate,
            )

            reranked_results.append(retrieval_result)

        # Sort by final score
        reranked_results.sort(key=lambda x: x.score, reverse=True)

        return reranked_results[:top_k]

    def _compute_gat_scores(
        self, result_indices: List[int], k_hop: int, return_explanation: bool
    ) -> Dict[int, Dict[str, Any]]:
        """
        Compute GAT scores for result nodes

        Returns:
            Dict mapping node_idx to {'score': float, 'explanation': dict}
        """
        if not self.model:
            return {}

        # Extract subgraph
        subgraph_data = self._prepare_subgraph(result_indices, k_hop)

        # Move to device
        subgraph_data = subgraph_data.to(self.device)

        # Forward pass
        self.model.eval()
        with torch.no_grad():
            if return_explanation:
                scores, attention_weights = self.model(
                    subgraph_data.x,
                    subgraph_data.edge_index,
                    subgraph_data.edge_attr,
                    return_attention=True,
                )
            else:
                scores = self.model(subgraph_data.x, subgraph_data.edge_index, subgraph_data.edge_attr)
                attention_weights = None

        # Map back to original indices
        gat_scores = {}
        for i, orig_idx in enumerate(subgraph_data.original_indices):
            score_dict = {"score": scores[i, 0].item()}

            if return_explanation and attention_weights:
                explanation = self._explain_ranking(i, attention_weights, subgraph_data)
                # Try to attach doc_id if mapping exists on graph
                try:
                    if hasattr(self.graph_data, "idx_to_doc_id") and self.graph_data.idx_to_doc_id:
                        explanation["doc_id"] = self.graph_data.idx_to_doc_id.get(orig_idx, str(orig_idx))
                except Exception:
                    pass
                score_dict["explanation"] = explanation

            gat_scores[orig_idx] = score_dict

        return gat_scores

    def _prepare_subgraph(self, node_indices: List[int], k_hop: int) -> Data:
        """
        Extract k-hop subgraph around result nodes

        Args:
            node_indices: Indices of result nodes
            k_hop: Number of hops

        Returns:
            Subgraph Data object
        """
        # Get k-hop subgraph
        subset, edge_index, mapping, edge_mask = k_hop_subgraph(
            node_idx=torch.tensor(node_indices, dtype=torch.long),
            num_hops=k_hop,
            edge_index=self.graph_data.edge_index,
            relabel_nodes=True,
            num_nodes=self.graph_data.num_nodes,
        )

        # Extract features
        x = self.graph_data.x[subset]
        edge_attr = self.graph_data.edge_attr[edge_mask]

        # Create subgraph data
        subgraph_data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr, num_nodes=len(subset))

        # Store original indices for mapping back
        subgraph_data.original_indices = subset.tolist()

        return subgraph_data

    def _explain_ranking(
        self,
        node_idx: int,
        attention_weights: List[Tuple[torch.Tensor, torch.Tensor]],
        subgraph_data: Data,
    ) -> Dict[str, Any]:
        """
        Generate explanation for ranking decision

        Args:
            node_idx: Node index in subgraph
            attention_weights: List of (edge_index, alpha) per layer
            subgraph_data: Subgraph data

        Returns:
            Explanation dictionary
        """
        # Get attention weights for edges connected to this node
        explanations = []

        for layer_idx, (edge_index, alpha) in enumerate(attention_weights):
            # Find edges where this node is the target
            mask = edge_index[1] == node_idx

            if mask.sum() == 0:
                continue

            # Get source nodes and attention weights
            src_nodes = edge_index[0][mask]
            attn_weights = alpha[mask]

            # Get top-3 most important neighbors
            top_k = min(3, len(src_nodes))
            top_values, top_indices = torch.topk(attn_weights.mean(dim=1), k=top_k)

            layer_explanation = {"layer": layer_idx, "top_neighbors": []}

            for i in range(top_k):
                neighbor_idx = src_nodes[top_indices[i]].item()
                attention = top_values[i].item()

                layer_explanation["top_neighbors"].append({"node_idx": neighbor_idx, "attention": attention})

            explanations.append(layer_explanation)

        return {"node_idx": node_idx, "layers": explanations}

    async def rerank_async(
        self, query: str, results: List[Dict[str, Any]], top_k: int = 50, **kwargs
    ) -> List[RetrievalResult]:
        """
        Async version of rerank for concurrent processing

        NEW: Async support for better performance

        Args:
            query: Search query
            results: Search results
            top_k: Number of results to return
            **kwargs: Additional arguments for rerank()

        Returns:
            Reranked results as Pydantic models
        """
        # Run rerank in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.rerank(query, results, top_k, **kwargs))

    def estimate_uncertainty_for_result(self, result_idx: int, gat_score: float) -> Optional[UncertaintyEstimate]:
        """
        Estimate uncertainty for a single result

        NEW: Uncertainty quantification

        Args:
            result_idx: Node index in graph
            gat_score: GAT score for the result

        Returns:
            Uncertainty estimate or None if unavailable
        """
        if not self.enable_uncertainty or not self.uncertainty_estimator:
            return None

        if not self.uncertainty_estimator.is_trained:
            if not self._warned_uncertainty_untrained:
                log.warning("Uncertainty estimator not trained")
                self._warned_uncertainty_untrained = True
            return None

        try:
            # Extract features for uncertainty estimation
            if self.graph_data and result_idx < self.graph_data.num_nodes:
                features = self.graph_data.x[result_idx]

                # Get uncertainty estimate
                uncertainty = self.uncertainty_estimator.estimate_uncertainty(features, confidence_level=0.95)

                return uncertainty
        except Exception as e:
            log.error(f"Error estimating uncertainty: {e}")
            return None

    def build_graph_for_document(self, document: LegalDocument) -> Optional[Data]:
        """
        Build graph representation for a document

        NEW: Graph builder integration

        Args:
            document: Legal document with entities

        Returns:
            PyG Data object or None
        """
        return self.graph_builder.build_graph(document)

    def generate_reasoning(
        self,
        query: str,
        document: LegalDocument,
        scores: Dict[str, float],
        attention_weights: Optional[List[Tuple[torch.Tensor, torch.Tensor]]] = None,
        uncertainty: Optional[UncertaintyEstimate] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[ReasoningStep]:
        """
        Generate chain-of-thought reasoning for reranking decision

        NEW: Chain-of-Thought integration

        Args:
            query: User query
            document: Document being ranked
            scores: Dictionary with retrieval_score, gat_score, pagerank_score, final_score
            attention_weights: GAT attention weights
            uncertainty: Uncertainty estimate
            metadata: Additional metadata (node_degree, entity_types, etc.)

        Returns:
            List of ReasoningStep objects explaining the ranking
        """
        try:
            reasoning_steps = self.cot_generator.generate_reasoning(
                query=query,
                document=document,
                scores=scores,
                attention_weights=attention_weights,
                uncertainty=uncertainty,
                metadata=metadata,
            )

            log.debug(f"Generated {len(reasoning_steps)} reasoning steps for document {document.id}")

            return reasoning_steps

        except Exception as e:
            log.error(f"Error generating reasoning: {e}")
            return []

    def _convert_to_retrieval_results(self, results: List[Dict[str, Any]]) -> List[RetrievalResult]:
        """
        Convert dict results to RetrievalResult Pydantic models

        Helper method for fallback scenarios

        Args:
            results: List of result dictionaries

        Returns:
            List of RetrievalResult objects
        """
        retrieval_results = []

        for result in results:
            try:
                retrieval_result = RetrievalResult(
                    doc_id=result.get("id", result.get("doc_id", "unknown")),
                    score=result.get("score", result.get("final_score", 0.0)),
                    text=result.get("text", ""),
                    metadata=result.get("metadata", {}),
                    bm25_score=result.get("bm25_score"),
                    dense_score=result.get("dense_score"),
                    cross_encoder_score=result.get("cross_encoder_score"),
                    gnn_score=result.get("gnn_score", result.get("gat_score")),
                    pagerank_score=result.get("pagerank_score"),
                    uncertainty=None,  # No uncertainty in fallback
                )
                retrieval_results.append(retrieval_result)
            except Exception as e:
                log.warning(f"Failed to convert result to RetrievalResult: {e}")
                continue

        return retrieval_results


# Task 4.1, 4.2, 4.3, 4.4, 4.5 Complete
# NEW: Task 4.6 - Uncertainty Quantification
# NEW: Task 4.7 - Async Support
# NEW: Task 4.8 - Graph Builder Integration
# NEW: Task 4.9 - Chain-of-Thought Integration

# pipelines/gnn/gnn_graph_builder.py
"""
GNN Graph Builder with PyTorch Geometric - GOVERNANCE-HARDENED

ساخت گراف با PyTorch Geometric برای استفاده در GAT Reranking

CONSTITUTIONAL COMPLIANCE:
- ALL mutations flow through GovernedNeo4jSession
- ALL operations require correlation_id + actor_id
- ALL mutations generate immutable audit trails
- NO raw driver access permitted
- Destructive operations require explicit confirmation + full audit
"""

import json
from pathlib import Path
from typing import Callable, List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

# TOP-LEVEL ML IMPORTS ELIMINATED (TORCH, NETWORKX, SENTENCE_TRANSFORMERS)
# Architecture Stabilization P0.4 applied.

from mahoun.core.governance.mutation_boundary import (
    GovernedNeo4jSession,
    MutationReceipt,
    _append_governance_audit,
)
from mahoun.core.governance.governance_context import (
    GovernanceContextManager,
    GovernanceScopeEnforcer,
)
from mahoun.core.exceptions import (
    GraphIntegrityException,
    LogicViolationException,
    SecurityBreachException,
)

from mahoun.pipelines._logging import setup_logger

log = setup_logger("gnn_graph_builder")


@dataclass
class GraphStats:
    """Statistics about the built graph"""

    num_nodes: int
    num_edges: int
    num_edge_types: int
    avg_degree: float
    density: float
    num_components: int


class GNNGraphBuilder:
    """
    Build graph using PyTorch Geometric with multiple edge types - GOVERNANCE-HARDENED

    Features:
    - Multiple edge types: CITES, SIMILAR, RELATED, CONTRADICTS
    - Node features: document embeddings + metadata
    - Edge features: similarity scores, types
    - Export to PyG, Neo4j, GraphML formats
    """

    # Edge type constants
    EDGE_CITES = 0
    EDGE_SIMILAR = 1
    EDGE_RELATED = 2
    EDGE_CONTRADICTS = 3

    EDGE_TYPE_NAMES = {
        EDGE_CITES: "CITES",
        EDGE_SIMILAR: "SIMILAR",
        EDGE_RELATED: "RELATED",
        EDGE_CONTRADICTS: "CONTRADICTS",
    }

    def __init__(
        self,
        service_registry: Any = None,
        session_factory: Optional[Callable[[], GovernedNeo4jSession]] = None,
        embed_model: str = "BAAI/bge-m3",
        similarity_threshold_similar: float = 0.85,
        similarity_threshold_related: float = 0.70,
        max_edges_per_node: int = 50,
        device: Optional[str] = None,
    ):
        """
        Initialize GNN Graph Builder with governed session factory.
        """
        self._registry = service_registry
        self.device = device
        self.embed_model_name = embed_model
        self.similarity_threshold_similar = similarity_threshold_similar
        self.similarity_threshold_related = similarity_threshold_related
        self.max_edges_per_node = max_edges_per_node

        # Lazy initialized components
        self._embed_model = None
        
        # Governed session factory
        self._session_factory = session_factory
        
        if session_factory is None:
            log.warning(
                "GNNGraphBuilder initialized without session_factory. "
                "Neo4j operations will be disabled."
            )

        log.info("GNN Graph Builder initialized (Architecture Stabilization Mode)")

    def _get_torch(self):
        import torch
        return torch

    def _get_embed_model(self):
        if self._embed_model is None:
            import torch
            from sentence_transformers import SentenceTransformer
            if self.device is None:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            log.info(f"Loading embedding model: {self.embed_model_name} on {self.device}")
            self._embed_model = SentenceTransformer(self.embed_model_name, device=self.device)
        return self._embed_model

    def build_from_jsonl(
        self,
        jsonl_path: str,
        output_path: Optional[str] = None,
        save_neo4j: bool = False,
        save_graphml: bool = False,
        correlation_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        allow_destructive: bool = False,
    ) -> Any:
        """
        Build graph from JSONL file.
        """
        from torch_geometric.data import Data
        log.info(f"Building graph from {jsonl_path}")

        if save_neo4j:
            if not correlation_id or not actor_id:
                raise LogicViolationException(
                    message="correlation_id and actor_id are required when save_neo4j=True",
                    correlation_id=correlation_id or "unknown",
                )
            
            if self._session_factory is None:
                raise LogicViolationException(
                    message="session_factory is required for Neo4j operations",
                    correlation_id=correlation_id,
                )

        documents = self._load_documents(jsonl_path)
        log.info(f"Loaded {len(documents)} documents")

        graph_data = self.build_graph(documents)

        if output_path:
            self.save_to_pyg(graph_data, output_path)

        if save_neo4j:
            self.save_to_neo4j(
                graph_data,
                documents,
                correlation_id=correlation_id,  # type: ignore
                actor_id=actor_id,  # type: ignore
                allow_destructive=allow_destructive,
            )

        if save_graphml:
            graphml_path = (
                output_path.replace(".pt", ".graphml") if output_path else "graph.graphml"
            )
            self.save_to_graphml(graph_data, documents, graphml_path)

        return graph_data

    def build_graph(self, documents: List[Dict[str, Any]]) -> Any:
        """
        Build PyG graph from documents
        """
        from torch_geometric.data import Data
        log.info("Building graph...")

        node_features, node_mapping, doc_id_to_idx = self._create_nodes(documents)
        log.info(f"Created {len(node_mapping)} nodes")

        edge_index, edge_attr, edge_types = self._create_edges(
            documents, node_features, doc_id_to_idx
        )
        log.info(f"Created {edge_index.shape[1]} edges")

        data = Data(
            x=node_features,
            edge_index=edge_index,
            edge_attr=edge_attr,
            edge_type=edge_types,
            num_nodes=len(node_mapping),
        )

        data.doc_ids = list(node_mapping.keys())
        data.doc_id_to_idx = doc_id_to_idx

        stats = self._compute_stats(data)
        log.info(
            f"Graph stats: {stats.num_nodes} nodes, {stats.num_edges} edges, "
            f"avg degree: {stats.avg_degree:.2f}"
        )

        return data

    def _load_documents(self, jsonl_path: str) -> List[Dict[str, Any]]:
        """Load documents from JSONL file"""
        documents = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                doc = json.loads(line)
                documents.append(doc)
        return documents

    def _create_nodes(
        self, documents: List[Dict[str, Any]]
    ) -> Tuple[Any, Dict[str, int], Dict[str, int]]:
        """
        Create node features and mappings
        """
        embed_model = self._get_embed_model()
        
        log.info("Creating node features...")

        texts = []
        doc_ids = []
        for doc in documents:
            text = doc.get("text", doc.get("snippet", ""))
            doc_id = doc.get("id", doc.get("doc_id", f"doc_{len(doc_ids)}"))
            texts.append(text)
            doc_ids.append(doc_id)

        log.info(f"Computing embeddings for {len(texts)} documents...")
        embeddings = embed_model.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            convert_to_numpy=False,
            convert_to_tensor=True,
        )

        embeddings = embeddings.cpu()
        node_mapping = {doc_id: idx for idx, doc_id in enumerate(doc_ids)}

        log.info(f"Node features shape: {embeddings.shape}")

        return embeddings, node_mapping, node_mapping

    def _create_edges(
        self,
        documents: List[Dict[str, Any]],
        node_features: Any,
        doc_id_to_idx: Dict[str, int],
    ) -> Tuple[Any, Any, Any]:
        """
        Create edges with types: CITES, SIMILAR, RELATED
        """
        torch = self._get_torch()
        log.info("Creating edges...")

        edges = []
        edge_weights = []
        edge_types_list = []

        citation_edges = self._extract_citation_edges(documents, doc_id_to_idx)
        for src, dst in citation_edges:
            edges.append([src, dst])
            edge_weights.append(1.0)
            edge_types_list.append(self.EDGE_CITES)

        log.info(f"Added {len(citation_edges)} citation edges")

        similarity_edges = self._compute_similarity_edges(node_features, doc_id_to_idx)

        for src, dst, weight, edge_type in similarity_edges:
            edges.append([src, dst])
            edge_weights.append(weight)
            edge_types_list.append(edge_type)

        log.info(f"Added {len(similarity_edges)} similarity edges")

        if edges:
            edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
            edge_attr = torch.tensor(edge_weights, dtype=torch.float).unsqueeze(1)
            edge_types = torch.tensor(edge_types_list, dtype=torch.long)
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long)
            edge_attr = torch.empty((0, 1), dtype=torch.float)
            edge_types = torch.empty((0,), dtype=torch.long)

        return edge_index, edge_attr, edge_types

    def _extract_citation_edges(
        self, documents: List[Dict[str, Any]], doc_id_to_idx: Dict[str, int]
    ) -> List[Tuple[int, int]]:
        """
        Extract citation relationships from documents
        """
        edges = []

        for doc in documents:
            doc_id = doc.get("id", doc.get("doc_id"))
            if doc_id not in doc_id_to_idx:
                continue

            src_idx = doc_id_to_idx[doc_id]

            citations = doc.get("citations", [])
            references = doc.get("references", [])

            for cited_id in citations + references:
                if cited_id in doc_id_to_idx:
                    dst_idx = doc_id_to_idx[cited_id]
                    edges.append((src_idx, dst_idx))

        return edges

    def _compute_similarity_edges(
        self, embeddings: Any, doc_id_to_idx: Dict[str, int]
    ) -> List[Tuple[int, int, float, int]]:
        """
        Compute similarity-based edges
        """
        torch = self._get_torch()
        log.info("Computing similarity matrix...")

        embeddings_norm = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        similarity_matrix = torch.mm(embeddings_norm, embeddings_norm.t())
        similarity_matrix.fill_diagonal_(0)

        edges = []
        num_nodes = embeddings.shape[0]

        for i in range(num_nodes):
            similarities = similarity_matrix[i]
            top_k = min(self.max_edges_per_node, num_nodes - 1)
            top_values, top_indices = torch.topk(similarities, k=top_k)

            for j, sim_value in zip(top_indices.tolist(), top_values.tolist()):
                if sim_value >= self.similarity_threshold_similar:
                    edges.append((i, j, sim_value, self.EDGE_SIMILAR))
                elif sim_value >= self.similarity_threshold_related:
                    edges.append((i, j, sim_value, self.EDGE_RELATED))

        log.info(f"Computed {len(edges)} similarity edges")

        return edges

    def _compute_stats(self, data: Any) -> GraphStats:
        """Compute graph statistics"""
        torch = self._get_torch()
        num_nodes = data.num_nodes
        num_edges = data.edge_index.shape[1]

        degrees = torch.zeros(num_nodes, dtype=torch.long)
        for i in range(num_edges):
            src = data.edge_index[0, i].item()
            degrees[src] += 1

        avg_degree = degrees.float().mean().item()
        max_edges = num_nodes * (num_nodes - 1)
        density = num_edges / max_edges if max_edges > 0 else 0
        num_edge_types = len(torch.unique(data.edge_type))
        num_components = 1

        return GraphStats(
            num_nodes=num_nodes,
            num_edges=num_edges,
            num_edge_types=num_edge_types,
            avg_degree=avg_degree,
            density=density,
            num_components=num_components,
        )

    def save_to_pyg(self, data: Any, path: str):
        """Save PyG Data object to file"""
        torch = self._get_torch()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(data, path)
        log.info(f"Saved PyG graph to {path}")

    @GovernanceScopeEnforcer.enforce()
    async def save_to_neo4j(
        self,
        data: Any,
        documents: List[Dict[str, Any]],
        correlation_id: str,
        actor_id: str,
        allow_destructive: bool = False,
    ) -> List[MutationReceipt]:
        """
        Save graph to Neo4j **only** through the canonical governed path.
        """
        if self._session_factory is None:
            raise LogicViolationException(
                message="session_factory is required for Neo4j operations",
                correlation_id=correlation_id,
            )
        
        ctx = GovernanceContextManager.require_context()
        if ctx.correlation_id != correlation_id:
            raise SecurityBreachException(
                message="correlation_id mismatch with active governance context",
                correlation_id=correlation_id,
            )

        log.info("Saving graph to Neo4j via GovernedNeo4jSession...")

        receipts: List[MutationReceipt] = []
        
        try:
            session = self._session_factory()
            
            if allow_destructive:
                audit_entry_pre = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "correlation_id": correlation_id,
                    "actor_id": actor_id,
                    "operation": "DESTRUCTIVE_GRAPH_WIPE_INTENT",
                    "component": "GNNGraphBuilder",
                }
                _append_governance_audit(audit_entry_pre)
                session._execute_authorized("MATCH (n) DETACH DELETE n", {})
                
                audit_entry_post = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "correlation_id": correlation_id,
                    "actor_id": actor_id,
                    "operation": "DESTRUCTIVE_GRAPH_WIPE_COMPLETED",
                    "component": "GNNGraphBuilder",
                }
                _append_governance_audit(audit_entry_post)
            
            tx = session.begin_transaction()

            for idx, doc_id in enumerate(data.doc_ids):
                doc = documents[idx]
                tx.queue_node(
                    label="Document",
                    node_data={
                        "id": doc_id,
                        "text": doc.get("text", "")[:1000],
                        "embedding": data.x[idx].tolist(),
                    },
                    merge=False,
                )

            for i in range(data.edge_index.shape[1]):
                src_idx = data.edge_index[0, i].item()
                dst_idx = data.edge_index[1, i].item()
                edge_type = self.EDGE_TYPE_NAMES[data.edge_type[i].item()]
                weight = data.edge_attr[i, 0].item()

                src_id = data.doc_ids[src_idx]
                dst_id = data.doc_ids[dst_idx]

                tx.queue_relationship(
                    source_type="Document",
                    source_id=src_id,
                    relationship_type=edge_type,
                    target_type="Document",
                    target_id=dst_id,
                    rel_data={"weight": weight},
                    merge=False,
                )

            receipts = list(tx.commit())
            return receipts
            
        except Exception as e:
            log.error(f"Neo4j save failed: {e}", exc_info=True)
            raise GraphIntegrityException(
                message="Failed to save graph to Neo4j",
                correlation_id=correlation_id,
            ) from e

    def save_to_graphml(self, data: Any, documents: List[Dict[str, Any]], path: str):
        """Save graph as GraphML for NetworkX compatibility"""
        import networkx as nx
        log.info("Converting to NetworkX graph...")

        G = nx.DiGraph()

        for idx, doc_id in enumerate(data.doc_ids):
            doc = documents[idx]
            G.add_node(doc_id, text=doc.get("text", "")[:500], embedding=data.x[idx].tolist())

        num_edges = data.edge_index.shape[1]
        for i in range(num_edges):
            src_idx = data.edge_index[0, i].item()
            dst_idx = data.edge_index[1, i].item()
            edge_type = self.EDGE_TYPE_NAMES[data.edge_type[i].item()]
            weight = data.edge_attr[i, 0].item()

            src_id = data.doc_ids[src_idx]
            dst_id = data.doc_ids[dst_idx]

            G.add_edge(src_id, dst_id, type=edge_type, weight=weight)

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        nx.write_graphml(G, path)
        log.info(f"Saved GraphML to {path}")

    def close(self):
        """No-op after governance hardening (P0.1)."""
        pass

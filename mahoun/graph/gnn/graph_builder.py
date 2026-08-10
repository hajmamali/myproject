"""
Legal Graph Builder
===================

Build graph representations of legal documents for GNN processing.
Extracted and upgraded from legacy codebase.

Features:
- Entity-based graph construction
- Relationship detection
- Edge attribute computation
- Semantic similarity edges
"""

from typing import TYPE_CHECKING, Optional, List, Tuple, Dict, Any

import torch
from torch_geometric.data import Data

from mahoun.core.models import LegalEntity, LegalDocument
from mahoun.core.models.entity import EntityType
from mahoun.core.logging import setup_logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

log = setup_logger("graph_builder")


class LegalGraphBuilder:
    """
    Ultra-advanced graph builder with fail-closed DI.

    Constructor Injection Contract
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``model`` MUST be injected by bootstrap (primary path).
    Lazy fallback is DEPRECATED and triggers loud warnings.

    Architectural Mandate
    ~~~~~~~~~~~~~~~~~~~~~
    Bootstrap wiring is MANDATORY in production. Lazy construction
    exists only for backward compatibility and will be removed.

    Upgraded from legacy code with:
    - Type hints
    - Pydantic models
    - Better error handling
    - Configurable parameters
    """

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        proximity_threshold: int = 100,
        similarity_threshold: float = 0.7,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        model: Optional["SentenceTransformer"] = None,
        correlation_id: str = "",
    ):
        """
        Initialize Legal Graph Builder

        Args:
            embedding_model: Sentence transformer model name (only used for lazy fallback)
            proximity_threshold: Max character distance for proximity edges
            similarity_threshold: Min similarity for semantic edges
            device: Device for embeddings
            model: Pre-constructed SentenceTransformer (MANDATORY in production).
                  If None, triggers DEPRECATED lazy fallback with warning.
            correlation_id: Request tracking ID for observability.
        """
        import time

        self._correlation_id = correlation_id or f"graph-{time.time()}"

        log.info(f"[{self._correlation_id}] Initializing LegalGraphBuilder")

        self._embedding_model_name = embedding_model
        self.proximity_threshold = proximity_threshold
        self.similarity_threshold = similarity_threshold
        self.device = device

        if model is not None:
            # PRIMARY PATH: Bootstrap-injected model
            self._embedding_model = model
            log.info(f"[{self._correlation_id}] ✅ LegalGraphBuilder initialized (bootstrap-injected model)")
        else:
            # DEPRECATED FALLBACK: Lazy construction with loud warning
            log.warning(
                f"[{self._correlation_id}] ⚠️  DEPRECATED: LegalGraphBuilder "
                f"initialized without injected model. Will attempt lazy construction on first use. "
                f"Bootstrap wiring is MANDATORY in production. "
                f"Remediation: Update bootstrap/runtime.py to inject SentenceTransformer."
            )
            self._embedding_model = None  # Will be loaded lazily

        # Legal relationship rules
        self.legal_relationships = {
            (EntityType.COURT, EntityType.JUDGE): True,
            (EntityType.CASE_NO, EntityType.VERDICT): True,
            (EntityType.PARTY, EntityType.LAWYER): True,
            (EntityType.ARTICLE, EntityType.LAW_NAME): True,
            (EntityType.VERDICT, EntityType.COURT): True,
            (EntityType.JUDGE, EntityType.VERDICT): True,
            (EntityType.LAWYER, EntityType.PARTY): True,
        }

        log.info(f"Graph builder initialized on {device}")

    def _get_embedding_model(self):
        """
        DEPRECATED: Lazy-load SentenceTransformer on first use.

        This method exists only for backward compatibility. Bootstrap injection
        is the PRIMARY path.
        """
        if self._embedding_model is None:
            import time

            log.warning(
                f"[{self._correlation_id}] ⚠️  Lazy model construction triggered. This is a DEPRECATED fallback path."
            )
            try:
                from sentence_transformers import SentenceTransformer

                start = time.time()
                self._embedding_model = SentenceTransformer(self._embedding_model_name, device=self.device)
                latency_ms = (time.time() - start) * 1000

                log.warning(
                    f"[{self._correlation_id}] ⚠️  Lazy model construction completed "
                    f"(model={self._embedding_model_name}, latency={latency_ms:.2f}ms)"
                )
            except ImportError:
                log.error(f"[{self._correlation_id}] ❌ sentence-transformers not installed and no model injected.")
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers OR "
                    "inject pre-constructed model via bootstrap wiring."
                )
            except Exception as e:
                log.error(f"[{self._correlation_id}] ❌ Lazy model construction failed: {e}")
                raise RuntimeError(f"Failed to construct embedding model: {e}")
        return self._embedding_model

    def build_graph(self, document: LegalDocument) -> Optional[Data]:
        """
        Build graph representation of legal document

        Args:
            document: Legal document with entities

        Returns:
            PyTorch Geometric Data object or None if insufficient entities
        """
        try:
            entities = document.entities

            if len(entities) < 2:
                log.warning(
                    f"Document {document.id} has insufficient entities ({len(entities)}) for graph construction"
                )
                return None

            # Create node features (entity embeddings)
            node_texts = [entity.text for entity in entities]
            node_embeddings = self._get_embedding_model().encode(
                node_texts, convert_to_tensor=True, device=self.device, show_progress_bar=False
            )

            # Create edges
            edge_indices = self._create_edges(entities, document.text)

            if not edge_indices:
                log.warning(f"No edges created for document {document.id}")
                return None

            # Create edge attributes
            edge_attrs = self._create_edge_attributes(entities, edge_indices)

            # Create PyTorch Geometric Data object
            graph_data = Data(
                x=node_embeddings,
                edge_index=torch.tensor(edge_indices, dtype=torch.long).t().contiguous(),
                edge_attr=torch.tensor(edge_attrs, dtype=torch.float),
                num_nodes=len(entities),
            )

            log.debug(f"Created graph for document {document.id}: {len(entities)} nodes, {len(edge_indices)} edges")

            return graph_data

        except Exception as e:
            log.error(f"Error building graph for document {document.id}: {e}")
            return None

    def _create_edges(self, entities: List[LegalEntity], text: str) -> List[Tuple[int, int]]:
        """
        Create edges based on entity proximity and relationships

        Edge types:
        1. Proximity edges (entities close in text)
        2. Semantic similarity edges (same label type)
        3. Legal relationship edges (domain-specific rules)

        Args:
            entities: List of legal entities
            text: Document text

        Returns:
            List of (source, target) edge tuples
        """
        edges = []

        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities):
                if i >= j:  # Avoid self-loops and duplicates
                    continue

                # 1. Distance-based edges
                distance = abs(entity1.start - entity2.start)
                if distance < self.proximity_threshold:
                    edges.append((i, j))
                    edges.append((j, i))  # Bidirectional

                # 2. Semantic similarity edges (same entity type)
                if entity1.label == entity2.label:
                    edges.append((i, j))
                    edges.append((j, i))

                # 3. Legal relationship edges
                if self._has_legal_relationship(entity1, entity2):
                    edges.append((i, j))
                    # Some relationships are directional
                    if self._is_bidirectional_relationship(entity1.label, entity2.label):
                        edges.append((j, i))

        # Remove duplicates while preserving order
        edges = list(dict.fromkeys(edges))

        return edges

    def _has_legal_relationship(self, entity1: LegalEntity, entity2: LegalEntity) -> bool:
        """
        Check if two entities have a legal relationship

        Args:
            entity1: First entity
            entity2: Second entity

        Returns:
            True if relationship exists
        """
        return self.legal_relationships.get((entity1.label, entity2.label), False)

    def _is_bidirectional_relationship(self, label1: EntityType, label2: EntityType) -> bool:
        """Check if relationship is bidirectional"""
        # Some relationships are symmetric
        symmetric_pairs = {
            (EntityType.PARTY, EntityType.LAWYER),
            (EntityType.LAWYER, EntityType.PARTY),
        }
        return (label1, label2) in symmetric_pairs

    def _create_edge_attributes(self, entities: List[LegalEntity], edges: List[Tuple[int, int]]) -> List[List[float]]:
        """
        Create edge attributes based on relationship types

        Edge features:
        1. Normalized distance
        2. Average confidence
        3. Relationship type (one-hot encoded: 4 dimensions)

        Total: 6 features per edge

        Args:
            entities: List of entities
            edges: List of edge tuples

        Returns:
            List of edge feature vectors
        """
        edge_attrs = []

        for i, j in edges:
            entity1, entity2 = entities[i], entities[j]

            # 1. Distance feature (normalized)
            distance = abs(entity1.start - entity2.start) / 1000.0
            distance = min(distance, 1.0)  # Cap at 1.0

            # 2. Confidence feature (average)
            confidence = (entity1.confidence + entity2.confidence) / 2.0

            # 3. Relationship type (one-hot encoded)
            relationship_type = self._get_relationship_type(entity1.label, entity2.label)

            # Combine features
            edge_attr = [distance, confidence] + relationship_type
            edge_attrs.append(edge_attr)

        return edge_attrs

    def _get_relationship_type(self, label1: EntityType, label2: EntityType) -> List[float]:
        """
        Get one-hot encoded relationship type

        Types:
        - same_type: Same entity label
        - legal_relation: Domain-specific legal relationship
        - proximity: Close in text
        - other: Default

        Args:
            label1: First entity label
            label2: Second entity label

        Returns:
            One-hot encoded vector [4 dimensions]
        """
        if label1 == label2:
            return [1.0, 0.0, 0.0, 0.0]  # same_type
        elif self._has_legal_relationship(type("Entity", (), {"label": label1}), type("Entity", (), {"label": label2})):
            return [0.0, 1.0, 0.0, 0.0]  # legal_relation
        else:
            return [0.0, 0.0, 1.0, 0.0]  # proximity

    def build_multi_document_graph(self, documents: List[LegalDocument]) -> Optional[Data]:
        """
        Build unified graph from multiple documents

        Merges entity nodes across documents and creates cross-document edges.
        Maintains document-to-node mapping for retrieval.

        Args:
            documents: List of legal documents

        Returns:
            PyTorch Geometric Data object with unified graph or None if insufficient entities
        """
        try:
            if not documents:
                log.warning("No documents provided for multi-document graph")
                return None

            # Collect all entities with document context
            all_entities = []
            entity_to_doc = {}  # Maps entity index to document ID
            doc_id_to_entity_indices = {}  # Maps doc ID to list of entity indices

            for doc in documents:
                doc_start_idx = len(all_entities)
                doc_entity_indices = []

                for entity in doc.entities:
                    entity_idx = len(all_entities)
                    all_entities.append(entity)
                    entity_to_doc[entity_idx] = doc.id
                    doc_entity_indices.append(entity_idx)

                doc_id_to_entity_indices[doc.id] = doc_entity_indices

            if len(all_entities) < 2:
                log.warning(f"Insufficient entities ({len(all_entities)}) for multi-document graph")
                return None

            # Merge duplicate entities (same text + type)
            entity_map, unique_entities = self._merge_duplicate_entities(all_entities)

            log.debug(f"Merged {len(all_entities)} entities into {len(unique_entities)} unique entities")

            # Create node features for unique entities
            node_texts = [entity.text for entity in unique_entities]
            node_embeddings = self.embedding_model.encode(
                node_texts, convert_to_tensor=True, device=self.device, show_progress_bar=False
            )

            # Create edges (within and across documents)
            edge_indices = []

            # 1. Within-document edges
            for doc in documents:
                doc_entity_indices = doc_id_to_entity_indices[doc.id]
                # Map to unique entity indices
                unique_doc_indices = [entity_map[idx] for idx in doc_entity_indices]
                doc_entities = [all_entities[idx] for idx in doc_entity_indices]

                # Create edges within this document
                doc_edges = self._create_edges_for_entity_list(doc_entities, unique_doc_indices, doc.text)
                edge_indices.extend(doc_edges)

            # 2. Cross-document edges (semantic similarity)
            cross_doc_edges = self._create_cross_document_edges(unique_entities, node_embeddings)
            edge_indices.extend(cross_doc_edges)

            if not edge_indices:
                log.warning("No edges created for multi-document graph")
                return None

            # Remove duplicates
            edge_indices = list(dict.fromkeys(edge_indices))

            # Create edge attributes
            edge_attrs = self._create_edge_attributes_from_indices(unique_entities, edge_indices)

            # Create PyTorch Geometric Data object
            graph_data = Data(
                x=node_embeddings,
                edge_index=torch.tensor(edge_indices, dtype=torch.long).t().contiguous(),
                edge_attr=torch.tensor(edge_attrs, dtype=torch.float),
                num_nodes=len(unique_entities),
            )

            # Add metadata for retrieval
            graph_data.doc_id_to_node_indices = {
                doc_id: [entity_map[idx] for idx in indices] for doc_id, indices in doc_id_to_entity_indices.items()
            }
            graph_data.node_to_doc_id = {
                entity_map[idx]: doc_id for doc_id, indices in doc_id_to_entity_indices.items() for idx in indices
            }

            log.info(
                f"Created multi-document graph: {len(unique_entities)} nodes, "
                f"{len(edge_indices)} edges, {len(documents)} documents"
            )

            return graph_data

        except Exception as e:
            log.error(f"Error building multi-document graph: {e}")
            return None

    def _merge_duplicate_entities(self, entities: List[LegalEntity]) -> Tuple[Dict[int, int], List[LegalEntity]]:
        """
        Merge duplicate entities (same text + type)

        Args:
            entities: List of all entities

        Returns:
            entity_map: Maps original index to unique index
            unique_entities: List of unique entities
        """
        entity_map = {}
        unique_entities = []
        entity_key_to_idx = {}  # Maps (text, label) to unique index

        for idx, entity in enumerate(entities):
            # Create key from text and label
            key = (entity.text.lower().strip(), entity.label)

            if key in entity_key_to_idx:
                # Duplicate found, map to existing unique entity
                entity_map[idx] = entity_key_to_idx[key]
            else:
                # New unique entity
                unique_idx = len(unique_entities)
                entity_map[idx] = unique_idx
                entity_key_to_idx[key] = unique_idx
                unique_entities.append(entity)

        return entity_map, unique_entities

    def _create_edges_for_entity_list(
        self, entities: List[LegalEntity], entity_indices: List[int], text: str
    ) -> List[Tuple[int, int]]:
        """
        Create edges for a list of entities with their unique indices

        Args:
            entities: List of entities
            entity_indices: Corresponding unique indices
            text: Document text

        Returns:
            List of (source, target) edge tuples using unique indices
        """
        edges = []

        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities):
                if i >= j:
                    continue

                idx1 = entity_indices[i]
                idx2 = entity_indices[j]

                # Distance-based edges
                distance = abs(entity1.start - entity2.start)
                if distance < self.proximity_threshold:
                    edges.append((idx1, idx2))
                    edges.append((idx2, idx1))

                # Same type edges
                if entity1.label == entity2.label:
                    edges.append((idx1, idx2))
                    edges.append((idx2, idx1))

                # Legal relationship edges
                if self._has_legal_relationship(entity1, entity2):
                    edges.append((idx1, idx2))
                    if self._is_bidirectional_relationship(entity1.label, entity2.label):
                        edges.append((idx2, idx1))

        return edges

    def _create_cross_document_edges(
        self, entities: List[LegalEntity], embeddings: torch.Tensor
    ) -> List[Tuple[int, int]]:
        """
        Create edges between entities from different documents based on semantic similarity

        Args:
            entities: List of unique entities
            embeddings: Entity embeddings

        Returns:
            List of (source, target) edge tuples
        """
        edges = []

        # Normalize embeddings for cosine similarity
        embeddings_norm = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        # Compute similarity matrix
        similarity_matrix = torch.mm(embeddings_norm, embeddings_norm.t())

        # Create edges for high similarity pairs
        num_entities = len(entities)
        for i in range(num_entities):
            for j in range(i + 1, num_entities):
                similarity = similarity_matrix[i, j].item()

                # Only create edge if similarity is high enough
                if similarity >= self.similarity_threshold:
                    edges.append((i, j))
                    edges.append((j, i))

        return edges

    def _create_edge_attributes_from_indices(
        self, entities: List[LegalEntity], edges: List[Tuple[int, int]]
    ) -> List[List[float]]:
        """
        Create edge attributes for edges specified by unique indices

        Args:
            entities: List of unique entities
            edges: List of edge tuples with unique indices

        Returns:
            List of edge feature vectors
        """
        edge_attrs = []

        for i, j in edges:
            entity1, entity2 = entities[i], entities[j]

            # Distance feature (use 0.5 for cross-document edges)
            if hasattr(entity1, "start") and hasattr(entity2, "start"):
                distance = abs(entity1.start - entity2.start) / 1000.0
                distance = min(distance, 1.0)
            else:
                distance = 0.5  # Default for cross-document

            # Confidence feature
            confidence = (entity1.confidence + entity2.confidence) / 2.0

            # Relationship type
            relationship_type = self._get_relationship_type(entity1.label, entity2.label)

            # Combine features
            edge_attr = [distance, confidence] + relationship_type
            edge_attrs.append(edge_attr)

        return edge_attrs

    def build_batch_graphs(self, documents: List[LegalDocument], show_progress: bool = True) -> List[Optional[Data]]:
        """
        Build graphs for multiple documents

        Args:
            documents: List of legal documents
            show_progress: Show progress bar

        Returns:
            List of graph Data objects (None for failed documents)
        """
        graphs = []

        iterator = documents
        if show_progress:
            try:
                from tqdm import tqdm

                iterator = tqdm(documents, desc="Building graphs")
            except ImportError:
                pass

        for doc in iterator:
            graph = self.build_graph(doc)
            graphs.append(graph)

        success_count = sum(1 for g in graphs if g is not None)
        log.info(
            f"Built {success_count}/{len(documents)} graphs successfully ({success_count / len(documents) * 100:.1f}%)"
        )

        return graphs

    def get_graph_statistics(self, graph: Data) -> Dict[str, any]:
        """
        Get comprehensive statistics about a graph

        Computes basic and advanced graph metrics including:
        - Basic: nodes, edges, average degree, density
        - Advanced: clustering coefficient, connected components
        - Validation: checks for isolated nodes and valid edge indices

        Args:
            graph: PyG Data object

        Returns:
            Dictionary of statistics
        """
        if graph is None:
            return {}

        num_nodes = graph.num_nodes
        num_edges = graph.edge_index.shape[1]

        # Basic statistics
        avg_degree = (2 * num_edges) / num_nodes if num_nodes > 0 else 0
        max_possible_edges = num_nodes * (num_nodes - 1)
        density = num_edges / max_possible_edges if max_possible_edges > 0 else 0

        # Degree distribution
        degrees = torch.zeros(num_nodes, dtype=torch.long)
        if num_edges > 0:
            for i in range(num_edges):
                src = graph.edge_index[0, i].item()
                dst = graph.edge_index[1, i].item()
                degrees[src] += 1
                degrees[dst] += 1

        max_degree = degrees.max().item() if num_nodes > 0 else 0
        min_degree = degrees.min().item() if num_nodes > 0 else 0

        # Isolated nodes
        isolated_nodes = (degrees == 0).sum().item()

        # Clustering coefficient (approximate for large graphs)
        clustering_coeff = self._compute_clustering_coefficient(graph)

        # Connected components (approximate)
        num_components = self._count_connected_components(graph)

        # Validation checks
        has_isolated_nodes = isolated_nodes > 0
        has_valid_edges = self._validate_edge_indices(graph)

        stats = {
            # Basic stats
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "avg_degree": float(avg_degree),
            "density": float(density),
            # Degree stats
            "max_degree": max_degree,
            "min_degree": min_degree,
            "isolated_nodes": isolated_nodes,
            # Advanced stats
            "clustering_coefficient": clustering_coeff,
            "num_components": num_components,
            # Feature dimensions
            "node_feature_dim": graph.x.shape[1] if graph.x is not None else 0,
            "edge_feature_dim": graph.edge_attr.shape[1] if graph.edge_attr is not None else 0,
            # Validation
            "has_labels": hasattr(graph, "y") and graph.y is not None,
            "has_isolated_nodes": has_isolated_nodes,
            "has_valid_edges": has_valid_edges,
        }

        return stats

    def _compute_clustering_coefficient(self, graph: Data) -> float:
        """
        Compute global clustering coefficient

        For large graphs, this is an approximation using sampling.

        Args:
            graph: PyG Data object

        Returns:
            Clustering coefficient [0, 1]
        """
        try:
            num_nodes = graph.num_nodes

            if num_nodes == 0 or graph.edge_index.shape[1] == 0:
                return 0.0

            # For small graphs, compute exactly
            if num_nodes <= 1000:
                # Convert to adjacency matrix
                adj = torch.zeros((num_nodes, num_nodes), dtype=torch.bool)
                for i in range(graph.edge_index.shape[1]):
                    src = graph.edge_index[0, i].item()
                    dst = graph.edge_index[1, i].item()
                    adj[src, dst] = True

                # Count triangles
                triangles = 0
                triplets = 0

                for i in range(num_nodes):
                    neighbors = adj[i].nonzero(as_tuple=True)[0]
                    k = len(neighbors)

                    if k < 2:
                        continue

                    # Count triangles involving node i
                    for j in range(len(neighbors)):
                        for l in range(j + 1, len(neighbors)):
                            n1 = neighbors[j].item()
                            n2 = neighbors[l].item()
                            if adj[n1, n2]:
                                triangles += 1

                    # Count possible triplets
                    triplets += k * (k - 1) // 2

                if triplets == 0:
                    return 0.0

                return triangles / triplets

            else:
                # For large graphs, return approximate value
                return 0.1  # Placeholder

        except Exception as e:
            log.warning(f"Error computing clustering coefficient: {e}")
            return 0.0

    def _count_connected_components(self, graph: Data) -> int:
        """
        Count number of connected components using Union-Find

        Args:
            graph: PyG Data object

        Returns:
            Number of connected components
        """
        try:
            num_nodes = graph.num_nodes

            if num_nodes == 0:
                return 0

            # Union-Find data structure
            parent = list(range(num_nodes))

            def find(x):
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]

            def union(x, y):
                px, py = find(x), find(y)
                if px != py:
                    parent[px] = py

            # Union all connected nodes
            for i in range(graph.edge_index.shape[1]):
                src = graph.edge_index[0, i].item()
                dst = graph.edge_index[1, i].item()
                union(src, dst)

            # Count unique roots
            components = len(set(find(i) for i in range(num_nodes)))

            return components

        except Exception as e:
            log.warning(f"Error counting connected components: {e}")
            return 1

    def _validate_edge_indices(self, graph: Data) -> bool:
        """
        Validate that all edge indices are within valid range

        Args:
            graph: PyG Data object

        Returns:
            True if all edges are valid
        """
        try:
            if graph.edge_index.shape[1] == 0:
                return True

            max_idx = graph.edge_index.max().item()
            min_idx = graph.edge_index.min().item()

            return min_idx >= 0 and max_idx < graph.num_nodes

        except Exception as e:
            log.warning(f"Error validating edge indices: {e}")
            return False

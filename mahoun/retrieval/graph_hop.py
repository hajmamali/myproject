"""
Graph Hop Retrieval
===================

K-hop expansion for graph-enhanced retrieval.
Expands initial retrieval results by traversing the knowledge graph.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING
from collections import defaultdict, deque
from dataclasses import dataclass, field

try:
    import networkx as nx  # type: ignore[no-redef]
    from networkx import DiGraph  # Import at runtime for type annotations
except ImportError:
    nx: Optional[Any] = None  # type: ignore[assignment]
    DiGraph = Any  # type: ignore[misc,assignment]  # Fallback when networkx not available

logger = logging.getLogger(__name__)


@dataclass
class HopResult:
    """Result from graph hop expansion"""
    entity_id: str
    entity_text: str
    entity_label: str
    hop_distance: int
    path_score: float
    path: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'entity_id': self.entity_id,
            'entity_text': self.entity_text,
            'entity_label': self.entity_label,
            'hop_distance': self.hop_distance,
            'path_score': self.path_score,
            'path': self.path,
            'relationships': self.relationships,
            'metadata': self.metadata
        }


class GraphHopRetriever:
    """
    K-hop graph expansion for retrieval
    
    Expands initial retrieval results by:
    1. Finding seed entities in graph
    2. Performing k-hop traversal
    3. Scoring paths based on relationships
    4. Filtering by constraints
    """
    
    def __init__(
        self,
        graph: Optional[DiGraph] = None,
        max_hops: int = 2,
        max_results_per_hop: int = 10,
        decay_factor: float = 0.7,
        relationship_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize GraphHopRetriever
        
        Args:
            graph: NetworkX graph
            max_hops: Maximum number of hops
            max_results_per_hop: Maximum results per hop level
            decay_factor: Score decay per hop (0-1)
            relationship_weights: Weights for different relationship types
        """
        self.graph = graph
        self.max_hops = max_hops
        self.max_results_per_hop = max_results_per_hop
        self.decay_factor = decay_factor
        
        # Default relationship weights
        self.relationship_weights = relationship_weights or {
            'CITES': 1.0,
            'REFERENCES': 0.9,
            'RELATED': 0.7,
            'CO_OCCURS': 0.5,
            'SIMILAR': 0.6,
            'CONTAINS': 0.8,
            'BASED_ON': 0.9,
        }
        
        logger.info(
            f"GraphHopRetriever initialized (max_hops={max_hops}, "
            f"decay_factor={decay_factor})"
        )
    
    def set_graph(self, graph: DiGraph):
        """Set the graph to use for retrieval"""
        self.graph = graph
        logger.info(f"Graph set: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    def k_hop_expansion(
        self,
        seed_entities: List[str],
        initial_scores: Optional[Dict[str, float]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[HopResult]:
        """
        Perform k-hop expansion from seed entities
        
        Args:
            seed_entities: List of seed entity IDs
            initial_scores: Initial scores for seed entities
            constraints: Filtering constraints (e.g., entity_types, min_score)
        
        Returns:
            List of HopResult objects
        """
        if self.graph is None or nx is None:
            logger.error("Graph not available")
            return []
        
        if not seed_entities:
            return []
        
        # Initialize scores
        if initial_scores is None:
            initial_scores = {entity: 1.0 for entity in seed_entities}
        
        # Initialize constraints
        constraints = constraints or {}
        allowed_entity_types = constraints.get('entity_types', None)
        min_score = constraints.get('min_score', 0.1)
        
        # BFS traversal with scoring
        visited = set()
        results: List[Any] = []
        # Queue: (entity_id, hop_distance, path, relationships, score)
        queue = deque([
            (entity, 0, [entity], [], initial_scores.get(entity, 1.0))
            for entity in seed_entities
            if entity in self.graph
        ])
        
        # Track results per hop level
        results_per_hop = defaultdict(list)
        
        while queue:
            current_entity, hop_distance, path, relationships, score = queue.popleft()
            
            # Skip if already visited
            if current_entity in visited:
                continue
            
            visited.add(current_entity)
            
            # Get entity data
            entity_data = self.graph.nodes.get(current_entity, {})
            entity_label = entity_data.get('label', 'UNKNOWN')
            entity_text = entity_data.get('text', current_entity)
            
            # Apply entity type filter
            if allowed_entity_types and entity_label not in allowed_entity_types:
                continue
            
            # Apply score threshold
            if score < min_score:
                continue
            
            # Create result
            result = HopResult(
                entity_id=current_entity,
                entity_text=entity_text,
                entity_label=entity_label,
                hop_distance=hop_distance,
                path_score=score,
                path=path.copy(),
                relationships=relationships.copy(),
                metadata=entity_data.get('metadata', {})
            )
            
            results_per_hop[hop_distance].append(result)
            
            # Continue expansion if within hop limit
            if hop_distance < self.max_hops:
                # Get neighbors
                neighbors = list(self.graph.successors(current_entity))
                
                for neighbor in neighbors:
                    if neighbor in visited:
                        continue
                    
                    # Get edge data
                    edge_data = self.graph.edges.get((current_entity, neighbor), {})
                    rel_type = edge_data.get('type', 'UNKNOWN')
                    rel_confidence = edge_data.get('confidence', 1.0)
                    
                    # Calculate new score
                    rel_weight = self.relationship_weights.get(rel_type, 0.5)
                    new_score = score * self.decay_factor * rel_weight * rel_confidence
                    
                    # Add to queue
                    new_path = path + [neighbor]
                    new_relationships = relationships + [rel_type]
                    
                    queue.append((
                        neighbor,
                        hop_distance + 1,
                        new_path,
                        new_relationships,
                        new_score
                    ))
        
        # Collect results with per-hop limits
        final_results: List[Any] = []
        for hop_distance in sorted(results_per_hop.keys()):
            hop_results = results_per_hop[hop_distance]
            
            # Sort by score
            hop_results.sort(key=lambda x: x.path_score, reverse=True)
            
            # Limit results per hop
            hop_results = hop_results[:self.max_results_per_hop]
            
            final_results.extend(hop_results)
        
        logger.info(
            f"K-hop expansion: {len(seed_entities)} seeds → "
            f"{len(final_results)} results (visited {len(visited)} nodes)"
        )
        
        return final_results
    
    def expand_retrieval_results(
        self,
        retrieval_results: List[Dict[str, Any]],
        score_field: str = 'score',
        id_field: str = 'id',
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[HopResult]:
        """
        Expand retrieval results using graph hops
        
        Args:
            retrieval_results: List of retrieval result dictionaries
            score_field: Field name for scores
            id_field: Field name for IDs
            constraints: Filtering constraints
        
        Returns:
            List of expanded HopResult objects
        """
        # Extract seed entities and scores
        seed_entities: List[Any] = []
        initial_scores: Dict[str, Any] = {}
        for result in retrieval_results:
            entity_id = result.get(id_field)
            score = result.get(score_field, 1.0)
            
            if entity_id:
                seed_entities.append(entity_id)
                initial_scores[entity_id] = score
        
        # Perform k-hop expansion
        return self.k_hop_expansion(seed_entities, initial_scores, constraints)
    
    def find_paths(
        self,
        source: str,
        target: str,
        max_path_length: Optional[int] = None
    ) -> List[List[str]]:
        """
        Find all paths between source and target
        
        Args:
            source: Source entity ID
            target: Target entity ID
            max_path_length: Maximum path length (None for unlimited)
        
        Returns:
            List of paths (each path is a list of entity IDs)
        """
        if self.graph is None or nx is None:
            return []
        
        if source not in self.graph or target not in self.graph:
            return []
        
        try:
            # Use NetworkX to find all simple paths
            if max_path_length:
                paths = list(nx.all_simple_paths(
                    self.graph,
                    source,
                    target,
                    cutoff=max_path_length
                ))
            else:
                paths = list(nx.all_simple_paths(
                    self.graph,
                    source,
                    target,
                    cutoff=self.max_hops
                ))
            
            return paths
            
        except Exception as e:
            logger.error(f"Error finding paths: {e}")
            return []
    
    def score_path(self, path: List[str]) -> float:
        """
        Score a path based on relationships
        
        Args:
            path: List of entity IDs forming a path
        
        Returns:
            Path score
        """
        if len(path) < 2:
            return 1.0
        
        score = 1.0
        
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            
            # Get edge data
            edge_data = self.graph.edges.get((source, target), {})
            rel_type = edge_data.get('type', 'UNKNOWN')
            rel_confidence = edge_data.get('confidence', 1.0)
            
            # Apply relationship weight and decay
            rel_weight = self.relationship_weights.get(rel_type, 0.5)
            score *= self.decay_factor * rel_weight * rel_confidence
        
        return score
    
    def get_subgraph(
        self,
        seed_entities: List[str],
        max_hops: Optional[int] = None
    ) -> Optional[DiGraph]:
        """
        Extract subgraph around seed entities
        
        Args:
            seed_entities: List of seed entity IDs
            max_hops: Maximum hops (None to use default)
        
        Returns:
            Subgraph as NetworkX DiGraph
        """
        if self.graph is None or nx is None:
            return None
        
        max_hops = max_hops or self.max_hops
        
        # Collect all nodes within k hops
        nodes_to_include = set(seed_entities)
        
        for seed in seed_entities:
            if seed not in self.graph:
                continue
            
            # BFS to find nodes within k hops
            visited = {seed}
            queue = deque([(seed, 0)])
            
            while queue:
                node, distance = queue.popleft()
                
                if distance >= max_hops:
                    continue
                
                # Add neighbors
                for neighbor in self.graph.successors(node):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        nodes_to_include.add(neighbor)
                        queue.append((neighbor, distance + 1))
        
        # Create subgraph
        subgraph = self.graph.subgraph(nodes_to_include).copy()
        
        logger.info(
            f"Extracted subgraph: {subgraph.number_of_nodes()} nodes, "
            f"{subgraph.number_of_edges()} edges"
        )
        
        return subgraph
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retriever statistics"""
        if self.graph is None:
            return {}
        
        return {
            'graph_nodes': self.graph.number_of_nodes() if self.graph else 0,
            'graph_edges': self.graph.number_of_edges() if self.graph else 0,
            'max_hops': self.max_hops,
            'max_results_per_hop': self.max_results_per_hop,
            'decay_factor': self.decay_factor,
            'relationship_weights': self.relationship_weights
        }


# Convenience function
def expand_with_graph_hops(
    retrieval_results: List[Dict[str, Any]],
    graph: DiGraph,
    max_hops: int = 2,
    max_results_per_hop: int = 10
) -> List[HopResult]:
    """
    Convenience function to expand retrieval results with graph hops
    
    Args:
        retrieval_results: List of retrieval results
        graph: NetworkX graph
        max_hops: Maximum hops
        max_results_per_hop: Maximum results per hop
    
    Returns:
        List of HopResult objects
    """
    retriever = GraphHopRetriever(
        graph=graph,
        max_hops=max_hops,
        max_results_per_hop=max_results_per_hop
    )
    
    return retriever.expand_retrieval_results(retrieval_results)

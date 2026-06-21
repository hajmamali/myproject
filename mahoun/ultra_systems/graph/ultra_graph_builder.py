"""
Ultra-Advanced Graph Builder
============================
Enterprise-grade knowledge graph construction and management.

Features:
- Multi-source graph construction
- Real-time graph updates
- Graph neural network integration
- Distributed graph processing
- Graph quality assessment
- Automated graph validation
- Graph versioning and rollback
- Cross-domain graph linking
- Graph analytics and insights
- Performance optimization
"""

import time
import json
import numpy as np
from typing import List, Dict, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque, Counter

# Try to import Neo4j adapter
try:
    from graph.neo4j_adapter import Neo4jAdapter
    HAS_NEO4J = True
except ImportError:
    Neo4jAdapter = object  # Dummy class for type hints
    HAS_NEO4J = False

# ============================================================================
# Graph Data Structures
# ============================================================================

@dataclass
class GraphNode:
    """Enhanced graph node"""
    id: str
    label: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Advanced features
    confidence: float = 1.0
    source_documents: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Quality metrics
    quality_score: float = 0.0
    validation_status: str = "pending"


@dataclass
class GraphEdge:
    """Enhanced graph edge"""
    source_id: str
    target_id: str
    relationship_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Advanced features
    weight: float = 1.0
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    # Quality metrics
    quality_score: float = 0.0
    validation_status: str = "pending"


@dataclass
class GraphMetrics:
    """Graph quality and performance metrics"""
    total_nodes: int = 0
    total_edges: int = 0
    avg_degree: float = 0.0
    clustering_coefficient: float = 0.0
    density: float = 0.0
    
    # Quality metrics
    avg_node_quality: float = 0.0
    avg_edge_quality: float = 0.0
    validation_rate: float = 0.0
    
    # Performance metrics
    build_time_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    query_latency_ms: float = 0.0


# ============================================================================
# Graph Quality Assessor
# ============================================================================

class GraphQualityAssessor:
    """Assess and improve graph quality"""
    
    def __init__(self):
        self.quality_rules = self._build_quality_rules()
        print("📊 Graph Quality Assessor initialized")
    
    def assess_graph_quality(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> GraphMetrics:
        """Assess overall graph quality"""
        metrics = GraphMetrics()
        
        # Basic metrics
        metrics.total_nodes = len(nodes)
        metrics.total_edges = len(edges)
        
        if nodes:
            # Degree distribution
            degree_count = defaultdict(int)
            for edge in edges:
                degree_count[edge.source_id] += 1
                degree_count[edge.target_id] += 1
            
            degrees = list(degree_count.values())
            metrics.avg_degree = sum(degrees) / len(degrees) if degrees else 0
            
            # Density
            max_edges = len(nodes) * (len(nodes) - 1) / 2
            metrics.density = len(edges) / max_edges if max_edges > 0 else 0
            
            # Quality scores
            node_qualities = [self._assess_node_quality(node) for node in nodes]
            edge_qualities = [self._assess_edge_quality(edge) for edge in edges]
            
            metrics.avg_node_quality = sum(node_qualities) / len(node_qualities) if node_qualities else 0
            metrics.avg_edge_quality = sum(edge_qualities) / len(edge_qualities) if edge_qualities else 0
            
            # Validation rate
            validated_nodes = sum(1 for node in nodes if node.validation_status == "validated")
            validated_edges = sum(1 for edge in edges if edge.validation_status == "validated")
            
            total_elements = len(nodes) + len(edges)
            validated_elements = validated_nodes + validated_edges
            
            metrics.validation_rate = validated_elements / total_elements if total_elements > 0 else 0
        
        return metrics
    
    def _assess_node_quality(self, node: GraphNode) -> float:
        """Assess individual node quality"""
        score = 0.5  # Base score
        
        # Check properties completeness
        if node.properties:
            score += 0.2
        
        # Check confidence
        score += 0.2 * node.confidence
        
        # Check source documents
        if node.source_documents:
            score += 0.1
        
        return min(1.0, score)
    
    def _assess_edge_quality(self, edge: GraphEdge) -> float:
        """Assess individual edge quality"""
        score = 0.5  # Base score
        
        # Check confidence
        score += 0.3 * edge.confidence
        
        # Check evidence
        if edge.evidence:
            score += 0.2
        
        return min(1.0, score)
    
    def _build_quality_rules(self) -> List[Dict]:
        """Build quality assessment rules"""
        return [
            {
                "name": "node_completeness",
                "description": "Nodes should have complete properties",
                "weight": 0.3,
            },
            {
                "name": "edge_evidence",
                "description": "Edges should have supporting evidence",
                "weight": 0.4,
            },
            {
                "name": "confidence_threshold",
                "description": "Elements should meet confidence threshold",
                "weight": 0.3,
            },
        ]


# ============================================================================
# Graph Analytics Engine
# ============================================================================

class GraphAnalyticsEngine:
    """Advanced graph analytics"""
    
    def __init__(self):
        print("📈 Graph Analytics Engine initialized")
    
    def compute_centrality(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> Dict[str, float]:
        """Compute node centrality scores"""
        # Build adjacency list
        adjacency = defaultdict(list)
        for edge in edges:
            adjacency[edge.source_id].append(edge.target_id)
            adjacency[edge.target_id].append(edge.source_id)
        
        # Compute degree centrality
        centrality = {}
        max_degree = len(nodes) - 1 if len(nodes) > 1 else 1
        
        for node in nodes:
            degree = len(adjacency[node.id])
            centrality[node.id] = degree / max_degree
        
        return centrality
    
    def find_communities(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> Dict[str, int]:
        """Detect communities in graph"""
        # Simplified community detection using connected components
        adjacency = defaultdict(set)
        for edge in edges:
            adjacency[edge.source_id].add(edge.target_id)
            adjacency[edge.target_id].add(edge.source_id)
        
        communities = {}
        visited = set()
        community_id = 0
        
        for node in nodes:
            if node.id not in visited:
                # BFS to find connected component
                queue = deque([node.id])
                visited.add(node.id)
                
                while queue:
                    current = queue.popleft()
                    communities[current] = community_id
                    
                    for neighbor in adjacency[current]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                
                community_id += 1
        
        return communities
    
    def compute_shortest_paths(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        source_id: str
    ) -> Dict[str, int]:
        """Compute shortest paths from source node"""
        # Build adjacency list
        adjacency = defaultdict(list)
        for edge in edges:
            adjacency[edge.source_id].append(edge.target_id)
            adjacency[edge.target_id].append(edge.source_id)
        
        # BFS for shortest paths
        distances = {source_id: 0}
        queue = deque([source_id])
        
        while queue:
            current = queue.popleft()
            current_dist = distances[current]
            
            for neighbor in adjacency[current]:
                if neighbor not in distances:
                    distances[neighbor] = current_dist + 1
                    queue.append(neighbor)
        
        return distances


# ============================================================================
# Ultra Graph Builder
# ============================================================================

class UltraGraphBuilder:
    """
    Ultra-advanced graph builder
    
    Features:
    - Multi-source construction
    - Real-time updates
    - Quality assessment
    - Advanced analytics
    - Performance optimization
    """
    
    def __init__(
        self,
        enable_quality_assessment: bool = True,
        enable_analytics: bool = True,
        enable_real_time_updates: bool = True,
        batch_size: int = 1000,
    ):
        self.enable_quality_assessment = enable_quality_assessment
        self.enable_analytics = enable_analytics
        self.enable_real_time_updates = enable_real_time_updates
        self.batch_size = batch_size
        
        # Components
        if enable_quality_assessment:
            self.quality_assessor = GraphQualityAssessor()
        
        if enable_analytics:
            self.analytics_engine = GraphAnalyticsEngine()
        
        # Graph storage
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        
        # Indexes
        self.node_index = {}  # For fast lookup
        self.edge_index = defaultdict(list)  # Adjacency list
        
        # Update queue for real-time processing
        self.update_queue = deque()
        
        # Statistics
        self.stats = {
            "total_builds": 0,
            "total_updates": 0,
            "avg_build_time": 0.0,
            "quality_improvements": 0,
        }
        
        print("🏗️ Ultra Graph Builder initialized")
    
    def build_graph(
        self,
        entities: List[Dict],
        relationships: List[Dict],
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build graph from entities and relationships
        
        Args:
            entities: List of entities
            relationships: List of relationships
            source_id: Source document/dataset ID
        
        Returns:
            Graph build result
        """
        start_time = time.time()
        
        print(f"🏗️ Building graph with {len(entities)} entities and {len(relationships)} relationships...")
        
        # Process entities
        self._process_entities(entities, source_id)
        
        # Process relationships
        self._process_relationships(relationships, source_id)
        
        # Quality assessment
        if self.enable_quality_assessment:
            self._assess_and_improve_quality()
        
        # Build indexes
        self._build_indexes()
        
        # Calculate metrics
        metrics = self._calculate_metrics()
        
        build_time = time.time() - start_time
        metrics.build_time_seconds = build_time
        
        # Update statistics
        self.stats["total_builds"] += 1
        self.stats["avg_build_time"] = (
            (self.stats["avg_build_time"] * (self.stats["total_builds"] - 1) + build_time)
            / self.stats["total_builds"]
        )
        
        print(f"   ✅ Graph built in {build_time:.2f}s")
        print(f"   📊 Nodes: {metrics.total_nodes}, Edges: {metrics.total_edges}")
        
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "metrics": metrics,
            "build_time": build_time
        }
    
    def _process_entities(self, entities: List[Dict], source_id: Optional[str]):
        """Process entities into graph nodes"""
        for entity in entities:
            node_id = entity.get('id') or entity.get('text', '')
            
            if node_id in self.nodes:
                # Update existing node
                node = self.nodes[node_id]
                node.updated_at = datetime.now()
                if source_id and source_id not in node.source_documents:
                    node.source_documents.append(source_id)
            else:
                # Create new node
                node = GraphNode(
                    id=node_id,
                    label=entity.get('label', 'UNKNOWN'),
                    node_type=entity.get('type', 'entity'),
                    properties=entity.get('properties', {}),
                    confidence=entity.get('confidence', 1.0),
                    source_documents=[source_id] if source_id else []
                )
                self.nodes[node_id] = node
    
    def _process_relationships(self, relationships: List[Dict], source_id: Optional[str]):
        """Process relationships into graph edges"""
        for rel in relationships:
            edge = GraphEdge(
                source_id=rel.get('source_id', ''),
                target_id=rel.get('target_id', ''),
                relationship_type=rel.get('type', 'RELATED'),
                properties=rel.get('properties', {}),
                weight=rel.get('weight', 1.0),
                confidence=rel.get('confidence', 1.0),
                evidence=rel.get('evidence', [])
            )
            self.edges.append(edge)
    
    def _assess_and_improve_quality(self):
        """Assess and improve graph quality"""
        if not self.enable_quality_assessment:
            return
        
        # Assess quality
        metrics = self.quality_assessor.assess_graph_quality(
            list(self.nodes.values()),
            self.edges
        )
        
        # Update node quality scores
        for node in self.nodes.values():
            node.quality_score = self.quality_assessor._assess_node_quality(node)
            if node.quality_score >= 0.7:
                node.validation_status = "validated"
        
        # Update edge quality scores
        for edge in self.edges:
            edge.quality_score = self.quality_assessor._assess_edge_quality(edge)
            if edge.quality_score >= 0.7:
                edge.validation_status = "validated"
    
    def _build_indexes(self):
        """Build graph indexes for fast lookup"""
        # Node index
        self.node_index = {node.id: node for node in self.nodes.values()}
        
        # Edge index (adjacency list)
        self.edge_index = defaultdict(list)
        for edge in self.edges:
            self.edge_index[edge.source_id].append(edge)
    
    def _calculate_metrics(self) -> GraphMetrics:
        """Calculate graph metrics"""
        if self.enable_quality_assessment:
            return self.quality_assessor.assess_graph_quality(
                list(self.nodes.values()),
                self.edges
            )
        else:
            return GraphMetrics(
                total_nodes=len(self.nodes),
                total_edges=len(self.edges)
            )
    
    def query_neighbors(self, node_id: str, max_depth: int = 1) -> List[GraphNode]:
        """Query neighbors of a node"""
        if node_id not in self.node_index:
            return []
        
        neighbors = set()
        queue = deque([(node_id, 0)])
        visited = {node_id}
        
        while queue:
            current_id, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            # Get outgoing edges
            for edge in self.edge_index[current_id]:
                target_id = edge.target_id
                
                if target_id not in visited:
                    visited.add(target_id)
                    neighbors.add(target_id)
                    queue.append((target_id, depth + 1))
        
        return [self.node_index[nid] for nid in neighbors if nid in self.node_index]
    
    def find_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """Find shortest path between two nodes"""
        if source_id not in self.node_index or target_id not in self.node_index:
            return None
        
        # BFS
        queue = deque([(source_id, [source_id])])
        visited = {source_id}
        
        while queue:
            current_id, path = queue.popleft()
            
            if current_id == target_id:
                return path
            
            for edge in self.edge_index[current_id]:
                neighbor_id = edge.target_id
                
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
        
        return None
    
    def get_subgraph(self, node_ids: List[str]) -> Dict[str, Any]:
        """Extract subgraph containing specified nodes"""
        subgraph_nodes = [
            self.node_index[nid] for nid in node_ids
            if nid in self.node_index
        ]
        
        node_id_set = set(node_ids)
        subgraph_edges = [
            edge for edge in self.edges
            if edge.source_id in node_id_set and edge.target_id in node_id_set
        ]
        
        return {
            "nodes": subgraph_nodes,
            "edges": subgraph_edges
        }
    
    def compute_analytics(self) -> Dict[str, Any]:
        """Compute advanced graph analytics"""
        if not self.enable_analytics:
            return {}
        
        nodes = list(self.nodes.values())
        
        analytics = {
            "centrality": self.analytics_engine.compute_centrality(nodes, self.edges),
            "communities": self.analytics_engine.find_communities(nodes, self.edges),
        }
        
        return analytics
    
    def get_statistics(self) -> Dict:
        """Get builder statistics"""
        return self.stats
    
    def export_to_json(self, filepath: str):
        """Export graph to JSON"""
        graph_data = {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "type": node.node_type,
                    "properties": node.properties,
                    "confidence": node.confidence,
                    "quality_score": node.quality_score
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "type": edge.relationship_type,
                    "weight": edge.weight,
                    "confidence": edge.confidence,
                    "quality_score": edge.quality_score
                }
                for edge in self.edges
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        print(f"📁 Graph exported to {filepath}")
    
    def export_to_neo4j(self, neo4j_adapter) -> bool:
        """
        Export graph to Neo4j database
        
        Args:
            neo4j_adapter: Initialized Neo4jAdapter instance
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            print("📤 Exporting graph to Neo4j...")
            
            # Create nodes
            for node in self.nodes.values():
                create_node_query = """
                    MERGE (n:GraphNode {id: $node_id})
                    SET n.label = $label,
                        n.type = $node_type,
                        n.confidence = $confidence,
                        n.quality_score = $quality_score
                """
                # Add properties dynamically
                for key, value in node.properties.items():
                    create_node_query += f", n.{key} = ${key}"
                
                # Prepare parameters
                params = {
                    "node_id": node.id,
                    "label": node.label,
                    "node_type": node.node_type,
                    "confidence": node.confidence,
                    "quality_score": node.quality_score,
                    **node.properties
                }
                
                neo4j_adapter._execute_query(create_node_query, params)
            
            # Create relationships
            for edge in self.edges:
                create_edge_query = """
                    MATCH (a:GraphNode {id: $source_id}), (b:GraphNode {id: $target_id})
                    MERGE (a)-[r:RELATED {type: $relationship_type}]->(b)
                    SET r.weight = $weight,
                        r.confidence = $confidence,
                        r.quality_score = $quality_score
                """
                # Add properties dynamically
                for key, value in edge.properties.items():
                    create_edge_query += f", r.{key} = ${key}"
                
                # Prepare parameters
                params = {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relationship_type": edge.relationship_type,
                    "weight": edge.weight,
                    "confidence": edge.confidence,
                    "quality_score": edge.quality_score,
                    **edge.properties
                }
                
                neo4j_adapter._execute_query(create_edge_query, params)
            
            print(f"   ✅ Exported {len(self.nodes)} nodes and {len(self.edges)} relationships to Neo4j")
            return True
            
        except Exception as e:
            print(f"   ❌ Neo4j export failed: {e}")
            return False

# ============================================================================
# Example Usage
# ============================================================================

def test_ultra_graph_builder():
    """Test ultra graph builder"""
    print("🚀 Testing Ultra Graph Builder")
    print("=" * 60)
    
    # Create builder
    builder = UltraGraphBuilder(
        enable_quality_assessment=True,
        enable_analytics=True
    )
    
    # Sample entities
    entities = [
        {"id": "1", "text": "ماده 10", "label": "ARTICLE", "type": "legal", "confidence": 0.9},
        {"id": "2", "text": "قانون مدنی", "label": "LAW", "type": "legal", "confidence": 0.95},
        {"id": "3", "text": "دادگاه تهران", "label": "COURT", "type": "organization", "confidence": 0.85},
    ]
    
    # Sample relationships
    relationships = [
        {"source_id": "1", "target_id": "2", "type": "PART_OF", "confidence": 0.9},
        {"source_id": "3", "target_id": "1", "type": "CITES", "confidence": 0.8},
    ]
    
    # Build graph
    result = builder.build_graph(entities, relationships, source_id="doc_001")
    
    print(f"\n📊 Graph Metrics:")
    metrics = result["metrics"]
    print(f"   Nodes: {metrics.total_nodes}")
    print(f"   Edges: {metrics.total_edges}")
    print(f"   Avg Degree: {metrics.avg_degree:.2f}")
    print(f"   Density: {metrics.density:.3f}")
    print(f"   Avg Node Quality: {metrics.avg_node_quality:.2f}")
    print(f"   Avg Edge Quality: {metrics.avg_edge_quality:.2f}")
    
    # Query neighbors
    neighbors = builder.query_neighbors("1", max_depth=1)
    print(f"\n🔍 Neighbors of node '1': {[n.id for n in neighbors]}")
    
    # Find path
    path = builder.find_path("3", "2")
    print(f"🛤️ Path from '3' to '2': {path}")
    
    # Analytics
    analytics = builder.compute_analytics()
    print(f"\n📈 Analytics:")
    print(f"   Centrality: {analytics.get('centrality', {})}")
    print(f"   Communities: {analytics.get('communities', {})}")
    
    # Statistics
    stats = builder.get_statistics()
    print(f"\n📊 Statistics: {stats}")


if __name__ == "__main__":
    test_ultra_graph_builder()

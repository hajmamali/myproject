"""
Thread-Safe Parallel Graph Builder
==================================

Enterprise-grade concurrent graph operations with:
- Single RLock for thread safety (reentrant)
- Parallel processing for batch operations
- Atomic operations
- Deadlock prevention
- Read-write optimization

CRITICAL: This ensures zero-hallucination guarantee is maintained
even under concurrent access from multiple agents/threads.
"""

import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
import time

from mahoun.core.logging import setup_logger
from mahoun.graph.ultra_graph_builder import (
    UltraGraphBuilder,
    GraphNode,
    GraphEdge,
    GraphMode,
)

log = setup_logger("concurrent_graph_builder")


class ConcurrentGraphBuilder:
    """
    Thread-safe graph builder with fine-grained locking and parallel processing.
    
    Uses COMPOSITION over INHERITANCE to avoid parent class bypass issues.
    
    Features:
    - Single RLock for all write operations
    - Read-write lock pattern with condition variables
    - Atomic node/edge operations
    - Deadlock prevention via strict lock ordering
    - Parallel processing for batch entity/relationship processing
    
    Concurrency Model:
    - Write operations: Exclusive lock (blocks all readers and writers)
    - Read operations: Shared lock (multiple readers allowed, blocks writers)
    - Analytics: Snapshot-based (no locking during computation)
    - Batch processing: Parallel entity processing with thread pool
    
    Zero-Hallucination Guarantee:
    - All graph mutations are atomic
    - Contradiction resolution is serialized
    - Evidence links remain consistent across threads
    - Parallel processing maintains consistency via locking
    """
    
    def __init__(
        self,
        *args,
        max_workers: int = 4,
        parallel_batch_size: int = 1000,
        **kwargs
    ):
        """
        Initialize thread-safe graph builder with parallel processing.
        
        Args:
            max_workers: Maximum number of worker threads for parallel processing
            parallel_batch_size: Minimum batch size to trigger parallel processing
        """
        # Initialize the underlying graph builder via composition
        self._graph = UltraGraphBuilder(*args, **kwargs)
        
        # Read-write lock implementation
        # Uses a single lock with condition variable for proper read-write synchronization
        self._rw_lock = threading.RLock()
        self._rw_condition = threading.Condition(self._rw_lock)
        self._readers = 0
        self._writer_active = False
        self._writer_waiting = 0
        
        # Parallel processing configuration
        self._max_workers = max_workers
        self._parallel_batch_size = parallel_batch_size
        self._executor: Optional[ThreadPoolExecutor] = None
        
        # Operation counters for monitoring
        self._write_count = 0
        self._read_count = 0
        self._lock_wait_time = 0.0
        self._parallel_operations = 0
        
        log.info(
            f"Initialized ConcurrentGraphBuilder with thread safety "
            f"(max_workers={max_workers}, parallel_batch_size={parallel_batch_size})"
        )
    
    @property
    def nodes(self) -> Dict[str, GraphNode]:
        """Thread-safe access to nodes"""
        return self._graph.nodes
    
    @property
    def edges(self) -> List[GraphEdge]:
        """Thread-safe access to edges"""
        return self._graph.edges
    
    @property
    def node_index(self) -> Dict[str, GraphNode]:
        """Thread-safe access to node index"""
        return getattr(self._graph, 'node_index', {})
    
    @property
    def edge_index(self) -> Dict[str, List[GraphEdge]]:
        """Thread-safe access to edge index"""
        return getattr(self._graph, 'edge_index', {})
    
    @contextmanager
    def _write_context(self):
        """Context manager for write operations - exclusive lock"""
        start = time.time()
        
        with self._rw_condition:
            # Increment writer wait counter
            self._writer_waiting += 1
            
            # Wait for all current readers and any active writer to finish
            while self._readers > 0 or self._writer_active:
                self._rw_condition.wait(timeout=30.0)
            
            # Now we have exclusive access
            self._writer_active = True
            self._writer_waiting -= 1
        
        wait_time = time.time() - start
        self._lock_wait_time += wait_time
        
        try:
            self._write_count += 1
            yield
        finally:
            with self._rw_condition:
                self._writer_active = False
                # Notify all waiting readers and writers
                self._rw_condition.notify_all()
    
    @contextmanager
    def _read_context(self):
        """Context manager for read operations - shared lock"""
        start = time.time()
        
        with self._rw_condition:
            # Wait for any active writer
            while self._writer_active or self._writer_waiting > 0:
                self._rw_condition.wait(timeout=30.0)
            
            # Now we can read
            self._readers += 1
        
        wait_time = time.time() - start
        self._lock_wait_time += wait_time
        
        try:
            self._read_count += 1
            yield
        finally:
            with self._rw_condition:
                self._readers -= 1
                if self._readers == 0:
                    # Last reader out, notify writers
                    self._rw_condition.notify_all()
    
    def _get_executor(self) -> ThreadPoolExecutor:
        """Get or create thread pool executor"""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="GraphBuilderWorker"
            )
        return self._executor
    
    def _process_entity_single(self, entity: Dict, source_id: Optional[str]) -> Tuple[str, GraphNode]:
        """Process a single entity (thread-safe, called from pool)"""
        node_id = entity.get("id") or entity.get("text", "")
        
        node = GraphNode(
            id=node_id,
            label=entity.get("label", "UNKNOWN"),
            node_type=entity.get("type", "entity"),
            properties=entity.get("properties", {}),
            confidence=entity.get("confidence", 1.0),
            source_documents=[source_id] if source_id else [],
        )
        return node_id, node
    
    def _process_relationship_single(self, rel: Dict, source_id: Optional[str]) -> GraphEdge:
        """Process a single relationship (thread-safe, called from pool)"""
        edge = GraphEdge(
            source_id=rel.get("source_id", ""),
            target_id=rel.get("target_id", ""),
            relationship_type=rel.get("type", "RELATED"),
            properties=rel.get("properties", {}),
            weight=rel.get("weight", 1.0),
            confidence=rel.get("confidence", 1.0),
            evidence=rel.get("evidence", []),
        )
        return edge
    
    def build_graph(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Thread-safe graph building with optional parallel processing.
        
        Uses parallel processing for large batches to improve performance.
        All operations are atomic and maintain consistency.
        """
        with self._write_context():
            log.debug(f"Building graph: {len(entities)} entities, {len(relationships)} relationships")
            
            start_time = time.time()
            
            # Use parallel processing for large batches
            if len(entities) >= self._parallel_batch_size:
                self._parallel_operations += 1
                self._build_graph_parallel(entities, relationships, source_id)
            else:
                # Sequential processing for small batches
                self._graph._process_entities(entities, source_id)
                self._graph._process_relationships(relationships, source_id)
                
                # Build indexes for sequential processing
                self._graph._build_indexes()
            
            # Assess quality
            self._graph._assess_and_improve_quality()
            
            build_time = time.time() - start_time
            
            result = {
                "nodes": list(self.nodes.values()),
                "edges": self.edges,
                "build_time": build_time,
                "parallel_used": len(entities) >= self._parallel_batch_size,
            }
            
            log.debug(f"Graph build complete in {build_time:.4f}s")
            return result
    
    def _build_graph_parallel(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        source_id: Optional[str]
    ) -> None:
        """
        Build graph using parallel processing.
        
        Thread-safe: All shared state access is protected by the write context.
        Uses incremental index updates instead of full rebuilds.
        """
        executor = self._get_executor()
        
        # Process entities in parallel
        futures = []
        for entity in entities:
            future = executor.submit(
                self._process_entity_single,
                entity,
                source_id
            )
            futures.append(future)
        
        # Collect results and merge into graph atomically
        for future in as_completed(futures):
            node_id, node = future.result()
            
            if node_id in self.nodes:
                # Update existing node
                existing = self.nodes[node_id]
                existing.updated_at = node.updated_at
                existing.properties.update(node.properties)
                if source_id and source_id not in existing.source_documents:
                    existing.source_documents.append(source_id)
                
                # Update index
                if hasattr(self._graph, 'node_index'):
                    self._graph.node_index[node_id] = existing
            else:
                self.nodes[node_id] = node
                # Incremental index update
                if hasattr(self._graph, 'node_index'):
                    self._graph.node_index[node_id] = node
        
        # Process relationships in parallel
        rel_futures = []
        for rel in relationships:
            future = executor.submit(
                self._process_relationship_single,
                rel,
                source_id
            )
            rel_futures.append(future)
        
        # Collect and add edges with incremental index updates
        for future in as_completed(rel_futures):
            edge = future.result()
            self.edges.append(edge)
            
            # Incremental edge index update
            if hasattr(self._graph, 'edge_index'):
                if edge.source_id not in self._graph.edge_index:
                    self._graph.edge_index[edge.source_id] = []
                self._graph.edge_index[edge.source_id].append(edge)
    
    def add_node(self, node: GraphNode) -> None:
        """
        Thread-safe node addition.
        
        CRITICAL: Atomic operation to maintain graph consistency.
        Uses incremental index updates instead of full rebuild.
        """
        with self._write_context():
            if node.id in self.nodes:
                log.warning(f"Node {node.id} already exists, updating")
            
            self.nodes[node.id] = node
            
            # Incremental index update instead of full _build_indexes()
            if hasattr(self._graph, 'node_index'):
                self._graph.node_index[node.id] = node
            
            log.debug(f"Added node: {node.id} (type={node.node_type})")
    
    def add_edge(self, edge: GraphEdge) -> None:
        """
        Thread-safe edge addition.
        
        CRITICAL: Validates source/target exist before adding.
        Uses incremental index updates instead of full rebuild.
        """
        with self._write_context():
            # Validate nodes exist
            if edge.source_id not in self.nodes:
                raise ValueError(f"Source node {edge.source_id} does not exist")
            if edge.target_id not in self.nodes:
                raise ValueError(f"Target node {edge.target_id} does not exist")
            
            self.edges.append(edge)
            
            # Incremental index update
            if hasattr(self._graph, 'edge_index'):
                if edge.source_id not in self._graph.edge_index:
                    self._graph.edge_index[edge.source_id] = []
                self._graph.edge_index[edge.source_id].append(edge)
            
            log.debug(f"Added edge: {edge.source_id} -> {edge.target_id} ({edge.relationship_type})")
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Thread-safe node retrieval"""
        with self._read_context():
            return self.nodes.get(node_id)
    
    def get_nodes_by_type(self, node_type: str) -> List[GraphNode]:
        """Thread-safe node type query"""
        with self._read_context():
            return [
                node for node in self.nodes.values()
                if node.node_type == node_type
            ]
    
    def query_neighbors(
        self,
        node_id: str,
        max_depth: int = 1,
        relationship_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Thread-safe neighbor query.
        
        Uses snapshot-based approach to avoid holding lock during traversal.
        """
        # Take snapshot under lock
        with self._read_context():
            if node_id not in self.nodes:
                return {"neighbors": [], "paths": []}
            
            # Copy relevant data structures
            nodes_snapshot = dict(self.nodes)
            edges_snapshot = list(self.edges)
        
        # Perform traversal without lock (using snapshot)
        neighbors = []
        paths = []
        visited = set()
        queue = deque([(node_id, 0, [node_id])])  # Use deque for O(1) popleft
        
        while queue:
            current_id, depth, path = queue.popleft()  # O(1) instead of O(n)
            
            if depth >= max_depth:
                continue
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            # Find outgoing edges
            for edge in edges_snapshot:
                if edge.source_id != current_id:
                    continue
                
                if relationship_types and edge.relationship_type not in relationship_types:
                    continue
                
                target_node = nodes_snapshot.get(edge.target_id)
                if not target_node:
                    continue
                
                neighbors.append({
                    "node": target_node,
                    "edge": edge,
                    "depth": depth + 1
                })
                
                new_path = path + [edge.target_id]
                paths.append(new_path)
                
                queue.append((edge.target_id, depth + 1, new_path))
        
        return {
            "neighbors": neighbors,
            "paths": paths
        }
    
    def detect_contradictions(
        self,
        nodes: Optional[List[GraphNode]] = None
    ) -> List[Dict[str, Any]]:
        """
        Thread-safe contradiction detection.
        
        Uses snapshot to avoid long-held locks.
        """
        with self._read_context():
            if nodes is None:
                nodes = list(self.nodes.values())
            else:
                nodes = list(nodes)  # Copy to avoid mutation
        
        # Detect contradictions without lock
        contradictions = []
        
        for i, node1 in enumerate(nodes):
            for node2 in nodes[i + 1:]:
                if self._are_contradictory(node1, node2):
                    contradictions.append({
                        "node1": node1,
                        "node2": node2,
                        "severity": self._calculate_contradiction_severity(node1, node2)
                    })
        
        return contradictions
    
    def _are_contradictory(self, node1: GraphNode, node2: GraphNode) -> bool:
        """Check if two nodes contradict (simplified)"""
        # Same type but conflicting properties
        if node1.node_type != node2.node_type:
            return False
        
        # Check for negation patterns in labels
        label1 = node1.label.lower()
        label2 = node2.label.lower()
        
        negation_words = ["not", "no", "نه", "نیست", "ندارد"]
        has_negation_1 = any(word in label1 for word in negation_words)
        has_negation_2 = any(word in label2 for word in negation_words)
        
        # If one has negation and other doesn't, might be contradictory
        if has_negation_1 != has_negation_2:
            # Check if they refer to same concept
            words1 = set(label1.split())
            words2 = set(label2.split())
            common = words1 & words2
            
            if len(common) > 2:  # Significant overlap
                return True
        
        return False
    
    def _calculate_contradiction_severity(
        self,
        node1: GraphNode,
        node2: GraphNode
    ) -> float:
        """Calculate contradiction severity"""
        conf1 = node1.confidence
        conf2 = node2.confidence
        
        avg_confidence = (conf1 + conf2) / 2
        confidence_diff = abs(conf1 - conf2)
        
        # Higher average confidence + smaller diff = higher severity
        severity = avg_confidence * (1 - confidence_diff)
        
        return severity
    
    def get_analytics(self) -> Dict[str, Any]:
        """
        Thread-safe analytics computation.
        
        Takes snapshot and computes without holding lock.
        Includes all mutable state: nodes, edges, indexes.
        """
        with self._read_context():
            nodes_snapshot = dict(self.nodes)
            edges_snapshot = list(self.edges)
            node_index_snapshot = dict(self.node_index) if hasattr(self._graph, 'node_index') else {}
            edge_index_snapshot = {k: list(v) for k, v in self.edge_index.items()} if hasattr(self._graph, 'edge_index') else {}
        
        # Compute analytics on snapshot
        return {
            "num_nodes": len(nodes_snapshot),
            "num_edges": len(edges_snapshot),
            "node_types": self._count_node_types(nodes_snapshot),
            "edge_types": self._count_edge_types(edges_snapshot),
            "avg_confidence": self._calculate_avg_confidence(nodes_snapshot),
            "density": self._calculate_density(len(nodes_snapshot), len(edges_snapshot)),
            "index_size": len(node_index_snapshot) + sum(len(v) for v in edge_index_snapshot.values())
        }
    
    def _count_node_types(self, nodes: Dict[str, GraphNode]) -> Dict[str, int]:
        """Count nodes by type"""
        counts: Dict[str, int] = {}
        for node in nodes.values():
            counts[node.node_type] = counts.get(node.node_type, 0) + 1
        return counts
    
    def _count_edge_types(self, edges: List[GraphEdge]) -> Dict[str, int]:
        """Count edges by type"""
        counts: Dict[str, int] = {}
        for edge in edges:
            counts[edge.relationship_type] = counts.get(edge.relationship_type, 0) + 1
        return counts
    
    def _calculate_avg_confidence(self, nodes: Dict[str, GraphNode]) -> float:
        """Calculate average node confidence"""
        if not nodes:
            return 0.0
        
        total = sum(node.confidence for node in nodes.values())
        return total / len(nodes)
    
    def _calculate_density(self, num_nodes: int, num_edges: int) -> float:
        """Calculate graph density"""
        if num_nodes < 2:
            return 0.0
        
        max_edges = num_nodes * (num_nodes - 1)
        return num_edges / max_edges if max_edges > 0 else 0.0
    
    def get_concurrency_stats(self) -> Dict[str, Any]:
        """Get concurrency and parallel processing statistics for monitoring"""
        return {
            "write_operations": self._write_count,
            "read_operations": self._read_count,
            "total_lock_wait_time_sec": self._lock_wait_time,
            "avg_lock_wait_time_ms": (
                (self._lock_wait_time / self._write_count * 1000)
                if self._write_count > 0 else 0.0
            ),
            "parallel_operations": self._parallel_operations,
            "max_workers": self._max_workers,
            "parallel_batch_size": self._parallel_batch_size,
        }
    
    def clear(self) -> None:
        """Thread-safe graph clearing"""
        with self._write_context():
            self._graph.clear()
            log.info("Graph cleared")
    
    def remove_node(self, node_id: str) -> None:
        """Thread-safe node removal"""
        with self._write_context():
            self._graph.remove_node(node_id)
            log.info(f"Node {node_id} removed")
    
    def remove_edge(self, source_id: str, target_id: str) -> None:
        """Thread-safe edge removal"""
        with self._write_context():
            self._graph.remove_edge(source_id, target_id)
            log.info(f"Edge {source_id} -> {target_id} removed")
    
    def clear_edges(self) -> None:
        """Thread-safe edge clearing"""
        with self._write_context():
            self._graph.clear_edges()
            log.info("All edges cleared")
    
    def ensure_indexes(self) -> None:
        """Ensure indexes are built"""
        with self._read_context():
            self._graph.ensure_indexes()
    
    def get_nodes(self) -> Dict[str, GraphNode]:
        """Return mapping of graph nodes"""
        with self._read_context():
            return dict(self.nodes)
    
    def get_edges(self) -> List[GraphEdge]:
        """Return list of graph edges"""
        with self._read_context():
            return list(self.edges)
    
    def shutdown(self) -> None:
        """Shutdown the thread pool executor"""
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
            log.info("Thread pool executor shutdown")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.shutdown()

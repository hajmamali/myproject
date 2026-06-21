"""
Comprehensive tests for ConcurrentGraphBuilder
==============================================

Tests thread safety, deadlock prevention, and performance.
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from mahoun.graph.concurrent_graph_builder import ConcurrentGraphBuilder
from mahoun.graph.ultra_graph_builder import GraphNode, GraphEdge, GraphMode


class TestThreadSafety:
    """Test thread safety of concurrent operations"""
    
    @pytest.fixture
    def builder(self):
        """Create concurrent graph builder"""
        return ConcurrentGraphBuilder(mode=GraphMode.STRICT)
    
    def test_concurrent_node_additions(self, builder):
        """Test adding nodes from multiple threads"""
        num_threads = 10
        nodes_per_thread = 100
        
        def add_nodes(thread_id: int):
            for i in range(nodes_per_thread):
                node = GraphNode(
                    id=f"node_{thread_id}_{i}",
                    label=f"Node {thread_id}-{i}",
                    node_type="TestNode",
                    confidence=0.9
                )
                builder.add_node(node)
        
        # Run concurrent additions
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(add_nodes, i)
                for i in range(num_threads)
            ]
            
            for future in as_completed(futures):
                future.result()  # Raise any exceptions
        
        # Verify all nodes added
        analytics = builder.get_analytics()
        assert analytics.num_nodes == num_threads * nodes_per_thread
    
    def test_concurrent_edge_additions(self, builder):
        """Test adding edges from multiple threads"""
        # First add nodes
        for i in range(100):
            builder.add_node(GraphNode(
                id=f"node_{i}",
                label=f"Node {i}",
                node_type="TestNode"
            ))
        
        num_threads = 10
        edges_per_thread = 50
        
        def add_edges(thread_id: int):
            for i in range(edges_per_thread):
                source = f"node_{(thread_id * edges_per_thread + i) % 100}"
                target = f"node_{(thread_id * edges_per_thread + i + 1) % 100}"
                
                edge = GraphEdge(
                    source_id=source,
                    target_id=target,
                    relationship_type="CONNECTS"
                )
                builder.add_edge(edge)
        
        # Run concurrent additions
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(add_edges, i)
                for i in range(num_threads)
            ]
            
            for future in as_completed(futures):
                future.result()
        
        # Verify all edges added
        analytics = builder.get_analytics()
        assert analytics.num_edges == num_threads * edges_per_thread
    
    def test_concurrent_read_write(self, builder):
        """Test concurrent reads and writes"""
        # Add initial nodes
        for i in range(50):
            builder.add_node(GraphNode(
                id=f"node_{i}",
                label=f"Node {i}",
                node_type="TestNode"
            ))
        
        results = []
        errors = []
        
        def writer():
            try:
                for i in range(50, 100):
                    builder.add_node(GraphNode(
                        id=f"node_{i}",
                        label=f"Node {i}",
                        node_type="TestNode"
                    ))
                    time.sleep(0.001)  # Simulate work
            except Exception as e:
                errors.append(e)
        
        def reader():
            try:
                for _ in range(100):
                    analytics = builder.get_analytics()
                    results.append(analytics.num_nodes)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        # Run concurrent read/write
        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # No errors
        assert len(errors) == 0
        
        # Final count correct
        analytics = builder.get_analytics()
        assert analytics.num_nodes == 100
        
        # Reads saw increasing counts
        assert min(results) >= 50
        assert max(results) == 100
    
    def test_no_deadlock_on_nested_calls(self, builder):
        """Test that nested method calls don't deadlock"""
        # Add nodes
        for i in range(10):
            builder.add_node(GraphNode(
                id=f"node_{i}",
                label=f"Node {i}",
                node_type="TestNode"
            ))
        
        # Add edges (calls get_node internally)
        for i in range(9):
            builder.add_edge(GraphEdge(
                source_id=f"node_{i}",
                target_id=f"node_{i+1}",
                relationship_type="NEXT"
            ))
        
        # Query neighbors (nested reads)
        result = builder.query_neighbors("node_0", max_depth=3)
        
        assert len(result["neighbors"]) > 0


class TestContradictionDetection:
    """Test concurrent contradiction detection"""
    
    @pytest.fixture
    def builder(self):
        return ConcurrentGraphBuilder(mode=GraphMode.STRICT)
    
    def test_concurrent_contradiction_detection(self, builder):
        """Test detecting contradictions from multiple threads"""
        # Add contradictory nodes
        builder.add_node(GraphNode(
            id="rule1",
            label="Contract is valid",
            node_type="Rule",
            confidence=0.9
        ))
        
        builder.add_node(GraphNode(
            id="rule2",
            label="Contract is not valid",
            node_type="Rule",
            confidence=0.8
        ))
        
        results = []
        
        def detect():
            contradictions = builder.detect_contradictions()
            results.append(len(contradictions))
        
        # Run concurrent detection
        threads = [threading.Thread(target=detect) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # All threads should find same contradictions
        assert all(r == results[0] for r in results)
        assert results[0] >= 1  # At least one contradiction


class TestPerformance:
    """Test performance under load"""
    
    @pytest.fixture
    def builder(self):
        return ConcurrentGraphBuilder(mode=GraphMode.STRICT)
    
    def test_high_throughput_writes(self, builder):
        """Test high-throughput concurrent writes"""
        num_threads = 20
        nodes_per_thread = 500
        
        start_time = time.time()
        
        def add_nodes(thread_id: int):
            for i in range(nodes_per_thread):
                builder.add_node(GraphNode(
                    id=f"node_{thread_id}_{i}",
                    label=f"Node {thread_id}-{i}",
                    node_type="TestNode"
                ))
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(add_nodes, i)
                for i in range(num_threads)
            ]
            
            for future in as_completed(futures):
                future.result()
        
        elapsed = time.time() - start_time
        total_nodes = num_threads * nodes_per_thread
        throughput = total_nodes / elapsed
        
        print(f"\nThroughput: {throughput:.0f} nodes/sec")
        print(f"Total time: {elapsed:.2f}s")
        
        # Should handle at least 1000 nodes/sec
        assert throughput > 1000
        
        # Verify count
        analytics = builder.get_analytics()
        assert analytics.num_nodes == total_nodes
    
    def test_lock_contention_metrics(self, builder):
        """Test lock contention monitoring"""
        # Add nodes with contention
        def add_nodes():
            for i in range(100):
                builder.add_node(GraphNode(
                    id=f"node_{threading.get_ident()}_{i}",
                    label=f"Node {i}",
                    node_type="TestNode"
                ))
        
        threads = [threading.Thread(target=add_nodes) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Check stats
        stats = builder.get_concurrency_stats()
        
        assert stats["write_operations"] == 1000
        assert stats["total_lock_wait_time_sec"] >= 0
        assert stats["avg_lock_wait_time_ms"] >= 0
        
        print(f"\nConcurrency stats: {stats}")


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def builder(self):
        return ConcurrentGraphBuilder(mode=GraphMode.STRICT)
    
    def test_add_duplicate_nodes(self, builder):
        """Test adding duplicate nodes from multiple threads"""
        node_id = "duplicate_node"
        
        def add_node():
            builder.add_node(GraphNode(
                id=node_id,
                label="Duplicate",
                node_type="TestNode"
            ))
        
        threads = [threading.Thread(target=add_node) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have only one node (last write wins)
        node = builder.get_node(node_id)
        assert node is not None
        assert node.id == node_id
    
    def test_add_edge_with_missing_nodes(self, builder):
        """Test adding edge when nodes don't exist"""
        def add_invalid_edge():
            try:
                builder.add_edge(GraphEdge(
                    source_id="nonexistent1",
                    target_id="nonexistent2",
                    relationship_type="INVALID"
                ))
            except ValueError:
                pass  # Expected
        
        threads = [threading.Thread(target=add_invalid_edge) for _ in range(5)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # No edges should be added
        analytics = builder.get_analytics()
        assert analytics.num_edges == 0


@pytest.mark.slow
class TestStressTest:
    """Stress tests for extreme scenarios"""
    
    def test_extreme_concurrency(self):
        """Test with extreme number of threads"""
        builder = ConcurrentGraphBuilder(mode=GraphMode.STRICT)
        
        num_threads = 100
        nodes_per_thread = 100
        
        def add_nodes(thread_id: int):
            for i in range(nodes_per_thread):
                builder.add_node(GraphNode(
                    id=f"node_{thread_id}_{i}",
                    label=f"Node {thread_id}-{i}",
                    node_type="TestNode"
                ))
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(add_nodes, i)
                for i in range(num_threads)
            ]
            
            for future in as_completed(futures):
                future.result()
        
        elapsed = time.time() - start_time
        
        analytics = builder.get_analytics()
        assert analytics.num_nodes == num_threads * nodes_per_thread
        
        print(f"\nExtreme concurrency: {num_threads} threads, {elapsed:.2f}s")

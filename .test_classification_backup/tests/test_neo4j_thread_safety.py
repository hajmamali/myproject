import pytest
pytest.importorskip("neo4j")
"""
Test Neo4j Connection Thread-Safety
====================================
Tests for CRITICAL-1: Neo4j Race Condition Fix

Verifies that:
1. get_connection() returns thread-safe singleton
2. Multiple threads can safely access connection
3. No race conditions during initialization
4. Connection pooling works correctly across threads
"""

import pytest
import threading
import time
from typing import List
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test"""
    from mahoun.graph.neo4j.connection import _neo4j_singleton
    _neo4j_singleton.reset()
    yield
    _neo4j_singleton.reset()


def test_get_connection_returns_singleton():
    """Test that get_connection() returns same instance"""
    from mahoun.graph.neo4j.connection import get_connection
    
    # Mock Neo4j driver and secrets
    with patch('neo4j.GraphDatabase') as mock_gd, \
         patch('mahoun.graph.neo4j.connection.require_secret', return_value='test_password'), \
         patch('mahoun.graph.neo4j.connection.get_secret', return_value='neo4j'):
        
        mock_driver = Mock()
        mock_gd.driver.return_value = mock_driver
        
        # Get connection twice
        conn1 = get_connection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test"
        )
        conn2 = get_connection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test"
        )
        
        # Should be same instance
        assert conn1 is conn2
        
        # Driver should be created only once
        assert mock_gd.driver.call_count == 1


def test_get_connection_thread_safety():
    """Test that get_connection() is thread-safe"""
    from mahoun.graph.neo4j.connection import get_connection
    
    # Mock Neo4j driver and secrets
    with patch('neo4j.GraphDatabase') as mock_gd, \
         patch('mahoun.graph.neo4j.connection.require_secret', return_value='test_password'), \
         patch('mahoun.graph.neo4j.connection.get_secret', return_value='neo4j'):
        mock_driver = Mock()
        mock_gd.driver.return_value = mock_driver
        
        connections: List[any] = []
        errors: List[any] = []
        
        def get_conn():
            try:
                conn = get_connection(
                    uri="bolt://localhost:7687",
                    user="neo4j",
                    password="test"
                )
                connections.append(conn)
            except Exception as e:
                errors.append(e)
        
        # Create 10 threads that all try to get connection simultaneously
        threads = []
        for _ in range(10):
            t = threading.Thread(target=get_conn)
            threads.append(t)
        
        # Start all threads at once
        for t in threads:
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all connections are same instance
        assert len(connections) == 10
        first_conn = connections[0]
        for conn in connections[1:]:
            assert conn is first_conn, "Different connection instances returned"
        
        # Driver should be created only once (thread-safe initialization)
        assert mock_gd.driver.call_count == 1


def test_get_connection_race_condition_stress():
    """Stress test for race conditions during initialization"""
    from mahoun.graph.neo4j.connection import get_connection, _neo4j_singleton
    
    # Reset singleton
    _neo4j_singleton.reset()
    
    # Mock Neo4j driver with delay to simulate slow initialization
    with patch('neo4j.GraphDatabase') as mock_gd:
        mock_driver = Mock()
        
        def slow_driver_creation(*args, **kwargs):
            time.sleep(0.01)  # Simulate slow initialization
            return mock_driver
        
        mock_gd.driver.side_effect = slow_driver_creation
        
        connections: List[any] = []
        errors: List[any] = []
        
        def get_conn():
            try:
                conn = get_connection(
                    uri="bolt://localhost:7687",
                    user="neo4j",
                    password="test"
                )
                connections.append(conn)
            except Exception as e:
                errors.append(e)
        
        # Create 50 threads to maximize race condition chance
        threads = []
        for _ in range(50):
            t = threading.Thread(target=get_conn)
            threads.append(t)
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Race condition errors: {errors}"
        
        # Verify all same instance
        assert len(connections) == 50
        first_conn = connections[0]
        for conn in connections[1:]:
            assert conn is first_conn
        
        # Driver created only once despite 50 concurrent attempts
        assert mock_gd.driver.call_count == 1


def test_neo4j_connection_class_warning():
    """Test that Neo4jConnection class has thread-safety warning"""
    from mahoun.graph.neo4j.connection import Neo4jConnection
    
    # Check docstring contains warning
    docstring = Neo4jConnection.__doc__
    assert docstring is not None
    assert "thread-safe" in docstring.lower() or "threadsafe" in docstring.lower()
    assert "get_connection()" in docstring


def test_connection_pool_thread_safety():
    """Test that connection pooling works correctly across threads"""
    from mahoun.graph.neo4j.connection import get_connection
    
    # Mock Neo4j driver
    with patch('neo4j.GraphDatabase') as mock_gd:
        mock_driver = Mock()
        mock_session = Mock()
        mock_driver.session.return_value = mock_session
        mock_gd.driver.return_value = mock_driver
        
        conn = get_connection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test"
        )
        
        session_calls: List[any] = []
        errors: List[any] = []
        
        def use_session():
            try:
                with conn.session() as session:
                    session_calls.append(session)
                    time.sleep(0.001)  # Simulate work
            except Exception as e:
                errors.append(e)
        
        # Create 20 threads using sessions concurrently
        threads = []
        for _ in range(20):
            t = threading.Thread(target=use_session)
            threads.append(t)
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Session errors: {errors}"
        
        # Verify all sessions were created
        assert len(session_calls) == 20
        
        # Verify driver.session was called 20 times (one per thread)
        assert mock_driver.session.call_count == 20


def test_singleton_reset_for_testing():
    """Test that singleton can be reset for testing purposes"""
    from mahoun.graph.neo4j.connection import get_connection, _neo4j_singleton
    
    # Mock Neo4j driver
    with patch('neo4j.GraphDatabase') as mock_gd:
        mock_driver1 = Mock()
        mock_driver2 = Mock()
        mock_gd.driver.side_effect = [mock_driver1, mock_driver2]
        
        # Get first connection
        conn1 = get_connection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test"
        )
        
        # Reset singleton
        _neo4j_singleton.reset()
        
        # Get second connection
        conn2 = get_connection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test"
        )
        
        # Should be different instances after reset
        assert conn1 is not conn2
        
        # Driver should be created twice
        assert mock_gd.driver.call_count == 2


def test_get_connection_with_different_params():
    """Test that get_connection() with different params returns same instance"""
    from mahoun.graph.neo4j.connection import get_connection, _neo4j_singleton
    
    # Reset singleton
    _neo4j_singleton.reset()
    
    # Mock Neo4j driver
    with patch('neo4j.GraphDatabase') as mock_gd:
        mock_driver = Mock()
        mock_gd.driver.return_value = mock_driver
        
        # Get connection with first params
        conn1 = get_connection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test1"
        )
        
        # Get connection with different params (should return same instance)
        conn2 = get_connection(
            uri="bolt://different:7687",
            user="different",
            password="test2"
        )
        
        # Should be same instance (singleton behavior)
        assert conn1 is conn2
        
        # Driver created only once with first params
        assert mock_gd.driver.call_count == 1
        call_kwargs = mock_gd.driver.call_args[1]
        assert call_kwargs['auth'] == ('neo4j', 'test1')


def test_thread_safe_singleton_double_check_locking():
    """Test that ThreadSafeSingleton uses double-check locking correctly"""
    from mahoun.core.singleton import ThreadSafeSingleton
    
    singleton = ThreadSafeSingleton[str]("TestSingleton")
    
    call_count = 0
    
    def factory():
        nonlocal call_count
        call_count += 1
        time.sleep(0.01)  # Simulate slow creation
        return f"instance_{call_count}"
    
    instances: List[any] = []
    
    def get_instance():
        instance = singleton.get_instance(factory)
        instances.append(instance)
    
    # Create 20 threads
    threads = []
    for _ in range(20):
        t = threading.Thread(target=get_instance)
        threads.append(t)
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    # Factory should be called only once (double-check locking works)
    assert call_count == 1
    
    # All instances should be same
    assert len(instances) == 20
    first = instances[0]
    for inst in instances[1:]:
        assert inst is first


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Runtime singleton validation — hostile production auditor phase B.

Verifies:
1. get_connection() returns same instance on repeated calls (object identity)
2. Lifecycle consistency (connection survives across calls)
3. Thread safety (basic verification - single thread only for now)
"""

import sys

def test_singleton_identity():
    """Verify get_connection() returns identical instance."""
    from mahoun.graph.neo4j.connection import get_connection
    
    conn1 = get_connection()
    conn2 = get_connection()
    conn3 = get_connection()
    
    # Object identity test
    assert conn1 is conn2, f"FAIL: conn1 ({id(conn1)}) is not conn2 ({id(conn2)})"
    assert conn2 is conn3, f"FAIL: conn2 ({id(conn2)}) is not conn3 ({id(conn3)})"
    assert conn1 is conn3, f"FAIL: conn1 ({id(conn1)}) is not conn3 ({id(conn3)})"
    
    print(f"✓ Singleton identity verified: all calls return same instance (id={id(conn1)})")
    return conn1

def test_lifecycle_consistency():
    """Verify connection state is preserved across calls."""
    from mahoun.graph.neo4j.connection import get_connection
    
    conn = get_connection()
    
    # Get connection again
    conn_new = get_connection()
    
    # Verify it's the same object
    assert conn_new is conn, f"FAIL: new call returned different instance"
    
    # Verify internal state matches (driver should be same object)
    assert hasattr(conn, '_driver'), "FAIL: connection has no _driver attribute"
    assert hasattr(conn_new, '_driver'), "FAIL: new connection has no _driver attribute"
    
    # If driver is initialized, verify it's the same instance
    if conn._driver is not None and conn_new._driver is not None:
        assert conn._driver is conn_new._driver, "FAIL: drivers are different objects"
        print(f"✓ Lifecycle consistency verified: driver instance preserved (id={id(conn._driver)})")
    else:
        print(f"✓ Lifecycle consistency verified: driver not yet initialized (lazy init)")
    
    return True

def test_repeatability():
    """Run singleton test multiple times to verify repeatability."""
    from mahoun.graph.neo4j.connection import get_connection
    
    instances = []
    for i in range(10):
        instances.append(get_connection())
    
    # All must be the same object
    first_id = id(instances[0])
    for i, inst in enumerate(instances):
        assert id(inst) == first_id, f"FAIL: call {i} returned different instance"
    
    print(f"✓ Repeatability verified: 10 consecutive calls returned same instance (id={first_id})")
    return True

if __name__ == "__main__":
    print("=== Phase B: Singleton Validation ===")
    print()
    
    try:
        # Test 1: Object identity
        conn = test_singleton_identity()
        print()
        
        # Test 2: Lifecycle consistency
        test_lifecycle_consistency()
        print()
        
        # Test 3: Repeatability
        test_repeatability()
        print()
        
        print("=== Phase B: PASS ===")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n=== Phase B: FAIL ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

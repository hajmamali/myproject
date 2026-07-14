#!/usr/bin/env python3
"""
Singleton Validation Script
============================
Runtime verification that get_connection() returns the SAME object instance
across multiple calls (true singleton behavior).

Verification tests:
1. Object identity across multiple calls (id() comparison)
2. Connection pool lifecycle consistency
3. Thread-safety (multiple threads get same singleton)
"""

import sys
import os
import threading

# Add project root to path
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')

def test_singleton_identity():
    """Test 1: Verify get_connection() returns same object instance"""
    print("=" * 70)
    print("TEST 1: Singleton Identity Verification")
    print("=" * 70)
    
    from mahoun.graph.neo4j.connection import get_connection
    
    # Call get_connection() multiple times
    conn1 = get_connection()
    conn2 = get_connection()
    conn3 = get_connection()
    
    # Get Python object IDs
    id1 = id(conn1)
    id2 = id(conn2)
    id3 = id(conn3)
    
    print(f"conn1 object ID: {id1}")
    print(f"conn2 object ID: {id2}")
    print(f"conn3 object ID: {id3}")
    print()
    
    # Verify ALL are identical
    if id1 == id2 == id3:
        print("✅ PASS: All calls return the SAME singleton instance")
        print(f"   Singleton object ID: {id1}")
        return True
    else:
        print("❌ FAIL: get_connection() returns DIFFERENT instances!")
        print("   This is a P0 singleton violation.")
        return False


def test_lifecycle_consistency():
    """Test 2: Verify singleton maintains consistent state"""
    print("\n" + "=" * 70)
    print("TEST 2: Lifecycle Consistency")
    print("=" * 70)
    
    from mahoun.graph.neo4j.connection import get_connection
    
    conn = get_connection()
    
    # Verify internal state is preserved across calls
    print(f"Connection URI: {conn.uri if hasattr(conn, 'uri') else 'N/A'}")
    print(f"Has driver: {hasattr(conn, '_driver')}")
    print(f"Driver initialized: {getattr(conn, '_driver', None) is not None}")
    
    # Get connection again and verify state consistency
    conn2 = get_connection()
    driver_state_1 = getattr(conn, '_driver', None) is not None
    driver_state_2 = getattr(conn2, '_driver', None) is not None
    
    if driver_state_1 == driver_state_2:
        print(f"✅ PASS: Driver state consistent across calls (initialized: {driver_state_1})")
        return True
    else:
        print("❌ FAIL: Driver state INCONSISTENT across calls")
        return False


def test_thread_safety():
    """Test 3: Verify singleton is thread-safe"""
    print("\n" + "=" * 70)
    print("TEST 3: Thread Safety Verification")
    print("=" * 70)
    
    from mahoun.graph.neo4j.connection import get_connection
    
    results = []
    
    def get_connection_in_thread():
        conn = get_connection()
        results.append(id(conn))
    
    # Create 10 threads that all call get_connection()
    threads = []
    for i in range(10):
        t = threading.Thread(target=get_connection_in_thread)
        threads.append(t)
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # Verify all threads got the SAME singleton
    unique_ids = set(results)
    
    print(f"Threads spawned: 10")
    print(f"Unique object IDs returned: {len(unique_ids)}")
    print(f"Object IDs: {unique_ids}")
    print()
    
    if len(unique_ids) == 1:
        print("✅ PASS: All threads received the SAME singleton instance")
        print(f"   Singleton object ID: {list(unique_ids)[0]}")
        return True
    else:
        print("❌ FAIL: Threads received DIFFERENT instances!")
        print("   This indicates a thread-safety violation.")
        return False


def main():
    """Run all singleton validation tests"""
    print("\n" + "=" * 70)
    print("PHASE B: SINGLETON VALIDATION")
    print("=" * 70)
    print()
    
    # Set minimal environment to avoid connecting to actual Neo4j
    os.environ['ENABLE_NEO4J'] = 'false'
    os.environ['MAHOUN_ENV'] = 'test'
    
    results = []
    
    try:
        results.append(("Identity Test", test_singleton_identity()))
        results.append(("Lifecycle Test", test_lifecycle_consistency()))
        results.append(("Thread Safety Test", test_thread_safety()))
    except Exception as e:
        print(f"\n❌ CRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 70)
    print("SINGLETON VALIDATION SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 VERDICT: Singleton implementation is CORRECT")
        print("   get_connection() returns a true singleton with thread safety.")
        return True
    else:
        print("⚠️  VERDICT: Singleton implementation has VIOLATIONS")
        print("   Production deployment is NOT SAFE until fixed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

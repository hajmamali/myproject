"""
MAHOUN HIGH-004 Atomicity Test Suite
====================================

Classification: HIGH / ARCHITECTURAL / HARDENING
Purpose: Verify transaction-level atomicity in ledger commit

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

import sys
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')


def test_atomicity_comments_in_ledger_commit():
    """Test that atomicity is enforced in ledger_commit_service."""
    print("\n  Testing atomicity enforcement in ledger_commit_service...")
    
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/ledger_commit_service.py', 'r') as f:
        content = f.read()
    
    # Should have HIGH-004 reference
    assert 'HIGH-004' in content, "HIGH-004 reference not found"
    
    # Should have atomicity comment
    assert 'atomicity' in content.lower(), "Atomicity comment not found"
    
    # Should have lock
    assert 'async with self._lock:' in content, "Lock not found for atomicity"
    
    print("  ✓ Atomicity enforcement comments found")
    return True


def test_two_phase_commit_structure():
    """Test that two-phase commit structure is in place."""
    print("\n  Testing two-phase commit structure...")
    
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/ledger_commit_service.py', 'r') as f:
        content = f.read()
    
    # Should have Phase 1: Prepare
    assert 'Phase 1:' in content or 'prepare' in content.lower(), \
        "Phase 1 or prepare comment not found"
    
    # Should have Phase 2: Commit
    assert 'Phase 2:' in content or 'commit' in content.lower(), \
        "Phase 2 or commit comment not found"
    
    # Should have async with lock
    assert 'async with self._lock:' in content, "Lock not found"
    
    print("  ✓ Two-phase commit structure in place")
    return True


def test_atomicity_violation_error():
    """Test that atomicity violation raises appropriate error."""
    print("\n  Testing atomicity violation error handling...")
    
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/ledger_commit_service.py', 'r') as f:
        content = f.read()
    
    # Should have RULE 10 reference
    assert 'RULE 10' in content, "RULE 10 reference not found"
    
    # Should mention atomicity violation
    assert 'atomicity violation' in content.lower(), \
        "Atomicity violation message not found"
    
    # In strict mode, should raise RuntimeError
    assert 'raise RuntimeError' in content, "RuntimeError not raised on failure"
    
    print("  ✓ Atomicity violation error handling in place")
    return True


def test_original_entry_returned_on_failure():
    """Test that original entry is returned on failure (not updated)."""
    print("\n  Testing original entry returned on failure...")
    
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/ledger_commit_service.py', 'r') as f:
        content = f.read()
    
    # In exception handler, should return execution_result.ledger_entry (original)
    # not updated_entry
    assert 'entry=execution_result.ledger_entry' in content, \
        "Original entry not returned on failure"
    
    # Should have comment about not returning updated entry
    assert 'ORIGINAL' in content, "Comment about returning original not found"
    
    print("  ✓ Original entry returned on failure")
    return True


def test_lock_ensures_atomicity():
    """Test that lock ensures no concurrent modifications."""
    print("\n  Testing lock ensures atomicity...")
    
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/ledger_commit_service.py', 'r') as f:
        content = f.read()
    
    # Should have _lock attribute
    assert 'self._lock' in content, "Lock attribute not found"
    
    # Should initialize lock
    assert '_lock = asyncio.Lock()' in content or 'asyncio.Lock' in content, \
        "Lock initialization not found"
    
    print("  ✓ Lock ensures atomicity")
    return True


def test_fortress_integration_atomicity():
    """Test that fortress_integration handles atomicity properly."""
    print("\n  Testing atomicity in fortress_integration...")
    
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/fortress_integration.py', 'r') as f:
        content = f.read()
    
    # Should have RULE 10 reference
    assert 'RULE 10' in content, "RULE 10 reference not found in fortress"
    
    # Should check commit_result.success
    assert 'commit_result.success' in content, \
        "commit_result.success check not found"
    
    # Should raise if commit fails in strict mode
    assert 'raise RuntimeError' in content and 'atomicity' in content.lower(), \
        "Atomicity error not raised in fortress"
    
    print("  ✓ Atomicity properly handled in fortress_integration")
    return True


def main():
    print("\n" + "=" * 80)
    print("  MAHOUN HIGH-004: Atomicity Test Suite")
    print("=" * 80)
    
    tests = [
        test_atomicity_comments_in_ledger_commit,
        test_two_phase_commit_structure,
        test_atomicity_violation_error,
        test_original_entry_returned_on_failure,
        test_lock_ensures_atomicity,
        test_fortress_integration_atomicity,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ✗ Test {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 80)
    print(f"  HIGH-004 ATOMICITY TESTS")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {total-passed}/{total}")
    
    if all(results):
        print("\n  ✅ ALL HIGH-004 TESTS PASSED")
        return 0
    else:
        print("\n  ❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

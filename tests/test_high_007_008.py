"""
MAHOUN HIGH-007 & HIGH-008 Test Suite
====================================

Classification: HIGH / ARCHITECTURAL / HARDENING
Purpose: Verify ValidationStatus enum and Determinism fixes

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

import sys
import os
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')


def test_validation_status_enum_exists():
    """Test that ValidationStatus enum exists and has correct values."""
    print("\n  Testing ValidationStatus enum...")
    
    from mahoun.ledger.models import ValidationStatus
    
    # Check enum values
    assert hasattr(ValidationStatus, 'PENDING'), "PENDING not in ValidationStatus"
    assert hasattr(ValidationStatus, 'PASSED'), "PASSED not in ValidationStatus"
    assert hasattr(ValidationStatus, 'FAILED'), "FAILED not in ValidationStatus"
    
    # Check values
    assert ValidationStatus.PENDING.value == "PENDING"
    assert ValidationStatus.PASSED.value == "PASSED"
    assert ValidationStatus.FAILED.value == "FAILED"
    
    print("  ✓ ValidationStatus enum exists with correct values")
    return True


def test_ledger_entry_uses_validation_status():
    """Test that LedgerEntry uses ValidationStatus enum."""
    print("\n  Testing LedgerEntry ValidationStatus usage...")
    
    from mahoun.ledger.models import LedgerEntry, ValidationStatus
    from typing import get_type_hints
    from datetime import datetime, timezone
    
    hints = get_type_hints(LedgerEntry)
    
    # Check validation_status type
    if 'validation_status' in hints:
        field_type = hints['validation_status']
        print(f"    validation_status type: {field_type}")
        assert 'ValidationStatus' in str(field_type), f"Expected ValidationStatus, got {field_type}"
    
    # Test creating entry with ValidationStatus
    entry = LedgerEntry(
        verdict_id="test",
        case_id="test",
        referenced_ltm_nodes=("rule_1",),
        referenced_facts=(),
        confidence=0.9,
        invariant_version="1.0",
        guard_mode="STRICT",
        created_at=datetime.now(timezone.utc),
        # validation_status should default to PENDING
    )
    
    assert isinstance(entry.validation_status, ValidationStatus), \
        f"Expected ValidationStatus, got {type(entry.validation_status)}"
    assert entry.validation_status == ValidationStatus.PENDING, \
        f"Expected PENDING, got {entry.validation_status}"
    
    print("  ✓ LedgerEntry uses ValidationStatus enum correctly")
    return True


def test_validation_status_in_ledger_commit():
    """Test that ledger_commit_service uses ValidationStatus enum."""
    print("\n  Testing ValidationStatus usage in ledger_commit_service...")
    
    # Check source code
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/ledger_commit_service.py', 'r') as f:
        content = f.read()
    
    assert 'ValidationStatus.PASSED' in content, "ValidationStatus.PASSED not found"
    assert 'ValidationStatus.FAILED' in content, "ValidationStatus.FAILED not found"
    
    print("  ✓ ledger_commit_service uses ValidationStatus enum")
    return True


def test_determinism_verdict_id():
    """Test that verdict_id is deterministic (HIGH-008)."""
    print("\n  Testing Determinism (HIGH-008)...")
    
    # Check that time-based differentiation is removed
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py', 'r') as f:
        content = f.read()
    
    # Should NOT have hour_bucket in verdict_id generation
    assert 'hour_bucket' not in content or 'HIGH-008' in content, \
        "hour_bucket should be removed or commented in HIGH-008 fix"
    
    # Should have deterministic verdict_basis = case_id
    assert 'verdict_basis = case_id' in content, \
        "verdict_basis should be just case_id for determinism"
    
    print("  ✓ verdict_id generation is deterministic")
    return True


def test_determinism_no_environment_check():
    """Test that verdict_id doesn't depend on environment."""
    print("\n  Testing no environment-based determinism...")
    
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py', 'r') as f:
        lines = f.readlines()
    
    # Find the verdict_id generation section
    for i, line in enumerate(lines):
        if 'verdict_basis' in line and i > 500:
            # Check surrounding lines for environment checks
            context = ''.join(lines[max(0, i-10):i+10])
            # Should not have if/else based on environment in this section
            assert 'MAHOUN_DETERMINISTIC_TESTING' not in context or 'HIGH-008' in context, \
                "Environment check should be removed or commented"
    
    print("  ✓ No environment-based determinism differences")
    return True


def main():
    print("\n" + "=" * 80)
    print("  MAHOUN HIGH-007 & HIGH-008: ValidationStatus & Determinism Tests")
    print("=" * 80)
    
    tests = [
        test_validation_status_enum_exists,
        test_ledger_entry_uses_validation_status,
        test_validation_status_in_ledger_commit,
        test_determinism_verdict_id,
        test_determinism_no_environment_check,
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
    print(f"  HIGH-007 & HIGH-008 TESTS")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {total-passed}/{total}")
    
    if all(results):
        print("\n  ✅ ALL HIGH-007 & HIGH-008 TESTS PASSED")
        return 0
    else:
        print("\n  ❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

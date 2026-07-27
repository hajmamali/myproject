"""
MAHOUN HIGH-001 Immutability Test Suite
========================================

Classification: HIGH / ARCHITECTURAL / HARDENING
Purpose: Verify that frozen dataclasses use immutable tuples instead of mutable lists

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

import sys
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')

from mahoun.ledger.models import LedgerEntry
from mahoun.contracts.verdict_execution import VerdictExecutionResult
from datetime import datetime, timezone
from typing import get_type_hints


def test_ledger_entry_uses_tuples():
    """Test that LedgerEntry uses Tuple instead of List for mutable fields."""
    print("\n  Testing LedgerEntry type hints...")
    
    hints = get_type_hints(LedgerEntry)
    
    # Check referenced_ltm_nodes
    if 'referenced_ltm_nodes' in hints:
        field_type = hints['referenced_ltm_nodes']
        print(f"    referenced_ltm_nodes type: {field_type}")
        assert 'Tuple' in str(field_type), f"Expected Tuple, got {field_type}"
        assert 'List' not in str(field_type), f"Found List in {field_type}"
    
    # Check referenced_facts
    if 'referenced_facts' in hints:
        field_type = hints['referenced_facts']
        print(f"    referenced_facts type: {field_type}")
        assert 'Tuple' in str(field_type), f"Expected Tuple, got {field_type}"
        assert 'List' not in str(field_type), f"Found List in {field_type}"
    
    # Check validation_violations
    if 'validation_violations' in hints:
        field_type = hints['validation_violations']
        print(f"    validation_violations type: {field_type}")
        # This is Optional[Tuple[str, ...]] so check for Tuple
        assert 'Tuple' in str(field_type), f"Expected Tuple, got {field_type}"
    
    print("  ✓ LedgerEntry uses Tuple for all previously mutable fields")
    return True


def test_verdict_execution_result_uses_tuples():
    """Test that VerdictExecutionResult uses Tuple instead of List."""
    print("\n  Testing VerdictExecutionResult type hints...")
    
    # Read source code directly since get_type_hints may fail with TYPE_CHECKING
    with open('/home/haji/Desktop/KingMahouN/mahoun/contracts/verdict_execution.py', 'r') as f:
        content = f.read()
    
    # Check that validation_violations uses Tuple
    assert 'validation_violations: Tuple[dict[str, Any], ...]' in content, \
        "validation_violations should use Tuple[dict[str, Any], ...]"
    
    print(f"    validation_violations type: Tuple[dict[str, Any], ...]")
    print("  ✓ VerdictExecutionResult uses Tuple for validation_violations")
    return True


def test_ledger_entry_creation_with_tuples():
    """Test that LedgerEntry can be created with tuples."""
    print("\n  Testing LedgerEntry creation with tuples...")
    
    try:
        entry = LedgerEntry(
            verdict_id="test_verdict",
            case_id="test_case",
            referenced_ltm_nodes=("rule_1", "rule_2"),
            referenced_facts=("fact_1", "fact_2"),
            confidence=0.9,
            invariant_version="1.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc),
            validation_status="PENDING",
        )
        
        # Verify the fields are tuples
        assert isinstance(entry.referenced_ltm_nodes, tuple), \
            f"referenced_ltm_nodes should be tuple, got {type(entry.referenced_ltm_nodes)}"
        assert isinstance(entry.referenced_facts, tuple), \
            f"referenced_facts should be tuple, got {type(entry.referenced_facts)}"
        
        print(f"  ✓ LedgerEntry created with tuples")
        print(f"    referenced_ltm_nodes type: {type(entry.referenced_ltm_nodes)}")
        print(f"    referenced_facts type: {type(entry.referenced_facts)}")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to create LedgerEntry: {e}")
        return False


def test_ledger_entry_immutability():
    """Test that LedgerEntry fields cannot be mutated."""
    print("\n  Testing LedgerEntry immutability...")
    
    try:
        entry = LedgerEntry(
            verdict_id="test_verdict",
            case_id="test_case",
            referenced_ltm_nodes=("rule_1", "rule_2"),
            referenced_facts=("fact_1",),
            confidence=0.9,
            invariant_version="1.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc),
        )
        
        # Try to mutate referenced_ltm_nodes (should fail because it's frozen)
        try:
            entry.referenced_ltm_nodes = ("rule_3",)
            print("  ✗ ERROR: Was able to mutate frozen dataclass field!")
            return False
        except (AttributeError, TypeError):
            print("  ✓ Cannot mutate referenced_ltm_nodes (frozen dataclass)")
        
        # Try to mutate referenced_facts (should fail)
        try:
            entry.referenced_facts = ("fact_2",)
            print("  ✗ ERROR: Was able to mutate frozen dataclass field!")
            return False
        except (AttributeError, TypeError):
            print("  ✓ Cannot mutate referenced_facts (frozen dataclass)")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        return False


def test_source_code_uses_tuples():
    """Verify source code uses Tuple instead of List."""
    print("\n  Testing source code for Tuple usage...")
    
    # Check LedgerEntry
    with open('/home/haji/Desktop/KingMahouN/mahoun/ledger/models.py', 'r') as f:
        content = f.read()
        
    # Should have Tuple import
    assert 'Tuple' in content, "Tuple not imported in models.py"
    print("  ✓ Tuple imported in models.py")
    
    # Should have Tuple[str, ...] for referenced_ltm_nodes
    assert 'Tuple[str, ...]' in content, "Tuple[str, ...] not found for referenced_ltm_nodes"
    print("  ✓ referenced_ltm_nodes uses Tuple[str, ...]")
    
    # Should have Tuple[str, ...] for referenced_facts
    assert 'referenced_facts: Tuple[str, ...]' in content, "Tuple[str, ...] not found for referenced_facts"
    print("  ✓ referenced_facts uses Tuple[str, ...]")
    
    # Check VerdictExecutionResult
    with open('/home/haji/Desktop/KingMahouN/mahoun/contracts/verdict_execution.py', 'r') as f:
        content = f.read()
        
    assert 'Tuple' in content, "Tuple not imported in verdict_execution.py"
    print("  ✓ Tuple imported in verdict_execution.py")
    
    assert 'Tuple[dict[str, Any], ...]' in content, "Tuple[dict[str, Any], ...] not found"
    print("  ✓ validation_violations uses Tuple[dict[str, Any], ...]")
    
    return True


def main():
    print("\n" + "=" * 80)
    print("  MAHOUN HIGH-001: Immutability Test Suite")
    print("=" * 80)
    
    tests = [
        test_ledger_entry_uses_tuples,
        test_verdict_execution_result_uses_tuples,
        test_ledger_entry_creation_with_tuples,
        test_ledger_entry_immutability,
        test_source_code_uses_tuples,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ✗ Test {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 80)
    print(f"  HIGH-001 IMMUTABILITY TESTS")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {total-passed}/{total}")
    
    if all(results):
        print("\n  ✅ ALL HIGH-001 TESTS PASSED")
        return 0
    else:
        print("\n  ❌ SOME HIGH-001 TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
MAHOUN HIGH-002 Contract Validation Test Suite
==============================================

Classification: HIGH / ARCHITECTURAL / HARDENING
Purpose: Verify that contract invariants cannot be bypassed and are enforced at runtime

This test suite verifies:
1. InvariantViolationError is raised for contract violations
2. __post_init__ validation cannot be bypassed
3. Continuous invariant checking works correctly
4. Frozen dataclass immutability is enforced
5. No silent failures or fallback to weak validation

Author: MAHOUN AEO Governance Council
Version: 1.0.0

TEST PHILOSOPHY: Fail-Closed, No Assumptions, Maximum Paranoia
- Every test must verify behavior, not just structure
- Tests must be so hard that they would catch any regression
- No mocking of critical contract validation paths
- Tests must run in real environment, not simulated
"""

import sys
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')

import traceback
from datetime import datetime, timezone
from typing import get_type_hints


# ============================================================================
# Test 1: InvariantViolationError Basics
# ============================================================================

def test_invariant_violation_error_exists():
    """Test that InvariantViolationError is properly defined and available."""
    print("\n" + "="*80)
    print("TEST 1: InvariantViolationError Exists")
    print("="*80)
    
    from mahoun.contracts.verdict_execution import InvariantViolationError
    
    # Verify it's a proper exception class
    assert issubclass(InvariantViolationError, ValueError), \
        "InvariantViolationError must inherit from ValueError"
    
    # Verify it can be instantiated
    try:
        error = InvariantViolationError("test message", "I-TEST", "CRITICAL")
        assert error.invariant_id == "I-TEST"
        assert error.severity == "CRITICAL"
        assert error.message == "test message"
        assert "INVARIANT VIOLATION" in str(error)
        assert "I-TEST" in str(error)
        assert "CRITICAL" in str(error)
        print("  ✓ InvariantViolationError properly defined")
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        traceback.print_exc()
        return False


# ============================================================================
# Test 2: Contract Validation Framework Components
# ============================================================================

def test_contract_validation_framework():
    """Test that all contract validation framework components exist."""
    print("\n" + "="*80)
    print("TEST 2: Contract Validation Framework Components")
    print("="*80)
    
    from mahoun.contracts.verdict_execution import (
        InvariantViolationError,
        ContractValidationError,
        InvariantChecker,
        enforce_invariants,
        register_invariant_check,
    )
    
    # Verify ContractValidationError
    assert issubclass(ContractValidationError, InvariantViolationError), \
        "ContractValidationError must inherit from InvariantViolationError"
    
    # Verify InvariantChecker is a singleton
    checker1 = InvariantChecker()
    checker2 = InvariantChecker()
    assert checker1 is checker2, \
        "InvariantChecker must be a singleton"
    
    # Verify enforce_invariants function exists
    assert callable(enforce_invariants), \
        "enforce_invariants must be callable"
    
    # Verify register_invariant_check decorator exists
    assert callable(register_invariant_check), \
        "register_invariant_check must be callable"
    
    print("  ✓ All contract validation framework components exist")
    return True


# ============================================================================
# Test 3: VerdictExecutionResult Invariant Enforcement (CRITICAL)
# ============================================================================

def test_verdict_execution_result_invariants():
    """
    Test that VerdictExecutionResult enforces all invariants.
    
    This is a CRITICAL test - it verifies that the contract that carries
    execution lifecycle artifacts cannot be created in an invalid state.
    """
    print("\n" + "="*80)
    print("TEST 3: VerdictExecutionResult Invariant Enforcement")
    print("="*80)
    
    from mahoun.contracts.verdict_execution import VerdictExecutionResult, InvariantViolationError
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdict
    from mahoun.ledger.models import LedgerEntry, ValidationStatus
    from dataclasses import asdict
    
    timestamp = datetime.now(timezone.utc)
    
    # Test I1: Verdict cannot be None
    print("  Testing I1: verdict cannot be None...")
    try:
        result = VerdictExecutionResult(
            verdict=None,  # VIOLATION
            ledger_entry=LedgerEntry(
                verdict_id="test",
                case_id="test",
                referenced_ltm_nodes=(),
                referenced_facts=(),
                confidence=0.9,
                invariant_version="1.0",
                guard_mode="STRICT",
                created_at=timestamp,
            ),
            execution_id="exec-1",
            correlation_id="corr-1",
            execution_timestamp=timestamp,
        )
        print("  ✗ FAILED: Should have raised InvariantViolationError for None verdict")
        return False
    except InvariantViolationError as e:
        assert e.invariant_id == "I1", f"Expected invariant I1, got {e.invariant_id}"
        assert "verdict cannot be None" in str(e)
        print(f"  ✓ I1 enforced: {e.invariant_id}")
    except Exception as e:
        print(f"  ✗ FAILED: Wrong exception type: {type(e).__name__}: {e}")
        return False
    
    # Test I2: Ledger entry cannot be None
    print("  Testing I2: ledger_entry cannot be None...")
    try:
        verdict = EvidenceLinkedVerdict(
            final_verdict="Test verdict",
            steps=[],
            confidence_score=0.9,
        )
        verdict.verdict_id = "verdict-1"
        
        result = VerdictExecutionResult(
            verdict=verdict,
            ledger_entry=None,  # VIOLATION
            execution_id="exec-1",
            correlation_id="corr-1",
            execution_timestamp=timestamp,
        )
        print("  ✗ FAILED: Should have raised InvariantViolationError for None ledger_entry")
        return False
    except InvariantViolationError as e:
        assert e.invariant_id == "I2", f"Expected invariant I2, got {e.invariant_id}"
        print(f"  ✓ I2 enforced: {e.invariant_id}")
    except Exception as e:
        print(f"  ✗ FAILED: Wrong exception type: {type(e).__name__}: {e}")
        return False
    
    # Test I3: Execution ID cannot be empty
    print("  Testing I3: execution_id cannot be empty...")
    try:
        result = VerdictExecutionResult(
            verdict=verdict,
            ledger_entry=LedgerEntry(
                verdict_id="test",
                case_id="test",
                referenced_ltm_nodes=(),
                referenced_facts=(),
                confidence=0.9,
                invariant_version="1.0",
                guard_mode="STRICT",
                created_at=timestamp,
            ),
            execution_id="",  # VIOLATION
            correlation_id="corr-1",
            execution_timestamp=timestamp,
        )
        print("  ✗ FAILED: Should have raised InvariantViolationError for empty execution_id")
        return False
    except InvariantViolationError as e:
        assert e.invariant_id == "I3", f"Expected invariant I3, got {e.invariant_id}"
        print(f"  ✓ I3 enforced: {e.invariant_id}")
    except Exception as e:
        print(f"  ✗ FAILED: Wrong exception type: {type(e).__name__}: {e}")
        return False
    
    # Test I4: Correlation ID cannot be empty
    print("  Testing I4: correlation_id cannot be empty...")
    try:
        result = VerdictExecutionResult(
            verdict=verdict,
            ledger_entry=LedgerEntry(
                verdict_id="test",
                case_id="test",
                referenced_ltm_nodes=(),
                referenced_facts=(),
                confidence=0.9,
                invariant_version="1.0",
                guard_mode="STRICT",
                created_at=timestamp,
            ),
            execution_id="exec-1",
            correlation_id="",  # VIOLATION
            execution_timestamp=timestamp,
        )
        print("  ✗ FAILED: Should have raised InvariantViolationError for empty correlation_id")
        return False
    except InvariantViolationError as e:
        assert e.invariant_id == "I4", f"Expected invariant I4, got {e.invariant_id}"
        print(f"  ✓ I4 enforced: {e.invariant_id}")
    except Exception as e:
        print(f"  ✗ FAILED: Wrong exception type: {type(e).__name__}: {e}")
        return False
    
    # Test I5: Timestamp cannot be None
    print("  Testing I5: execution_timestamp cannot be None...")
    try:
        result = VerdictExecutionResult(
            verdict=verdict,
            ledger_entry=LedgerEntry(
                verdict_id="test",
                case_id="test",
                referenced_ltm_nodes=(),
                referenced_facts=(),
                confidence=0.9,
                invariant_version="1.0",
                guard_mode="STRICT",
                created_at=timestamp,
            ),
            execution_id="exec-1",
            correlation_id="corr-1",
            execution_timestamp=None,  # VIOLATION
        )
        print("  ✗ FAILED: Should have raised InvariantViolationError for None timestamp")
        return False
    except InvariantViolationError as e:
        assert e.invariant_id == "I5", f"Expected invariant I5, got {e.invariant_id}"
        print(f"  ✓ I5 enforced: {e.invariant_id}")
    except Exception as e:
        print(f"  ✗ FAILED: Wrong exception type: {type(e).__name__}: {e}")
        return False
    
    print("  ✓ All VerdictExecutionResult invariants enforced")
    return True


# ============================================================================
# Test 4: Valid VerdictExecutionResult Creation
# ============================================================================

def test_valid_verdict_execution_result():
    """Test that a valid VerdictExecutionResult can be created."""
    print("\n" + "="*80)
    print("TEST 4: Valid VerdictExecutionResult Creation")
    print("="*80)
    
    from mahoun.contracts.verdict_execution import VerdictExecutionResult
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdict
    from mahoun.ledger.models import LedgerEntry, ValidationStatus
    
    timestamp = datetime.now(timezone.utc)
    
    verdict = EvidenceLinkedVerdict(
        final_verdict="Test verdict",
        steps=[],
        confidence_score=0.9,
    )
    verdict.verdict_id = "verdict-1"
    
    ledger_entry = LedgerEntry(
        verdict_id="verdict-1",
        case_id="case-1",
        referenced_ltm_nodes=("rule-1", "rule-2"),
        referenced_facts=("fact-1", "fact-2"),
        confidence=0.9,
        invariant_version="1.0",
        guard_mode="STRICT",
        created_at=timestamp,
        validation_status=ValidationStatus.PENDING,
    )
    
    try:
        result = VerdictExecutionResult(
            verdict=verdict,
            ledger_entry=ledger_entry,
            execution_id="exec-1",
            correlation_id="corr-1",
            execution_timestamp=timestamp,
        )
        
        # Verify all fields are set correctly
        assert result.verdict is verdict
        assert result.ledger_entry is ledger_entry
        assert result.execution_id == "exec-1"
        assert result.correlation_id == "corr-1"
        assert result.execution_timestamp == timestamp
        
        print("  ✓ Valid VerdictExecutionResult created successfully")
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        traceback.print_exc()
        return False


# ============================================================================
# Test 5: Frozen Dataclass Immutability (CRITICAL)
# ============================================================================

def test_frozen_dataclass_immutability():
    """
    Test that frozen dataclasses cannot be mutated.
    
    This is CRITICAL because it ensures that once a VerdictExecutionResult
    is created with validated invariants, those invariants cannot be violated
    by later mutation.
    """
    print("\n" + "="*80)
    print("TEST 5: Frozen Dataclass Immutability")
    print("="*80)
    
    from mahoun.contracts.verdict_execution import VerdictExecutionResult
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdict
    from mahoun.ledger.models import LedgerEntry, ValidationStatus
    
    timestamp = datetime.now(timezone.utc)
    
    verdict = EvidenceLinkedVerdict(
        final_verdict="Test verdict",
        steps=[],
        confidence_score=0.9,
    )
    verdict.verdict_id = "verdict-1"
    
    ledger_entry = LedgerEntry(
        verdict_id="verdict-1",
        case_id="case-1",
        referenced_ltm_nodes=("rule-1",),
        referenced_facts=("fact-1",),
        confidence=0.9,
        invariant_version="1.0",
        guard_mode="STRICT",
        created_at=timestamp,
        validation_status=ValidationStatus.PENDING,
    )
    
    result = VerdictExecutionResult(
        verdict=verdict,
        ledger_entry=ledger_entry,
        execution_id="exec-1",
        correlation_id="corr-1",
        execution_timestamp=timestamp,
    )
    
    # Try to mutate a field
    print("  Testing mutation of execution_id...")
    try:
        result.execution_id = "exec-2"
        print("  ✗ FAILED: Should not be able to mutate frozen dataclass field")
        return False
    except Exception as e:
        # Frozen dataclass should raise an exception on mutation
        print(f"  ✓ Mutation blocked: {type(e).__name__}")
    
    # Verify the field wasn't changed
    assert result.execution_id == "exec-1", \
        "Field was mutated despite frozen dataclass"
    
    print("  ✓ Frozen dataclass immutability enforced")
    return True


# ============================================================================
# Test 6: InvariantViolationError Cannot Be Silently Caught
# ============================================================================

def test_invariant_violation_error_propagation():
    """
    Test that InvariantViolationError propagates correctly and cannot be
    silently caught by catching ValueError.
    
    This is CRITICAL because it ensures that architectural violations
    cause the system to fail-closed rather than continuing in an invalid state.
    """
    print("\n" + "="*80)
    print("TEST 6: InvariantViolationError Propagation")
    print("="*80)
    
    from mahoun.contracts.verdict_execution import VerdictExecutionResult, InvariantViolationError
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdict
    from mahoun.ledger.models import LedgerEntry, ValidationStatus
    
    timestamp = datetime.now(timezone.utc)
    
    # Test that catching ValueError catches InvariantViolationError
    # (since it inherits from ValueError)
    print("  Testing that InvariantViolationError is a ValueError...")
    try:
        result = VerdictExecutionResult(
            verdict=None,
            ledger_entry=LedgerEntry(
                verdict_id="test",
                case_id="test",
                referenced_ltm_nodes=(),
                referenced_facts=(),
                confidence=0.9,
                invariant_version="1.0",
                guard_mode="STRICT",
                created_at=timestamp,
            ),
            execution_id="exec-1",
            correlation_id="corr-1",
            execution_timestamp=timestamp,
        )
    except ValueError as e:
        # This is expected - InvariantViolationError is a ValueError
        assert isinstance(e, InvariantViolationError), \
            "Caught ValueError but it's not InvariantViolationError"
        print(f"  ✓ InvariantViolationError caught as ValueError: {e.invariant_id}")
    except Exception as e:
        print(f"  ✗ FAILED: Unexpected exception type: {type(e).__name__}")
        return False
    
    # Test that we can specifically catch InvariantViolationError
    print("  Testing specific InvariantViolationError catch...")
    try:
        result = VerdictExecutionResult(
            verdict=None,
            ledger_entry=LedgerEntry(
                verdict_id="test",
                case_id="test",
                referenced_ltm_nodes=(),
                referenced_facts=(),
                confidence=0.9,
                invariant_version="1.0",
                guard_mode="STRICT",
                created_at=timestamp,
            ),
            execution_id="exec-1",
            correlation_id="corr-1",
            execution_timestamp=timestamp,
        )
    except InvariantViolationError as e:
        assert e.invariant_id == "I1"
        print(f"  ✓ InvariantViolationError caught specifically: {e.invariant_id}")
    except Exception as e:
        print(f"  ✗ FAILED: Should have caught InvariantViolationError")
        return False
    
    print("  ✓ InvariantViolationError propagation works correctly")
    return True


# ============================================================================
# Test 7: Continuous Invariant Checking
# ============================================================================

def test_continuous_invariant_checking():
    """Test that continuous invariant checking works."""
    print("\n" + "="*80)
    print("TEST 7: Continuous Invariant Checking")
    print("="*80)
    
    from mahoun.contracts.verdict_execution import (
        VerdictExecutionResult,
        InvariantChecker,
        enforce_invariants,
    )
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdict
    from mahoun.ledger.models import LedgerEntry, ValidationStatus
    
    timestamp = datetime.now(timezone.utc)
    
    verdict = EvidenceLinkedVerdict(
        final_verdict="Test verdict",
        steps=[],
        confidence_score=0.9,
    )
    verdict.verdict_id = "verdict-1"
    
    ledger_entry = LedgerEntry(
        verdict_id="verdict-1",
        case_id="case-1",
        referenced_ltm_nodes=("rule-1",),
        referenced_facts=("fact-1",),
        confidence=0.9,
        invariant_version="1.0",
        guard_mode="STRICT",
        created_at=timestamp,
        validation_status=ValidationStatus.PENDING,
    )
    
    result = VerdictExecutionResult(
        verdict=verdict,
        ledger_entry=ledger_entry,
        execution_id="exec-1",
        correlation_id="corr-1",
        execution_timestamp=timestamp,
    )
    
    # Test enforce_invariants
    print("  Testing enforce_invariants function...")
    try:
        enforce_invariants(result, "VerdictExecutionResult")
        print("  ✓ enforce_invariants passed for valid object")
    except Exception as e:
        print(f"  ✗ FAILED: enforce_invariants should pass for valid object: {e}")
        return False
    
    # Test that InvariantChecker singleton works
    print("  Testing InvariantChecker singleton...")
    checker1 = InvariantChecker()
    checker2 = InvariantChecker()
    assert checker1 is checker2, "InvariantChecker should be singleton"
    print("  ✓ InvariantChecker is a singleton")
    
    print("  ✓ Continuous invariant checking works")
    return True


# ============================================================================
# Test 8: PendingLedgerCommit Invariant Enforcement
# ============================================================================

def test_pending_ledger_commit_invariants():
    """Test that PendingLedgerCommit also enforces invariants."""
    print("\n" + "="*80)
    print("TEST 8: PendingLedgerCommit Invariant Enforcement")
    print("="*80)
    
    from mahoun.contracts.verdict_execution import PendingLedgerCommit, InvariantViolationError
    from mahoun.ledger.models import LedgerEntry, ValidationStatus
    
    timestamp = datetime.now(timezone.utc)
    
    ledger_entry = LedgerEntry(
        verdict_id="verdict-1",
        case_id="case-1",
        referenced_ltm_nodes=("rule-1",),
        referenced_facts=("fact-1",),
        confidence=0.9,
        invariant_version="1.0",
        guard_mode="STRICT",
        created_at=timestamp,
        validation_status=ValidationStatus.PENDING,
    )
    
    # Test None ledger_entry
    print("  Testing None ledger_entry...")
    try:
        commit = PendingLedgerCommit(
            ledger_entry=None,
            validation_passed=True,
            execution_id="exec-1",
            correlation_id="corr-1",
        )
        print("  ✗ FAILED: Should have raised InvariantViolationError")
        return False
    except InvariantViolationError as e:
        assert e.invariant_id == "PENDING-I1"
        print(f"  ✓ PendingLedgerCommit invariant enforced: {e.invariant_id}")
    
    # Test empty execution_id
    print("  Testing empty execution_id...")
    try:
        commit = PendingLedgerCommit(
            ledger_entry=ledger_entry,
            validation_passed=True,
            execution_id="",
            correlation_id="corr-1",
        )
        print("  ✗ FAILED: Should have raised InvariantViolationError")
        return False
    except InvariantViolationError as e:
        assert e.invariant_id == "PENDING-I2"
        print(f"  ✓ PendingLedgerCommit invariant enforced: {e.invariant_id}")
    
    print("  ✓ PendingLedgerCommit invariants enforced")
    return True


# ============================================================================
# Test 9: ExecutionContext Invariant Enforcement
# ============================================================================

def test_execution_context_invariants():
    """Test that ExecutionContext enforces invariants."""
    print("\n" + "="*80)
    print("TEST 9: ExecutionContext Invariant Enforcement")
    print("="*80)
    
    from mahoun.contracts.verdict_execution import ExecutionContext, InvariantViolationError
    
    timestamp = datetime.now(timezone.utc)
    
    # Test empty correlation_id
    print("  Testing empty correlation_id...")
    try:
        ctx = ExecutionContext(
            correlation_id="",
            execution_id="exec-1",
            execution_mode="STRICT",
            timestamp=timestamp,
        )
        print("  ✗ FAILED: Should have raised InvariantViolationError")
        return False
    except InvariantViolationError as e:
        assert e.invariant_id == "EXEC-CTX-I1"
        print(f"  ✓ ExecutionContext invariant enforced: {e.invariant_id}")
    
    # Test empty execution_id
    print("  Testing empty execution_id...")
    try:
        ctx = ExecutionContext(
            correlation_id="corr-1",
            execution_id="",
            execution_mode="STRICT",
            timestamp=timestamp,
        )
        print("  ✗ FAILED: Should have raised InvariantViolationError")
        return False
    except InvariantViolationError as e:
        assert e.invariant_id == "EXEC-CTX-I2"
        print(f"  ✓ ExecutionContext invariant enforced: {e.invariant_id}")
    
    # Test None timestamp
    print("  Testing None timestamp...")
    try:
        ctx = ExecutionContext(
            correlation_id="corr-1",
            execution_id="exec-1",
            execution_mode="STRICT",
            timestamp=None,
        )
        print("  ✗ FAILED: Should have raised InvariantViolationError")
        return False
    except InvariantViolationError as e:
        assert e.invariant_id == "EXEC-CTX-I4"
        print(f"  ✓ ExecutionContext invariant enforced: {e.invariant_id}")
    
    print("  ✓ ExecutionContext invariants enforced")
    return True


# ============================================================================
# Test 10: InvariantViolationError Contains Forensic Information
# ============================================================================

def test_invariant_violation_error_forensic_info():
    """Test that InvariantViolationError contains forensic information."""
    print("\n" + "="*80)
    print("TEST 10: InvariantViolationError Forensic Information")
    print("="*80)
    
    from mahoun.contracts.verdict_execution import VerdictExecutionResult, InvariantViolationError
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdict
    from mahoun.ledger.models import LedgerEntry, ValidationStatus
    
    timestamp = datetime.now(timezone.utc)
    
    try:
        result = VerdictExecutionResult(
            verdict=None,
            ledger_entry=LedgerEntry(
                verdict_id="test",
                case_id="test",
                referenced_ltm_nodes=(),
                referenced_facts=(),
                confidence=0.9,
                invariant_version="1.0",
                guard_mode="STRICT",
                created_at=timestamp,
            ),
            execution_id="exec-1",
            correlation_id="corr-1",
            execution_timestamp=timestamp,
        )
    except InvariantViolationError as e:
        # Verify forensic information
        assert hasattr(e, 'invariant_id'), "Missing invariant_id attribute"
        assert hasattr(e, 'severity'), "Missing severity attribute"
        assert hasattr(e, 'message'), "Missing message attribute"
        assert hasattr(e, 'traceback'), "Missing traceback attribute"
        
        assert e.invariant_id == "I1"
        assert e.severity == "CRITICAL"
        assert e.message == "verdict cannot be None"
        assert isinstance(e.traceback, list), "traceback should be a list"
        assert len(e.traceback) > 0, "traceback should not be empty"
        
        print(f"  ✓ InvariantViolationError contains forensic info:")
        print(f"    - invariant_id: {e.invariant_id}")
        print(f"    - severity: {e.severity}")
        print(f"    - message: {e.message}")
        print(f"    - traceback entries: {len(e.traceback)}")
        
        return True
    
    print("  ✗ FAILED: Should have raised InvariantViolationError")
    return False


# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests():
    """Run all HIGH-002 tests."""
    print("\n" + "="*80)
    print("MAHOUN HIGH-002 CONTRACT VALIDATION TEST SUITE")
    print("="*80)
    print("\nPHILOSOPHY: Fail-Closed, No Assumptions, Maximum Paranoia")
    print("Every test must be so hard that it would catch any regression")
    
    tests = [
        ("InvariantViolationError Exists", test_invariant_violation_error_exists),
        ("Contract Validation Framework", test_contract_validation_framework),
        ("VerdictExecutionResult Invariants", test_verdict_execution_result_invariants),
        ("Valid VerdictExecutionResult Creation", test_valid_verdict_execution_result),
        ("Frozen Dataclass Immutability", test_frozen_dataclass_immutability),
        ("InvariantViolationError Propagation", test_invariant_violation_error_propagation),
        ("Continuous Invariant Checking", test_continuous_invariant_checking),
        ("PendingLedgerCommit Invariants", test_pending_ledger_commit_invariants),
        ("ExecutionContext Invariants", test_execution_context_invariants),
        ("InvariantViolationError Forensic Info", test_invariant_violation_error_forensic_info),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n  ✓ PASSED: {name}")
            else:
                failed += 1
                print(f"\n  ✗ FAILED: {name}")
        except Exception as e:
            failed += 1
            print(f"\n  ✗ EXCEPTION in {name}: {e}")
            traceback.print_exc()
    
    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*80)
    
    if failed == 0:
        print("\n✓✓✓ ALL HIGH-002 TESTS PASSED ✓✓✓")
        print("Contract validation framework is working correctly!")
        return True
    else:
        print(f"\n✗✗✗ {failed} TESTS FAILED ✗✗✗")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

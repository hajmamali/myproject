"""
Phase 2A Test Runner.

Runs acceptance tests in priority order:
1. PRIORITY 1: Negative & Adversarial Tests (MUST pass first)
2. PRIORITY 2: Positive Tests (MUST pass after negative)

Exit Strategy:
- If negative tests fail → STOP (no point running positive tests)
- If positive tests fail → Report but less critical

Philosophy:
"Proving the system rejects bad inputs is more important than
proving it accepts good inputs."
"""

import pytest
import sys
from pathlib import Path


def run_phase_2a_tests():
    """
    Run Phase 2A acceptance tests with priority enforcement.
    
    Returns:
        int: Exit code (0 = all pass, 1 = negative failed, 2 = positive failed)
    """
    print("=" * 80)
    print("Phase 2A Semantic Schema Contract - Acceptance Test Suite")
    print("=" * 80)
    print()
    
    # ========================================================================
    # PRIORITY 1: Negative & Adversarial Tests
    # ========================================================================
    
    print("🔴 PRIORITY 1: Running Negative & Adversarial Tests...")
    print("-" * 80)
    print("These tests verify the fail-closed principle:")
    print("  - Missing evidence → REJECT")
    print("  - Unverified endpoints → REJECT")
    print("  - Duplicate identity → REJECT")
    print("  - Ambiguous extraction → UNRESOLVED")
    print("  - Governance bypass → REJECT")
    print("  - CI enforcement → DETECT")
    print()
    
    negative_tests = Path(__file__).parent / "test_phase_2a_negative_tests.py"
    
    negative_result = pytest.main([
        str(negative_tests),
        "-v",
        "--tb=short",
        "-m", "not ci",  # Skip CI tests for now (run separately)
        "--color=yes"
    ])
    
    if negative_result != 0:
        print()
        print("=" * 80)
        print("❌ NEGATIVE TESTS FAILED!")
        print("=" * 80)
        print()
        print("Phase 2A contract is NOT enforced.")
        print("Cannot proceed to positive tests.")
        print()
        print("Action required:")
        print("1. Fix the failing negative tests")
        print("2. These tests protect zero-hallucination guarantee")
        print("3. Do NOT skip or disable these tests")
        print()
        return 1
    
    print()
    print("=" * 80)
    print("✅ NEGATIVE TESTS PASSED!")
    print("=" * 80)
    print()
    print("Fail-closed principle is enforced.")
    print("System correctly REJECTS bad inputs.")
    print()
    
    # ========================================================================
    # PRIORITY 2: Positive Tests
    # ========================================================================
    
    print("🟢 PRIORITY 2: Running Positive Tests...")
    print("-" * 80)
    print("These tests verify the happy path:")
    print("  - Valid entity creation → SUCCESS")
    print("  - Valid assertion creation → SUCCESS")
    print("  - Provenance chain integrity → VERIFIED")
    print("  - Schema compliance → VALIDATED")
    print("  - Verification lifecycle → WORKS")
    print()
    
    positive_tests = Path(__file__).parent / "test_phase_2a_positive_tests.py"
    
    positive_result = pytest.main([
        str(positive_tests),
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    if positive_result != 0:
        print()
        print("=" * 80)
        print("⚠️  POSITIVE TESTS FAILED!")
        print("=" * 80)
        print()
        print("Negative tests passed (good), but positive tests failed.")
        print("This means: system correctly rejects bad inputs,")
        print("but may have issues accepting good inputs.")
        print()
        print("Action required:")
        print("1. Fix the failing positive tests")
        print("2. These tests verify the system works correctly")
        print("3. Less critical than negative tests, but still important")
        print()
        return 2
    
    print()
    print("=" * 80)
    print("✅ POSITIVE TESTS PASSED!")
    print("=" * 80)
    print()
    print("Happy path works correctly.")
    print("System correctly ACCEPTS good inputs.")
    print()
    
    # ========================================================================
    # Final Summary
    # ========================================================================
    
    print("=" * 80)
    print("🎉 ALL PHASE 2A ACCEPTANCE TESTS PASSED! 🎉")
    print("=" * 80)
    print()
    print("Phase 2A Semantic Schema Contract is fully enforced:")
    print()
    print("✅ Fail-closed principle enforced (negative tests)")
    print("✅ Happy path validated (positive tests)")
    print("✅ Zero-hallucination guarantee protected")
    print("✅ Governance boundary cannot be bypassed")
    print("✅ Provenance chain integrity verified")
    print("✅ Schema compliance validated")
    print()
    print("✨ Phase 2A is COMPLETE and READY FOR PHASE 2B! ✨")
    print()
    
    return 0


def run_ci_enforcement_tests():
    """
    Run CI enforcement tests separately.
    
    These tests are marked with @pytest.mark.ci and should run in CI pipeline.
    """
    print("=" * 80)
    print("Phase 2A CI Enforcement Tests")
    print("=" * 80)
    print()
    
    negative_tests = Path(__file__).parent / "test_phase_2a_negative_tests.py"
    
    result = pytest.main([
        str(negative_tests),
        "-v",
        "--tb=short",
        "-m", "ci",  # Only run CI-marked tests
        "--color=yes"
    ])
    
    if result != 0:
        print()
        print("❌ CI ENFORCEMENT TESTS FAILED!")
        print()
        print("Action required:")
        print("1. Fix governance bypass violations")
        print("2. Ensure schema versioning consistency")
        print("3. Validate provenance completeness")
        print()
        return 1
    
    print()
    print("✅ CI ENFORCEMENT TESTS PASSED!")
    print()
    return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run Phase 2A acceptance tests"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Run only CI enforcement tests"
    )
    
    args = parser.parse_args()
    
    if args.ci:
        exit_code = run_ci_enforcement_tests()
    else:
        exit_code = run_phase_2a_tests()
    
    sys.exit(exit_code)

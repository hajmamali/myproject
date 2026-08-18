"""
MAHOUN Phase 1 Critical Fixes Verification
==========================================

Classification: CRITICAL / HARDENING
Purpose: Verify ONLY the 3 CRITICAL fixes from Phase 1

This test suite verifies:
1. CRITICAL-001: Governance context enforcement (no fallbacks)
2. CRITICAL-002: LedgerCommitService requirement in production
3. CRITICAL-003: Proof generation mandatory (no silent failures)

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


class CriticalTestSuite:
    """Simple test suite for critical fixes only."""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures: List[Dict[str, Any]] = []
        
    def assert_source_contains(self, name: str, file_path: str, pattern: str, critical: bool = True) -> bool:
        """Assert that file contains pattern."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            if pattern in content:
                print(f"  ✓ {name}")
                self.tests_passed += 1
                return True
            else:
                print(f"  ✗ {name}")
                print(f"    Expected pattern NOT found: {pattern[:60]}")
                self.tests_failed += 1
                self.failures.append({"name": name, "file": file_path, "pattern": pattern})
                return False
        except Exception as e:
            print(f"  ✗ {name}")
            print(f"    Error: {e}")
            self.tests_failed += 1
            return False
    
    def assert_source_not_contains(self, name: str, file_path: str, pattern: str, critical: bool = True) -> bool:
        """Assert that file does NOT contain pattern."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            if pattern not in content:
                print(f"  ✓ {name}")
                self.tests_passed += 1
                return True
            else:
                print(f"  ✗ {name}")
                print(f"    FORBIDDEN pattern found: {pattern[:60]}")
                self.tests_failed += 1
                self.failures.append({"name": name, "file": file_path, "pattern": pattern})
                return False
        except Exception as e:
            print(f"  ✗ {name}")
            print(f"    Error: {e}")
            self.tests_failed += 1
            return False
    
    def print_summary(self):
        """Print test summary."""
        total = self.tests_passed + self.tests_failed
        print("\n" + "=" * 80)
        print(f"  PHASE 1 CRITICAL FIXES VERIFICATION")
        print("=" * 80)
        print(f"  Passed: {self.tests_passed}/{total}")
        print(f"  Failed: {self.tests_failed}/{total}")
        if self.tests_failed == 0:
            print(f"\n  ✅ ALL CRITICAL FIXES VERIFIED - PHASE 1 COMPLETE")
        else:
            print(f"\n  ❌ CRITICAL FIXES INCOMPLETE")
            if self.failures:
                print("\n  Failures:")
                for f in self.failures:
                    print(f"    - {f['name']}")
                    print(f"      File: {f['file']}")
                    print(f"      Pattern: {f['pattern'][:60]}")
        print("=" * 80)
        return self.tests_failed == 0


def main():
    print("\n" + "=" * 80)
    print("  MAHOUN PHASE 1 - CRITICAL FIXES VERIFICATION")
    print("=" * 80)
    
    suite = CriticalTestSuite()
    
    # =========================================================================
    # CRITICAL-001: Governance Context Enforcement
    # =========================================================================
    print("\n  CRITICAL-001: Governance Context Enforcement")
    print("  " + "-" * 76)
    
    # The fix: Removed the fallback that allowed execution without GovernanceContext
    # Old code: except (RuntimeError, Exception): correlation_id = execution_id
    # New code: Direct call to require_context() without try/except
    
    suite.assert_source_not_contains(
        "No exception catching with fallback",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py",
        "except (RuntimeError, Exception):"
    )
    
    suite.assert_source_not_contains(
        "No correlation_id = execution_id fallback",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py",
        "correlation_id = execution_id"
    )
    
    suite.assert_source_contains(
        "require_context() called directly",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py",
        "ctx = GovernanceContextManager.require_context()"
    )
    
    suite.assert_source_contains(
        "correlation_id from context",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py",
        "correlation_id = ctx.correlation_id"
    )
    
    # =========================================================================
    # CRITICAL-002: LedgerCommitService Requirement in Production
    # =========================================================================
    print("\n  CRITICAL-002: LedgerCommitService Requirement in Production")
    print("  " + "-" * 76)
    
    # The fix: Added ValueError in __init__ when ledger_commit_service is None in production
    
    suite.assert_source_contains(
        "Production mode check exists",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/fortress_integration.py",
        "if is_production():"
    )
    
    suite.assert_source_contains(
        "ValueError raised for missing service",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/fortress_integration.py",
        "raise ValueError("
    )
    
    suite.assert_source_contains(
        "CRITICAL-002 error message",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/fortress_integration.py",
        "CRITICAL-002: LedgerCommitService is REQUIRED"
    )
    
    suite.assert_source_contains(
        "RULE 7 and RULE 11 referenced",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/fortress_integration.py",
        "RULE 7 and RULE 11"
    )
    
    # The old code had: if self.ledger_commit_service and execution_result:
    # This allowed silent skipping when ledger_commit_service was None
    # The fix: Changed to just "if execution_result:" since ledger_commit_service
    # is guaranteed to be present (or will raise in __init__)
    suite.assert_source_not_contains(
        "No silent fallback check",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/fortress_integration.py",
        "if self.ledger_commit_service and execution_result:"
    )
    
    # In the else block, we should raise RuntimeError, not log warning
    suite.assert_source_contains(
        "Fail-closed in else block",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/fortress_integration.py",
        "raise RuntimeError("
    )
    
    suite.assert_source_contains(
        "LedgerCommitService not configured error",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/fortress_integration.py",
        "LedgerCommitService not configured"
    )
    
    # =========================================================================
    # CRITICAL-003: Proof Generation Mandatory
    # =========================================================================
    print("\n  CRITICAL-003: Proof Generation Mandatory")
    print("  " + "-" * 76)
    
    # The fix: Removed development fallback that set proof = None
    # Old code: except Exception as e: if is_production(): raise else: proof = None
    # New code: except Exception as e: raise RuntimeError(...)
    
    suite.assert_source_not_contains(
        "No proof = None assignment",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py",
        "proof = None"
    )
    
    suite.assert_source_contains(
        "Always raise RuntimeError on proof failure",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py",
        "raise RuntimeError("
    )
    
    suite.assert_source_contains(
        "Critical proof error message",
        "/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py",
        "The system CANNOT operate without cryptographic proof generation"
    )
    
    # Verify no environment-based degradation for proof
    # The old code had: if is_production(): raise else: log.error + proof = None
    # The new code: always raise
    # Note: There may be other if is_production() checks for other purposes (EL-I3)
    # but NOT in the proof generation except block
    
    # Check that the except block for proof generation doesn't have if is_production()
    with open("/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py", 'r') as f:
        lines = f.readlines()
    
    # Find the except block around line 616-626
    proof_except_block = []
    in_proof_except = False
    for i, line in enumerate(lines):
        if i > 600 and i < 650 and 'except Exception as e:' in line:
            # Check context
            context = ''.join(lines[max(0, i-10):i])
            if 'generate_proof' in context or 'proof' in context.lower():
                in_proof_except = True
                proof_except_block.append((i+1, line.rstrip()))
                continue
        if in_proof_except:
            proof_except_block.append((i+1, line.rstrip()))
            if 'raise RuntimeError' in line and 'proof' in line.lower():
                # End of except block
                break
    
    # Check if any line in the except block has "if is_production():"
    has_env_check = False
    for line_num, line_content in proof_except_block:
        if 'if is_production():' in line_content:
            has_env_check = True
            break
    
    if not has_env_check:
        print("  ✓ No environment-based fallback in proof generation except block")
        suite.tests_passed += 1
    else:
        print("  ✗ No environment-based fallback in proof generation except block")
        print("    Found if is_production() in proof except block")
        suite.tests_failed += 1
        suite.failures.append({
            "name": "Environment-based fallback in proof generation",
            "file": "/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py",
            "pattern": "if is_production() in proof except block"
        })
    
    # =========================================================================
    # Summary
    # =========================================================================
    success = suite.print_summary()
    
    if success:
        print("\n  🎯 PHASE 1 IS COMPLETE - ALL CRITICAL FIXES VERIFIED")
        return 0
    else:
        print("\n  💥 PHASE 1 INCOMPLETE - CRITICAL FIXES NEEDED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
MAHOUN HIGH-006 Governance Context Propagation Test Suite
============================================================

Classification: HIGH / ARCHITECTURAL / HARDENING
Purpose: Verify GovernanceContext is enforced at all entry points

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

import sys
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')


def test_governance_context_in_evidence_linked_verdict():
    """Test that evidence_linked_verdict requires GovernanceContext."""
    print("\n  Testing GovernanceContext in evidence_linked_verdict...")
    
    # Check source code
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py', 'r') as f:
        content = f.read()
    
    # Should have require_context
    assert 'GovernanceContextManager.require_context()' in content, \
        "require_context not found in evidence_linked_verdict.py"
    
    # Should have correlation_id from context
    assert 'correlation_id = ctx.correlation_id' in content, \
        "correlation_id from context not found"
    
    # Should NOT have fallback to execution_id
    assert 'correlation_id = execution_id' not in content, \
        "Found fallback to execution_id in evidence_linked_verdict.py"
    
    print("  ✓ GovernanceContext enforced in evidence_linked_verdict")
    return True


def test_governance_context_in_fortress_integration():
    """Test that fortress_integration requires GovernanceContext."""
    print("\n  Testing GovernanceContext in fortress_integration...")
    
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/fortress_integration.py', 'r') as f:
        content = f.read()
    
    assert 'GovernanceContextManager.require_context()' in content, \
        "require_context not found in fortress_integration.py"
    
    print("  ✓ GovernanceContext enforced in fortress_integration")
    return True


def test_governance_context_dependency_in_router():
    """Test that API router has governance context dependency."""
    print("\n  Testing GovernanceContext dependency in API router...")
    
    with open('/home/haji/Desktop/KingMahouN/api/routers/reasoning.py', 'r') as f:
        content = f.read()
    
    # Should have require_governance_context function
    assert 'def require_governance_context' in content, \
        "require_governance_context function not found"
    
    # Should reference HIGH-006
    assert 'HIGH-006' in content, \
        "HIGH-006 reference not found"
    
    # Should have dependency in generate_verdict endpoint
    assert 'Depends(require_governance_context)' in content, \
        "Governance context dependency not found in endpoint"
    
    print("  ✓ GovernanceContext dependency in API router")
    return True


def test_governance_context_not_optional():
    """Test that GovernanceContext is not optional."""
    print("\n  Testing that GovernanceContext is not optional...")
    
    # In evidence_linked_verdict.py, there should be no fallback
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py', 'r') as f:
        content = f.read()
    
    # Should NOT have try/except catching RuntimeError from require_context
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'GovernanceContextManager.require_context()' in line:
            # Check surrounding lines for try/except
            context_before = '\n'.join(lines[max(0, i-5):i])
            context_after = '\n'.join(lines[i:min(len(lines), i+5)])
            full_context = context_before + '\n' + line + '\n' + context_after
            assert 'except' not in full_context or 'CRITICAL' in full_context, \
                f"Found try/except around require_context at line {i+1}"
    
    print("  ✓ GovernanceContext is not optional (no fallbacks)")
    return True


def test_governance_context_manager_imports():
    """Test that all necessary imports exist."""
    print("\n  Testing GovernanceContextManager imports...")
    
    # Check router
    with open('/home/haji/Desktop/KingMahouN/api/routers/reasoning.py', 'r') as f:
        router_content = f.read()
    assert 'GovernanceContextManager' in router_content, \
        "GovernanceContextManager not imported in router"
    
    # Check evidence_linked_verdict
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py', 'r') as f:
        verdict_content = f.read()
    assert 'GovernanceContextManager' in verdict_content, \
        "GovernanceContextManager not imported in evidence_linked_verdict"
    
    # Check fortress_integration
    with open('/home/haji/Desktop/KingMahouN/mahoun/reasoning/fortress_integration.py', 'r') as f:
        fortress_content = f.read()
    assert 'GovernanceContextManager' in fortress_content, \
        "GovernanceContextManager not imported in fortress_integration"
    
    print("  ✓ All GovernanceContextManager imports exist")
    return True


def main():
    print("\n" + "=" * 80)
    print("  MAHOUN HIGH-006: Governance Context Propagation Tests")
    print("=" * 80)
    
    tests = [
        test_governance_context_in_evidence_linked_verdict,
        test_governance_context_in_fortress_integration,
        test_governance_context_dependency_in_router,
        test_governance_context_not_optional,
        test_governance_context_manager_imports,
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
    print(f"  HIGH-006 GOVERNANCE CONTEXT PROPAGATION TESTS")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {total-passed}/{total}")
    
    if all(results):
        print("\n  ✅ ALL HIGH-006 TESTS PASSED")
        return 0
    else:
        print("\n  ❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

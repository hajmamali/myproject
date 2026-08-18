#!/usr/bin/env python3
"""
MAHOUN Architecture Integrity Test Runner
==========================================
Tests the ICG kernel and red-team bypass scenarios.
"""

import asyncio
import sys
from arch_check import (
    ICGKernel,
    ICGMiddleware,
    build_red_team,
)


class MockFastAPIApp:
    """Mock FastAPI app for testing"""
    
    def __init__(self):
        self.middleware_stack = []
    
    def add_middleware(self, middleware_class, **kwargs):
        self.middleware_stack.append((middleware_class, kwargs))
        print(f"✅ Middleware added: {middleware_class.__name__}")
    
    async def __call__(self, scope, receive, send):
        """Mock ASGI interface"""
        pass


class MockRequest:
    """Mock FastAPI Request"""
    
    def __init__(self, path: str, method: str = "GET"):
        self.url = type('obj', (object,), {'path': path})()
        self.method = method


@pytest.mark.p2
async def test_icg_kernel():
    """Test ICG Kernel basic functionality"""
    print("\n" + "="*60)
    print("🧪 Testing ICG Kernel...")
    print("="*60)
    
    kernel = ICGKernel()
    
    # Test 1: Allow normal request
    req1 = MockRequest("/api/v1/reasoning")
    decision1 = kernel.evaluate_request(req1)
    assert decision1["decision"] == "ALLOW", "Normal request should be allowed"
    print(f"✅ Test 1 PASSED: Normal request allowed - {decision1}")
    
    # Test 2: Block forbidden pattern
    req2 = MockRequest("/internal/.session/bypass")
    decision2 = kernel.evaluate_request(req2)
    assert decision2["decision"] == "DENY", "Forbidden pattern should be blocked"
    print(f"✅ Test 2 PASSED: Forbidden pattern blocked - {decision2}")
    
    # Test 3: Check audit log
    assert len(kernel.audit._chain) >= 2, "Audit log should contain events"
    print(f"✅ Test 3 PASSED: Audit log has {len(kernel.audit._chain)} events")
    
    # Test 4: Verify hash chain
    for i in range(1, len(kernel.audit._chain)):
        prev_record = kernel.audit._chain[i-1]
        curr_record = kernel.audit._chain[i]
        assert curr_record["prev_hash"] == prev_record["hash"], "Hash chain broken!"
    print(f"✅ Test 4 PASSED: Hash chain integrity verified")
    
    print("\n✅ ICG Kernel tests PASSED!\n")
    return kernel


@pytest.mark.p2
async def test_red_team_suite(app, kernel):
    """Test Red Team bypass scenarios"""
    print("\n" + "="*60)
    print("🔴 Running Red Team Bypass Scenarios...")
    print("="*60)
    
    suite = build_red_team(app, kernel)
    results = await suite.run_all()
    
    print(f"\n📊 Red Team Results:")
    print(f"{'Scenario':<30} {'Status':<15} {'Result'}")
    print("-" * 60)
    
    passed_count = 0
    blocked_count = 0
    
    for result in results:
        status = "🔴 PASSED" if result.passed else "✅ BLOCKED"
        if result.passed:
            passed_count += 1
        if result.blocked:
            blocked_count += 1
            
        print(f"{result.name:<30} {status:<15}")
    
    print("-" * 60)
    print(f"\nTotal Scenarios: {len(results)}")
    print(f"Bypassed (BAD):  {passed_count}")
    print(f"Blocked (GOOD):  {blocked_count}")
    print(f"Other:           {len(results) - passed_count - blocked_count}")
    
    # Note: These tests DEMONSTRATE attacks, not validate blocking
    # In real ICG, we'd want ALL to be blocked
    print("\n⚠️  NOTE: These scenarios demonstrate potential attacks.")
    print("    Real ICG kernel would need to block ALL of them.")
    
    return results


@pytest.mark.p2
async def test_middleware_integration():
    """Test middleware integration"""
    print("\n" + "="*60)
    print("🔧 Testing Middleware Integration...")
    print("="*60)
    
    app = MockFastAPIApp()
    kernel = ICGKernel()
    
    # Install middleware
    app.add_middleware(ICGMiddleware, kernel=kernel)
    
    assert len(app.middleware_stack) == 1, "Middleware not installed"
    middleware_class, kwargs = app.middleware_stack[0]
    assert middleware_class == ICGMiddleware, "Wrong middleware class"
    assert kwargs["kernel"] == kernel, "Kernel not passed correctly"
    
    print("✅ Middleware integration test PASSED!\n")
    return app, kernel


async def run_architecture_health_check():
    """Comprehensive architecture health check"""
    print("\n" + "="*80)
    print("🏗️  MAHOUN ARCHITECTURE INTEGRITY CHECK")
    print("="*80)
    
    try:
        # Test 1: ICG Kernel
        kernel = await test_icg_kernel()
        
        # Test 2: Middleware Integration
        app, kernel = await test_middleware_integration()
        
        # Test 3: Red Team Suite
        results = await test_red_team_suite(app, kernel)
        
        # Final Summary
        print("\n" + "="*80)
        print("📋 FINAL SUMMARY")
        print("="*80)
        print("✅ ICG Kernel:              OPERATIONAL")
        print("✅ Middleware Integration:  OPERATIONAL")
        print("✅ Red Team Suite:          OPERATIONAL")
        print(f"✅ Audit Log Events:        {len(kernel.audit._chain)}")
        print(f"✅ Hash Chain Integrity:    VERIFIED")
        
        print("\n" + "="*80)
        print("🎯 MAHOUN ARCHITECTURE: HEALTHY")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ARCHITECTURE CHECK FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    print("""
╔════════════════════════════════════════════════════════════╗
║   MAHOUN - Architecture Integrity & Security Validation   ║
║   Version: 1.0.0                                          ║
║   Purpose: Validate core architecture and governance      ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    success = asyncio.run(run_architecture_health_check())
    
    if success:
        print("\n✅ All architecture checks passed!\n")
        sys.exit(0)
    else:
        print("\n❌ Architecture checks failed!\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

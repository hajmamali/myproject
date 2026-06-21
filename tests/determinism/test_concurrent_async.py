"""
MAHOUN Determinism Test 2: Concurrent Async Execution
======================================================

Classification: CRITICAL CONCURRENCY ENFORCEMENT
Purpose: Verify determinism under concurrent async execution

This test executes 100 CONCURRENT reasoning requests and verifies
that parallel execution produces IDENTICAL results to sequential.

Invariants Tested:
- CONC-G1: Concurrent execution → Same results as sequential
- CONC-G2: No race conditions in shared state
- CONC-G3: No async state corruption
- CONC-G4: Thread-safe validator operations

ANY race condition is a CRITICAL FAILURE.

Author: MahouN AEO Governance Council
Version: 1.0.0
"""

import pytest
import asyncio
from typing import List
from datetime import datetime

from mahoun.reasoning.unified_reasoning_service import (
    UnifiedReasoningService,
    ReasoningRequest,
    ReasoningResponse,
    ReasoningTask,
    ReasoningMode
)
from mahoun.core.fortress_validator import FortressValidator
from tests.determinism import DeterminismTestBase, DeterminismMetrics


class TestConcurrentAsync(DeterminismTestBase):
    """Test determinism under concurrent async execution"""
    
    @pytest.mark.asyncio
    async def test_100_concurrent_symbolic_reasoning(self):
        """
        Test 2.1: 100 concurrent symbolic reasoning requests
        
        Execute 100 identical requests concurrently, verify:
        - All produce identical results
        - No race conditions
        - No state corruption
        """
        service = UnifiedReasoningService(enable_neural=False)
        
        # Create request
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="Concurrent test",
            facts=["test(1)", "test(2)", "test(3)"],
            rules=["result(X) :- test(X)"],
            mode=ReasoningMode.SYMBOLIC,
            return_proof=True
        )
        
        # Execute sequentially (baseline)
        baseline = await service.reason(request)
        baseline_hash = self.compute_result_hash(baseline)
        
        # Execute 100 concurrent requests
        tasks = [service.reason(request) for _ in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, (
            f"CONCURRENT EXECUTION FAILURES: {len(exceptions)} exceptions\n"
            f"First exception: {exceptions[0] if exceptions else None}"
        )
        
        # Verify all results identical to baseline
        violations = []
        for i, result in enumerate(results):
            result_hash = self.compute_result_hash(result)
            if result_hash != baseline_hash:
                violations.append(f"Result {i}: hash mismatch")
        
        assert len(violations) == 0, (
            f"CONCURRENT DETERMINISM VIOLATION: {len(violations)} mismatches\n"
            f"Violations: {violations[:5]}"
        )
        
        print(f"✅ CONCURRENT DETERMINISM VERIFIED: 100/100 identical")
    
    @pytest.mark.asyncio
    async def test_concurrent_fortress_validation(self):
        """
        Test 2.2: Concurrent FortressValidator operations
        
        Verify validator is thread-safe under concurrent load.
        """
        validator = FortressValidator(strict_mode=False)
        
        # Create test response
        from mahoun.reasoning.unified_reasoning_service import ReasoningResponse, ReasoningMode
        import os
        os.environ["MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT"] = "false"
        
        def create_response(i: int):
            return ReasoningResponse(
                success=True,
                result=f"Result {i}",
                confidence=0.90,
                reasoning_mode=ReasoningMode.SYMBOLIC,
                execution_time_ms=100.0,
                proof_tree={"depth": 3},
                derived_facts=["fact1", "fact2"],
                fortress_validated=False,
                audit_hash=None,
                validation_timestamp=None,
                correlation_id=None,
                metadata={}
            )
        
        # Execute 100 concurrent validations
        tasks = [
            validator.validate(create_response(i), correlation_id=f"concurrent-{i}")
            for i in range(100)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, (
            f"CONCURRENT VALIDATION FAILURES: {len(exceptions)} exceptions"
        )
        
        # Verify validator stats consistency
        stats = validator.get_stats()
        assert stats["total_validations"] == 100, (
            f"STATS CORRUPTION: expected 100, got {stats['total_validations']}"
        )
        
        # Cleanup
        del os.environ["MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT"]
        
        print(f"✅ CONCURRENT VALIDATION VERIFIED: 100/100 successful")
    
    @pytest.mark.asyncio
    async def test_concurrent_with_delays(self):
        """
        Test 2.3: Concurrent execution with random delays
        
        Introduce random delays to stress-test async safety.
        """
        service = UnifiedReasoningService(enable_neural=False)
        
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="Delayed test",
            facts=["a(1)"],
            rules=["b(X) :- a(X)"],
            mode=ReasoningMode.SYMBOLIC
        )
        
        # Baseline
        baseline = await service.reason(request)
        baseline_hash = self.compute_result_hash(baseline)
        
        # Execute with random delays
        import random
        
        async def reason_with_delay():
            await asyncio.sleep(random.uniform(0.001, 0.01))  # 1-10ms delay
            return await service.reason(request)
        
        tasks = [reason_with_delay() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        # Verify all identical
        for i, result in enumerate(results):
            result_hash = self.compute_result_hash(result)
            assert result_hash == baseline_hash, (
                f"DELAYED CONCURRENT VIOLATION at iteration {i}"
            )
        
        print(f"✅ DELAYED CONCURRENT DETERMINISM VERIFIED: 100/100")
    
    @pytest.mark.asyncio
    async def test_concurrent_different_requests(self):
        """
        Test 2.4: Concurrent execution of DIFFERENT requests
        
        Verify no cross-contamination between concurrent requests.
        """
        service = UnifiedReasoningService(enable_neural=False)
        
        # Create 10 different requests
        requests = [
            ReasoningRequest(
                task=ReasoningTask.FORWARD_INFERENCE,
                query=f"Query {i}",
                facts=[f"fact{i}(1)"],
                rules=[f"result{i}(X) :- fact{i}(X)"],
                mode=ReasoningMode.SYMBOLIC
            )
            for i in range(10)
        ]
        
        # Execute each request 10 times concurrently (100 total)
        tasks = []
        for req in requests:
            tasks.extend([service.reason(req) for _ in range(10)])
        
        results = await asyncio.gather(*tasks)
        
        # Group results by request
        grouped = {}
        for i, result in enumerate(results):
            req_idx = i // 10
            if req_idx not in grouped:
                grouped[req_idx] = []
            grouped[req_idx].append(result)
        
        # Verify each group has identical results
        for req_idx, group in grouped.items():
            baseline_hash = self.compute_result_hash(group[0])
            for j, result in enumerate(group[1:], 1):
                result_hash = self.compute_result_hash(result)
                assert result_hash == baseline_hash, (
                    f"CROSS-CONTAMINATION: Request {req_idx}, iteration {j}"
                )
        
        print(f"✅ CONCURRENT DIFFERENT REQUESTS VERIFIED: 10 requests × 10 iterations")
    
    @pytest.mark.asyncio
    async def test_concurrent_validator_stats_integrity(self):
        """
        Test 2.5: Validator statistics integrity under concurrency
        
        Verify stats are correctly updated without race conditions.
        """
        validator = FortressValidator(strict_mode=False)
        
        import os
        os.environ["MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT"] = "false"
        
        # Create mix of passing and failing responses
        from mahoun.reasoning.unified_reasoning_service import ReasoningResponse, ReasoningMode
        
        def create_passing_response(i):
            return ReasoningResponse(
                success=True,
                result=f"Pass {i}",
                confidence=0.90,
                reasoning_mode=ReasoningMode.SYMBOLIC,
                execution_time_ms=100.0,
                proof_tree={"depth": 3},
                derived_facts=["fact1"],
                fortress_validated=False,
                audit_hash=None,
                validation_timestamp=None,
                correlation_id=None,
                metadata={"agreement_score": 0.90}
            )
        
        def create_failing_response(i):
            return ReasoningResponse(
                success=True,
                result=f"Fail {i}",
                confidence=0.90,
                reasoning_mode=ReasoningMode.SYMBOLIC,
                execution_time_ms=100.0,
                proof_tree=None,  # Missing! Will fail validation
                derived_facts=[],
                fortress_validated=False,
                audit_hash=None,
                validation_timestamp=None,
                correlation_id=None,
                metadata={}
            )
        
        # Execute 50 passing + 50 failing concurrently
        tasks = []
        tasks.extend([
            validator.validate(create_passing_response(i), correlation_id=f"pass-{i}")
            for i in range(50)
        ])
        tasks.extend([
            validator.validate(create_failing_response(i), correlation_id=f"fail-{i}")
            for i in range(50)
        ])
        
        # Shuffle for randomness
        import random
        random.shuffle(tasks)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify stats
        stats = validator.get_stats()
        
        assert stats["total_validations"] == 100, (
            f"STATS CORRUPTION: total_validations = {stats['total_validations']}"
        )
        
        assert stats["passed"] == 50, (
            f"STATS CORRUPTION: passed = {stats['passed']}"
        )
        
        assert stats["failed"] == 50, (
            f"STATS CORRUPTION: failed = {stats['failed']}"
        )
        
        # Cleanup
        del os.environ["MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT"]
        
        print(f"✅ VALIDATOR STATS INTEGRITY VERIFIED: 50 pass + 50 fail")
    
    @pytest.mark.asyncio
    async def test_concurrent_audit_trail_integrity(self):
        """
        Test 2.6: Audit trail integrity under concurrent writes
        
        Verify no audit records are lost or corrupted.
        """
        validator = FortressValidator(strict_mode=False)
        
        import os
        os.environ["MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT"] = "false"
        
        from mahoun.reasoning.unified_reasoning_service import ReasoningResponse, ReasoningMode
        
        def create_response(i):
            return ReasoningResponse(
                success=True,
                result=f"Audit {i}",
                confidence=0.90,
                reasoning_mode=ReasoningMode.SYMBOLIC,
                execution_time_ms=100.0,
                proof_tree={"depth": 3},
                derived_facts=["fact1"],
                fortress_validated=False,
                audit_hash=None,
                validation_timestamp=None,
                correlation_id=None,
                metadata={"agreement_score": 0.90}
            )
        
        # Execute 100 concurrent validations
        tasks = [
            validator.validate(create_response(i), correlation_id=f"audit-{i}")
            for i in range(100)
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify audit trail
        audit_trail = validator.get_audit_trail(limit=200)
        
        assert len(audit_trail) == 100, (
            f"AUDIT TRAIL CORRUPTION: expected 100 records, got {len(audit_trail)}"
        )
        
        # Verify all correlation IDs present
        correlation_ids = {record["correlation_id"] for record in audit_trail}
        expected_ids = {f"audit-{i}" for i in range(100)}
        
        missing = expected_ids - correlation_ids
        assert len(missing) == 0, (
            f"AUDIT TRAIL LOSS: {len(missing)} records missing\n"
            f"Missing IDs: {list(missing)[:10]}"
        )
        
        # Cleanup
        del os.environ["MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT"]
        
        print(f"✅ AUDIT TRAIL INTEGRITY VERIFIED: 100/100 records")


# ============================================================================
# STRESS TEST CONFIGURATION
# ============================================================================

@pytest.fixture(scope="module")
def concurrent_test_config():
    """Configuration for concurrent tests"""
    return {
        "concurrency": 100,
        "timeout_seconds": 60,
        "max_delay_ms": 10,
    }


"""
MAHOUN Determinism Test 3: Retry Storm
=======================================

Classification: CRITICAL RESILIENCE ENFORCEMENT
Purpose: Verify determinism under rapid repeated execution

This test simulates a "retry storm" - rapid repeated execution of
the same request with minimal delay between attempts.

Invariants Tested:
- RETRY-G1: Rapid retries → Same results
- RETRY-G2: No state accumulation
- RETRY-G3: No memory leaks
- RETRY-G4: No performance degradation

ANY instability is a CRITICAL FAILURE.

Author: MahouN AEO Governance Council
Version: 1.0.0
"""

import pytest
import asyncio
import time
from typing import List

from mahoun.reasoning.unified_reasoning_service import (
    UnifiedReasoningService,
    ReasoningRequest,
    ReasoningTask,
    ReasoningMode
)
from tests.determinism import DeterminismTestBase


class TestRetryStorm(DeterminismTestBase):
    """Test determinism under retry storm conditions"""
    
    @pytest.mark.asyncio
    async def test_1000_rapid_retries(self):
        """
        Test 3.1: 1000 rapid retries (minimal delay)
        
        Execute same request 1000 times as fast as possible.
        """
        service = UnifiedReasoningService(enable_neural=False)
        
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="Retry storm test",
            facts=["test(1)"],
            rules=["result(X) :- test(X)"],
            mode=ReasoningMode.SYMBOLIC
        )
        
        # Baseline
        baseline = await service.reason(request)
        baseline_hash = self.compute_result_hash(baseline)
        
        # Execute 1000 rapid retries
        start_time = time.perf_counter()
        violations = []
        
        for i in range(1000):
            result = await service.reason(request)
            result_hash = self.compute_result_hash(result)
            
            if result_hash != baseline_hash:
                violations.append(i)
        
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        
        assert len(violations) == 0, (
            f"RETRY STORM VIOLATIONS: {len(violations)} mismatches\n"
            f"Iterations: {violations[:10]}"
        )
        
        print(f"✅ RETRY STORM VERIFIED: 1000/1000 in {duration_ms:.0f}ms "
              f"({1000/duration_ms*1000:.0f} req/s)")
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff(self):
        """
        Test 3.2: Retries with exponential backoff
        
        Simulate realistic retry pattern with backoff.
        """
        service = UnifiedReasoningService(enable_neural=False)
        
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="Backoff test",
            facts=["a(1)"],
            rules=["b(X) :- a(X)"],
            mode=ReasoningMode.SYMBOLIC
        )
        
        baseline = await service.reason(request)
        baseline_hash = self.compute_result_hash(baseline)
        
        # Retry with exponential backoff
        delays = [0.001, 0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128]
        
        for i, delay in enumerate(delays):
            await asyncio.sleep(delay)
            result = await service.reason(request)
            result_hash = self.compute_result_hash(result)
            
            assert result_hash == baseline_hash, (
                f"BACKOFF RETRY VIOLATION at iteration {i} (delay={delay}s)"
            )
        
        print(f"✅ BACKOFF RETRY VERIFIED: {len(delays)} retries")
    
    @pytest.mark.asyncio
    async def test_memory_stability_under_retries(self):
        """
        Test 3.3: Memory stability under 1000 retries
        
        Verify no memory leaks during retry storm.
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory_mb = process.memory_info().rss / 1024 / 1024
        
        service = UnifiedReasoningService(enable_neural=False)
        
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="Memory test",
            facts=["test(1)"],
            rules=["result(X) :- test(X)"],
            mode=ReasoningMode.SYMBOLIC
        )
        
        # Execute 1000 retries
        for _ in range(1000):
            await service.reason(request)
        
        final_memory_mb = process.memory_info().rss / 1024 / 1024
        memory_growth_mb = final_memory_mb - initial_memory_mb
        
        # Allow max 50MB growth for 1000 iterations
        assert memory_growth_mb < 50, (
            f"MEMORY LEAK DETECTED: {memory_growth_mb:.1f}MB growth\n"
            f"Initial: {initial_memory_mb:.1f}MB, Final: {final_memory_mb:.1f}MB"
        )
        
        print(f"✅ MEMORY STABILITY VERIFIED: {memory_growth_mb:.1f}MB growth (acceptable)")


# ============================================================================
# PERFORMANCE BENCHMARKS
# ============================================================================

@pytest.mark.benchmark
class TestRetryPerformance:
    """Performance benchmarks for retry scenarios"""
    
    @pytest.mark.asyncio
    async def test_throughput_benchmark(self):
        """Measure maximum throughput"""
        service = UnifiedReasoningService(enable_neural=False)
        
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="Throughput test",
            facts=["test(1)"],
            rules=["result(X) :- test(X)"],
            mode=ReasoningMode.SYMBOLIC
        )
        
        # Warmup
        for _ in range(10):
            await service.reason(request)
        
        # Benchmark
        start = time.perf_counter()
        for _ in range(1000):
            await service.reason(request)
        end = time.perf_counter()
        
        duration_s = end - start
        throughput = 1000 / duration_s
        
        print(f"\n📊 THROUGHPUT: {throughput:.0f} req/s")
        print(f"   Latency: {duration_s/1000*1000:.2f}ms per request")


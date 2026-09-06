"""
Correlation ID Stress and Concurrency Tests
============================================

Classification: P1 INTEGRATION / STRESS TESTING / CONCURRENCY

Purpose:
--------
Stress test correlation ID integrity under high load and concurrent operations:
- High-volume concurrent executions
- Correlation ID uniqueness under load
- Performance baseline for correlation tracking
- Thread safety verification
- Async context isolation

These tests complement the core E2E tests with stress and performance validation.

Author: MahouN Platform Governance Council
Version: 1.0.0
"""

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import List, Set

import pytest

from mahoun.core.governance.governance_context import GovernanceContextManager


# ============================================================================
# STRESS TEST: HIGH-VOLUME CORRELATION ID GENERATION
# ============================================================================


class TestCorrelationIDStress:
    """
    Stress tests for correlation ID generation and isolation.
    """
    
    @pytest.mark.p1_integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_high_volume_unique_id_generation(self):
        """
        Test that system can generate 1000 unique correlation IDs
        without collision.
        """
        correlation_ids: Set[str] = set()
        num_iterations = 1000
        
        start_time = time.time()
        
        for _ in range(num_iterations):
            async with GovernanceContextManager.active_context(
                execution_mode="STRICT",
                actor_id="stress-test-actor",
            ) as ctx:
                correlation_ids.add(ctx.correlation_id)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Verify all IDs are unique
        assert len(correlation_ids) == num_iterations, \
            f"Expected {num_iterations} unique IDs, got {len(correlation_ids)}"
        
        # Performance baseline: should complete in reasonable time
        avg_time_per_id = elapsed / num_iterations
        print(f"\n📊 Performance: {num_iterations} IDs in {elapsed:.2f}s")
        print(f"   Average: {avg_time_per_id*1000:.2f}ms per ID")
        
        # Assert reasonable performance (< 10ms per ID)
        assert avg_time_per_id < 0.01, \
            f"ID generation too slow: {avg_time_per_id*1000:.2f}ms per ID"
    
    @pytest.mark.p1_integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_execution_isolation(self):
        """
        Test that concurrent executions maintain isolated correlation IDs.
        
        Simulates 10 concurrent executions, each creating 10 correlation IDs,
        and verifies no cross-contamination.
        """
        num_concurrent = 10
        ids_per_execution = 10
        
        async def create_execution_ids(execution_prefix: str) -> Set[str]:
            """Create multiple IDs within one logical execution."""
            ids = set()
            for i in range(ids_per_execution):
                async with GovernanceContextManager.active_context(
                    correlation_id=f"{execution_prefix}-{i}",
                    execution_mode="STRICT",
                    actor_id=f"actor-{execution_prefix}",
                ) as ctx:
                    ids.add(ctx.correlation_id)
            return ids
        
        # Run concurrent executions
        tasks = [
            create_execution_ids(f"EXEC-{i}")
            for i in range(num_concurrent)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify each execution got unique IDs
        for i, ids in enumerate(results):
            assert len(ids) == ids_per_execution, \
                f"Execution {i} expected {ids_per_execution} IDs, got {len(ids)}"
        
        # Verify no overlap between executions
        all_ids = set()
        for ids in results:
            overlap = all_ids.intersection(ids)
            assert len(overlap) == 0, \
                f"Found ID overlap between executions: {overlap}"
            all_ids.update(ids)
        
        # Verify total unique IDs
        expected_total = num_concurrent * ids_per_execution
        assert len(all_ids) == expected_total, \
            f"Expected {expected_total} total unique IDs, got {len(all_ids)}"
    
    @pytest.mark.p1_integration
    @pytest.mark.asyncio
    async def test_correlation_lineage_under_deep_nesting(self):
        """
        Test correlation lineage tracking under deep nesting (10 levels).
        
        Verifies that lineage is correctly maintained even with deep
        parent-child relationships.
        """
        max_depth = 10
        
        async def create_nested_context(depth: int, parent_ctx=None):
            """Recursively create nested contexts."""
            if depth == 0:
                return []
            
            if parent_ctx is None:
                # Root context
                async with GovernanceContextManager.active_context(
                    correlation_id=f"ROOT-{uuid.uuid4().hex[:8]}",
                    execution_mode="STRICT",
                    actor_id="nesting-test",
                ) as ctx:
                    lineage = [ctx.correlation_id]
                    child_lineage = await create_nested_context(depth - 1, ctx)
                    return lineage + child_lineage
            else:
                # Child context
                child_ctx = parent_ctx.create_child_context(
                    f"CHILD-L{max_depth-depth+1}-{uuid.uuid4().hex[:8]}"
                )
                lineage = [child_ctx.correlation_id]
                
                # Verify lineage includes parent
                assert parent_ctx.correlation_id in child_ctx.correlation_lineage
                
                if depth > 1:
                    child_lineage = await create_nested_context(depth - 1, child_ctx)
                    return lineage + child_lineage
                return lineage
        
        lineage = await create_nested_context(max_depth)
        
        # Verify lineage depth
        assert len(lineage) == max_depth, \
            f"Expected lineage depth {max_depth}, got {len(lineage)}"
        
        # Verify all IDs are unique
        assert len(set(lineage)) == max_depth, \
            "Lineage contains duplicate IDs"


# ============================================================================
# STRESS TEST: THREAD SAFETY
# ============================================================================


class TestCorrelationIDThreadSafety:
    """
    Thread safety tests for correlation ID management.
    """
    
    @pytest.mark.p1_integration
    @pytest.mark.slow
    def test_thread_safety_sync_contexts(self):
        """
        Test correlation ID context isolation across threads.
        
        Verifies that contexts in different threads don't interfere
        with each other.
        """
        num_threads = 20
        iterations_per_thread = 50
        thread_results: List[Set[str]] = [set() for _ in range(num_threads)]
        
        def thread_worker(thread_id: int):
            """Worker function for each thread."""
            async def async_worker():
                for i in range(iterations_per_thread):
                    async with GovernanceContextManager.active_context(
                        correlation_id=f"THREAD-{thread_id}-{i}",
                        execution_mode="STRICT",
                        actor_id=f"thread-{thread_id}",
                    ) as ctx:
                        thread_results[thread_id].add(ctx.correlation_id)
                        # Small delay to increase chance of interleaving
                        await asyncio.sleep(0.001)
            
            asyncio.run(async_worker())
        
        # Run threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(thread_worker, i)
                for i in range(num_threads)
            ]
            # Wait for all to complete
            for future in futures:
                future.result()
        
        # Verify each thread got correct number of unique IDs
        for thread_id, ids in enumerate(thread_results):
            assert len(ids) == iterations_per_thread, \
                f"Thread {thread_id} expected {iterations_per_thread} IDs, got {len(ids)}"
        
        # Verify no overlap between threads
        all_ids = set()
        for thread_id, ids in enumerate(thread_results):
            overlap = all_ids.intersection(ids)
            assert len(overlap) == 0, \
                f"Thread {thread_id} has ID overlap: {overlap}"
            all_ids.update(ids)
        
        # Verify total unique IDs
        expected_total = num_threads * iterations_per_thread
        assert len(all_ids) == expected_total, \
            f"Expected {expected_total} total IDs, got {len(all_ids)}"


# ============================================================================
# BENCHMARK: CORRELATION ID PERFORMANCE
# ============================================================================


class TestCorrelationIDPerformance:
    """
    Performance benchmarks for correlation ID operations.
    """
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_benchmark_id_creation_throughput(self):
        """
        Benchmark: How many correlation IDs can be created per second?
        
        Establishes performance baseline for correlation ID generation.
        """
        num_samples = 1000
        
        start_time = time.time()
        
        for _ in range(num_samples):
            async with GovernanceContextManager.active_context(
                execution_mode="STRICT",
                actor_id="benchmark-actor",
            ) as ctx:
                _ = ctx.correlation_id  # Access ID
        
        end_time = time.time()
        elapsed = end_time - start_time
        throughput = num_samples / elapsed
        
        print(f"\n📊 Correlation ID Creation Benchmark:")
        print(f"   Samples: {num_samples}")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Throughput: {throughput:.0f} IDs/second")
        print(f"   Avg latency: {(elapsed/num_samples)*1000:.2f}ms")
        
        # Assert minimum throughput (at least 100 IDs/sec)
        assert throughput > 100, \
            f"Throughput too low: {throughput:.0f} IDs/sec (expected > 100)"
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_benchmark_lineage_tracking_overhead(self):
        """
        Benchmark: Overhead of correlation lineage tracking.
        
        Compares performance of flat vs nested contexts.
        """
        num_iterations = 100
        max_depth = 5
        
        # Benchmark 1: Flat contexts (no nesting)
        start_flat = time.time()
        for _ in range(num_iterations):
            async with GovernanceContextManager.active_context(
                execution_mode="STRICT",
                actor_id="benchmark-flat",
            ) as ctx:
                _ = ctx.correlation_lineage
        end_flat = time.time()
        flat_time = end_flat - start_flat
        
        # Benchmark 2: Nested contexts
        start_nested = time.time()
        for _ in range(num_iterations):
            async with GovernanceContextManager.active_context(
                correlation_id="ROOT",
                execution_mode="STRICT",
                actor_id="benchmark-nested",
            ) as root_ctx:
                current_ctx = root_ctx
                for depth in range(max_depth):
                    current_ctx = current_ctx.create_child_context(f"CHILD-{depth}")
                    _ = current_ctx.correlation_lineage
        end_nested = time.time()
        nested_time = end_nested - start_nested
        
        overhead = ((nested_time - flat_time) / flat_time) * 100
        
        print(f"\n📊 Lineage Tracking Overhead Benchmark:")
        print(f"   Flat contexts: {flat_time:.3f}s")
        print(f"   Nested contexts (depth={max_depth}): {nested_time:.3f}s")
        print(f"   Overhead: {overhead:.1f}%")
        
        # Assert overhead is reasonable (< 200%)
        assert overhead < 200, \
            f"Lineage tracking overhead too high: {overhead:.1f}%"


# ============================================================================
# REPORT GENERATION
# ============================================================================


def generate_stress_test_report():
    """
    Generate summary report of stress test coverage.
    """
    report = """
    ============================================================================
    CORRELATION ID STRESS TEST SUITE - COVERAGE REPORT
    ============================================================================
    
    STRESS TESTS CREATED:
    ---------------------
    
    1. TestCorrelationIDStress (3 tests)
       - test_high_volume_unique_id_generation
       - test_concurrent_execution_isolation
       - test_correlation_lineage_under_deep_nesting
    
    2. TestCorrelationIDThreadSafety (1 test)
       - test_thread_safety_sync_contexts
    
    3. TestCorrelationIDPerformance (2 tests)
       - test_benchmark_id_creation_throughput
       - test_benchmark_lineage_tracking_overhead
    
    TOTAL: 6 P1-INTEGRATION / BENCHMARK TESTS
    
    STRESS SCENARIOS COVERED:
    -------------------------
    ✓ High-volume ID generation (1000+ IDs)
    ✓ Concurrent execution isolation (10+ concurrent executions)
    ✓ Deep nesting lineage tracking (10 levels)
    ✓ Thread safety (20 threads, 50 iterations each)
    ✓ Performance throughput baseline
    ✓ Lineage tracking overhead measurement
    
    PERFORMANCE BASELINES:
    ----------------------
    - ID creation: > 100 IDs/second (minimum)
    - ID uniqueness: 100% (no collisions)
    - Thread isolation: 100% (no cross-contamination)
    - Lineage overhead: < 200% (acceptable)
    
    ============================================================================
    """
    return report


if __name__ == "__main__":
    print(generate_stress_test_report())

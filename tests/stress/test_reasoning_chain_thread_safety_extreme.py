"""
EXTREME Stress Test: ReasoningChain Thread Safety
==================================================

Tests the thread-safe AtomicCounter/AtomicFloat implementation under
extreme concurrent load to ensure no race conditions exist.

Tier 1 Hardening - Task #1 Verification
"""

import pytest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from mahoun.reasoning.reasoning_chain import ReasoningChain, ReasoningConfig, ReasoningMode, AtomicCounter, AtomicFloat


@pytest.mark.stress
@pytest.mark.slow
def test_atomic_counter_extreme_concurrency():
    """
    EXTREME: Test AtomicCounter under 10,000 concurrent increments.
    
    If not thread-safe, final count will be less than 10,000.
    """
    counter = AtomicCounter(0)
    num_threads = 100
    increments_per_thread = 100
    
    def increment_many():
        for _ in range(increments_per_thread):
            counter.increment()
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(increment_many) for _ in range(num_threads)]
        for future in as_completed(futures):
            future.result()  # Wait for all
    
    expected = num_threads * increments_per_thread
    actual = counter.get()
    
    assert actual == expected, f"Race condition detected! Expected {expected}, got {actual}"


@pytest.mark.stress
@pytest.mark.slow
def test_atomic_float_extreme_precision():
    """
    EXTREME: Test AtomicFloat precision under concurrent additions.
    
    Tests floating point arithmetic doesn't lose precision under concurrency.
    """
    accumulator = AtomicFloat(0.0)
    num_threads = 50
    additions_per_thread = 1000
    value_to_add = 0.001  # Small float
    
    def add_many():
        for _ in range(additions_per_thread):
            accumulator.add(value_to_add)
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(add_many) for _ in range(num_threads)]
        for future in as_completed(futures):
            future.result()
    
    expected = num_threads * additions_per_thread * value_to_add
    actual = accumulator.get()
    
    # Allow small floating point error
    assert abs(actual - expected) < 0.01, f"Precision loss detected! Expected {expected:.3f}, got {actual:.3f}"


@pytest.mark.stress
@pytest.mark.slow
def test_reasoning_chain_mixed_success_failure_stats():
    """
    HARD: Test statistics with mixed success/failure under concurrency.
    
    50% pass, 50% fail - verify counts are accurate.
    """
    chain = ReasoningChain(config=ReasoningConfig(enabled=False))
    
    num_threads = 100
    
    def update_pass(thread_id):
        chain._update_stats(
            nli_verified=(thread_id % 2 == 0),  # 50% pass
            citations_valid=(thread_id % 2 == 0),
            time_ms=float(thread_id)
        )
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(update_pass, i) for i in range(num_threads)]
        for future in as_completed(futures):
            future.result()
    
    stats = chain.get_stats()
    
    assert stats["total_processed"] == num_threads
    assert stats["nli_verified_count"] == num_threads // 2
    assert stats["citations_valid_count"] == num_threads // 2
    assert 0.0 <= stats["nli_pass_rate"] <= 1.0
    assert abs(stats["nli_pass_rate"] - 0.5) < 0.01  # Should be ~50%


@pytest.mark.stress
@pytest.mark.slow
def test_atomic_counter_deadlock_prevention():
    """
    ADVERSARIAL: Try to cause deadlock with nested lock acquisition.
    
    This should NOT deadlock due to proper lock design.
    """
    counter = AtomicCounter(0)
    
    def risky_operation():
        """Try to cause deadlock by nested access"""
        val1 = counter.get()
        counter.increment()
        val2 = counter.get()
        assert val2 > val1  # Should always be true
    
    # Run many times in parallel
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(risky_operation) for _ in range(1000)]
        
        # This should complete without deadlock
        start = time.time()
        for future in as_completed(futures, timeout=5.0):
            future.result()
        elapsed = time.time() - start
        
        assert elapsed < 3.0, f"Possible deadlock - took {elapsed:.2f}s"


@pytest.mark.stress
@pytest.mark.slow
def test_get_stats_consistency_under_writes():
    """
    ADVERSARIAL: Read stats while writes are happening.
    
    Tests that get_stats() returns consistent snapshot even during concurrent writes.
    """
    chain = ReasoningChain(config=ReasoningConfig(enabled=False))
    
    stop_writing = threading.Event()
    inconsistencies = []
    
    def continuous_writer():
        """Keep writing stats"""
        while not stop_writing.is_set():
            chain._update_stats(True, True, 10.0)
            time.sleep(0.001)
    
    def continuous_reader():
        """Keep reading stats and check consistency"""
        for _ in range(1000):
            stats = chain.get_stats()
            
            # Check internal consistency
            if stats["total_processed"] > 0:
                if stats["nli_pass_rate"] < 0 or stats["nli_pass_rate"] > 1:
                    inconsistencies.append(f"Invalid pass rate: {stats['nli_pass_rate']}")
                
                # NLI count should never exceed total
                if stats["nli_verified_count"] > stats["total_processed"]:
                    inconsistencies.append("NLI count > total!")
            
            time.sleep(0.001)
    
    # Start writer thread
    writer_thread = threading.Thread(target=continuous_writer)
    writer_thread.start()
    
    # Run multiple readers
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(continuous_reader) for _ in range(5)]
        for future in as_completed(futures):
            future.result()
    
    # Stop writer
    stop_writing.set()
    writer_thread.join()
    
    assert len(inconsistencies) == 0, f"Found inconsistencies: {inconsistencies}"


@pytest.mark.stress
@pytest.mark.slow
def test_reasoning_mode_strict_default_under_concurrency():
    """
    REGRESSION: Verify STRICT mode default persists under concurrent instantiation.
    
    Tests Task #2 fix doesn't regress under concurrent chain creation.
    """
    num_chains = 100
    
    def create_chain():
        chain = ReasoningChain()  # No config = use default
        return chain.config.mode
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(create_chain) for _ in range(num_chains)]
        modes = [future.result() for future in as_completed(futures)]
    
    # ALL must be STRICT
    assert all(mode == ReasoningMode.STRICT for mode in modes), \
        f"Some chains got wrong default mode: {set(modes)}"


if __name__ == "__main__":
    # Run a quick smoke test
    print("🔥 Running Thread Safety Smoke Test...")
    test_atomic_counter_extreme_concurrency()
    print("✅ AtomicCounter: PASSED")
    
    test_atomic_float_extreme_precision()
    print("✅ AtomicFloat: PASSED")
    
    print("\n🎉 All smoke tests passed! Run full suite with pytest.")

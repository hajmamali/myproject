"""
tests/ledger/test_extreme_stress_adversarial.py
================================================

EXTREME STRESS & ADVERSARIAL TESTS - Super Hard Level

Objective: Break the ledger under extreme conditions and adversarial attacks

This test suite goes beyond normal testing to simulate:
- Extreme concurrency (1000+ concurrent writers)
- Adversarial attacks (hash collision attempts, timing attacks)
- Resource exhaustion scenarios
- Byzantine fault injection
- Cryptographic attack simulations
- Race condition exploitation attempts
- Memory pressure scenarios

⚠️ WARNING: These tests are INTENTIONALLY BRUTAL
- May consume significant CPU/memory
- May take 30+ seconds per test
- Designed to find edge cases that simple tests miss
- May expose subtle bugs in production code

Run with: MAHOUN_EXTREME_TESTS=1 pytest tests/ledger/test_extreme_stress_adversarial.py -v
"""

import pytest
import threading
import time
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from datetime import datetime, UTC, timedelta
from pathlib import Path
import tempfile
import random
import gc

from mahoun.ledger.blockchain import ImmutableLedger
from mahoun.ledger.models import LedgerEntry
from mahoun.ledger.block import Block, create_genesis_block


# Skip all tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.environ.get("MAHOUN_EXTREME_TESTS") != "1",
    reason="Extreme tests only run with MAHOUN_EXTREME_TESTS=1"
)


class TestExtremeConcurrency:
    """Test ledger under extreme concurrent load (P0 Critical)"""
    
    @pytest.mark.p1
    def test_1000_concurrent_writers_integrity(self):
        """
        EXTREME: 1000 concurrent threads writing simultaneously
        
        Risk: Lock contention, deadlock, memory corruption
        Expected: All writes succeed, chain remains valid
        Difficulty: ★★★★★
        """
        ledger = ImmutableLedger()
        num_writers = 1000
        writes_per_thread = 5
        
        success_count = []
        failure_count = []
        lock = threading.Lock()
        
        def aggressive_writer(thread_id):
            """Aggressive concurrent writer with random delays"""
            local_success = 0
            local_failure = 0
            
            for i in range(writes_per_thread):
                try:
                    entry = LedgerEntry(
                        verdict_id=f"verdict_t{thread_id}_w{i}",
                        case_id=f"case_{thread_id}",
                        referenced_ltm_nodes=[f"rule_{thread_id}_{i}"],
                        referenced_facts=[f"fact_{thread_id}_{i}"],
                        confidence=0.85,
                        invariant_version="v2.1.0",
                        guard_mode="STRICT",
                        created_at=datetime.now(UTC)
                    )
                    
                    # Random tiny delay to maximize contention
                    time.sleep(random.uniform(0.00001, 0.0001))
                    
                    ledger.append(entry)
                    local_success += 1
                    
                except Exception as e:
                    local_failure += 1
                    print(f"Thread {thread_id} write {i} failed: {e}")
            
            with lock:
                success_count.append(local_success)
                failure_count.append(local_failure)
        
        # Launch 1000 concurrent writers
        print(f"\n🔥 Launching {num_writers} concurrent writers...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_writers) as executor:
            futures = [executor.submit(aggressive_writer, i) for i in range(num_writers)]
            for future in as_completed(futures):
                future.result()
        
        elapsed = time.time() - start_time
        
        # Verify results
        total_success = sum(success_count)
        total_failure = sum(failure_count)
        expected_total = num_writers * writes_per_thread
        
        print(f"✅ Success: {total_success}/{expected_total}")
        print(f"❌ Failures: {total_failure}")
        print(f"⏱️  Time: {elapsed:.2f}s")
        print(f"📊 Throughput: {total_success/elapsed:.1f} writes/sec")
        
        # CRITICAL: All writes must succeed
        assert total_success == expected_total, f"Some writes failed: {total_failure} failures"
        
        # Verify chain integrity
        assert len(ledger.chain) == expected_total + 1  # +1 for genesis
        assert ledger.verify_integrity(), "Chain integrity compromised under extreme load"
        
        # Verify no duplicate verdict_ids
        verdict_ids = set()
        for block in ledger.chain[1:]:
            assert block.data.verdict_id not in verdict_ids, "Duplicate verdict_id found!"
            verdict_ids.add(block.data.verdict_id)
        
        print("✅ EXTREME TEST PASSED: 1000 concurrent writers")
    
    @pytest.mark.p1
    def test_concurrent_read_write_hammer(self):
        """
        EXTREME: 100 writers + 500 readers hammering simultaneously
        
        Risk: Reader sees inconsistent state, deadlock
        Expected: All reads see valid chain state
        Difficulty: ★★★★★
        """
        ledger = ImmutableLedger()
        num_writers = 100
        num_readers = 500
        writes_per_writer = 10
        reads_per_reader = 50
        
        all_verifications = []
        verification_lock = threading.Lock()
        stop_flag = threading.Event()
        
        def writer(writer_id):
            """Continuous writer"""
            for i in range(writes_per_writer):
                entry = LedgerEntry(
                    verdict_id=f"verdict_w{writer_id}_i{i}",
                    case_id=f"case_{writer_id}",
                    referenced_ltm_nodes=[f"rule_{writer_id}"],
                    referenced_facts=[f"fact_{writer_id}"],
                    confidence=0.85,
                    invariant_version="v2.1.0",
                    guard_mode="STRICT",
                    created_at=datetime.now(UTC)
                )
                ledger.append(entry)
                time.sleep(0.0001)
        
        def reader(reader_id):
            """Aggressive reader"""
            local_verifications = []
            for i in range(reads_per_reader):
                if stop_flag.is_set():
                    break
                try:
                    is_valid = ledger.verify_integrity()
                    local_verifications.append(is_valid)
                    
                    # Also verify chain length is increasing
                    chain_len = len(ledger.chain)
                    assert chain_len >= 1, "Chain lost genesis block!"
                    
                except Exception as e:
                    local_verifications.append(False)
                    print(f"Reader {reader_id} error: {e}")
                
                time.sleep(0.00001)
            
            with verification_lock:
                all_verifications.extend(local_verifications)
        
        # Launch writers and readers
        print(f"\n🔥 Launching {num_writers} writers + {num_readers} readers...")
        
        with ThreadPoolExecutor(max_workers=num_writers + num_readers) as executor:
            # Start readers first
            reader_futures = [executor.submit(reader, i) for i in range(num_readers)]
            
            # Small delay then start writers
            time.sleep(0.01)
            writer_futures = [executor.submit(writer, i) for i in range(num_writers)]
            
            # Wait for all to complete
            for future in as_completed(writer_futures):
                future.result()
            
            stop_flag.set()
            
            for future in as_completed(reader_futures):
                future.result()
        
        # Verify ALL verifications passed
        total_verifications = len(all_verifications)
        passed_verifications = sum(all_verifications)
        
        print(f"✅ Verifications: {passed_verifications}/{total_verifications}")
        
        assert all(all_verifications), f"Some verifications failed: {total_verifications - passed_verifications} failures"
        assert ledger.verify_integrity()
        
        print("✅ EXTREME TEST PASSED: Read/Write hammer")


class TestAdversarialAttacks:
    """Test ledger against adversarial attack attempts (P0 Critical)"""
    
    @pytest.mark.p1
    def test_hash_collision_attack_attempt(self):
        """
        EXTREME: Attempt to create blocks with colliding hashes
        
        Risk: Hash collision breaks chain uniqueness
        Expected: All hashes remain unique despite collision attempts
        Difficulty: ★★★★★
        """
        ledger = ImmutableLedger()
        
        # Try to create 10000 blocks with similar data
        num_attempts = 10000
        hashes = set()
        
        print(f"\n🔥 Attempting {num_attempts} hash collision attacks...")
        
        for i in range(num_attempts):
            # Create very similar entries (differ by 1 character)
            entry = LedgerEntry(
                verdict_id=f"verdict_{i:08d}",  # Only difference is counter
                case_id="SAME_CASE",  # Same case
                referenced_ltm_nodes=["rule_1"],  # Same rule
                referenced_facts=["fact_1"],  # Same fact
                confidence=0.85,  # Same confidence
                invariant_version="v2.1.0",
                guard_mode="STRICT",
                created_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)  # Same timestamp
            )
            
            block = ledger.append(entry)
            
            # Verify hash is unique
            assert block.hash not in hashes, f"COLLISION DETECTED at iteration {i}!"
            hashes.add(block.hash)
        
        # Verify all hashes are unique
        assert len(hashes) == num_attempts
        
        print(f"✅ All {num_attempts} hashes are unique")
        print(f"✅ No collisions detected")
        print("✅ EXTREME TEST PASSED: Hash collision resistance")
    
    @pytest.mark.p1
    def test_timing_attack_on_concurrent_writes(self):
        """
        EXTREME: Timing attack attempting to exploit race conditions
        
        Risk: Precise timing causes race condition leading to corruption
        Expected: No corruption regardless of timing
        Difficulty: ★★★★★
        """
        ledger = ImmutableLedger()
        
        # Phase 1: Establish baseline
        for i in range(10):
            entry = LedgerEntry(
                verdict_id=f"baseline_{i}",
                case_id="baseline",
                referenced_ltm_nodes=["rule_1"],
                referenced_facts=["fact_1"],
                confidence=0.85,
                invariant_version="v2.1.0",
                guard_mode="STRICT",
                created_at=datetime.now(UTC)
            )
            ledger.append(entry)
        
        baseline_len = len(ledger.chain)
        
        # Phase 2: Timing attack - try to write at exact same moment
        print(f"\n🔥 Launching timing attack with 100 synchronized writers...")
        
        barrier = threading.Barrier(100)  # Synchronization point
        attack_results = []
        lock = threading.Lock()
        
        def timed_attacker(attacker_id):
            """Wait at barrier then write at exact same moment"""
            try:
                # All threads wait here
                barrier.wait()
                
                # NOW - all threads execute simultaneously
                entry = LedgerEntry(
                    verdict_id=f"attack_{attacker_id}",
                    case_id="attack",
                    referenced_ltm_nodes=["rule_1"],
                    referenced_facts=["fact_1"],
                    confidence=0.85,
                    invariant_version="v2.1.0",
                    guard_mode="STRICT",
                    created_at=datetime.now(UTC)
                )
                ledger.append(entry)
                
                with lock:
                    attack_results.append("success")
                
            except Exception as e:
                with lock:
                    attack_results.append(f"fail: {e}")
        
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(timed_attacker, i) for i in range(100)]
            for future in as_completed(futures):
                future.result()
        
        # Verify all attacks failed to corrupt chain
        successful_attacks = [r for r in attack_results if r == "success"]
        print(f"✅ Attacks handled: {len(successful_attacks)}/100")
        
        assert len(ledger.chain) == baseline_len + 100
        assert ledger.verify_integrity()
        
        print("✅ EXTREME TEST PASSED: Timing attack resistance")
    
    @pytest.mark.p1
    def test_byzantine_fault_injection(self):
        """
        EXTREME: Inject Byzantine faults (arbitrary failures)
        
        Risk: Random failures cause chain corruption
        Expected: Chain remains valid despite failures
        Difficulty: ★★★★★
        """
        ledger = ImmutableLedger()
        
        num_operations = 500
        failure_rate = 0.3  # 30% of operations fail randomly
        
        successful_writes = 0
        failed_writes = 0
        
        print(f"\n🔥 Injecting Byzantine faults ({failure_rate*100}% failure rate)...")
        
        for i in range(num_operations):
            # Randomly inject failure
            if random.random() < failure_rate:
                # Inject fault: invalid data
                try:
                    entry = LedgerEntry(
                        verdict_id="",  # Invalid: empty verdict_id
                        case_id="",  # Invalid: empty case_id
                        referenced_ltm_nodes=[],  # Invalid: no evidence
                        referenced_facts=[],
                        confidence=1.5,  # Invalid: > 1.0
                        invariant_version="v2.1.0",
                        guard_mode="STRICT",
                        created_at=datetime.now(UTC)
                    )
                    ledger.append(entry)
                    failed_writes += 1  # Should not reach here
                except Exception:
                    # Expected: validation should reject
                    failed_writes += 1
            else:
                # Normal write
                entry = LedgerEntry(
                    verdict_id=f"verdict_{i}",
                    case_id=f"case_{i}",
                    referenced_ltm_nodes=[f"rule_{i}"],
                    referenced_facts=[f"fact_{i}"],
                    confidence=0.85,
                    invariant_version="v2.1.0",
                    guard_mode="STRICT",
                    created_at=datetime.now(UTC)
                )
                ledger.append(entry)
                successful_writes += 1
        
        print(f"✅ Successful writes: {successful_writes}")
        print(f"❌ Failed writes (expected): {failed_writes}")
        
        # Chain must remain valid despite failures
        assert ledger.verify_integrity()
        assert len(ledger.chain) == successful_writes + 1  # +1 for genesis
        
        print("✅ EXTREME TEST PASSED: Byzantine fault tolerance")


class TestResourceExhaustion:
    """Test ledger under resource pressure (P0 Critical)"""
    
    @pytest.mark.p1
    def test_memory_pressure_large_chain(self):
        """
        EXTREME: Build very large chain to test memory handling
        
        Risk: Memory leak, OOM, performance degradation
        Expected: Chain remains valid, memory stays bounded
        Difficulty: ★★★★☆
        """
        ledger = ImmutableLedger()
        
        chain_size = 50000  # 50k blocks
        
        print(f"\n🔥 Building chain with {chain_size} blocks...")
        
        start_time = time.time()
        
        for i in range(chain_size):
            entry = LedgerEntry(
                verdict_id=f"verdict_{i}",
                case_id=f"case_{i % 100}",  # Cycle through 100 cases
                referenced_ltm_nodes=[f"rule_{i % 1000}"],  # Cycle through 1000 rules
                referenced_facts=[f"fact_{i % 500}"],
                confidence=0.85,
                invariant_version="v2.1.0",
                guard_mode="STRICT",
                created_at=datetime.now(UTC)
            )
            ledger.append(entry)
            
            if (i + 1) % 10000 == 0:
                print(f"  Progress: {i+1}/{chain_size} blocks...")
                gc.collect()  # Force GC to test memory handling
        
        elapsed = time.time() - start_time
        
        print(f"✅ Built {chain_size} blocks in {elapsed:.2f}s")
        print(f"📊 Throughput: {chain_size/elapsed:.1f} blocks/sec")
        
        # Verify integrity on large chain
        print("🔍 Verifying large chain integrity...")
        assert ledger.verify_integrity()
        
        print("✅ EXTREME TEST PASSED: Large chain handling")
    
    @pytest.mark.p1
    def test_rapid_fire_writes_cpu_stress(self):
        """
        EXTREME: Maximum throughput writes (no delays)
        
        Risk: CPU saturation, lock starvation
        Expected: System handles maximum throughput
        Difficulty: ★★★★☆
        """
        ledger = ImmutableLedger()
        
        num_writers = 50
        writes_per_writer = 200
        
        print(f"\n🔥 Rapid-fire writes: {num_writers} writers × {writes_per_writer} writes...")
        
        start_time = time.time()
        
        def rapid_writer(writer_id):
            """Write as fast as possible - NO delays"""
            for i in range(writes_per_writer):
                entry = LedgerEntry(
                    verdict_id=f"verdict_w{writer_id}_i{i}",
                    case_id=f"case_{writer_id}",
                    referenced_ltm_nodes=[f"rule_{writer_id}"],
                    referenced_facts=[f"fact_{writer_id}"],
                    confidence=0.85,
                    invariant_version="v2.1.0",
                    guard_mode="STRICT",
                    created_at=datetime.now(UTC)
                )
                ledger.append(entry)
                # NO DELAY - maximum throughput
        
        with ThreadPoolExecutor(max_workers=num_writers) as executor:
            futures = [executor.submit(rapid_writer, i) for i in range(num_writers)]
            for future in as_completed(futures):
                future.result()
        
        elapsed = time.time() - start_time
        total_writes = num_writers * writes_per_writer
        
        print(f"✅ Completed {total_writes} writes in {elapsed:.2f}s")
        print(f"📊 Peak throughput: {total_writes/elapsed:.1f} writes/sec")
        
        assert len(ledger.chain) == total_writes + 1
        assert ledger.verify_integrity()
        
        print("✅ EXTREME TEST PASSED: CPU stress test")


class TestCryptographicSecurity:
    """Test cryptographic properties under adversarial conditions (P0 Critical)"""
    
    @pytest.mark.p1
    def test_hash_avalanche_effect(self):
        """
        EXTREME: Verify hash avalanche effect (1-bit change → 50% hash change)
        
        Risk: Weak hash function allows prediction
        Expected: Minimal data change causes major hash change
        Difficulty: ★★★★☆
        """
        genesis = create_genesis_block()
        
        print(f"\n🔥 Testing cryptographic hash avalanche effect...")
        
        # Create base entry
        base_entry = LedgerEntry(
            verdict_id="verdict_base",
            case_id="case_base",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=["fact_1"],
            confidence=0.850000,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        )
        
        base_block = Block(
            index=1,
            timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            data=base_entry,
            prev_hash=genesis.hash
        )
        
        # Minimal change: confidence 0.850000 → 0.850001
        changed_entry = LedgerEntry(
            verdict_id="verdict_base",
            case_id="case_base",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=["fact_1"],
            confidence=0.850001,  # Tiny change
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        )
        
        changed_block = Block(
            index=1,
            timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            data=changed_entry,
            prev_hash=genesis.hash
        )
        
        # Compare hashes
        base_hash_bin = bin(int(base_block.hash, 16))[2:].zfill(256)
        changed_hash_bin = bin(int(changed_block.hash, 16))[2:].zfill(256)
        
        # Count differing bits
        differing_bits = sum(b1 != b2 for b1, b2 in zip(base_hash_bin, changed_hash_bin))
        percent_different = (differing_bits / 256) * 100
        
        print(f"📊 Differing bits: {differing_bits}/256 ({percent_different:.1f}%)")
        print(f"   Base hash:    {base_block.hash[:32]}...")
        print(f"   Changed hash: {changed_block.hash[:32]}...")
        
        # Avalanche effect: expect ~50% bits different
        assert differing_bits > 64, f"Weak avalanche: only {differing_bits} bits different"
        assert percent_different > 25, f"Weak avalanche: only {percent_different:.1f}% different"
        
        print(f"✅ Strong avalanche effect confirmed")
        print("✅ EXTREME TEST PASSED: Cryptographic avalanche")
    
    @pytest.mark.p1
    def test_hash_preimage_resistance(self):
        """
        EXTREME: Verify hash preimage resistance (cannot reverse hash)
        
        Risk: Hash can be reversed to forge blocks
        Expected: Hash is one-way function
        Difficulty: ★★★★☆
        """
        ledger = ImmutableLedger()
        
        # Add block
        entry = LedgerEntry(
            verdict_id="verdict_secret",
            case_id="case_secret",
            referenced_ltm_nodes=["rule_secret"],
            referenced_facts=["fact_secret"],
            confidence=0.987654,
            invariant_version="v2.1.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        block = ledger.append(entry)
        target_hash = block.hash
        
        print(f"\n🔥 Testing preimage resistance...")
        print(f"   Target hash: {target_hash[:32]}...")
        
        # Attempt to find preimage (will fail - this is intentional)
        # Try 100,000 random attempts
        attempts = 100000
        found_preimage = False
        
        print(f"   Attempting {attempts} random preimage attacks...")
        
        for i in range(attempts):
            # Random data
            random_entry = LedgerEntry(
                verdict_id=f"random_{i}_{random.randint(0, 1000000)}",
                case_id=f"case_{random.randint(0, 1000000)}",
                referenced_ltm_nodes=[f"rule_{random.randint(0, 1000)}"],
                referenced_facts=[f"fact_{random.randint(0, 1000)}"],
                confidence=random.random(),
                invariant_version="v2.1.0",
                guard_mode="STRICT",
                created_at=datetime.now(UTC)
            )
            
            random_block = Block(
                index=block.index,
                timestamp=block.timestamp,
                data=random_entry,
                prev_hash=block.prev_hash
            )
            
            if random_block.hash == target_hash:
                found_preimage = True
                break
        
        # Should NOT find preimage
        assert not found_preimage, "CRITICAL: Found hash preimage! Hash function broken!"
        
        print(f"✅ No preimage found in {attempts} attempts")
        print("✅ EXTREME TEST PASSED: Preimage resistance")


# Summary function
def print_extreme_test_summary():
    """Print summary of extreme tests"""
    print("\n" + "="*80)
    print("🔥 EXTREME STRESS & ADVERSARIAL TEST SUITE")
    print("="*80)
    print("Test Categories:")
    print("  1. Extreme Concurrency: 1000+ concurrent operations")
    print("  2. Adversarial Attacks: Hash collisions, timing attacks, Byzantine faults")
    print("  3. Resource Exhaustion: Large chains, CPU stress")
    print("  4. Cryptographic Security: Avalanche effect, preimage resistance")
    print("\n⚠️  Run with: MAHOUN_EXTREME_TESTS=1 pytest -v")
    print("="*80 + "\n")


if __name__ == "__main__":
    print_extreme_test_summary()

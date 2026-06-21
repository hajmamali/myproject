"""
Comprehensive tests for AsyncLedgerWriter
=========================================

Tests async I/O, batching, retry logic, and DLQ.
"""

import pytest
import asyncio
import time
from pathlib import Path
from datetime import datetime, timezone

from mahoun.ledger.async_writer import AsyncLedgerWriter, WriteResult
from mahoun.ledger.models import LedgerEntry
from mahoun.ledger.storage import FileLedgerBackend


@pytest.fixture
def temp_ledger_path(tmp_path):
    """Create temporary ledger path"""
    return tmp_path / "ledger"


@pytest.fixture
def temp_dlq_path(tmp_path):
    """Create temporary DLQ path"""
    return tmp_path / "dlq"


@pytest.fixture
async def writer(temp_ledger_path, temp_dlq_path):
    """Create async ledger writer"""
    backend = FileLedgerBackend(temp_ledger_path)
    writer = AsyncLedgerWriter(
        backend=backend,
        batch_size=10,
        flush_interval_sec=0.5,
        dlq_path=temp_dlq_path
    )
    
    await writer.start()
    yield writer
    await writer.stop()


class TestBasicOperations:
    """Test basic async operations"""
    
    @pytest.mark.asyncio
    async def test_single_write(self, writer):
        """Test writing single entry"""
        entry = LedgerEntry(
            verdict_id="v1",
            case_id="c1",
            referenced_ltm_nodes=["rule1"],
            referenced_facts=["fact1"],
            confidence=0.9,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        result = await writer.write(entry)
        
        assert result.success
        assert result.entry_hash is not None
        assert len(result.entry_hash) == 64  # SHA256
    
    @pytest.mark.asyncio
    async def test_multiple_writes(self, writer):
        """Test writing multiple entries"""
        results = []
        
        for i in range(50):
            entry = LedgerEntry(
                verdict_id=f"v{i}",
                case_id=f"c{i}",
                referenced_ltm_nodes=[f"rule{i}"],
                referenced_facts=[f"fact{i}"],
                confidence=0.9,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now(timezone.utc)
            )
            
            result = await writer.write(entry)
            results.append(result)
        
        # All successful
        assert all(r.success for r in results)
        
        # All have unique hashes
        hashes = [r.entry_hash for r in results]
        assert len(set(hashes)) == len(hashes)
    
    @pytest.mark.asyncio
    async def test_hash_chain_integrity(self, writer):
        """Test that hash chain is maintained"""
        results = []
        
        for i in range(20):
            entry = LedgerEntry(
                verdict_id=f"v{i}",
                case_id=f"c{i}",
                referenced_ltm_nodes=[],
                referenced_facts=[],
                confidence=0.9,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now(timezone.utc)
            )
            
            result = await writer.write(entry)
            results.append(result)
        
        # Wait for flush
        await asyncio.sleep(1.0)
        
        # All hashes should be different (chain property)
        hashes = [r.entry_hash for r in results]
        assert len(set(hashes)) == len(hashes)


class TestBatching:
    """Test batch processing"""
    
    @pytest.mark.asyncio
    async def test_batch_writes(self, temp_ledger_path, temp_dlq_path):
        """Test that writes are batched"""
        backend = FileLedgerBackend(temp_ledger_path)
        writer = AsyncLedgerWriter(
            backend=backend,
            batch_size=10,
            flush_interval_sec=5.0,  # Long interval
            dlq_path=temp_dlq_path
        )
        
        await writer.start()
        
        try:
            # Write 25 entries (should create 3 batches: 10, 10, 5)
            for i in range(25):
                entry = LedgerEntry(
                    verdict_id=f"v{i}",
                    case_id=f"c{i}",
                    referenced_ltm_nodes=[],
                    referenced_facts=[],
                    confidence=0.9,
                    invariant_version="1.0.0",
                    guard_mode="STRICT",
                    created_at=datetime.now(timezone.utc)
                )
                
                await writer.write(entry)
            
            # Wait for batches to process
            await asyncio.sleep(0.5)
            
            stats = writer.get_stats()
            
            # Should have processed 3 batches
            assert stats["total_batches"] >= 2
            assert stats["successful_writes"] == 25
            
        finally:
            await writer.stop()
    
    @pytest.mark.asyncio
    async def test_auto_flush_on_interval(self, temp_ledger_path, temp_dlq_path):
        """Test auto-flush based on time interval"""
        backend = FileLedgerBackend(temp_ledger_path)
        writer = AsyncLedgerWriter(
            backend=backend,
            batch_size=100,  # Large batch
            flush_interval_sec=0.5,  # Short interval
            dlq_path=temp_dlq_path
        )
        
        await writer.start()
        
        try:
            # Write only 5 entries (less than batch size)
            for i in range(5):
                entry = LedgerEntry(
                    verdict_id=f"v{i}",
                    case_id=f"c{i}",
                    referenced_ltm_nodes=[],
                    referenced_facts=[],
                    confidence=0.9,
                    invariant_version="1.0.0",
                    guard_mode="STRICT",
                    created_at=datetime.now(timezone.utc)
                )
                
                await writer.write(entry)
            
            # Wait for auto-flush
            await asyncio.sleep(1.0)
            
            stats = writer.get_stats()
            
            # Should have flushed despite small batch
            assert stats["successful_writes"] == 5
            assert stats["total_batches"] >= 1
            
        finally:
            await writer.stop()


class TestPerformance:
    """Test performance under load"""
    
    @pytest.mark.asyncio
    async def test_high_throughput(self, writer):
        """Test high-throughput writes"""
        num_entries = 1000
        
        start_time = time.time()
        
        # Write concurrently
        tasks = []
        for i in range(num_entries):
            entry = LedgerEntry(
                verdict_id=f"v{i}",
                case_id=f"c{i}",
                referenced_ltm_nodes=[],
                referenced_facts=[],
                confidence=0.9,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now(timezone.utc)
            )
            
            task = asyncio.create_task(writer.write(entry))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        throughput = num_entries / elapsed
        
        print(f"\nThroughput: {throughput:.0f} writes/sec")
        print(f"Total time: {elapsed:.2f}s")
        
        # All successful
        assert all(r.success for r in results)
        
        # Should handle 1000+ writes/sec
        assert throughput > 500  # Conservative target
    
    @pytest.mark.asyncio
    async def test_latency(self, writer):
        """Test write latency"""
        latencies = []
        
        for i in range(100):
            entry = LedgerEntry(
                verdict_id=f"v{i}",
                case_id=f"c{i}",
                referenced_ltm_nodes=[],
                referenced_facts=[],
                confidence=0.9,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now(timezone.utc)
            )
            
            start = time.time()
            await writer.write(entry)
            latency = (time.time() - start) * 1000  # ms
            
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        print(f"\nAvg latency: {avg_latency:.2f}ms")
        print(f"P95 latency: {p95_latency:.2f}ms")
        
        # Should be fast (batched)
        assert avg_latency < 50  # <50ms average
        assert p95_latency < 100  # <100ms p95


class TestErrorHandling:
    """Test error handling and retry logic"""
    
    @pytest.mark.asyncio
    async def test_backpressure(self, temp_ledger_path, temp_dlq_path):
        """Test backpressure when queue is full"""
        backend = FileLedgerBackend(temp_ledger_path)
        writer = AsyncLedgerWriter(
            backend=backend,
            batch_size=10,
            max_queue_size=50,  # Small queue
            flush_interval_sec=10.0,  # Long interval (slow flush)
            dlq_path=temp_dlq_path
        )
        
        await writer.start()
        
        try:
            # Try to write more than queue size
            results = []
            for i in range(100):
                entry = LedgerEntry(
                    verdict_id=f"v{i}",
                    case_id=f"c{i}",
                    referenced_ltm_nodes=[],
                    referenced_facts=[],
                    confidence=0.9,
                    invariant_version="1.0.0",
                    guard_mode="STRICT",
                    created_at=datetime.now(timezone.utc)
                )
                
                result = await writer.write(entry)
                results.append(result)
            
            # Some should fail due to backpressure
            failed = [r for r in results if not r.success]
            assert len(failed) > 0
            
            # Failed should have backpressure error
            assert any("backpressure" in r.error.lower() for r in failed if r.error)
            
        finally:
            await writer.stop()


class TestStatistics:
    """Test statistics and monitoring"""
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, writer):
        """Test that statistics are tracked correctly"""
        # Write some entries
        for i in range(20):
            entry = LedgerEntry(
                verdict_id=f"v{i}",
                case_id=f"c{i}",
                referenced_ltm_nodes=[],
                referenced_facts=[],
                confidence=0.9,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now(timezone.utc)
            )
            
            await writer.write(entry)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        stats = writer.get_stats()
        
        assert stats["total_writes"] == 20
        assert stats["successful_writes"] == 20
        assert stats["failed_writes"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["total_batches"] >= 1
        
        print(f"\nStats: {stats}")


@pytest.mark.slow
class TestStressTest:
    """Stress tests for extreme scenarios"""
    
    @pytest.mark.asyncio
    async def test_extreme_load(self, temp_ledger_path, temp_dlq_path):
        """Test under extreme load"""
        backend = FileLedgerBackend(temp_ledger_path)
        writer = AsyncLedgerWriter(
            backend=backend,
            batch_size=100,
            max_queue_size=10000,
            flush_interval_sec=0.5,
            dlq_path=temp_dlq_path
        )
        
        await writer.start()
        
        try:
            num_entries = 10000
            
            start_time = time.time()
            
            # Write concurrently
            tasks = []
            for i in range(num_entries):
                entry = LedgerEntry(
                    verdict_id=f"v{i}",
                    case_id=f"c{i}",
                    referenced_ltm_nodes=[],
                    referenced_facts=[],
                    confidence=0.9,
                    invariant_version="1.0.0",
                    guard_mode="STRICT",
                    created_at=datetime.now(timezone.utc)
                )
                
                task = asyncio.create_task(writer.write(entry))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            elapsed = time.time() - start_time
            throughput = num_entries / elapsed
            
            print(f"\nExtreme load: {num_entries} entries in {elapsed:.2f}s")
            print(f"Throughput: {throughput:.0f} writes/sec")
            
            # Most should succeed
            successful = [r for r in results if r.success]
            success_rate = len(successful) / len(results)
            
            assert success_rate > 0.95  # >95% success rate
            
        finally:
            await writer.stop()

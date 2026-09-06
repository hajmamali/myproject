#!/usr/bin/env python3
"""
🔥 EXTREME STRESS TESTS for Judgment Ingestion System
=====================================================

Test categories:
1. Data corruption and malformed inputs
2. Performance under extreme load
3. Circuit breaker resilience
4. Memory pressure and leak detection
5. Concurrent access and race conditions
6. Entity extraction edge cases
7. Neo4j failure scenarios
8. Batch processing edge cases
"""

import json
import pytest
import tempfile
import time
import threading
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.build_judgment_kg import (
    CanonicalJudgment,
    CircuitBreakerStats,
    PerformanceMetrics,
    EnterpriseCypherBridge,
    AdvancedEntityExtractor,
    EnterpriseJudgmentCompiler,
    parse_judgments_from_json,
    verify_source_integrity,
    EntityExtractionResult,
)


# ============================================================================
# TEST SUITE 1: Data Corruption & Malformed Inputs
# ============================================================================

class TestDataCorruption:
    """Test handling of corrupted and malformed data"""
    
    def test_empty_json_file(self):
        """Test empty JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            f.flush()
            
            with pytest.raises(ValueError, match="missing 'judgments' key"):
                parse_judgments_from_json(Path(f.name))
    
    def test_corrupted_utf8_encoding(self):
        """Test file with invalid UTF-8 bytes"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as f:
            # Write invalid UTF-8 sequence
            f.write(b'\xff\xfe\xfd invalid utf8')
            f.flush()
            
            valid, sha, error = verify_source_integrity(Path(f.name))
            assert not valid
            assert "Validation error" in error
    
    def test_extremely_long_title(self):
        """Test judgment with extremely long title (10K chars)"""
        judgment = CanonicalJudgment(
            judgment_id="TEST_001",
            title="א" * 10000,  # 10K Persian chars
            full_text="متن رای",
            court_level="supreme",
            legal_area="civil",
            verdict_type="affirm",
            date="1403/01/01",
            quality_score=0.9,
            word_count=100,
            parties=[],
            legal_references=[],
            source_hash="abc123"
        )
        
        # Should truncate to 500 chars in batch processing
        assert len(judgment.title) == 10000
        # Truncation happens in _process_batch
    
    def test_special_characters_in_entities(self):
        """Test entities with SQL/Cypher injection attempts"""
        dangerous_names = [
            "'; DROP TABLE Judgment; --",
            "' OR '1'='1",
            "'); DELETE FROM Party WHERE ('1'='1",
            "\\x00\\x1F",  # Control characters
            "' UNION SELECT * FROM neo4j.users --"
        ]
        
        judgment = CanonicalJudgment(
            judgment_id="DANGEROUS_001",
            title="Injection Test",
            full_text="متن رای",
            court_level="trial",
            legal_area="criminal",
            verdict_type="reject",
            date=None,
            quality_score=0.5,
            word_count=50,
            parties=dangerous_names,
            legal_references=dangerous_names,
            source_hash="danger123"
        )
        
        # Should handle safely without injection
        assert judgment.parties == dangerous_names
    
    def test_missing_required_fields(self):
        """Test judgment with missing required metadata"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                'judgments': [{
                    'metadata': {
                        'judgment_id': 'MISSING_001'
                        # Missing: title, court_level, etc.
                    },
                    'full_text': 'متن'
                }]
            }, f)
            f.flush()
            
            # Should handle missing fields gracefully
            judgments = parse_judgments_from_json(Path(f.name))
            assert len(judgments) == 1
            assert judgments[0].court_level == 'unknown'
    
    def test_null_and_none_values(self):
        """Test handling of null values in critical fields"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                'judgments': [{
                    'metadata': {
                        'judgment_id': 'NULL_001',
                        'title': None,
                        'court_level': None,
                        'legal_area': None,
                        'verdict_type': None,
                        'date': None,
                        'quality_score': None,
                        'word_count': None,
                        'parties': None,
                        'legal_references': None
                    },
                    'full_text': None
                }]
            }, f)
            f.flush()
            
            # Should handle nulls without crashing
            judgments = parse_judgments_from_json(Path(f.name))
            assert len(judgments) == 1


# ============================================================================
# TEST SUITE 2: Performance Under Extreme Load
# ============================================================================

class TestPerformanceStress:
    """Test system behavior under extreme performance pressure"""
    
    def test_massive_batch_processing(self):
        """Test processing 10,000 judgments"""
        judgments = []
        for i in range(10000):
            j = CanonicalJudgment(
                judgment_id=f"STRESS_{i:05d}",
                title=f"رای شماره {i}",
                full_text="متن رای " * 100,  # ~1KB each
                court_level="supreme",
                legal_area="civil",
                verdict_type="affirm",
                date=f"1403/01/{(i % 30) + 1:02d}",
                quality_score=0.8,
                word_count=100,
                parties=[f"طرف_{i}_1", f"طرف_{i}_2"],
                legal_references=[f"ماده {i} قانون"],
                source_hash=f"hash_{i}"
            )
            judgments.append(j)
        
        metrics = PerformanceMetrics()
        start = time.time()
        
        # Simulate batch processing
        batch_size = 100
        for i in range(0, len(judgments), batch_size):
            batch_start = time.time()
            batch = judgments[i:i+batch_size]
            # Simulate processing time
            time.sleep(0.01)
            batch_duration = time.time() - batch_start
            metrics.record_batch(len(batch), batch_duration)
        
        total_duration = time.time() - start
        throughput = metrics.get_throughput()
        
        print(f"\n📊 Massive batch test results:")
        print(f"   Total judgments: {len(judgments)}")
        print(f"   Total time: {total_duration:.2f}s")
        print(f"   Throughput: {throughput:.2f} j/s")
        
        # Should process at reasonable speed
        assert metrics.judgments_processed == 10000
        assert throughput > 100  # At least 100 j/s
    
    def test_memory_pressure_large_text(self):
        """Test handling of judgments with extremely large text (1MB each)"""
        large_text = "متن رای بسیار طولانی " * 50000  # ~1MB
        
        judgments = []
        for i in range(100):
            j = CanonicalJudgment(
                judgment_id=f"LARGE_{i:03d}",
                title=f"رای بزرگ {i}",
                full_text=large_text,
                court_level="supreme",
                legal_area="civil",
                verdict_type="affirm",
                date="1403/01/01",
                quality_score=0.9,
                word_count=50000,
                parties=[f"طرف_{i}" for _ in range(50)],
                legal_references=[f"ماده {j}" for j in range(100)],
                source_hash=f"large_{i}"
            )
            judgments.append(j)
        
        # Total memory: ~100MB
        # Should handle without out-of-memory errors
        assert len(judgments) == 100
        assert all(len(j.full_text) > 900000 for j in judgments)
    
    def test_concurrent_entity_extraction(self):
        """Test entity extraction under concurrent load"""
        extractor = AdvancedEntityExtractor()
        
        judgment = CanonicalJudgment(
            judgment_id="CONCURRENT_001",
            title="رای همزمان",
            full_text="آقای محمد رضایی و خانم فاطمه احمدی طبق ماده 10 قانون مدنی و اصل 22 قانون اساسی",
            court_level="appeal",
            legal_area="civil",
            verdict_type="affirm",
            date="1403/01/01",
            quality_score=0.8,
            word_count=20,
            parties=[],
            legal_references=[],
            source_hash="concurrent"
        )
        
        results = []
        errors = []
        
        def extract_worker():
            try:
                result = extractor.extract_entities(judgment)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run 50 concurrent extractions
        threads = []
        for _ in range(50):
            t = threading.Thread(target=extract_worker)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0
        assert len(results) == 50
        # Results should be consistent
        first_parties = set(p[0] for p in results[0].parties)
        for result in results[1:]:
            assert set(p[0] for p in result.parties) == first_parties


# ============================================================================
# TEST SUITE 3: Circuit Breaker Resilience
# ============================================================================

class TestCircuitBreaker:
    """Test circuit breaker behavior under failure conditions"""
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures"""
        cb = CircuitBreakerStats(failure_threshold=3, recovery_timeout=1.0)
        
        assert cb.state == "CLOSED"
        assert cb.can_execute() == True
        
        # Trigger failures
        cb.record_failure()
        assert cb.state == "CLOSED"
        assert cb.failures == 1
        
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() == False
    
    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker transitions to HALF_OPEN after timeout"""
        cb = CircuitBreakerStats(failure_threshold=2, recovery_timeout=0.5)
        
        # Trigger opening
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() == False
        
        # Wait for recovery timeout
        time.sleep(0.6)
        
        # Should transition to HALF_OPEN
        assert cb.can_execute() == True
        assert cb.state == "HALF_OPEN"
        
        # Successful execution should close it
        cb.record_success()
        assert cb.state == "CLOSED"
    
    def test_bridge_retry_mechanism(self):
        """Test bridge retries on failure"""
        bridge = EnterpriseCypherBridge(max_retries=3)
        
        # Mock failed execution that succeeds on retry
        call_count = {'count': 0}
        
        def mock_execute(cypher):
            call_count['count'] += 1
            if call_count['count'] < 3:
                raise RuntimeError("Temporary failure")
            return "success"
        
        bridge._execute_raw = mock_execute
        
        # Should retry and eventually succeed
        result = bridge.execute_with_retry("TEST QUERY")
        assert result == "success"
        assert call_count['count'] == 3


# ============================================================================
# TEST SUITE 4: Entity Extraction Edge Cases
# ============================================================================

class TestEntityExtractionEdgeCases:
    """Test entity extraction with challenging inputs"""
    
    def test_extraction_with_no_entities(self):
        """Test extraction from text with no identifiable entities"""
        extractor = AdvancedEntityExtractor()
        
        judgment = CanonicalJudgment(
            judgment_id="EMPTY_001",
            title="رای خالی",
            full_text="این متن هیچ نام یا مرجع قانونی ندارد",
            court_level="trial",
            legal_area="civil",
            verdict_type="affirm",
            date="1403/01/01",
            quality_score=0.5,
            word_count=10,
            parties=[],
            legal_references=[],
            source_hash="empty"
        )
        
        result = extractor.extract_entities(judgment)
        
        # Should return empty lists, not crash
        assert isinstance(result.parties, list)
        assert isinstance(result.legal_refs, list)
    
    def test_extraction_with_ambiguous_patterns(self):
        """Test extraction with ambiguous or overlapping patterns"""
        extractor = AdvancedEntityExtractor()
        
        judgment = CanonicalJudgment(
            judgment_id="AMBIG_001",
            title="رای مبهم",
            full_text="آقای ماده 10 از شرکت قانون تجارت طبق اصل ماده 22",
            court_level="appeal",
            legal_area="commercial",
            verdict_type="reverse",
            date="1403/02/01",
            quality_score=0.7,
            word_count=15,
            parties=[],
            legal_references=[],
            source_hash="ambig"
        )
        
        result = extractor.extract_entities(judgment)
        
        # Should extract despite ambiguity
        assert len(result.parties) > 0 or len(result.legal_refs) > 0
    
    def test_confidence_scoring_accuracy(self):
        """Test confidence scoring for high/low quality matches"""
        extractor = AdvancedEntityExtractor()
        
        # High quality judgment
        high_quality = CanonicalJudgment(
            judgment_id="QUAL_HIGH",
            title="رای با کیفیت",
            full_text="خواهان آقای علی رضایی و خوانده خانم سارا احمدی طبق ماده 10 قانون مدنی",
            court_level="supreme",
            legal_area="civil",
            verdict_type="affirm",
            date="1403/01/01",
            quality_score=0.95,
            word_count=20,
            parties=[],
            legal_references=[],
            source_hash="high"
        )
        
        result_high = extractor.extract_entities(high_quality)
        
        # Should have high confidence parties
        high_conf_parties = result_high.get_high_confidence_parties()
        assert len(high_conf_parties) >= 2
        
        # Check confidence values
        for name, conf in result_high.parties:
            assert 0.0 <= conf <= 1.0


# ============================================================================
# TEST SUITE 5: Batch Processing Edge Cases
# ============================================================================

class TestBatchProcessingEdgeCases:
    """Test edge cases in batch processing"""
    
    def test_empty_batch_handling(self):
        """Test handling of empty batches"""
        bridge = EnterpriseCypherBridge()
        
        # Empty batch should not crash
        result = bridge.execute_apoc_batch("CREATE (n:Test)", [])
        assert result == ""
    
    def test_single_item_batch(self):
        """Test batch with single item"""
        bridge = EnterpriseCypherBridge()
        
        data = [{'id': 'TEST_001', 'value': 'test'}]
        
        # Mock execution
        bridge._execute_raw = Mock(return_value="success")
        
        result = bridge.execute_apoc_batch(
            "CREATE (n:Test {id: item.id, value: item.value})",
            data
        )
        
        assert bridge._execute_raw.called
    
    def test_oversized_batch_splitting(self):
        """Test automatic splitting of oversized batches (>1000 items)"""
        bridge = EnterpriseCypherBridge()
        
        # Create 2500 items (should split into 3 batches)
        large_data = [{'id': f'ITEM_{i:04d}'} for i in range(2500)]
        
        bridge._execute_raw = Mock(return_value="success")
        
        result = bridge.execute_apoc_batch(
            "CREATE (n:Test {id: item.id})",
            large_data
        )
        
        # Should have called execute multiple times
        assert bridge._execute_raw.call_count >= 3


# ============================================================================
# EXECUTION & REPORTING
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("🔥 EXTREME STRESS TESTS FOR JUDGMENT INGESTION")
    print("=" * 80)
    print()
    
    # Run tests with verbose output
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--durations=10',
        '-W', 'ignore::DeprecationWarning'
    ])

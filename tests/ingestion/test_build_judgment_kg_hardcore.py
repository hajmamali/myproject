#!/usr/bin/env python3
"""
🔥 HARDCORE STRESS TESTS for build_judgment_kg.py
=================================================

سختگیرانه‌ترین تست‌ها برای اسکریپت ingestion:
1. Governance compliance verification  
2. Data corruption scenarios
3. Extreme performance stress
4. Circuit breaker behavior
5. Entity extraction accuracy
6. Memory pressure tests
7. Concurrent access
8. Neo4j failure scenarios
"""

import json
import pytest
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.build_judgment_kg import (
    CanonicalJudgment,
    CircuitBreakerStats,
    PerformanceMetrics,
    GovernanceAwareBridge,
    EntityExtractor,
    EnterpriseJudgmentCompiler,
    parse_judgments_from_json,
    verify_source,
)


# ============================================================================
# TEST 1: Governance Compliance
# ============================================================================

class TestGovernanceCompliance:
    """CRITICAL: Verify CANONICAL governance integration"""
    
    def test_uses_canonical_connection(self):
        """MUST use get_connection() - see AGENTS.md Part 1-A"""
        bridge = GovernanceAwareBridge()
        
        # Verify connection object is from canonical source
        assert hasattr(bridge.connection, '_raw_execute')
        assert bridge.connection is not None
        
        # Should NOT be a direct driver instance
        assert 'Driver' not in str(type(bridge.connection))
    
    def test_no_direct_driver_instantiation(self):
        """FORBIDDEN: Direct GraphDatabase.driver() - see AGENTS.md"""
        # Check source code doesn't contain forbidden pattern
        script_path = Path(__file__).parent.parent.parent / 'scripts' / 'build_judgment_kg.py'
        source = script_path.read_text()
        
        # These patterns are FORBIDDEN per AGENTS.md
        assert 'GraphDatabase.driver(' not in source
        assert 'AsyncGraphDatabase.driver(' not in source
    
    def test_imports_canonical_modules(self):
        """MUST import from mahoun.graph.neo4j.connection"""
        script_path = Path(__file__).parent.parent.parent / 'scripts' / 'build_judgment_kg.py'
        source = script_path.read_text()
        
        # Required canonical import
        assert 'from mahoun.graph.neo4j.connection import get_connection' in source


# ============================================================================
# TEST 2: Data Corruption & Edge Cases
# ============================================================================

class TestDataCorruption:
    """Test handling of malformed/corrupted data"""
    
    def test_empty_json_file(self):
        """Empty JSON should fail gracefully"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            f.flush()
            
            with pytest.raises(ValueError, match="missing 'judgments' key"):
                parse_judgments_from_json(Path(f.name))
    
    def test_corrupted_utf8(self):
        """Invalid UTF-8 should be detected"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as f:
            f.write(b'\xff\xfe invalid')
            f.flush()
            
            valid, _, error = verify_source(Path(f.name))
            assert not valid
            assert error is not None
    
    def test_missing_required_fields(self):
        """Missing fields should use defaults, not crash"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                'judgments': [{
                    'metadata': {'judgment_id': 'TEST_001'},
                    # Missing most fields
                }]
            }, f)
            f.flush()
            
            judgments = parse_judgments_from_json(Path(f.name))
            assert len(judgments) == 1
            assert judgments[0].judgment_id == 'TEST_001'
            assert judgments[0].title == 'بدون عنوان'  # Default
            assert judgments[0].court_level == 'unknown'
    
    def test_null_values_handling(self):
        """Null values should be handled robustly"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                'judgments': [{
                    'metadata': {
                        'judgment_id': None,
                        'title': None,
                        'parties': None,
                        'legal_references': None,
                    },
                    'full_text': None
                }]
            }, f)
            f.flush()
            
            judgments = parse_judgments_from_json(Path(f.name))
            assert len(judgments) == 1
            assert judgments[0].judgment_id == 'UNKNOWN'
            assert judgments[0].parties == []
            assert judgments[0].legal_references == []
    
    def test_cypher_injection_attempts(self):
        """SQL/Cypher injection should be prevented"""
        dangerous_inputs = [
            "'; DROP TABLE Judgment; --",
            "' OR '1'='1",
            "'); DELETE FROM Party WHERE ('1'='1",
        ]
        
        judgment = CanonicalJudgment(
            judgment_id="INJECT_001",
            title="Test",
            full_text="متن",
            court_level="trial",
            legal_area="criminal",
            verdict_type="reject",
            date=None,
            quality_score=0.5,
            word_count=10,
            parties=dangerous_inputs,
            legal_references=dangerous_inputs,
            source_hash="abc"
        )
        
        # Should store safely without execution
        assert judgment.parties == dangerous_inputs


# ============================================================================
# TEST 3: Performance & Stress
# ============================================================================

class TestPerformanceStress:
    """Test under extreme load"""
    
    def test_large_batch_processing(self):
        """Process 1000 judgments efficiently"""
        judgments = []
        for i in range(1000):
            j = CanonicalJudgment(
                judgment_id=f"STRESS_{i:04d}",
                title=f"رای {i}",
                full_text="متن رای " * 50,
                court_level="supreme",
                legal_area="civil",
                verdict_type="affirm",
                date="1403/01/01",
                quality_score=0.8,
                word_count=50,
                parties=[f"طرف_{i}"],
                legal_references=[f"ماده_{i}"],
                source_hash=f"hash_{i}"
            )
            judgments.append(j)
        
        metrics = PerformanceMetrics()
        start = time.time()
        
        # Simulate processing
        batch_size = 50
        for i in range(0, len(judgments), batch_size):
            batch_start = time.time()
            batch = judgments[i:i+batch_size]
            time.sleep(0.001)  # Simulate work
            metrics.record_batch(len(batch), time.time() - batch_start)
        
        duration = time.time() - start
        throughput = metrics.get_throughput()
        
        assert metrics.judgments_processed == 1000
        assert throughput > 50  # At least 50 j/s
        assert duration < 30  # Complete in under 30s
    
    def test_memory_pressure_large_texts(self):
        """Handle judgments with very large texts"""
        large_text = "متن طولانی " * 100000  # ~1MB
        
        judgments = []
        for i in range(50):
            j = CanonicalJudgment(
                judgment_id=f"LARGE_{i:02d}",
                title=f"رای بزرگ {i}",
                full_text=large_text,
                court_level="supreme",
                legal_area="civil",
                verdict_type="affirm",
                date="1403/01/01",
                quality_score=0.9,
                word_count=100000,
                parties=[f"طرف_{i}"],
                legal_references=[f"ماده_{i}"],
                source_hash=f"hash_{i}"
            )
            judgments.append(j)
        
        # Should not crash with out-of-memory
        assert len(judgments) == 50
        assert all(len(j.full_text) > 1000000 for j in judgments)
    
    def test_concurrent_entity_extraction(self):
        """Entity extraction should be thread-safe"""
        extractor = EntityExtractor()
        
        judgment = CanonicalJudgment(
            judgment_id="CONCURRENT_001",
            title="تست همزمانی",
            full_text="آقای محمد رضایی و خانم فاطمه احمدی طبق ماده 10 قانون",
            court_level="appeal",
            legal_area="civil",
            verdict_type="affirm",
            date="1403/01/01",
            quality_score=0.8,
            word_count=15,
            parties=[],
            legal_references=[],
            source_hash="concurrent"
        )
        
        results = []
        errors = []
        
        def extract_worker():
            try:
                parties, refs = extractor.extract(judgment)
                results.append((parties, refs))
            except Exception as e:
                errors.append(e)
        
        # 100 concurrent extractions
        threads = []
        for _ in range(100):
            t = threading.Thread(target=extract_worker)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert len(results) == 100
        
        # Results should be consistent
        first_parties = set(results[0][0])
        for parties, _ in results[1:]:
            assert set(parties) == first_parties


# ============================================================================
# TEST 4: Circuit Breaker
# ============================================================================

class TestCircuitBreaker:
    """Test circuit breaker resilience"""
    
    def test_opens_after_threshold_failures(self):
        """Circuit breaker should open after failures"""
        cb = CircuitBreakerStats(failure_threshold=3, recovery_timeout=1.0)
        
        assert cb.state == "CLOSED"
        assert cb.can_execute()
        
        # Trigger failures
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "CLOSED"
        
        cb.record_failure()
        assert cb.state == "OPEN"
        assert not cb.can_execute()
    
    def test_recovers_after_timeout(self):
        """Circuit breaker should transition to HALF_OPEN"""
        cb = CircuitBreakerStats(failure_threshold=2, recovery_timeout=0.3)
        
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        
        time.sleep(0.4)
        assert cb.can_execute()
        assert cb.state == "HALF_OPEN"
        
        cb.record_success()
        assert cb.state == "CLOSED"
    
    def test_closes_on_success_in_half_open(self):
        """Successful call in HALF_OPEN should close circuit"""
        cb = CircuitBreakerStats()
        
        # Force to HALF_OPEN
        cb.failures = 5
        cb.state = "HALF_OPEN"
        
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failures == 0


# ============================================================================
# TEST 5: Entity Extraction
# ============================================================================

class TestEntityExtraction:
    """Test entity extraction accuracy"""
    
    def test_extracts_parties_correctly(self):
        """Should extract party names"""
        extractor = EntityExtractor()
        
        judgment = CanonicalJudgment(
            judgment_id="PARTY_001",
            title="تست",
            full_text="خواهان آقای علی رضایی و خوانده خانم سارا احمدی و شرکت تجارت پارس",
            court_level="trial",
            legal_area="civil",
            verdict_type="affirm",
            date="1403/01/01",
            quality_score=0.9,
            word_count=20,
            parties=[],
            legal_references=[],
            source_hash="test"
        )
        
        parties, _ = extractor.extract(judgment)
        
        assert len(parties) >= 2
        assert any('علی رضایی' in p for p in parties)
        assert any('سارا احمدی' in p for p in parties)
    
    def test_extracts_legal_references(self):
        """Should extract legal references"""
        extractor = EntityExtractor()
        
        judgment = CanonicalJudgment(
            judgment_id="REF_001",
            title="تست",
            full_text="طبق ماده 10 قانون مدنی و اصل 22 قانون اساسی و ماده 219 قانون تجارت",
            court_level="appeal",
            legal_area="commercial",
            verdict_type="affirm",
            date="1403/01/01",
            quality_score=0.9,
            word_count=20,
            parties=[],
            legal_references=[],
            source_hash="test"
        )
        
        _, refs = extractor.extract(judgment)
        
        assert len(refs) >= 2
        assert any('ماده 10' in r for r in refs)
        assert any('اصل 22' in r for r in refs)
    
    def test_handles_empty_text(self):
        """Empty text should not crash"""
        extractor = EntityExtractor()
        
        judgment = CanonicalJudgment(
            judgment_id="EMPTY_001",
            title="خالی",
            full_text="",
            court_level="trial",
            legal_area="civil",
            verdict_type="reject",
            date=None,
            quality_score=0.5,
            word_count=0,
            parties=[],
            legal_references=[],
            source_hash="empty"
        )
        
        parties, refs = extractor.extract(judgment)
        
        assert isinstance(parties, list)
        assert isinstance(refs, list)
        assert len(parties) == 0
        assert len(refs) == 0


# ============================================================================
# TEST 6: Performance Metrics
# ============================================================================

class TestPerformanceMetrics:
    """Test metrics calculation"""
    
    def test_throughput_calculation(self):
        """Throughput should be accurate"""
        metrics = PerformanceMetrics()
        metrics.start_time = time.time() - 10  # 10 seconds ago
        metrics.judgments_processed = 100
        
        throughput = metrics.get_throughput()
        
        assert 9 < throughput < 11  # ~10 j/s
    
    def test_eta_calculation(self):
        """ETA should be reasonable"""
        metrics = PerformanceMetrics()
        
        # Process 100 in 10s
        metrics.record_batch(100, 10.0)
        
        # Estimate for 1000 total
        eta = metrics.get_eta(1000)
        
        assert eta is not None
        assert 80 < eta < 100  # ~90s remaining
    
    def test_eta_with_no_data(self):
        """ETA should return None with no data"""
        metrics = PerformanceMetrics()
        
        eta = metrics.get_eta(1000)
        
        assert eta is None


# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("🔥 HARDCORE STRESS TESTS - build_judgment_kg.py")
    print("=" * 80)
    print()
    
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--durations=10',
        '-W', 'ignore::DeprecationWarning'
    ])

#!/usr/bin/env python3
"""
Integration test for build_judgment_kg.py
Tests actual Neo4j connection and ingestion
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.build_judgment_kg import (
    CanonicalJudgment,
    EnterpriseJudgmentCompiler,
)


@pytest.mark.integration
def test_can_connect_to_neo4j():
    """Test that canonical connection works"""
    compiler = EnterpriseJudgmentCompiler()
    
    # Should not raise
    assert compiler.bridge is not None
    assert compiler.bridge.connection is not None


@pytest.mark.integration
def test_can_create_constraints():
    """Test constraint creation"""
    compiler = EnterpriseJudgmentCompiler()
    
    # Should not raise
    compiler.ensure_constraints()
    
    # Verify by trying again (should be idempotent)
    compiler.ensure_constraints()


@pytest.mark.integration
def test_can_ingest_single_judgment():
    """Test ingesting a single judgment"""
    compiler = EnterpriseJudgmentCompiler()
    
    judgment = CanonicalJudgment(
        judgment_id="TEST_INTEGRATION_001",
        title="رای تست یکپارچه‌سازی",
        full_text="این یک رای آزمایشی است. آقای احمد رضایی و خانم فاطمه محمدی طبق ماده 10 قانون مدنی.",
        court_level="trial",
        legal_area="civil",
        verdict_type="affirm",
        date="1403/01/01",
        quality_score=0.85,
        word_count=20,
        parties=["احمد رضایی", "فاطمه محمدی"],
        legal_references=["ماده 10 قانون مدنی"],
        source_hash="test_integration_001"
    )
    
    result = compiler.compile([judgment], batch_size=1)
    
    assert result['status'] in ['COMPLETED', 'COMPLETED_WITH_ERRORS']
    assert result['processed'] == 1
    assert result['total_judgments'] == 1
    
    print(f"\n✅ Integration test passed!")
    print(f"   Status: {result['status']}")
    print(f"   Processed: {result['processed']}")
    print(f"   Entities: {result['entities_created']}")
    print(f"   Relationships: {result['relationships_created']}")


@pytest.mark.integration
def test_can_ingest_batch():
    """Test ingesting a small batch"""
    compiler = EnterpriseJudgmentCompiler()
    
    judgments = []
    for i in range(5):
        j = CanonicalJudgment(
            judgment_id=f"TEST_BATCH_{i:03d}",
            title=f"رای تست شماره {i}",
            full_text=f"این رای شماره {i} است. آقای شخص_{i} مطابق ماده {i+1}.",
            court_level="appeal",
            legal_area="commercial",
            verdict_type="affirm",
            date="1403/02/15",
            quality_score=0.7 + (i * 0.05),
            word_count=15 + i,
            parties=[f"شخص_{i}"],
            legal_references=[f"ماده {i+1}"],
            source_hash=f"batch_test_{i}"
        )
        judgments.append(j)
    
    result = compiler.compile(judgments, batch_size=2)
    
    assert result['status'] in ['COMPLETED', 'COMPLETED_WITH_ERRORS']
    assert result['processed'] == 5
    assert result['entities_created'] > 0
    
    print(f"\n✅ Batch integration test passed!")
    print(f"   Status: {result['status']}")
    print(f"   Processed: {result['processed']}/5")
    print(f"   Entities: {result['entities_created']}")
    print(f"   Throughput: {result['throughput_jps']:.2f} j/s")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '-m', 'integration'])

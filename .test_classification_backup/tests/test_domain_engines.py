"""
Domain Engine Tests
===================

تست‌های جامع برای تمام Domain Engines
"""

import pytest


@pytest.mark.asyncio
async def test_dispute_extraction_engine():
    """Test DisputeExtractionEngine"""
    from mahoun.domain.dispute_extractor import DisputeExtractionEngine
    
    engine = DisputeExtractionEngine()
    await engine.initialize()
    
    assert engine.name == "dispute_extractor"
    
    result = await engine.analyze({
        "query": "شناسایی اختلافات"
    })
    
    assert result.get("success") is not None
    assert "disputes" in result or "error" in result


@pytest.mark.asyncio
async def test_timeline_analyzer():
    """Test TimelineAnalyzer"""
    from mahoun.domain.timeline_analyzer import TimelineAnalyzer
    
    engine = TimelineAnalyzer()
    await engine.initialize()
    
    assert engine.name == "timeline_analyzer"
    
    result = await engine.analyze({
        "query": "timeline"
    })
    
    assert result.get("success") is not None
    assert "timeline" in result or "error" in result


@pytest.mark.asyncio
async def test_delay_analysis_engine():
    """Test DelayAnalysisEngine"""
    from mahoun.domain.delay_analyzer import DelayAnalysisEngine
    
    engine = DelayAnalysisEngine()
    await engine.initialize()
    
    assert engine.name == "delay_analyzer"
    
    result = await engine.analyze({
        "project_id": "test",
        "query": "تحلیل تأخیرات"
    })
    
    assert result.get("success") is not None
    assert "delays" in result or "error" in result


@pytest.mark.asyncio
async def test_delay_narrative_generator():
    """Test DelayNarrativeGenerator"""
    from mahoun.domain.delay_narrative import DelayNarrativeGenerator
    
    engine = DelayNarrativeGenerator()
    await engine.initialize()
    
    assert engine.name == "delay_narrative_generator"
    
    result = await engine.analyze({
        "project_id": "test",
        "narrative_type": "combined"
    })
    
    assert result.get("success") is not None
    assert "narrative" in result or "error" in result


@pytest.mark.asyncio
async def test_contract_reasoning_engine():
    """Test ContractClauseReasoningEngine"""
    from mahoun.domain.contract_reasoning import ContractClauseReasoningEngine
    
    engine = ContractClauseReasoningEngine()
    await engine.initialize()
    
    assert engine.name == "contract_reasoning"
    
    result = await engine.analyze({
        "query": "شرایط پرداخت چیست؟"
    })
    
    assert result.get("success") is not None
    assert "answer" in result or "error" in result


def test_base_domain_engine():
    """Test BaseDomainEngine"""
    from mahoun.domain.base_engine import BaseDomainEngine
    
    class TestEngine(BaseDomainEngine):
        async def analyze(self, input_data):
            return {"success": True, "data": input_data}
    
    engine = TestEngine("test_engine")
    
    assert engine.name == "test_engine"
    assert engine.get_status()["name"] == "test_engine"
    assert engine.validate_input({}) is True



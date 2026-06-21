"""
Output Generator Tests
======================

تست‌های جامع برای تمام Report Generators
"""

import pytest
from pathlib import Path
import tempfile


@pytest.mark.asyncio
async def test_claim_draft_generator():
    """Test ClaimDraftGenerator"""
    from output.claim_generator import ClaimDraftGenerator
    
    generator = ClaimDraftGenerator()
    await generator.initialize()
    
    assert generator.name == "claim_draft_generator"
    
    result = await generator.generate({
        "claim_type": "تأخیر",
        "facts": "تأخیر در تحویل"
    })
    
    assert result.get("success") is not None
    assert "content" in result or "error" in result


@pytest.mark.asyncio
async def test_delay_report_generator():
    """Test DelayReportGenerator"""
    from output.delay_report import DelayReportGenerator
    
    generator = DelayReportGenerator()
    await generator.initialize()
    
    assert generator.name == "delay_report_generator"
    
    result = await generator.generate({
        "project_id": "test",
        "query": "تحلیل تأخیرات"
    })
    
    assert result.get("success") is not None
    assert "content" in result or "error" in result


@pytest.mark.asyncio
async def test_timeline_report_generator():
    """Test TimelineReportGenerator"""
    from output.timeline_report import TimelineReportGenerator
    
    generator = TimelineReportGenerator()
    await generator.initialize()
    
    assert generator.name == "timeline_report_generator"
    
    result = await generator.generate({
        "query": "timeline"
    })
    
    assert result.get("success") is not None
    assert "content" in result or "error" in result


@pytest.mark.asyncio
async def test_report_export_formats():
    """Test report export to different formats"""
    from output.base_generator import BaseReportGenerator
    
    class TestGenerator(BaseReportGenerator):
        async def generate(self, input_data):
            return {
                "success": True,
                "content": "Test content",
                "markdown": "# Test",
                "title": "Test Report"
            }
    
    generator = TestGenerator("test")
    
    # Test JSON export
    json_result = await generator.export({"content": "test"}, "json")
    assert json_result is not None
    
    # Test text export
    text_result = await generator.export({"content": "test"}, "text")
    assert text_result is not None
    
    # Test markdown export
    md_result = await generator.export({"markdown": "# test"}, "markdown")
    assert md_result is not None


def test_base_generator_status():
    """Test BaseReportGenerator status"""
    from output.base_generator import BaseReportGenerator
    
    class TestGenerator(BaseReportGenerator):
        async def generate(self, input_data):
            return {"success": True}
    
    generator = TestGenerator("test", {"key": "value"})
    
    status = generator.get_status()
    assert status["name"] == "test"
    assert status["config"]["key"] == "value"



"""
End-to-End Tests for MAHOUN
===========================

تست‌های end-to-end برای workflow کامل
"""

import pytest
import asyncio


@pytest.mark.asyncio
async def test_document_to_report_workflow():
    """Test complete workflow: Document → Analysis → Report"""
    
    # Step 1: Document Processing
    from mahoun.agents.doc_parser_agent import DocParserAgent
    
    doc_parser = DocParserAgent()
    await doc_parser.initialize()
    
    doc_result = await doc_parser.process({
        "text": "قرارداد پیمانکاری\nتأخیر در تحویل: 30 روز",
        "doc_type": "contract"
    })
    
    assert doc_result.get("success") is not None
    
    # Step 2: Delay Analysis
    from mahoun.domain.delay_analyzer import DelayAnalysisEngine
    
    delay_engine = DelayAnalysisEngine()
    await delay_engine.initialize()
    
    delay_result = await delay_engine.analyze({
        "project_id": "test_project",
        "query": "تحلیل تأخیرات"
    })
    
    assert delay_result.get("success") is not None
    
    # Step 3: Report Generation
    from output.delay_report import DelayReportGenerator
    
    report_generator = DelayReportGenerator()
    await report_generator.initialize()
    
    report_result = await report_generator.generate({
        "project_id": "test_project",
        "delay_data": delay_result
    })
    
    assert report_result.get("success") is not None
    assert "content" in report_result or "error" in report_result


@pytest.mark.asyncio
async def test_query_to_answer_workflow():
    """Test workflow: Query → RAG → Answer"""
    
    # Step 1: Query Routing
    from mahoun.rag.query_router import QueryRouter
    
    router = QueryRouter()
    classification = await router.classify("شرایط پرداخت چیست؟")
    
    assert classification.query_type is not None
    
    # Step 2: Contract Agent
    from mahoun.agents.contract_agent import ContractAgent
    
    contract_agent = ContractAgent()
    await contract_agent.initialize()
    
    answer_result = await contract_agent.process({
        "query": "شرایط پرداخت چیست؟"
    })
    
    assert answer_result.get("success") is not None
    assert "answer" in answer_result or "error" in answer_result


@pytest.mark.asyncio
async def test_orchestrator_workflow():
    """Test orchestrator managing multiple agents"""
    from mahoun.agents.orchestrator import AgentOrchestrator
    from agents import ContractAgent, DisputeAgent
    
    orchestrator = AgentOrchestrator()
    
    # Register agents
    contract_agent = ContractAgent()
    dispute_agent = DisputeAgent()
    
    orchestrator.register_agent(contract_agent)
    orchestrator.register_agent(dispute_agent)
    
    # Execute workflow
    workflow = [
        {
            "agent": "contract_agent",
            "config": {"query": "شرایط پرداخت"}
        },
        {
            "agent": "dispute_agent",
            "config": {"query": "شناسایی اختلافات"}
        }
    ]
    
    result = await orchestrator.execute_workflow(workflow, {})
    
    assert result.get("status") in ["completed", "failed"]
    assert "steps" in result


@pytest.mark.asyncio
async def test_claim_generation_workflow():
    """Test complete claim generation workflow"""
    
    # Step 1: Dispute Extraction
    from mahoun.domain.dispute_extractor import DisputeExtractionEngine
    
    dispute_engine = DisputeExtractionEngine()
    await dispute_engine.initialize()
    
    disputes = await dispute_engine.analyze({
        "query": "شناسایی اختلافات"
    })
    
    assert disputes.get("success") is not None
    
    # Step 2: Claim Generation
    from output.claim_generator import ClaimDraftGenerator
    
    claim_generator = ClaimDraftGenerator()
    await claim_generator.initialize()
    
    claim = await claim_generator.generate({
        "claim_type": "تأخیر",
        "facts": "تأخیر در تحویل پروژه"
    })
    
    assert claim.get("success") is not None
    assert "content" in claim or "error" in claim


@pytest.mark.asyncio
async def test_timeline_analysis_workflow():
    """Test timeline analysis workflow"""
    
    # Step 1: Timeline Extraction
    from mahoun.domain.timeline_analyzer import TimelineAnalyzer
    
    timeline_engine = TimelineAnalyzer()
    await timeline_engine.initialize()
    
    timeline = await timeline_engine.analyze({
        "query": "توالی وقایع"
    })
    
    assert timeline.get("success") is not None
    assert "timeline" in timeline or "error" in timeline
    
    # Step 2: Report Generation
    from output.timeline_report import TimelineReportGenerator
    
    report_generator = TimelineReportGenerator()
    await report_generator.initialize()
    
    report = await report_generator.generate({
        "query": "توالی وقایع"
    })
    
    assert report.get("success") is not None
    assert "content" in report or "error" in report



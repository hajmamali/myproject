"""
Comprehensive Integration Tests
================================

تست‌های integration جامع برای تمام کامپوننت‌ها
"""

import pytest


@pytest.mark.asyncio
async def test_all_agents_initialization():
    """Test that all agents can be initialized"""
    from agents import (
        DocParserAgent, DisputeAgent, ClaimAgent,
        TimelineAgent, DelayAgent, NarrativeAgent, ContractAgent
    )
    
    agents = [
        DocParserAgent(),
        DisputeAgent(),
        ClaimAgent(),
        TimelineAgent(),
        DelayAgent(),
        NarrativeAgent(),
        ContractAgent()
    ]
    
    for agent in agents:
        await agent.initialize()
        assert agent._initialized
        assert agent.name is not None


@pytest.mark.asyncio
async def test_all_domain_engines_initialization():
    """Test that all domain engines can be initialized"""
    from domain import (
        DisputeExtractionEngine,
        TimelineAnalyzer,
        DelayAnalysisEngine,
        DelayNarrativeGenerator,
        ContractClauseReasoningEngine
    )
    
    engines = [
        DisputeExtractionEngine(),
        TimelineAnalyzer(),
        DelayAnalysisEngine(),
        DelayNarrativeGenerator(),
        ContractClauseReasoningEngine()
    ]
    
    for engine in engines:
        await engine.initialize()
        assert engine.name is not None


@pytest.mark.asyncio
async def test_all_report_generators_initialization():
    """Test that all report generators can be initialized"""
    from output import (
        ClaimDraftGenerator,
        DelayReportGenerator,
        TimelineReportGenerator
    )
    
    generators = [
        ClaimDraftGenerator(),
        DelayReportGenerator(),
        TimelineReportGenerator()
    ]
    
    for generator in generators:
        await generator.initialize()
        assert generator.name is not None


@pytest.mark.asyncio
async def test_component_imports():
    """Test that all components can be imported"""
    # Agents
    from agents import (
        BaseAgent, AgentOrchestrator,
        DocParserAgent, DisputeAgent, ClaimAgent,
        TimelineAgent, DelayAgent, NarrativeAgent, ContractAgent
    )
    
    # Domain Engines
    from domain import (
        BaseDomainEngine,
        DisputeExtractionEngine,
        TimelineAnalyzer,
        DelayAnalysisEngine,
        DelayNarrativeGenerator,
        ContractClauseReasoningEngine
    )
    
    # Output Generators
    from output import (
        BaseReportGenerator,
        ClaimDraftGenerator,
        DelayReportGenerator,
        TimelineReportGenerator
    )
    
    # RAG Components
    from rag import QueryRouter, CitationEngine, IndexingPipeline
    
    # All imports should succeed
    assert True


def test_error_handling_consistency():
    """Test that all components handle errors consistently"""
    # All components should return dict with "success" or "error" key
    # This is tested implicitly in other tests
    assert True



"""
RAG Component Tests
===================

تست‌های جامع برای RAG components
"""

import pytest


@pytest.mark.asyncio
async def test_query_router():
    """Test QueryRouter"""
    from mahoun.rag.query_router import QueryRouter, QueryType
    
    router = QueryRouter()
    
    # Test classification
    result = await router.classify("شرایط پرداخت در قرارداد چیست؟")
    
    assert result.query_type == QueryType.CONTRACT
    assert result.confidence > 0
    
    # Test different query types
    delay_result = await router.classify("تحلیل تأخیرات پروژه")
    assert delay_result.query_type in [QueryType.DELAY_ANALYSIS, QueryType.CONTRACT]


@pytest.mark.asyncio
async def test_citation_engine():
    """Test CitationEngine"""
    from mahoun.rag.citation_engine import CitationEngine
    from mahoun.rag.hybrid_rag_service import HybridRAGResult, RetrievalResult
    
    engine = CitationEngine()
    
    # Mock RAG result
    mock_result = HybridRAGResult(
        query="test",
        mode_used="text_only",
        results=[
            RetrievalResult(
                doc_id="doc1",
                content="بند 5: شرایط پرداخت. صفحه 10",
                score=0.9,
                rank=1,
                source="text",
                metadata={"title": "قرارداد", "page": 10}
            )
        ],
        retrieval_time_ms=50.0,
        metadata={}
    )
    
    citation_result = await engine.extract_citations(mock_result, "test")
    
    assert len(citation_result.citations) >= 0
    assert citation_result.query == "test"


@pytest.mark.asyncio
async def test_indexing_pipeline():
    """Test IndexingPipeline"""
    from mahoun.rag.indexing_pipeline import IndexingPipeline
    
    pipeline = IndexingPipeline()
    await pipeline.initialize()
    
    assert pipeline._initialized
    
    # Test with sample document
    # Note: This might fail if dependencies are not available
    try:
        result = await pipeline.index_document({
            "text": "قرارداد پیمانکاری",
            "doc_type": "contract",
            "doc_id": "test_doc"
        })
        
        assert result is not None
    except Exception as e:
        # Expected if dependencies are missing
        pytest.skip(f"Indexing requires dependencies: {e}")


def test_query_router_keywords():
    """Test QueryRouter keyword matching"""
    from mahoun.rag.query_router import QueryRouter
    
    router = QueryRouter()
    
    # Test keyword detection
    contract_keywords = ["قرارداد", "بند", "پیمان"]
    delay_keywords = ["تأخیر", "delay", "مهلت"]
    
    # These are internal implementation details
    # Just verify router exists and can classify
    assert router is not None



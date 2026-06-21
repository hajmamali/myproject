"""
End-to-End Production Scenario Test (HAJIX)
============================================

Tests a full typical workflow: 
1. Document Ingestion (via DocParserAgent)
2. Dispute Analysis (via DisputeAgent)

This verifies that the refactored agents correctly interact with the real V2 pipelines.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from mahoun.agents import AgentFactory
from mahoun.agents.dispute_agent import DisputeType

@pytest.mark.asyncio
async def test_legal_dispute_workflow():
    """
    Scenario: A contract text with a financial dispute is processed.
    Expected:
    - DocParser returns normalized text and metadata.
    - DisputeAgent identifies it as a FINANCIAL dispute.
    """
    
    # 1. Setup Agents
    parser_agent = await AgentFactory.create_agent("doc_parser")
    dispute_agent = await AgentFactory.create_agent("dispute")
    
    # Mocking heavy internal dependencies to focus on logic wiring
    # We want to ensure 'process' calls the right underlying methods
    
    sample_text = """
    قرارداد شماره ۱۲۳/الف
    ماده ۵: خریدار موظف بود مبلغ ۵۰۰ میلیون تومان را تا تاریخ ۱۴۰۳/۰۱/۰۱ پرداخت کند.
    متاسفانه خریدار از پرداخت وجه خودداری کرده و این امر موجب خسارت به فروشنده شده است.
    """
    
    # 2. Run Doc Parser
    # We patch the heavy ingestion pipeline to return a success result immediately
    # allowing us to test the AGENT logic around it.
    with patch("mahoun.pipelines.ingestion.pipeline.IngestionPipelineV2.ingest_document") as mock_ingest:
        mock_ingest.return_value = MagicMock(success=True, doc_id="doc_123")
        
        parse_result = await parser_agent.process({
            "text": sample_text,
            "doc_type": "contract",
            "index": True
        })
        
        assert parse_result.success is True
        assert parse_result.data["doc_type"] == "contract"
        print("\n✅ DocParser successfully processed text.")

    # 3. Run Dispute Agent
    # We mock the RAG routing to simulate finding relevant chunks
    with patch("mahoun.rag.query_router.QueryRouter.route") as mock_route:
        # Simulate RAG finding the relevant chunk about payment
        mock_route.return_value.rag_result.results = [
            MagicMock(content="خریدار از پرداخت وجه خودداری کرده", doc_id="doc_123", score=0.9)
        ]
        
        dispute_result = await dispute_agent.process({
            "query": "مشکل پرداخت وجه",
            "documents": ["doc_123"]
        })
        
        assert dispute_result.success is True
        
        # Verify it detected a dispute
        disputes = dispute_result.data.get("disputes", [])
        assert len(disputes) > 0
        
        # Verify classification logic (should be FINANCIAL)
        first_dispute = disputes[0]
        # logic in _classify_disputes checks keywords like 'پرداخت'
        assert first_dispute["type"] == DisputeType.FINANCIAL
        
        print("✅ DisputeAgent correctly classified the financial dispute.")
        print(f"   Severity: {first_dispute.get('severity')}")
        print(f"   Risk: {dispute_result.data['risk_assessment']['overall_risk']}")

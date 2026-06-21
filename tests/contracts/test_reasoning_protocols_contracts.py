"""
Contract Tests for Reasoning Protocols
=======================================

Verifies that protocol implementations satisfy their contracts:
- QueryRouterProtocol contract
- RAGServiceProtocol contract  
- ModelOrchestratorProtocol contract
- ReasoningEngineProtocol contract

These tests ensure Liskov Substitution Principle (LSP) compliance.
"""

import pytest
from typing import Protocol
from unittest.mock import Mock, AsyncMock

from mahoun.core.protocols import (
    QueryRouterProtocol,
    RAGServiceProtocol,
    ModelOrchestratorProtocol,
    ModelDriverProtocol,
    ReasoningEngineProtocol,
    QueryClassificationResult,
    RoutedQueryResult,
    QueryType,
)


# ============================================================================
# Contract: QueryRouterProtocol
# ============================================================================


class TestQueryRouterContract:
    """Verify QueryRouterProtocol contract compliance."""

    @pytest.mark.asyncio
    async def test_route_returns_routed_query_result(self):
        """Contract: route() must return RoutedQueryResult."""
        router = Mock(spec=QueryRouterProtocol)
        
        # Mock implementation
        classification = QueryClassificationResult(
            query="test",
            query_type=QueryType.LEGAL_INQUIRY,
            confidence=0.9,
            keywords_found=[],
            metadata={},
        )
        
        expected_result = RoutedQueryResult(
            query="test",
            query_type=QueryType.LEGAL_INQUIRY,
            rag_result=Mock(),
            classification=classification,
            metadata={},
        )
        
        router.route = AsyncMock(return_value=expected_result)
        
        # Verify contract
        result = await router.route("test query")
        assert isinstance(result, RoutedQueryResult)
        assert result.query == "test"

    @pytest.mark.asyncio
    async def test_classify_returns_classification_result(self):
        """Contract: classify() must return QueryClassificationResult."""
        router = Mock(spec=QueryRouterProtocol)
        
        expected_result = QueryClassificationResult(
            query="test",
            query_type=QueryType.LEGAL_INQUIRY,
            confidence=0.9,
            keywords_found=["legal"],
            metadata={},
        )
        
        router.classify = AsyncMock(return_value=expected_result)
        
        # Verify contract
        result = await router.classify("test query")
        assert isinstance(result, QueryClassificationResult)
        assert 0.0 <= result.confidence <= 1.0

    def test_get_stats_returns_dict(self):
        """Contract: get_stats() must return Dict[str, Any]."""
        router = Mock(spec=QueryRouterProtocol)
        router.get_stats = Mock(return_value={"total_queries": 10})
        
        # Verify contract
        stats = router.get_stats()
        assert isinstance(stats, dict)


# ============================================================================
# Contract: ModelDriverProtocol
# ============================================================================


class TestModelDriverContract:
    """Verify ModelDriverProtocol contract compliance."""

    def test_model_name_is_string(self):
        """Contract: model_name must be a string."""
        driver = Mock(spec=ModelDriverProtocol)
        driver.model_name = "test-model"
        
        assert isinstance(driver.model_name, str)
        assert len(driver.model_name) > 0

    def test_generate_returns_string(self):
        """Contract: generate() must return string."""
        driver = Mock(spec=ModelDriverProtocol)
        driver.generate = Mock(return_value="Generated text")
        
        result = driver.generate("test prompt")
        assert isinstance(result, str)

    def test_is_loaded_returns_bool(self):
        """Contract: is_loaded() must return bool."""
        driver = Mock(spec=ModelDriverProtocol)
        driver.is_loaded = Mock(return_value=True)
        
        result = driver.is_loaded()
        assert isinstance(result, bool)


# ============================================================================
# Contract: ModelOrchestratorProtocol
# ============================================================================


class TestModelOrchestratorContract:
    """Verify ModelOrchestratorProtocol contract compliance."""

    @pytest.mark.asyncio
    async def test_get_driver_returns_model_driver(self):
        """Contract: get_driver() must return ModelDriverProtocol."""
        orchestrator = Mock(spec=ModelOrchestratorProtocol)
        
        mock_driver = Mock(spec=ModelDriverProtocol)
        mock_driver.model_name = "test-model"
        
        orchestrator.get_driver = AsyncMock(return_value=mock_driver)
        
        # Verify contract
        from mahoun.llm.orchestrator import ModelCapability
        
        driver = await orchestrator.get_driver(ModelCapability.REASONING)
        assert isinstance(driver, ModelDriverProtocol)


# ============================================================================
# Contract: ReasoningEngineProtocol
# ============================================================================


class TestReasoningEngineContract:
    """Verify ReasoningEngineProtocol contract compliance."""

    @pytest.mark.asyncio
    async def test_process_query_returns_dict_with_required_keys(self):
        """Contract: process_query() must return dict with specific keys."""
        engine = Mock(spec=ReasoningEngineProtocol)
        
        expected_result = {
            "response": "Test response",
            "query_type": "legal_inquiry",
            "model_used": "test-model",
            "capability": "reasoning",
            "confidence": 0.95,
            "context_sources": 2,
            "metadata": {},
        }
        
        engine.process_query = AsyncMock(return_value=expected_result)
        
        # Verify contract
        result = await engine.process_query("test query")
        
        # Required keys
        assert "response" in result
        assert "query_type" in result
        assert "model_used" in result
        assert "capability" in result
        assert "confidence" in result
        assert "context_sources" in result
        
        # Type checks
        assert isinstance(result["response"], str)
        assert isinstance(result["query_type"], str)
        assert isinstance(result["model_used"], str)
        assert isinstance(result["confidence"], (int, float))
        assert 0.0 <= result["confidence"] <= 1.0
        assert isinstance(result["context_sources"], int)
        assert result["context_sources"] >= 0


# ============================================================================
# Invariant Tests
# ============================================================================


class TestProtocolInvariants:
    """Test invariants that must hold for all protocol implementations."""

    def test_query_classification_confidence_bounds(self):
        """Invariant: Classification confidence must be in [0, 1]."""
        # Valid
        result = QueryClassificationResult(
            query="test",
            query_type=QueryType.LEGAL_INQUIRY,
            confidence=0.5,
            keywords_found=[],
            metadata={},
        )
        assert 0.0 <= result.confidence <= 1.0
        
        # Invalid - too high
        with pytest.raises(ValueError):
            QueryClassificationResult(
                query="test",
                query_type=QueryType.LEGAL_INQUIRY,
                confidence=1.5,
                keywords_found=[],
                metadata={},
            )
        
        # Invalid - negative
        with pytest.raises(ValueError):
            QueryClassificationResult(
                query="test",
                query_type=QueryType.LEGAL_INQUIRY,
                confidence=-0.1,
                keywords_found=[],
                metadata={},
            )

    def test_query_cannot_be_empty(self):
        """Invariant: Query strings cannot be empty."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            QueryClassificationResult(
                query="",
                query_type=QueryType.LEGAL_INQUIRY,
                confidence=0.9,
                keywords_found=[],
                metadata={},
            )
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            QueryClassificationResult(
                query="   ",  # Whitespace only
                query_type=QueryType.LEGAL_INQUIRY,
                confidence=0.9,
                keywords_found=[],
                metadata={},
            )

    def test_routed_result_must_have_valid_classification(self):
        """Invariant: RoutedQueryResult must have valid classification."""
        classification = QueryClassificationResult(
            query="test",
            query_type=QueryType.LEGAL_INQUIRY,
            confidence=0.9,
            keywords_found=[],
            metadata={},
        )
        
        # Valid
        result = RoutedQueryResult(
            query="test",
            query_type=QueryType.LEGAL_INQUIRY,
            rag_result=Mock(),
            classification=classification,
            metadata={},
        )
        assert isinstance(result.classification, QueryClassificationResult)
        
        # Invalid - wrong type
        with pytest.raises(TypeError):
            RoutedQueryResult(
                query="test",
                query_type=QueryType.LEGAL_INQUIRY,
                rag_result=Mock(),
                classification="not a classification",
                metadata={},
            )

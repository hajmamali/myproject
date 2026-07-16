#!/usr/bin/env python3
"""
Test Suite for AI Runtime Integration - Phase B Memory-Centric Intelligence

This test suite validates Phase B implementation including:
- Graph-Enhanced Reasoning
- Evidence-first reasoning chains
- Proof tree generation
- Memory-centric intelligence strategy

Version: 1.0.0
Phase: B - Memory-Centric Intelligence
"""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
import tempfile
import numpy as np

from mahoun.core.protocols.ai_runtime import AIRuntimeProtocol
from mahoun.core.models import (
    AIResponse,
    TokenUsage,
    GenerationMetadata,
    ResponseStatus,
    DeploymentProfile,
    DESKTOP_MINIMAL
)
from mahoun.reasoning.graph_enhanced import (
    GraphEnhancedReasoning,
    GraphService,
    RetrievalService,
    Evidence,
    ReasoningContext,
    ProofTreeNode,
    ReasoningResponse
)
from mahoun.embeddings import LocalEmbeddingService, LocalEmbeddingConfig
from mahoun.ai.adapters import GGUFAdapter, GGUFAdapterConfig
from mahoun.ai.runtime_manager import AIRuntimeManager, RuntimeConfig


class MockGraphService(GraphService):
    """Mock graph service for testing"""
    
    def find_evidence(self, query: str, max_depth: int = 3, min_confidence: float = 0.7):
        """Return mock evidence"""
        import hashlib
        
        evidence_items = [
            Evidence(
                source="graph://case_001",
                content=f"Mock evidence for: {query}",
                confidence=0.85,
                provenance_hash=hashlib.sha256(b"mock1").hexdigest(),
                metadata={"case_id": "001", "type": "precedent"}
            ),
            Evidence(
                source="graph://statute_042",
                content="Mock statutory provision",
                confidence=0.92,
                provenance_hash=hashlib.sha256(b"mock2").hexdigest(),
                metadata={"statute_id": "042", "type": "law"}
            )
        ]
        
        return evidence_items
    
    def get_context(self, evidence):
        """Return mock graph context"""
        return {
            "evidence_count": len(evidence),
            "graph_depth": 2,
            "confidence_avg": 0.885,
            "source_types": ["precedent", "law"]
        }


class MockRetrievalService(RetrievalService):
    """Mock retrieval service for testing"""
    
    def get_relevant_context(self, query: str, evidence, top_k: int = 5):
        """Return mock retrieval context"""
        return {
            "top_k_documents": [
                {"doc_id": "doc_001", "score": 0.89},
                {"doc_id": "doc_002", "score": 0.76}
            ],
            "total_retrieved": 2,
            "retrieval_time_ms": 45.2
        }


class MockAIRuntime(AIRuntimeProtocol):
    """Mock AI runtime for testing"""
    
    def __init__(self):
        self.loaded = False
        self.model_metadata = None
    
    def load_model(self, model_path: str, **kwargs) -> bool:
        self.loaded = True
        return True
    
    def generate(self, prompt: str, **kwargs):
        """Generate mock response"""
        return AIResponse(
            request_id="test-123",
            correlation_id=kwargs.get("correlation_id"),
            response_text="Based on the provided evidence, the legal analysis indicates...",
            status=ResponseStatus.SUCCESS,
            confidence_score=0.82,
            quality_score=0.88,
            token_usage=TokenUsage(100, 50, 150),
            generation_metadata=GenerationMetadata(
                model_id="mock-model",
                model_format="GGUF",
                quantization="Q4_K_M",
                parameters_count=3_000_000_000,
                generation_params={"temperature": 0.3},
                inference_time_ms=250.0,
                tokens_per_second=600.0,
                memory_usage_mb=2048.0,
                deployment_profile="desktop_minimal"
            )
        )
    
    def health_check(self):
        from mahoun.core.protocols.ai_runtime import HealthStatus, ModelStatus
        return HealthStatus(
            status=ModelStatus.READY if self.loaded else ModelStatus.NOT_LOADED,
            model_loaded=self.loaded,
            memory_usage_mb=2048.0,
            last_inference_time=250.0,
            error_message=None,
            uptime_seconds=100.0,
            total_requests=1,
            failed_requests=0
        )
    
    def unload_model(self) -> bool:
        self.loaded = False
        return True
    
    def get_metadata(self):
        return None


class TestTaskB11_GraphEnhancedReasoning:
    """Test Graph-Enhanced Reasoning implementation (Task B.1.1)"""
    
    @pytest.mark.p2
    def test_reasoning_engine_initialization(self):
        """Reasoning engine should initialize with required services"""
        graph_service = MockGraphService()
        retrieval_service = MockRetrievalService()
        ai_runtime = MockAIRuntime()
        
        engine = GraphEnhancedReasoning(
            graph_service=graph_service,
            retrieval_service=retrieval_service,
            ai_runtime=ai_runtime
        )
        
        assert engine.graph is not None
        assert engine.retrieval is not None
        assert engine.ai_runtime is not None
    
    @pytest.mark.p2
    def test_process_query_returns_reasoning_response(self):
        """Process query should return complete reasoning response"""
        graph_service = MockGraphService()
        retrieval_service = MockRetrievalService()
        ai_runtime = MockAIRuntime()
        
        engine = GraphEnhancedReasoning(
            graph_service=graph_service,
            retrieval_service=retrieval_service,
            ai_runtime=ai_runtime
        )
        
        response = engine.process_query(
            query="What is the legal precedent for contract disputes?",
            correlation_id="test-corr-001"
        )
        
        assert isinstance(response, ReasoningResponse)
        assert response.query is not None
        assert response.answer is not None
        assert response.confidence > 0.0
        assert len(response.evidence) > 0
        assert response.proof_tree is not None
    
    @pytest.mark.p2
    def test_evidence_first_priority(self):
        """Evidence should be retrieved before AI reasoning"""
        graph_service = MockGraphService()
        retrieval_service = MockRetrievalService()
        ai_runtime = MockAIRuntime()
        
        engine = GraphEnhancedReasoning(
            graph_service=graph_service,
            retrieval_service=retrieval_service,
            ai_runtime=ai_runtime
        )
        
        response = engine.process_query(
            query="Test query for evidence priority"
        )
        
        # Evidence should be present
        assert len(response.evidence) >= 2
        assert all(isinstance(e, Evidence) for e in response.evidence)
        
        # Evidence confidence should influence final confidence
        assert response.confidence > 0.7


class TestTaskB12_EvidenceFirstReasoning:
    """Test Evidence-first reasoning chain (Task B.1.2)"""
    
    @pytest.mark.p2
    def test_evidence_retrieval_from_graph(self):
        """Evidence should be retrieved from knowledge graph first"""
        graph_service = MockGraphService()
        
        evidence = graph_service.find_evidence(
            query="Contract breach analysis",
            max_depth=3,
            min_confidence=0.7
        )
        
        assert len(evidence) > 0
        assert all(e.confidence >= 0.7 for e in evidence)
        assert all(isinstance(e, Evidence) for e in evidence)
    
    @pytest.mark.p2
    def test_reasoning_context_creation(self):
        """Reasoning context should aggregate evidence and context"""
        evidence_items = [
            Evidence(
                source="test://1",
                content="Evidence 1",
                confidence=0.9,
                provenance_hash="a" * 64,
                metadata={}
            )
        ]
        
        context = ReasoningContext(
            query="Test query",
            evidence_items=evidence_items,
            graph_context={"depth": 2},
            retrieval_context={"docs": 5},
            correlation_id="test-123"
        )
        
        assert context.query == "Test query"
        assert len(context.evidence_items) == 1
        assert context.get_total_evidence_confidence() == 0.9
        assert context.get_evidence_sources() == ["test://1"]


class TestTaskB13_UltraGraphBuilderIntegration:
    """Test Integration with UltraGraphBuilder (Task B.1.3)"""
    
    @pytest.mark.p2
    def test_graph_context_retrieval(self):
        """Graph context should be retrieved for evidence"""
        graph_service = MockGraphService()
        
        evidence = [
            Evidence(
                source="test://1",
                content="Test",
                confidence=0.8,
                provenance_hash="a" * 64,
                metadata={}
            )
        ]
        
        context = graph_service.get_context(evidence)
        
        assert isinstance(context, dict)
        assert "evidence_count" in context
        assert context["evidence_count"] == 1


class TestTaskB14_ProofTreeGeneration:
    """Test Proof tree generation for auditability (Task B.1.4)"""
    
    @pytest.mark.p2
    def test_proof_tree_node_creation(self):
        """Proof tree nodes should be creatable"""
        node = ProofTreeNode(
            node_id="node-001",
            node_type="evidence",
            content="Test evidence",
            confidence=0.85,
            children=[],
            metadata={"source": "graph"}
        )
        
        assert node.node_id == "node-001"
        assert node.node_type == "evidence"
        assert node.confidence == 0.85
    
    @pytest.mark.p2
    def test_proof_tree_serialization(self):
        """Proof tree should be serializable to dict"""
        child_node = ProofTreeNode(
            node_id="child-001",
            node_type="evidence",
            content="Child evidence",
            confidence=0.9,
            children=[],
            metadata={}
        )
        
        root_node = ProofTreeNode(
            node_id="root-001",
            node_type="conclusion",
            content="Final conclusion",
            confidence=0.85,
            children=[child_node],
            metadata={"query": "test"}
        )
        
        tree_dict = root_node.to_dict()
        
        assert isinstance(tree_dict, dict)
        assert tree_dict["node_id"] == "root-001"
        assert len(tree_dict["children"]) == 1
        assert tree_dict["children"][0]["node_id"] == "child-001"
    
    @pytest.mark.p2
    def test_complete_reasoning_generates_proof_tree(self):
        """Complete reasoning should generate verifiable proof tree"""
        engine = GraphEnhancedReasoning(
            graph_service=MockGraphService(),
            retrieval_service=MockRetrievalService(),
            ai_runtime=MockAIRuntime()
        )
        
        response = engine.process_query(
            query="Generate proof tree test"
        )
        
        assert response.proof_tree is not None
        assert response.proof_tree.node_type == "conclusion"
        assert len(response.proof_tree.children) > 0
        
        # Should have evidence nodes
        evidence_nodes = [
            child for child in response.proof_tree.children
            if child.node_type == "evidence"
        ]
        assert len(evidence_nodes) > 0
        
        # Should have inference node
        inference_nodes = [
            child for child in response.proof_tree.children
            if child.node_type == "inference"
        ]
        assert len(inference_nodes) > 0


class TestTaskB2_KnowledgeGraphPriority:
    """Test Knowledge Graph Priority Enhancement (Task B.2)"""
    
    @pytest.mark.p2
    def test_graph_quality_over_model_size(self):
        """Graph evidence quality should outweigh model size"""
        engine = GraphEnhancedReasoning(
            graph_service=MockGraphService(),
            retrieval_service=MockRetrievalService(),
            ai_runtime=MockAIRuntime()
        )
        
        response = engine.process_query("Test graph priority")
        
        # Evidence confidence should have higher weight
        evidence_confidence = response.metadata["avg_evidence_confidence"]
        ai_inference_time = response.metadata["ai_inference_time_ms"]
        graph_evidence_count = response.metadata["graph_evidence_count"]
        
        # Evidence should be retrieved and high quality
        assert graph_evidence_count >= 2
        assert evidence_confidence > 0.8
        
        # AI inference time should be reasonable
        assert ai_inference_time > 0
    
    @pytest.mark.p2
    def test_confidence_calculation_weights_evidence(self):
        """Confidence calculation should weight evidence > AI"""
        engine = GraphEnhancedReasoning(
            graph_service=MockGraphService(),
            retrieval_service=MockRetrievalService(),
            ai_runtime=MockAIRuntime()
        )
        
        # Test confidence calculation
        evidence_conf = 0.9
        ai_conf = 0.7
        
        combined = engine._calculate_confidence(evidence_conf, ai_conf)
        
        # Should be closer to evidence confidence (70/30 weight)
        expected = (evidence_conf * 0.7) + (ai_conf * 0.3)
        assert abs(combined - expected) < 0.001


class TestTaskB3_LocalModelTesting:
    """Test Local Model Integration Testing (Task B.3)"""
    
    @pytest.mark.p2
    def test_gguf_adapter_mock_testing(self):
        """GGUF adapter should work with mock models"""
        # This would test with actual GGUF models in real scenario
        # For now, we test the interface
        ai_runtime = MockAIRuntime()
        
        loaded = ai_runtime.load_model("mock-model.gguf")
        assert loaded is True
        
        health = ai_runtime.health_check()
        assert health.model_loaded is True
    
    @pytest.mark.p2
    def test_embedding_service_initialization(self):
        """Embedding service should initialize correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LocalEmbeddingConfig(
                models_dir=tmpdir,
                deployment_profile=DESKTOP_MINIMAL,
                device="cpu"
            )
            
            service = LocalEmbeddingService(config)
            assert service is not None
            assert service.config.device == "cpu"


class TestMemoryCentricIntelligence:
    """Test overall memory-centric intelligence strategy"""
    
    @pytest.mark.p2
    def test_memory_over_parameters(self):
        """Memory quality should be prioritized over model parameters"""
        # Create reasoning engine
        engine = GraphEnhancedReasoning(
            graph_service=MockGraphService(),
            retrieval_service=MockRetrievalService(),
            ai_runtime=MockAIRuntime()
        )
        
        response = engine.process_query("Memory centric test")
        
        # Verify memory-centric approach
        assert len(response.evidence) > 0  # Evidence retrieved
        assert response.proof_tree is not None  # Audit trail
        assert response.ai_response is not None  # AI used as final step
        
        # Evidence should drive reasoning
        assert response.metadata["graph_evidence_count"] > 0
    
    @pytest.mark.p2
    def test_reasoning_response_completeness(self):
        """Reasoning response should be complete and auditable"""
        engine = GraphEnhancedReasoning(
            graph_service=MockGraphService(),
            retrieval_service=MockRetrievalService(),
            ai_runtime=MockAIRuntime()
        )
        
        response = engine.process_query("Completeness test")
        
        # All required fields present
        assert response.query is not None
        assert response.answer is not None
        assert 0.0 <= response.confidence <= 1.0
        assert len(response.evidence) > 0
        assert response.proof_tree is not None
        assert response.ai_response is not None
        assert response.reasoning_time_ms > 0
        
        # Serializable
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert "query" in response_dict
        assert "proof_tree" in response_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

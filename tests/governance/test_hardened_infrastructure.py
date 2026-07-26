"""
Tests for Hardened Infrastructure & Layered Facade Pipeline
===========================================================

Classification: CRITICAL HARDENING TESTS
Purpose: Ruthlessly verify that all strict validation layers, governance gates,
         quarantine routing, graduation, facade boundaries, and parallelized
         pipelines perform flawlessly without silent failures.

Test Coverage:
- Strict Schema Validation Gate (rejects extra/mistyped fields)
- Confidence-based Quarantine Routing
- Graduation Manager promotion lifecycle & invariants
- Facade Backdoor Seal (Governed session enforcement in UltraGraphBuilder)
- Parallel LLM Refinement Concurrency & Safety
"""

import asyncio
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, AsyncMock

from pydantic import BaseModel, Field, ConfigDict, ValidationError

from mahoun.core.governance import GovernanceContextManager
from mahoun.core.governance.violations import GovernanceViolationError, ViolationCategory
from mahoun.core.governance.validator_pipeline import (
    ValidatorPipeline,
    register_schema,
    strict_schema_validation_gate,
    SCHEMA_REGISTRY,
)
from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
from mahoun.graph.neo4j.graduation_manager import GraduationManager, GraduationError
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder, GraphNode, GraphEdge
from mahoun.pipelines.ingestion.hardened_legal_pipeline import HardenedLegalPipeline
from mahoun.pipelines.ingestion.provenance_aware_mapper import ProvenanceAwareNERMapper

from tests.fixtures.provenance_factory import build_test_provenance


# ============================================================================
# PYDANTIC SCHEMAS FOR TESTING
# ============================================================================

class TestVerdictSchema(BaseModel):
    id: str = Field(description="Unique verdict identifier")
    title: str = Field(description="Title of the verdict")
    court_name: str = Field(description="Name of the issuing court")
    confidence: float = Field(default=1.0)
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def setup_governance_context():
    """Ensure an active governance context exists for all tests."""
    GovernanceContextManager._reset_for_test()
    ctx = GovernanceContextManager.create_context(
        correlation_id="test-corr-id-999",
        execution_mode="STRICT",
    )
    ctx.validate_governance_scope()
    # _governance_stack holds a mutable list — use the ContextVar API directly.
    current = GovernanceContextManager._get_stack()
    token = GovernanceContextManager._governance_stack.set([*current, ctx])
    yield ctx
    GovernanceContextManager._governance_stack.reset(token)


@pytest.fixture
def mock_raw_executor():
    """Create a mock query executor for Neo4j."""
    executor = MagicMock()
    executor.return_value = []
    return executor


@pytest.fixture
def governed_session(mock_raw_executor):
    """Create a governed session with mock validation pipeline."""
    pipeline = ValidatorPipeline()
    session = GovernedNeo4jSession(
        raw_executor=mock_raw_executor,
        pipeline=pipeline,
        correlation_id="test-corr-id-999",
        actor_id="test_actor",
    )
    return session


# ============================================================================
# TESTS: Strict Schema Validation Gate
# ============================================================================

class TestStrictSchemaValidationGate:
    """Verifies that the schema validation gate is strict and unbypassable."""

    @pytest.mark.p2
    def test_schema_registration(self):
        """Test that schemas can be registered and retrieved correctly."""
        register_schema("Verdict", TestVerdictSchema)
        assert SCHEMA_REGISTRY["Verdict"] == TestVerdictSchema

    @pytest.mark.p2
    def test_valid_node_passes_strict_gate(self):
        """Test that fully compliant data passes the strict validation gate."""
        register_schema("Verdict", TestVerdictSchema)
        
        valid_data = {
            "id": "verd-001",
            "title": "Verdict on Tax Avoidance Case",
            "court_name": "Tehran Supreme Court",
            "confidence": 1.0,
            "_label": "Verdict",
            "provenance": build_test_provenance(correlation_id="test-corr-id-999"),
        }
        
        # Should not raise any exception
        strict_schema_validation_gate(valid_data, correlation_id="test-corr")

    @pytest.mark.p2
    def test_extra_fields_raise_governance_violation(self):
        """Test that extra/hallucinated fields trigger immediate fail-closed violation."""
        register_schema("Verdict", TestVerdictSchema)
        
        invalid_data = {
            "id": "verd-001",
            "title": "Verdict on Tax Avoidance Case",
            "court_name": "Tehran Supreme Court",
            "confidence": 1.0,
            "hallucinated_field": "LLM_garbage",  # Extra field!
            "_label": "Verdict",
            "provenance": {"source": "test"},
        }
        
        with pytest.raises(GovernanceViolationError) as exc_info:
            strict_schema_validation_gate(invalid_data, correlation_id="test-corr")
            
        violation = exc_info.value.violation
        assert violation.category == ViolationCategory.SCHEMA_VIOLATION
        assert "Strict schema validation failed" in violation.message

    @pytest.mark.p2
    def test_invalid_field_type_raises_governance_violation(self):
        """Test that mismatched data types trigger immediate fail-closed violation."""
        register_schema("Verdict", TestVerdictSchema)
        
        invalid_data = {
            "id": "verd-001",
            "title": "Verdict on Tax Avoidance Case",
            "court_name": "Tehran Supreme Court",
            "confidence": "highly_confident",  # Mismatched type! Expected float
            "_label": "Verdict",
            "provenance": {"source": "test"},
        }
        
        with pytest.raises(GovernanceViolationError) as exc_info:
            strict_schema_validation_gate(invalid_data, correlation_id="test-corr")
            
        violation = exc_info.value.violation
        assert violation.category == ViolationCategory.SCHEMA_VIOLATION


# ============================================================================
# TESTS: Confidence-Based Quarantine Routing
# ============================================================================

class TestQuarantineRouting:
    """Verifies that nodes are routed to Quarantine based on confidence."""

    @pytest.mark.p2
    def test_high_confidence_routes_to_master_graph(self, governed_session, mock_raw_executor):
        """Nodes with confidence == 1.0 are committed to Master Graph."""
        node_data = {
            "id": "node-100",
            "title": "Perfect Node",
            "court_name": "Tehran",
            "confidence": 1.0,
            "_label": "Verdict",
            "provenance": build_test_provenance(correlation_id="test-corr-id-999"),
        }
        
        governed_session.write_node(label="Verdict", node_data=node_data, merge=True)
        
        # Verify executed query matches canonical label
        args, kwargs = mock_raw_executor.call_args
        executed_query = args[0]
        assert "MERGE (n:Verdict {id: $id})" in executed_query

    @pytest.mark.p2
    def test_low_confidence_routes_to_quarantine(self, governed_session, mock_raw_executor):
        """Nodes with confidence < 1.0 are routed to Quarantined label."""
        node_data = {
            "id": "node-200",
            "title": "Uncertain Node",
            "court_name": "Tehran",
            "confidence": 0.85,  # Low confidence!
            "provenance": build_test_provenance(correlation_id="test-corr-id-999"),
        }
        
        governed_session.write_node(label="Verdict", node_data=node_data, merge=True)
        
        # Verify executed query routes to QuarantinedVerdict
        args, kwargs = mock_raw_executor.call_args
        executed_query = args[0]
        assert "MERGE (n:QuarantinedVerdict {id: $id})" in executed_query


# ============================================================================
# TESTS: Graduation Manager
# ============================================================================

class TestGraduationManager:
    """Verifies lifecycle promotion and strict invariants of GraduationManager."""

    @pytest.mark.p2
    def test_successful_graduation(self, governed_session, mock_raw_executor):
        """Test that promotion works perfectly when verified confidence is exactly 1.0."""
        manager = GraduationManager(governed_session)
        
        result = manager.graduate_node(
            node_id="node-200",
            quarantined_label="QuarantinedVerdict",
            target_label="Verdict",
            verified_confidence=1.0,
            attestation_source="human_verifier:ali",
        )
        
        assert result["node_id"] == "node-200"
        assert result["from_label"] == "QuarantinedVerdict"
        assert result["to_label"] == "Verdict"
        assert result["attestation_source"] == "human_verifier:ali"
        assert manager.get_statistics()["total_graduated"] == 1

        # Check Cypher call to canonical label
        args, kwargs = mock_raw_executor.call_args
        executed_query = args[0]
        assert "MERGE (n:Verdict {id: $id})" in executed_query

    @pytest.mark.p2
    def test_graduation_rejected_for_low_confidence(self, governed_session):
        """Test that promoting with confidence < 1.0 is strictly forbidden."""
        manager = GraduationManager(governed_session)
        
        with pytest.raises(GraduationError) as exc_info:
            manager.graduate_node(
                node_id="node-200",
                quarantined_label="QuarantinedVerdict",
                target_label="Verdict",
                verified_confidence=0.99,  # Forbidden! Must be exactly 1.0
                attestation_source="automated_pipeline",
            )
            
        assert "confidence must be exactly 1.0" in str(exc_info.value)

    @pytest.mark.p2
    def test_graduation_rejected_for_invalid_quarantined_label(self, governed_session):
        """Test that promoting non-quarantined nodes is forbidden."""
        manager = GraduationManager(governed_session)
        
        with pytest.raises(GraduationError) as exc_info:
            manager.graduate_node(
                node_id="node-200",
                quarantined_label="Verdict",  # Invalid quarantined label format
                target_label="Verdict",
                verified_confidence=1.0,
                attestation_source="human_verifier:ali",
            )
            
        assert "does not start with 'Quarantined'" in str(exc_info.value)


# ============================================================================
# TESTS: Facade Backdoor Seal
# ============================================================================

class TestFacadeBackdoorSeal:
    """Verifies that all pipelines route writes through governed session only."""

    @pytest.mark.p2
    def test_graph_builder_rejects_raw_adapter(self):
        """Test that UltraGraphBuilder throws exception if raw adapter is passed."""
        builder = UltraGraphBuilder()
        raw_adapter = MagicMock()
        
        # Should raise TypeError because raw adapter bypasses governance
        with pytest.raises(TypeError) as exc_info:
            builder.export_to_neo4j(raw_adapter)
            
        assert "GOVERNANCE VIOLATION" in str(exc_info.value)

    @pytest.mark.p2
    def test_graph_builder_export_via_governed_session(self, governed_session, mock_raw_executor):
        """Test that UltraGraphBuilder successfully exports via GovernedNeo4jSession."""
        builder = UltraGraphBuilder()
        
        # Populate nodes/edges in builder
        node_1 = GraphNode(
            id="node-300",
            label="ماده 10",
            node_type="Verdict",
            confidence=1.0,
        )
        node_2 = GraphNode(
            id="node-400",
            label="ماده 11",
            node_type="LawArticle",  # Valid target for REFERS_TO
            confidence=1.0,
        )
        builder.nodes[node_1.id] = node_1
        builder.nodes[node_2.id] = node_2
        
        edge = GraphEdge(
            source_id="node-300",
            target_id="node-400",
            relationship_type="REFERS_TO",  # Valid: Verdict -> LawArticle
            confidence=0.9,
        )
        builder.edges.append(edge)
        
        # Export via governed session
        builder.export_to_neo4j(governed_session)
        
        # Ensure raw executor was called (node writes + relationship write)
        assert mock_raw_executor.call_count == 3


# ============================================================================
# TESTS: Parallel LLM Refinement & High-Throughput
# ============================================================================

class TestParallelLLMRefinement:
    """Verifies that the concurrent LLM refinement performs safely and fast."""

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_parallel_refinement_performance(self):
        """Test that parallelized refinement runs under concurrency controls."""
        # Create pipeline instance
        ner_engine = MagicMock()
        ner_engine.extract.return_value = {
            "Verdict": [{"text": f"Entity {i}", "confidence": 0.9} for i in range(15)]
        }
        
        mapper = MagicMock()
        
        # Mock LLM validation helper to be async with a slight sleep
        async def mock_llm_validate(entity, text):
            await asyncio.sleep(0.05)  # Simulate API latency
            return True, 0.95, "Valid entity"

        gate = MagicMock()
        id_gen = MagicMock()
        id_gen.generate_entity_id.side_effect = lambda entity_type, entity_data, context: f"id-{entity_data['text']}"

        # Initialize pipeline
        pipeline = HardenedLegalPipeline(
            ner_engine=ner_engine,
            mapper=mapper,
            llm_refiner=MagicMock(),
            gate=gate,
            id_gen=id_gen,
        )
        pipeline._llm_validate_entity = mock_llm_validate
        
        # Fast path mapping
        pipeline._strict_map_entity = lambda ent, chunks: {"source": "chunk-1"}
        
        # Process document
        start_time = asyncio.get_event_loop().time()
        final_entities, audit_trail = await pipeline.process_document(
            text="Iran supreme court verdict",
            chunks=[{"chunk_id": "chunk-1", "text": "text", "start": 0, "end": 10}],
            doc_id="doc-001"
        )
        duration = asyncio.get_event_loop().time() - start_time
        
        # 15 entities * 0.05s = 0.75s if sequential.
        # Since concurrency limit is 10, it should execute in ~2 batches: ~0.10s.
        assert duration < 0.25  # High-throughput parallel execution verified!
        assert len(final_entities) == 15
        assert len(audit_trail) == 15

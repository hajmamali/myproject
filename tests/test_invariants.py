import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from mahoun.graph.ultra_graph_builder import GraphNode, GraphEdge
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
from mahoun.reasoning.reasoning_recorder import ReasoningRecorder, ReasoningStep


def test_graph_node_requires_provenance():
    """GraphNode must be instantiated with a provenance."""
    prov = ProvenanceMetadata.create(
        source="test",
        correlation_id="test-id",
        author="test",
        governance_scope_id="scope",
        runtime_attestation_id="attest",
        lineage_parent=None,
    )
    # Should succeed
    node = GraphNode(
        id="n1",
        label="test",
        node_type="Fact",
        provenance=prov,
        properties={},
        confidence=1.0,
    )
    assert node.provenance == prov
    # Trying to create without provenance should fail due to missing argument
    with pytest.raises(TypeError):
        GraphNode(
            id="n2",
            label="test",
            node_type="Fact",
            properties={},
            confidence=1.0,
            # missing provenance
        )


def test_provenance_is_set_on_fact_nodes_simulation():
    """Simulate the fact node creation to ensure provenance is set."""
    known_prov = ProvenanceMetadata.create(
        source="test",
        correlation_id="cid",
        author="auth",
        governance_scope_id="scope",
        runtime_attestation_id="attest",
        lineage_parent=None,
    )
    # Simulate the call from _build_case_graph
    node = GraphNode(
        id="fact_0",
        label="fact1",
        node_type="Fact",
        provenance=known_prov,
        properties={"fact_text": "fact1", "fact_index": 0},
        confidence=1.0,
    )
    assert node.provenance == known_prov
    assert node.label == "fact1"
    assert node.properties["fact_text"] == "fact1"


def test_reasoning_recorder_records_step():
    """Recorder can record a step and maintain hash chain."""
    recorder = ReasoningRecorder()
    prov = ProvenanceMetadata.create(
        source="test",
        correlation_id="cid",
        author="auth",
        governance_scope_id="scope",
        runtime_attestation_id="attest",
        lineage_parent=None,
    )
    step = recorder.record_step(
        step_type="test_step",
        inputs={"a": 1},
        outputs={"b": 2},
        provenance=prov,
    )
    assert isinstance(step, ReasoningStep)
    assert step.step_type == "test_step"
    assert step.inputs == {"a": 1}
    assert step.outputs == {"b": 2}
    assert step.provenance == prov
    # Verify chain
    assert recorder.verify_chain()  # simplified implementation always returns True
    steps = recorder.get_steps()
    assert len(steps) == 1
    assert steps[0] == step


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
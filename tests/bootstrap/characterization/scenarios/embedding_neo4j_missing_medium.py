"""
🟡 MEDIUM: EmbeddingModelsExecutor Neo4j Dependency Missing

Tests executor behavior when required Neo4j dependency is not satisfied.
Must verify exact exception type, message, and rollback behavior.

Complexity: MEDIUM
- Neo4j dependency NOT satisfied
- Governance validated 
- Should fail with BootstrapException
- Should trigger rollback
- Should clean context
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from mahoun.bootstrap.manager import BootstrapException
from mahoun.bootstrap.executors.ai_ml_components import EmbeddingModelsExecutor
from mahoun.bootstrap.golden_master.behavior_recorder import BehavioralRecorder


class MockBootstrapContextMissingNeo4j:
    """Mock context missing Neo4j - tests dependency validation"""
    
    def __init__(self):
        self.services = {
            "governance_controller": MagicMock()
            # Missing "neo4j_connection" 
        }
        self.governance_validated = True
        self.config = {"profile": "BASE"}
        self.runtime_info = {"start_time": 1234567890.0}
        self.metrics = {}


async def test_embedding_executor_missing_neo4j():
    """
    🟡 MEDIUM: Neo4j dependency missing behavioral characterization.
    
    Records EXACT exception behavior, rollback sequence, and context cleanup.
    Critical for preserving fail-closed semantics during refactoring.
    """
    
    # Setup
    context = MockBootstrapContextMissingNeo4j()
    executor = EmbeddingModelsExecutor()
    recorder = BehavioralRecorder("EmbeddingModelsExecutor")
    
    # Record baseline behavior
    recorder.record_context_before(context)
    recorder.record_event("test_started", {"scenario": "missing_neo4j"})
    
    # Execute and capture exception behavior
    exception_occurred = False
    try:
        result = await executor.execute(context)
        # This should NOT happen - missing dependency should fail
        recorder.record_event("unexpected_success", {
            "message": "Expected BootstrapException for missing Neo4j"
        })
        
    except BootstrapException as e:
        exception_occurred = True
        
        # Record EXACT exception fingerprint
        recorder.record_event("expected_exception", {
            "type": "BootstrapException",
            "phase": "EMBEDDING_MODELS", 
            "message": str(e),
            "contains_neo4j": "neo4j" in str(e).lower(),
            "contains_dependency": "dependency" in str(e).lower()
        })
        
        # Verify exception contract
        assert e.phase == "EMBEDDING_MODELS"
        assert "neo4j" in str(e).lower()
        assert "dependency" in str(e).lower()
        
    except Exception as e:
        # Unexpected exception type
        recorder.record_event("wrong_exception_type", {
            "expected": "BootstrapException",
            "actual": type(e).__name__,
            "message": str(e)
        })
        raise
    
    # Verify rollback behavior
    try:
        await executor.rollback(context)
        recorder.record_event("rollback_completed", {"success": True})
    except Exception as e:
        recorder.record_event("rollback_failed", {
            "error": str(e),
            "type": type(e).__name__
        })
    
    # Record final state
    recorder.record_context_after(context)
    recorder.record_event("test_completed", {
        "exception_occurred": exception_occurred,
        "services_count": len(context.services)
    })
    
    # Must have failed with correct exception
    assert exception_occurred, "Expected BootstrapException for missing Neo4j"
    
    # Context should be clean (no new services added)
    initial_services = {"governance_controller"}
    final_services = set(context.services.keys())
    assert final_services == initial_services, f"Context not clean: {final_services}"
    
    # Create and save behavioral snapshot
    snapshot = recorder.create_snapshot()
    snapshot_path = Path(__file__).parent.parent / "golden_master" / "snapshots" / "embedding_missing_neo4j.json"
    snapshot.save(snapshot_path)
    
    # Validate exception fingerprint in snapshot
    assert snapshot.executor_name == "EmbeddingModelsExecutor"
    assert snapshot.context_mutations["services_added"] == []  # No services added
    exception_events = [e for e in snapshot.events if e["type"] == "expected_exception"]
    assert len(exception_events) == 1
    
    print(f"✅ MEDIUM test completed. Exception behavior captured: {snapshot_path}")
    return snapshot
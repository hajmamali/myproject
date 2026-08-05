"""
🟢 EASY: EmbeddingModelsExecutor Basic Success Path

This is the simplest characterization test - happy path execution
with all dependencies satisfied and BASE profile.

Complexity: EASY
- Neo4j dependency satisfied
- Governance validated  
- BASE profile (minimal models)
- No failures or edge cases

KEY PRINCIPLE:
- REAL Executor code (not mocked)
- FAKE infrastructure (controlled)
- Captures behavioral contract, not implementation details
"""

import pytest
from pathlib import Path

from mahoun.bootstrap.executors.ai_ml_components import EmbeddingModelsExecutor
from mahoun.bootstrap.golden_master.behavior_recorder import BehavioralRecorder
from tests.bootstrap.characterization.fixtures import (
    build_easy_scenario,
    inject_fake_embedding_service,
    assert_behavioral_contract_preserved
)


@pytest.mark.asyncio
async def test_embedding_executor_easy_success():
    """
    🟢 EASY: Basic success path behavioral characterization.
    
    This test records the EXACT behavioral contract for the simplest
    possible execution. Any deviation during refactoring = regression.
    
    What we capture:
    ✅ Service registration sequence (embedding_service added)
    ✅ Context mutations (metrics, config changes)
    ✅ Success/failure paths
    ✅ Rollback availability
    
    What we DON'T capture (irrelevant for behavior):
    ❌ Actual model weights
    ❌ GPU memory usage
    ❌ File system layout
    ❌ Network calls
    """
    
    # Build controlled test environment
    context = build_easy_scenario()
    executor = EmbeddingModelsExecutor()
    recorder = BehavioralRecorder("EmbeddingModelsExecutor")
    
    # Capture state BEFORE execution
    snapshot_before = context.snapshot()
    recorder.record_context_before(context)
    recorder.record_event("test_started", {"scenario": "easy_success"})
    
    # Execute with FAKE infrastructure but REAL executor logic
    with inject_fake_embedding_service():
        try:
            result = await executor.execute(context)
            
            # Record what actually happened
            recorder.record_event("execution_completed", {
                "success": result.success,
                "phase": result.phase,
                "components_count": len(result.components)
            })
            
            #  Capture state AFTER execution
            snapshot_after = context.snapshot()
            recorder.record_context_after(context)
            recorder.record_event("test_completed", {"status": "success"})
            
            # Verify behavioral contract (THIS is what refactoring must preserve)
            assert result.success is True, "Executor must succeed in EASY scenario"
            assert result.phase == "EMBEDDING_MODELS", "Phase must be EMBEDDING_MODELS"
            assert "embedding_service" in context.services, "embedding_service must be registered"
            
            # Deep behavioral contract verification
            # NOTE: Metrics are in result.metrics, not context.metrics!
            assert_behavioral_contract_preserved(
                snapshot_before,
                snapshot_after,
                expected_services_added=["embedding_service"],
                expected_metrics=[]  # Metrics are checked separately below
            )
            
            # Verify critical metrics from PhaseResult
            assert "models_loaded" in result.metrics, "models_loaded metric must be present"
            assert "total_execution_time_ms" in result.metrics, "total_execution_time_ms metric must be present"
            assert result.metrics["models_loaded"] > 0, "At least one model must be loaded"
            
        except Exception as e:
            recorder.record_event("unexpected_exception", {
                "type": type(e).__name__,
                "message": str(e)
            })
            recorder.record_context_after(context)
            raise
    
    # Create and save behavioral snapshot (golden master)
    snapshot = recorder.create_snapshot()
    snapshot_path = Path(__file__).parent.parent / "golden_master" / "snapshots" / "embedding_easy_success.json"
    snapshot.save(snapshot_path)
    
    # Validate snapshot quality
    assert snapshot.executor_name == "EmbeddingModelsExecutor"
    assert "embedding_service" in snapshot.context_mutations.get("services_added", [])
    assert len(snapshot.events) >= 3, "Must record at least: start, execute, complete"
    
    print(f"✅ EASY test completed. Behavioral snapshot saved to: {snapshot_path}")
    print(f"   Services added: {snapshot.context_mutations.get('services_added')}")
    print(f"   Mutations logged: {len(context._mutation_log)}")
    
    return snapshot
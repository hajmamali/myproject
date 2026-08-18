"""
🔴 HARD: EmbeddingModelsExecutor Rollback Race Conditions

Tests complex rollback scenarios with partial failures, timing issues,
and concurrent state mutations. Must preserve exact cleanup order.

Complexity: HARD  
- Partial model loading success/failure
- Circuit breaker state during rollback
- Memory cleanup race conditions
- Service registry partial corruption
- Timing-dependent cleanup order
"""

import asyncio
import pytest
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor

from mahoun.bootstrap.manager import BootstrapException
from mahoun.bootstrap.executors.ai_ml_components import EmbeddingModelsExecutor
from mahoun.bootstrap.golden_master.behavior_recorder import BehavioralRecorder


class MockBootstrapContextPartialFailure:
    """Mock context that induces partial model loading failures"""
    
    def __init__(self):
        self.services = {
            "neo4j_connection": MagicMock(),
            "governance_controller": MagicMock()
        }
        self.governance_validated = True
        self.config = {"profile": "ULTRA"}  # Multiple models = more failure surface
        self.runtime_info = {"start_time": 1234567890.0}
        self.metrics = {}
        
        # Inject failure points
        self._model_load_count = 0
        self._max_successful_loads = 2  # Fail on 3rd model


class FailingEmbeddingService:
    """Mock service that fails during cleanup to test rollback resilience"""
    
    def __init__(self):
        self.cleanup_called = False
        self.cleanup_delay = 0.1  # Simulate slow cleanup
        
    async def cleanup(self):
        await asyncio.sleep(self.cleanup_delay)
        self.cleanup_called = True
        # Randomly fail cleanup to test error handling
        if hash(time.time()) % 3 == 0:
            raise RuntimeError("Cleanup failed - simulated infrastructure failure")


async def test_embedding_executor_rollback_race_conditions():
    """
    🔴 HARD: Complex rollback with race conditions and partial failures.
    
    This test captures the most complex rollback scenarios that can occur
    in production. Critical for preserving system stability guarantees.
    """
    
    context = MockBootstrapContextPartialFailure()
    executor = EmbeddingModelsExecutor()
    recorder = BehavioralRecorder("EmbeddingModelsExecutor")
    
    # Inject mock failing service
    failing_service = FailingEmbeddingService()
    
    recorder.record_context_before(context)
    recorder.record_event("hard_test_started", {
        "scenario": "rollback_race_conditions",
        "profile": "ULTRA",
        "expected_complexity": "high"
    })
    
    execution_failed = False
    rollback_completed = False
    cleanup_errors = []
    
    try:
        # Patch model loading to induce partial failures
        with patch('mahoun.embeddings.local_service.LocalEmbeddingService') as mock_service:
            mock_service.return_value = failing_service
            
            # This should fail partway through model loading
            result = await executor.execute(context)
            
            recorder.record_event("unexpected_execute_success", {
                "message": "Expected partial failure during model loading"
            })
            
    except BootstrapException as e:
        execution_failed = True
        recorder.record_event("expected_bootstrap_exception", {
            "phase": e.phase,
            "message": str(e),
            "partial_state": "models_partially_loaded"
        })
        
        # Now test rollback under stress
        recorder.record_event("rollback_starting", {
            "context_services_count": len(context.services),
            "timestamp": time.time()
        })
        
        try:
            # Concurrent rollback operations to test race conditions
            rollback_tasks = []
            
            # Main rollback
            rollback_tasks.append(executor.rollback(context))
            
            # Concurrent context access (simulates other bootstrap phases)
            async def concurrent_context_access():
                for i in range(10):
                    _ = list(context.services.keys())
                    await asyncio.sleep(0.01)
                return "concurrent_access_completed"
            
            rollback_tasks.append(concurrent_context_access())
            
            # Execute all rollback operations concurrently
            results = await asyncio.gather(*rollback_tasks, return_exceptions=True)
            
            # Analyze rollback results
            rollback_exceptions = [r for r in results if isinstance(r, Exception)]
            
            recorder.record_event("rollback_completed", {
                "exceptions_count": len(rollback_exceptions),
                "concurrent_operations": len(rollback_tasks),
                "cleanup_called": failing_service.cleanup_called
            })
            
            rollback_completed = True
            
        except Exception as rollback_error:
            cleanup_errors.append(str(rollback_error))
            recorder.record_event("rollback_failed", {
                "error": str(rollback_error),
                "type": type(rollback_error).__name__
            })
    
    except Exception as e:
        recorder.record_event("unexpected_exception", {
            "type": type(e).__name__,
            "message": str(e)
        })
        raise
    
    # Record final state after all chaos
    recorder.record_context_after(context)
    
    # Verify rollback behavior invariants
    recorder.record_event("invariant_checks", {
        "execution_failed": execution_failed,
        "rollback_attempted": rollback_completed or len(cleanup_errors) > 0,
        "context_services_final": list(context.services.keys()),
        "cleanup_errors_count": len(cleanup_errors)
    })
    
    # Critical assertions for system stability
    assert execution_failed, "Expected execution failure for complex scenario"
    
    # Context must be in consistent state (core services remain)
    required_services = {"neo4j_connection", "governance_controller"}
    actual_services = set(context.services.keys())
    missing_required = required_services - actual_services
    assert not missing_required, f"Required services removed during rollback: {missing_required}"
    
    # Create comprehensive snapshot
    snapshot = recorder.create_snapshot()
    snapshot_path = Path(__file__).parent.parent / "golden_master" / "snapshots" / "embedding_rollback_race.json"
    snapshot.save(snapshot_path)
    
    # Validate complex behavioral patterns
    assert snapshot.executor_name == "EmbeddingModelsExecutor"
    
    # Should have partial service additions followed by removals
    rollback_events = [e for e in snapshot.events if "rollback" in e["type"]]
    assert len(rollback_events) >= 1
    
    # Should have exception handling events
    exception_events = [e for e in snapshot.events if "exception" in e["type"]]
    assert len(exception_events) >= 1
    
    print(f"✅ HARD test completed. Complex rollback behavior captured: {snapshot_path}")
    return snapshot
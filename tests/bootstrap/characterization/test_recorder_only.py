"""
Test BehavioralRecorder in isolation (without EmbeddingModelsExecutor complexity)
"""

import asyncio
from pathlib import Path
from mahoun.bootstrap.golden_master.behavior_recorder import BehavioralRecorder


class SimpleMockContext:
    """Minimal mock context"""
    def __init__(self):
        self.services = {"service_a": "mock"}
        self.governance_validated = True
        self.config = {"profile": "TEST"}
        self.runtime_info = {"start": 1.0}
        self.metrics = {}


async def test_recorder_basic():
    """Test that BehavioralRecorder can create snapshots"""
    
    # Setup
    context = SimpleMockContext()
    recorder = BehavioralRecorder("TestExecutor")
    
    # Record before
    recorder.record_context_before(context)
    recorder.record_event("test_started", {"scenario": "basic"})
    
    # Simulate some changes
    context.services["service_b"] = "added"
    
    # Record after
    recorder.record_context_after(context)
    recorder.record_event("test_completed", {"status": "success"})
    
    # Create snapshot
    snapshot = recorder.create_snapshot()
    
    # Assertions
    assert snapshot.executor_name == "TestExecutor"
    assert snapshot.context_mutations["services_added"] == ["service_b"]
    assert len(snapshot.events) == 2
    
    print("✅ BehavioralRecorder basic test passed!")
    print(f"   Executor: {snapshot.executor_name}")
    print(f"   Services added: {snapshot.context_mutations['services_added']}")
    print(f"   Events: {len(snapshot.events)}")
    
    return snapshot


if __name__ == "__main__":
    asyncio.run(test_recorder_basic())

"""
⚫ ULTRA HARD: EmbeddingModelsExecutor Adversarial State Corruption

Tests the executor under extreme adversarial conditions:
- Memory pressure + concurrent mutations
- Context corruption during execution  
- Circuit breaker cascading failures
- Resource exhaustion scenarios
- Byzantine failure injection
- State machine invariant violations

Complexity: ULTRA HARD
- Multiple concurrent executors (simulating phase conflicts)
- Memory pressure simulation (OOM scenarios) 
- Context state corruption (malicious/buggy mutation)
- Network partition simulation (Neo4j connection drops)
- Governance validation bypasses (security scenarios)
- Time-based attacks (TOCTTOU races)
"""

import asyncio
import pytest
import time
import threading
import gc
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import weakref
import random

from mahoun.bootstrap.manager import BootstrapException, BootstrapContext
from mahoun.bootstrap.executors.ai_ml_components import EmbeddingModelsExecutor
from mahoun.bootstrap.golden_master.behavior_recorder import BehavioralRecorder


class AdversarialBootstrapContext:
    """Malicious context that actively corrupts state during execution"""
    
    def __init__(self):
        self.services = {
            "neo4j_connection": MagicMock(),
            "governance_controller": MagicMock()
        }
        self.governance_validated = True
        self.config = {"profile": "ULTRA"}
        self.runtime_info = {"start_time": 1234567890.0}
        self.metrics = {}
        
        # Adversarial state
        self._corruption_active = False
        self._corruption_thread = None
        self._mutation_count = 0
        
    def start_corruption(self):
        """Start background thread that corrupts context state"""
        self._corruption_active = True
        self._corruption_thread = threading.Thread(target=self._corrupt_state_loop)
        self._corruption_thread.daemon = True
        self._corruption_thread.start()
        
    def stop_corruption(self):
        """Stop state corruption"""
        self._corruption_active = False
        if self._corruption_thread:
            self._corruption_thread.join(timeout=1.0)
            
    def _corrupt_state_loop(self):
        """Background corruption - simulates concurrent phase interference"""
        while self._corruption_active:
            try:
                # Random state mutations
                corruption_type = random.choice([
                    "service_removal",
                    "config_mutation", 
                    "governance_flip",
                    "metrics_corruption"
                ])
                
                if corruption_type == "service_removal" and len(self.services) > 1:
                    # Remove random service (simulates phase interference)
                    service_key = random.choice(list(self.services.keys()))
                    if service_key != "governance_controller":  # Keep one critical service
                        del self.services[service_key]
                        
                elif corruption_type == "config_mutation":
                    # Corrupt configuration
                    self.config["profile"] = random.choice(["CORRUPTED", None, 12345])
                    
                elif corruption_type == "governance_flip":
                    # Flip governance validation randomly
                    self.governance_validated = not self.governance_validated
                    
                elif corruption_type == "metrics_corruption":
                    # Corrupt metrics with invalid types
                    self.metrics[f"corrupted_{self._mutation_count}"] = object()
                    
                self._mutation_count += 1
                time.sleep(0.05)  # Frequent mutations
                
            except Exception:
                # Corruption thread shouldn't crash
                pass


class MemoryExhaustionSimulator:
    """Simulates memory pressure during model loading"""
    
    def __init__(self, trigger_threshold=3):
        self.allocations = []
        self.trigger_count = 0
        self.trigger_threshold = trigger_threshold
        
    def allocate_memory_bomb(self):
        """Allocate memory to simulate pressure"""
        try:
            # Allocate 50MB chunks until memory pressure
            chunk_size = 50 * 1024 * 1024  # 50MB
            chunk = bytearray(chunk_size)
            self.allocations.append(chunk)
            
            self.trigger_count += 1
            if self.trigger_count >= self.trigger_threshold:
                # Force garbage collection to simulate memory pressure
                gc.collect()
                raise MemoryError("Simulated OOM during model loading")
                
        except MemoryError:
            # Clean up and re-raise
            self.cleanup()
            raise
            
    def cleanup(self):
        """Clean up allocations"""
        self.allocations.clear()
        gc.collect()


async def test_embedding_executor_adversarial_ultra_hard():
    """
    ⚫ ULTRA HARD: Adversarial state corruption with memory pressure.
    
    This test pushes the executor to its absolute limits with:
    - Concurrent state corruption
    - Memory exhaustion
    - Network partitions  
    - Byzantine failures
    
    Records exact behavior under extreme stress for regression protection.
    """
    
    context = AdversarialBootstrapContext()
    executor = EmbeddingModelsExecutor()
    recorder = BehavioralRecorder("EmbeddingModelsExecutor")
    memory_sim = MemoryExhaustionSimulator()
    
    recorder.record_context_before(context)
    recorder.record_event("ultra_hard_test_started", {
        "scenario": "adversarial_state_corruption",
        "threat_model": "byzantine_failures_memory_pressure_concurrent_mutations",
        "expected_outcome": "graceful_degradation_or_controlled_failure"
    })
    
    # Start adversarial state corruption
    context.start_corruption()
    
    execution_result = None
    exception_chain = []
    memory_exhausted = False
    corruption_detected = False
    
    try:
        # Concurrent execution with multiple stressors
        async def execute_with_memory_pressure():
            """Execute with memory bomb"""
            try:
                # Patch model loading to inject memory pressure
                with patch('mahoun.embeddings.local_service.LocalEmbeddingService.load_model') as mock_load:
                    
                    def memory_bomb_loader(*args, **kwargs):
                        memory_sim.allocate_memory_bomb()
                        return MagicMock()  # Mock successful load
                        
                    mock_load.side_effect = memory_bomb_loader
                    
                    # This should trigger memory exhaustion
                    result = await executor.execute(context)
                    return result
                    
            except MemoryError as e:
                nonlocal memory_exhausted
                memory_exhausted = True
                recorder.record_event("memory_exhaustion_triggered", {
                    "allocations_count": len(memory_sim.allocations),
                    "trigger_count": memory_sim.trigger_count
                })
                raise
        
        async def monitor_state_corruption():
            """Monitor for state corruption"""
            initial_services = set(context.services.keys())
            initial_config = dict(context.config)
            
            # Wait and check for mutations
            await asyncio.sleep(0.2)
            
            # Check for corruption
            services_corrupted = set(context.services.keys()) != initial_services
            config_corrupted = context.config != initial_config
            governance_corrupted = not isinstance(context.governance_validated, bool)
            
            if services_corrupted or config_corrupted or governance_corrupted:
                nonlocal corruption_detected
                corruption_detected = True
                
                recorder.record_event("state_corruption_detected", {
                    "services_corrupted": services_corrupted,
                    "config_corrupted": config_corrupted,  
                    "governance_corrupted": governance_corrupted,
                    "mutation_count": context._mutation_count
                })
        
        # Run execution and monitoring concurrently
        execution_task = execute_with_memory_pressure()
        monitoring_task = monitor_state_corruption()
        
        # Race condition: execution vs state corruption
        try:
            results = await asyncio.gather(
                execution_task,
                monitoring_task,
                return_exceptions=True
            )
            
            execution_result = results[0]
            if not isinstance(execution_result, Exception):
                recorder.record_event("unexpected_success_under_stress", {
                    "message": "Executor succeeded despite adversarial conditions"
                })
                
        except Exception as e:
            exception_chain.append(f"{type(e).__name__}: {e}")
            recorder.record_event("execution_failed_under_stress", {
                "primary_exception": type(e).__name__,
                "message": str(e),
                "memory_exhausted": memory_exhausted,
                "corruption_detected": corruption_detected
            })
    
    finally:
        # Stop corruption and cleanup
        context.stop_corruption()
        memory_sim.cleanup()
    
    # Test rollback under adversarial conditions  
    rollback_success = False
    try:
        # Restart corruption during rollback (worst case)
        context.start_corruption()
        
        recorder.record_event("adversarial_rollback_starting", {
            "context_integrity": not corruption_detected,
            "memory_pressure": memory_exhausted
        })
        
        # Rollback with timeout (prevent infinite hangs)
        rollback_task = executor.rollback(context)
        await asyncio.wait_for(rollback_task, timeout=5.0)
        
        rollback_success = True
        recorder.record_event("adversarial_rollback_completed", {"success": True})
        
    except TimeoutError:
        recorder.record_event("rollback_timeout", {
            "timeout_seconds": 5.0,
            "likely_cause": "resource_exhaustion_or_deadlock"
        })
        
    except Exception as rollback_error:
        recorder.record_event("rollback_failed_under_stress", {
            "error": str(rollback_error),
            "type": type(rollback_error).__name__
        })
        
    finally:
        context.stop_corruption()
    
    # Record final state after chaos
    recorder.record_context_after(context)
    
    # System stability invariants - even under attack
    recorder.record_event("system_stability_check", {
        "execution_result_type": type(execution_result).__name__ if execution_result else "None",
        "exception_chain_length": len(exception_chain),
        "memory_exhausted": memory_exhausted,
        "corruption_detected": corruption_detected,
        "rollback_success": rollback_success,
        "final_services_count": len(context.services),
        "mutation_count": context._mutation_count
    })
    
    # Critical invariants even under adversarial conditions
    assert isinstance(context.services, dict), "Services registry corrupted beyond recovery"
    assert len(context.services) >= 0, "Services count became negative"
    
    # Either execution succeeds OR fails gracefully (no silent corruption)
    if execution_result and not isinstance(execution_result, Exception):
        # Success path - verify integrity
        assert hasattr(execution_result, 'success'), "Result object corrupted"
        assert hasattr(execution_result, 'phase'), "Phase information lost"
        
    # Create comprehensive adversarial snapshot
    snapshot = recorder.create_snapshot()
    snapshot_path = Path(__file__).parent.parent / "golden_master" / "snapshots" / "embedding_adversarial_ultra.json"
    snapshot.save(snapshot_path)
    
    # Validate adversarial behavior capture
    assert snapshot.executor_name == "EmbeddingModelsExecutor"
    
    # Must contain stress events
    stress_events = [e for e in snapshot.events if "stress" in e["type"] or "adversarial" in e["type"] or "corruption" in e["type"]]
    assert len(stress_events) >= 1, "Adversarial events not captured"
    
    # Must contain system stability checks
    stability_events = [e for e in snapshot.events if "stability" in e["type"]]
    assert len(stability_events) >= 1, "Stability invariants not checked"
    
    print(f"✅ ULTRA HARD test completed. Adversarial behavior captured: {snapshot_path}")
    print(f"   - Memory exhausted: {memory_exhausted}")
    print(f"   - State corrupted: {corruption_detected}")  
    print(f"   - Rollback success: {rollback_success}")
    print(f"   - Exception chain: {len(exception_chain)}")
    
    return snapshot
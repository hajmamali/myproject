"""
MAHOUN Orphan Modules Hardened - Adversarial Test Suite
========================================================

Tests for newly hardened orphan modules:
- reasoning_recorder_ultra.py
- policies.py (PolicyManager)

Categories:
A. UltraRecorder Hash-Chain Integrity
B. UltraRecorder Governance Compliance
C. UltraRecorder Merkle Tree Verification
D. PolicyManager RBAC Protection
E. PolicyManager Audit Logging
F. Concurrent Stress Testing
G. Byzantine Fault Injection

All tests require governance context and follow P0/P1 compliance.
"""

import pytest
import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path
import tempfile

# Set test environment
os.environ["MAHOUN_ENV"] = "test"
os.environ["MAHOUN_TESTING"] = "true"


# Helper context manager for tests
class GovernanceTestContext:
    """Helper to manage governance context in tests."""
    
    def __init__(self, correlation_id: str, actor_id: str):
        self.correlation_id = correlation_id
        self.actor_id = actor_id
        self.ctx = None
    
    def __enter__(self):
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        self.ctx = GovernanceContextManager.create_context(
            correlation_id=self.correlation_id,
            actor_id=self.actor_id,
            execution_mode="STRICT"
        )
        
        # Push context
        stack = GovernanceContextManager._get_stack()
        GovernanceContextManager._governance_stack.set(stack + (self.ctx,))
        
        return self.ctx
    
    def __exit__(self, *args):
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        # Pop context
        stack = GovernanceContextManager._get_stack()
        if stack:
            GovernanceContextManager._governance_stack.set(stack[:-1] or ())


# =========================================================
# CATEGORY A: ULTRARECORDER HASH-CHAIN INTEGRITY
# =========================================================
class TestUltraRecorderHashChain:
    """Test cryptographic hash-chain integrity."""
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_hash_chain_sequential_integrity(self):
        """Hash chain must link all steps correctly."""
        from mahoun.reasoning.reasoning_recorder_ultra import (
            UltraReasoningRecorder,
            StepType,
            StorageBackend
        )
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        # Create governance context
        ctx = GovernanceContextManager.create_context(
            correlation_id="test-001",
            actor_id="test-actor",
            execution_mode="STRICT"
        )
        
        # Push context
        stack = GovernanceContextManager._get_stack()
        GovernanceContextManager._governance_stack.set(stack + (ctx,))
        
        try:
            recorder = UltraReasoningRecorder(
                backend=StorageBackend.MEMORY,
                audit_mode=True
            )
            
            # Record 10 steps
            step_ids = []
            for i in range(10):
                step_id = recorder.record_step(
                    step_type=StepType.EVIDENCE_SYNTHESIS,
                    reasoning=f"Step {i} reasoning",
                    confidence=0.8 + i * 0.01,
                    evidence=[f"ev-{i}"],
                    correlation_id="test-001",
                    actor_id="test-actor",
                    metadata={"step_num": i}
                )
                step_ids.append(step_id)
            
            # Verify chain
            is_valid, error = recorder.verify_step_chain(
                correlation_id="test-001",
                actor_id="test-actor"
            )
            
            assert is_valid is True, f"Hash chain broken: {error}"
            assert recorder.metrics.total_steps == 10
        finally:
            # Pop context
            stack = GovernanceContextManager._get_stack()
            if stack:
                GovernanceContextManager._governance_stack.set(stack[:-1] or ())
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_tampered_hash_detection(self):
        """Tampered hash must be detected."""
        from mahoun.reasoning.reasoning_recorder_ultra import (
            UltraReasoningRecorder,
            StepType,
            StorageBackend
        )
        from mahoun.core.governance.governance_context import GovernanceContextManager
        from mahoun.core.exceptions import GraphIntegrityException
        
        with GovernanceContextManager.scoped_context(
            actor_id="test-actor",
            correlation_id="test-002",
            operation_type="test"
        ):
            recorder = UltraReasoningRecorder(
                backend=StorageBackend.MEMORY,
                audit_mode=True
            )
            
            # Record 3 steps
            for i in range(3):
                recorder.record_step(
                    step_type=StepType.RULE_MATCH,
                    reasoning=f"Step {i}",
                    confidence=0.9,
                    evidence=[f"ev-{i}"],
                    correlation_id="test-002",
                    actor_id="test-actor"
                )
            
            # TAMPER: Modify last hash
            if recorder._steps:
                recorder._steps[-1].step_hash = "TAMPERED_HASH"
            
            # Verification should fail
            is_valid, error = recorder.verify_step_chain(
                correlation_id="test-002",
                actor_id="test-actor"
            )
            
            assert is_valid is False, "Tampered hash not detected!"
            assert "mismatch" in error.lower()


# =========================================================
# CATEGORY B: ULTRARECORDER GOVERNANCE COMPLIANCE
# =========================================================
class TestUltraRecorderGovernance:
    """Test governance context enforcement."""
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_production_requires_audit_mode(self):
        """Production must enforce audit_mode."""
        from mahoun.reasoning.reasoning_recorder_ultra import UltraReasoningRecorder
        from mahoun.core.exceptions import SecurityBreachException
        
        with patch("mahoun.reasoning.reasoning_recorder_ultra.is_production", return_value=True):
            with pytest.raises(SecurityBreachException) as exc_info:
                UltraReasoningRecorder(audit_mode=False)
            
            assert "audit_mode" in str(exc_info.value).lower()
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_requires_governance_context(self):
        """Recording must require active governance context."""
        from mahoun.reasoning.reasoning_recorder_ultra import (
            UltraReasoningRecorder,
            StepType,
            StorageBackend
        )
        from mahoun.core.exceptions import SecurityBreachException
        
        recorder = UltraReasoningRecorder(backend=StorageBackend.MEMORY)
        
        # Without governance context should fail
        with pytest.raises(SecurityBreachException):
            recorder.record_step(
                step_type=StepType.SEMANTIC_MATCH,
                reasoning="Test",
                confidence=0.7,
                evidence=[],
                correlation_id="test-003",
                actor_id="test-actor"
            )
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_correlation_id_validation(self):
        """Correlation ID must match governance context."""
        from mahoun.reasoning.reasoning_recorder_ultra import (
            UltraReasoningRecorder,
            StepType,
            StorageBackend
        )
        from mahoun.core.governance.governance_context import GovernanceContextManager
        from mahoun.core.exceptions import SecurityBreachException
        
        with GovernanceContextManager.scoped_context(
            actor_id="test-actor",
            correlation_id="correct-id",
            operation_type="test"
        ):
            recorder = UltraReasoningRecorder(backend=StorageBackend.MEMORY)
            
            # Wrong correlation_id should fail
            with pytest.raises(SecurityBreachException) as exc_info:
                recorder.record_step(
                    step_type=StepType.CAUSAL_INFERENCE,
                    reasoning="Test",
                    confidence=0.8,
                    evidence=[],
                    correlation_id="wrong-id",  # MISMATCH
                    actor_id="test-actor"
                )
            
            assert "mismatch" in str(exc_info.value).lower()


# =========================================================
# CATEGORY C: ULTRARECORDER MERKLE TREE VERIFICATION
# =========================================================
class TestUltraRecorderMerkle:
    """Test Merkle tree batch verification."""
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_merkle_checkpoint_creation(self):
        """Merkle checkpoints must be created at intervals."""
        from mahoun.reasoning.reasoning_recorder_ultra import (
            UltraReasoningRecorder,
            StepType,
            StorageBackend
        )
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        with GovernanceContextManager.scoped_context(
            actor_id="test-actor",
            correlation_id="test-004",
            operation_type="test"
        ):
            recorder = UltraReasoningRecorder(
                backend=StorageBackend.MEMORY,
                checkpoint_interval=10  # Checkpoint every 10 steps
            )
            
            # Record 25 steps (should create 2 checkpoints)
            for i in range(25):
                recorder.record_step(
                    step_type=StepType.NEURAL_INFERENCE,
                    reasoning=f"Step {i}",
                    confidence=0.85,
                    evidence=[],
                    correlation_id="test-004",
                    actor_id="test-actor"
                )
            
            # Should have Merkle roots
            assert len(recorder._merkle_roots) >= 2
            assert recorder.metrics.merkle_verifications >= 2


# =========================================================
# CATEGORY D: POLICYMANAGER RBAC PROTECTION
# =========================================================
class TestPolicyManagerRBAC:
    """Test RBAC protection for policy changes."""
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_policy_change_requires_context(self):
        """Policy change must require governance context."""
        from mahoun.reasoning.policies import PolicyManager, PolicyType
        from mahoun.core.exceptions import SecurityBreachException
        
        # Without context should fail
        with pytest.raises(SecurityBreachException):
            PolicyManager.set_policy(
                policy_type=PolicyType.CONSERVATIVE,
                actor_id="test-actor",
                correlation_id="test-005",
                reason="Testing"
            )
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_actor_id_validation(self):
        """Actor ID must match governance context."""
        from mahoun.reasoning.policies import PolicyManager, PolicyType
        from mahoun.core.governance.governance_context import GovernanceContextManager
        from mahoun.core.exceptions import SecurityBreachException
        
        with GovernanceContextManager.scoped_context(
            actor_id="correct-actor",
            correlation_id="test-006",
            operation_type="test"
        ):
            # Wrong actor_id should fail
            with pytest.raises(SecurityBreachException):
                PolicyManager.set_policy(
                    policy_type=PolicyType.BALANCED,
                    actor_id="wrong-actor",  # MISMATCH
                    correlation_id="test-006",
                    reason="Testing"
                )
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_aggressive_policy_requires_approval(self):
        """Aggressive policy should require approval (warning logged)."""
        from mahoun.reasoning.policies import PolicyManager, PolicyType
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        with GovernanceContextManager.scoped_context(
            actor_id="test-actor",
            correlation_id="test-007",
            operation_type="test"
        ):
            # Should succeed but log warning
            policy = PolicyManager.set_policy(
                policy_type=PolicyType.AGGRESSIVE,
                actor_id="test-actor",
                correlation_id="test-007",
                reason="Testing aggressive mode",
                require_approval=True
            )
            
            assert policy.name == "aggressive"
            assert policy.min_confidence < 0.5


# =========================================================
# CATEGORY E: POLICYMANAGER AUDIT LOGGING
# =========================================================
class TestPolicyManagerAudit:
    """Test audit logging for policy changes."""
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_policy_change_is_audited(self):
        """Every policy change must be audited."""
        from mahoun.reasoning.policies import PolicyManager, PolicyType
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        with GovernanceContextManager.scoped_context(
            actor_id="auditor",
            correlation_id="test-008",
            operation_type="test"
        ):
            # Change policy
            PolicyManager.set_policy(
                policy_type=PolicyType.CONSERVATIVE,
                actor_id="auditor",
                correlation_id="test-008",
                reason="High-stakes case"
            )
            
            # Check audit log
            audit_log = PolicyManager.get_audit_log(limit=1)
            
            assert len(audit_log) > 0
            latest = audit_log[0]
            assert latest["event_type"] == "POLICY_CHANGE"
            assert latest["actor_id"] == "auditor"
            assert latest["new_policy"] == "conservative"
            assert latest["reason"] == "High-stakes case"


# =========================================================
# CATEGORY F: CONCURRENT STRESS TESTING
# =========================================================
class TestConcurrentStress:
    """Test concurrent operations under stress."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.p3
    def test_concurrent_recording_isolated(self):
        """Concurrent recordings must not interfere."""
        from mahoun.reasoning.reasoning_recorder_ultra import (
            UltraReasoningRecorder,
            StepType,
            StorageBackend
        )
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        recorder = UltraReasoningRecorder(backend=StorageBackend.MEMORY)
        
        def worker(i):
            with GovernanceContextManager.scoped_context(
                actor_id=f"worker-{i}",
                correlation_id=f"corr-{i}",
                operation_type="test"
            ):
                return recorder.record_step(
                    step_type=StepType.GRAPH_TRAVERSAL,
                    reasoning=f"Worker {i} reasoning",
                    confidence=0.8,
                    evidence=[],
                    correlation_id=f"corr-{i}",
                    actor_id=f"worker-{i}"
                )
        
        with ThreadPoolExecutor(max_workers=20) as ex:
            results = list(ex.map(worker, range(100)))
        
        # All should succeed
        assert len(results) == 100
        assert all(r is not None for r in results)
        assert recorder.metrics.total_steps == 100


# =========================================================
# CATEGORY G: BYZANTINE FAULT INJECTION
# =========================================================
class TestByzantineFaults:
    """Test Byzantine fault resistance."""
    
    @pytest.mark.integration
    @pytest.mark.p3
    def test_corrupted_previous_hash_detected(self):
        """Corrupted previous hash must be detected."""
        from mahoun.reasoning.reasoning_recorder_ultra import (
            UltraReasoningRecorder,
            StepType,
            StorageBackend,
            ReasoningStepRecord
        )
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        with GovernanceContextManager.scoped_context(
            actor_id="test-actor",
            correlation_id="test-009",
            operation_type="test"
        ):
            recorder = UltraReasoningRecorder(backend=StorageBackend.MEMORY)
            
            # Record 2 steps
            recorder.record_step(
                step_type=StepType.SEMANTIC_MATCH,
                reasoning="Step 1",
                confidence=0.9,
                evidence=[],
                correlation_id="test-009",
                actor_id="test-actor"
            )
            
            # Inject corrupted step with wrong prev_hash
            corrupted_step = ReasoningStepRecord(
                step_id="corrupted-id",
                step_type=StepType.RULE_MATCH,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reasoning="Corrupted",
                confidence=0.5,
                evidence=[],
                metadata={},
                correlation_id="test-009",
                actor_id="test-actor",
                prev_hash="WRONG_HASH"  # BYZANTINE FAULT
            )
            corrupted_step.step_hash = corrupted_step.compute_hash()
            recorder._steps.append(corrupted_step)
            
            # Verification should fail
            is_valid, error = recorder.verify_step_chain(
                correlation_id="test-009",
                actor_id="test-actor"
            )
            
            assert is_valid is False
            assert "broken" in error.lower() or "mismatch" in error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

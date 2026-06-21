"""
P1-2 ReasoningRecorder INTEGRATION Tests (NO MOCKS)
====================================================
Real integration tests without mocks to catch real bugs.
"""

import pytest
import logging
import os

from mahoun.reasoning.reasoning_recorder import ReasoningRecorder, ReasoningStep
from mahoun.core.governance.governance_context import GovernanceContextManager


def test_real_dev_mode_behavior(caplog):
    """
    INTEGRATION: Test REAL development mode behavior WITHOUT mocks.
    
    This catches real bugs that mocked tests might miss.
    """
    # Set real environment (will be reset after test)
    original_env = os.environ.get('MAHOUN_ENV')
    try:
        os.environ['MAHOUN_ENV'] = 'development'
        
        recorder = ReasoningRecorder()
        
        with caplog.at_level(logging.INFO):
            # Record step WITHOUT any GovernanceContext
            step = recorder.record_step(
                step_type="test",
                inputs={"test": "input"},
                outputs={"test": "output"},
            )
        
        # Verify P1-2 audit log exists
        audit_logs = [r for r in caplog.records if "P1-2 DEVELOPMENT AUDIT" in r.message]
        assert len(audit_logs) > 0, "P1-2 audit log not found in REAL development mode"
        
        # Verify provenance is synthetic
        assert step.provenance.governance_scope_id == "development_synthetic_scope"
        
    finally:
        # Restore original environment
        if original_env:
            os.environ['MAHOUN_ENV'] = original_env
        else:
            os.environ.pop('MAHOUN_ENV', None)


def test_real_governance_context_integration():
    """
    INTEGRATION: Test WITH real GovernanceContext.
    
    This verifies the REAL integration between ReasoningRecorder and GovernanceContext.
    """
    original_env = os.environ.get('MAHOUN_ENV')
    try:
        os.environ['MAHOUN_ENV'] = 'development'
        
        # Create REAL GovernanceContext
        with GovernanceContextManager.active_context(
            operation="test_reasoning_recording",
            actor_id="test_actor",
            correlation_id="test_correlation",
        ) as ctx:
            recorder = ReasoningRecorder()
            
            # Record step WITH real context
            step = recorder.record_step(
                step_type="test",
                inputs={"test": "input"},
                outputs={"test": "output"},
            )
            
            # Verify provenance comes from REAL context (not synthetic)
            assert step.provenance.governance_scope_id == ctx.context_id
            assert step.provenance.correlation_id == "test_correlation"
            assert "synthetic" not in step.provenance.governance_scope_id
            
    finally:
        if original_env:
            os.environ['MAHOUN_ENV'] = original_env
        else:
            os.environ.pop('MAHOUN_ENV', None)


def test_real_chain_verification_no_mocks():
    """
    INTEGRATION: Test chain verification with REAL implementation.
    """
    original_env = os.environ.get('MAHOUN_ENV')
    try:
        os.environ['MAHOUN_ENV'] = 'development'
        
        recorder = ReasoningRecorder()
        
        # Record multiple steps
        for i in range(5):
            recorder.record_step(
                step_type=f"step_{i}",
                inputs={"i": i},
                outputs={"result": i * 2},
            )
        
        # Verify clean chain
        assert recorder.verify_chain() is True
        
        # Verify hash linkage
        steps = recorder.get_steps()
        assert len(steps) == 5
        
        # Verify REAL hash chain integrity
        for i in range(1, len(steps)):
            assert steps[i].chain_prev_hash == steps[i-1].chain_hash
            # Verify sequence numbers
            assert steps[i].sequence_number == i
        
        # Test tampering detection with REAL verify_chain logic
        tampered_step = ReasoningStep(
            step_id=steps[2].step_id,
            step_type=steps[2].step_type,
            inputs=steps[2].inputs,
            outputs=steps[2].outputs,
            provenance=steps[2].provenance,
            chain_hash="TAMPERED_HASH",  # Invalid hash
            chain_prev_hash=steps[2].chain_prev_hash,
            timestamp=steps[2].timestamp,
            sequence_number=steps[2].sequence_number,
        )
        recorder._steps[2] = tampered_step
        
        # Verify REAL chain verification catches tampering
        assert recorder.verify_chain() is False
        
    finally:
        if original_env:
            os.environ['MAHOUN_ENV'] = original_env
        else:
            os.environ.pop('MAHOUN_ENV', None)


@pytest.mark.skipif(
    os.getenv('MAHOUN_ENV') == 'production',
    reason="Cannot test production blocking in actual production environment"
)
def test_production_mode_requires_context():
    """
    INTEGRATION: Verify production mode REALLY requires GovernanceContext.
    
    Note: Skipped in real production to avoid disruption.
    """
    original_env = os.environ.get('MAHOUN_ENV')
    try:
        os.environ['MAHOUN_ENV'] = 'production'
        
        recorder = ReasoningRecorder()
        
        # This should REALLY fail in production without context
        with pytest.raises(RuntimeError, match="P0-1 GOVERNANCE VIOLATION"):
            recorder.record_step(
                step_type="test",
                inputs={},
                outputs={},
            )
        
    finally:
        if original_env:
            os.environ['MAHOUN_ENV'] = original_env
        else:
            os.environ.pop('MAHOUN_ENV', None)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

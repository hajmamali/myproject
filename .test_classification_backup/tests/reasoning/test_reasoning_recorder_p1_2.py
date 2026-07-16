"""
P1-2 ReasoningRecorder Development Audit Test
==============================================
Simple focused test for P1-2 compliance.
"""

import pytest
import logging
from unittest.mock import patch, Mock, MagicMock

from mahoun.reasoning.reasoning_recorder import ReasoningRecorder, ReasoningStep


@pytest.mark.p1
def test_p1_2_dev_mode_logs_synthetic_provenance(caplog):
    """P1-2: Development mode explicitly logs synthetic provenance."""
    
    # Mock environment as development
    with patch('mahoun.core.environment.get_current_environment') as mock_env:
        mock_env_obj = Mock()
        mock_env_obj.is_production.return_value = False
        mock_env_obj.is_staging.return_value = False
        mock_env_obj.environment.value = "development"
        mock_env.return_value = mock_env_obj
        
        with patch('mahoun.core.governance.governance_context.GovernanceContextManager.get_current_context') as mock_ctx:
            mock_ctx.return_value = None  # No context in dev
            
            recorder = ReasoningRecorder()
            
            with caplog.at_level(logging.INFO):
                step = recorder.record_step(
                    step_type="test",
                    inputs={"test": "input"},
                    outputs={"test": "output"},
                )
            
            # Verify P1-2 audit log exists
            audit_logs = [r for r in caplog.records if "P1-2 DEVELOPMENT AUDIT" in r.message]
            assert len(audit_logs) > 0, "P1-2 audit log not found"
            
            audit_log = audit_logs[0]
            assert "synthetic provenance" in audit_log.message
            assert audit_log.levelname == "INFO"
            
            # Verify provenance is synthetic
            assert step.provenance.governance_scope_id == "development_synthetic_scope"


@pytest.mark.p1
def test_p1_2_production_blocks_synthetic_provenance():
    """P1-2: Production mode blocks synthetic provenance."""
    
    # Mock environment as production
    with patch('mahoun.core.environment.get_current_environment') as mock_env:
        mock_env_obj = Mock()
        mock_env_obj.is_production.return_value = True
        mock_env_obj.is_staging.return_value = False
        mock_env_obj.environment.value = "production"
        mock_env.return_value = mock_env_obj
        
        with patch('mahoun.core.governance.governance_context.GovernanceContextManager.get_current_context') as mock_ctx:
            # No context in production (error condition)
            mock_ctx.return_value = None
            
            recorder = ReasoningRecorder()
            
            with pytest.raises(RuntimeError, match="P0-1 GOVERNANCE VIOLATION"):
                recorder.record_step(
                    step_type="test",
                    inputs={},
                    outputs={},
                )


@pytest.mark.p1
def test_p0_5_chain_verification():
    """P0-5: Chain verification works correctly."""
    
    with patch('mahoun.core.environment.get_current_environment') as mock_env:
        mock_env_obj = Mock()
        mock_env_obj.is_production.return_value = False
        mock_env_obj.is_staging.return_value = False
        mock_env_obj.environment.value = "development"
        mock_env.return_value = mock_env_obj
        
        with patch('mahoun.core.governance.governance_context.GovernanceContextManager.get_current_context') as mock_ctx:
            mock_ctx.return_value = None  # Dev mode
            
            recorder = ReasoningRecorder()
            
            # Record steps
            for i in range(3):
                recorder.record_step(
                    step_type=f"step_{i}",
                    inputs={"i": i},
                    outputs={"result": i * 2},
                )
            
            # Verify chain
            assert recorder.verify_chain()
            
            # Verify hash linkage
            steps = recorder.get_steps()
            assert len(steps) == 3
            
            for i in range(1, len(steps)):
                assert steps[i].chain_prev_hash == steps[i-1].chain_hash
            
            # Test tampering detection
            # Modify a step's hash to simulate tampering
            tampered_step = ReasoningStep(
                step_id=steps[1].step_id,
                step_type=steps[1].step_type,
                inputs=steps[1].inputs,
                outputs=steps[1].outputs,
                provenance=steps[1].provenance,
                chain_hash="TAMPERED_HASH",  # Invalid hash
                chain_prev_hash=steps[1].chain_prev_hash,
                timestamp=steps[1].timestamp,
                sequence_number=steps[1].sequence_number,
            )
            recorder._steps[1] = tampered_step
            
            # Verify chain detects tampering
            assert recorder.verify_chain() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

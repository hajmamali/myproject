"""
Phase 5: TEST 2 - Failed Validation
====================================

RULE 11: Failed executions MUST also be recorded in ledger.

This test verifies:
1. Verdict is generated internally
2. Fortress rejects (agreement_score < threshold)
3. Ledger is committed
4. status = FAILED
5. Validation violations are preserved
6. Execution is auditable

Per CONSTITUTION.md:
- AI agents MUST provide evidence for decisions
- Evidence MUST be preserved
- Governance MUST NOT be bypassed
- Tests MUST NOT be modified to conceal defects
"""

import pytest
import sys
from pathlib import Path
from datetime import UTC, datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Constitutional compliance: Load governance framework
from mahoun.core.governance import GovernanceContextManager


@pytest.mark.p0
@pytest.mark.asyncio
async def test_failed_validation_ledger_commit():
    """
    Explicitly test a FAILED validation scenario.
    
    This test creates a response with agreement_score < 0.85 to force
    Fortress validation to fail, then verifies:
    1. Ledger is committed
    2. validation_status = FAILED
    3. validation_violations are recorded
    
    Per RULE 11: Failed executions MUST also be recorded
    """
    from mahoun.reasoning.ledger_commit_service import LedgerCommitService
    from mahoun.reasoning.verdict_engine_adapter import VerdictEngineAdapter
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
    from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
    from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
    from mahoun.ledger.writer import EvidenceLedgerWriter, ImmutableLedger
    from mahoun.reasoning.adapters import ReasoningDependencyContainer
    from mahoun.contracts.verdict_execution import VerdictExecutionResult
    from mahoun.core.fortress_validator import FortressValidator, ValidationResult, ViolationType, ViolationSeverity
    from mahoun.reasoning.unified_reasoning_service import ReasoningResponse, ReasoningMode
    
    import tempfile
    import os
    
    async with GovernanceContextManager.active_context(correlation_id="test_failed_val") as gov_ctx:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            graph_builder = UltraGraphBuilder()
            knowledge_graph = LegalKnowledgeGraph()
            storage_path = os.path.join(tmpdir, "test_ledger.json")
            blockchain = ImmutableLedger(storage_path=storage_path)
            ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
            container = ReasoningDependencyContainer()
            
            # Create engine
            engine = EvidenceLinkedVerdictEngine(
                graph_builder=graph_builder,
                knowledge_graph=knowledge_graph,
                ledger_writer=ledger_writer,
                container=container
            )
            
            # Create adapter
            adapter = VerdictEngineAdapter(engine=engine)
            
            # Create ledger commit service
            ledger_commit_service = LedgerCommitService(
                ledger_writer=ledger_writer,
                strict_mode=False
            )
            
            # Get a normal execution result first
            class TestRequest:
                question = "Test question"
                facts = ["Test fact 1", "Test fact 2"]
                case_id = "test_explicit_fail_case"
            
            response = await adapter.reason(TestRequest())
            
            # Extract execution_result
            execution_result = response.execution_result
            assert execution_result is not None, "Need execution_result"
            
            # Create modified execution result with LOW agreement_score
            # This will cause Fortress to FAIL the validation
            modified_execution_result = VerdictExecutionResult(
                verdict=execution_result.verdict,
                ledger_entry=execution_result.ledger_entry,
                proof=execution_result.proof,
                execution_id=execution_result.execution_id,
                correlation_id=execution_result.correlation_id,
                execution_timestamp=execution_result.execution_timestamp,
                agreement_score=0.5,  # BELOW threshold of 0.85 - will FAIL
                validation_passed=None,
            )
            
            # Create a ReasoningResponse with low agreement_score in metadata
            modified_response = ReasoningResponse(
                success=True,
                result=response.result,
                confidence=response.confidence,
                reasoning_mode=response.reasoning_mode,
                execution_time_ms=response.execution_time_ms,
                proof_tree=response.proof_tree,
                derived_facts=response.derived_facts,
                metadata={**response.metadata, "agreement_score": 0.5},
                fortress_validated=False,
                audit_hash=None,
                validation_timestamp=None,
                correlation_id=response.correlation_id,
                execution_result=modified_execution_result,
            )
            
            # Now manually validate this response through Fortress
            # This should FAIL because agreement_score = 0.5 < 0.85
            validator = fortress_service.validator if hasattr(adapter, 'validator') else FortressValidator()
            
            # Get validator from adapter's fortress service
            # Actually, we need to create a fortress service to get the validator
            from mahoun.reasoning.fortress_integration import FortressProtectedReasoningService
            fortress_service = FortressProtectedReasoningService(
                reasoning_service=adapter,
                strict_mode=False,
                ledger_commit_service=ledger_commit_service
            )
            validator = fortress_service.validator
            
            validation_result = await validator.validate(modified_response)
            
            # VERIFY: Validation must fail
            assert validation_result is not None, "Validation result must exist"
            assert not validation_result.passed, \
                f"Validation should FAIL with agreement_score=0.5, but passed={validation_result.passed}"
            
            # VERIFY: There must be violations
            assert len(validation_result.violations) > 0, \
                "There must be violations when agreement_score < threshold"
            
            # VERIFY: One of the violations should be LOW_AGREEMENT_SCORE
            violation_types = [v.get("type") for v in validation_result.violations]
            assert ViolationType.LOW_AGREEMENT_SCORE.value in violation_types, \
                f"Expected LOW_AGREEMENT_SCORE violation, got: {violation_types}"
            
            print(f"✓ Validation correctly FAILED with {len(validation_result.violations)} violations")
            print(f"  Violation types: {violation_types}")
            
            # Now commit this execution with FAILED validation
            commit_result = await ledger_commit_service.commit_execution(
                execution_result=modified_execution_result,
                validation_passed=validation_result.passed,
                validation_violations=validation_result.violations,
                validation_timestamp=datetime.now(UTC),
                fortress_version="1.0.0"
            )
            
            # VERIFY: Commit must succeed
            assert commit_result.success, \
                f"Ledger commit must succeed even for failed validation: {commit_result.error}"
            
            # VERIFY: The committed entry must have FAILED status
            committed_entry = commit_result.entry
            assert committed_entry is not None, "Committed entry must exist"
            
            assert hasattr(committed_entry, 'validation_status'), \
                "Committed entry must have validation_status field"
            
            # THIS IS THE CRITICAL CHECK FOR RULE 11 AND RULE 6
            assert committed_entry.validation_status == "FAILED", \
                f"Committed entry must have validation_status='FAILED' for failed validation, " \
                f"got '{committed_entry.validation_status}'"
            
            # VERIFY: Validation violations are preserved
            assert committed_entry.validation_violations is not None, \
                "Committed entry must have validation_violations"
            
            assert len(committed_entry.validation_violations) > 0, \
                "Committed entry must have at least one validation violation"
            
            # VERIFY: Validation timestamp is set
            assert committed_entry.validation_timestamp is not None, \
                "Committed entry must have validation_timestamp"
            
            # VERIFY: Fortress version is set
            assert committed_entry.fortress_version is not None, \
                "Committed entry must have fortress_version"
            
            print(f"✓ Ledger entry committed with FAILED status")
            print(f"  validation_status: {committed_entry.validation_status}")
            print(f"  validation_violations: {len(committed_entry.validation_violations)} violations")
            print(f"  fortress_version: {committed_entry.fortress_version}")
            
            # VERIFY: Entry is in immutable ledger
            assert len(blockchain.chain) >= 1, "Entry must be in ledger"
            
            # Find our entry in the blockchain
            found = False
            for block in blockchain.chain:
                if hasattr(block, 'data') and block.data and hasattr(block.data, 'verdict_id') and block.data.verdict_id == committed_entry.verdict_id:
                    found = True
                    assert block.data.validation_status == "FAILED", \
                        f"Block in ledger must have FAILED status"
                    break
            
            assert found, f"Committed entry with verdict_id={committed_entry.verdict_id} not found in ledger"
            
            print("✓ TEST 2: Failed validation properly recorded in immutable ledger (RULE 11)")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))

"""
MAHOUN Ledger Commit Service
===============================

Classification: MISSION-CRITICAL / ARCHITECTURAL SERVICE / DEPENDENCY INJECTION
Purpose: Dedicated service for committing ledger entries AFTER Fortress validation.

This service enforces:
- RULE 1: Ledger is NEVER written before Fortress validation
- RULE 2: Delayed Ledger Commit
- RULE 8: Dependencies point inward (no object graph walking)
- RULE 10: Execution Atomicity
- RULE 11: Failed executions must also be recorded

The LedgerCommitService is explicitly injected into FortressProtectedReasoningService,
not discovered by walking object graphs.

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Any, Optional

from mahoun.core.governance import GovernanceContextManager
from mahoun.ledger.models import LedgerEntry, ValidationStatus
from mahoun.ledger.writer import EvidenceLedgerWriter

if TYPE_CHECKING:
    from mahoun.contracts.verdict_execution import VerdictExecutionResult, PendingLedgerCommit

log = logging.getLogger(__name__)


@dataclass
class LedgerCommitResult:
    """
    Result of a ledger commit operation.
    
    Attributes:
        success: Whether the commit succeeded
        ledger_hash: The hash of the committed entry (if successful)
        entry: The committed LedgerEntry
        error: Error message if commit failed
        timestamp: When the commit was attempted
    """
    success: bool
    ledger_hash: Optional[str]
    entry: Optional[LedgerEntry]
    error: Optional[str]
    timestamp: datetime


class LedgerCommitService:
    """
    Service responsible for committing ledger entries after validation.
    
    This service is the ONLY authorized mechanism for committing ledger entries
    in the execution pipeline. It ensures:
    
    1. All commits happen AFTER Fortress validation (RULE 1)
    2. Failed validations are also recorded (RULE 11)
    3. Commit operations are atomic (RULE 10)
    4. No object graph walking (RULE 8)
    
    Usage:
        # Inject into FortressProtectedReasoningService
        commit_service = LedgerCommitService(ledger_writer=ledger_writer)
        
        protected_service = FortressProtectedReasoningService(
            reasoning_service=adapter,
            ledger_commit_service=commit_service  # Explicit injection
        )
    """
    
    def __init__(
        self,
        ledger_writer: EvidenceLedgerWriter,
        strict_mode: bool = True
    ):
        """
        Initialize LedgerCommitService.
        
        Args:
            ledger_writer: The EvidenceLedgerWriter to use for commits
            strict_mode: If True, raise exceptions on commit failures
        """
        self.ledger_writer = ledger_writer
        self.strict_mode = strict_mode
        self._lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            "total_commits": 0,
            "successful_commits": 0,
            "failed_commits": 0,
        }
        
        log.info("LedgerCommitService initialized with strict_mode={strict_mode}")
    
    async def commit_execution(
        self,
        execution_result: VerdictExecutionResult,
        validation_passed: bool,
        validation_violations: list[dict[str, Any]] | None = None,
        validation_timestamp: datetime | None = None,
        fortress_version: str | None = None
    ) -> LedgerCommitResult:
        """
        Commit a verdict execution to the ledger.
        
        This method is called by FortressProtectedReasoningService AFTER
        validation is complete. It updates the pending ledger entry with
        validation results and commits it to immutable storage.
        
        Per RULE 11, this commits BOTH successful and failed validations.
        
        Args:
            execution_result: The VerdictExecutionResult containing the pending ledger entry
            validation_passed: Whether Fortress validation passed
            validation_violations: List of violations if validation failed
            validation_timestamp: When validation occurred
            fortress_version: Version of Fortress validator used
            
        Returns:
            LedgerCommitResult with commit status
            
        Raises:
            RuntimeError: In strict_mode, if commit fails
        """
        self.stats["total_commits"] += 1
        timestamp = datetime.now(UTC)
        
        # Get correlation ID from governance context
        try:
            ctx = GovernanceContextManager.require_context()
            correlation_id = ctx.correlation_id
        except RuntimeError:
            correlation_id = execution_result.correlation_id
        
        log.info(
            f"[{correlation_id}] Committing execution to ledger: "
            f"verdict_id={execution_result.ledger_entry.verdict_id}, "
            f"validation_status={execution_result.validation_status}"
        )
        
        # HIGH-004 FIX: Implement transaction-level atomicity
        # Use two-phase approach: prepare -> commit
        # If commit fails, the prepared entry is discarded (no side effects)
        # Lock ensures no concurrent modifications during transaction
        async with self._lock:
            try:
                # Phase 1: Prepare updated entry (no side effects yet)
                updated_entry = self._update_entry_with_validation(
                    entry=execution_result.ledger_entry,
                    validation_passed=validation_passed,
                    validation_violations=validation_violations,
                    validation_timestamp=validation_timestamp,
                    fortress_version=fortress_version,
                    execution_result=execution_result
                )
                
                # Phase 2: Commit to ledger (atomic operation)
                # HIGH-004: If this fails, no changes are persisted
                ledger_hash = await self._commit_entry_async(updated_entry)
                
                self.stats["successful_commits"] += 1
                
                log.info(
                    f"[{correlation_id}] Ledger commit successful: "
                    f"verdict_id={updated_entry.verdict_id}, "
                    f"hash={ledger_hash[:16]}..., "
                    f"validation_status={updated_entry.validation_status}"
                )
                
                return LedgerCommitResult(
                    success=True,
                    ledger_hash=ledger_hash,
                    entry=updated_entry,
                    error=None,
                    timestamp=timestamp
                )
                
            except Exception as e:
                self.stats["failed_commits"] += 1
                error_msg = f"Ledger commit failed: {e}"
                
                log.error(
                    f"[{correlation_id}] {error_msg}",
                    exc_info=True
                )
                
                # HIGH-004: Atomicity - no partial state persisted
                # The prepared entry (updated_entry) is discarded
                # Return original entry (not updated) to indicate failure
                # This ensures no inconsistent state between preparation and commit
                
                if self.strict_mode:
                    # In strict mode, always raise to ensure atomicity
                    # RULE 10: Execution Atomicity - no partial commits
                    raise RuntimeError(
                        f"[{correlation_id}] HIGH-004: Ledger commit atomicity violation. "
                        f"Commit failed after preparation: {e}"
                    ) from e
                
                return LedgerCommitResult(
                    success=False,
                    ledger_hash=None,
                    entry=execution_result.ledger_entry,  # Return ORIGINAL, not updated
                    error=error_msg,
                    timestamp=timestamp
                )
    
    async def commit_pending(
        self,
        pending_commit: PendingLedgerCommit
    ) -> LedgerCommitResult:
        """
        Commit a pending ledger commit.
        
        Alternative method that accepts a PendingLedgerCommit contract.
        
        Args:
            pending_commit: The PendingLedgerCommit containing entry and validation results
            
        Returns:
            LedgerCommitResult with commit status
        """
        # Extract execution result fields from pending commit
        # This is a convenience method for compatibility
        
        from mahoun.contracts.verdict_execution import VerdictExecutionResult
        
        # We need to reconstruct a minimal VerdictExecutionResult
        # This method exists for backward compatibility during migration
        
        execution_result = VerdictExecutionResult(
            verdict=None,  # Not available in PendingLedgerCommit
            ledger_entry=pending_commit.ledger_entry,
            proof=None,
            execution_id=pending_commit.execution_id,
            correlation_id=pending_commit.correlation_id,
            execution_timestamp=pending_commit.validation_timestamp or datetime.now(UTC),
            validation_passed=pending_commit.validation_passed,
            validation_violations=pending_commit.validation_violations,
            validation_timestamp=pending_commit.validation_timestamp,
            fortress_version=pending_commit.fortress_version,
        )
        
        return await self.commit_execution(
            execution_result=execution_result,
            validation_passed=pending_commit.validation_passed,
            validation_violations=pending_commit.validation_violations,
            validation_timestamp=pending_commit.validation_timestamp,
            fortress_version=pending_commit.fortress_version
        )
    
    def _update_entry_with_validation(
        self,
        entry: LedgerEntry,
        validation_passed: bool,
        validation_violations: list[dict[str, Any]] | None,
        validation_timestamp: datetime | None,
        fortress_version: str | None,
        execution_result: VerdictExecutionResult
    ) -> LedgerEntry:
        """
        Create an updated LedgerEntry with validation results.
        
        Per RULE 6, this ensures the ledger entry permanently records:
        - Validation status (PASSED/FAILED)
        - Validation timestamp
        - Validation violations (if any)
        - Fortress version
        - Execution identifiers
        - Proof hashes
        - Public key and key version (for independent verification)
        
        PER RULE 5: Evidence binding
        - public_key and key_version from proof enable independent verification
        
        PER RULE 7: Ledger becomes source of truth
        - All information for verification is stored in ledger
        
        Args:
            entry: The original pending LedgerEntry
            validation_passed: Whether validation passed
            validation_violations: List of violations if validation failed
            validation_timestamp: When validation occurred
            fortress_version: Version of Fortress validator
            execution_result: The full execution result for additional data
            
        Returns:
            Updated LedgerEntry with validation results
        """
        # Extract validation violations as strings
        violation_strings = None
        if validation_violations:
            violation_strings = [str(v) for v in validation_violations]
        
        # Get proof hashes and key information if proof exists
        proof_hash = None
        reasoning_chain_hash = None
        evidence_merkle_root = None
        graph_state_hash = None
        public_key = None
        key_version = None
        
        if execution_result.proof:
            proof_hash = execution_result.proof.signature
            reasoning_chain_hash = execution_result.proof.reasoning_chain_hash
            evidence_merkle_root = execution_result.proof.evidence_merkle_root
            graph_state_hash = execution_result.proof.graph_state_hash
            # Store public key and key version for independent verification
            public_key = execution_result.proof.public_key
            key_version = execution_result.proof.key_version
        
        # Create updated entry
        # Note: LedgerEntry is frozen, so we create a new instance
        return LedgerEntry(
            # Original fields
            verdict_id=entry.verdict_id,
            case_id=entry.case_id,
            referenced_ltm_nodes=entry.referenced_ltm_nodes,
            referenced_facts=entry.referenced_facts,
            confidence=entry.confidence,
            invariant_version=entry.invariant_version,
            guard_mode=entry.guard_mode,
            created_at=entry.created_at,
            
            # Updated fields
            event_type=entry.event_type or "VERDICT_EXECUTION",
            request_id=entry.request_id or execution_result.execution_id,
            
            # Validation results (RULE 6)
            # HIGH-007: Use ValidationStatus enum
            validation_status=ValidationStatus.PASSED if validation_passed else ValidationStatus.FAILED,
            validation_timestamp=validation_timestamp or datetime.now(UTC),
            validation_violations=violation_strings,
            fortress_version=fortress_version,
            
            # Proof hashes (RULE 4, RULE 5)
            proof_hash=proof_hash,
            reasoning_chain_hash=reasoning_chain_hash,
            evidence_merkle_root=evidence_merkle_root,
            graph_state_hash=graph_state_hash,
            
            # Key information for independent verification (RULE 5, RULE 6, RULE 7)
            public_key=public_key,
            key_version=key_version,
            
            # Execution identifiers (RULE 7)
            execution_id=execution_result.execution_id,
            correlation_id=execution_result.correlation_id,
        )
    
    async def _commit_entry_async(self, entry: LedgerEntry) -> str:
        """
        Internal method to commit a ledger entry.
        
        Args:
            entry: The LedgerEntry to commit
            
        Returns:
            The ledger hash of the committed entry
        """
        # Use the ledger writer to commit
        # EvidenceLedgerWriter.write() is synchronous, so we run it in executor
        # This is the ONLY place where ledger writer is used for execution commits
        loop = asyncio.get_event_loop()
        ledger_hash = await loop.run_in_executor(
            None, 
            self.ledger_writer.write, 
            entry
        )
        return ledger_hash
    
    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Reset service statistics."""
        self.stats = {
            "total_commits": 0,
            "successful_commits": 0,
            "failed_commits": 0,
        }


# Factory function for creating LedgerCommitService
def create_ledger_commit_service(
    ledger_writer: EvidenceLedgerWriter,
    strict_mode: bool = True
) -> LedgerCommitService:
    """
    Factory function for creating LedgerCommitService.
    
    Args:
        ledger_writer: The EvidenceLedgerWriter to use
        strict_mode: If True, raise exceptions on commit failures
        
    Returns:
        Configured LedgerCommitService instance
    """
    return LedgerCommitService(
        ledger_writer=ledger_writer,
        strict_mode=strict_mode
    )

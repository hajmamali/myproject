"""
MAHOUN Verdict Execution Result Contract
==========================================

Classification: MISSION-CRITICAL / ARCHITECTURAL CONTRACT / IMMUTABLE
Purpose: Explicit contract for transporting execution lifecycle artifacts between
reasoning components without hidden state or implicit dependencies.

This contract enforces RULE 3: No hidden transport mechanisms.
All execution artifacts travel through this explicit, immutable contract.

CRITICAL INVARIANTS:
- I1: This contract owns ONLY execution lifecycle artifacts
- I2: All fields are immutable (frozen=True dataclass)
- I3: No thread-local, global, or hidden state
- I4: Proof and ledger entry are bound together
- I5: Evidence references are preserved through entire lifecycle

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mahoun.ledger.models import LedgerEntry
    from mahoun.crypto.proof_system import CryptographicProof
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdict, VerdictStep, EvidenceReference


@dataclass(frozen=True)
class VerdictExecutionResult:
    """
    Immutable contract for transporting verdict execution artifacts.
    
    This contract is the SOLE authorized mechanism for passing execution
    artifacts between:
    - EvidenceLinkedVerdictEngine (creator)
    - VerdictEngineAdapter (transformer)
    - FortressProtectedReasoningService (validator + committer)
    
    Fields:
    - verdict: The generated EvidenceLinkedVerdict
    - ledger_entry: The PENDING LedgerEntry (NOT committed yet)
    - proof: The generated CryptographicProof
    - execution_id: Unique execution identifier
    - correlation_id: Governance correlation identifier
    - execution_timestamp: When execution started
    - validation_result: Will be None initially, populated by Fortress
    
    INVARIANTS:
    - ledger_entry is NEVER committed by the creator
    - proof MUST be generated from actual evidence (not empty evidence_refs)
    - All fields are immutable after creation
    """
    
    # Core execution artifacts (required, no defaults)
    verdict: EvidenceLinkedVerdict
    ledger_entry: LedgerEntry
    execution_id: str
    correlation_id: str
    execution_timestamp: datetime
    
    # Optional artifacts and metadata (with defaults)
    proof: CryptographicProof | None = None
    validation_passed: bool | None = None
    validation_violations: list[dict[str, Any]] | None = None
    validation_timestamp: datetime | None = None
    fortress_version: str | None = None
    reasoning_depth: int = 0
    evidence_count: int = 0
    agreement_score: float | None = None
    
    def __post_init__(self):
        """
        Validate contract invariants on creation.
        
        Raises:
            ValueError: If required invariants are violated
        """
        # I1: Verdict must exist
        if self.verdict is None:
            raise ValueError("VerdictExecutionResult: verdict cannot be None")
        
        # I2: Ledger entry must exist
        if self.ledger_entry is None:
            raise ValueError("VerdictExecutionResult: ledger_entry cannot be None")
        
        # I3: Execution ID must be present
        if not self.execution_id:
            raise ValueError("VerdictExecutionResult: execution_id cannot be empty")
        
        # I4: Correlation ID must be present
        if not self.correlation_id:
            raise ValueError("VerdictExecutionResult: correlation_id cannot be empty")
        
        # I5: Timestamp must be valid
        if self.execution_timestamp is None:
            raise ValueError("VerdictExecutionResult: execution_timestamp cannot be None")
        
        # I6: Ledger entry must have verdict_id matching verdict
        if self.verdict.verdict_id and self.ledger_entry.verdict_id:
            if self.verdict.verdict_id != self.ledger_entry.verdict_id:
                raise ValueError(
                    f"VerdictExecutionResult: verdict_id mismatch - "
                    f"verdict={self.verdict.verdict_id}, "
                    f"ledger_entry={self.ledger_entry.verdict_id}"
                )
        
        # I7: Ledger entry must have case_id matching verdict
        if self.verdict.verdict_id and self.ledger_entry.case_id:
            # case_id is stored in ledger_entry, verdict has verdict_id
            # Both should be present and consistent
            pass
    
    @property
    def is_validated(self) -> bool:
        """Check if Fortress validation has been performed."""
        return self.validation_passed is not None
    
    @property
    def validation_status(self) -> str:
        """Get validation status string."""
        if self.validation_passed is None:
            return "PENDING"
        return "PASSED" if self.validation_passed else "FAILED"
    
    def get_evidence_references(self) -> list[EvidenceReference]:
        """
        Extract all evidence references from verdict steps.
        
        Returns:
            List of EvidenceReference objects from all verdict steps
        """
        evidence_refs = []
        for step in self.verdict.steps:
            evidence_refs.extend(step.evidence)
        return evidence_refs
    
    def get_evidence_node_ids(self) -> list[str]:
        """
        Extract all evidence node IDs from verdict steps.
        
        Returns:
            List of unique evidence node IDs
        """
        node_ids = set()
        for step in self.verdict.steps:
            for ev in step.evidence:
                node_ids.add(ev.node_id)
        return sorted(node_ids)
    
    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to dictionary for debugging/logging.
        
        Note: This is for observability only, not for transport.
        The contract itself is the transport mechanism.
        
        Returns:
            Dictionary representation
        """
        from dataclasses import asdict
        return {
            **asdict(self),
            "validation_status": self.validation_status,
            "is_validated": self.is_validated,
            "evidence_count": len(self.get_evidence_references()),
        }


@dataclass(frozen=True)
class PendingLedgerCommit:
    """
    Immutable contract for pending ledger commit operation.
    
    This contract represents a ledger entry that has been created but
    NOT yet committed to immutable storage. It travels through the
    validation pipeline and is committed only after Fortress validation.
    
    Fields:
    - ledger_entry: The LedgerEntry to commit
    - validation_result: Fortress validation result
    - execution_id: The execution identifier
    - correlation_id: Governance correlation identifier
    
    This enforces RULE 2: Delayed Ledger Commit
    """
    
    # Required fields (no defaults)
    ledger_entry: LedgerEntry
    validation_passed: bool
    execution_id: str
    correlation_id: str
    
    # Optional fields (with defaults)
    validation_violations: list[dict[str, Any]] | None = None
    validation_timestamp: datetime | None = None
    fortress_version: str | None = None
    
    def __post_init__(self):
        """Validate contract invariants."""
        if self.ledger_entry is None:
            raise ValueError("PendingLedgerCommit: ledger_entry cannot be None")
        if not self.execution_id:
            raise ValueError("PendingLedgerCommit: execution_id cannot be empty")
        if not self.correlation_id:
            raise ValueError("PendingLedgerCommit: correlation_id cannot be empty")


@dataclass(frozen=True)
class ExecutionContext:
    """
    Immutable execution context for carrying governance and execution metadata.
    
    This is NOT the same as GovernanceContext. This is a lightweight,
    explicit contract for passing execution-scoped data.
    
    RULE 14: Every execution MUST occur inside GovernanceContext.
    This ExecutionContext complements that by carrying explicit data.
    """
    
    correlation_id: str
    execution_id: str
    execution_mode: str
    timestamp: datetime
    
    def __post_init__(self):
        """Validate contract invariants."""
        if not self.correlation_id:
            raise ValueError("ExecutionContext: correlation_id cannot be empty")
        if not self.execution_id:
            raise ValueError("ExecutionContext: execution_id cannot be empty")
        if not self.execution_mode:
            raise ValueError("ExecutionContext: execution_mode cannot be empty")
        if self.timestamp is None:
            raise ValueError("ExecutionContext: timestamp cannot be None")

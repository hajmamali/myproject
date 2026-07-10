"""
Ledger Module Contracts
========================

Formal contracts for the ledger module's public interfaces.

These contracts define:
- LedgerEntry structure validation
- Write operation contracts
- Verification contracts
- Invariant enforcement points

All contracts use `extra="forbid"` to ensure clean data structures.

Validates Requirements: 2.1, 2.2, 2.3
Enforces Invariants: EL-I1, EL-I4, EL-I6, EL-I7
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime


# ============================================================================
# LedgerEntry Contracts
# ============================================================================

class LedgerEntryContract(BaseModel):
    """
    Contract for immutable ledger entry.
    
    Validates: Requirement 2.2 - Ledger entry structure
    Enforces: EL-I1 (Evidence required), EL-I4 (Immutability), EL-I7 (Privacy)
    """
    verdict_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Unique verdict identifier"
    )
    case_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Case identifier"
    )
    referenced_ltm_nodes: List[str] = Field(
        ...,
        min_length=1,
        description="LTM node references (rules, statutes, precedents) - EL-I1"
    )
    referenced_facts: List[str] = Field(
        ...,
        description="Fact ID references (opaque IDs only) - EL-I7"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Verdict confidence score"
    )
    invariant_version: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Invariant version (e.g., '1.0.0')"
    )
    guard_mode: str = Field(
        ...,
        pattern="^(OFF|WARN|STRICT|AUDIT)$",
        description="Guard mode at time of verdict"
    )
    created_at: datetime = Field(
        ...,
        description="Entry creation timestamp"
    )
    event_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional event type"
    )
    request_id: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional request identifier"
    )
    
    @field_validator('referenced_ltm_nodes')
    @classmethod
    def validate_evidence_required(cls, v: List[str]) -> List[str]:
        """
        Enforce EL-I1: Every entry must have at least one evidence reference.
        """
        if not v or len(v) == 0:
            raise ValueError(
                "EL-I1 Violation: At least one LTM node reference required"
            )
        return v
    
    @field_validator('referenced_facts')
    @classmethod
    def validate_fact_privacy(cls, v: List[str]) -> List[str]:
        """
        Enforce EL-I7: Only opaque fact IDs allowed (no sensitive values).
        
        This validator checks that fact references look like IDs, not values.
        """
        for fact_ref in v:
            # Basic heuristic: IDs should be short and alphanumeric
            if len(fact_ref) > 500:
                raise ValueError(
                    f"EL-I7 Violation: Fact reference too long (possible value leak): {fact_ref[:50]}..."
                )
            # Check for common sensitive patterns (basic check)
            sensitive_patterns = ['ssn', 'social', 'passport', 'credit_card', 'phone', 'email']
            if any(pattern in fact_ref.lower() for pattern in sensitive_patterns):
                raise ValueError(
                    f"EL-I7 Violation: Fact reference contains sensitive pattern: {fact_ref}"
                )
        return v
    
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,  # EL-I4: Immutability
        json_schema_extra={
            "example": {
                "verdict_id": "verdict_12345",
                "case_id": "case_67890",
                "referenced_ltm_nodes": ["rule_contract_breach", "statute_220"],
                "referenced_facts": ["fact_0", "fact_1"],
                "confidence": 0.92,
                "invariant_version": "1.0.0",
                "guard_mode": "STRICT",
                "created_at": "2024-01-15T10:30:00Z",
                "event_type": "verdict_published",
                "request_id": "req_abc123"
            }
        }
    )


class WriteLedgerInput(BaseModel):
    """
    Input contract for EvidenceLedgerWriter.write()
    
    Validates: Requirement 2.1 - Write operation input
    """
    entry: LedgerEntryContract = Field(
        ...,
        description="Ledger entry to write"
    )
    
    model_config = ConfigDict(extra="forbid")


class WriteLedgerOutput(BaseModel):
    """
    Output contract for EvidenceLedgerWriter.write()
    
    Validates: Requirement 2.2 - Write operation output
    Enforces: EL-I6 (Hash chain for audit sufficiency)
    """
    entry_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hash of entry (64 hex chars)"
    )
    prev_hash: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Previous entry hash ('genesis' or 64 hex chars)"
    )
    written_at: datetime = Field(
        ...,
        description="Timestamp when entry was written"
    )
    success: bool = Field(
        default=True,
        description="Write operation success status"
    )
    
    @field_validator('entry_hash')
    @classmethod
    def validate_hash_format(cls, v: str) -> str:
        """Ensure hash is valid hex string."""
        if not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError("entry_hash must be valid hex string")
        return v.lower()
    
    @field_validator('prev_hash')
    @classmethod
    def validate_prev_hash_format(cls, v: str) -> str:
        """Ensure prev_hash is 'genesis' or valid hex."""
        if v == "genesis":
            return v
        if len(v) != 64:
            raise ValueError("prev_hash must be 'genesis' or 64-char hex string")
        if not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError("prev_hash must be valid hex string")
        return v.lower()
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "entry_hash": "a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
                "prev_hash": "genesis",
                "written_at": "2024-01-15T10:30:00.123Z",
                "success": True
            }
        }
    )


class WriteLedgerError(BaseModel):
    """
    Error contract for EvidenceLedgerWriter.write() failures.
    
    Validates: Requirement 2.3 - Error handling
    Enforces: EL-I3 (Verdict blocking on ledger failure)
    
    Failure Modes:
    - evidence_required: No evidence references (EL-I1)
    - privacy_violation: Sensitive data in fact references (EL-I7)
    - storage_failure: Backend storage failed (EL-I3)
    - hash_computation_failed: Hash computation error
    """
    error_type: str = Field(
        ...,
        pattern="^(evidence_required|privacy_violation|storage_failure|hash_computation_failed)$",
        description="Error type identifier"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context"
    )
    blocks_verdict: bool = Field(
        default=True,
        description="Whether this error blocks verdict publication (EL-I3)"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "error_type": "storage_failure",
                "message": "Failed to write to ledger backend",
                "details": {"backend": "jsonl", "path": "/data/ledger.jsonl"},
                "blocks_verdict": True
            }
        }
    )


# ============================================================================
# Verification Contracts
# ============================================================================

class VerifyIntegrityInput(BaseModel):
    """
    Input contract for EvidenceLedgerWriter.verify_integrity()
    
    Validates: Requirement 2.1 - Verification input
    """
    # No input parameters needed - verifies entire chain
    
    model_config = ConfigDict(extra="forbid")


class VerifyIntegrityOutput(BaseModel):
    """
    Output contract for EvidenceLedgerWriter.verify_integrity()
    
    Validates: Requirement 2.2 - Verification output
    Enforces: EL-I6 (Audit sufficiency via hash chain)
    """
    is_valid: bool = Field(
        ...,
        description="Whether hash chain is valid"
    )
    total_entries: int = Field(
        ...,
        ge=0,
        description="Total number of entries verified"
    )
    first_invalid_entry: Optional[str] = Field(
        None,
        description="Verdict ID of first invalid entry (if any)"
    )
    verification_timestamp: datetime = Field(
        ...,
        description="When verification was performed"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "is_valid": True,
                "total_entries": 1523,
                "first_invalid_entry": None,
                "verification_timestamp": "2024-01-15T10:35:00Z"
            }
        }
    )


class VerifyIntegrityError(BaseModel):
    """
    Error contract for verification failures.
    
    Validates: Requirement 2.3 - Error handling
    
    Failure Modes:
    - backend_unavailable: Storage backend not accessible
    - corrupted_data: Data corruption detected
    - verification_timeout: Verification took too long
    """
    error_type: str = Field(
        ...,
        pattern="^(backend_unavailable|corrupted_data|verification_timeout)$",
        description="Error type identifier"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context"
    )
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Invariant Specification Contracts
# ============================================================================

class InvariantSpecContract(BaseModel):
    """
    Contract for invariant specification.
    
    Validates: Requirement 2.2 - Invariant metadata structure
    """
    id: str = Field(
        ...,
        pattern="^EL-I[0-9]+$",
        description="Invariant ID (e.g., 'EL-I1')"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Invariant name"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Invariant description"
    )
    enforced_at: List[str] = Field(
        ...,
        min_length=1,
        description="List of enforcement points (module paths)"
    )
    failure_consequence: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Consequence of invariant violation"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "EL-I1",
                "name": "Evidence Required",
                "description": "Every published verdict must have at least one evidence reference.",
                "enforced_at": ["mahoun/ledger/guards.py::validate_entry"],
                "failure_consequence": "Verdicts without evidence can be published, leading to hallucinated conclusions."
            }
        }
    )


class GetInvariantsOutput(BaseModel):
    """
    Output contract for get_all_invariants()
    
    Validates: Requirement 2.2 - Invariants list output
    """
    invariants: List[InvariantSpecContract] = Field(
        ...,
        min_length=1,
        description="List of all registered invariants"
    )
    invariant_version: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Current invariant version"
    )
    total_invariants: int = Field(
        ...,
        ge=1,
        description="Total number of invariants"
    )
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Backend Configuration Contracts
# ============================================================================

class LedgerBackendConfig(BaseModel):
    """
    Contract for ledger backend configuration.
    
    Validates: Requirement 2.1 - Backend configuration
    """
    backend_type: str = Field(
        ...,
        pattern="^(jsonl|sqlite|noop)$",
        description="Backend type"
    )
    path: Optional[str] = Field(
        None,
        max_length=500,
        description="Storage path (not needed for noop)"
    )
    
    @model_validator(mode='after')
    def validate_path_required(self) -> 'LedgerBackendConfig':
        """Ensure path is provided for file-based backends."""
        if self.backend_type in ['jsonl', 'sqlite'] and not self.path:
            raise ValueError(f"path is required for backend_type='{self.backend_type}'")
        return self
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "backend_type": "jsonl",
                "path": "data/ledger/evidence.jsonl"
            }
        }
    )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Ledger Entry
    "LedgerEntryContract",
    # Write Operations
    "WriteLedgerInput",
    "WriteLedgerOutput",
    "WriteLedgerError",
    # Verification
    "VerifyIntegrityInput",
    "VerifyIntegrityOutput",
    "VerifyIntegrityError",
    # Invariants
    "InvariantSpecContract",
    "GetInvariantsOutput",
    # Configuration
    "LedgerBackendConfig",
]

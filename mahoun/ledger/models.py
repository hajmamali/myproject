# mahoun/ledger/models.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple


class ValidationStatus(str, Enum):
    """
    Validation status enum for ledger entries.
    
    HIGH-007 FIX: validation_status is now required and uses explicit enum values
    instead of Optional[str] to ensure it's never None after commit.
    
    PER RULE 6: Validation result ownership - ledger must permanently record validation status
    """
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class LedgerEntry:
    """
    Immutable ledger entry representing a single execution event.
    
    Per RULE 6 and RULE 7, this entry must permanently record:
    - Evidence references (referenced_ltm_nodes, referenced_facts)
    - Validation status (validation_status) - REQUIRED
    - Proof hashes (proof_hash, reasoning_chain_hash, evidence_merkle_root)
    - Execution metadata (execution_id, correlation_id)
    - Key information (public_key, key_version) for proof verification
    
    This enables complete reconstruction of execution from ledger alone.
    
    PER RULE 5: Evidence binding
    - public_key enables independent verification of proofs
    - key_version tracks which key was used
    
    PER RULE 6: Validation result ownership
    - validation_status records whether execution PASSED or FAILED
    
    PER RULE 7: Ledger becomes source of truth
    - All information needed for verification is stored in ledger
    
    # ARCHITECTURE Section 156: Architectural integrity
    
    HIGH-001 FIX: All mutable lists replaced with immutable tuples
    to prevent post-creation tampering in frozen dataclass.
    """
    # Core identifiers
    verdict_id: str
    case_id: str

    # Evidence references (RULE 5: Evidence binding)
    # HIGH-001: Use Tuple instead of List for immutability
    referenced_ltm_nodes: Tuple[str, ...]   # rule_id, statute_id, precedent_id
    referenced_facts: Tuple[str, ...]       # fact_id

    # Execution quality metrics
    confidence: float
    invariant_version: str
    guard_mode: str

    # Timestamps
    created_at: datetime
    
    # Execution identifiers (RULE 7: Ledger becomes source of truth)
    execution_id: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Validation result (RULE 6: Validation result ownership)
    # HIGH-007 FIX: Now uses ValidationStatus enum and defaults to PENDING
    # This ensures validation_status is never None after commit
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_timestamp: Optional[datetime] = None
    # HIGH-001: Use Tuple instead of List for immutability
    validation_violations: Optional[Tuple[str, ...]] = None
    fortress_version: Optional[str] = None
    
    # Proof hashes (RULE 4: Proof generation ownership, RULE 5: Evidence binding)
    # These cryptographically bind the ledger entry to the execution proof
    proof_hash: Optional[str] = None
    reasoning_chain_hash: Optional[str] = None
    evidence_merkle_root: Optional[str] = None
    graph_state_hash: Optional[str] = None
    
    # Key information for proof verification (RULE 5, RULE 6)
    # Enables independent verification without external key management
    public_key: Optional[str] = None
    key_version: Optional[str] = None
    
    # Audit metadata
    event_type: Optional[str] = None

# HARDENING PATCH P11: Canonical serialization
def canonical_serialize(entry: LedgerEntry) -> dict:
    """
    Deterministically serialize a LedgerEntry to a dictionary.
    Used for cryptographic hashing across all ledger components to ensure
    consistent verification regardless of backend or parsing logic.
    """
    from dataclasses import asdict
    d = asdict(entry)
    
    # Ensure all datetime fields are strictly ISO formatted
    # Datetime MUST be strictly ISO formatted for JSON serialization
    datetime_fields = ['created_at', 'validation_timestamp', 'execution_timestamp']
    for field in datetime_fields:
        if isinstance(d.get(field), datetime):
            d[field] = d[field].isoformat()
        
    return d

"""
Mahoun Invariants Module
=========================
System invariants enforcement and validation.

This module provides the formal invariants that govern the platform's
zero-hallucination guarantees.

Key Invariants:
- EL-I1: Evidence Required
- EL-I2: No Reasoning Persistence  
- EL-I3: Verdict Blocking
- EL-I4: Immutability
- EL-I5: No Resurrection via Ledger
- EL-I6: Audit Sufficiency
- EL-I7: Privacy Preservation
- EL-I8: Tombstone Security Guards (NEW)
"""

from mahoun.invariants.ledger_invariants import (
    InvariantSpec,
    INVARIANT_VERSION,
    LEDGER_INVARIANTS,
    get_invariant_by_id,
    get_all_invariants,
)

# Verify EL-I8 is properly registered
def verify_el_i8_registration() -> bool:
    """Verify EL-I8 Tombstone Security is properly registered in invariants."""
    try:
        el_i8 = get_invariant_by_id("EL-I8")
        return (
            el_i8.name == "Tombstone Security Guards" and
            ("tombstone" in el_i8.description.lower() or 
             "deleted" in el_i8.description.lower() or
             "redacted" in el_i8.description.lower()) and
            len(el_i8.enforced_at) >= 1
        )
    except ValueError:
        return False

# Runtime verification
_EL_I8_REGISTERED = verify_el_i8_registration()

__all__ = [
    "InvariantSpec",
    "INVARIANT_VERSION", 
    "LEDGER_INVARIANTS",
    "get_invariant_by_id",
    "get_all_invariants",
    "verify_el_i8_registration",
]

# mahoun/invariants/ledger_invariants.py
"""
Evidence Ledger Invariants Registry
====================================

This module defines the formal invariants that govern the Evidence Ledger.
These invariants are non-negotiable guarantees that maintain system integrity.

CRITICAL: These invariants must be enforced at runtime. Violation means
the system cannot be trusted for legal decision-making.
"""

from dataclasses import dataclass
from typing import List

# Current invariant version - must be updated when invariants change
INVARIANT_VERSION = "1.0.0"


@dataclass(frozen=True)
class InvariantSpec:
    """Specification of a system invariant"""
    id: str
    name: str
    description: str
    enforced_at: List[str]
    failure_consequence: str


# ============================================================================
# REGISTERED EVIDENCE LEDGER INVARIANTS
# ============================================================================

LEDGER_INVARIANTS = [
    InvariantSpec(
        id="EL-I1",
        name="Evidence Required",
        description="Every published verdict must have at least one evidence reference.",
        enforced_at=["mahoun/ledger/guards.py::validate_entry"],
        failure_consequence="Verdicts without evidence references can be published, leading to hallucinated legal conclusions that cannot be audited or invalidated."
    ),

    InvariantSpec(
        id="EL-I2",
        name="No Reasoning Persistence",
        description="Ledger must never store reasoning steps, inference paths, or graph structure.",
        enforced_at=["mahoun/ledger/models.py::LedgerEntry", "mahoun/ledger/storage.py"],
        failure_consequence="If reasoning artifacts are stored, the ledger becomes a reasoning trace, violating the separation of concerns and potentially exposing internal inference details."
    ),

    InvariantSpec(
        id="EL-I3",
        name="Verdict Blocking",
        description="If ledger write fails, verdict publication must fail.",
        enforced_at=["mahoun/reasoning/evidence_linked_verdict.py::generate_verdict"],
        failure_consequence="Verdicts can be published without audit trail, making the system non-auditable and allowing untraceable legal decisions."
    ),

    InvariantSpec(
        id="EL-I4",
        name="Immutability",
        description="Ledger entries are immutable once written.",
        enforced_at=["mahoun/ledger/models.py::LedgerEntry", "mahoun/ledger/storage.py"],
        failure_consequence="If entries can be modified, the audit trail becomes unreliable, allowing evidence tampering or verdict rewriting."
    ),

    InvariantSpec(
        id="EL-I5",
        name="No Resurrection via Ledger",
        description="Defeated or excluded nodes must never appear in ledger references.",
        enforced_at=["mahoun/reasoning/evidence_linked_verdict.py::generate_verdict"],
        failure_consequence="Invalidated evidence can reappear in verdicts, undermining contradiction resolution and allowing logically inconsistent legal conclusions."
    ),

    InvariantSpec(
        id="EL-I6",
        name="Audit Sufficiency",
        description="Ledger must contain enough references to invalidate a verdict if evidence is removed.",
        enforced_at=["mahoun/reasoning/evidence_linked_verdict.py::generate_verdict"],
        failure_consequence="Removing evidence does not invalidate verdicts, allowing decisions to persist despite lost evidentiary foundation."
    ),

    InvariantSpec(
        id="EL-I7",
        name="Privacy Preservation",
        description="Evidence Ledger must never store sensitive fact values. Only opaque fact identifiers are allowed.",
        enforced_at=["mahoun/ledger/privacy.py::filter_facts_for_ledger", "mahoun/reasoning/evidence_linked_verdict.py::generate_verdict"],
        failure_consequence="Irreversible personal data leak and legal liability."
    ),
]


def get_invariant_by_id(invariant_id: str) -> InvariantSpec:
    """Get invariant specification by ID"""
    for inv in LEDGER_INVARIANTS:
        if inv.id == invariant_id:
            return inv
    raise ValueError(f"Unknown invariant ID: {invariant_id}")


def get_all_invariants() -> List[InvariantSpec]:
    """Get all registered invariants"""
    return LEDGER_INVARIANTS.copy()
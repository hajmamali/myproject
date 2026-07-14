"""
Mahoun Reasoning Recorder
=========================
Records every reasoning micro-step for auditability.

P0-1/P0-5 HARDENING:
- Synthetic provenance (provenance=None) is NOW marked as synthetic,
  not silently created with default_scope/default_attestation.
- In production, provenance MUST be supplied explicitly or fail.
- verify_chain() now performs REAL hash-chain validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json

from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
from mahoun.core.governance.violations import GovernanceViolation, GovernanceViolationError, ViolationCategory, ViolationSeverity


@dataclass(frozen=True)
class ReasoningStep:
    """Single recorded reasoning step."""
    step_id: str
    step_type: str          # e.g., "rule_match", "semantic_eq", "contradiction_resolution"
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    provenance: ProvenanceMetadata
    chain_hash: str = ""    # Hash of this step in the chain (for verification)
    chain_prev_hash: str = "genesis"  # Previous hash in chain
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "provenance": self.provenance.to_dict(),
            "chain_hash": self.chain_hash,
            "chain_prev_hash": self.chain_prev_hash,
            "timestamp": self.timestamp,
        }


class ReasoningRecorder:
    """Collects reasoning steps and provides immutable audit trail."""

    def __init__(self):
        self._steps: List[ReasoningStep] = []
        self._last_hash: str = "genesis"

    def _resolve_provenance(self, operation: str = "reasoning_recorder") -> ProvenanceMetadata:
        """
        P0-1: Resolve provenance through GovernanceContext when available.
        Synthetic provenance is permitted only in development mode.
        """
        from mahoun.core.environment import get_current_environment
        from mahoun.core.governance.governance_context import GovernanceContextManager

        env = get_current_environment()

        if env.is_production() or env.is_staging():
            ctx = GovernanceContextManager.get_current_context()
            if ctx is None:
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.GOVERNANCE_BYPASS,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            "P0-1 GOVERNANCE VIOLATION: Cannot record reasoning step "
                            f"in {env.environment.value} without active GovernanceContext. "
                            "Operation blocked."
                        ),
                        source="ReasoningRecorder",
                        correlation_id="unknown",
                        details={},
                    )
                )
            return ctx.provenance_tracker.create_provenance(
                source=f"governed_{operation}",
                correlation_id=ctx.correlation_id,
                author="mahoun_reasoning_recorder",
                governance_scope_id=ctx.context_id,
                runtime_attestation_id=ctx.runtime_attestation.get("context_id", ctx.context_id),
                lineage_parent=None,
            )

        return ProvenanceMetadata.create(
            source=f"synthetic_{operation}",
            correlation_id=f"synthetic_{operation}",
            author="mahoun_dev_mode",
            governance_scope_id="development_synthetic_scope",
            runtime_attestation_id="development_synthetic_attestation",
            lineage_parent=None,
        )

    def record_step(
        self,
        step_type: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        provenance: Optional[ProvenanceMetadata] = None,
    ) -> ReasoningStep:
        """
        Record a reasoning step and return it.

        P0-1: When provenance is None (synthetic), use _resolve_provenance()
        which enforces GovernanceContext in production and marks as synthetic in dev.
        """
        if provenance is None:
            provenance = self._resolve_provenance(f"step_{step_type}")

        step_data_raw = {
            "step_type": step_type,
            "inputs": inputs,
            "outputs": outputs,
            "provenance": provenance.to_dict(),
        }
        step_id = hashlib.sha256(
            json.dumps(step_data_raw, sort_keys=True).encode()
        ).hexdigest()[:16]

        # P0-5: Compute chain hash (include prev hash for chain integrity)
        chain_payload = {
            "prev_hash": self._last_hash,
            "step_data": step_data_raw,
            "step_id": step_id,
        }
        chain_hash = hashlib.sha256(
            json.dumps(chain_payload, sort_keys=True).encode()
        ).hexdigest()

        step = ReasoningStep(
            step_id=step_id,
            step_type=step_type,
            inputs=inputs,
            outputs=outputs,
            provenance=provenance,
            chain_hash=chain_hash,
            chain_prev_hash=self._last_hash,
        )
        self._steps.append(step)
        self._last_hash = chain_hash
        return step

    def get_steps(self) -> List[ReasoningStep]:
        return list(self._steps)

    def verify_chain(self) -> bool:
        """
        P0-5: Real hash-chain verification.

        Re-computes the chain hash for every step and compares it to the
        stored chain_hash. Returns True only if the entire chain is intact.
        Raises RuntimeError in production if chain is broken.
        """
        last = "genesis"
        for step in self._steps:
            # Re-compute expected chain hash from stored data
            step_data_raw = {
                "step_type": step.step_type,
                "inputs": step.inputs,
                "outputs": step.outputs,
                "provenance": step.provenance.to_dict(),
            }
            chain_payload = {
                "prev_hash": last,
                "step_data": step_data_raw,
                "step_id": step.step_id,
            }
            expected_hash = hashlib.sha256(
                json.dumps(chain_payload, sort_keys=True).encode()
            ).hexdigest()

            if step.chain_hash != expected_hash:
                from mahoun.core.environment import get_current_environment
                env = get_current_environment()
                if env.is_production():
                    raise RuntimeError(
                        f"P0-5 CHAIN VIOLATION: Hash chain broken at step {step.step_id}. "
                        f"Expected {expected_hash}, got {step.chain_hash}. "
                        "Data tampering detected."
                    )
                return False
            last = step.chain_hash
        return True
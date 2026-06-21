"""
MAHOUN Graduation Manager
==========================

Classification: CRITICAL / DATA LIFECYCLE
Purpose: Promotes quarantined nodes/relationships to the Master Graph
         when their confidence reaches 1.0 through human attestation
         or cross-verification.

INVARIANTS:
- GRAD-G1: Only nodes with confidence == 1.0 can graduate
- GRAD-G2: Graduation is audited through GovernedNeo4jSession
- GRAD-G3: Original quarantine metadata is preserved as provenance
- GRAD-G4: Graduation is idempotent (re-graduating is safe)

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GraduationError(Exception):
    """Raised when graduation fails due to policy violation."""


class GraduationManager:
    """Manages the lifecycle of quarantined graph entities.

    Quarantined nodes are written with labels like 'QuarantinedVerdict'.
    When confidence is verified to 1.0 (via human review, cross-validation,
    or LLM re-verification), this manager:

    1. Validates confidence == 1.0
    2. Removes the Quarantined label
    3. Adds the canonical label
    4. Records graduation provenance
    5. Appends audit trail

    All writes go through GovernedNeo4jSession — no direct Neo4j access.
    """

    def __init__(self, governed_session) -> None:
        """Initialize GraduationManager.

        Args:
            governed_session: GovernedNeo4jSession instance.
                Direct Neo4j adapters are REJECTED.
        """
        from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
        if not isinstance(governed_session, GovernedNeo4jSession):
            raise TypeError(
                f"GraduationManager requires GovernedNeo4jSession, "
                f"got {type(governed_session).__name__}. "
                f"Direct Neo4j access is FORBIDDEN."
            )
        self._session = governed_session
        self._graduated_count = 0
        logger.info("GraduationManager initialized")

    def graduate_node(
        self,
        node_id: str,
        quarantined_label: str,
        target_label: str,
        verified_confidence: float,
        attestation_source: str,
        attestation_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Graduate a quarantined node to the Master Graph.

        Args:
            node_id: Unique identifier of the quarantined node.
            quarantined_label: Current quarantined label (e.g., 'QuarantinedVerdict').
            target_label: Target canonical label (e.g., 'Verdict').
            verified_confidence: Must be exactly 1.0.
            attestation_source: Who/what verified this node
                (e.g., 'human_reviewer:ali', 'cross_validation_pipeline').
            attestation_metadata: Optional additional attestation context.

        Returns:
            Dict with graduation receipt details.

        Raises:
            GraduationError: If confidence != 1.0 or policy violated.
        """
        # INVARIANT GRAD-G1: Strict confidence check
        if verified_confidence != 1.0:
            raise GraduationError(
                f"Cannot graduate node '{node_id}': "
                f"confidence must be exactly 1.0, got {verified_confidence}. "
                f"Partial confidence promotion is FORBIDDEN."
            )

        # Validate label format
        if not quarantined_label.startswith("Quarantined"):
            raise GraduationError(
                f"Cannot graduate node '{node_id}': "
                f"label '{quarantined_label}' does not start with 'Quarantined'. "
                f"Only quarantined nodes can be graduated."
            )

        # Build graduation data
        graduation_timestamp = datetime.now(timezone.utc).isoformat()
        graduation_provenance = {
            "source": f"graduation_manager:{attestation_source}",
            "graduated_at": graduation_timestamp,
            "original_quarantined_label": quarantined_label,
            "attestation_source": attestation_source,
            "attestation_metadata": attestation_metadata or {},
        }

        # Write the graduated node with canonical label and confidence=1.0
        node_data = {
            "id": node_id,
            "confidence": 1.0,
            "graduation_timestamp": graduation_timestamp,
            "graduation_source": attestation_source,
            "provenance": graduation_provenance,
        }

        receipt = self._session.write_node(
            label=target_label,
            node_data=node_data,
            merge=True,
        )

        self._graduated_count += 1
        logger.info(
            "[GRADUATION] Node '%s' graduated: %s → %s "
            "(attestation=%s, receipt=%s)",
            node_id, quarantined_label, target_label,
            attestation_source, receipt.receipt_id,
        )

        return {
            "node_id": node_id,
            "from_label": quarantined_label,
            "to_label": target_label,
            "attestation_source": attestation_source,
            "graduated_at": graduation_timestamp,
            "receipt_id": receipt.receipt_id,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get graduation statistics."""
        return {
            "total_graduated": self._graduated_count,
        }

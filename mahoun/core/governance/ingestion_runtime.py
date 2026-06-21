"""
MAHOUN Governed Ingestion Runtime
=================================

Classification: KERNEL / INGESTION AUTHORITY

This is the governance-native replacement for the deprecated UnifiedLoader.
It eliminates orchestration-era middleware, retry-driven nondeterminism, and DLQ state corruption.

Core Principles:
1. Governance BEFORE orchestration
2. Determinism BEFORE retries
3. Immutable lineage BEFORE rollback
4. Append-only semantics (no DETACH DELETE compensation)
5. Capability-scoped execution (isolated per invocation)
"""

import logging
from typing import Any

from mahoun.core.exceptions import MahounError
from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata

logger = logging.getLogger(__name__)


class IngestionAbortedError(MahounError):
    """Raised when an ingestion sequence violates constraints and is aborted."""


class GovernedIngestionRuntime:
    """
    Capability-Scoped Execution Runtime for Document Ingestion.

    Unlike UnifiedLoader:
    - No background worker queues (avoids async authority leakage).
    - No DLQ (fails closed deterministically).
    - No retries (execution is deterministic; if it fails, the input is invalid or state is constrained).
    - No destructive rollbacks (relies on atomic GovernedWriteTransaction to naturally revert on exception).
    """

    def __init__(self, session: GovernedNeo4jSession):
        self._session = session

    def ingest_document_atomic(
        self, doc_id: str, text: str, metadata: dict[str, Any], author_id: str
    ) -> dict[str, Any]:
        """
        Atomically process a document into the graph via the governed boundary.

        If any validation fails (Ontology, Provenance, Capability), the entire
        transaction is aborted automatically by the session context.
        We NEVER execute DETACH DELETE to clean up.
        """
        logger.info("[RUNTIME] Commencing atomic ingestion sequence for %s", doc_id)

        # 1. Establish Immutable Provenance Identity
        provenance = ProvenanceMetadata.create_evidence(
            source=metadata.get("source", "api_ingestion"),
            correlation_id=doc_id,
            author=author_id,
            evidence_hash=doc_id,  # In reality, hash of the text
        )

        # 2. Begin Transaction
        tx = self._session.begin_transaction()

        try:
            # 3. Queue the primary Document Node
            doc_payload = {
                "id": doc_id,
                "text_content": text[:2000],  # Minimal preview for graph
                "title": metadata.get("title", "Untitled"),
                "provenance": provenance.to_dict(),
            }
            tx.queue_node(label="Document", node_data=doc_payload, merge=True)

            # (Here, integration with Vector pipelines would occur deterministically
            #  but WITHOUT breaking the atomicity of the Graph transaction)

            # 4. Commit (Validate-All-Then-Execute-All)
            receipts = tx.commit()

            logger.info(
                "[RUNTIME] Ingestion sequence finalized successfully. Generated %d immutable receipts.", len(receipts)
            )

            return {"status": "success", "doc_id": doc_id, "receipts": [r.receipt_id for r in receipts]}

        except Exception as e:
            # 5. Natural Abort (No destructive compensation)
            tx.abort()
            logger.error("[RUNTIME] Ingestion sequence aborted due to violation: %s", e)
            raise IngestionAbortedError(f"Deterministic ingestion failed: {e}") from e

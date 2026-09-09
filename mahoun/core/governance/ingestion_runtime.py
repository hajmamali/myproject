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
from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.ingestion_contract import CanonicalIngestionBatch
from mahoun.core.governance.ingestion_execution_gate import (
    IngestionExecutionGate,
)
from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession

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

        # 1. Establish Immutable Provenance Identity via the canonical factory.
        #    ProvenanceMetadata.create_evidence() does not exist; the only
        #    canonical path is GovernanceContextManager.require_provenance(),
        #    which extracts governance_scope_id / runtime_attestation_id from
        #    the active context and produces a fully-attested record.
        provenance = GovernanceContextManager.require_provenance(
            source=metadata.get("source", "api_ingestion"),
            author=author_id,
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

    def ingest_batch_atomic(
        self,
        batch: CanonicalIngestionBatch,
        author_id: str,
    ) -> dict[str, Any]:
        """Atomically materialize a specialized adapter batch.

        Adapters only emit the canonical contract. This method owns the
        governed transaction, ontology boundary, provenance attestation, and
        receipt collection.
        """
        if not isinstance(batch, CanonicalIngestionBatch):
            raise IngestionAbortedError("ingestion batch has an invalid type")
        if not batch.documents:
            raise IngestionAbortedError(
                "ingestion batch must contain a document"
            )
        permit = IngestionExecutionGate.require_active()
        if permit.request.source != batch.documents[0].source_uri:
            raise IngestionAbortedError(
                "execution permit does not match batch source"
            )

        source = str(batch.documents[0].provenance["source"])
        attested_provenance = GovernanceContextManager.require_provenance(
            source=source,
            author=author_id,
        ).to_dict()
        source_hashes = {
            document.provenance["source_hash"] for document in batch.documents
        }
        document_ids = {document.document_id for document in batch.documents}
        tx = self._session.begin_transaction()

        try:
            for document in batch.documents:
                document_provenance = {
                    **attested_provenance,
                    "source_hash": document.provenance["source_hash"],
                }
                tx.queue_node(
                    label="Document",
                    node_data={
                        "id": document.document_id,
                        "source_uri": document.source_uri,
                        "text_content": document.text[:2000],
                        "source_hash": document.provenance["source_hash"],
                        "provenance": document_provenance,
                    },
                    merge=True,
                )

            fact_by_object_id = {}
            for fact in batch.facts:
                if fact.provenance["source_hash"] not in source_hashes:
                    raise IngestionAbortedError(
                        "fact provenance is not bound to the batch: "
                        f"{fact.fact_id}"
                    )
                if fact.object_id in fact_by_object_id:
                    raise IngestionAbortedError(
                        f"duplicate semantic target in batch: {fact.object_id}"
                    )
                fact_by_object_id[fact.object_id] = fact
                tx.queue_node(
                    label="LawArticle",
                    node_data={
                        "id": fact.object_id,
                        "evidence_text": fact.evidence_text,
                        "source_hash": fact.provenance["source_hash"],
                        "provenance": {
                            **attested_provenance,
                            "source_hash": fact.provenance["source_hash"],
                        },
                    },
                    merge=True,
                )

            for relationship in batch.relationships:
                if relationship.source_id not in document_ids:
                    raise IngestionAbortedError(
                        "relationship source is not a document in the batch"
                    )
                if relationship.provenance["source_hash"] not in source_hashes:
                    raise IngestionAbortedError(
                        "relationship provenance is not bound to the batch"
                    )
                fact = fact_by_object_id.get(relationship.target_id)
                if (
                    fact is None
                    or fact.predicate != relationship.relationship_type
                ):
                    raise IngestionAbortedError(
                        "relationship is not backed by a matching "
                        "semantic fact"
                    )
                tx.queue_relationship(
                    source_type="Document",
                    source_id=relationship.source_id,
                    relationship_type=relationship.relationship_type,
                    target_type="LawArticle",
                    target_id=relationship.target_id,
                    rel_data={
                        **dict(relationship.properties),
                        "provenance": {
                            **attested_provenance,
                            "source_hash": relationship.provenance[
                                "source_hash"
                            ],
                        },
                    },
                    merge=True,
                )

            receipts = tx.commit()
            return {
                "status": "success",
                "document_ids": [
                    document.document_id for document in batch.documents
                ],
                "fact_count": len(batch.facts),
                "relationship_count": len(batch.relationships),
                "receipts": [receipt.receipt_id for receipt in receipts],
            }
        except Exception as exc:
            if tx.is_open:
                tx.abort()
            if isinstance(exc, IngestionAbortedError):
                raise
            raise IngestionAbortedError(
                f"Deterministic batch ingestion failed: {exc}"
            ) from exc

import pytest

from mahoun.core.governance.ingestion_contract import (
    CanonicalIngestionBatch,
    IngestionContractError,
    IngestionDocument,
    RelationshipFact,
    SemanticFact,
    sha256_text,
)


TEXT = "ماده ۱۰ قانون مدنی"
PROVENANCE = {
    "source": "test://specialized-adapter",
    "source_hash": sha256_text(TEXT),
    "correlation_id": "corr-test-001",
}


def document() -> IngestionDocument:
    return IngestionDocument(
        document_id="doc:civil:10",
        source_uri="test://specialized-adapter/civil-10",
        text=TEXT,
        provenance=PROVENANCE,
    )


def test_document_requires_hash_bound_to_exact_text():
    with pytest.raises(IngestionContractError, match="source_hash"):
        IngestionDocument(
            document_id="doc:civil:10",
            source_uri="test://source",
            text=TEXT,
            provenance={**PROVENANCE, "source_hash": "wrong"},
        )


def test_contract_rejects_untrimmed_or_missing_identifiers():
    with pytest.raises(IngestionContractError, match="document_id"):
        IngestionDocument(
            document_id=" doc:civil:10",
            source_uri="test://source",
            text=TEXT,
            provenance=PROVENANCE,
        )


def test_batch_rejects_duplicate_and_unrelated_provenance():
    fact = SemanticFact(
        fact_id="fact:1",
        subject_id="article:10",
        predicate="REGULATES",
        object_id="norm:contract",
        evidence_text=TEXT,
        provenance=PROVENANCE,
    )
    relationship = RelationshipFact(
        relationship_id="rel:1",
        source_id="article:10",
        relationship_type="REGULATES",
        target_id="norm:contract",
        properties={},
        provenance=PROVENANCE,
    )

    batch = CanonicalIngestionBatch((document(),), (fact,), (relationship,))
    assert batch.documents[0].document_id == "doc:civil:10"

    with pytest.raises(IngestionContractError, match="duplicate document"):
        CanonicalIngestionBatch((document(), document()))

    with pytest.raises(IngestionContractError, match="does not reference"):
        CanonicalIngestionBatch(
            (document(),),
            (
                SemanticFact(
                    fact_id="fact:foreign",
                    subject_id="article:10",
                    predicate="REGULATES",
                    object_id="norm:contract",
                    evidence_text=TEXT,
                    provenance={**PROVENANCE, "source_hash": sha256_text("other")},
                ),
            ),
        )
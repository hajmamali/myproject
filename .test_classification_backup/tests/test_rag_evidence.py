"""
Tests for RAGEvidenceNode — audit-grade RAG provenance wrapper.

These tests pin the invariants declared in mahoun/reasoning/rag_evidence.py.
They are deliberately exhaustive over the __post_init__ validation surface
because this class is the boundary at which RAG-retrieved evidence becomes
ledger-eligible. A failure here means un-auditable evidence can reach the
ledger.
"""

import hashlib

import pytest

from mahoun.reasoning.rag_evidence import (
    RAGEvidenceNode,
    RAGSource,
    SourceAuthority,
    _DEFAULT_CONFIDENCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _valid_content_hash(text: str = "some fact text") -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_kwargs(**overrides) -> dict:
    """Baseline kwargs that pass __post_init__. Individual tests override
    one field at a time to assert exactly which invariant failed."""
    base = dict(
        fact_index=0,
        doc_id="doc-abc",
        source=RAGSource.RAG,
        authority=SourceAuthority.TRUSTED_INTERNAL,
        score=0.8,
        retrieval_rank=0,
        correlation_id="corr-xyz",
        content_hash=_valid_content_hash(),
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Construction: happy path
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_minimal_valid_construction(self):
        node = RAGEvidenceNode(**_make_kwargs())
        assert node.fact_index == 0
        assert node.source == RAGSource.RAG
        assert node.authority == SourceAuthority.TRUSTED_INTERNAL
        assert node.is_sensitive is False
        assert node.confidence_threshold == _DEFAULT_CONFIDENCE_THRESHOLD

    def test_metadata_default_is_empty_dict(self):
        # Each instance must get its own dict, not a shared mutable default
        n1 = RAGEvidenceNode(**_make_kwargs())
        n2 = RAGEvidenceNode(**_make_kwargs())
        n1.metadata["k"] = "v"
        assert n2.metadata == {}

    def test_frozen_dataclass_rejects_mutation(self):
        node = RAGEvidenceNode(**_make_kwargs())
        with pytest.raises(Exception):  # FrozenInstanceError
            node.score = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# __post_init__ validation: fail-closed on bad input
# ---------------------------------------------------------------------------


class TestPostInitValidation:
    def test_negative_fact_index_rejected(self):
        with pytest.raises(ValueError, match="fact_index must be >= 0"):
            RAGEvidenceNode(**_make_kwargs(fact_index=-1))

    def test_negative_retrieval_rank_rejected(self):
        with pytest.raises(ValueError, match="retrieval_rank must be >= 0"):
            RAGEvidenceNode(**_make_kwargs(retrieval_rank=-1))

    def test_score_above_one_rejected(self):
        with pytest.raises(ValueError, match="score must be in"):
            RAGEvidenceNode(**_make_kwargs(score=1.5))

    def test_score_below_zero_rejected(self):
        with pytest.raises(ValueError, match="score must be in"):
            RAGEvidenceNode(**_make_kwargs(score=-0.1))

    def test_confidence_threshold_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="confidence_threshold must be in"):
            RAGEvidenceNode(**_make_kwargs(confidence_threshold=2.0))

    def test_string_source_rejected_must_be_enum(self):
        with pytest.raises(ValueError, match="source must be RAGSource"):
            RAGEvidenceNode(**_make_kwargs(source="rag"))  # type: ignore[arg-type]

    def test_string_authority_rejected_must_be_enum(self):
        with pytest.raises(ValueError, match="authority must be SourceAuthority"):
            RAGEvidenceNode(**_make_kwargs(authority="trusted_internal"))  # type: ignore[arg-type]

    def test_empty_correlation_id_rejected(self):
        with pytest.raises(ValueError, match="correlation_id is required"):
            RAGEvidenceNode(**_make_kwargs(correlation_id=""))

    def test_short_content_hash_rejected(self):
        with pytest.raises(ValueError, match="content_hash must be a 64-char"):
            RAGEvidenceNode(**_make_kwargs(content_hash="abc123"))

    def test_non_hex_content_hash_rejected(self):
        bad = "z" * 64
        with pytest.raises(ValueError, match="content_hash must be a 64-char"):
            RAGEvidenceNode(**_make_kwargs(content_hash=bad))

    def test_uppercase_hex_content_hash_rejected(self):
        # Contract: lowercase hex only. Uppercase breaks cross-process equality
        # and deterministic JSON serialization.
        upper = _valid_content_hash().upper()
        with pytest.raises(ValueError, match="content_hash must be a 64-char"):
            RAGEvidenceNode(**_make_kwargs(content_hash=upper))


# ---------------------------------------------------------------------------
# Identity: stable_id determinism and dedup semantics
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_stable_id_deterministic(self):
        a = RAGEvidenceNode(**_make_kwargs())
        b = RAGEvidenceNode(**_make_kwargs())
        assert a.stable_id == b.stable_id

    def test_stable_id_independent_of_rank_drift(self):
        # Two retrievals of the same doc in the same correlation must
        # produce the same stable_id even if rank differs (rank drift
        # between calls is a real scenario in the RAG pipeline).
        a = RAGEvidenceNode(**_make_kwargs(retrieval_rank=0))
        b = RAGEvidenceNode(**_make_kwargs(retrieval_rank=3))
        assert a.stable_id == b.stable_id
        assert a == b
        assert hash(a) == hash(b)

    def test_stable_id_independent_of_score_drift(self):
        a = RAGEvidenceNode(**_make_kwargs(score=0.91))
        b = RAGEvidenceNode(**_make_kwargs(score=0.74))
        assert a.stable_id == b.stable_id

    def test_stable_id_changes_with_different_doc(self):
        a = RAGEvidenceNode(**_make_kwargs(doc_id="doc-A"))
        b = RAGEvidenceNode(**_make_kwargs(doc_id="doc-B"))
        assert a.stable_id != b.stable_id

    def test_stable_id_changes_with_different_correlation(self):
        a = RAGEvidenceNode(**_make_kwargs(correlation_id="corr-1"))
        b = RAGEvidenceNode(**_make_kwargs(correlation_id="corr-2"))
        assert a.stable_id != b.stable_id


# ---------------------------------------------------------------------------
# Classification: privacy filter integration
# ---------------------------------------------------------------------------


class TestClassification:
    def test_is_high_confidence_at_threshold(self):
        node = RAGEvidenceNode(**_make_kwargs(score=_DEFAULT_CONFIDENCE_THRESHOLD))
        assert node.is_high_confidence() is True

    def test_is_high_confidence_below_threshold(self):
        node = RAGEvidenceNode(**_make_kwargs(score=_DEFAULT_CONFIDENCE_THRESHOLD - 0.01))
        assert node.is_high_confidence() is False

    def test_is_audit_eligible_requires_high_confidence(self):
        node = RAGEvidenceNode(**_make_kwargs(score=0.3))
        assert node.is_audit_eligible() is False

    def test_is_audit_eligible_blocks_sensitive(self):
        node = RAGEvidenceNode(**_make_kwargs(score=0.9, is_sensitive=True))
        assert node.is_audit_eligible() is False

    def test_is_audit_eligible_allows_safe_high_confidence(self):
        node = RAGEvidenceNode(**_make_kwargs(score=0.9, is_sensitive=False))
        assert node.is_audit_eligible() is True


# ---------------------------------------------------------------------------
# Serialization: deterministic, cross-process stable
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_to_ledger_provenance_contains_all_fields(self):
        node = RAGEvidenceNode(**_make_kwargs())
        payload = node.to_ledger_provenance()
        expected_keys = {
            "fact_index", "doc_id", "source", "authority", "score",
            "retrieval_rank", "correlation_id", "content_hash",
            "is_sensitive", "is_high_confidence", "is_audit_eligible",
            "stable_id", "metadata",
        }
        assert set(payload.keys()) == expected_keys

    def test_to_ledger_provenance_is_deterministic(self):
        a = RAGEvidenceNode(**_make_kwargs())
        b = RAGEvidenceNode(**_make_kwargs())
        assert a.to_ledger_provenance() == b.to_ledger_provenance()

    def test_to_ledger_provenance_enums_serialized_as_strings(self):
        node = RAGEvidenceNode(**_make_kwargs(
            source=RAGSource.HYBRID,
            authority=SourceAuthority.UNTRUSTED_EXTERNAL,
        ))
        payload = node.to_ledger_provenance()
        assert payload["source"] == "hybrid"
        assert payload["authority"] == "untrusted_external"

    def test_to_ledger_provenance_metadata_is_copy(self):
        node = RAGEvidenceNode(**_make_kwargs(metadata={"k": "v"}))
        payload = node.to_ledger_provenance()
        payload["metadata"]["k"] = "tampered"
        # Internal metadata must not be aliased to the payload
        assert node.metadata == {"k": "v"}


# ---------------------------------------------------------------------------
# Factory: from_evidence_dict coerces and defaults correctly
# ---------------------------------------------------------------------------


class TestFactory:
    def test_factory_minimal_dict(self):
        node = RAGEvidenceNode.from_evidence_dict(
            {"value": "fact text", "source": "rag", "score": 0.7, "metadata": {}},
            fact_index=2,
            correlation_id="corr-1",
            retrieval_rank=0,
        )
        assert node.fact_index == 2
        assert node.retrieval_rank == 0
        assert node.correlation_id == "corr-1"
        assert node.score == 0.7
        assert node.source == RAGSource.RAG
        # default authority = UNTRUSTED_EXTERNAL (fail-closed on trust class)
        assert node.authority == SourceAuthority.UNTRUSTED_EXTERNAL
        # content_hash is SHA-256 of the fact text
        assert node.content_hash == hashlib.sha256(b"fact text").hexdigest()

    def test_factory_picks_up_authority_from_metadata(self):
        node = RAGEvidenceNode.from_evidence_dict(
            {"value": "x", "metadata": {"authority": "trusted_partner"}},
            fact_index=0,
            correlation_id="c",
            retrieval_rank=0,
        )
        assert node.authority == SourceAuthority.TRUSTED_PARTNER

    def test_factory_unknown_authority_falls_back_to_default(self):
        # If metadata carries a garbage authority, default to UNTRUSTED_EXTERNAL
        node = RAGEvidenceNode.from_evidence_dict(
            {"value": "x", "metadata": {"authority": "lol"}},
            fact_index=0,
            correlation_id="c",
            retrieval_rank=0,
        )
        assert node.authority == SourceAuthority.UNTRUSTED_EXTERNAL

    def test_factory_unknown_source_falls_back_to_rag(self):
        node = RAGEvidenceNode.from_evidence_dict(
            {"value": "x", "source": "weird-source"},
            fact_index=0,
            correlation_id="c",
            retrieval_rank=0,
        )
        assert node.source == RAGSource.RAG

    def test_factory_picks_up_doc_id_from_metadata(self):
        node = RAGEvidenceNode.from_evidence_dict(
            {"value": "x", "metadata": {"doc_id": "meta-doc"}},
            fact_index=0,
            correlation_id="c",
            retrieval_rank=0,
        )
        assert node.doc_id == "meta-doc"

    def test_factory_is_sensitive_propagates(self):
        node = RAGEvidenceNode.from_evidence_dict(
            {"value": "x"},
            fact_index=0,
            correlation_id="c",
            retrieval_rank=0,
            is_sensitive=True,
        )
        assert node.is_sensitive is True
        assert node.is_audit_eligible() is False

    def test_factory_handles_missing_keys(self):
        # Empty dict must not crash — all fields must have defaults
        node = RAGEvidenceNode.from_evidence_dict(
            {},
            fact_index=0,
            correlation_id="c",
            retrieval_rank=0,
        )
        assert node.score == 0.0
        assert node.doc_id == ""
        assert node.content_hash == hashlib.sha256(b"").hexdigest()

    def test_factory_confidence_threshold_override(self):
        node = RAGEvidenceNode.from_evidence_dict(
            {"value": "x", "score": 0.4},
            fact_index=0,
            correlation_id="c",
            retrieval_rank=0,
            confidence_threshold=0.3,
        )
        assert node.is_high_confidence() is True

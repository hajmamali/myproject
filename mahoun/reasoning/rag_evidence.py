"""
RAG Evidence Node — audit-grade wrapper for retrieval provenance.

Closes the AGENTS.md Part 1-F documented gap: RAG-retrieved evidence must
carry its source, score, retrieval rank, content hash, authority class,
sensitivity flag, and a correlation_id that ties it back to the originating
GovernanceContext. All of these fields must be available at the ledger
boundary so that the proof tree is fully auditable.

Design constraints:
- frozen=True so identity is stable across processes
- __post_init__ enforces all invariants (fail closed on bad input)
- custom __hash__/__eq__ keyed on stable_id only, so re-retrievals of
  the same (doc, correlation) are equal regardless of rank drift
- to_ledger_provenance() produces a deterministic dict (fixed key order)
  suitable for hashing at the ledger layer
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RAGSource(str, Enum):
    """Retrieval mode used to obtain this evidence. Orthogonal to authority."""
    GRAPH = "graph"
    TEXT = "text"
    HYBRID = "hybrid"
    RAG = "rag"
    USER_PROVIDED = "user_provided"


class SourceAuthority(str, Enum):
    """Trust class of the upstream source.

    Distinct from RAGSource: a 'graph' retrieval from an untrusted corpus
    is still UNTRUSTED_EXTERNAL. The verdict engine's privacy filter uses
    this to decide whether a chunk may enter the ledger.
    """
    TRUSTED_INTERNAL = "trusted_internal"
    TRUSTED_PARTNER = "trusted_partner"
    UNTRUSTED_EXTERNAL = "untrusted_external"
    USER_PROVIDED = "user_provided"


_DEFAULT_CONFIDENCE_THRESHOLD = 0.5


@dataclass(frozen=True)
class RAGEvidenceNode:
    """Audit-grade wrapper carrying retrieval provenance into the verdict graph.

    Invariants (enforced in __post_init__):
    - fact_index, retrieval_rank >= 0
    - score, confidence_threshold in [0.0, 1.0]
    - source is RAGSource; authority is SourceAuthority
    - correlation_id is non-empty
    - content_hash is a 64-char lowercase hex SHA-256 digest

    Identity:
    - __hash__ and __eq__ are keyed on stable_id only
      (= SHA-256("{doc_id}|{correlation_id}")), so two retrievals of the
      same document in the same correlation are equal regardless of rank
      or score drift. This enables cross-process dedup.
    """

    fact_index: int
    doc_id: str
    source: RAGSource
    authority: SourceAuthority
    score: float
    retrieval_rank: int
    correlation_id: str
    content_hash: str                              # SHA-256(fact_text)
    is_sensitive: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD

    # ---------- construction ----------

    def __post_init__(self):
        if self.fact_index < 0:
            raise ValueError(f"fact_index must be >= 0, got {self.fact_index}")
        if self.retrieval_rank < 0:
            raise ValueError(f"retrieval_rank must be >= 0, got {self.retrieval_rank}")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}")
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be in [0.0, 1.0], got {self.confidence_threshold}"
            )
        if not isinstance(self.source, RAGSource):
            raise ValueError(f"source must be RAGSource, got {self.source!r}")
        if not isinstance(self.authority, SourceAuthority):
            raise ValueError(f"authority must be SourceAuthority, got {self.authority!r}")
        if not self.correlation_id:
            raise ValueError("correlation_id is required for audit traceability")
        if (
            len(self.content_hash) != 64
            or any(c not in "0123456789abcdef" for c in self.content_hash)
        ):
            raise ValueError(
                "content_hash must be a 64-char lowercase hex SHA-256 digest"
            )

    # ---------- identity (re-retrieval dedup) ----------

    @property
    def stable_id(self) -> str:
        """Deterministic identity: same (doc, correlation) -> same id,
        regardless of retrieval rank or score drift across calls."""
        return hashlib.sha256(
            f"{self.doc_id}|{self.correlation_id}".encode("utf-8")
        ).hexdigest()

    def __hash__(self) -> int:
        return int(self.stable_id, 16)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RAGEvidenceNode):
            return NotImplemented
        return self.stable_id == other.stable_id

    # ---------- classification (privacy filter integration) ----------

    def is_high_confidence(self) -> bool:
        return self.score >= self.confidence_threshold

    def is_audit_eligible(self) -> bool:
        """Evidence may enter the ledger only if it is high-confidence AND
        not flagged sensitive. Lets the privacy filter drop RAG chunks
        from UNTRUSTED_EXTERNAL before they reach EvidenceLedgerWriter.
        """
        return self.is_high_confidence() and not self.is_sensitive

    # ---------- serialization (deterministic, cross-process stable) ----------

    def to_ledger_provenance(self) -> Dict[str, Any]:
        """Stable dict payload for the ledger's retrieval_provenance field.

        Key order is fixed so dict equality and JSON serialization are
        deterministic across processes.
        """
        return {
            "fact_index": self.fact_index,
            "doc_id": self.doc_id,
            "source": self.source.value,
            "authority": self.authority.value,
            "score": self.score,
            "retrieval_rank": self.retrieval_rank,
            "correlation_id": self.correlation_id,
            "content_hash": self.content_hash,
            "is_sensitive": self.is_sensitive,
            "is_high_confidence": self.is_high_confidence(),
            "is_audit_eligible": self.is_audit_eligible(),
            "stable_id": self.stable_id,
            "metadata": dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"RAGEvidenceNode(idx={self.fact_index}, doc={self.doc_id!r}, "
            f"src={self.source.value}, auth={self.authority.value}, "
            f"score={self.score:.3f}, corr={self.correlation_id[:8]}...)"
        )

    # ---------- factory ----------

    @staticmethod
    def from_evidence_dict(
        evidence_dict: Dict[str, Any],
        *,
        fact_index: int,
        correlation_id: str,
        retrieval_rank: int,
        is_sensitive: bool = False,
        confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
        default_authority: Optional[SourceAuthority] = None,
    ) -> "RAGEvidenceNode":
        """Build a node from the dict format produced by the verdict engine's
        RAG retrieval loop. Centralizes the .get()/getattr() coercion and
        default-fallback logic so the verdict engine stays clean.

        Args:
            evidence_dict: the dict built at the RAG retrieval site, with
                keys: value (content text), source, score, metadata.
            fact_index: index assigned when this chunk is appended to the
                fact_texts list.
            correlation_id: pulled from GovernanceContextManager; required.
            retrieval_rank: 0-based rank within the RAG result set.
            is_sensitive: explicit sensitivity flag (default False; the
                absence of a sensitivity signal is fail-open).
            confidence_threshold: per-call override of the score cutoff
                used by is_high_confidence().
            default_authority: authority to assign when metadata does not
                carry one. If None, defaults to UNTRUSTED_EXTERNAL
                (fail-closed for trust class).
        """
        content_text = str(evidence_dict.get("value", "") or "")
        metadata = dict(evidence_dict.get("metadata", {}) or {})

        raw_source = evidence_dict.get("source") or metadata.get("source") or "rag"
        try:
            source = RAGSource(raw_source)
        except ValueError:
            source = RAGSource.RAG

        raw_authority = metadata.get("authority")
        if raw_authority is not None:
            try:
                authority = SourceAuthority(raw_authority)
            except ValueError:
                authority = default_authority or SourceAuthority.UNTRUSTED_EXTERNAL
        else:
            authority = default_authority or SourceAuthority.UNTRUSTED_EXTERNAL

        doc_id = str(
            metadata.get("doc_id")
            or evidence_dict.get("doc_id")
            or ""
        )
        score = float(evidence_dict.get("score", 0.0))
        content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

        return RAGEvidenceNode(
            fact_index=fact_index,
            doc_id=doc_id,
            source=source,
            authority=authority,
            score=score,
            retrieval_rank=retrieval_rank,
            correlation_id=correlation_id,
            content_hash=content_hash,
            is_sensitive=is_sensitive,
            metadata=metadata,
            confidence_threshold=confidence_threshold,
        )

"""Canonical output contract for specialized legal ingestion adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping


class IngestionContractError(ValueError):
    """Raised when an adapter emits an unsafe or incomplete contract."""


def sha256_text(text: str) -> str:
    if not isinstance(text, str) or not text:
        raise IngestionContractError("text must be a non-empty string")
    return sha256(text.encode("utf-8")).hexdigest()


def _require_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise IngestionContractError(f"{field_name} must be a non-empty trimmed string")
    return value


def _require_provenance(provenance: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(provenance, Mapping):
        raise IngestionContractError("provenance must be a mapping")
    required = ("source", "source_hash", "correlation_id")
    missing = [key for key in required if not provenance.get(key)]
    if missing:
        raise IngestionContractError(
            f"provenance is missing required fields: {', '.join(missing)}"
        )
    return dict(provenance)


@dataclass(frozen=True, slots=True)
class IngestionDocument:
    """Normalized source document emitted by a specialized adapter."""

    document_id: str
    source_uri: str
    text: str
    provenance: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_identifier(self.document_id, "document_id")
        _require_identifier(self.source_uri, "source_uri")
        if not isinstance(self.text, str) or not self.text.strip():
            raise IngestionContractError("text must contain non-whitespace content")
        _require_provenance(self.provenance)
        if self.provenance["source_hash"] != sha256_text(self.text):
            raise IngestionContractError("source_hash does not match document text")


@dataclass(frozen=True, slots=True)
class SemanticFact:
    """A typed semantic assertion extracted from a source document."""

    fact_id: str
    subject_id: str
    predicate: str
    object_id: str
    evidence_text: str
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.fact_id, "fact_id"),
            (self.subject_id, "subject_id"),
            (self.predicate, "predicate"),
            (self.object_id, "object_id"),
        ):
            _require_identifier(value, field_name)
        if not isinstance(self.evidence_text, str) or not self.evidence_text.strip():
            raise IngestionContractError("evidence_text must contain content")
        _require_provenance(self.provenance)


@dataclass(frozen=True, slots=True)
class RelationshipFact:
    """A graph relationship emitted by an adapter before governed mutation."""

    relationship_id: str
    source_id: str
    relationship_type: str
    target_id: str
    properties: Mapping[str, Any]
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.relationship_id, "relationship_id"),
            (self.source_id, "source_id"),
            (self.relationship_type, "relationship_type"),
            (self.target_id, "target_id"),
        ):
            _require_identifier(value, field_name)
        if not isinstance(self.properties, Mapping):
            raise IngestionContractError("properties must be a mapping")
        _require_provenance(self.provenance)


@dataclass(frozen=True, slots=True)
class CanonicalIngestionBatch:
    """Complete adapter output accepted by the governance kernel."""

    documents: tuple[IngestionDocument, ...]
    facts: tuple[SemanticFact, ...] = ()
    relationships: tuple[RelationshipFact, ...] = ()

    def __post_init__(self) -> None:
        document_ids = [document.document_id for document in self.documents]
        fact_ids = [fact.fact_id for fact in self.facts]
        relationship_ids = [item.relationship_id for item in self.relationships]
        for values, name in (
            (document_ids, "document"),
            (fact_ids, "fact"),
            (relationship_ids, "relationship"),
        ):
            if len(values) != len(set(values)):
                raise IngestionContractError(f"duplicate {name} identifiers in batch")

        document_hashes = {document.provenance["source_hash"] for document in self.documents}
        for item in (*self.facts, *self.relationships):
            if item.provenance["source_hash"] not in document_hashes:
                raise IngestionContractError(
                    "fact provenance does not reference a document in the batch"
                )
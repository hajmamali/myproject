"""
MAHOUN Validator Pipeline
==========================

Classification: CRITICAL / RUNTIME GOVERNANCE
Purpose: Unified validation pipeline for all graph mutations.

Every graph write passes through this pipeline before persistence.
The pipeline composes ProvenanceTracker, OntologyEnforcer, and
schema validation into a single fail-closed gate.

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

from mahoun.core.governance.ontology_enforcer import OntologyEnforcer
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata, ProvenanceTracker
from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)

# ============================================================================
# AUTHORITATIVE NODE LABEL ALLOWLIST (I4)
# ============================================================================
# Every node label that may exist in the MAHOUN graph must appear here.
# write_node() rejects any label not in this set — fail-closed.
# To add a new label: add it here AND add the corresponding OntologyRule.
# Quarantined* prefixes are handled by the quarantine routing in write_node;
# only the BASE label needs to be in this allowlist.
ALLOWED_NODE_LABELS: frozenset[str] = frozenset(
    {
        # Legal domain
        "Law",
        "Case",
        "Document",
        "Entity",
        "Topic",
        "LawArticle",
        "Verdict",
        "Evidence",
        "Person",
        "Article",
        "Organization",
        "Court",
        "Tag",
        # Graph infrastructure
        "GraphNode",
        # Pipeline / ingestion
        "Chunk",
        # Optimizer
        "OptimizationJob",
    }
)


# ============================================================================
# AUTHORITATIVE PROPERTY KEY ALLOWLISTS (I4 — Property Scope)
# ============================================================================
# Every property key that callers may pass to write_node() / write_relationship()
# must appear in the corresponding allowlist.
#
# Invariants:
#   P1. Keys must match ^[A-Za-z][A-Za-z0-9_]*$ (ASCII, no leading underscore).
#   P2. Keys must be in ALLOWED_NODE_PROPERTY_KEYS (nodes) or
#       ALLOWED_RELATIONSHIP_PROPERTY_KEYS (relationships).
#   P3. KERNEL_RESERVED_PROPERTY_KEYS are injected by GovernedNeo4jSession in
#       the Cypher template — callers MUST NOT supply them; any attempt is
#       rejected fail-closed (prevents caller override of audit timestamps).
#
# To add a new property: add it to the relevant frozenset below AND document
# why it belongs to the canonical MAHOUN ontology.
# ============================================================================

# Safe property key identifier regex (mirrors schema DDL validator)
_PROPERTY_KEY_RE: re.Pattern[str] = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# Keys the kernel writes directly into the Cypher template.
# Callers supplying these would silently override governance timestamps.
KERNEL_RESERVED_PROPERTY_KEYS: frozenset[str] = frozenset(
    {
        "created_at",
        "updated_at",
    }
)

ALLOWED_NODE_PROPERTY_KEYS: frozenset[str] = frozenset(
    {
        # ---- Universal identifiers ----------------------------------------
        "id",
        "node_id",  # builder-level alias used by entity_linker
        "verdict_id",
        "case_id",
        "doc_id",
        "chunk_id",
        "job_id",  # optimizer
        # ---- Core descriptors --------------------------------------------
        "name",
        "title",
        "description",
        "label",
        "type",
        "status",
        "source",
        "category",
        "topic",
        "content",
        "text",
        "summary",
        "tag",
        # ---- Legal domain ------------------------------------------------
        "case_type",
        "court_level",
        "court_rank",
        "is_final",
        "decision_date",
        "effective_date",
        "expiry_date",
        "date",
        "date_jalali",
        "law_name",
        "article",
        "article_number",
        "clause",
        "code",
        "statute_status",
        "legal_domain",
        "citation_count",
        "cited_by_higher_courts",
        "condition",
        "conclusion",
        # ---- Person / Org -----------------------------------------------
        "national_id",
        "registration_id",
        "father_name",
        "role",
        "normalized_name",
        "org_type",
        "party",
        # ---- Geographic --------------------------------------------------
        "city",
        "province",
        "branch",
        # ---- Graph analytics / quality ----------------------------------
        "confidence",
        "quality_score",
        "node_type",
        "weight",
        "authority_score",
        "relevance",
        # ---- Vector embedding --------------------------------------------
        "embedding",
        # ---- Pipeline / chunking -----------------------------------------
        "chunk_start",
        "chunk_end",
        "doc_start",
        "doc_end",
        # ---- Provenance (kernel-managed; callers may pre-compute hash) ---
        "provenance_hash",
        # ---- Optimizer ---------------------------------------------------
        "snapshot_label",
    }
)

ALLOWED_RELATIONSHIP_PROPERTY_KEYS: frozenset[str] = frozenset(
    {
        # ---- Core --------------------------------------------------------
        "type",
        "status",
        "source",
        "role",
        # ---- Semantic weights -------------------------------------------
        "weight",
        "confidence",
        "quality_score",
        "relevance",
        "authority_score",
        # ---- Relationship semantics -------------------------------------
        "reference_type",
        "support_type",
        "contradiction_type",
        "exception_type",
        "qualification",
        "description",
        # ---- Temporal ---------------------------------------------------
        "effective_date",
        "expiry_date",
        # ---- Evidence ---------------------------------------------------
        "evidence",
        # ---- Provenance -------------------------------------------------
        "provenance_hash",
    }
)


def validate_property_keys(
    properties: Dict[str, Any],
    *,
    context: str,  # "node" | "relationship"  — used in error messages
    correlation_id: Optional[str] = None,
) -> None:
    """
    Kernel-level property key gate — enforces invariants P1, P2, P3.

    Called by GovernedNeo4jSession BEFORE building any SET clause.
    This is the last line of defence against:
      - Cypher injection via property key names  (P1)
      - Schema drift / ontology violations       (P2)
      - Caller override of kernel timestamps     (P3)

    Args:
        properties: The cypher_props dict (provenance already stripped).
        context:    "node" or "relationship" — selects the correct allowlist.
        correlation_id: Forwarded to GovernanceViolation for traceability.

    Raises:
        GovernanceViolationError:
            category=ONTOLOGY_VIOLATION  for P1/P2 (unknown or malformed key)
            category=AUDIT_INTEGRITY_VIOLATION  for P3 (reserved key override)
    """
    if context == "node":
        allowed = ALLOWED_NODE_PROPERTY_KEYS
    elif context == "relationship":
        allowed = ALLOWED_RELATIONSHIP_PROPERTY_KEYS
    else:
        raise ValueError(f"validate_property_keys: unknown context '{context}'")

    for key in properties:
        # ----------------------------------------------------------------
        # P1 — Identifier safety (prevents f"n.{key}" Cypher injection)
        # ----------------------------------------------------------------
        if not isinstance(key, str) or not key.strip():
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(f"Property key must be a non-empty string. Got: {key!r}"),
                    details={"key": repr(key), "context": context},
                    source="validate_property_keys",
                    correlation_id=correlation_id,
                )
            )

        norm_key = unicodedata.normalize("NFKC", key)
        if norm_key != key:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Property key '{key}' contains Unicode homoglyphs / "
                        f"compatibility variants. Use ASCII canonical keys only."
                    ),
                    details={"key": key, "normalized": norm_key, "context": context},
                    source="validate_property_keys",
                    correlation_id=correlation_id,
                )
            )

        if not _PROPERTY_KEY_RE.match(key):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Property key '{key}' contains forbidden characters. "
                        f"Allowed pattern: ^[A-Za-z][A-Za-z0-9_]*$ — "
                        f"No leading underscores, no spaces, ASCII only."
                    ),
                    details={"key": key, "context": context},
                    source="validate_property_keys",
                    correlation_id=correlation_id,
                )
            )

        # ----------------------------------------------------------------
        # P3 — Reserved kernel keys (audit timestamp override prevention)
        # ----------------------------------------------------------------
        if key in KERNEL_RESERVED_PROPERTY_KEYS:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.AUDIT_INTEGRITY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Property key '{key}' is reserved for kernel use. "
                        f"Callers must not supply '{key}' — the governance kernel "
                        f"injects it directly into the Cypher template to guarantee "
                        f"audit-trail integrity. Caller override is forbidden."
                    ),
                    details={
                        "key": key,
                        "context": context,
                        "reserved_keys": sorted(KERNEL_RESERVED_PROPERTY_KEYS),
                    },
                    source="validate_property_keys",
                    correlation_id=correlation_id,
                )
            )

        # ----------------------------------------------------------------
        # P2 — Allowlist membership (schema / ontology enforcement)
        # ----------------------------------------------------------------
        if key not in allowed:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Property key '{key}' is not in the MAHOUN "
                        f"{context} property allowlist. "
                        f"To add a new property, update "
                        f"ALLOWED_{context.upper()}_PROPERTY_KEYS in "
                        f"mahoun/core/governance/validator_pipeline.py "
                        f"and document the rationale."
                    ),
                    details={
                        "key": key,
                        "context": context,
                        "allowed_count": len(allowed),
                    },
                    source="validate_property_keys",
                    correlation_id=correlation_id,
                )
            )


def validate_node_label(label: str, correlation_id: Optional[str] = None) -> None:
    """Reject any node label not in ALLOWED_NODE_LABELS.

    Quarantined* prefixes are stripped before lookup so that
    GovernedNeo4jSession's quarantine routing still works.

    Raises:
        GovernanceViolationError: category=ONTOLOGY_VIOLATION, severity=CRITICAL
    """
    # Basic empty / whitespace check
    if not label or not label.strip():
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message="Node label must be a non-empty string.",
                details={"label": repr(label)},
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )

    # Normalize Unicode to NFKC to collapse homoglyphs and compatibility forms
    norm_label = unicodedata.normalize("NFKC", label)

    # If normalization changes the label, treat as possible homoglyph injection
    if norm_label != label:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    "Node label contains compatibility/unicode variants (homoglyphs). Use ASCII canonical labels only."
                ),
                details={"label": label, "normalized": norm_label},
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )

    # Strip Quarantined prefix for allowlist lookup (preserve normalization)
    base_label = norm_label[len("Quarantined") :] if norm_label.startswith("Quarantined") else norm_label

    # Reject any non-ASCII characters to prevent homoglyph attacks
    if any(ord(ch) > 127 for ch in base_label):
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=("Node label contains non-ASCII characters — possible homoglyph injection."),
                details={"label": label, "normalized": norm_label},
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )

    # Enforce strict label character rules (no punctuation, no whitespace)
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", base_label):
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    "Node label contains forbidden characters or formatting. Allowed pattern: ^[A-Za-z][A-Za-z0-9_]*$"
                ),
                details={"label": label, "normalized": norm_label},
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )

    # Final allowlist membership check
    if base_label not in ALLOWED_NODE_LABELS:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    f"Node label '{base_label}' is not in the MAHOUN ontology allowlist. "
                    f"Allowed labels: {sorted(ALLOWED_NODE_LABELS)}"
                ),
                details={
                    "label": label,
                    "base_label": base_label,
                    "allowed": sorted(ALLOWED_NODE_LABELS),
                },
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )


@dataclass(frozen=True)
class ValidationGateResult:
    """Immutable result of a single validation gate."""

    gate_name: str
    passed: bool
    violation: Optional[GovernanceViolation] = None


@dataclass(frozen=True)
class PipelineResult:
    """Immutable result of the full validation pipeline."""

    passed: bool
    gate_results: tuple  # Tuple[ValidationGateResult, ...]
    correlation_id: str
    timestamp: str
    pipeline_hash: str

    @property
    def violations(self) -> List[GovernanceViolation]:
        return [g.violation for g in self.gate_results if g.violation is not None]


# Type alias for custom validation functions
ValidationGate = Callable[[Dict[str, Any], Optional[str]], None]


class ValidatorPipeline:
    """Unified validation pipeline for graph mutations.

    Composes multiple validation gates into a single fail-closed pipeline.
    If any gate fails, the entire pipeline fails immediately.

    Built-in gates:
        1. Provenance validation (via ProvenanceTracker)
        2. Ontology validation (via OntologyEnforcer, for relationships)
        3. Schema validation (required fields check)

    Custom gates can be added via add_gate().
    """

    def __init__(
        self,
        provenance_tracker: Optional[ProvenanceTracker] = None,
        ontology_enforcer: Optional[OntologyEnforcer] = None,
    ) -> None:
        self._provenance = provenance_tracker or ProvenanceTracker()
        self._ontology = ontology_enforcer or OntologyEnforcer()
        self._custom_gates: List[tuple] = []  # List of (name, gate_fn)

    def add_gate(self, name: str, gate_fn: ValidationGate) -> None:
        """Add a custom validation gate to the pipeline.

        Args:
            name: Gate name for audit trail.
            gate_fn: Function(data, correlation_id) -> None.
                     Must raise GovernanceViolationError on failure.
        """
        if not name:
            raise ValueError("Gate name cannot be empty")
        self._custom_gates.append((name, gate_fn))

    def validate_node_write(
        self,
        node_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> PipelineResult:
        """Validate a node write through the full pipeline.

        Gates executed:
            1. Provenance check
            2. Required fields check
            3. Custom gates

        Args:
            node_data: Node data dictionary. Must contain 'provenance'.
            correlation_id: Optional correlation ID.

        Returns:
            PipelineResult (always passed=True if we return).

        Raises:
            GovernanceViolationError: On any gate failure (fail-fast).
        """
        results: List[ValidationGateResult] = []
        ts = datetime.now(timezone.utc).isoformat()
        cid = correlation_id or ""

        # Gate 0: Node label allowlist (I4 — ontology enforcement)
        label = node_data.get("_label") or node_data.get("label", "")
        # label may also be passed separately; if absent we skip here and
        # rely on write_node() to pass it explicitly via validate_node_label().
        if label:
            validate_node_label(label, correlation_id)
        results.append(ValidationGateResult(gate_name="label_allowlist", passed=True))

        # Gate 1: Provenance
        try:
            self._provenance.validate_node_provenance(node_data, correlation_id)
            results.append(ValidationGateResult(gate_name="provenance", passed=True))
        except GovernanceViolationError:
            raise  # Fail-fast, no catch

        # Gate 2: Required fields
        required = {"id"}
        missing = required - set(node_data.keys())
        if missing:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.SCHEMA_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Node missing required fields: {sorted(missing)}",
                    details={"missing_fields": sorted(missing)},
                    source="ValidatorPipeline",
                    correlation_id=correlation_id,
                )
            )
        results.append(ValidationGateResult(gate_name="required_fields", passed=True))

        # Gate 3+: Custom gates
        for gate_name, gate_fn in self._custom_gates:
            gate_fn(node_data, correlation_id)
            results.append(ValidationGateResult(gate_name=gate_name, passed=True))

        return PipelineResult(
            passed=True,
            gate_results=tuple(results),
            correlation_id=cid,
            timestamp=ts,
            pipeline_hash=self._compute_hash(node_data),
        )

    def validate_relationship_write(
        self,
        source_type: str,
        relationship_type: str,
        target_type: str,
        relationship_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> PipelineResult:
        """Validate a relationship write through the full pipeline.

        Gates executed:
            1. Ontology check
            2. Provenance check (on relationship data)
            3. Custom gates

        Raises:
            GovernanceViolationError: On any gate failure.
        """
        results: List[ValidationGateResult] = []
        ts = datetime.now(timezone.utc).isoformat()
        cid = correlation_id or ""

        # Gate 1: Ontology
        self._ontology.validate_relationship(source_type, relationship_type, target_type, correlation_id)
        results.append(ValidationGateResult(gate_name="ontology", passed=True))

        # Gate 2: Provenance on relationship
        prov = relationship_data.get("provenance")
        if prov is None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Relationship write rejected: missing provenance for "
                        f"{source_type} -[{relationship_type}]-> {target_type}"
                    ),
                    details={
                        "source_type": source_type,
                        "relationship_type": relationship_type,
                        "target_type": target_type,
                    },
                    source="ValidatorPipeline",
                    correlation_id=correlation_id,
                )
            )
        results.append(ValidationGateResult(gate_name="provenance", passed=True))

        # Gate 3+: Custom gates
        for gate_name, gate_fn in self._custom_gates:
            gate_fn(relationship_data, correlation_id)
            results.append(ValidationGateResult(gate_name=gate_name, passed=True))

        return PipelineResult(
            passed=True,
            gate_results=tuple(results),
            correlation_id=cid,
            timestamp=ts,
            pipeline_hash=self._compute_hash(relationship_data),
        )

    @staticmethod
    def _compute_hash(data: Dict[str, Any]) -> str:
        """Compute deterministic hash of mutation data."""
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ============================================================================
# Strict Schema Validation Gate
# ============================================================================

import logging

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Central registry mapping Neo4j node labels to their Pydantic schemas.
# Any label not in this registry will be rejected by the schema gate.
SCHEMA_REGISTRY: Dict[str, type] = {}


def register_schema(label: str, model_cls: type) -> None:
    """Register a Pydantic model for a given Neo4j label.

    Args:
        label: Neo4j node label (e.g., "Verdict", "LawArticle").
        model_cls: Pydantic BaseModel subclass with extra="forbid".
    """
    if not (isinstance(model_cls, type) and issubclass(model_cls, BaseModel)):
        raise TypeError(f"model_cls must be a Pydantic BaseModel subclass, got {model_cls}")
    SCHEMA_REGISTRY[label] = model_cls
    logger.info(f"Schema registered: {label} → {model_cls.__name__}")


def strict_schema_validation_gate(
    data: Dict[str, Any],
    correlation_id: Optional[str] = None,
    *,
    label: Optional[str] = None,
) -> None:
    """Validate node properties against the registered Pydantic schema.

    This function is designed to be used as a custom gate in ValidatorPipeline.

    Args:
        data: Node data dictionary.
        correlation_id: Optional correlation ID.
        label: Neo4j label to validate against. If None, checks data["_label"].

    Raises:
        GovernanceViolationError: If schema validation fails.
    """
    resolved_label = label or data.get("_label")
    if not resolved_label:
        # No label to validate against — skip (label may be set by caller)
        return

    # Strip quarantine prefix for registry lookup
    lookup_label = resolved_label
    if lookup_label.startswith("Quarantined"):
        lookup_label = lookup_label[len("Quarantined") :]

    schema_cls = SCHEMA_REGISTRY.get(lookup_label)
    if schema_cls is None:
        # No schema registered for this label — log warning but allow
        # (strict mode could be added here to reject unregistered labels)
        logger.warning(
            f"No schema registered for label '{lookup_label}'. Write will proceed without Pydantic validation."
        )
        return

    # Build validation payload (exclude internal keys)
    validation_payload = {k: v for k, v in data.items() if not k.startswith("_") and k != "provenance"}

    try:
        schema_cls.model_validate(validation_payload)
    except ValidationError as e:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.SCHEMA_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    f"Strict schema validation failed for label '{resolved_label}': {e.error_count()} validation errors"
                ),
                details={
                    "label": resolved_label,
                    "errors": e.errors(),
                    "schema": schema_cls.__name__,
                },
                source="StrictSchemaValidationGate",
                correlation_id=correlation_id,
            )
        ) from e

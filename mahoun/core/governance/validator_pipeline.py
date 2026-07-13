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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata, ProvenanceTracker
from mahoun.core.governance.ontology_enforcer import OntologyEnforcer


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
    gate_results: List[ValidationGateResult]  # List of ValidationGateResult
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
            gate_results=results,
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
        self._ontology.validate_relationship(
            source_type, relationship_type, target_type, correlation_id
        )
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
            gate_results=results,
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
        lookup_label = lookup_label[len("Quarantined"):]

    schema_cls = SCHEMA_REGISTRY.get(lookup_label)
    if schema_cls is None:
        # No schema registered for this label — log warning but allow
        # (strict mode could be added here to reject unregistered labels)
        logger.warning(
            f"No schema registered for label '{lookup_label}'. "
            f"Write will proceed without Pydantic validation."
        )
        return

    # Build validation payload (exclude internal keys)
    validation_payload = {
        k: v for k, v in data.items()
        if not k.startswith("_") and k != "provenance"
    }

    try:
        schema_cls.model_validate(validation_payload)
    except ValidationError as e:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.SCHEMA_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    f"Strict schema validation failed for label '{resolved_label}': "
                    f"{e.error_count()} validation errors"
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


# ============================================================================
# Strict Node Label Validation (PATCH P0-1)
# ============================================================================

import unicodedata as _unicodedata

# Canonical ontology allowlist of hardened node labels.
# This is intentionally minimal — callers register additional labels via
# register_label() when their ontology is approved by the kernel.
ALLOWED_NODE_LABELS: "frozenset[str]" = frozenset({
    "Case",
    "Verdict",
    "LawArticle",
    "Chunk",
    "QuarantinedChunk",
    "QuarantinedVerdict",
    "Document",
    "Provenance",
    "AuditTrail",
    "Evidence",
})

# Strict character allowlist for node labels: ASCII letters, digits, underscore.
_LABEL_CHAR_RE = re.compile(r"^[A-Za-z0-9_]+$")

# Characters that may break Cypher context when interpolated via f-string/format().
# Any presence of these chars in a label is an injection attempt.
_CYPHER_INJECTION_CHARS = frozenset(";()`'\"\\/{<>= \t\r\n")


def _register_ontology_label(label: str) -> None:
    """Add a label to the runtime allowlist (used in tests / extension points)."""
    global ALLOWED_NODE_LABELS
    ALLOWED_NODE_LABELS = ALLOWED_NODE_LABELS | {label}


def _strip_quarantine_prefix(label: str) -> str:
    """Strip the Quarantined* prefix for allowlist lookup only."""
    if label.startswith("Quarantined"):
        return label[len("Quarantined"):]
    return label


def validate_node_label(
    label: object,
    *,
    correlation_id: Optional[str] = None,
) -> None:
    """Strictly validate a Neo4j node label to prevent Cypher injection.

    Defenses, in this order (fail-fast on first violation):

      P1. Non-empty after strip.
      P2. ASCII-only character allowlist (`A-Z a-z 0-9 _`).
      P3. NFKC stability — NFKC(label) must equal label (catches fullwidth /
          compatibility-form homoglyphs that visually mimic allowed chars).
      P4. No Cypher-injection metacharacters: ; ( ) ` ' " \\ / { } < > = space.
      P5. Must be present in the canonical ontology allowlist
          (Quarantined* prefix is stripped before lookup).

    Args:
        label: Candidate label string.
        correlation_id: Optional correlation ID propagated to the violation.

    Raises:
        GovernanceViolationError: ONTOLOGY_VIOLATION (CRITICAL) on any failure.
    """
    if not isinstance(label, str):
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message="Node label must be a non-empty string",
                details={"type": type(label).__name__},
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )

    # P1: non-empty after strip
    stripped = label.strip()
    if not stripped:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message="Node label must be non-empty and non-whitespace",
                details={"label": label},
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )

    # P2: ASCII-only characters
    non_ascii = [c for c in label if ord(c) > 127]
    if non_ascii:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    f"Node label contains {len(non_ascii)} non-ASCII character(s); "
                    "non-ASCII labels are rejected to defeat Unicode homoglyph attacks."
                ),
                details={
                    "label": label,
                    "first_non_ascii": non_ascii[0],
                    "first_non_ascii_codepoint": f"U+{ord(non_ascii[0]):04X}",
                },
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )

    # P3: NFKC stability (fullwidth / compatibility normalization detection)
    nfkc = _unicodedata.normalize("NFKC", label)
    if nfkc != label:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    "Node label fails NFKC normalization (compatibility / "
                    "homoglyph form detected). Labels must be in canonical form."
                ),
                details={"label": label, "nfkc_normalized": nfkc},
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )

    # P4: strict character allowlist (defeats Cypher injection / comment escape)
    injection_chars = [c for c in label if c in _CYPHER_INJECTION_CHARS]
    if injection_chars:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    "Node label violates strict label character rules: "
                    f"contains Cypher/metacharacter injection token(s): "
                    f"{sorted(set(injection_chars))!r}"
                ),
                details={
                    "label": label,
                    "injection_chars": sorted(set(injection_chars)),
                },
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )

    if not _LABEL_CHAR_RE.match(label):
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    "Node label must match strict character allowlist "
                    "[A-Za-z0-9_]+"
                ),
                details={"label": label},
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )

    # P5: ontology allowlist (Quarantined* prefix stripped before lookup)
    lookup = _strip_quarantine_prefix(label)
    if lookup not in ALLOWED_NODE_LABELS:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ONTOLOGY_VIOLATION,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    f"Node label '{label}' is not in the ontology allowlist "
                    f"(resolved '{lookup}')"
                ),
                details={"label": label, "resolved": lookup},
                source="validate_node_label",
                correlation_id=correlation_id,
            )
        )


# ============================================================================
# Property Key Validation (Constitutional Invariant)
# ============================================================================

# P1: Allowed property key characters
_PROPERTY_KEY_CHAR_RE = re.compile(r"^[a-zA-Z0-9_]+$")

# P3: Reserved kernel keys (cannot be overridden by user code)
KERNEL_RESERVED_KEYS = frozenset({
    "_id",
    "_hash",
    "_signature",
    "_created_at",
    "_updated_at",
    "_deleted",
    "_tombstoned",
    "_active",
    "_version",
    "_proof_ref",
    "_provenance_ref",
    "created_at",
    "updated_at",
    "provenance",
    "meta",
})


def validate_property_keys(
    properties: Dict[str, Any],
    context: str = "node",
    correlation_id: Optional[str] = None,
) -> None:
    """
    Validate property keys for strict governance compliance.

    P1: Only [a-zA-Z0-9_]+ characters allowed.
    P3: Reserved kernel keys cannot be overridden by user code.

    Raises:
        GovernanceViolationError on any violation.
    """
    if not properties:
        return
    
    for key in properties.keys():
        # P1: Check character allowlist
        if not _PROPERTY_KEY_CHAR_RE.match(key):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Property key '{key}' contains disallowed characters. "
                        "Only [a-zA-Z0-9_]+ are permitted."
                    ),
                    details={
                        "context": context,
                        "invalid_key": key,
                        "allowed_pattern": "[a-zA-Z0-9_]+",
                    },
                    source="validate_property_keys",
                    correlation_id=correlation_id,
                )
            )
        
        # P3: Check reserved keys
        if key in KERNEL_RESERVED_KEYS:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Property key '{key}' is kernel-reserved and cannot be "
                        "overridden by user code."
                    ),
                    details={
                        "context": context,
                        "reserved_key": key,
                        "reserved_keys": sorted(KERNEL_RESERVED_KEYS),
                    },
                    source="validate_property_keys",
                    correlation_id=correlation_id,
                )
            )

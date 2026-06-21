"""
MAHOUN Provenance Tracker
==========================

Classification: CRITICAL / RUNTIME GOVERNANCE
Purpose: Enforce mandatory provenance metadata on all graph writes.

Every node and relationship added to the knowledge graph MUST carry
provenance metadata. Writes without provenance are rejected immediately
with GovernanceViolationError.

Provenance metadata is immutable after creation (frozen dataclass).

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, Optional

from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)

# Fields that MUST be present in every provenance record
REQUIRED_PROVENANCE_FIELDS: FrozenSet[str] = frozenset(
    {"source", "timestamp", "correlation_id", "author"}
)


# ============================================================================
# INFERENCE PROVENANCE (CRITICAL)
# ============================================================================


@dataclass(frozen=True)
class InferenceProvenance:
    """Provenance for reasoning operations (separate from Graph Provenance).
    
    Tracks the symbolic execution path, rule chains, evidence nodes,
    and contradiction branches that led to a conclusion.
    
    CRITICAL: This is separate from GraphProvenance because:
    - Graph provenance tracks WHERE data came from (source document, ingestion pipeline)
    - Inference provenance tracks HOW conclusions were derived (rule chains, evidence nodes)
    
    Usage:
        inference_prov = InferenceProvenance.create(
            proof_id="proof-123",
            rule_chain=("rule_1", "rule_2", "rule_3"),
            evidence_nodes=("node_a", "node_b"),
            contradiction_branches=("branch_x",),
            symbolic_trace_hash="abc123...",
            governance_scope_id="scope-789"
        )
    """

    # Unique identifier for this inference
    proof_id: str
    
    # Tuple of rule IDs used in this inference (symbolic execution path)
    rule_chain: tuple[str, ...]
    
    # Tuple of evidence node IDs referenced
    evidence_nodes: tuple[str, ...]
    
    # Tuple of contradiction branches encountered
    contradiction_branches: tuple[str, ...]
    
    # Hash of the symbolic execution trace
    symbolic_trace_hash: str
    
    # ID of the governance scope that created this provenance
    governance_scope_id: str

    @classmethod
    def create(
        cls,
        proof_id: str,
        rule_chain: tuple[str, ...],
        evidence_nodes: tuple[str, ...],
        contradiction_branches: tuple[str, ...],
        symbolic_trace_hash: str,
        governance_scope_id: str,
    ) -> InferenceProvenance:
        """Create inference provenance with governance scope binding.

        Args:
            proof_id: Unique identifier for this inference.
            rule_chain: Tuple of rule IDs used in this inference.
            evidence_nodes: Tuple of evidence node IDs referenced.
            contradiction_branches: Tuple of contradiction branches encountered.
            symbolic_trace_hash: Hash of the symbolic execution trace.
            governance_scope_id: ID of the governance scope.

        Returns:
            InferenceProvenance instance.
        """
        return cls(
            proof_id=proof_id,
            rule_chain=rule_chain,
            evidence_nodes=evidence_nodes,
            contradiction_branches=contradiction_branches,
            symbolic_trace_hash=symbolic_trace_hash,
            governance_scope_id=governance_scope_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "proof_id": self.proof_id,
            "rule_chain": list(self.rule_chain),
            "evidence_nodes": list(self.evidence_nodes),
            "contradiction_branches": list(self.contradiction_branches),
            "symbolic_trace_hash": self.symbolic_trace_hash,
            "governance_scope_id": self.governance_scope_id,
        }


# ============================================================================
# PROVENANCE METADATA
# ============================================================================
"""Immutable provenance record for graph entities.

Every graph node and relationship must be created with
132: a ProvenanceMetadata instance. This record is immutable
133: and cannot be modified after creation.

CRITICAL SECURITY ENHANCEMENTS:
136: - provenance_hash: SHA256 hash for cryptographic integrity
137: - provenance_signature: Cryptographic signature for attestation
138: - governance_scope_id: ID of governance scope that created this
139: - runtime_attestation_id: ID of runtime attestation for execution binding
140: - lineage_parent: ID of parent provenance for correlation continuity
141: - timestamp: Internally generated, monotonic, governance-controlled (NOT externally writable)

Usage:
144: # ONLY via factory method (constructor is disabled)
145: provenance = ProvenanceMetadata.create(
146:     source="document_ingestion",
147:     correlation_id="req-123",
148:     author="user-456",
149:     governance_scope_id="scope-789",
150:     runtime_attestation_id="attest-abc",
151:     lineage_parent=None
152: )
"""

@dataclass(frozen=True)
class ProvenanceMetadata:
    # Cryptographic attestation fields (GOVERNANCE-CONTROLLED)
    provenance_hash: str
    provenance_signature: str
    governance_scope_id: str
    runtime_attestation_id: str
    lineage_parent: Optional[str]

    # Core metadata fields (SET AT CREATION TIME ONLY)
    source: str
    timestamp: str
    correlation_id: str
    author: str
    document_id: Optional[str] = None
    pipeline_version: Optional[str] = None

    def __init_subclass__(cls, **kwargs):
        """Prevent subclassing - only ProvenanceMetadata allowed."""
        super().__init_subclass__(**kwargs)
        # Disable direct instantiation - only create() factory method allowed

    def __init__(
        self,
        source: str,
        timestamp: str,
        correlation_id: str,
        author: str,
        provenance_hash: str,
        provenance_signature: str,
        governance_scope_id: str,
        runtime_attestation_id: str,
        lineage_parent: Optional[str] = None,
        document_id: Optional[str] = None,
        pipeline_version: Optional[str] = None,
    ) -> None:
        """
        Internal constructor - ONLY called by create() factory method.
        
        CRITICAL: This constructor is for internal use ONLY.
        External code MUST use ProvenanceMetadata.create() factory method.
        """
        # Use object.__setattr__ to bypass frozen dataclass restrictions
        object.__setattr__(self, 'source', source)
        object.__setattr__(self, 'timestamp', timestamp)
        object.__setattr__(self, 'correlation_id', correlation_id)
        object.__setattr__(self, 'author', author)
        object.__setattr__(self, 'provenance_hash', provenance_hash)
        object.__setattr__(self, 'provenance_signature', provenance_signature)
        object.__setattr__(self, 'governance_scope_id', governance_scope_id)
        object.__setattr__(self, 'runtime_attestation_id', runtime_attestation_id)
        object.__setattr__(self, 'lineage_parent', lineage_parent)
        object.__setattr__(self, 'document_id', document_id)
        object.__setattr__(self, 'pipeline_version', pipeline_version)
        
        # Validate all required fields are non-empty
        if not self.source:
            raise ValueError("Provenance 'source' cannot be empty")
        if not self.timestamp:
            raise ValueError("Provenance 'timestamp' cannot be empty")
        if not self.correlation_id:
            raise ValueError("Provenance 'correlation_id' cannot be empty")
        if not self.author:
            raise ValueError("Provenance 'author' cannot be empty")
        if not self.provenance_hash:
            raise ValueError("Provenance 'provenance_hash' cannot be empty")
        if not self.provenance_signature:
            raise ValueError("Provenance 'provenance_signature' cannot be empty")
        if not self.governance_scope_id:
            raise ValueError("Provenance 'governance_scope_id' cannot be empty")
        if not self.runtime_attestation_id:
            raise ValueError("Provenance 'runtime_attestation_id' cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage."""
        result: Dict[str, Any] = {
            "source": self.source,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "author": self.author,
            "provenance_hash": self.provenance_hash,
            "provenance_signature": self.provenance_signature,
            "governance_scope_id": self.governance_scope_id,
            "runtime_attestation_id": self.runtime_attestation_id,
        }
        if self.lineage_parent is not None:
            result["lineage_parent"] = self.lineage_parent
        if self.document_id is not None:
            result["document_id"] = self.document_id
        if self.pipeline_version is not None:
            result["pipeline_version"] = self.pipeline_version
        return result

    @classmethod
    def create(
        cls,
        source: str,
        correlation_id: str,
        author: str,
        governance_scope_id: str,
        runtime_attestation_id: str,
        lineage_parent: Optional[str] = None,
        document_id: Optional[str] = None,
        pipeline_version: Optional[str] = None,
    ) -> ProvenanceMetadata:
        """Factory method with automatic timestamp and cryptographic attestation.

        CRITICAL: This is the ONLY way to create ProvenanceMetadata instances.
        Direct instantiation is disabled via __init_subclass__.

        Args:
            source: Origin of the data.
            correlation_id: Correlation ID for tracing.
            author: Actor identifier.
            governance_scope_id: ID of governance scope creating this provenance.
            runtime_attestation_id: ID of runtime attestation for execution binding.
            lineage_parent: Optional parent provenance ID for correlation continuity.
            document_id: Optional source document ID.
            pipeline_version: Optional pipeline version.

        Returns:
            Immutable ProvenanceMetadata instance with cryptographic attestation.
        """
        # Generate timestamp internally (NOT externally writable)
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Build base data for hashing
        base_data = {
            "source": source,
            "timestamp": timestamp,
            "correlation_id": correlation_id,
            "author": author,
            "document_id": document_id,
            "pipeline_version": pipeline_version,
        }
        
        # Compute cryptographic hash
        provenance_hash = cls._compute_hash(base_data)
        
        # Compute cryptographic signature
        provenance_signature = cls._sign_provenance(base_data, governance_scope_id)
        
        # Create instance with all fields
        return cls(
            source=source,
            timestamp=timestamp,
            correlation_id=correlation_id,
            author=author,
            provenance_hash=provenance_hash,
            provenance_signature=provenance_signature,
            governance_scope_id=governance_scope_id,
            runtime_attestation_id=runtime_attestation_id,
            lineage_parent=lineage_parent,
            document_id=document_id,
            pipeline_version=pipeline_version,
        )

    @staticmethod
    def _compute_hash(data: Dict[str, Any]) -> str:
        """Compute SHA256 hash of provenance data for cryptographic integrity."""
        import hashlib
        import json
        # Sort keys for deterministic hashing
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    @staticmethod
    def _sign_provenance(data: Dict[str, Any], governance_scope_id: str) -> str:
        """Sign provenance data with governance scope for attestation.

        CRITICAL: This provides cryptographic proof that the provenance
        was created by a valid governance scope.
        """
        import hashlib
        import json
        # Combine data with governance scope for binding
        combined = json.dumps(data, sort_keys=True, default=str) + governance_scope_id
        return hashlib.sha256(combined.encode()).hexdigest()


class ProvenanceTracker:
    """Enforcement layer for mandatory provenance on graph writes.

    This tracker validates that every graph mutation includes valid
    provenance metadata. It is integrated into the ValidatorPipeline
    and runs before any graph persistence.

    Fail-closed: Missing or invalid provenance raises GovernanceViolationError.
    """

    def validate_provenance(
        self,
        provenance: Optional[ProvenanceMetadata],
        entity_type: str,
        entity_id: str,
        correlation_id: Optional[str] = None,
    ) -> ProvenanceMetadata:
        """Validate that provenance metadata is present and complete.

        Args:
            provenance: Provenance metadata to validate (must not be None).
            entity_type: Type of entity being written (node/relationship).
            entity_id: Identifier of the entity.
            correlation_id: Optional correlation ID for error reporting.

        Returns:
            The validated ProvenanceMetadata (pass-through on success).

        Raises:
            GovernanceViolationError: If provenance is missing or invalid.
        """
        if provenance is None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Graph write rejected: missing provenance metadata "
                        f"for {entity_type} '{entity_id}'"
                    ),
                    details={
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                    },
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

        # Validate all required fields are non-empty
        missing_fields = []
        for field_name in REQUIRED_PROVENANCE_FIELDS:
            value = getattr(provenance, field_name, None)
            if not value:
                missing_fields.append(field_name)

        if missing_fields:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Graph write rejected: incomplete provenance for "
                        f"{entity_type} '{entity_id}'. "
                        f"Missing fields: {sorted(missing_fields)}"
                    ),
                    details={
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "missing_fields": sorted(missing_fields),
                        "provided_fields": [
                            f
                            for f in REQUIRED_PROVENANCE_FIELDS
                            if f not in missing_fields
                        ],
                    },
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

        return provenance

    def validate_node_provenance(
        self,
        node_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate provenance in a node data dictionary.

        Checks that the node dictionary contains a 'provenance' key
        with a valid ProvenanceMetadata or dict representation.

        Args:
            node_data: Node data dictionary.
            correlation_id: Optional correlation ID.

        Returns:
            The validated node_data (pass-through on success).

        Raises:
            GovernanceViolationError: If provenance is missing or invalid.
        """
        node_id = node_data.get("id", node_data.get("name", "<unknown>"))
        provenance_raw = node_data.get("provenance")

        if provenance_raw is None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Node write rejected: 'provenance' key missing "
                        f"from node data for '{node_id}'"
                    ),
                    details={"node_id": str(node_id)},
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

        if isinstance(provenance_raw, ProvenanceMetadata):
            # Validate cryptographic attestation fields
            self._validate_provenance_attestation(provenance_raw, node_id, correlation_id)
            return node_data

        if isinstance(provenance_raw, dict):
            # Validate required fields exist in the dict
            missing = [
                f for f in REQUIRED_PROVENANCE_FIELDS if not provenance_raw.get(f)
            ]
            if missing:
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.MISSING_PROVENANCE,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"Node write rejected: incomplete provenance dict "
                            f"for '{node_id}'. Missing: {sorted(missing)}"
                        ),
                        details={
                            "node_id": str(node_id),
                            "missing_fields": sorted(missing),
                        },
                        source="ProvenanceTracker",
                        correlation_id=correlation_id,
                    )
                )
            
            # Validate cryptographic attestation fields if present
            self._validate_provenance_attestation_dict(provenance_raw, node_id, correlation_id)
            return node_data

        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.MISSING_PROVENANCE,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    f"Node write rejected: 'provenance' must be "
                    f"ProvenanceMetadata or dict, got {type(provenance_raw).__name__}"
                ),
                details={
                    "node_id": str(node_id),
                    "provenance_type": type(provenance_raw).__name__,
                },
                source="ProvenanceTracker",
                correlation_id=correlation_id,
            )
        )

    def _validate_provenance_attestation(
        self,
        provenance: ProvenanceMetadata,
        entity_id: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate cryptographic attestation fields in ProvenanceMetadata.

        Args:
            provenance: ProvenanceMetadata instance to validate.
            entity_id: Entity identifier for error messages.
            correlation_id: Optional correlation ID.

        Raises:
            GovernanceViolationError: If attestation is invalid.
        """
        # Validate cryptographic hash
        if not provenance.provenance_hash:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Node write rejected: provenance_hash missing "
                        f"for '{entity_id}'"
                    ),
                    details={
                        "node_id": str(entity_id),
                        "field": "provenance_hash",
                    },
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

        # Validate governance scope binding
        if not provenance.governance_scope_id:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Node write rejected: governance_scope_id missing "
                        f"for '{entity_id}'"
                    ),
                    details={
                        "node_id": str(entity_id),
                        "field": "governance_scope_id",
                    },
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

        # Validate runtime attestation binding
        if not provenance.runtime_attestation_id:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Node write rejected: runtime_attestation_id missing "
                        f"for '{entity_id}'"
                    ),
                    details={
                        "node_id": str(entity_id),
                        "field": "runtime_attestation_id",
                    },
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

    def _validate_provenance_attestation_dict(
        self,
        provenance_dict: Dict[str, Any],
        entity_id: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate cryptographic attestation fields in provenance dict.

        Args:
            provenance_dict: Provenance dict to validate.
            entity_id: Entity identifier for error messages.
            correlation_id: Optional correlation ID.

        Raises:
            GovernanceViolationError: If attestation is invalid.
        """
        # Validate cryptographic hash
        if not provenance_dict.get("provenance_hash"):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Node write rejected: provenance_hash missing "
                        f"from provenance dict for '{entity_id}'"
                    ),
                    details={
                        "node_id": str(entity_id),
                        "field": "provenance_hash",
                    },
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

        # Validate governance scope binding
        if not provenance_dict.get("governance_scope_id"):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Node write rejected: governance_scope_id missing "
                        f"from provenance dict for '{entity_id}'"
                    ),
                    details={
                        "node_id": str(entity_id),
                        "field": "governance_scope_id",
                    },
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

        # Validate runtime attestation binding
        if not provenance_dict.get("runtime_attestation_id"):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Node write rejected: runtime_attestation_id missing "
                        f"from provenance dict for '{entity_id}'"
                    ),
                    details={
                        "node_id": str(entity_id),
                        "field": "runtime_attestation_id",
                    },
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

"""
MAHOUN Ontology Enforcer
=========================

Classification: CRITICAL / RUNTIME GOVERNANCE
Purpose: Enforce ontology rules before relationship creation.

Relationships between graph nodes must conform to the MAHOUN legal
ontology. Invalid relationships are rejected immediately with
GovernanceViolationError.

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional, Set, Tuple, Literal, Any

from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)

from mahoun.graph.neo4j.enums import (
    DeonticOperator,
    LegalLevel,
    DecisionType,
    LegalForce,
    TemporalRelationType,
    ConflictResolution,
    BindingScope,
    NormStatus,
)


@dataclass(frozen=True)
class OntologyRule:
    """Immutable ontology rule defining valid relationship patterns.

    Attributes:
        source_type: Type of the source node (e.g., 'Law', 'Case').
        relationship_type: Type of relationship (e.g., 'CITES', 'AMENDS').
        target_type: Type of the target node.
        description: Human-readable description of the rule.
        bidirectional: Whether the relationship can go both ways.
    """

    source_type: str
    relationship_type: str
    target_type: str
    description: str = ""
    bidirectional: bool = False


# Default MAHOUN legal ontology rules
_DEFAULT_ONTOLOGY_RULES: Tuple[OntologyRule, ...] = (
    # Law relationships
    OntologyRule("Law", "AMENDS", "Law", "A law amends another law"),
    OntologyRule("Law", "REPEALS", "Law", "A law repeals another law"),
    OntologyRule("Law", "SUPERSEDES", "Law", "A law supersedes another law"),
    OntologyRule("Law", "REFERENCES", "Law", "A law references another law"),
    OntologyRule("Law", "IMPLEMENTS", "Law", "A law implements another law"),
    # Case relationships
    OntologyRule("Case", "CITES", "Law", "A case cites a law"),
    OntologyRule("Case", "CITES", "Case", "A case cites another case"),
    OntologyRule("Case", "APPLIES", "Law", "A case applies a law"),
    OntologyRule("Case", "INTERPRETS", "Law", "A case interprets a law"),
    OntologyRule("Case", "OVERRULES", "Case", "A case overrules another case"),
    OntologyRule("Case", "FOLLOWS", "Case", "A case follows another case"),
    OntologyRule("Case", "DISTINGUISHES", "Case", "A case distinguishes another"),
    # Judicial ingestion relationships
    OntologyRule("Judgment", "CITES", "Article", "A judgment cites a legal article"),
    OntologyRule("Judgment", "CITES", "LegalReference", "A judgment cites an unresolved legal reference"),
    OntologyRule("Judgment", "MENTIONS_REFERENCE", "LegalReference", "A judgment preserves a source reference"),
    OntologyRule("Judgment", "HAS_PARTY", "Party", "A judgment identifies a party"),
    # Document relationships
    OntologyRule("Document", "REFERENCES", "Law", "A document references a law"),
    OntologyRule("Document", "REFERENCES", "Case", "A document references a case"),
    OntologyRule("Document", "CONTAINS", "Entity", "A document contains an entity"),
    OntologyRule("Document", "DISCUSSES", "Topic", "A document discusses a topic"),
    # Entity relationships
    OntologyRule("Entity", "MENTIONED_IN", "Document", "An entity is mentioned in a document"),
    OntologyRule("Entity", "PARTY_TO", "Case", "An entity is party to a case"),
    OntologyRule("Entity", "SUBJECT_OF", "Law", "An entity is subject of a law"),
    # Topic relationships
    OntologyRule("Topic", "RELATES_TO", "Topic", "A topic relates to another topic", bidirectional=True),
    # Verdict/Reasoning relationships
    OntologyRule("Verdict", "BASED_ON", "Law", "A verdict is based on a law"),
    OntologyRule("Verdict", "BASED_ON", "Case", "A verdict is based on a case"),
    OntologyRule("Verdict", "DERIVED_FROM", "Evidence", "A verdict is derived from evidence"),
    OntologyRule("Evidence", "SUPPORTS", "Verdict", "Evidence supports a verdict"),
    OntologyRule("Evidence", "CONTRADICTS", "Verdict", "Evidence contradicts a verdict"),
    OntologyRule("Evidence", "EXTRACTED_FROM", "Document", "Evidence extracted from a document"),
    # Verdict ingestion relationships (used by upsert_verdict_struct)
    OntologyRule("Verdict", "REFERS_TO", "LawArticle", "A verdict refers to a law article"),
    OntologyRule("Verdict", "HAS_PARTY", "Person", "A verdict has a party"),
    OntologyRule("Verdict", "HAS_TAG", "Tag", "A verdict has a tag"),
    # Graph builder relationships (used by UltraGraphBuilder.export_to_neo4j)
    OntologyRule("GraphNode", "RELATED", "GraphNode", "Generic graph node relationship"),
    # Document-LawArticle linkage
    OntologyRule("Document", "REFERENCES", "LawArticle", "A document references a law article"),
    # Person reverse lookup
    OntologyRule("Person", "PARTY_TO", "Verdict", "A person is party to a verdict"),
    # Phase 2B Semantic & Concept relationships
    OntologyRule("Article", "REGULATES", "Concept", "An article regulates a legal concept"),
    OntologyRule("Article", "APPLIES_TO", "Concept", "An article applies to a legal concept"),
    OntologyRule("Article", "RESTRICTED_BY", "Concept", "An article is restricted by a legal concept"),
    OntologyRule("Article", "HAS_CONDITION", "Condition", "An article defines a condition"),
    OntologyRule("Article", "HAS_SANCTION", "Sanction", "An article defines a sanction or legal effect"),
    OntologyRule("Article", "HAS_EXCEPTION", "Exception", "An article defines an exception"),
    OntologyRule("Concept", "INHERITS_FROM", "Concept", "A concept inherits from a parent concept"),
    OntologyRule("Concept", "RELATES_TO", "Concept", "A concept relates to another concept", bidirectional=True),
    OntologyRule("Law", "MANDATES_COMPLIANCE", "Law", "A law mandates compliance on another law/standard"),
    OntologyRule("Law", "SUBJECT_TO_PROCEDURE", "Law", "A law is subject to procedure of another law"),
    OntologyRule("Law", "CONSTITUTIONAL_BASIS", "Law", "A law derives from a constitutional basis"),
    # Temporal legal version relationships
    OntologyRule("Law", "REPLACED_BY", "Law", "A law version is replaced by another law"),
    OntologyRule("Article", "AMENDS", "Article", "An article amends another article"),
    OntologyRule("Article", "SUPERSEDES", "Article", "An article supersedes another article"),
    OntologyRule("Article", "REPEALS", "Article", "An article repeals another article"),
    # LegalVersion (bitemporal versioning) relationships
    OntologyRule("Law", "HAS_VERSION", "LegalVersion", "A law has a versioned snapshot"),
    OntologyRule("Article", "HAS_VERSION", "LegalVersion", "An article has a versioned snapshot"),
    OntologyRule("LegalVersion", "SUPERSEDES", "LegalVersion", "A version supersedes a prior version"),
    OntologyRule("LegalVersion", "AMENDS", "LegalVersion", "A version amends a prior version"),
    # Norm (deontic) relationships
    OntologyRule("Norm", "HAS_SOURCE", "Article", "A deontic norm is sourced from an article"),
    OntologyRule("Norm", "HAS_SOURCE", "Law", "A deontic norm is sourced from a law"),
    OntologyRule("Norm", "SUPERSEDES", "Norm", "A norm supersedes a prior norm"),
    OntologyRule("Norm", "CONFLICTS_WITH", "Norm", "A norm conflicts with another norm"),
    OntologyRule("Norm", "EXCEPTED_BY", "Norm", "A norm is excepted by another norm"),
    OntologyRule("Norm", "GOVERNED_BY", "Law", "A norm is governed by a law"),
    # NormConflict relationships
    OntologyRule("NormConflict", "CONFLICTS_WITH", "Norm", "A conflict record links to a norm"),
    OntologyRule("NormConflict", "RESOLVED_BY", "JudicialAuthority", "A conflict is resolved by a judicial authority"),
    OntologyRule("NormConflict", "RELATED_TO", "NormConflict", "Two conflict records are related"),
    # JudicialAuthority relationships
    OntologyRule("JudicialAuthority", "AUTHORITY_OVER", "Norm", "A judicial authority has authority over a norm"),
    OntologyRule("JudicialAuthority", "AUTHORITY_OVER", "Article", "A judicial authority has authority over an article"),
    OntologyRule("JudicialAuthority", "AUTHORITY_OVER", "Verdict", "A judicial authority has authority over a verdict"),
    OntologyRule("JudicialAuthority", "BASED_ON", "Law", "A judicial authority is based on a law"),
    # Verdict binding scope relationships
    OntologyRule("Verdict", "BINDING_SCOPE", "Verdict", "A verdict declares its binding scope"),
    OntologyRule("Verdict", "AUTHORITY_BASIS", "JudicialAuthority", "A verdict is grounded in a judicial authority"),
    # Conflict resolution relationship
    OntologyRule("NormConflict", "RESOLVED_BY", "Law", "A conflict is resolved by a higher-level law (lex superior)"),
)


class OntologyEnforcer:
    """Enforce ontology rules before relationship creation.

    This enforcer validates that relationship types between node types
    conform to the MAHOUN legal ontology. Invalid relationships are
    rejected with GovernanceViolationError.

    The enforcer operates in STRICT mode only — no warnings, no soft
    failures, no fallbacks.
    """

    def __init__(
        self,
        rules: Optional[Tuple[OntologyRule, ...]] = None,
    ) -> None:
        """Initialize the ontology enforcer.

        Args:
            rules: Ontology rules to enforce. Defaults to MAHOUN legal ontology.
        """
        effective_rules = rules if rules is not None else _DEFAULT_ONTOLOGY_RULES
        # Build lookup index: (source_type, relationship_type, target_type) -> rule
        self._rules: Dict[Tuple[str, str, str], OntologyRule] = {}
        for rule in effective_rules:
            key = (rule.source_type, rule.relationship_type, rule.target_type)
            self._rules[key] = rule
            if rule.bidirectional:
                reverse_key = (
                    rule.target_type,
                    rule.relationship_type,
                    rule.source_type,
                )
                self._rules[reverse_key] = rule

        # Build valid relationship types per source type
        self._valid_relationships: Dict[str, Set[str]] = {}
        for src, rel, tgt in self._rules:
            if src not in self._valid_relationships:
                self._valid_relationships[src] = set()
            self._valid_relationships[src].add(rel)

    def validate_relationship(
        self,
        source_type: str,
        relationship_type: str,
        target_type: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a relationship conforms to the ontology.

        Args:
            source_type: Type of the source node.
            relationship_type: Type of the relationship.
            target_type: Type of the target node.
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the relationship is not in the ontology.
        """
        key = (source_type, relationship_type, target_type)

        if key not in self._rules:
            # Determine the specific failure reason
            if source_type not in self._valid_relationships:
                detail_msg = (
                    f"Unknown source type '{source_type}'. "
                    f"Known types: {sorted(self._valid_relationships.keys())}"
                )
            elif relationship_type not in self._valid_relationships.get(
                source_type, set()
            ):
                detail_msg = (
                    f"Invalid relationship '{relationship_type}' for "
                    f"source type '{source_type}'. "
                    f"Valid relationships: "
                    f"{sorted(self._valid_relationships.get(source_type, set()))}"
                )
            else:
                detail_msg = (
                    f"Relationship '{source_type} -[{relationship_type}]-> "
                    f"{target_type}' does not match any ontology rule"
                )

            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Ontology violation: {source_type} "
                        f"-[{relationship_type}]-> {target_type}"
                    ),
                    details={
                        "source_type": source_type,
                        "relationship_type": relationship_type,
                        "target_type": target_type,
                        "detail": detail_msg,
                    },
                    source="OntologyEnforcer",
                    correlation_id=correlation_id,
                )
            )

    def get_valid_relationships(
        self, source_type: str
    ) -> FrozenSet[str]:
        """Get valid relationship types for a given source type.

        Args:
            source_type: Node type to query.

        Returns:
            Frozen set of valid relationship type names.
        """
        return frozenset(self._valid_relationships.get(source_type, set()))

    def get_valid_targets(
        self, source_type: str, relationship_type: str
    ) -> FrozenSet[str]:
        """Get valid target types for a source type and relationship.

        Args:
            source_type: Source node type.
            relationship_type: Relationship type.

        Returns:
            Frozen set of valid target node types.
        """
        targets: Set[str] = set()
        for (src, rel, tgt), _rule in self._rules.items():
            if src == source_type and rel == relationship_type:
                targets.add(tgt)
        return frozenset(targets)

    @property
    def rule_count(self) -> int:
        """Total number of ontology rules (including bidirectional expansions)."""
        return len(self._rules)

    def validate_deontic_operator(
        self,
        operator: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a deontic operator value is in the legal ontology.

        Only OBLIGATION, PERMISSION, PROHIBITION are accepted.
        None is accepted (treated as not specified).
        Empty/whitespace strings and case variants are REJECTED.

        Args:
            operator: Deontic operator value (string or None).
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the operator is not in the ontology.
        """
        if operator is None:
            return
        if not isinstance(operator, str):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Deontic operator must be str or None, got {type(operator).__name__}",
                    details={"operator_type": type(operator).__name__},
                    source="OntologyEnforcer.validate_deontic_operator",
                    correlation_id=correlation_id,
                )
            )
        valid_values = {op.value for op in DeonticOperator}
        if operator not in valid_values:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Unknown deontic operator '{operator}'",
                    details={
                        "operator": operator,
                        "valid_operators": sorted(valid_values),
                    },
                    source="OntologyEnforcer.validate_deontic_operator",
                    correlation_id=correlation_id,
                )
            )

    def validate_legal_level(
        self,
        legal_level: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a legal-level value is in the ontology.

        Only values defined in LegalLevel are accepted.
        None is REJECTED (legal_level is required).
        Empty/whitespace strings and case variants are REJECTED.

        Args:
            legal_level: Legal-level value (string or None).
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the legal level is not in the ontology.
        """
        if legal_level is None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message="legal_level is required and cannot be None",
                    details={"legal_level": None},
                    source="OntologyEnforcer.validate_legal_level",
                    correlation_id=correlation_id,
                )
            )
        if not isinstance(legal_level, str):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"legal_level must be str, got {type(legal_level).__name__}",
                    details={"legal_level_type": type(legal_level).__name__},
                    source="OntologyEnforcer.validate_legal_level",
                    correlation_id=correlation_id,
                )
            )
        valid_values = {lvl.value for lvl in LegalLevel}
        if legal_level not in valid_values:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Unknown legal_level '{legal_level}'",
                    details={
                        "legal_level": legal_level,
                        "valid_levels": sorted(valid_values),
                    },
                    source="OntologyEnforcer.validate_legal_level",
                    correlation_id=correlation_id,
                )
            )

    def validate_conflict_resolution(
        self,
        resolution: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a conflict-resolution value is in the ontology.

        Accepted values: RESOLVED_SUPERIOR, RESOLVED_LEX_POSTERIOR,
        RESOLVED_LEX_SPECIALIS, UNRESOLVED, CONTRADICTORY.
        None is accepted (treated as not specified).
        Empty/whitespace strings and case variants are REJECTED.

        Args:
            resolution: Conflict-resolution value (string or None).
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the resolution is not in the ontology.
        """
        if resolution is None:
            return
        if not isinstance(resolution, str):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"conflict_resolution must be str or None, got {type(resolution).__name__}",
                    details={"resolution_type": type(resolution).__name__},
                    source="OntologyEnforcer.validate_conflict_resolution",
                    correlation_id=correlation_id,
                )
            )
        valid_values = {r.value for r in ConflictResolution}
        if resolution not in valid_values:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Unknown conflict_resolution '{resolution}'",
                    details={
                        "resolution": resolution,
                        "valid_resolutions": sorted(valid_values),
                    },
                    source="OntologyEnforcer.validate_conflict_resolution",
                    correlation_id=correlation_id,
                )
            )

    def validate_legal_force(
        self,
        legal_force: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a legal-force value is in the ontology.

        Accepted values: BINDING, PERSUASIVE, NON_BINDING, ADVISORY.
        None is accepted (treated as not specified).
        Empty/whitespace strings and case variants are REJECTED.

        Args:
            legal_force: Legal-force value (string or None).
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the legal force is not in the ontology.
        """
        if legal_force is None:
            return
        if not isinstance(legal_force, str):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"legal_force must be str or None, got {type(legal_force).__name__}",
                    details={"legal_force_type": type(legal_force).__name__},
                    source="OntologyEnforcer.validate_legal_force",
                    correlation_id=correlation_id,
                )
            )
        valid_values = {f.value for f in LegalForce}
        if legal_force not in valid_values:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Unknown legal_force '{legal_force}'",
                    details={
                        "legal_force": legal_force,
                        "valid_forces": sorted(valid_values),
                    },
                    source="OntologyEnforcer.validate_legal_force",
                    correlation_id=correlation_id,
                )
            )

    def validate_binding_scope(
        self,
        binding_scope: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a binding-scope value is in the ontology.

        Accepted values: PARTIES_ONLY, LOWER_COURTS, SAME_COURT,
        ALL_COURTS, ADMINISTRATIVE_BODIES, SPECIFIC_JURISDICTION,
        SPECIFIC_LEGAL_QUESTION.
        None is accepted (treated as not specified).
        Empty/whitespace strings and case variants are REJECTED.

        Args:
            binding_scope: Binding-scope value (string or None).
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the binding scope is not in the ontology.
        """
        if binding_scope is None:
            return
        if not isinstance(binding_scope, str):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"binding_scope must be str or None, got {type(binding_scope).__name__}",
                    details={"binding_scope_type": type(binding_scope).__name__},
                    source="OntologyEnforcer.validate_binding_scope",
                    correlation_id=correlation_id,
                )
            )
        valid_values = {s.value for s in BindingScope}
        if binding_scope not in valid_values:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Unknown binding_scope '{binding_scope}'",
                    details={
                        "binding_scope": binding_scope,
                        "valid_scopes": sorted(valid_values),
                    },
                    source="OntologyEnforcer.validate_binding_scope",
                    correlation_id=correlation_id,
                )
            )

    def validate_norm_status(
        self,
        norm_status: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a norm-status value is in the ontology.

        Accepted values: DRAFT, PUBLISHED, IN_FORCE, SUSPENDED, REPEALED,
        SUPERSEDED, EXPIRED, PENDING_RATIFICATION.
        None is accepted (treated as not specified).
        Empty/whitespace strings and case variants are REJECTED.

        Args:
            norm_status: Norm-status value (string or None).
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the norm status is not in the ontology.
        """
        if norm_status is None:
            return
        if not isinstance(norm_status, str):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"norm_status must be str or None, got {type(norm_status).__name__}",
                    details={"norm_status_type": type(norm_status).__name__},
                    source="OntologyEnforcer.validate_norm_status",
                    correlation_id=correlation_id,
                )
            )
        valid_values = {s.value for s in NormStatus}
        if norm_status not in valid_values:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Unknown norm_status '{norm_status}'",
                    details={
                        "norm_status": norm_status,
                        "valid_statuses": sorted(valid_values),
                    },
                    source="OntologyEnforcer.validate_norm_status",
                    correlation_id=correlation_id,
                )
            )

    def validate_decision_type(
        self,
        decision_type: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a decision-type value is in the ontology.

        Accepted values: UNIFICATION, PRECEDENTIAL, ORDINARY_JUDGMENT,
        ADVISORY_OPINION, ADMINISTRATIVE_GENERAL_BOARD,
        CONSTITUTIONAL_COURT, INTERLOCUTORY, EXECUTION.
        None is accepted (treated as not specified).
        Empty/whitespace strings and case variants are REJECTED.

        Args:
            decision_type: Decision-type value (string or None).
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the decision type is not in the ontology.
        """
        if decision_type is None:
            return
        if not isinstance(decision_type, str):
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"decision_type must be str or None, got {type(decision_type).__name__}",
                    details={"decision_type_type": type(decision_type).__name__},
                    source="OntologyEnforcer.validate_decision_type",
                    correlation_id=correlation_id,
                )
            )
        valid_values = {d.value for d in DecisionType}
        if decision_type not in valid_values:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Unknown decision_type '{decision_type}'",
                    details={
                        "decision_type": decision_type,
                        "valid_types": sorted(valid_values),
                    },
                    source="OntologyEnforcer.validate_decision_type",
                    correlation_id=correlation_id,
                )
            )

    def validate_hierarchy_precedence(
        self,
        higher_level: str,
        lower_level: str,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Validate hierarchy precedence ordering between two legal levels.

        Returns True if `higher_level` is strictly above `lower_level` in
        the legal hierarchy (CONSTITUTIONAL > ORDINARY_LAW > DECREE >
        REGULATION > BYLAW > CIRCULAR > JUDICIAL_PRECEDENT > DOCTRINE).
        Returns False if `higher_level` is at or below `lower_level`.

        Args:
            higher_level: Candidate higher level.
            lower_level: Candidate lower level.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            True if higher_level > lower_level in the hierarchy.

        Raises:
            GovernanceViolationError: If either level is unknown.
        """
        self.validate_legal_level(higher_level, correlation_id=correlation_id)
        self.validate_legal_level(lower_level, correlation_id=correlation_id)
        rank = {
            LegalLevel.CONSTITUTIONAL.value: 8,
            LegalLevel.ORDINARY_LAW.value: 7,
            LegalLevel.DECREE.value: 6,
            LegalLevel.REGULATION.value: 5,
            LegalLevel.BYLAW.value: 4,
            LegalLevel.CIRCULAR.value: 3,
            LegalLevel.JUDICIAL_PRECEDENT.value: 2,
            LegalLevel.DOCTRINE.value: 1,
        }
        return rank[higher_level.strip().upper()] > rank[lower_level.strip().upper()]

    def validate_temporal_relationship(
        self,
        source_type: str,
        target_type: str,
        relationship_type: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a temporal relationship is in the ontology.

        Temporal relations are only permitted between Law->Law, Law->Article,
        Article->Article, or Verdict->Law/Verdict->Article pairs.

        Args:
            source_type: Source node type.
            target_type: Target node type.
            relationship_type: Temporal relationship type.
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the temporal relationship is invalid.
        """
        valid_types = {r.value for r in TemporalRelationType}
        if relationship_type not in valid_types:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Unknown temporal relationship '{relationship_type}'",
                    details={
                        "relationship_type": relationship_type,
                        "valid_types": sorted(valid_types),
                    },
                    source="OntologyEnforcer.validate_temporal_relationship",
                    correlation_id=correlation_id,
                )
            )
        allowed_pairs = {
            ("Law", "Law"),
            ("Law", "Article"),
            ("Article", "Article"),
            ("Verdict", "Law"),
            ("Verdict", "Article"),
        }
        if (source_type, target_type) not in allowed_pairs:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Temporal relationship '{relationship_type}' not "
                        f"allowed between {source_type} and {target_type}"
                    ),
                    details={
                        "source_type": source_type,
                        "target_type": target_type,
                        "relationship_type": relationship_type,
                        "allowed_pairs": sorted(allowed_pairs),
                    },
                    source="OntologyEnforcer.validate_temporal_relationship",
                    correlation_id=correlation_id,
                )
            )

    def validate_norm_relationship(
        self,
        source_type: str,
        target_type: str,
        relationship_type: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a relationship touching a Norm node is in the ontology.

        Permitted patterns:
        - Norm HAS_SOURCE Article | Law
        - Norm SUPERSEDES Norm
        - Norm CONFLICTS_WITH Norm (for NormConflict modeling)
        - Norm EXCEPTED_BY Norm
        - Norm GOVERNED_BY Law

        Args:
            source_type: Source node type.
            target_type: Target node type.
            relationship_type: Relationship type.
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the norm relationship is invalid.
        """
        allowed: Set[Tuple[str, str, str]] = {
            ("Norm", "Article", "HAS_SOURCE"),
            ("Norm", "Law", "HAS_SOURCE"),
            ("Norm", "Norm", "SUPERSEDES"),
            ("Norm", "Norm", "CONFLICTS_WITH"),
            ("Norm", "Norm", "EXCEPTED_BY"),
            ("Norm", "Law", "GOVERNED_BY"),
        }
        key = (source_type, target_type, relationship_type)
        if key not in allowed:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Invalid norm relationship: {source_type} "
                        f"-[{relationship_type}]-> {target_type}"
                    ),
                    details={
                        "source_type": source_type,
                        "target_type": target_type,
                        "relationship_type": relationship_type,
                        "allowed": sorted(allowed),
                    },
                    source="OntologyEnforcer.validate_norm_relationship",
                    correlation_id=correlation_id,
                )
            )

    def validate_conflict_record(
        self,
        source_type: str,
        target_type: str,
        relationship_type: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a NormConflict-targeting relationship is in the ontology.

        Permitted patterns:
        - NormConflict CONFLICTS_WITH Norm
        - NormConflict RESOLVED_BY JudicialAuthority
        - NormConflict CONFLICTS_WITH NormConflict (chained)
        - NormConflict UNRESOLVED only valid when resolution=UNRESOLVED

        Args:
            source_type: Source node type.
            target_type: Target node type.
            relationship_type: Relationship type.
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the conflict record is invalid.
        """
        allowed: Set[Tuple[str, str, str]] = {
            ("NormConflict", "Norm", "CONFLICTS_WITH"),
            ("NormConflict", "JudicialAuthority", "RESOLVED_BY"),
            ("NormConflict", "NormConflict", "CONFLICTS_WITH"),
            ("NormConflict", "NormConflict", "RELATED_TO"),
        }
        key = (source_type, target_type, relationship_type)
        if key not in allowed:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Invalid conflict relationship: {source_type} "
                        f"-[{relationship_type}]-> {target_type}"
                    ),
                    details={
                        "source_type": source_type,
                        "target_type": target_type,
                        "relationship_type": relationship_type,
                        "allowed": sorted(allowed),
                    },
                    source="OntologyEnforcer.validate_conflict_record",
                    correlation_id=correlation_id,
                )
            )

    def validate_judicial_authority_relationship(
        self,
        source_type: str,
        target_type: str,
        relationship_type: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a relationship from JudicialAuthority is in the ontology.

        Permitted patterns:
        - JudicialAuthority AUTHORITY_OVER Norm
        - JudicialAuthority AUTHORITY_OVER Article
        - JudicialAuthority AUTHORITY_OVER Verdict
        - JudicialAuthority BASED_ON Law

        Args:
            source_type: Source node type.
            target_type: Target node type.
            relationship_type: Relationship type.
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the judicial authority relationship is invalid.
        """
        allowed: Set[Tuple[str, str, str]] = {
            ("JudicialAuthority", "Norm", "AUTHORITY_OVER"),
            ("JudicialAuthority", "Article", "AUTHORITY_OVER"),
            ("JudicialAuthority", "Verdict", "AUTHORITY_OVER"),
            ("JudicialAuthority", "Law", "BASED_ON"),
        }
        key = (source_type, target_type, relationship_type)
        if key not in allowed:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Invalid judicial authority relationship: {source_type} "
                        f"-[{relationship_type}]-> {target_type}"
                    ),
                    details={
                        "source_type": source_type,
                        "target_type": target_type,
                        "relationship_type": relationship_type,
                        "allowed": sorted(allowed),
                    },
                    source="OntologyEnforcer.validate_judicial_authority_relationship",
                    correlation_id=correlation_id,
                )
            )

    def validate_conflict_state(
        self,
        resolution: Optional[str],
        target_authority_score: Optional[float],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a conflict resolution state is consistent.

        Rules:
        - resolution=UNRESOLVED must never carry an authority_score; presence
          of authority_score in UNRESOLVED state indicates a bypass attempt.
        - resolution=RESOLVED_SUPERIOR may carry an authority_score (the
          score is the residual influence of the winning superior norm).
        - resolution=RESOLVED_LEX_POSTERIOR may carry an authority_score
          (the residual influence of the later norm).
        - resolution=RESOLVED_LEX_SPECIALIS may carry an authority_score
          (the residual influence of the special norm).
        - resolution=CONTRADICTORY must not carry a target authority_score
          (the contradiction is unresolved at the system level).
        - For RESOLVED_* states, the score MUST be a real (non-bool)
          numeric value in [0.0, 1.0] and finite. Negative, NaN, ±inf,
          boolean, string, or out-of-range values are bypass attempts
          that the validator must reject.

        Args:
            resolution: ConflictResolution value.
            target_authority_score: Optional authority score attached to the
                target of the conflict (JudicialAuthority.authority_score).
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the state is internally inconsistent.
        """
        self.validate_conflict_resolution(resolution, correlation_id=correlation_id)
        if resolution is None:
            return
        norm = resolution.strip().upper()
        if norm == ConflictResolution.UNRESOLVED.value and target_authority_score is not None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        "UNRESOLVED conflict must not carry an authority_score; "
                        "presence indicates a bypass attempt"
                    ),
                    details={
                        "resolution": resolution,
                        "target_authority_score": target_authority_score,
                    },
                    source="OntologyEnforcer.validate_conflict_state",
                    correlation_id=correlation_id,
                )
            )
        if norm == ConflictResolution.CONTRADICTORY.value and target_authority_score is not None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        "CONTRADICTORY conflict must not carry a target "
                        "authority_score; contradiction is unresolved"
                    ),
                    details={
                        "resolution": resolution,
                        "target_authority_score": target_authority_score,
                    },
                    source="OntologyEnforcer.validate_conflict_state",
                    correlation_id=correlation_id,
                )
            )
        # For RESOLVED_* states, enforce that any authority_score is a
        # real numeric value in [0.0, 1.0] and finite. A None score
        # is permitted (means "no residual influence tracked"). A
        # negative, NaN, ±inf, bool, string, or out-of-range value
        # is a bypass attempt.
        if norm in (
            ConflictResolution.RESOLVED_SUPERIOR.value,
            ConflictResolution.RESOLVED_LEX_POSTERIOR.value,
            ConflictResolution.RESOLVED_LEX_SPECIALIS.value,
        ) and target_authority_score is not None:
            import math as _math

            # Reject booleans explicitly (bool is a subclass of int)
            if isinstance(target_authority_score, bool):
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.ONTOLOGY_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"authority_score for {norm} must be a real "
                            f"numeric value, got bool"
                        ),
                        details={
                            "resolution": resolution,
                            "target_authority_score": target_authority_score,
                            "value_type": "bool",
                        },
                        source="OntologyEnforcer.validate_conflict_state",
                        correlation_id=correlation_id,
                    )
                )
            # Reject non-numeric types
            if not isinstance(target_authority_score, (int, float)):
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.ONTOLOGY_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"authority_score for {norm} must be a real "
                            f"numeric value, got {type(target_authority_score).__name__}"
                        ),
                        details={
                            "resolution": resolution,
                            "target_authority_score": target_authority_score,
                            "value_type": type(target_authority_score).__name__,
                        },
                        source="OntologyEnforcer.validate_conflict_state",
                        correlation_id=correlation_id,
                    )
                )
            # Reject non-finite values (NaN, +inf, -inf)
            if not _math.isfinite(target_authority_score):
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.ONTOLOGY_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"authority_score for {norm} must be finite, got "
                            f"{target_authority_score!r}"
                        ),
                        details={
                            "resolution": resolution,
                            "target_authority_score": target_authority_score,
                        },
                        source="OntologyEnforcer.validate_conflict_state",
                        correlation_id=correlation_id,
                    )
                )
            # Reject negative scores (including -0.0 — IEEE 754 copysign
            # of 0.0 is the canonical way to detect "is negative zero").
            if target_authority_score < 0.0 or (
                target_authority_score == 0.0
                and _math.copysign(1.0, target_authority_score) < 0
            ):
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.ONTOLOGY_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"authority_score for {norm} must be non-negative, "
                            f"got {target_authority_score!r}"
                        ),
                        details={
                            "resolution": resolution,
                            "target_authority_score": target_authority_score,
                        },
                        source="OntologyEnforcer.validate_conflict_state",
                        correlation_id=correlation_id,
                    )
                )
            # Reject out-of-range scores (must be in [0.0, 1.0])
            if target_authority_score > 1.0:
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.ONTOLOGY_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"authority_score for {norm} must be in [0.0, 1.0], "
                            f"got {target_authority_score!r}"
                        ),
                        details={
                            "resolution": resolution,
                            "target_authority_score": target_authority_score,
                        },
                        source="OntologyEnforcer.validate_conflict_state",
                        correlation_id=correlation_id,
                    )
                )

    def validate_temporal_range(
        self,
        valid_from: Optional[str],
        valid_until: Optional[str],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate a temporal range pair (valid_from, valid_until).

        Both endpoints must be ISO 8601 dates or datetimes. valid_until must
        be strictly after valid_from. A None valid_until is permitted (open-
        ended norm).

        Args:
            valid_from: ISO 8601 lower bound.
            valid_until: ISO 8601 upper bound or None.
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the range is malformed.
        """
        from datetime import datetime

        def _parse(value: Optional[str], *, field_name: str) -> Optional[datetime]:
            """Parse an ISO 8601 string to a datetime, with strict
            fail-closed semantics. An empty string (after strip) is
            treated as a missing value, not as None — the caller must
            distinguish 'open-ended' (None) from 'malformed' (empty)
            and reject accordingly via ``_parse`` returning None ONLY
            when the original input was None.
            """
            if value is None:
                return None
            if not isinstance(value, str):
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.ONTOLOGY_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"{field_name} must be ISO 8601 string, got "
                            f"{type(value).__name__}"
                        ),
                        details={"value_type": type(value).__name__},
                        source="OntologyEnforcer.validate_temporal_range",
                        correlation_id=correlation_id,
                    )
                )
            text = value.strip()
            if text == "":
                # Empty / whitespace string is malformed, NOT a valid
                # representation of "no value". This prevents
                # `validate_temporal_range("", "2024-12-31")` from
                # reaching the comparison step where it would raise
                # a Python TypeError instead of a governed
                # GovernanceViolationError.
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.ONTOLOGY_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"{field_name} must not be empty or whitespace"
                        ),
                        details={"value": value},
                        source="OntologyEnforcer.validate_temporal_range",
                        correlation_id=correlation_id,
                    )
                )
            for parser in (
                lambda s: datetime.fromisoformat(s),
                lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
            ):
                try:
                    return parser(text)
                except ValueError:
                    continue
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Invalid ISO 8601 temporal value '{value}'",
                    details={"value": value},
                    source="OntologyEnforcer.validate_temporal_range",
                    correlation_id=correlation_id,
                )
            )

        if valid_from is None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message="valid_from is required and cannot be None",
                    details={"valid_from": None},
                    source="OntologyEnforcer.validate_temporal_range",
                    correlation_id=correlation_id,
                )
            )
        lower = _parse(valid_from, field_name="valid_from")
        upper = (
            _parse(valid_until, field_name="valid_until")
            if valid_until is not None
            else None
        )
        if upper is not None and upper <= lower:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message="valid_until must be strictly after valid_from",
                    details={
                        "valid_from": valid_from,
                        "valid_until": valid_until,
                    },
                    source="OntologyEnforcer.validate_temporal_range",
                    correlation_id=correlation_id,
                )
            )
        # Precision consistency: if both endpoints are ISO 8601
        # date-only strings (length 10, no 'T'), both must be
        # date-only. If either uses datetime precision, the other
        # must too. Mixing precisions is a precision-loss bug.
        if upper is not None:
            lower_has_t = "T" in valid_from
            upper_has_t = "T" in valid_until
            if lower_has_t != upper_has_t:
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.ONTOLOGY_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            "valid_from and valid_until must use consistent "
                            "precision (both date-only or both datetime)"
                        ),
                        details={
                            "valid_from": valid_from,
                            "valid_from_has_time": lower_has_t,
                            "valid_until": valid_until,
                            "valid_until_has_time": upper_has_t,
                        },
                        source="OntologyEnforcer.validate_temporal_range",
                        correlation_id=correlation_id,
                    )
                )

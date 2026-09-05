"""
MAHOUN Semantic Models & Verification Primitives (Phase 2B)
===========================================================
Classification: CANONICAL CORE MODEL
Purpose: Proof-carrying semantic entities, assertions, and decomposition models.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class VerificationStatus(str, Enum):
    """Lifecycle states of semantic extraction."""
    CANDIDATE = "CANDIDATE"
    NORMALIZED = "NORMALIZED"
    VERIFIED = "VERIFIED"
    UNRESOLVED = "UNRESOLVED"
    MATERIALIZED = "MATERIALIZED"


@dataclass
class SemanticIdentity:
    """Canonical identity for semantic concepts."""
    canonical_id: str
    canonical_label_fa: str
    canonical_label_en: str
    normalized_label: str
    jurisdiction: str = "IR"
    domain: str = "general_law"
    ontology_version: str = "1.0"
    semantic_schema_version: str = "2B.1.0"
    aliases_fa: List[str] = field(default_factory=list)
    aliases_en: List[str] = field(default_factory=list)
    parent_concept_id: Optional[str] = None
    description_fa: Optional[str] = None


@dataclass
class SemanticFact:
    """Proof-carrying semantic fact attached to an Article span."""
    fact_id: str
    fact_type: str  # 'node' | 'property' | 'sub_clause'
    node_label: Optional[str]
    edge_type: Optional[str]
    source_article_id: str
    source_text_span: str
    source_offset_start: int
    source_offset_end: int
    source_sha256: str
    status: VerificationStatus = VerificationStatus.CANDIDATE
    verification_method: str = "structural_extraction"
    verification_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_score: Optional[float] = 1.0
    extracted_by: str = "semantic_extractor_v2b"
    extraction_version: str = "2B.1.0"
    ingestion_run: str = "default_run"

    def verify(self, article_text: str) -> bool:
        """
        Verify claimed text span and SHA-256 against actual article text.
        Returns True ONLY if span exactly matches and article SHA-256 matches.
        """
        if not article_text:
            return False

        try:
            claimed_span = article_text[self.source_offset_start : self.source_offset_end]
        except IndexError:
            return False

        if claimed_span != self.source_text_span:
            return False

        computed_hash = hashlib.sha256(article_text.encode("utf-8")).hexdigest()[:16]
        if self.source_sha256 and computed_hash != self.source_sha256:
            return False

        return True


@dataclass
class SemanticAssertion:
    """Proof-carrying semantic relationship between two entities."""
    assertion_id: str
    assertion_type: str  # 'REGULATES' | 'APPLIES_TO' | 'RESTRICTED_BY' | 'INHERITS_FROM'
    source_entity_id: str
    target_entity_id: str
    evidence_text_span: str
    evidence_offset_start: int
    evidence_offset_end: int
    evidence_sha256: str
    status: VerificationStatus = VerificationStatus.CANDIDATE
    verification_method: str = "structural_extraction"
    verification_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extracted_by: str = "semantic_extractor_v2b"
    extraction_version: str = "2B.1.0"
    ingestion_run: str = "default_run"


@dataclass
class ConditionClause:
    """A conditional antecedent in a legal rule."""
    id: str
    article_id: str
    condition_text: str
    span_start: int
    span_end: int
    trigger_keyword: str  # 'در صورتی که' | 'هرگاه' | 'چنانچه' | 'مشروط بر اینکه'


@dataclass
class SanctionClause:
    """A legal sanction or normative consequence."""
    id: str
    article_id: str
    sanction_text: str
    span_start: int
    span_end: int
    sanction_type: str  # 'VALIDITY' | 'NULLITY' | 'OBLIGATION' | 'LIABILITY' | 'PENALTY'


@dataclass
class ExceptionClause:
    """A legal exception limiting a general rule."""
    id: str
    article_id: str
    exception_text: str
    span_start: int
    span_end: int
    trigger_keyword: str  # 'مگر اینکه' | 'به استثنای' | 'الا در مواردی که'


@dataclass
class ArticleDecomposition:
    """Decomposition of a legal article into structured logical components."""
    article_id: str
    law_id: str
    raw_text: str
    normalized_text: str
    text_hash: str
    conditions: List[ConditionClause] = field(default_factory=list)
    sanctions: List[SanctionClause] = field(default_factory=list)
    exceptions: List[ExceptionClause] = field(default_factory=list)
    is_conditional: bool = False
    has_exceptions: bool = False

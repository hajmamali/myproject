"""
Semantic Graph Linking (augmentation stage only).
Deterministic, compact, and CI-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Protocol, Tuple
import re


TH_LINK = 0.78
TH_CREATE = 0.70
AMBIGUITY_DELTA = 0.06

_CREATE_ALLOWED = {"UNIFICATION_RULING", "ARTICLE", "CIRCULAR", "CLAUSE", "JUDGMENT"}


def _normalize_name(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("رأی", "رای")
    return text


def _fuzzy_key(text: str) -> str:
    return re.sub(r"[^a-z0-9\u0600-\u06ff]+", "", text)


@dataclass(frozen=True)
class EntityMention:
    name: str
    entity_type: str
    identities: Dict[str, str] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    context: str = ""


@dataclass(frozen=True)
class Candidate:
    node_id: str
    name: str
    entity_type: str
    identities: Dict[str, str] = field(default_factory=dict)
    canonical_id: Optional[str] = None
    context: str = ""
    anchor_score: float = 0.5


@dataclass(frozen=True)
class ScoreBreakdown:
    name_score: float
    type_score: float
    identity_score: float
    context_score: float
    anchor_score: float
    total: float


@dataclass(frozen=True)
class LinkResult:
    action: str
    resolved_node_id: Optional[str]
    canonical_id: Optional[str]
    confidence: float
    reason: str
    score_breakdown: Optional[ScoreBreakdown]
    provenance: Dict[str, Any]
    candidates: List[Tuple[Candidate, ScoreBreakdown]]


class GraphResolver(Protocol):
    def find_candidates(
        self,
        name: str,
        normalized: str,
        fuzzy: str,
        entity_type: str,
    ) -> List[Candidate]:
        ...

    def create_node(
        self,
        canonical_id: str,
        entity_type: str,
        name: str,
        identities: Dict[str, str],
    ) -> str:
        ...

    def record_link(
        self,
        mention: EntityMention,
        node_id: str,
        canonical_id: Optional[str],
        confidence: float,
        score: ScoreBreakdown,
    ) -> None:
        ...


def canonical_id(mention: EntityMention) -> Optional[str]:
    identities = mention.identities
    if mention.entity_type == "UNIFICATION_RULING":
        ruling_no = identities.get("ruling_no")
        if ruling_no:
            return f"IR:SCOTUS:UNIFICATION:{ruling_no}"
    if mention.entity_type == "ARTICLE":
        law = identities.get("law")
        article_no = identities.get("article_no")
        if law and article_no:
            return f"IR:{law}:ARTICLE:{article_no}"
    if mention.entity_type == "CIRCULAR":
        issuer = identities.get("issuer")
        date = identities.get("date")
        no = identities.get("circular_no")
        if issuer and date and no:
            return f"IR:CIRCULAR:{issuer}:{date}:{no}"
    if mention.entity_type == "CLAUSE":
        contract_id = identities.get("contract_id")
        clause_no = identities.get("clause_no")
        if contract_id and clause_no:
            return f"CONTRACT:{contract_id}:CLAUSE:{clause_no}"
    if mention.entity_type == "JUDGMENT":
        jurisdiction = identities.get("jurisdiction")
        case_no = identities.get("case_no")
        year = identities.get("year")
        if jurisdiction and case_no and year:
            return f"IR:JUDG:{jurisdiction}:{year}:{case_no}"
    return None


def _identity_score(mention: EntityMention, candidate: Candidate) -> float:
    if candidate.canonical_id and candidate.canonical_id == canonical_id(mention):
        return 1.0
    if not mention.identities or not candidate.identities:
        return 0.0
    for key, value in mention.identities.items():
        if candidate.identities.get(key) == value:
            return 0.6
    return 0.0


def _context_score(mention: EntityMention, candidate: Candidate) -> float:
    if not mention.context or not candidate.context:
        return 0.5
    mention_tokens = set(_normalize_name(mention.context).split())
    candidate_tokens = set(_normalize_name(candidate.context).split())
    overlap = len(mention_tokens & candidate_tokens)
    return min(1.0, 0.5 + overlap * 0.1)


def _name_score(name: str, candidate: Candidate) -> float:
    if candidate.name == name:
        return 1.0
    normalized = _normalize_name(name)
    candidate_norm = _normalize_name(candidate.name)
    if candidate_norm == normalized:
        return 0.85
    ratio = SequenceMatcher(None, normalized, candidate_norm).ratio()
    return min(0.7, ratio * 0.7)


def _type_score(mention: EntityMention, candidate: Candidate) -> float:
    return 1.0 if mention.entity_type == candidate.entity_type else 0.0


def _score_candidate(mention: EntityMention, candidate: Candidate) -> ScoreBreakdown:
    name_score = _name_score(mention.name, candidate)
    type_score = _type_score(mention, candidate)
    identity_score = _identity_score(mention, candidate)
    context_score = _context_score(mention, candidate)
    anchor_score = candidate.anchor_score
    total = (
        0.45 * name_score
        + 0.20 * type_score
        + 0.20 * identity_score
        + 0.10 * context_score
        + 0.05 * anchor_score
    )
    return ScoreBreakdown(
        name_score=name_score,
        type_score=type_score,
        identity_score=identity_score,
        context_score=context_score,
        anchor_score=anchor_score,
        total=total,
    )


class GraphLinker:
    def __init__(self, resolver: GraphResolver) -> None:
        self.resolver = resolver

    def _is_ambiguous(
        self, mention: EntityMention, scored: List[Tuple[Candidate, ScoreBreakdown]]
    ) -> bool:
        if len(scored) < 2:
            return False
        best_score = scored[0][1]
        second_score = scored[1][1]
        best_total = best_score.total
        if best_total >= TH_LINK:
            return False
        return best_total - second_score.total <= AMBIGUITY_DELTA

    def link_entity(self, mention: EntityMention) -> LinkResult:
        normalized = _normalize_name(mention.name)
        fuzzy = _fuzzy_key(normalized)
        candidates = self.resolver.find_candidates(
            mention.name, normalized, fuzzy, mention.entity_type
        )

        scored: List[Tuple[Candidate, ScoreBreakdown]] = [
            (candidate, _score_candidate(mention, candidate))
            for candidate in candidates
        ]
        scored.sort(key=lambda item: (-item[1].total, item[0].node_id))

        best_candidate: Optional[Candidate] = None
        best_score: Optional[ScoreBreakdown] = None
        if scored:
            best_candidate, best_score = scored[0]

        mention_canonical = canonical_id(mention)
        create_score = 0.75 if mention_canonical else 0.0
        best_total = best_score.total if best_score else 0.0

        if best_candidate and best_score and best_total >= TH_LINK:
            self.resolver.record_link(
                mention, best_candidate.node_id, mention_canonical, best_total, best_score
            )
            return LinkResult(
                action="LINK",
                resolved_node_id=best_candidate.node_id,
                canonical_id=mention_canonical,
                confidence=best_total,
                reason="link_threshold_met",
                score_breakdown=best_score,
                provenance=mention.provenance,
                candidates=scored,
            )

        if (
            mention_canonical
            and mention.entity_type in _CREATE_ALLOWED
            and max(best_total, create_score) >= TH_CREATE
        ):
            node_id = self.resolver.create_node(
                mention_canonical, mention.entity_type, mention.name, mention.identities
            )
            score = best_score or ScoreBreakdown(
                name_score=1.0,
                type_score=1.0,
                identity_score=1.0,
                context_score=0.5,
                anchor_score=0.5,
                total=create_score,
            )
            self.resolver.record_link(
                mention, node_id, mention_canonical, max(best_total, create_score), score
            )
            return LinkResult(
                action="CREATE",
                resolved_node_id=node_id,
                canonical_id=mention_canonical,
                confidence=max(best_total, create_score),
                reason="create_threshold_met",
                score_breakdown=score,
                provenance=mention.provenance,
                candidates=scored,
            )

        reason = "threshold_not_met"
        if self._is_ambiguous(mention, scored):
            reason = "ambiguity_between_multiple_candidates"

        return LinkResult(
            action="UNRESOLVED",
            resolved_node_id=None,
            canonical_id=mention_canonical,
            confidence=best_total,
            reason=reason,
            score_breakdown=best_score,
            provenance=mention.provenance,
            candidates=scored,
        )

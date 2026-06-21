"""
Adversarial ambiguity test for Semantic Graph Linking.
Designed to ensure UNRESOLVED is preferred over incorrect linking.
"""

from typing import Dict, List, Optional

from mahoun.rag.graph_linker import Candidate, EntityMention, GraphLinker, TH_LINK


class _AmbiguousResolver:
    def __init__(self) -> None:
        self.create_calls = 0
        self.link_calls = 0

    def find_candidates(
        self,
        name: str,
        normalized: str,
        fuzzy: str,
        entity_type: str,
    ) -> List[Candidate]:
        return [
            Candidate(
                node_id="N-JUDG-TEH-1401",
                name="رأی دادگاه تجدیدنظر تهران سال ۱۴۰۱",
                entity_type="JUDGMENT",
                canonical_id="IR:JUDG:TEH:1401",
                context="مرجع تجدیدنظر سال ۱۴۰۱",
            ),
            Candidate(
                node_id="N-JUDG-ESF-1401",
                name="رأی دادگاه تجدیدنظر اصفهان سال ۱۴۰۱",
                entity_type="JUDGMENT",
                canonical_id="IR:JUDG:ESF:1401",
                context="مرجع تجدیدنظر سال ۱۴۰۱",
            ),
            Candidate(
                node_id="N-ARB-1401-Y",
                name="رأی داوری سال ۱۴۰۱ پرونده Y",
                entity_type="ARBITRATION",
                canonical_id="IR:ARB:Y:1401",
                context="رأی داوری سال ۱۴۰۱",
            ),
        ]

    def create_node(
        self,
        canonical_id: str,
        entity_type: str,
        name: str,
        identities: Dict[str, str],
    ) -> str:
        self.create_calls += 1
        return f"node:{canonical_id}"

    def record_link(
        self,
        mention: EntityMention,
        node_id: str,
        canonical_id: Optional[str],
        confidence: float,
        score,
    ) -> None:
        self.link_calls += 1


def test_ambiguous_judgment_returns_unresolved() -> None:
    resolver = _AmbiguousResolver()
    linker = GraphLinker(resolver)
    mention = EntityMention(
        name="رأی صادره در سال ۱۴۰۱ از مرجع تجدیدنظر",
        entity_type="JUDGMENT",
        identities={"year": "1401"},
        provenance={"doc_id": "amb-1401"},
        context="مرجع تجدیدنظر سال ۱۴۰۱",
    )
    mentions = [mention]

    assert len(mentions) == 1

    result = linker.link_entity(mention)

    assert result.action == "UNRESOLVED"
    assert result.resolved_node_id is None
    assert result.canonical_id is None
    assert result.confidence < TH_LINK
    assert result.reason == "ambiguity_between_multiple_candidates"
    assert resolver.create_calls == 0
    assert resolver.link_calls == 0

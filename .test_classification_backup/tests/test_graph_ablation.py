"""
Graph Ablation Tests
====================

بررسی می‌کند که حذف گراف یا edgeها خروجی reasoning را تغییر می‌دهد.
"""

import pytest
from typing import Dict, List, Optional

from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
from mahoun.reasoning.chain_of_thought import ChainOfThoughtReasoner
from mahoun.rag.graph_linker import Candidate, EntityMention, GraphLinker


def _build_entities():
    return [
        {"id": "A", "label": "A", "type": "Condition"},
        {"id": "B", "label": "B", "type": "Conclusion"},
        {"id": "C", "label": "C", "type": "Conclusion"},
    ]


@pytest.mark.graph_native
class TestGraphAblation:
    """Comparison of reasoning with and without graph edges"""
    
    def test_answer_differs_when_graph_removed(self):
        kg = LegalKnowledgeGraph()
        kg.add_legal_rule("r1", "A", "B", 0.9)
        kg.add_legal_rule("r2", "B", "C", 0.8)
        
        entities = _build_entities()
        relationships = [
            {"source_id": "A", "target_id": "B", "type": "IMPLIES"},
            {"source_id": "B", "target_id": "C", "type": "IMPLIES"},
        ]
        
        builder_full = UltraGraphBuilder()
        builder_full.build_graph(entities, relationships)
        reasoner_full = ChainOfThoughtReasoner(kg, graph=builder_full)
        result_full = reasoner_full.reason("سوال", "کانتکست", facts=["A"])
        
        builder_empty = UltraGraphBuilder()
        builder_empty.build_graph(entities, relationships=[])
        reasoner_empty = ChainOfThoughtReasoner(kg, graph=builder_empty)
        result_empty = reasoner_empty.reason("سوال", "کانتکست", facts=["A"])
        
        assert result_full["answer"] != result_empty["answer"]
        assert result_empty["graph_edges_used"] == []
        assert result_empty["limitations"] == "graph_missing_or_empty"
    
    def test_removing_edge_changes_reasoning_chain(self):
        kg = LegalKnowledgeGraph()
        kg.add_legal_rule("r1", "X", "Y", 0.9)
        kg.add_legal_rule("r2", "Y", "Z", 0.9)
        
        entities = [
            {"id": "X", "label": "X", "type": "Condition"},
            {"id": "Y", "label": "Y", "type": "Intermediate"},
            {"id": "Z", "label": "Z", "type": "Conclusion"},
        ]
        relationships = [
            {"source_id": "X", "target_id": "Y", "type": "IMPLIES"},
            {"source_id": "Y", "target_id": "Z", "type": "IMPLIES"},
        ]
        
        builder = UltraGraphBuilder()
        builder.build_graph(entities, relationships)
        reasoner = ChainOfThoughtReasoner(kg, graph=builder)
        result_full = reasoner.reason("سوال", "کانتکست", facts=["X"])
        
        builder.remove_edge("Y", "Z")
        reasoner_ablation = ChainOfThoughtReasoner(kg, graph=builder)
        result_ablation = reasoner_ablation.reason("سوال", "کانتکست", facts=["X"])
        
        assert len(result_full["graph_edges_used"]) > len(result_ablation["graph_edges_used"])
        assert result_full["answer"] != result_ablation["answer"]
        assert not any(edge[1] == "Z" for edge in result_ablation["graph_edges_used"])


class _MockResolver:
    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, str]] = {}
        self.create_calls = 0
        self.link_calls = 0

    def find_candidates(
        self,
        name: str,
        normalized: str,
        fuzzy: str,
        entity_type: str,
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        for canonical_id, payload in self.nodes.items():
            if payload["entity_type"] != entity_type:
                continue
            candidates.append(
                Candidate(
                    node_id=payload["node_id"],
                    name=payload["name"],
                    entity_type=payload["entity_type"],
                    identities=payload["identities"],
                    canonical_id=canonical_id,
                )
            )
        return candidates

    def create_node(
        self,
        canonical_id: str,
        entity_type: str,
        name: str,
        identities: Dict[str, str],
    ) -> str:
        node_id = f"node:{canonical_id}"
        if canonical_id not in self.nodes:
            self.create_calls += 1
            self.nodes[canonical_id] = {
                "node_id": node_id,
                "name": name,
                "entity_type": entity_type,
                "identities": identities,
            }
        return node_id

    def record_link(
        self,
        mention: EntityMention,
        node_id: str,
        canonical_id: Optional[str],
        confidence: float,
        score,
    ) -> None:
        self.link_calls += 1


class TestSemanticGraphLinking:
    def test_deterministic_linking(self):
        resolver = _MockResolver()
        linker = GraphLinker(resolver)
        mention = EntityMention(
            name="رای وحدت رویه ۸۰۵",
            entity_type="UNIFICATION_RULING",
            identities={"ruling_no": "805"},
            provenance={"doc_id": "d1"},
        )

        first = linker.link_entity(mention)
        second = linker.link_entity(mention)

        assert first.canonical_id == second.canonical_id
        assert first.resolved_node_id == second.resolved_node_id
        assert resolver.create_calls == 1

    def test_no_uncontrolled_creation(self):
        resolver = _MockResolver()
        linker = GraphLinker(resolver)
        mention = EntityMention(
            name="وزارت راه",
            entity_type="ORG",
            identities={},
            provenance={"doc_id": "d2"},
        )

        result = linker.link_entity(mention)

        assert result.action == "UNRESOLVED"
        assert resolver.create_calls == 0

    def test_dedup_unification_ruling(self):
        resolver = _MockResolver()
        linker = GraphLinker(resolver)
        mention_1 = EntityMention(
            name="رای وحدت رویه ۸۰۵",
            entity_type="UNIFICATION_RULING",
            identities={"ruling_no": "805"},
            provenance={"doc_id": "d3"},
        )
        mention_2 = EntityMention(
            name="رای وحدت رویه ۸۰۵",
            entity_type="UNIFICATION_RULING",
            identities={"ruling_no": "805"},
            provenance={"doc_id": "d4"},
        )

        result_1 = linker.link_entity(mention_1)
        result_2 = linker.link_entity(mention_2)

        assert result_1.canonical_id == result_2.canonical_id
        assert result_1.resolved_node_id == result_2.resolved_node_id
        assert resolver.create_calls == 1

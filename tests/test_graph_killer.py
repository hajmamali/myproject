"""
Graph-Killer Tests
==================

این تست‌ها ثابت می‌کنند که Reasoning واقعاً به ساختار گراف وابسته است.
"""

from typing import List

import pytest

from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
from mahoun.reasoning.chain_of_thought import ChainOfThoughtReasoner


def _build_chain_entities(labels: List[str]) -> List[dict]:
    return [
        {"id": label, "label": label, "type": "Node"}
        for label in labels
    ]


@pytest.mark.graph_native
class TestGraphKiller:
    """مجموعه تست‌های Graph-Killer"""
    
    def test_reasoning_breaks_without_edges(self):
        """
        Graph-Killer #1:
        زمانی که هیچ edgeای وجود ندارد، نباید زنجیره کامل شود.
        """
        kg = LegalKnowledgeGraph()
        kg.add_legal_rule("r1", "قرارداد امضا شده", "تعهد ایجاد می‌شود", 0.9)
        kg.add_legal_rule("r2", "تعهد ایجاد می‌شود", "باید اجرا شود", 0.9)
        kg.add_legal_rule("r3", "باید اجرا شود", "خسارت باید پرداخت شود", 0.9)
        
        entities = _build_chain_entities([
            "قرارداد امضا شده",
            "تعهد ایجاد می‌شود",
            "باید اجرا شود",
            "خسارت باید پرداخت شود",
        ])
        
        # بدون edge
        builder_no_edges = UltraGraphBuilder()
        builder_no_edges.build_graph(entities, relationships=[])
        
        reasoner_without_edges = ChainOfThoughtReasoner(kg, graph=builder_no_edges)
        result_without = reasoner_without_edges.reason(
            question="اگر قرارداد امضا شود و اجرا نشود چه می‌شود؟",
            context="قرارداد امضا شده اما اجرا نشده است.",
            facts=["قرارداد امضا شده"]
        )
        
        targets_without = {edge[1] for edge in result_without["graph_edges_used"]}
        assert "تعهد ایجاد می‌شود" not in targets_without, "نباید edgeای ثبت شود"
        assert "خسارت باید پرداخت شود" not in result_without["answer"]
        assert result_without["limitations"] == "graph_missing_or_empty"
        
        # با edges کامل
        builder_with_edges = UltraGraphBuilder()
        relationships = [
            {"source_id": "قرارداد امضا شده", "target_id": "تعهد ایجاد می‌شود", "type": "IMPLIES"},
            {"source_id": "تعهد ایجاد می‌شود", "target_id": "باید اجرا شود", "type": "IMPLIES"},
            {"source_id": "باید اجرا شود", "target_id": "خسارت باید پرداخت شود", "type": "IMPLIES"},
        ]
        builder_with_edges.build_graph(entities, relationships)
        
        reasoner_with_edges = ChainOfThoughtReasoner(kg, graph=builder_with_edges)
        result_with = reasoner_with_edges.reason(
            question="اگر قرارداد امضا شود و اجرا نشود چه می‌شود؟",
            context="قرارداد امضا شده اما اجرا نشده است.",
            facts=["قرارداد امضا شده"]
        )
        
        assert any(
            edge[1] == "خسارت باید پرداخت شود"
            for edge in result_with["graph_edges_used"]
        ), "باید به گره نهایی برسد"
        assert "خسارت باید پرداخت شود" in result_with["answer"]
    
    def test_output_changes_when_path_changes(self):
        """
        Graph-Killer #2:
        تغییر مسیر گراف باید خروجی reasoning را تغییر دهد.
        """
        kg = LegalKnowledgeGraph()
        kg.add_legal_rule("r1", "A", "B", 0.9)
        kg.add_legal_rule("r2", "B", "C", 0.9)
        kg.add_legal_rule("r3", "B", "D", 0.9)
        
        entities = _build_chain_entities(["A", "B", "C", "D"])
        
        # مسیر به سمت C
        builder_path_c = UltraGraphBuilder()
        relationships_c = [
            {"source_id": "A", "target_id": "B", "type": "IMPLIES"},
            {"source_id": "B", "target_id": "C", "type": "IMPLIES"},
        ]
        builder_path_c.build_graph(entities, relationships_c)
        reasoner_c = ChainOfThoughtReasoner(kg, graph=builder_path_c)
        result_c = reasoner_c.reason("سوال", "کانتکست", facts=["A"])
        
        assert "C" in result_c["answer"], "باید به C برسد"
        edges_to_c = [edge for edge in result_c["graph_edges_used"] if edge[1] == "C"]
        assert edges_to_c, "Edge به C باید استفاده شود"
        
        # مسیر به سمت D
        builder_path_d = UltraGraphBuilder()
        relationships_d = [
            {"source_id": "A", "target_id": "B", "type": "IMPLIES"},
            {"source_id": "B", "target_id": "D", "type": "IMPLIES"},
        ]
        builder_path_d.build_graph(entities, relationships_d)
        reasoner_d = ChainOfThoughtReasoner(kg, graph=builder_path_d)
        result_d = reasoner_d.reason("سوال", "کانتکست", facts=["A"])
        
        assert "D" in result_d["answer"], "باید به D برسد"
        assert result_c["answer"] != result_d["answer"], "تغییر مسیر باید خروجی را عوض کند"
    
    def test_inference_breaks_when_intermediate_node_removed(self):
        """
        Graph-Killer #3:
        حذف node میانی باید زنجیره را بشکند.
        """
        kg = LegalKnowledgeGraph()
        kg.add_legal_rule("r1", "X", "Y", 0.9)
        kg.add_legal_rule("r2", "Y", "Z", 0.9)
        
        entities = _build_chain_entities(["X", "Y", "Z"])
        relationships = [
            {"source_id": "X", "target_id": "Y", "type": "IMPLIES"},
            {"source_id": "Y", "target_id": "Z", "type": "IMPLIES"},
        ]
        
        builder = UltraGraphBuilder()
        builder.build_graph(entities, relationships)
        reasoner = ChainOfThoughtReasoner(kg, graph=builder)
        
        result_full = reasoner.reason("سوال", "کانتکست", facts=["X"])
        assert "Z" in result_full["answer"], "با گراف کامل باید به Z برسد"
        assert any(
            edge[1] == "Z" for edge in result_full["graph_edges_used"]
        ), "Edge منتهی به Z باید ثبت شود"
        
        # حذف Y و edges مرتبط
        builder.remove_node("Y")
        reasoner_after = ChainOfThoughtReasoner(kg, graph=builder)
        result_broken = reasoner_after.reason("سوال", "کانتکست", facts=["X"])
        
        assert "Z" not in result_broken["answer"], "بعد از حذف Y نباید به Z برسد"
        assert not any(
            edge[1] == "Z" for edge in result_broken["graph_edges_used"]
        ), "بدون node میانی نباید edge به Z باشد"

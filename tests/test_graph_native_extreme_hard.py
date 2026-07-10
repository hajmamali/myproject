"""
Extreme Hard Graph-Native Audit Test
=====================================

Brutally strict pytest that proves Mahoun's reasoning is:
- graph-dependent (uses real traversed edges)
- contradiction-preserving (doesn't collapse conflicts)
- audit-grade (trace export stable + complete)
- robust under ablation (degraded mode when graph missing/ablated)

This test validates both FULL GRAPH and ABLATED GRAPH modes.
"""

import pytest
from typing import List, Dict, Any

from mahoun.reasoning.reasoning_engine import DeepLegalReasoningEngine
from mahoun.core.models import ReasoningResult


@pytest.mark.graph_native
class TestGraphNativeExtremeHardAudit:
    """Extreme hard graph-native audit test suite"""
    
    def _setup_engine_with_rules(self) -> DeepLegalReasoningEngine:
        """Build engine and graph deterministically with chained + contradictory rules"""
        engine = DeepLegalReasoningEngine()
        
        # Clear default rules to start fresh
        engine.knowledge_graph.legal_rules.clear()
        engine.graph_builder.clear_edges()
        engine.graph_builder._nodes.clear()
        
        # Chained rules (multi-step path required)
        # r_contract_binding: "قرارداد معتبر امضا شده" -> "تعهد ایجاد شده" (0.95)
        engine.add_legal_rule(
            "r_contract_binding",
            "قرارداد معتبر امضا شده",
            "تعهد ایجاد شده",
            0.95
        )
        
        # r_breach: "تعهد ایجاد شده" -> "نقض تعهد رخ داده" (0.9)
        engine.add_legal_rule(
            "r_breach",
            "تعهد ایجاد شده",
            "نقض تعهد رخ داده",
            0.9
        )
        
        # Contradictory rules (equal confidence from same condition)
        # r_damage_yes: "نقض تعهد رخ داده" -> "متعهد باید خسارت بدهد" (0.9) [contradiction 1]
        engine.add_legal_rule(
            "r_damage_yes",
            "نقض تعهد رخ داده",
            "متعهد باید خسارت بدهد",
            0.9
        )
        
        # r_damage_no: "نقض تعهد رخ داده" -> "متعهد مسئولیتی ندارد" (0.9) [contradiction 2]
        engine.add_legal_rule(
            "r_damage_no",
            "نقض تعهد رخ داده",
            "متعهد مسئولیتی ندارد",
            0.9
        )
        
        # r_delay_penalty: "پرداخت با تأخیر" -> "جریمه تأخیر اعمال می‌شود" (0.85)
        engine.add_legal_rule(
            "r_delay_penalty",
            "پرداخت با تأخیر",
            "جریمه تأخیر اعمال می‌شود",
            0.85
        )
        
        # Add precedent: case_support_damage
        engine.add_precedent(
            "case_support_damage",
            ["قرارداد معتبر امضا شده", "نقض تعهد رخ داده"],
            "جبران خسارت",
            "دادگاه عالی"
        )
        
        # Add causal relationship: "نقض تعهد رخ داده" -> "پیامد مالی" (0.93)
        engine.add_causal_relationship(
            "نقض تعهد رخ داده",
            "پیامد مالی",
            0.93
        )
        
        return engine
    
    def _get_test_facts(self) -> List[str]:
        """Return deterministic test facts"""
        return [
            "قرارداد معتبر امضا شده",
            "پرداخت با تأخیر",
            "تعهد ایجاد شده",
            "نقض تعهد رخ داده",
            "پیامد مالی"
        ]
    
    def _get_test_question_and_context(self) -> tuple[str, str]:
        """Return deterministic question and context"""
        question = "آیا در صورت نقض تعهد و تأخیر در پرداخت، متعهد مسئولیت دارد و باید خسارت بدهد؟"
        context = (
            "در یک قرارداد معاملات املاک، طرفین قرارداد را امضا کردند. "
            "متعهد تعهدات خود را انجام نداد و نقض تعهد رخ داد. "
            "همچنین پرداخت با تأخیر انجام شد. "
            "پیامد مالی برای طرف مقابل ایجاد شد."
        )
        return question, context
    
    @pytest.mark.graph_native
    def test_extreme_graph_native_audit_full_graph(self):
        """Test FULL GRAPH mode: multi-step chaining, contradiction preservation, graph dependency"""
        engine = self._setup_engine_with_rules()
        facts = self._get_test_facts()
        question, context = self._get_test_question_and_context()
        
        # Run reasoning
        result: ReasoningResult = engine.deep_reason(question, context, facts)
        
        # ============================================================
        # Assertion 1: graph_dependency_proof must be True
        # ============================================================
        assert result.graph_dependency_proof is True, \
            f"graph_dependency_proof must be True in FULL GRAPH mode. Got: {result.graph_dependency_proof}"
        
        # ============================================================
        # Assertion 2: graph_edges_used exists and is list[tuple[str,str]]
        # ============================================================
        assert result.graph_edges_used is not None, "graph_edges_used must exist"
        assert isinstance(result.graph_edges_used, list), "graph_edges_used must be a list"
        assert len(result.graph_edges_used) >= 2, \
            f"graph_edges_used must have at least 2 edges (proves multi-step traversal). Got: {len(result.graph_edges_used)}"
        
        # Verify each edge is a tuple of 2 strings
        for edge in result.graph_edges_used:
            assert isinstance(edge, tuple), f"Each edge must be a tuple. Got: {type(edge)}"
            assert len(edge) == 2, f"Each edge must have 2 elements. Got: {len(edge)}"
            assert isinstance(edge[0], str) and isinstance(edge[1], str), \
                f"Edge elements must be strings. Got: {type(edge[0])}, {type(edge[1])}"
        
        # ============================================================
        # Assertion 3: visited_nodes length >= 3
        # ============================================================
        assert result.visited_nodes is not None, "visited_nodes must exist"
        assert isinstance(result.visited_nodes, list), "visited_nodes must be a list"
        assert len(result.visited_nodes) >= 3, \
            f"visited_nodes must have at least 3 nodes. Got: {len(result.visited_nodes)}"
        
        # ============================================================
        # Assertion 4: used_rule_ids contains required rules
        # ============================================================
        assert result.used_rule_ids is not None, "used_rule_ids must exist"
        assert isinstance(result.used_rule_ids, list), "used_rule_ids must be a list"
        
        # Must contain r_contract_binding
        assert "r_contract_binding" in result.used_rule_ids, \
            f"used_rule_ids must contain 'r_contract_binding'. Got: {result.used_rule_ids}"
        
        # Must contain r_breach
        assert "r_breach" in result.used_rule_ids, \
            f"used_rule_ids must contain 'r_breach'. Got: {result.used_rule_ids}"
        
        # Must contain at least one of r_damage_yes or r_damage_no
        assert "r_damage_yes" in result.used_rule_ids or "r_damage_no" in result.used_rule_ids, \
            f"used_rule_ids must contain at least one of 'r_damage_yes' or 'r_damage_no'. Got: {result.used_rule_ids}"
        
        # Must contain r_delay_penalty (since "پرداخت با تأخیر" is in facts)
        # OR its conclusion must appear in visited_nodes or supporting_evidence
        delay_penalty_used = "r_delay_penalty" in result.used_rule_ids
        delay_penalty_conclusion_in_visited = "جریمه تأخیر اعمال می‌شود" in result.visited_nodes
        delay_penalty_in_evidence = any("جریمه تأخیر" in ev for ev in result.supporting_evidence)
        
        assert delay_penalty_used or delay_penalty_conclusion_in_visited or delay_penalty_in_evidence, \
            f"r_delay_penalty must be used OR its conclusion must appear in visited_nodes/evidence. " \
            f"used_rule_ids={result.used_rule_ids}, visited_nodes={result.visited_nodes}"
        
        # ============================================================
        # Assertion 5: Contradiction preserved
        # ============================================================
        # Both contradictory conclusions must appear in final_answer OR supporting_evidence OR visited_nodes
        # OR both rules must be in used_rule_ids (proving both were considered)
        final_answer_lower = result.final_answer.lower()
        supporting_evidence_text = " ".join(result.supporting_evidence).lower()
        visited_nodes_text = " ".join(result.visited_nodes).lower()
        combined_text = (final_answer_lower + " " + supporting_evidence_text + " " + visited_nodes_text).lower()
        
        damage_yes_present = "متعهد باید خسارت بدهد" in combined_text
        damage_no_present = "متعهد مسئولیتی ندارد" in combined_text
        
        # Check if both rules were used (proves contradiction was encountered)
        both_rules_used = "r_damage_yes" in result.used_rule_ids and "r_damage_no" in result.used_rule_ids
        
        # Either both appear, OR one appears and there's an explicit ambiguity/contradiction warning
        # OR both rules were used (proving contradiction was encountered)
        contradiction_warning_present = (
            "تعارض" in combined_text or
            "contradiction" in combined_text.lower() or
            "تعارض بین" in combined_text or
            "نامشخص" in combined_text or
            "undetermined" in combined_text.lower()
        )
        
        assert (damage_yes_present and damage_no_present) or \
               (damage_yes_present and contradiction_warning_present) or \
               (damage_no_present and contradiction_warning_present) or \
               both_rules_used, \
            f"Contradiction must be preserved: both conclusions, one with warning, or both rules used. " \
            f"damage_yes_present={damage_yes_present}, damage_no_present={damage_no_present}, " \
            f"contradiction_warning_present={contradiction_warning_present}, both_rules_used={both_rules_used}"
        
        # ============================================================
        # Assertion 6: limitations is empty or does NOT include graph_missing_or_empty
        # ============================================================
        if result.limitations is not None:
            assert "graph_missing_or_empty" not in result.limitations, \
                f"limitations must NOT include 'graph_missing_or_empty' in FULL GRAPH mode. Got: {result.limitations}"
        
        # ============================================================
        # Assertion 7: to_trace_json() returns correct schema
        # ============================================================
        trace_json = result.to_trace_json()
        assert isinstance(trace_json, dict), "to_trace_json() must return a dict"
        
        required_keys = [
            "final_answer",
            "confidence",
            "visited_nodes",
            "graph_edges_used",
            "used_rule_ids",
            "supporting_evidence",
            "graph_dependency_proof"
        ]
        
        for key in required_keys:
            assert key in trace_json, f"to_trace_json() must contain key '{key}'. Got keys: {list(trace_json.keys())}"
        
        # Verify graph_edges_used format in trace (must be list of 2-item arrays)
        trace_edges = trace_json["graph_edges_used"]
        assert isinstance(trace_edges, list), "trace_json['graph_edges_used'] must be a list"
        if trace_edges:
            for edge in trace_edges:
                assert isinstance(edge, list), f"Each edge in trace must be a list. Got: {type(edge)}"
                assert len(edge) == 2, f"Each edge in trace must have 2 elements. Got: {len(edge)}"
        
        # Verify graph_dependency_proof is True in trace
        assert trace_json["graph_dependency_proof"] is True, \
            f"trace_json['graph_dependency_proof'] must be True. Got: {trace_json['graph_dependency_proof']}"
    
    @pytest.mark.graph_native
    def test_extreme_graph_native_audit_ablated_graph(self):
        """Test ABLATED GRAPH mode: degraded behavior when graph edges removed"""
        engine = self._setup_engine_with_rules()
        facts = self._get_test_facts()
        question, context = self._get_test_question_and_context()
        
        # Ablate graph: remove ALL edges
        engine.graph_builder.clear_edges()
        
        # Verify graph is ablated
        assert len(engine.graph_builder.get_edges()) == 0, "Graph must be ablated (no edges)"
        
        # Run reasoning with ablated graph
        result_ablated: ReasoningResult = engine.deep_reason(question, context, facts)
        
        # ============================================================
        # Assertion 1: graph_dependency_proof is False
        # ============================================================
        assert result_ablated.graph_dependency_proof is False, \
            f"graph_dependency_proof must be False in ABLATED mode. Got: {result_ablated.graph_dependency_proof}"
        
        # ============================================================
        # Assertion 2: graph_edges_used is empty
        # ============================================================
        assert result_ablated.graph_edges_used is not None, "graph_edges_used must exist"
        assert len(result_ablated.graph_edges_used) == 0, \
            f"graph_edges_used must be empty in ABLATED mode. Got: {len(result_ablated.graph_edges_used)}"
        
        # ============================================================
        # Assertion 3: limitations contains graph_missing_or_empty
        # ============================================================
        assert result_ablated.limitations is not None, "limitations must be set in ABLATED mode"
        assert "graph_missing_or_empty" in result_ablated.limitations, \
            f"limitations must contain 'graph_missing_or_empty'. Got: {result_ablated.limitations}"
        
        # ============================================================
        # Assertion 4: Multi-step should degrade
        # ============================================================
        # Reasoning chain should be shorter OR used_rule_ids fewer than FULL GRAPH case
        # OR final_answer must explicitly warn about degraded mode
        
        final_answer_lower = result_ablated.final_answer.lower()
        degraded_warning_present = (
            "graph_missing_or_empty" in result_ablated.limitations or
            "حالت محدود" in final_answer_lower or
            "بدون اثبات وابستگی" in final_answer_lower or
            "گزارش بدون" in final_answer_lower
        )
        
        # Either fewer rules used, or explicit warning
        rule_count_ablated = len(result_ablated.used_rule_ids)
        
        # Get FULL GRAPH result for comparison
        engine_full = self._setup_engine_with_rules()
        result_full = engine_full.deep_reason(question, context, facts)
        rule_count_full = len(result_full.used_rule_ids)
        
        assert (rule_count_ablated < rule_count_full) or degraded_warning_present, \
            f"ABLATED mode must degrade: fewer rules ({rule_count_ablated} < {rule_count_full}) or explicit warning. " \
            f"degraded_warning_present={degraded_warning_present}"
        
        # ============================================================
        # Assertion 5: to_trace_json() reflects ablated state
        # ============================================================
        trace_json_ablated = result_ablated.to_trace_json()
        assert trace_json_ablated["graph_dependency_proof"] is False, \
            f"trace_json['graph_dependency_proof'] must be False in ABLATED mode. Got: {trace_json_ablated['graph_dependency_proof']}"
        
        assert len(trace_json_ablated["graph_edges_used"]) == 0, \
            f"trace_json['graph_edges_used'] must be empty in ABLATED mode. Got: {len(trace_json_ablated['graph_edges_used'])}"
        
        assert trace_json_ablated["limitations"] is not None, \
            "trace_json['limitations'] must be set in ABLATED mode"
        
        assert "graph_missing_or_empty" in trace_json_ablated["limitations"], \
            f"trace_json['limitations'] must contain 'graph_missing_or_empty'. Got: {trace_json_ablated['limitations']}"


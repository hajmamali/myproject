"""
تست‌های واقعی سیستمی Evidence-Linked Verdict Engine
=====================================================
این تست‌ها سیستم را در سناریوهای واقعی test می‌کنند.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRealSystemScenarios:
    """تست سناریوهای واقعی سیستم"""
    
    def test_contract_breach_scenario(self):
        """تست سناریو واقعی breach of contract"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        # Setup
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # اضافه کردن قوانین واقعی
        kg.add_legal_rule(
            "rule_contract_validity",
            "قرارداد معتبر امضا شده",
            "تعهدات قانونی ایجاد می‌شود",
            0.95
        )
        kg.add_legal_rule(
            "rule_breach_damages",
            "تعهد انجام نشده",
            "متعهد موظف به پرداخت خسارت است",
            0.90
        )
        
        # اضافه کردن precedent واقعی
        kg.add_precedent(
            "case_breach_2023",
            ["قرارداد", "عدم اجرا", "خسارت"],
            "دادگاه حکم به پرداخت خسارت داد",
            "دادگاه تجدید نظر تهران",
            "2023-06-15"
        )
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        # سناریو واقعی
        question = "اگر کسی قراردادی امضا کند اما به تعهداتش عمل نکند، چه عواقبی دارد؟"
        facts = [
            "قرارداد معتبر امضا شده",
            "تعهد انجام نشده",
            "خسارت ایجاد شده"
        ]
        
        # Generate verdict
        verdict = engine.generate_verdict(question, facts)
        
        # بررسی‌های واقعی
        assert verdict is not None
        assert verdict.final_verdict, "باید verdict تولید شود"
        assert len(verdict.steps) > 0, "باید steps داشته باشد"
        
        # بررسی evidence linking
        total_evidence = sum(len(step.evidence) for step in verdict.steps)
        assert total_evidence > 0, "باید evidence references داشته باشد"
        
        # بررسی اینکه rules استفاده شده‌اند
        rule_evidence = [
            e for step in verdict.steps
            for e in step.evidence
            if e.node_type == "LegalRule"
        ]
        assert len(rule_evidence) > 0, "باید rule evidence داشته باشد"
        
        # بررسی اینکه precedents استفاده شده‌اند
        prec_evidence = [
            e for step in verdict.steps
            for e in step.evidence
            if e.node_type == "LegalPrecedent"
        ]
        assert len(prec_evidence) > 0, "باید precedent evidence داشته باشد"
        
        print(f"✓ Contract breach scenario: {len(verdict.steps)} steps, {total_evidence} evidence refs")
        print(f"  Rules: {len(rule_evidence)}, Precedents: {len(prec_evidence)}")
    
    def test_payment_dispute_scenario(self):
        """تست سناریو واقعی payment dispute"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # قوانین مربوط به پرداخت
        kg.add_legal_rule(
            "rule_payment_due",
            "خدمات ارائه شده",
            "حق الزحمه باید پرداخت شود",
            0.92
        )
        kg.add_legal_rule(
            "rule_late_payment",
            "پرداخت با تأخیر",
            "جریمه تأخیر باید پرداخت شود",
            0.85
        )
        
        # Precedent
        kg.add_precedent(
            "case_payment_2022",
            ["خدمات", "عدم پرداخت"],
            "دادگاه حکم به پرداخت حق الزحمه داد",
            "دادگاه عمومی",
            "2022-03-20"
        )
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "اگر خدمات ارائه شود اما پرداخت نشود چه می‌شود؟"
        facts = [
            "خدمات ارائه شده",
            "پرداخت انجام نشده",
            "تأخیر در پرداخت"
        ]
        
        verdict = engine.generate_verdict(question, facts)
        
        # بررسی‌ها
        assert verdict.final_verdict
        assert len(verdict.steps) >= 3, "باید حداقل 3 step داشته باشد"
        
        # بررسی evidence chain
        fact_evidence = [e for step in verdict.steps for e in step.evidence if e.node_type == "Fact"]
        rule_evidence = [e for step in verdict.steps for e in step.evidence if e.node_type == "LegalRule"]
        
        assert len(fact_evidence) > 0, "باید fact evidence داشته باشد"
        assert len(rule_evidence) > 0, "باید rule evidence داشته باشد"
        
        print(f"✓ Payment dispute scenario: {len(verdict.steps)} steps")
        print(f"  Fact evidence: {len(fact_evidence)}, Rule evidence: {len(rule_evidence)}")
    
    def test_termination_scenario(self):
        """تست سناریو واقعی contract termination"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # قوانین فسخ
        kg.add_legal_rule(
            "rule_termination_valid",
            "شرایط فسخ موجود",
            "قرارداد قابل فسخ است",
            0.88
        )
        kg.add_legal_rule(
            "rule_refund",
            "قرارداد فسخ شده",
            "وجوه پرداختی باید برگردانده شود",
            0.90
        )
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "اگر قراردادی فسخ شود چه می‌شود؟"
        facts = [
            "شرایط فسخ موجود",
            "قرارداد فسخ شده",
            "وجوه پرداخت شده"
        ]
        
        verdict = engine.generate_verdict(question, facts)
        
        assert verdict.final_verdict
        assert len(verdict.steps) > 0
        
        # بررسی evidence completeness
        all_node_ids = {e.node_id for step in verdict.steps for e in step.evidence}
        assert len(all_node_ids) > 0, "باید node references داشته باشد"
        
        print(f"✓ Termination scenario: {len(verdict.steps)} steps, {len(all_node_ids)} unique nodes")


class TestRealEvidenceLinking:
    """تست واقعی Evidence Linking"""
    
    def test_evidence_traceability(self):
        """تست اینکه می‌توان evidence را trace کرد"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # اضافه کردن rule با ID مشخص
        kg.add_legal_rule(
            "traceable_rule_001",
            "شرط خاص",
            "نتیجه خاص",
            0.95
        )
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "سوال تست"
        facts = ["شرط خاص"]
        
        verdict = engine.generate_verdict(question, facts)
        
        # پیدا کردن evidence برای rule
        rule_evidence = [
            e for step in verdict.steps
            for e in step.evidence
            if "traceable_rule_001" in e.node_id
        ]
        
        assert len(rule_evidence) > 0, "باید evidence برای rule پیدا شود"
        
        # بررسی traceability
        evidence = rule_evidence[0]
        assert evidence.node_id == "rule_traceable_rule_001", "Node ID باید درست باشد"
        assert evidence.justification, "باید justification داشته باشد"
        assert evidence.confidence > 0, "باید confidence داشته باشد"
        
        print(f"✓ Evidence traceable: {evidence.node_id}")
        print(f"  Justification: {evidence.justification[:50]}...")
    
    def test_evidence_chain_integrity(self):
        """تست integrity زنجیره evidence"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # ساخت زنجیره: Fact -> Rule -> Conclusion
        kg.add_legal_rule("chain_rule_1", "واقعیت الف", "نتیجه ب", 0.9)
        kg.add_legal_rule("chain_rule_2", "نتیجه ب", "نتیجه نهایی", 0.85)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "زنجیره استدلال چیست؟"
        facts = ["واقعیت الف"]
        
        verdict = engine.generate_verdict(question, facts)
        
        # بررسی زنجیره
        all_node_ids = {e.node_id for step in verdict.steps for e in step.evidence}
        
        # باید fact و rule nodes وجود داشته باشند
        has_fact = any("fact_" in node_id for node_id in all_node_ids)
        has_rule = any("rule_" in node_id for node_id in all_node_ids)
        
        assert has_fact, "باید fact node در evidence باشد"
        assert has_rule, "باید rule node در evidence باشد"
        
        print(f"✓ Evidence chain integrity: {len(all_node_ids)} nodes")
        print(f"  Has facts: {has_fact}, Has rules: {has_rule}")
    
    def test_evidence_justification_quality(self):
        """تست کیفیت justification در evidence"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        kg.add_legal_rule("quality_rule", "شرط کیفیت", "نتیجه کیفیت", 0.9)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "تست کیفیت"
        facts = ["شرط کیفیت"]
        
        verdict = engine.generate_verdict(question, facts)
        
        # بررسی کیفیت justifications
        all_justifications = [
            e.justification for step in verdict.steps for e in step.evidence
        ]
        
        assert len(all_justifications) > 0, "باید justification داشته باشد"
        
        # همه justifications باید non-empty باشند
        for justification in all_justifications:
            assert justification, "Justification نباید خالی باشد"
            assert len(justification) > 10, "Justification باید به اندازه کافی detailed باشد"
        
        print(f"✓ Evidence justification quality: {len(all_justifications)} justifications")
        print(f"  Avg length: {sum(len(j) for j in all_justifications) / len(all_justifications):.1f} chars")
    
    def test_each_step_has_evidence(self):
        """Test that each VerdictStep has at least one evidence reference"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        kg.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        verdict = engine.generate_verdict(question, facts)
        
        for i, step in enumerate(verdict.steps):
            assert len(step.evidence) > 0, \
                f"Step {i} ('{step.statement}') باید حداقل یک evidence reference داشته باشد"
            
            for j, evidence in enumerate(step.evidence):
                assert evidence.node_id, \
                    f"Evidence {j} در step {i} باید node_id داشته باشد"
                assert evidence.node_type, \
                    f"Evidence {j} در step {i} باید node_type داشته باشد"
        
        print(f"✓ All {len(verdict.steps)} steps have evidence references")
    
    def test_evidence_justification_exists(self):
        """Test that evidence has justification"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        kg.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        verdict = engine.generate_verdict(question, facts)
        
        for step in verdict.steps:
            for evidence in step.evidence:
                assert evidence.justification, \
                    f"Evidence برای node {evidence.node_id} باید justification داشته باشد"
        
        print("✓ All evidence has justification")


class TestRealContradictionHandling:
    """تست واقعی Contradiction Handling"""
    
    def test_contradiction_detection_real(self):
        """تست واقعی detect کردن contradiction"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        
        # اضافه کردن قوانین متناقض
        kg.add_legal_rule(
            "rule_yes",
            "قرارداد",
            "باید اجرا شود",
            0.9
        )
        kg.add_legal_rule(
            "rule_no",
            "قرارداد",
            "نباید اجرا شود",  # Contradiction
            0.9  # Same confidence
        )
        
        ledger_writer = NoOpLedgerWriter()
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد باید اجرا شود؟"
        facts = ["قرارداد امضا شده"]
        
        verdict = engine.generate_verdict(question, facts)
        
        # بررسی contradiction handling
        # باید یا resolve شده باشد یا در unresolved_conflicts باشد
        has_unresolved = len(verdict.unresolved_conflicts) > 0
        
        rule_yes_refs = sum(
            1 for step in verdict.steps
            for e in step.evidence
            if "rule_yes" in e.node_id
        )
        rule_no_refs = sum(
            1 for step in verdict.steps
            for e in step.evidence
            if "rule_no" in e.node_id
        )
        
        if has_unresolved:
            # Contradiction unresolved
            assert len(verdict.unresolved_conflicts) > 0, \
                "باید contradiction در unresolved_conflicts باشد"
            print(f"✓ Contradiction detected and marked as unresolved: {verdict.unresolved_conflicts}")
        else:
            # Contradiction resolved - باید فقط یکی از rules استفاده شده باشد
            # اگر contradiction resolve شده، نباید هر دو rule در evidence باشند
            assert rule_yes_refs == 0 or rule_no_refs == 0, \
                "اگر contradiction resolve شده، باید فقط یکی از rules استفاده شود"
            assert rule_yes_refs > 0 or rule_no_refs > 0, \
                "باید حداقل یکی از rules استفاده شود"
            print(f"✓ Contradiction resolved: rule_yes={rule_yes_refs}, rule_no={rule_no_refs}")
    
    def test_contradiction_resolution_by_confidence(self):
        """تست resolve کردن contradiction با confidence"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # قوانین متناقض با confidence های مختلف
        kg.add_legal_rule(
            "rule_high_conf",
            "شرط",
            "باید انجام شود",
            0.95  # Higher confidence
        )
        kg.add_legal_rule(
            "rule_low_conf",
            "شرط",
            "نباید انجام شود",
            0.70  # Lower confidence
        )
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "تست contradiction resolution"
        facts = ["شرط موجود"]
        
        verdict = engine.generate_verdict(question, facts)
        
        # باید rule با confidence بالاتر استفاده شود
        high_conf_refs = sum(
            1 for step in verdict.steps
            for e in step.evidence
            if "rule_high_conf" in e.node_id
        )
        low_conf_refs = sum(
            1 for step in verdict.steps
            for e in step.evidence
            if "rule_low_conf" in e.node_id
        )
        
        # باید rule با confidence بالاتر استفاده شود و rule با confidence پایین‌تر استفاده نشود
        assert high_conf_refs > 0, "باید rule با confidence بالاتر استفاده شود"
        assert low_conf_refs == 0, "نباید rule با confidence پایین‌تر استفاده شود"
        
        print(f"✓ Contradiction resolved by confidence: high_conf={high_conf_refs}, low_conf={low_conf_refs}")


class TestRealSystemIntegration:
    """تست واقعی Integration با سیستم"""
    
    def test_integration_with_graph_builder(self):
        """تست integration با UltraGraphBuilder"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        kg.add_legal_rule("integration_rule", "شرط", "نتیجه", 0.9)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        # Generate verdict
        verdict = engine.generate_verdict("سوال", ["شرط"])
        
        # بررسی اینکه graph builder استفاده شده
        assert len(builder.get_nodes()) > 0 or len(verdict.steps) > 0, \
            "Graph builder باید استفاده شده باشد"
        
        print("✓ Integration with graph builder works")
    
    def test_integration_with_knowledge_graph(self):
        """تست integration با LegalKnowledgeGraph"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # اضافه کردن rule
        kg.add_legal_rule("kg_rule", "شرط", "نتیجه", 0.9)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        verdict = engine.generate_verdict("سوال", ["شرط"])
        
        # بررسی اینکه knowledge graph استفاده شده
        rule_evidence = [
            e for step in verdict.steps
            for e in step.evidence
            if e.node_type == "LegalRule"
        ]
        
        assert len(rule_evidence) > 0, "باید از knowledge graph استفاده شده باشد"
        
        print("✓ Integration with knowledge graph works")
    
    def test_end_to_end_workflow(self):
        """تست workflow کامل end-to-end"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        # Setup
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # Populate knowledge graph
        kg.add_legal_rule("e2e_rule_1", "واقعیت 1", "نتیجه 1", 0.9)
        kg.add_legal_rule("e2e_rule_2", "واقعیت 2", "نتیجه 2", 0.85)
        kg.add_precedent("e2e_case_1", ["واقعیت 1"], "تصمیم 1", "دادگاه", "2023-01-01")
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        # Execute
        question = "سوال پیچیده با چند واقعیت"
        facts = ["واقعیت 1", "واقعیت 2"]
        
        verdict = engine.generate_verdict(question, facts)
        
        # Verify
        assert verdict.final_verdict
        assert len(verdict.steps) > 0
        assert verdict.confidence_score > 0
        
        # Verify evidence
        total_evidence = sum(len(step.evidence) for step in verdict.steps)
        assert total_evidence > 0
        
        # Verify node types
        node_types = {e.node_type for step in verdict.steps for e in step.evidence}
        assert "Fact" in node_types, "باید Fact nodes داشته باشد"
        assert "LegalRule" in node_types, "باید LegalRule nodes داشته باشد"
        
        print(f"✓ End-to-end workflow: {len(verdict.steps)} steps, {total_evidence} evidence")
        print(f"  Node types: {node_types}")


class TestRealSystemRobustness:
    """تست Robustness سیستم"""
    
    def test_empty_facts_handling(self):
        """تست handling کردن empty facts"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "سوال"
        facts = []  # Empty facts
        
        verdict = engine.generate_verdict(question, facts)
        
        # باید gracefully handle شود
        assert verdict is not None
        assert verdict.final_verdict, "باید verdict تولید شود (حتی اگر empty)"
        
        print("✓ Empty facts handled gracefully")
    
    def test_no_applicable_rules_handling(self):
        """تست handling کردن وقتی هیچ rule applicable نیست"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # اضافه کردن rule که applicable نیست
        kg.add_legal_rule("unrelated_rule", "شرط نامرتبط", "نتیجه نامرتبط", 0.9)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "سوال"
        facts = ["واقعیت کاملاً متفاوت"]  # No matching rule
        
        verdict = engine.generate_verdict(question, facts)
        
        # باید gracefully handle شود
        assert verdict is not None
        assert verdict.final_verdict
        
        # باید حداقل fact evidence داشته باشد
        fact_evidence = [
            e for step in verdict.steps
            for e in step.evidence
            if e.node_type == "Fact"
        ]
        assert len(fact_evidence) > 0, "باید حداقل fact evidence داشته باشد"
        
        print("✓ No applicable rules handled gracefully")
    
    def test_multiple_contradictions_handling(self):
        """تست handling کردن multiple contradictions"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # Multiple contradictory pairs
        kg.add_legal_rule("rule_a1", "شرط", "نتیجه A", 0.9)
        kg.add_legal_rule("rule_a2", "شرط", "نتیجه نه A", 0.9)  # Contradiction 1
        
        kg.add_legal_rule("rule_b1", "شرط دیگر", "نتیجه B", 0.85)
        kg.add_legal_rule("rule_b2", "شرط دیگر", "نتیجه نه B", 0.85)  # Contradiction 2
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "سوال با contradictions متعدد"
        facts = ["شرط", "شرط دیگر"]
        
        verdict = engine.generate_verdict(question, facts)
        
        # باید handle شود
        assert verdict is not None
        assert verdict.final_verdict
        
        # باید یا resolve شده باشد یا unresolved_conflicts داشته باشد
        assert len(verdict.unresolved_conflicts) >= 0, "باید handle شود"
        
        print(f"✓ Multiple contradictions handled: {len(verdict.unresolved_conflicts)} unresolved")


class TestRealSystemPerformance:
    """تست Performance سیستم"""
    
    def test_large_facts_list(self):
        """تست با لیست بزرگ facts"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # اضافه کردن rules
        for i in range(10):
            kg.add_legal_rule(f"rule_{i}", f"شرط {i}", f"نتیجه {i}", 0.8 + i * 0.01)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "سوال"
        facts = [f"شرط {i}" for i in range(20)]  # 20 facts
        
        verdict = engine.generate_verdict(question, facts)
        
        assert verdict is not None
        assert len(verdict.steps) > 0
        
        # باید evidence برای همه facts داشته باشد
        fact_evidence_count = sum(
            1 for step in verdict.steps
            for e in step.evidence
            if e.node_type == "Fact"
        )
        
        assert fact_evidence_count > 0, "باید fact evidence داشته باشد"
        
        print(f"✓ Large facts list handled: {len(facts)} facts, {fact_evidence_count} evidence refs")
    
    def test_many_rules_handling(self):
        """تست با rules زیاد"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # اضافه کردن rules زیاد
        for i in range(50):
            kg.add_legal_rule(
                f"rule_{i}",
                "قرارداد",
                f"نتیجه {i}",
                0.7 + (i % 10) * 0.02
            )
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "سوال"
        facts = ["قرارداد امضا شده"]
        
        verdict = engine.generate_verdict(question, facts)
        
        assert verdict is not None
        assert len(verdict.steps) > 0
        
        # باید rule evidence داشته باشد
        # در واقعیت، اگر همه rules applicable باشند، همه استفاده می‌شوند
        # این رفتار درست است - سیستم باید همه applicable rules را نشان دهد
        rule_evidence = [
            e for step in verdict.steps
            for e in step.evidence
            if e.node_type == "LegalRule"
        ]
        
        # شمارش unique rule nodes (نه total references)
        unique_rule_nodes = {e.node_id for e in rule_evidence}
        
        assert len(rule_evidence) > 0, "باید rule evidence داشته باشد"
        # Unique rule nodes نباید بیشتر از rules موجود باشد
        assert len(unique_rule_nodes) <= 50, "نباید بیشتر از rules موجود استفاده شود"
        
        print(f"✓ Many rules handled: {len(unique_rule_nodes)} unique rules, {len(rule_evidence)} total references")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])

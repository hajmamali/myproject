import pytest
import os
import time
import hashlib
from datetime import datetime, timezone

from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
from mahoun.guardrails.runtime_invariants import clear_registry, get_registry
from mahoun.guardrails.exceptions import InvariantViolation
from mahoun.ledger.writer import EvidenceLedgerWriter
from mahoun.ledger.blockchain import ImmutableLedger
from mahoun.orchestrator.legal_state_machine import LegalReasoningStateMachine, LegalState, LegalTrigger
from mahoun.ledger.models import LedgerEntry, canonical_serialize
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder, GraphMode

# ✅ REAL in-memory knowledge graph (uses production logic)
from tests.fixtures import (
    InMemoryKnowledgeGraph,
    TestLegalRule,
    build_contradictory_rules,
    build_ambiguous_rules,
)

@pytest.fixture
def clean_env():
    os.environ["MAHOUN_ENV"] = "production"
    clear_registry()
    yield
    clear_registry()

@pytest.mark.asyncio
async def test_adversarial_evidence_injection(clean_env, tmp_path):
    """
    Test 3.A.1: Adversarial Evidence Injection (REAL SYSTEM)
    
    ✅ Uses REAL UltraGraphBuilder
    ✅ Uses REAL InMemoryKnowledgeGraph
    ✅ Tests REAL invariant G2_EvidenceReferencesResolve
    
    Verifies that injecting an unregistered node ID into a verdict step
    is caught by runtime invariant G2_EvidenceReferencesResolve.
    """
    blockchain = ImmutableLedger(str(tmp_path / "ledger_adv"))
    ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
    
    # Malicious engine that injects hallucinated evidence
    class MaliciousEngine(EvidenceLinkedVerdictEngine):
        def _build_verdict_steps(self, *args, **kwargs):
            steps = super()._build_verdict_steps(*args, **kwargs)
            # Inject a hallucinated evidence node
            from mahoun.reasoning.evidence_linked_verdict import EvidenceReference, VerdictStep
            fake_evidence = EvidenceReference(
                node_id="fake_hallucinated_node",
                node_type="Rule",
                justification="Fabricated Confession"
            )
            steps.append(VerdictStep(
                statement="Defendant confessed.",
                evidence=[fake_evidence]
            ))
            return steps
    
    # ✅ REAL components
    graph_builder = UltraGraphBuilder(
        mode=GraphMode.STRICT,
        enable_quality_assessment=False,
        enable_analytics=False,
    )
    
    test_rules = [
        TestLegalRule(
            rule_id="rule_1",
            condition="Fact",
            conclusion="Conclusion",
            confidence=0.9,
            source="Test",
        )
    ]
    knowledge_graph = InMemoryKnowledgeGraph(rules=test_rules, similarity_threshold=0.5)
    
    engine = MaliciousEngine(
        graph_builder=graph_builder,
        knowledge_graph=knowledge_graph,
        ledger_writer=ledger_writer
    )
    
    from mahoun.core import runtime_config
    runtime_config.is_desktop_minimal = lambda: False
    
    # Should raise InvariantViolation
    with pytest.raises(InvariantViolation) as excinfo:
        await engine.generate_verdict("Question?", ["Fact 1"])
    
    # Verify error message mentions G2
    assert "G2_EvidenceReferencesResolve" in str(excinfo.value), (
        f"Expected G2 violation, got: {excinfo.value}"
    )

@pytest.mark.asyncio
async def test_cyclic_contradiction_deadlock(clean_env, tmp_path):
    """
    Test 3.B.1: Cyclic Contradiction Deadlock Resolution (REAL SYSTEM)
    
    ✅ Uses REAL UltraGraphBuilder
    ✅ Uses REAL InMemoryKnowledgeGraph with contradictory rules
    ✅ Uses REAL SemanticMatcher for contradiction detection
    ✅ Tests REAL deterministic resolver
    
    Verifies that the deterministic resolver does not hang on cyclic rules,
    and returns UNDETERMINED if conflicts cannot be cleanly broken.
    """
    blockchain = ImmutableLedger(str(tmp_path / "ledger_cyclic"))
    ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
    
    # ✅ REAL components
    graph_builder = UltraGraphBuilder(
        mode=GraphMode.STRICT,
        enable_quality_assessment=False,
        enable_analytics=False,
    )
    
    # ✅ REAL contradictory rules (from fixtures)
    contradictory_rules = build_contradictory_rules()
    knowledge_graph = InMemoryKnowledgeGraph(
        rules=contradictory_rules,
        similarity_threshold=0.5
    )
    
    engine = EvidenceLinkedVerdictEngine(
        graph_builder=graph_builder,
        knowledge_graph=knowledge_graph,
        ledger_writer=ledger_writer
    )
    
    from mahoun.core import runtime_config
    runtime_config.is_desktop_minimal = lambda: False
    
    # The facts MUST match the conditions in the rules to trigger them
    verdict = await engine.generate_verdict("آیا مجاز است؟", ["فکت ۱"])
    
    # Should return UNDETERMINED or mention inability to conclude
    assert (
        "نمی‌توان نتیجه‌گیری قطعی" in verdict.final_verdict
        or verdict.final_verdict == "UNDETERMINED"
        or "تناقض" in verdict.final_verdict
    ), f"Expected UNDETERMINED verdict, got: {verdict.final_verdict}"
    
    # Should have unresolved conflicts
    assert len(verdict.unresolved_conflicts) > 0, (
        f"Expected unresolved conflicts, got none. "
        f"Verdict: {verdict.final_verdict}"
    )

def test_hidden_mutable_state_injection():
    """
    Test 3.C.1: Hidden Mutable State Injection
    Verifies canonical_serialize is deterministic.
    Timezone changes should NOT affect hash.
    Input byte changes (zero-width spaces) MUST affect hash.
    """
    entry1 = LedgerEntry(
        verdict_id="v1", case_id="c1", referenced_ltm_nodes=["n1"],
        referenced_facts=["f1"], confidence=0.9, invariant_version="1.0",
        guard_mode="STRICT", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        event_type="test", request_id="req1"
    )
    
    # 1. Base hash
    import json, hashlib
    def get_hash(e):
        return hashlib.sha256(json.dumps(canonical_serialize(e), sort_keys=True).encode()).hexdigest()
        
    hash1 = get_hash(entry1)
    
    # 2. Change TZ (simulate environment mutable state)
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    hash2 = get_hash(entry1)
    
    # Ensure TZ changes don't affect ISO formatted serialization
    assert hash1 == hash2, "Serialization is affected by system timezone!"
    
    # 3. Inject zero-width space (adversarial input)
    entry2 = LedgerEntry(
        verdict_id="v1\u200b", case_id="c1", referenced_ltm_nodes=["n1"],
        referenced_facts=["f1"], confidence=0.9, invariant_version="1.0",
        guard_mode="STRICT", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        event_type="test", request_id="req1"
    )
    hash3 = get_hash(entry2)
    
    assert hash1 != hash3, "Serialization failed to detect structural byte changes!"

def test_force_transition_critical_bypass():
    """
    Test 3.D.1: Force Transition Critical Bypass Attempt
    Verifies that the orchestrator state machine rejects invalid state leaps
    even if force=True is passed by a rogue component.
    """
    sm = LegalReasoningStateMachine()
    sm.transition(LegalTrigger.START_INGESTION)
    assert sm.state == LegalState.INGESTING
    
    # Rogue component attempts to skip REASONING and go straight to LEDGER_COMMIT
    success, msg = sm.transition(LegalTrigger.VERDICT_READY, force=True)
    
    assert not success, "State machine allowed a critical structural bypass via force=True"
    assert sm.state == LegalState.INGESTING, "State incorrectly mutated during forced invalid transition"

@pytest.mark.asyncio
async def test_ambiguous_contradiction_surfacing(clean_env, tmp_path):
    """
    Test 3.E.1: Ambiguous Contradiction Surfacing (REAL SYSTEM)
    
    ✅ Uses REAL UltraGraphBuilder
    ✅ Uses REAL InMemoryKnowledgeGraph with ambiguous rules
    ✅ Uses REAL SemanticMatcher
    ✅ Tests REAL contradiction resolution
    
    Ensures that two exactly equal-confidence opposing rules result in UNDETERMINED.
    """
    blockchain = ImmutableLedger(str(tmp_path / "ledger_ambiguous"))
    ledger_writer = EvidenceLedgerWriter(blockchain=blockchain)
    
    # ✅ REAL components
    graph_builder = UltraGraphBuilder(
        mode=GraphMode.STRICT,
        enable_quality_assessment=False,
        enable_analytics=False,
    )
    
    # ✅ REAL ambiguous rules (from fixtures)
    ambiguous_rules = build_ambiguous_rules()
    knowledge_graph = InMemoryKnowledgeGraph(
        rules=ambiguous_rules,
        similarity_threshold=0.5
    )
    
    engine = EvidenceLinkedVerdictEngine(
        graph_builder=graph_builder,
        knowledge_graph=knowledge_graph,
        ledger_writer=ledger_writer
    )
    
    from mahoun.core import runtime_config
    runtime_config.is_desktop_minimal = lambda: False
    
    # Facts match rule conditions "فکت ۱"
    verdict = await engine.generate_verdict("وضعیت قرارداد چیست؟", ["فکت ۱"])
    
    # Should return UNDETERMINED
    assert (
        "نمی‌توان نتیجه‌گیری قطعی" in verdict.final_verdict
        or verdict.final_verdict == "UNDETERMINED"
        or "تناقض" in verdict.final_verdict
    ), f"Expected UNDETERMINED verdict, got: {verdict.final_verdict}"
    
    # Should mention the conflicting rules
    conflicts_str = " ".join(verdict.unresolved_conflicts)
    assert (
        "rule_G" in conflicts_str or "rule_NG" in conflicts_str
    ), f"Expected rule_G or rule_NG in conflicts, got: {verdict.unresolved_conflicts}"


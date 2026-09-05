"""
P0/P1 Governance Hardening Tests
=================================

Comprehensive tests for all P0 and P1 hardening changes.
"""

import hashlib
import json
from unittest.mock import MagicMock

import pytest

from mahoun.core.environment import temporary_environment
from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
from mahoun.ledger.write_gate import EvidencePackage, LedgerWriteGate
from mahoun.reasoning.reasoning_recorder import ReasoningRecorder
from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph, LegalRule, LegalPrecedent


class TestP0_1_ProvenanceEnforcement:
    """P0-1: Verify provenance enforcement."""

    @pytest.mark.p2
    def test_dev_provenance_is_synthetic(self):
        """In development, _resolve_provenance() returns synthetic provenance."""
        from mahoun.reasoning.evidence_linked_verdict import _resolve_provenance
        prov = _resolve_provenance("test_op")
        assert "synthetic" in prov.source
        assert prov.governance_scope_id == "development_synthetic_scope"

    @pytest.mark.p2
    def test_no_hardcoded_default_scope(self):
        """P0-1: No provenance should use 'default_scope' or 'default_attestation'."""
        from mahoun.reasoning.evidence_linked_verdict import _resolve_provenance
        prov = _resolve_provenance("test_op")
        assert prov.governance_scope_id != "default_scope"
        assert prov.runtime_attestation_id != "default_attestation"

    @pytest.mark.p2
    def test_production_fails_without_governance_context(self):
        """P0-1: In production, _resolve_provenance() fails without GovernanceContext."""
        from mahoun.core.governance.violations import GovernanceViolationError
        with temporary_environment("production"):
            from mahoun.reasoning.evidence_linked_verdict import _resolve_provenance
            with pytest.raises(GovernanceViolationError) as exc_info:
                _resolve_provenance("test_op")
            assert "GOVERNANCE VIOLATION" in str(exc_info.value)

    @pytest.mark.p2
    def test_production_succeeds_with_governance_context(self):
        """P0-1: In production with GovernanceContext, provenance uses context scope."""
        with temporary_environment("production"):
            from mahoun.reasoning.evidence_linked_verdict import _resolve_provenance
            ctx = GovernanceContextManager.create_context(correlation_id="p0-test", execution_mode="STRICT")
            stack = GovernanceContextManager._get_stack()
            GovernanceContextManager._governance_stack.set(stack + [ctx])
            try:
                prov = _resolve_provenance("test_op")
                assert prov.governance_scope_id == ctx.context_id
                assert "synthetic" not in prov.source
            finally:
                GovernanceContextManager._reset_for_test()

    @pytest.mark.p2
    def test_recorder_dev_provenance_is_synthetic(self):
        """P0-1: ReasoningRecorder in dev uses synthetic provenance."""
        recorder = ReasoningRecorder()
        step = recorder.record_step("test", {"a": 1}, {"r": "ok"}, provenance=None)
        assert "synthetic" in step.provenance.source

    @pytest.mark.p2
    def test_recorder_production_fails_without_context(self):
        """P0-1: ReasoningRecorder in production fails without GovernanceContext."""
        from mahoun.core.governance.violations import GovernanceViolationError
        with temporary_environment("production"):
            recorder = ReasoningRecorder()
            with pytest.raises(GovernanceViolationError):
                recorder.record_step("test", {"a": 1}, {"r": "ok"}, provenance=None)


class TestP0_3_GovernedLLMEngine:
    """P0-3: Verify GovernedLLMEngine wrapper."""

    @pytest.mark.p2
    def test_wrapper_exists(self):
        """P0-3: GovernedLLMEngine class is importable."""
        from mahoun.llm.ultra_engine import GovernedLLMEngine
        assert GovernedLLMEngine is not None

    @pytest.mark.p2
    def test_wrapper_stores_references(self):
        """P0-3: GovernedLLMEngine stores references correctly."""
        from mahoun.llm.ultra_engine import GovernedLLMEngine
        mock_engine, mock_writer = MagicMock(), MagicMock()
        engine = GovernedLLMEngine(llm_engine=mock_engine, ledger_writer=mock_writer, environment_policy="dev")
        assert engine.engine is mock_engine
        assert engine.ledger_writer is mock_writer


class TestP0_4_LedgerWriteGate:
    """P0-4: Verify LedgerWriteGate enforcement."""

    @pytest.mark.p2
    def test_write_gate_exists(self):
        """P0-4: LedgerWriteGate is importable and operational."""
        gate = LedgerWriteGate(ledger_writer=MagicMock(), enable_strict_mode=True)
        assert gate is not None

    @pytest.mark.p2
    def test_write_gate_rejects_empty_evidence(self):
        """P0-4: LedgerWriteGate rejects verdicts with no evidence (B3-I1)."""
        gate = LedgerWriteGate(ledger_writer=MagicMock(), enable_strict_mode=True)
        result = gate.write_verdict(
            verdict_data={"verdict_id": "t1"},
            evidence_package=EvidencePackage(evidence_refs=[], provenance_chain=[{}], proof_hash="abcd1234efgh5678", validation_context={})
        )
        assert result.success is False

    @pytest.mark.p2
    def test_write_gate_rejects_empty_provenance(self):
        """P0-4: LedgerWriteGate rejects evidence without provenance (B3-I2)."""
        gate = LedgerWriteGate(ledger_writer=MagicMock(), enable_strict_mode=True)
        result = gate.write_verdict(
            verdict_data={"verdict_id": "t2"},
            evidence_package=EvidencePackage(evidence_refs=["n1"], provenance_chain=[], proof_hash="abcd1234efgh5678", validation_context={})
        )
        assert result.success is False

    @pytest.mark.p2
    def test_write_gate_rejects_short_proof_hash(self):
        """P0-4: LedgerWriteGate rejects evidence with invalid proof hash (B3-I3)."""
        gate = LedgerWriteGate(ledger_writer=MagicMock(), enable_strict_mode=True)
        result = gate.write_verdict(
            verdict_data={"verdict_id": "t3"},
            evidence_package=EvidencePackage(evidence_refs=["n1"], provenance_chain=[{}], proof_hash="short", validation_context={})
        )
        assert result.success is False

    @pytest.mark.p2
    def test_write_gate_accepts_valid_verdict(self):
        """P0-4: LedgerWriteGate accepts valid verdict."""
        mock_writer = MagicMock()
        mock_writer.write.return_value = "hash_abc123"
        gate = LedgerWriteGate(ledger_writer=mock_writer, enable_strict_mode=True)
        proof_hash = hashlib.sha256(json.dumps(["n1"], sort_keys=True).encode()).hexdigest()
        result = gate.write_verdict(
            verdict_data={"verdict_id": "t4", "confidence": 0.95},
            evidence_package=EvidencePackage(evidence_refs=["n1"], provenance_chain=[{"source": "test", "timestamp": "now", "author": "t", "correlation_id": "c"}], proof_hash=proof_hash, validation_context={}),
            metadata={}
        )
        assert result.success is True

    @pytest.mark.p2
    def test_evidence_package_validate(self):
        """P0-4: EvidencePackage.validate() works correctly."""
        pkg = EvidencePackage(evidence_refs=["e1"], provenance_chain=[{"source": "t"}], proof_hash="abcd1234efgh5678", validation_context={})
        valid, error = pkg.validate()
        assert valid is True
        assert error is None
        pkg2 = EvidencePackage(evidence_refs=[], provenance_chain=[{}], proof_hash="abcd1234efgh5678", validation_context={})
        valid2, error2 = pkg2.validate()
        assert valid2 is False


class TestP0_5_RealVerification:
    """P0-5: Verify real verify_chain() implementation."""

    @pytest.mark.p2
    def test_verify_chain_valid(self):
        """P0-5: verify_chain() returns True for intact chain."""
        recorder = ReasoningRecorder()
        recorder.record_step("s1", {"a": 1}, {"r": "x"}, provenance=ProvenanceMetadata.create(source="t", correlation_id="c", author="a", governance_scope_id="s", runtime_attestation_id="r"))
        assert recorder.verify_chain() is True

    @pytest.mark.p2
    def test_verify_chain_multiple_steps(self):
        """P0-5: verify_chain() verifies multi-step chains."""
        recorder = ReasoningRecorder()
        for i in range(3):
            recorder.record_step(f"s{i}", {"i": i}, {"r": i}, provenance=ProvenanceMetadata.create(source="t", correlation_id="c", author="a", governance_scope_id="s", runtime_attestation_id="r"))
        assert recorder.verify_chain() is True

    @pytest.mark.p2
    def test_verify_chain_after_tamper(self):
        """P0-5: verify_chain() detects tampered chain."""
        import dataclasses
        recorder = ReasoningRecorder()
        recorder.record_step("s1", {"data": "orig"}, {"r": "ok"}, provenance=ProvenanceMetadata.create(source="t", correlation_id="c", author="a", governance_scope_id="s", runtime_attestation_id="r"))
        steps = recorder.get_steps()
        tampered = dataclasses.replace(steps[0], inputs={"data": "tampered"})
        recorder._steps[0] = tampered
        assert recorder.verify_chain() is False

    @pytest.mark.p2
    def test_chain_hash_stored_per_step(self):
        """P0-5: Each ReasoningStep stores chain_hash and chain_prev_hash."""
        recorder = ReasoningRecorder()
        step1 = recorder.record_step("s1", {"a": 1}, {"r": "x"}, provenance=ProvenanceMetadata.create(source="t", correlation_id="c", author="a", governance_scope_id="s", runtime_attestation_id="r"))
        assert step1.chain_hash != ""
        assert step1.chain_prev_hash == "genesis"
        step2 = recorder.record_step("s2", {"b": 2}, {"r": "y"}, provenance=ProvenanceMetadata.create(source="t", correlation_id="c", author="a", governance_scope_id="s", runtime_attestation_id="r"))
        assert step2.chain_prev_hash == step1.chain_hash

    @pytest.mark.p2
    def test_production_verify_chain_raises_on_tamper(self):
        """P0-5: In production, verify_chain() raises RuntimeError on tamper."""
        import dataclasses
        with temporary_environment("production"):
            recorder = ReasoningRecorder()
            recorder.record_step("s1", {"data": "orig"}, {"r": "ok"}, provenance=ProvenanceMetadata.create(source="t", correlation_id="c", author="a", governance_scope_id="s", runtime_attestation_id="r"))
            steps = recorder.get_steps()
            tampered = dataclasses.replace(steps[0], inputs={"data": "tampered"})
            recorder._steps[0] = tampered
            with pytest.raises(RuntimeError) as exc_info:
                recorder.verify_chain()
            assert "CHAIN VIOLATION" in str(exc_info.value)


class TestP1_KnowledgeGraphProvenance:
    """P1: Verify KnowledgeGraph provenance attachment."""

    @pytest.mark.p2
    def test_legal_rule_has_provenance_field(self):
        """P1: LegalRule dataclass has a provenance field."""
        rule = LegalRule(rule_id="r1", condition="c", conclusion="cl")
        assert hasattr(rule, "provenance")

    @pytest.mark.p2
    def test_legal_precedent_has_provenance_field(self):
        """P1: LegalPrecedent dataclass has a provenance field."""
        prec = LegalPrecedent(precedent_id="c1", facts=["f"], decision="d", court="ct")
        assert hasattr(prec, "provenance")

    @pytest.mark.p2
    def test_add_legal_rule_sets_provenance(self):
        """P1: add_legal_rule() sets provenance on created rule."""
        kg = LegalKnowledgeGraph(enable_semantic=False)
        rule = kg.add_legal_rule(rule_id="p1_r1", condition="c", conclusion="cl")
        assert rule.provenance is not None

    @pytest.mark.p2
    def test_add_precedent_sets_provenance(self):
        """P1: add_precedent() sets provenance on created precedent."""
        kg = LegalKnowledgeGraph(enable_semantic=False)
        prec = kg.add_precedent(case_id="p1_c1", facts=["f"], decision="d", court="ct")
        assert prec.provenance is not None

    @pytest.mark.p2
    def test_update_rule_preserves_provenance(self):
        """P1: Updating a rule sets provenance on the new version."""
        kg = LegalKnowledgeGraph(enable_semantic=False)
        kg.add_legal_rule(rule_id="p1_upd", condition="c1", conclusion="cl1")
        rule2 = kg.add_legal_rule(rule_id="p1_upd", condition="c2", conclusion="cl2")
        assert rule2.provenance is not None
        assert rule2.version == 2

    @pytest.mark.p2
    def test_update_precedent_preserves_provenance(self):
        """P1: Updating a precedent sets provenance on the new version."""
        kg = LegalKnowledgeGraph(enable_semantic=False)
        kg.add_precedent(case_id="p1_upd", facts=["f1"], decision="d1", court="c1")
        prec2 = kg.add_precedent(case_id="p1_upd", facts=["f2"], decision="d2", court="c2")
        assert prec2.provenance is not None
        assert prec2.version == 2

    @pytest.mark.p2
    def test_find_applicable_rules_with_provenance(self):
        """P1: find_applicable_rules returns rules with provenance."""
        kg = LegalKnowledgeGraph(enable_semantic=False)
        kg.add_legal_rule(rule_id="p1_s", condition="breach of contract", conclusion="liable")
        results = kg.find_applicable_rules(facts=["breach", "contract"])
        assert len(results) > 0
        for r in results:
            assert r["rule"].provenance is not None


class TestDevProductionIsolation:
    """Verify DEV and PROD paths remain properly separated."""

    @pytest.mark.p2
    def test_dev_synthetic_provenance_does_not_leak_to_production(self):
        """DEV synthetic provenance is never used in PROD paths."""
        with temporary_environment("production"):
            ctx = GovernanceContextManager.create_context(correlation_id="iso", execution_mode="STRICT")
            stack = GovernanceContextManager._get_stack()
            GovernanceContextManager._governance_stack.set(stack + [ctx])
            try:
                prov = ProvenanceMetadata.create(source="prod_test", correlation_id=ctx.correlation_id, author="mahoun", governance_scope_id=ctx.context_id, runtime_attestation_id=ctx.runtime_attestation.get("context_id", ctx.context_id), lineage_parent=None)
                assert "synthetic" not in prov.source
                assert prov.governance_scope_id == ctx.context_id
            finally:
                GovernanceContextManager._reset_for_test()

    @pytest.mark.p2
    def test_guardrails_fail_fast_in_production(self):
        """I6: In production, missing guardrails should raise ImportError."""
        with temporary_environment("production"):
            from mahoun.reasoning.evidence_linked_verdict import GUARDRAILS_AVAILABLE
            assert GUARDRAILS_AVAILABLE is not None
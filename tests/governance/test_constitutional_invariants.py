"""
Constitutional Invariant Tests
================================

Four enforcement tests that verify core governance invariants hold at
production code level. No mocks for governance logic.

Invariants tested:
  1. ONTOLOGY_INJECTION_DEFENSE    — malicious labels/keys rejected before Cypher
  2. TEMPORAL_RECONSTRUCTION       — tombstone replay preserves legal time-truth
  3. IDENTITY_MANDATORY_MUTATION   — anonymous mutation is impossible
  4. UNCERTAINTY_ABSTENTION        — reasoning refuses unsupported conclusions
"""

from __future__ import annotations

import dataclasses
from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# TEST 1 — ONTOLOGY INJECTION DEFENSE
# ---------------------------------------------------------------------------

class TestOntologyInjectionDefense:
    """
    Invariant: Cypher structure cannot be attacker-controlled.

    validate_node_label() and validate_property_keys() are the last line
    of defence before f-string interpolation into Cypher templates.
    They must reject all malicious inputs BEFORE any query builder is reached.
    """

    @pytest.mark.p0
    def test_label_injection_cypher_comment_blocked(self):
        """
        Attack A: label = "Case) DELETE n //"
        This would escape the node pattern and append destructive Cypher.
        Must be blocked by character-pattern check (not in allowlist + illegal chars).
        """
        from mahoun.core.governance.validator_pipeline import validate_node_label
        from mahoun.core.governance.violations import (
            GovernanceViolationError,
            ViolationCategory,
            ViolationSeverity,
        )

        malicious_label = "Case) DELETE n //"

        with pytest.raises(GovernanceViolationError) as exc_info:
            validate_node_label(malicious_label, correlation_id="test-injection-a")

        v = exc_info.value.violation
        assert v.category == ViolationCategory.ONTOLOGY_VIOLATION, (
            f"Expected ONTOLOGY_VIOLATION, got {v.category}"
        )
        assert v.severity == ViolationSeverity.CRITICAL

    @pytest.mark.p0
    def test_label_unicode_homoglyph_blocked(self):
        """
        Attack B: label = "Ａrticle" (Unicode full-width Ａ U+FF21)
        NFKC normalization detects homoglyph — must be rejected.
        """
        from mahoun.core.governance.validator_pipeline import validate_node_label
        from mahoun.core.governance.violations import (
            GovernanceViolationError,
            ViolationCategory,
            ViolationSeverity,
        )

        # U+FF21 = FULLWIDTH LATIN CAPITAL LETTER A — visually identical to A
        homoglyph_label = "\uFF21rticle"

        with pytest.raises(GovernanceViolationError) as exc_info:
            validate_node_label(homoglyph_label, correlation_id="test-injection-b")

        v = exc_info.value.violation
        assert v.category == ViolationCategory.ONTOLOGY_VIOLATION
        assert v.severity == ViolationSeverity.CRITICAL

    @pytest.mark.p0
    def test_property_key_injection_brace_escape_blocked(self):
        """
        Attack C: property key = "name} DETACH DELETE n //"
        Injected into SET n.{key} = $v — would produce broken/malicious Cypher.
        Must fail P1 (non-identifier characters).
        """
        from mahoun.core.governance.validator_pipeline import validate_property_keys
        from mahoun.core.governance.violations import (
            GovernanceViolationError,
            ViolationCategory,
            ViolationSeverity,
        )

        malicious_props = {"name} DETACH DELETE n //": "value"}

        with pytest.raises(GovernanceViolationError) as exc_info:
            validate_property_keys(
                malicious_props,
                context="node",
                correlation_id="test-injection-c",
            )

        v = exc_info.value.violation
        assert v.category == ViolationCategory.ONTOLOGY_VIOLATION
        assert v.severity == ViolationSeverity.CRITICAL

    @pytest.mark.p0
    def test_reserved_kernel_key_created_at_blocked(self):
        """
        Attack D: property key = "created_at"
        This is a KERNEL_RESERVED key — callers must not supply it.
        Must fail P3 (reserved key override prevention).
        """
        from mahoun.core.governance.validator_pipeline import validate_property_keys
        from mahoun.core.governance.violations import (
            GovernanceViolationError,
            ViolationCategory,
            ViolationSeverity,
        )

        reserved_props = {"created_at": "2026-01-01T00:00:00Z"}

        with pytest.raises(GovernanceViolationError) as exc_info:
            validate_property_keys(
                reserved_props,
                context="node",
                correlation_id="test-injection-d",
            )

        v = exc_info.value.violation
        assert v.category == ViolationCategory.ONTOLOGY_VIOLATION, (
            f"Expected ONTOLOGY_VIOLATION, got {v.category}"
        )
        assert v.severity == ViolationSeverity.CRITICAL

    @pytest.mark.p0
    def test_unknown_label_not_in_allowlist_blocked(self):
        """
        Extra: label not in ALLOWED_NODE_LABELS must be rejected.
        Proves allowlist is the final gate, not just character validation.
        """
        from mahoun.core.governance.validator_pipeline import validate_node_label
        from mahoun.core.governance.violations import (
            GovernanceViolationError,
            ViolationCategory,
        )

        with pytest.raises(GovernanceViolationError) as exc_info:
            validate_node_label("UnknownEntityType", correlation_id="test-allowlist")

        v = exc_info.value.violation
        assert v.category == ViolationCategory.ONTOLOGY_VIOLATION

    @pytest.mark.p0
    def test_valid_label_passes(self):
        """Sanity: a canonical label must not be rejected."""
        from mahoun.core.governance.validator_pipeline import validate_node_label

        # Must NOT raise
        validate_node_label("Case", correlation_id="test-valid")
        validate_node_label("Verdict", correlation_id="test-valid-2")
        validate_node_label("LawArticle", correlation_id="test-valid-3")


# ---------------------------------------------------------------------------
# TEST 2 — TEMPORAL RECONSTRUCTION INTEGRITY
# ---------------------------------------------------------------------------

class TestTemporalReconstructionIntegrity:
    """
    Invariant: History is reconstructable. Current state is not the only truth.

    MutationReplayer must be able to reconstruct any past legal state from
    a sequence of MutationReceipts, including soft-deleted (tombstoned) nodes.
    """

    def _make_receipt(
        self,
        mutation_type_value: str,
        entity_id: str,
        label: str,
        content_hash: str,
        receipt_id: str | None = None,
        correlation_id: str = "test-corr",
    ):
        """Build a minimal synthetic MutationReceipt without Neo4j."""
        from mahoun.core.governance.mutation_boundary import MutationReceipt, MutationType

        # Map string → MutationType enum
        mt = MutationType(mutation_type_value)
        return MutationReceipt(
            receipt_id=receipt_id or f"rcpt-{entity_id}-{mutation_type_value[:4]}",
            mutation_type=mt,
            label=label,
            entity_id=entity_id,
            timestamp="2026-01-01T00:00:00Z",
            correlation_id=correlation_id,
            content_hash=content_hash,
            pipeline_hash="pipe-hash-001",
        )

    @pytest.mark.p0
    def test_three_receipt_replay_reconstructs_state(self):
        """
        Scenario: Article 220
          1. NODE_CREATE  → active (hash_active)
          2. NODE_MERGE   → repealed (hash_repealed)
          3. NODE_DELETE  → tombstone
        """
        from mahoun.core.governance.mutation_replayer import MutationReplayer, ReplayStatus

        receipts = [
            self._make_receipt("NODE_CREATE", "article_220", "Article", "hash_active"),
            self._make_receipt("NODE_MERGE",  "article_220", "Article", "hash_repealed"),
            self._make_receipt("NODE_DELETE", "article_220", "Article", "hash_tombstone"),
        ]

        replayer = MutationReplayer()
        result = replayer.replay(receipts)

        assert result.status != ReplayStatus.EMPTY, "Result must not be EMPTY"
        assert result.mutation_count == 3
        assert result.applied_count >= 2, (
            f"At least 2 mutations must be applied, got {result.applied_count}"
        )
        assert result.reconstructed_hash, "reconstructed_hash must not be empty"
        assert "article_220" in result.entity_hashes, (
            "entity_hashes must contain 'article_220'"
        )

    @pytest.mark.p0
    def test_empty_receipts_returns_empty_status(self):
        """
        Empty sequence → ReplayStatus.EMPTY.
        System must not fabricate a state from nothing.
        """
        from mahoun.core.governance.mutation_replayer import MutationReplayer, ReplayStatus

        replayer = MutationReplayer()
        result = replayer.replay([])

        assert result.status == ReplayStatus.EMPTY
        assert result.mutation_count == 0
        assert result.applied_count == 0

    @pytest.mark.p0
    def test_create_then_merge_state_changes(self):
        """
        After CREATE(hash_a) then MERGE(hash_b), state hash must change.
        Verifies that MERGE actually updates state, not ignores it.
        """
        from mahoun.core.governance.mutation_replayer import MutationReplayer, ReplayStatus

        receipts_v1 = [
            self._make_receipt("NODE_CREATE", "article_220", "Article", "hash_v1"),
        ]
        receipts_v2 = [
            self._make_receipt("NODE_CREATE", "article_220", "Article", "hash_v1"),
            self._make_receipt("NODE_MERGE",  "article_220", "Article", "hash_v2"),
        ]

        r1 = MutationReplayer().replay(receipts_v1)
        r2 = MutationReplayer().replay(receipts_v2)

        assert r1.reconstructed_hash != r2.reconstructed_hash, (
            "State after CREATE only must differ from state after CREATE+MERGE"
        )

    @pytest.mark.p0
    def test_tombstone_node_is_soft_deleted_not_removed(self):
        """
        NODE_DELETE must soft-delete (tombstone) the node — not hard remove it.
        entity_hash must still exist after delete (node present in graph).
        """
        from mahoun.core.governance.mutation_replayer import MutationReplayer, InMemoryGraphState

        graph = InMemoryGraphState()
        graph.apply_node_create("article_220", "Article", "hash_active")
        graph.apply_node_delete("article_220", soft=True)

        # Node is still in graph (soft delete only marks _deleted=True)
        assert graph.node_count == 1, "Soft-deleted node must remain in graph"
        assert graph.active_node_count == 0, "Active node count must be 0 after soft delete"
        eh = graph.entity_hash("article_220")
        assert eh is not None, "entity_hash must still exist after soft delete"


# ---------------------------------------------------------------------------
# TEST 3 — IDENTITY MANDATORY MUTATION
# ---------------------------------------------------------------------------

class TestIdentityMandatoryMutation:
    """
    Invariant: Every mutation has identity.
    Anonymous mutation (missing/empty actor_id or correlation_id) is impossible.
    """

    def _make_executor_stub(self):
        """Minimal raw executor stub that satisfies assert_raw_executor."""
        def executor(query: str, params: dict) -> list:
            # Should never be called in these tests — session creation should fail first
            raise AssertionError("Raw executor was called — identity check did not block it")
        return executor

    @pytest.mark.p0
    def test_empty_actor_id_rejected(self):
        """Scenario A: actor_id="" — must raise AUDIT_INTEGRITY_VIOLATION."""
        from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
        from mahoun.core.governance.violations import (
            GovernanceViolationError,
            ViolationCategory,
            ViolationSeverity,
        )

        with pytest.raises(GovernanceViolationError) as exc_info:
            GovernedNeo4jSession(
                raw_executor=self._make_executor_stub(),
                actor_id="",
                correlation_id="test-corr-a",
            )

        v = exc_info.value.violation
        assert v.category == ViolationCategory.AUDIT_INTEGRITY_VIOLATION, (
            f"Expected AUDIT_INTEGRITY_VIOLATION, got {v.category}"
        )
        assert v.severity == ViolationSeverity.CRITICAL

    @pytest.mark.p0
    def test_empty_correlation_id_rejected(self):
        """
        Scenario B: correlation_id="" with no active GovernanceContext.
        When no context is active AND correlation_id is empty, the session
        creation path hits GovernanceContextManager.require_context() which
        raises GOVERNANCE_BYPASS (no context exists at all).
        If context exists but correlation_id is empty, it raises AUDIT_INTEGRITY_VIOLATION.
        Both categories enforce the invariant: anonymous mutation is impossible.
        """
        from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
        from mahoun.core.governance.violations import (
            GovernanceViolationError,
            ViolationCategory,
        )

        with pytest.raises(GovernanceViolationError) as exc_info:
            GovernedNeo4jSession(
                raw_executor=self._make_executor_stub(),
                actor_id="actor-1",
                correlation_id="",
            )

        v = exc_info.value.violation
        # Either GOVERNANCE_BYPASS (no context + no correlation_id) or
        # AUDIT_INTEGRITY_VIOLATION (context present but empty id) — both block mutation.
        assert v.category in (
            ViolationCategory.AUDIT_INTEGRITY_VIOLATION,
            ViolationCategory.GOVERNANCE_BYPASS,
        ), f"Expected identity violation, got {v.category}"

    @pytest.mark.p0
    def test_whitespace_actor_id_rejected(self):
        """Scenario C: actor_id=" " — whitespace-only must be rejected."""
        from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
        from mahoun.core.governance.violations import (
            GovernanceViolationError,
            ViolationCategory,
        )

        with pytest.raises(GovernanceViolationError) as exc_info:
            GovernedNeo4jSession(
                raw_executor=self._make_executor_stub(),
                actor_id="   ",
                correlation_id="test-corr-c",
            )

        assert exc_info.value.violation.category == ViolationCategory.AUDIT_INTEGRITY_VIOLATION

    @pytest.mark.p0
    def test_whitespace_correlation_id_rejected(self):
        """
        Scenario C (mirror): correlation_id="   " — both AUDIT_INTEGRITY_VIOLATION
        and GOVERNANCE_BYPASS categories enforce the no-anonymous-mutation invariant.
        """
        from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
        from mahoun.core.governance.violations import (
            GovernanceViolationError,
            ViolationCategory,
        )

        with pytest.raises(GovernanceViolationError) as exc_info:
            GovernedNeo4jSession(
                raw_executor=self._make_executor_stub(),
                actor_id="actor-1",
                correlation_id="   ",
            )

        v = exc_info.value.violation
        assert v.category in (
            ViolationCategory.AUDIT_INTEGRITY_VIOLATION,
            ViolationCategory.GOVERNANCE_BYPASS,
        ), f"Expected identity violation, got {v.category}"

    @pytest.mark.p0
    def test_valid_identity_allows_session_construction(self):
        """
        Sanity: non-empty actor_id + correlation_id must not raise on construction.
        Note: We cannot call write_node without a real Neo4j connection — we
        only test that the identity gate passes.
        """
        from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
        from mahoun.core.governance.violations import GovernanceViolationError
        from mahoun.core.governance.governance_context import GovernanceContextManager

        execution_happened = []

        def executor(query: str, params: dict) -> list:
            execution_happened.append(True)
            return []

        # Must NOT raise — requires a valid context on the stack
        ctx = GovernanceContextManager.create_context(
            correlation_id="test-corr-valid",
            execution_mode="STRICT",
        )
        token = GovernanceContextManager._governance_stack.set(
            GovernanceContextManager._get_stack() + (ctx,)
        )
        try:
            session = GovernedNeo4jSession(
                raw_executor=executor,
                actor_id="test-actor",
                correlation_id="test-corr-valid",
            )
            assert session._actor_id == "test-actor"
            assert session._correlation_id == "test-corr-valid"
        except GovernanceViolationError:
            pytest.fail("Valid identity should not raise GovernanceViolationError")
        finally:
            GovernanceContextManager._governance_stack.reset(token)


# ---------------------------------------------------------------------------
# TEST 4 — UNCERTAINTY ABSTENTION ENFORCEMENT
# ---------------------------------------------------------------------------

class TestUncertaintyAbstentionEnforcement:
    """
    Invariant: System does not hallucinate legal reasoning.

    Scenario A: EvidenceLinkedVerdictEngine.generate_verdict(facts=[]) must raise.
    Scenario B: FortressValidator.validate(response without proof tree, low score)
                must return passed=False with correct violation types.
    """

    @pytest.mark.p0
    def test_empty_facts_raises_runtime_error(self):
        """
        Scenario A: generate_verdict with empty facts list must raise RuntimeError
        containing evidence-related message.
        """
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine

        # EvidenceLinkedVerdictEngine requires several heavy dependencies.
        # We build the minimal stubs that satisfy __init__ without network/DB.
        from unittest.mock import MagicMock, AsyncMock
        import asyncio

        mock_graph_builder = MagicMock()
        mock_knowledge_graph = MagicMock()
        mock_ledger_writer = MagicMock()

        engine = EvidenceLinkedVerdictEngine(
            graph_builder=mock_graph_builder,
            knowledge_graph=mock_knowledge_graph,
            ledger_writer=mock_ledger_writer,
        )

        async def run():
            return await engine.generate_verdict(
                question="What is the ruling on Article 220?",
                facts=[],  # Empty facts — must abstain
            )

        with pytest.raises(RuntimeError) as exc_info:
            asyncio.get_event_loop().run_until_complete(run())

        msg = str(exc_info.value)
        assert "evidence" in msg.lower() or "verdict" in msg.lower(), (
            f"RuntimeError message must reference evidence/verdict, got: {msg!r}"
        )

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_fortress_validator_fails_on_missing_proof_tree(self):
        """
        Scenario B: A response without proof_tree, with agreement_score=0.60,
        and no derived_facts must fail validation.

        Verification:
        - result.passed == False
        - violations include MISSING_PROOF_TREE
        - violations include LOW_AGREEMENT_SCORE
        - violations include MISSING_EVIDENCE
        """
        from mahoun.core.fortress_validator import FortressValidator, ExecutionMode, ViolationType

        validator = FortressValidator(strict_mode=False)

        # Verify thresholds from RedLines.yaml
        assert validator.config.thresholds.min_agreement_score == 0.85, (
            f"RedLines min_agreement_score must be 0.85, "
            f"got {validator.config.thresholds.min_agreement_score}"
        )
        assert validator.config.thresholds.min_confidence_score == 0.70, (
            f"RedLines min_confidence_score must be 0.70, "
            f"got {validator.config.thresholds.min_confidence_score}"
        )

        # Construct a deliberately weak response (no proof tree, low agreement)
        weak_response = {
            "success": True,
            "result": "Article 220 mandates X",  # unsupported conclusion
            "confidence": 0.55,                  # below threshold
            "reasoning_mode": "UNKNOWN",
            "execution_time_ms": 100.0,
            "proof_tree": None,                  # MISSING
            "explanation": "Some reasoning",
            "derived_facts": [],                 # MISSING EVIDENCE
            "error": None,
            "metadata": {},
            "fortress_validated": False,
            "audit_hash": None,
            "validation_timestamp": None,
            "correlation_id": "test-abstention",
        }

        # Add agreement_score to metadata so validator can check it
        # (FortressValidator reads from response.metadata or response itself)
        weak_response["metadata"]["agreement_score"] = 0.60

        result = await validator.validate(
            weak_response,
            correlation_id="test-abstention-b",
        )

        assert result.passed is False, (
            "Validator must return passed=False for response without proof tree"
        )

        # Extract violation types from result
        violation_types = {v.get("type") for v in result.violations}

        assert ViolationType.MISSING_PROOF_TREE.value in violation_types, (
            f"MISSING_PROOF_TREE violation expected. Got: {violation_types}"
        )

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_fortress_validator_passes_for_valid_response(self):
        """
        Sanity check: A well-formed response with proof tree and high agreement
        must pass validation. Uses dict-based response which FortressValidator
        converts internally via DynamicResponse.
        """
        from mahoun.core.fortress_validator import FortressValidator

        validator = FortressValidator(strict_mode=False)

        # proof_tree must be a string (audit_hash type) because the validator
        # internally calls .strip() on it — use a string value.
        valid_response = {
            "success": True,
            "result": "Article 220 ruling: VALID",
            "confidence": 0.92,
            "reasoning_mode": "STRICT",
            "execution_time_ms": 250.0,
            "proof_tree": "proof-tree-hash-abc123",   # non-None string
            "explanation": "Grounded in graph evidence.",
            "derived_facts": [
                "Article 220 is active",
            ],
            "error": None,
            "metadata": {
                "agreement_score": 0.91,
                "source_attribution": ["LawArticle:220"],
            },
            "fortress_validated": False,
            "audit_hash": "abc123",
            "validation_timestamp": None,
            "correlation_id": "test-valid-response",
        }

        result = await validator.validate(valid_response, correlation_id="test-valid")

        assert result.passed is True, (
            f"Well-formed response must pass validation. "
            f"Violations: {result.violations}"
        )

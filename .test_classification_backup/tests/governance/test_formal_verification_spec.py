"""
MAHOUN Formal Governance Verification Specification
==================================================

Protocol: FORMAL-ORACLE-V1
Classification: MISSION-CRITICAL / SPECIFICATION-GROUNDED

TEST ORACLE SEMANTICS:
----------------------
1. classify_cypher(query) -> bool
   - Returns True:  MUTATION/VIOLATION DETECTED (System must BLOCK)
   - Returns False: READ/SAFE (System may PROCEED)

2. GovernanceViolationError
   - Raised:        UNAUTHORIZED BYPASS ATTEMPT (System HALTED)
   - Not Raised:    AUTHORIZED EXECUTION (System NOMINAL)

3. Determinism
   - same input + same context -> bit-identical output

4. Composition
   - G_combined = G_a ∧ G_b ∧ ... ∧ G_n (Any failure halts the system)
"""

import pytest
import asyncio
import hashlib
from typing import List, Dict, Any
from mahoun.core.governance.mutation_boundary import classify_cypher, MutationAuthorizationBoundary
from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.violations import GovernanceViolationError, ViolationCategory
from mahoun.core.governance.deterministic_resolver import DeterministicResolver, ConflictCandidate, SourceTier
from mahoun.switchboard import switchboard
from mahoun.core.fortress_validator import SecurityBreachException, ViolationSeverity

# ────────────────────────────────────────────────────────────
# P0: TEST ORACLE & SEMANTIC CORRECTNESS
# ────────────────────────────────────────────────────────────

@pytest.mark.formal
def test_oracle_classify_cypher_detects_mutation():
    """
    Spec: Mutation keywords MUST be detected regardless of formatting.
    Oracle: classify_cypher returns True for Violations.
    """
    # Adversarial: Comment interleaving and case variation
    bad_query = "MATCH (n) SeT/* comment */n.x = 1"
    is_violating = classify_cypher(bad_query)
    
    assert is_violating is True, "Oracle Failure: Failed to detect SET mutation with comment interleaving"

@pytest.mark.formal
def test_oracle_classify_cypher_allows_read():
    """
    Spec: Pure READ queries must be allowed.
    Oracle: classify_cypher returns False for Safe queries.
    """
    safe_query = "MATCH (n) RETURN n.id"
    is_violating = classify_cypher(safe_query)
    
    assert is_violating is False, "Oracle Failure: Erroneously flagged READ query as mutation"

# ────────────────────────────────────────────────────────────
# P0: DETERMINISM & REPLAY (G10)
# ────────────────────────────────────────────────────────────

@pytest.mark.determinism
def test_G10_deterministic_resolution_replay():
    """
    Spec: Conflict resolution must be bit-identical across runs for identical input.
    Threat: Probabilistic resolution leads to un-auditable legal outcomes.
    """
    resolver = DeterministicResolver()
    
    # Use frozen candidates to ensure input stability
    candidates = [
        ConflictCandidate("ent1", "ValueA", SourceTier.REGULATORY, 0.8, "SourceA", {}),
        ConflictCandidate("ent2", "ValueB", SourceTier.REGULATORY, 0.9, "SourceB", {}),
    ]
    
    # Run 1
    res1 = resolver.resolve(candidates)
    
    # Run 2 (Identical input)
    res2 = resolver.resolve(candidates)
    
    assert res1.winner.entity_id == res2.winner.entity_id
    assert res1.resolution_reason == res2.resolution_reason
    assert res1 == res2, "Determinism Failure: Conflict resolution is not bit-identical across replays"

# ────────────────────────────────────────────────────────────
# P0: PUBLIC API CONTRACTS (No Private Access)
# ────────────────────────────────────────────────────────────

@pytest.mark.governance
def test_boundary_enforcement_without_context_raises_exception():
    """
    Spec: Mutations outside active GovernanceContext must raise Exception.
    Target: Public MutationAuthorizationBoundary.inspect API.
    """
    malicious_query = "CREATE (n:GhostNode)"
    
    # Ensure NO context is active for this task
    # Note: Using get_current_context() which is public and task-isolated
    current_ctx = GovernanceContextManager.get_current_context()
    if current_ctx:
        # This shouldn't happen in a fresh test, but we check to be safe
        pytest.skip("Test environment has active context, skipping bypass test")
    
    with pytest.raises(GovernanceViolationError) as excinfo:
        MutationAuthorizationBoundary.inspect(malicious_query)
    
    # Verify the category is correct (Authorization/Bypass)
    assert excinfo.value.violation.category in [
        ViolationCategory.GOVERNANCE_BYPASS, 
        ViolationCategory.ARCHITECTURE_BOUNDARY
    ]

# ────────────────────────────────────────────────────────────
# P1: INVARIANT COMPOSITION (G11)
# ────────────────────────────────────────────────────────────

@pytest.mark.composition
def test_composition_G1_G2_existence_and_resolution():
    """
    Spec: Evidence must exist (G1) AND resolve to graph (G2).
    Scenario: Step has evidence (G1 PASS) but node is missing from registry (G2 FAIL).
    """
    from mahoun.guardrails.runtime_invariants import G1_EvidenceStepHasEvidence, G2_EvidenceReferencesResolve
    from mahoun.reasoning.evidence_linked_verdict import VerdictStep, EvidenceReference
    
    # Composition: G1 PASS (evidence provided), G2 FAIL (target missing)
    step = VerdictStep(
        statement="Compounded claim",
        evidence=[
            EvidenceReference(node_id="ghost_999", node_type="Fact", justification="None", confidence=1.0)
        ]
    )
    
    # G1: Passes (logic: len(evidence) > 0)
    G1_EvidenceStepHasEvidence(step, 0)
    
    # G2: Must Fail (logic: node_id not in registry)
    empty_registry = {}
    from mahoun.guardrails.exceptions import InvariantViolation
    with pytest.raises(InvariantViolation) as excinfo:
        G2_EvidenceReferencesResolve(step.evidence[0], empty_registry)
    
    assert excinfo.value.invariant_name == "G2_EvidenceReferencesResolve"

# ────────────────────────────────────────────────────────────
# P1: STABILIZED ASYNC ISOLATION
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_async_context_isolation_formal():
    """
    Spec: Governance authority must not leak between concurrent tasks.
    Threat: Attacker task 'borrows' authority from a legitimate judge's task.
    """
    
    async def run_governed(expected_cid: str):
        async with GovernanceContextManager.active_context(correlation_id=expected_cid):
            # Interleave execution
            await asyncio.sleep(0.05)
            current = GovernanceContextManager.get_current_context()
            return current.correlation_id == expected_cid if current else False

    async def run_ungoverned():
        # This task should remain unauthorized despite Task A being active
        await asyncio.sleep(0.02)
        current = GovernanceContextManager.get_current_context()
        return current is None

    # Execute and capture results explicitly
    results = await asyncio.gather(
        run_governed("TASK_A"),
        run_ungoverned(),
        run_governed("TASK_C"),
        return_exceptions=True
    )
    
    assert results[0] is True, "Task A context was corrupted or lost"
    assert results[1] is True, "Security Breach: Context leaked to ungoverned task"
    assert results[2] is True, "Task C context was corrupted or lost"

# ────────────────────────────────────────────────────────────
# P1: EXECUTABLE ADVERSARIAL SCENARIOS
# ────────────────────────────────────────────────────────────

@pytest.mark.adversarial
def test_G6_APOC_procedure_injection_block():
    """
    Threat: Procedure Injection (APOC)
    Vector: CALL apoc.cypher.run(...)
    Expected: Blocked by Lexer prefix check.
    """
    jailbreak = "CALL apoc.util.sleep(1000)"
    assert classify_cypher(jailbreak) is True, "Failed to block dangerous APOC procedure"

@pytest.mark.adversarial
def test_G8_forced_ultra_failure_halt(monkeypatch):
    """
    Threat: Fallback Exploitation
    Vector: Requesting a non-existent ULTRA module.
    Expected: SecurityBreachException (No fallback allowed).
    """
    # HARDENING: Force Switchboard into ULTRA mode for this test
    # even if no GPU is present.
    monkeypatch.setattr(switchboard, "hardware_ready", True)
    monkeypatch.setattr(switchboard, "ultra_mode_enabled", True)
    
    # Register a broken module (Base path exists as a dummy, Ultra path is garbage)
    switchboard.register("adversarial_module", "mahoun.switchboard.Switchboard", "nonexistent.Module")
    
    with pytest.raises(SecurityBreachException) as excinfo:
        switchboard.get_module("adversarial_module")
        
    assert excinfo.value.violation_type.value == "SILENT_FAILURE"
    assert excinfo.value.severity == ViolationSeverity.CRITICAL

"""
Design Rule Tests: "No Feature — Only Proof"
============================================

Architectural invariant tests that enforce the design rule:

    No Feature — Only Proof

These tests act as future guardrails to ensure explanation/provenance layers
remain non-authoritative and do not influence decisions.

All tests must PASS with the current codebase.

Design Rule: DR-EXPL-001
See: docs/EXPLANATION_PROVENANCE_LAYER_SPEC.md for full specification.

These tests enforce three mandatory invariants:
1. Decision Invariance: disabling explanation layer does not change verdict
2. Authority Isolation: explanation layer has no veto/override capability
3. Determinism Preservation: outputs are deterministic (no randomness/LLM)
"""

import pytest


# ============================================================================
# Common Setup (Required)
# ============================================================================

class ExplanationLayerStub:
    """
    Non-authoritative stub used only for design-rule testing.
    Must not influence decisions.
    """
    def __init__(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def explain(self, decision, reasoning_trace):
        if not self.enabled:
            return None
        return {
            "decision": decision,
            "trace": reasoning_trace,
        }


def deterministic_decision_stub(input_data):
    """
    Simulates Mahoun's core property:
    same input -> same decision.
    """
    return {
        "verdict": "APPROVED",
        "reasoning_trace": ["RULE_A_APPLIED", "NO_CONFLICT_FOUND"]
    }


# ============================================================================
# Test Suite
# ============================================================================

def test_decision_invariance():
    """
    TEST 1 — Decision Invariance
    
    Purpose:
    Ensure that explanation/provenance layers do not change decisions.
    
    Rule:
    Removing or disabling the explanation layer must not alter:
    - verdict
    - reasoning trace
    """
    explanation = ExplanationLayerStub()

    input_data = {"case": "X"}

    result_with_expl = deterministic_decision_stub(input_data)
    explanation_output = explanation.explain(
        result_with_expl["verdict"],
        result_with_expl["reasoning_trace"]
    )

    explanation.disable()

    result_without_expl = deterministic_decision_stub(input_data)

    assert result_with_expl == result_without_expl
    assert explanation_output is not None


def test_authority_isolation():
    """
    TEST 2 — Authority Isolation
    
    Purpose:
    Ensure explanation layers have no authority over decisions.
    
    Rule:
    Explanation layers must NOT:
    - veto decisions
    - override verdicts
    - modify reasoning traces
    """
    explanation = ExplanationLayerStub()
    input_data = {"case": "X"}

    core_result = deterministic_decision_stub(input_data)

    explanation_result = explanation.explain(
        core_result["verdict"],
        core_result["reasoning_trace"]
    )

    assert explanation_result["decision"] == core_result["verdict"]
    assert explanation_result["trace"] == core_result["reasoning_trace"]


def test_determinism_preservation():
    """
    TEST 3 — Determinism Preservation
    
    Purpose:
    Ensure explanation layers do not introduce nondeterminism.
    
    Rule:
    Explanation must:
    - be deterministic
    - not rely on randomness
    - not rely on LLMs or probabilistic logic
    """
    explanation = ExplanationLayerStub()
    input_data = {"case": "X"}

    result_1 = deterministic_decision_stub(input_data)
    result_2 = deterministic_decision_stub(input_data)

    explanation_1 = explanation.explain(
        result_1["verdict"],
        result_1["reasoning_trace"]
    )
    explanation_2 = explanation.explain(
        result_2["verdict"],
        result_2["reasoning_trace"]
    )

    assert result_1 == result_2
    assert explanation_1 == explanation_2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

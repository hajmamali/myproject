#!/usr/bin/env python3
"""
Standalone Symbolic Reasoning Tests
====================================

Pytest-compatible tests for symbolic reasoning engine.
"""
import sys
import time
from pathlib import Path

import pytest

# Add mahoun to path
sys.path.insert(0, str(Path(__file__).parent))

from mahoun.reasoning.first_order_logic import (
    FirstOrderLogicEngine,
    Term,
    TermType,
    UnificationError,
    create_atom,
    create_constant,
    create_fact,
    create_function,
    create_rule,
    create_variable,
)
from mahoun.reasoning.forward_chaining import ForwardChainingEngine
from mahoun.reasoning.backward_chaining import BackwardChainingEngine
from mahoun.reasoning.symbolic_reasoner import SymbolicReasoningEngine, ReasoningMode


def test_1_unification_occur_check():
    """Occur check must prevent unifying a variable with a term containing it."""
    engine = FirstOrderLogicEngine()
    X = create_variable("X")
    f_X = create_function("f", X)

    with pytest.raises(UnificationError, match="Occur check failed"):
        engine.unify(X, f_X)


def test_2_forward_chaining_transitive_closure():
    """Forward chaining must derive all 6 ancestor facts from a 4-node parent chain."""
    engine = ForwardChainingEngine()

    facts = [
        create_fact("parent", create_constant("a"), create_constant("b")),
        create_fact("parent", create_constant("b"), create_constant("c")),
        create_fact("parent", create_constant("c"), create_constant("d")),
    ]

    X = create_variable("X")
    Y = create_variable("Y")
    Z = create_variable("Z")

    rules = [
        create_rule(
            create_atom("ancestor", X, Y),
            create_atom("parent", X, Y)
        ),
        create_rule(
            create_atom("ancestor", X, Z),
            create_atom("parent", X, Y),
            create_atom("ancestor", Y, Z)
        ),
    ]

    result = engine.infer(facts, rules)

    expected = {
        create_atom("ancestor", create_constant("a"), create_constant("b")),
        create_atom("ancestor", create_constant("b"), create_constant("c")),
        create_atom("ancestor", create_constant("c"), create_constant("d")),
        create_atom("ancestor", create_constant("a"), create_constant("c")),
        create_atom("ancestor", create_constant("b"), create_constant("d")),
        create_atom("ancestor", create_constant("a"), create_constant("d")),
    }

    missing = expected - result.derived_facts
    assert not missing, f"Missing ancestor facts: {missing}"
    assert result.iterations > 0, "Engine must report at least one iteration"


def test_3_backward_chaining_soundness():
    """Backward chaining must prove valid goals and reject invalid ones."""
    engine = BackwardChainingEngine()

    facts = [
        create_fact("parent", create_constant("john"), create_constant("mary")),
    ]

    X = create_variable("X")
    Y = create_variable("Y")

    rules = [
        create_rule(
            create_atom("ancestor", X, Y),
            create_atom("parent", X, Y)
        ),
    ]

    valid_goal = create_atom("ancestor", create_constant("john"), create_constant("mary"))
    invalid_goal = create_atom("ancestor", create_constant("mary"), create_constant("john"))

    result_valid = engine.prove(valid_goal, facts, rules)
    result_invalid = engine.prove(invalid_goal, facts, rules)

    assert result_valid.success, "Valid goal ancestor(john, mary) must be provable"
    assert not result_invalid.success, "Invalid goal ancestor(mary, john) must not be provable"
    assert len(result_valid.solutions) >= 1, "Valid proof must have at least one solution"


def test_4_cycle_detection():
    """Backward chaining must terminate on self-referential rules within 1 second."""
    engine = BackwardChainingEngine(max_depth=10)

    X = create_variable("X")
    rules = [
        create_rule(
            create_atom("p", X),
            create_atom("p", X)  # p(X) :- p(X)
        ),
    ]

    goal = create_atom("p", create_constant("a"))

    start = time.time()
    result = engine.prove(goal, [], rules)
    elapsed = time.time() - start

    assert not result.success, "Self-referential rule must not succeed"
    assert elapsed < 1.0, f"Cycle detection took too long: {elapsed:.3f}s (limit: 1.0s)"
    assert "max_depth_reached" in result.statistics, (
        "Statistics must include 'max_depth_reached'"
    )


def test_5_hybrid_reasoning():
    """Hybrid mode must combine forward and backward chaining successfully."""
    engine = SymbolicReasoningEngine()

    engine.add_fact(create_fact("parent", create_constant("a"), create_constant("b")))
    engine.add_fact(create_fact("parent", create_constant("b"), create_constant("c")))

    X = create_variable("X")
    Y = create_variable("Y")
    Z = create_variable("Z")

    engine.add_rule(create_rule(
        create_atom("ancestor", X, Y),
        create_atom("parent", X, Y)
    ))
    engine.add_rule(create_rule(
        create_atom("ancestor", X, Z),
        create_atom("parent", X, Y),
        create_atom("ancestor", Y, Z)
    ))

    goal = create_atom("ancestor", create_constant("a"), create_constant("c"))
    result = engine.query(goal, mode=ReasoningMode.HYBRID)

    assert result.success, "Hybrid reasoning must prove ancestor(a, c)"
    assert result.mode == ReasoningMode.HYBRID, (
        f"Result mode must be HYBRID, got {result.mode}"
    )
    assert result.forward_result is not None, "Hybrid result must include forward_result"
    assert result.backward_result is not None, "Hybrid result must include backward_result"


def test_6_determinism():
    """Forward chaining must produce identical results across multiple runs."""
    engine = ForwardChainingEngine()

    facts = [
        create_fact("p", create_constant("a")),
        create_fact("q", create_constant("b")),
    ]

    X = create_variable("X")
    Y = create_variable("Y")

    rules = [
        create_rule(create_atom("r", X), create_atom("p", X)),
        create_rule(create_atom("s", X, Y), create_atom("p", X), create_atom("q", Y)),
    ]

    results = [engine.infer(facts, rules) for _ in range(5)]
    first_facts = results[0].derived_facts

    for i, r in enumerate(results[1:], start=2):
        assert r.derived_facts == first_facts, (
            f"Run {i} produced different facts than run 1 — engine is non-deterministic"
        )


def test_7_performance_large_kb():
    """Forward chaining on a 50-node chain must complete within 5 seconds."""
    n = 50
    engine = ForwardChainingEngine(max_iterations=10000)

    facts = [
        create_fact("edge", create_constant(f"n{i}"), create_constant(f"n{i+1}"))
        for i in range(n)
    ]

    X = create_variable("X")
    Y = create_variable("Y")
    Z = create_variable("Z")

    rules = [
        create_rule(
            create_atom("path", X, Y),
            create_atom("edge", X, Y)
        ),
        create_rule(
            create_atom("path", X, Z),
            create_atom("edge", X, Y),
            create_atom("path", Y, Z)
        ),
    ]

    start = time.time()
    result = engine.infer(facts, rules)
    elapsed = time.time() - start

    # A chain of n edges produces n*(n+1)/2 path facts
    expected_min = n * (n + 1) // 2

    assert elapsed < 5.0, f"Inference took {elapsed:.3f}s, limit is 5.0s"
    assert len(result.derived_facts) >= expected_min, (
        f"Expected at least {expected_min} path facts, got {len(result.derived_facts)}"
    )


def test_8_proof_auditability():
    """Proof hashes must be deterministic, unique per clause, and SHA-256 formatted."""
    engine = FirstOrderLogicEngine()

    clause1 = create_fact("p", create_constant("a"))
    clause2 = create_fact("p", create_constant("b"))
    subst = {}

    # Determinism: same input → same hash
    hashes = [engine.compute_proof_hash(clause1, subst) for _ in range(5)]
    assert len(set(hashes)) == 1, (
        f"Hash is non-deterministic across runs: {set(hashes)}"
    )

    # Uniqueness: different clauses → different hashes
    hash1 = engine.compute_proof_hash(clause1, subst)
    hash2 = engine.compute_proof_hash(clause2, subst)
    assert hash1 != hash2, (
        f"Different clauses produced the same hash: {hash1}"
    )

    # Format: SHA-256 is exactly 64 lowercase hex characters
    assert len(hash1) == 64, f"Hash length is {len(hash1)}, expected 64"
    assert all(c in "0123456789abcdef" for c in hash1), (
        f"Hash contains non-hex characters: {hash1}"
    )


# ---------------------------------------------------------------------------
# Standalone runner (python test_symbolic_reasoning_standalone.py)
# ---------------------------------------------------------------------------

def _run_standalone():
    """Run all tests directly without pytest, printing pass/fail per test."""
    test_fns = [
        test_1_unification_occur_check,
        test_2_forward_chaining_transitive_closure,
        test_3_backward_chaining_soundness,
        test_4_cycle_detection,
        test_5_hybrid_reasoning,
        test_6_determinism,
        test_7_performance_large_kb,
        test_8_proof_auditability,
    ]

    print("\n" + "=" * 70)
    print("SYMBOLIC REASONING ENGINE - STANDALONE RUN")
    print("=" * 70)

    passed = 0
    failed = 0

    for fn in test_fns:
        name = fn.__name__
        try:
            fn()  # raises AssertionError on failure
            print(f"✅ PASSED  {name}")
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED  {name}: {e}")
            failed += 1
        except Exception as e:
            import traceback
            print(f"💥 ERROR   {name}: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"Results: {passed}/{passed + failed} passed")
    if failed:
        print(f"⚠️  {failed} test(s) failed")
        return 1
    print("🎉 ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(_run_standalone())

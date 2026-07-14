#!/usr/bin/env python3
"""
HARD Symbolic Reasoning Tests
==============================

Challenging tests for edge cases, performance, and correctness.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mahoun.reasoning import first_order_logic as fol
from mahoun.reasoning import forward_chaining as fc
from mahoun.reasoning import backward_chaining as bc
from mahoun.reasoning import symbolic_reasoner as sr

print("="*70)
print("HARD SYMBOLIC REASONING TESTS")
print("="*70)

# TEST 1: Nested Function Unification
print("\n" + "="*70)
print("TEST 1: Nested Function Unification (HARD)")
print("="*70)

engine = fol.FirstOrderLogicEngine()
X = fol.create_variable("X")
Y = fol.create_variable("Y")
a = fol.create_constant("a")
b = fol.create_constant("b")

# f(g(X), h(a)) = f(g(b), h(Y))
# Should produce {X -> b, Y -> a}
term1 = fol.create_function("f",
    fol.create_function("g", X),
    fol.create_function("h", a)
)
term2 = fol.create_function("f",
    fol.create_function("g", b),
    fol.create_function("h", Y)
)

subst = engine.unify(term1, term2)
print(f"✓ Unified nested functions")
print(f"  X -> {subst[X]}")
print(f"  Y -> {subst[Y]}")

assert subst[X] == b, f"Expected X->b, got X->{subst[X]}"
assert subst[Y] == a, f"Expected Y->a, got Y->{subst[Y]}"
print("✅ TEST 1 PASSED\n")

# TEST 2: Transitive Closure Completeness
print("="*70)
print("TEST 2: Transitive Closure Completeness (HARD)")
print("="*70)

fc_engine = fc.ForwardChainingEngine()

# Chain: a->b->c->d
facts = [
    fol.create_fact("parent", fol.create_constant("a"), fol.create_constant("b")),
    fol.create_fact("parent", fol.create_constant("b"), fol.create_constant("c")),
    fol.create_fact("parent", fol.create_constant("c"), fol.create_constant("d")),
]

X = fol.create_variable("X")
Y = fol.create_variable("Y")
Z = fol.create_variable("Z")

rules = [
    fol.create_rule(
        fol.create_atom("ancestor", X, Y),
        fol.create_atom("parent", X, Y)
    ),
    fol.create_rule(
        fol.create_atom("ancestor", X, Z),
        fol.create_atom("parent", X, Y),
        fol.create_atom("ancestor", Y, Z)
    ),
]

result = fc_engine.infer(facts, rules)

# Must derive ALL 6 ancestor facts
expected = [
    ("a", "b"), ("b", "c"), ("c", "d"),  # Direct
    ("a", "c"), ("b", "d"),              # 2-hop
    ("a", "d"),                          # 3-hop
]

missing = []
for (x, y) in expected:
    atom = fol.create_atom("ancestor", fol.create_constant(x), fol.create_constant(y))
    if atom not in result.derived_facts:
        missing.append(f"ancestor({x}, {y})")

if missing:
    print(f"❌ FAILED: Missing facts: {missing}")
    sys.exit(1)

print(f"✓ Derived all {len(expected)} expected ancestor facts")
print(f"  Total facts: {len(result.derived_facts)}")
print(f"  Iterations: {result.iterations}")
print("✅ TEST 2 PASSED\n")

# TEST 3: Cycle Detection
print("="*70)
print("TEST 3: Cycle Detection (HARD)")
print("="*70)

bc_engine = bc.BackwardChainingEngine(max_depth=10)

# Self-referential rule: p(X) :- p(X)
facts = []
X = fol.create_variable("X")
rules = [
    fol.create_rule(
        fol.create_atom("p", X),
        fol.create_atom("p", X)
    ),
]

goal = fol.create_atom("p", fol.create_constant("a"))

start = time.time()
result = bc_engine.prove(goal, facts, rules)
elapsed = time.time() - start

if result.success:
    print("❌ FAILED: Should not have proved goal (infinite loop)")
    sys.exit(1)

if elapsed > 1.0:
    print(f"❌ FAILED: Took too long ({elapsed:.3f}s)")
    sys.exit(1)

print(f"✓ Cycle detected and terminated in {elapsed:.3f}s")
print(f"  Max depth reached: {result.statistics['max_depth_reached']}")
print("✅ TEST 3 PASSED\n")

# TEST 4: Determinism
print("="*70)
print("TEST 4: Determinism (HARD)")
print("="*70)

fc_engine = fc.ForwardChainingEngine()

facts = [
    fol.create_fact("p", fol.create_constant("a")),
    fol.create_fact("q", fol.create_constant("b")),
]

X = fol.create_variable("X")
Y = fol.create_variable("Y")

rules = [
    fol.create_rule(fol.create_atom("r", X), fol.create_atom("p", X)),
    fol.create_rule(fol.create_atom("s", X, Y), fol.create_atom("p", X), fol.create_atom("q", Y)),
]

# Run 10 times
results = []
for i in range(10):
    result = fc_engine.infer(facts, rules)
    results.append(result.derived_facts)

# All must be identical
first = results[0]
for i, result in enumerate(results[1:], 1):
    if result != first:
        print(f"❌ FAILED: Run {i+1} produced different results")
        sys.exit(1)

print(f"✓ All 10 runs produced identical results")
print(f"  Derived facts: {len(first)}")
print("✅ TEST 4 PASSED\n")

# TEST 5: Find All Solutions
print("="*70)
print("TEST 5: Find All Solutions (HARD)")
print("="*70)

bc_engine = bc.BackwardChainingEngine(find_all=True)

facts = [
    fol.create_fact("parent", fol.create_constant("john"), fol.create_constant("mary")),
    fol.create_fact("parent", fol.create_constant("john"), fol.create_constant("bob")),
]

X = fol.create_variable("X")
Y = fol.create_variable("Y")

# No rules - just match facts directly
rules = []

# Query: parent(john, X) - should find mary and bob
goal = fol.create_atom("parent", fol.create_constant("john"), X)
result = bc_engine.prove(goal, facts, rules)

if not result.success:
    print("❌ FAILED: Goal not proved")
    sys.exit(1)

if len(result.solutions) != 2:
    print(f"❌ FAILED: Expected 2 solutions, got {len(result.solutions)}")
    print(f"  Solutions: {result.solutions}")
    sys.exit(1)

# Extract bindings
bindings = []
for sol in result.solutions:
    if X in sol:
        bindings.append(sol[X].name)

if "mary" not in bindings or "bob" not in bindings:
    print(f"❌ FAILED: Expected mary and bob, got {bindings}")
    sys.exit(1)

print(f"✓ Found all {len(result.solutions)} solutions")
print(f"  Bindings: {bindings}")
print("✅ TEST 5 PASSED\n")

# TEST 6: Performance - Large KB
print("="*70)
print("TEST 6: Performance - Large Knowledge Base (HARD)")
print("="*70)

fc_engine = fc.ForwardChainingEngine(max_iterations=10000)

# Chain of 50 nodes (back to original)
n = 50
facts = [
    fol.create_fact("edge", fol.create_constant(f"n{i}"), fol.create_constant(f"n{i+1}"))
    for i in range(n)
]

X = fol.create_variable("X")
Y = fol.create_variable("Y")
Z = fol.create_variable("Z")

rules = [
    fol.create_rule(
        fol.create_atom("path", X, Y),
        fol.create_atom("edge", X, Y)
    ),
    fol.create_rule(
        fol.create_atom("path", X, Z),
        fol.create_atom("edge", X, Y),
        fol.create_atom("path", Y, Z)
    ),
]

start = time.time()
result = fc_engine.infer(facts, rules)
elapsed = time.time() - start

expected_paths = n * (n + 1) // 2  # n + (n-1) + ... + 1

if len(result.derived_facts) < expected_paths:
    print(f"❌ FAILED: Expected at least {expected_paths} paths, got {len(result.derived_facts)}")
    sys.exit(1)

if elapsed > 5.0:
    print(f"❌ FAILED: Too slow ({elapsed:.3f}s) - optimization needed")
    sys.exit(1)

print(f"✓ Derived {len(result.derived_facts)} facts in {elapsed:.3f}s")
print(f"  Iterations: {result.iterations}")
print(f"  Performance: {len(result.derived_facts)/elapsed:.0f} facts/sec")
print("✅ TEST 6 PASSED\n")

# TEST 7: Proof Auditability
print("="*70)
print("TEST 7: Proof Auditability (HARD)")
print("="*70)

engine = fol.FirstOrderLogicEngine()

clause1 = fol.create_fact("p", fol.create_constant("a"))
clause2 = fol.create_fact("p", fol.create_constant("b"))
subst = {}

# Same clause -> same hash
hashes1 = [engine.compute_proof_hash(clause1, subst) for _ in range(5)]
if len(set(hashes1)) != 1:
    print("❌ FAILED: Non-deterministic hashes")
    sys.exit(1)

# Different clauses -> different hashes
hash1 = engine.compute_proof_hash(clause1, subst)
hash2 = engine.compute_proof_hash(clause2, subst)
if hash1 == hash2:
    print("❌ FAILED: Same hash for different clauses")
    sys.exit(1)

# SHA-256 format (64 hex chars)
if len(hash1) != 64 or not all(c in "0123456789abcdef" for c in hash1):
    print(f"❌ FAILED: Invalid hash format: {hash1}")
    sys.exit(1)

print(f"✓ Proof hashes are deterministic and unique")
print(f"  Sample hash: {hash1[:16]}...")
print("✅ TEST 7 PASSED\n")

# TEST 8: Legal Reasoning Scenario
print("="*70)
print("TEST 8: Legal Reasoning Scenario (VERY HARD)")
print("="*70)

sym_engine = sr.SymbolicReasoningEngine()

# Facts: defendant breached duty, owed duty, caused harm
sym_engine.add_fact(fol.create_fact("breached_duty", fol.create_constant("defendant")))
sym_engine.add_fact(fol.create_fact("owed_duty", fol.create_constant("defendant")))
sym_engine.add_fact(fol.create_fact("caused_harm", fol.create_constant("defendant")))

X = fol.create_variable("X")

# Rules: negligent if breached and owed duty
sym_engine.add_rule(fol.create_rule(
    fol.create_atom("negligent", X),
    fol.create_atom("breached_duty", X),
    fol.create_atom("owed_duty", X),
))

# Rules: liable if negligent and caused harm
sym_engine.add_rule(fol.create_rule(
    fol.create_atom("liable", X),
    fol.create_atom("negligent", X),
    fol.create_atom("caused_harm", X),
))

# Query: Is defendant liable?
goal = fol.create_atom("liable", fol.create_constant("defendant"))
result = sym_engine.query(goal, mode=sr.ReasoningMode.HYBRID)

if not result.success:
    print("❌ FAILED: Could not prove liability")
    sys.exit(1)

# Get explanation
explanation = sym_engine.explain_derivation(goal)
if explanation is None:
    print("❌ FAILED: No explanation generated")
    sys.exit(1)

print(f"✓ Successfully proved liability")
print(f"✓ Explanation generated:")
for line in explanation.split('\n')[:5]:  # First 5 lines
    print(f"    {line}")
print("✅ TEST 8 PASSED\n")

# SUMMARY
print("="*70)
print("ALL HARD TESTS PASSED! 🎉🎉🎉")
print("="*70)
print("\nSymbolic Reasoning Engine passed all hard tests:")
print("  ✓ Nested function unification")
print("  ✓ Transitive closure completeness")
print("  ✓ Cycle detection")
print("  ✓ Determinism (10 runs)")
print("  ✓ Find all solutions")
print("  ✓ Performance (50-node graph)")
print("  ✓ Proof auditability (SHA-256)")
print("  ✓ Legal reasoning scenario")
print("\n" + "="*70)

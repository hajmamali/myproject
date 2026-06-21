#!/usr/bin/env python3
"""
Direct Symbolic Reasoning Tests - No Pytest
============================================
"""
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

# Import directly without going through __init__.py
from mahoun.reasoning import first_order_logic as fol
from mahoun.reasoning import forward_chaining as fc
from mahoun.reasoning import backward_chaining as bc
from mahoun.reasoning import symbolic_reasoner as sr

print("✓ Imports successful\n")

# Test 1: Basic FOL
print("="*60)
print("TEST 1: Basic First-Order Logic")
print("="*60)

engine = fol.FirstOrderLogicEngine()
x = fol.create_variable("X")
a = fol.create_constant("a")

subst = engine.unify(x, a)
print(f"✓ Unify X with a: {subst}")
assert x in subst and subst[x] == a

result = engine.apply_substitution(x, subst)
print(f"✓ Apply substitution: {result}")
assert result == a

print("✅ TEST 1 PASSED\n")

# Test 2: Occur Check
print("="*60)
print("TEST 2: Occur Check")
print("="*60)

x = fol.create_variable("X")
f_x = fol.create_function("f", x)

try:
    engine.unify(x, f_x)
    print("❌ FAILED: Should have raised UnificationError")
    sys.exit(1)
except fol.UnificationError as e:
    print(f"✓ Occur check prevented: {e}")
    print("✅ TEST 2 PASSED\n")

# Test 3: Forward Chaining
print("="*60)
print("TEST 3: Forward Chaining - Transitive Closure")
print("="*60)

fc_engine = fc.ForwardChainingEngine()

facts = [
    fol.create_fact("parent", fol.create_constant("a"), fol.create_constant("b")),
    fol.create_fact("parent", fol.create_constant("b"), fol.create_constant("c")),
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
print(f"✓ Derived {len(result.derived_facts)} facts in {result.iterations} iterations")

expected = fol.create_atom("ancestor", fol.create_constant("a"), fol.create_constant("c"))
if expected in result.derived_facts:
    print(f"✓ Found transitive fact: {expected}")
    print("✅ TEST 3 PASSED\n")
else:
    print(f"❌ FAILED: Missing {expected}")
    sys.exit(1)

# Test 4: Backward Chaining
print("="*60)
print("TEST 4: Backward Chaining - Goal Proving")
print("="*60)

bc_engine = bc.BackwardChainingEngine()

facts = [
    fol.create_fact("parent", fol.create_constant("john"), fol.create_constant("mary")),
]

rules = [
    fol.create_rule(
        fol.create_atom("ancestor", X, Y),
        fol.create_atom("parent", X, Y)
    ),
]

goal = fol.create_atom("ancestor", fol.create_constant("john"), fol.create_constant("mary"))
result = bc_engine.prove(goal, facts, rules)

if result.success:
    print(f"✓ Goal proved with {len(result.solutions)} solution(s)")
    print("✅ TEST 4 PASSED\n")
else:
    print("❌ FAILED: Goal not proved")
    sys.exit(1)

# Test 5: Symbolic Reasoner
print("="*60)
print("TEST 5: Symbolic Reasoner - Hybrid Mode")
print("="*60)

sym_engine = sr.SymbolicReasoningEngine()

sym_engine.add_fact(fol.create_fact("parent", fol.create_constant("a"), fol.create_constant("b")))
sym_engine.add_fact(fol.create_fact("parent", fol.create_constant("b"), fol.create_constant("c")))

sym_engine.add_rule(fol.create_rule(
    fol.create_atom("ancestor", X, Y),
    fol.create_atom("parent", X, Y)
))

sym_engine.add_rule(fol.create_rule(
    fol.create_atom("ancestor", X, Z),
    fol.create_atom("parent", X, Y),
    fol.create_atom("ancestor", Y, Z)
))

goal = fol.create_atom("ancestor", fol.create_constant("a"), fol.create_constant("c"))
result = sym_engine.query(goal, mode=sr.ReasoningMode.HYBRID)

if result.success:
    print(f"✓ Hybrid reasoning succeeded")
    print(f"✓ Mode: {result.mode}")
    print(f"✓ Derived facts: {len(result.derived_facts)}")
    print("✅ TEST 5 PASSED\n")
else:
    print("❌ FAILED: Hybrid reasoning failed")
    sys.exit(1)

# Summary
print("="*60)
print("ALL TESTS PASSED! 🎉")
print("="*60)
print("\nSymbolic Reasoning Engine is working correctly:")
print("  ✓ First-Order Logic (unification, substitution)")
print("  ✓ Occur Check (prevents infinite structures)")
print("  ✓ Forward Chaining (data-driven reasoning)")
print("  ✓ Backward Chaining (goal-driven reasoning)")
print("  ✓ Hybrid Reasoning (combined approach)")

"""
Basic First-Order Logic Tests
==============================

Simple tests for FOL engine - unification and substitution.
"""
import sys
from pathlib import Path

# Direct import to avoid __init__.py circular dependencies
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

# Direct module imports
from mahoun.reasoning import first_order_logic

FirstOrderLogicEngine = first_order_logic.FirstOrderLogicEngine
Term = first_order_logic.Term
TermType = first_order_logic.TermType
UnificationError = first_order_logic.UnificationError
create_atom = first_order_logic.create_atom
create_constant = first_order_logic.create_constant
create_function = first_order_logic.create_function
create_variable = first_order_logic.create_variable


def test_create_constant():
    """Test creating a constant term"""
    c = create_constant("john")
    assert c.name == "john"
    assert c.term_type == TermType.CONSTANT
    assert c.is_constant()
    assert not c.is_variable()
    assert c.is_ground()


def test_create_variable():
    """Test creating a variable term"""
    v = create_variable("X")
    assert v.name == "X"
    assert v.term_type == TermType.VARIABLE
    assert v.is_variable()
    assert not v.is_constant()
    assert not v.is_ground()


def test_create_function():
    """Test creating a function term"""
    x = create_variable("X")
    f = create_function("f", x)
    assert f.name == "f"
    assert f.term_type == TermType.FUNCTION
    assert len(f.args) == 1
    assert not f.is_ground()


def test_unify_constant_with_constant():
    """Test unifying two identical constants"""
    engine = FirstOrderLogicEngine()
    a = create_constant("a")
    b = create_constant("a")
    
    subst = engine.unify(a, b)
    assert subst == {}


def test_unify_variable_with_constant():
    """Test unifying variable with constant"""
    engine = FirstOrderLogicEngine()
    x = create_variable("X")
    a = create_constant("a")
    
    subst = engine.unify(x, a)
    assert x in subst
    assert subst[x] == a


def test_unify_different_constants_fails():
    """Test that unifying different constants fails"""
    engine = FirstOrderLogicEngine()
    a = create_constant("a")
    b = create_constant("b")
    
    with pytest.raises(UnificationError):
        engine.unify(a, b)


def test_apply_substitution_to_variable():
    """Test applying substitution to variable"""
    engine = FirstOrderLogicEngine()
    x = create_variable("X")
    a = create_constant("a")
    
    subst = {x: a}
    result = engine.apply_substitution(x, subst)
    assert result == a


def test_apply_substitution_to_constant():
    """Test applying substitution to constant (no change)"""
    engine = FirstOrderLogicEngine()
    a = create_constant("a")
    x = create_variable("X")
    b = create_constant("b")
    
    subst = {x: b}
    result = engine.apply_substitution(a, subst)
    assert result == a


def test_atom_creation():
    """Test creating atoms"""
    a = create_constant("a")
    b = create_constant("b")
    atom = create_atom("parent", a, b)
    
    assert atom.predicate == "parent"
    assert len(atom.terms) == 2
    assert atom.is_ground()


def test_atom_with_variables():
    """Test atom with variables"""
    x = create_variable("X")
    y = create_variable("Y")
    atom = create_atom("parent", x, y)
    
    assert not atom.is_ground()
    vars = atom.get_variables()
    assert x in vars
    assert y in vars

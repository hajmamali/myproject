"""
First-Order Logic Engine
========================

Pure symbolic reasoning engine for MAHOUN platform.
Implements unification, substitution, and FOL inference without LLM dependency.

This module provides deterministic, auditable logical reasoning for high-stakes decisions.

Design Principles:
- Zero hallucination: All inferences are graph-grounded
- Deterministic: Same input always produces same output
- Auditable: Complete proof traces
- Thread-safe: Immutable data structures
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Optional, Set, Tuple

log = logging.getLogger(__name__)


class TermType(Enum):
    """Types of FOL terms"""
    CONSTANT = "constant"
    VARIABLE = "variable"
    FUNCTION = "function"
    PREDICATE = "predicate"


@dataclass(frozen=True)
class Term:
    """
    Immutable FOL term (constant, variable, or function application)
    
    Examples:
        - Constant: Term("john", TermType.CONSTANT)
        - Variable: Term("X", TermType.VARIABLE)
        - Function: Term("father", TermType.FUNCTION, [Term("john")])
    """
    name: str
    term_type: TermType
    args: Tuple[Term, ...] = field(default_factory=tuple)
    
    def __post_init__(self) -> None:
        """Validate term structure"""
        if self.term_type in (TermType.CONSTANT, TermType.VARIABLE):
            if self.args:
                raise ValueError(f"{self.term_type.value} cannot have arguments")
        elif self.term_type == TermType.FUNCTION:
            if not self.args:
                raise ValueError("Function must have at least one argument")
    
    def is_variable(self) -> bool:
        """Check if term is a variable"""
        return self.term_type == TermType.VARIABLE
    
    def is_constant(self) -> bool:
        """Check if term is a constant"""
        return self.term_type == TermType.CONSTANT
    
    def is_ground(self) -> bool:
        """Check if term contains no variables"""
        if self.is_variable():
            return False
        if self.is_constant():
            return True
        return all(arg.is_ground() for arg in self.args)
    
    def get_variables(self) -> FrozenSet[Term]:
        """Extract all variables from term"""
        if self.is_variable():
            return frozenset([self])
        if self.is_constant():
            return frozenset()
        vars_set: Set[Term] = set()
        for arg in self.args:
            vars_set.update(arg.get_variables())
        return frozenset(vars_set)
    
    def __str__(self) -> str:
        if self.term_type in (TermType.CONSTANT, TermType.VARIABLE):
            return self.name
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({args_str})"
    
    def __hash__(self) -> int:
        return hash((self.name, self.term_type, self.args))


@dataclass(frozen=True)
class Atom:
    """
    Atomic formula (predicate applied to terms)
    
    Example: Atom("parent", [Term("john"), Term("mary")])
    Represents: parent(john, mary)
    """
    predicate: str
    terms: Tuple[Term, ...] = field(default_factory=tuple)

    @property
    def name(self) -> str:
        """Alias for predicate to maintain compatibility with Predicate interface."""
        return self.predicate
    
    def is_ground(self) -> bool:
        """Check if atom contains no variables"""
        return all(term.is_ground() for term in self.terms)
    
    def get_variables(self) -> FrozenSet[Term]:
        """Extract all variables from atom"""
        vars_set: Set[Term] = set()
        for term in self.terms:
            vars_set.update(term.get_variables())
        return frozenset(vars_set)
    
    def __str__(self) -> str:
        if not self.terms:
            return self.predicate
        terms_str = ", ".join(str(t) for t in self.terms)
        return f"{self.predicate}({terms_str})"
    
    def __hash__(self) -> int:
        return hash((self.predicate, self.terms))


@dataclass(frozen=True)
class Clause:
    """
    Horn clause: head :- body1, body2, ..., bodyN
    
    If body is empty, this is a fact.
    If head is None, this is a goal/query.
    
    Examples:
        - Fact: Clause(Atom("parent", [john, mary]), [])
        - Rule: Clause(Atom("ancestor", [X, Y]), [Atom("parent", [X, Y])])
        - Goal: Clause(None, [Atom("ancestor", [john, Z])])
    """
    head: Optional[Atom]
    body: Tuple[Atom, ...] = field(default_factory=tuple)
    
    def is_fact(self) -> bool:
        """Check if clause is a fact (no body)"""
        return self.head is not None and len(self.body) == 0
    
    def is_rule(self) -> bool:
        """Check if clause is a rule (has body)"""
        return self.head is not None and len(self.body) > 0
    
    def is_goal(self) -> bool:
        """Check if clause is a goal (no head)"""
        return self.head is None
    
    def get_variables(self) -> FrozenSet[Term]:
        """Extract all variables from clause"""
        vars_set: Set[Term] = set()
        if self.head:
            vars_set.update(self.head.get_variables())
        for atom in self.body:
            vars_set.update(atom.get_variables())
        return frozenset(vars_set)
    
    def __str__(self) -> str:
        if self.is_fact():
            return f"{self.head}."
        if self.is_goal():
            body_str = ", ".join(str(atom) for atom in self.body)
            return f"?- {body_str}."
        body_str = ", ".join(str(atom) for atom in self.body)
        return f"{self.head} :- {body_str}."
    
    def __hash__(self) -> int:
        return hash((self.head, self.body))


# Type alias for substitution (immutable mapping)
Substitution = Dict[Term, Term]


class UnificationError(Exception):
    """Raised when unification fails"""
    pass


class FirstOrderLogicEngine:
    """
    First-Order Logic reasoning engine with unification and substitution.
    
    This engine provides:
    - Robinson's unification algorithm
    - Substitution application
    - Variable renaming for clause variants
    - Deterministic, auditable inference
    
    Thread-safe: All operations use immutable data structures.
    """
    
    def __init__(self) -> None:
        """Initialize FOL engine"""
        self._rename_counter = 0
        log.info("Initialized FirstOrderLogicEngine")
    
    def unify(self, term1: Term, term2: Term, subst: Optional[Substitution] = None) -> Substitution:
        """
        Robinson's unification algorithm.
        
        Returns most general unifier (MGU) if terms can be unified.
        Raises UnificationError if unification fails.
        
        Args:
            term1: First term
            term2: Second term
            subst: Existing substitution (default: empty)
        
        Returns:
            Most general unifier
        
        Raises:
            UnificationError: If terms cannot be unified
        
        Examples:
            >>> engine = FirstOrderLogicEngine()
            >>> X = Term("X", TermType.VARIABLE)
            >>> john = Term("john", TermType.CONSTANT)
            >>> subst = engine.unify(X, john)
            >>> subst[X] == john
            True
        """
        if subst is None:
            subst = {}
        
        # Apply existing substitution
        term1 = self.apply_substitution(term1, subst)
        term2 = self.apply_substitution(term2, subst)
        
        # Same term
        if term1 == term2:
            return subst
        
        # Variable unification
        if term1.is_variable():
            return self._unify_variable(term1, term2, subst)
        if term2.is_variable():
            return self._unify_variable(term2, term1, subst)
        
        # Function unification
        if term1.term_type == TermType.FUNCTION and term2.term_type == TermType.FUNCTION:
            if term1.name != term2.name or len(term1.args) != len(term2.args):
                raise UnificationError(f"Cannot unify {term1} with {term2}: different functors")
            
            # Unify arguments left-to-right
            current_subst = dict(subst)
            for arg1, arg2 in zip(term1.args, term2.args):
                current_subst = self.unify(arg1, arg2, current_subst)
            return current_subst
        
        # Constants must match exactly
        raise UnificationError(f"Cannot unify {term1} with {term2}")
    
    def _unify_variable(self, var: Term, term: Term, subst: Substitution) -> Substitution:
        """
        Unify a variable with a term.
        
        Performs occur check to prevent infinite structures.
        """
        if not var.is_variable():
            raise ValueError(f"{var} is not a variable")
        
        # Occur check: var must not appear in term
        if var in term.get_variables():
            raise UnificationError(f"Occur check failed: {var} appears in {term}")
        
        # Create new substitution
        new_subst = dict(subst)
        new_subst[var] = term
        return new_subst
    
    def apply_substitution(self, term: Term, subst: Substitution) -> Term:
        """
        Apply substitution to a term.
        
        Args:
            term: Term to substitute into
            subst: Substitution mapping
        
        Returns:
            Term with substitution applied
        
        Examples:
            >>> engine = FirstOrderLogicEngine()
            >>> X = Term("X", TermType.VARIABLE)
            >>> john = Term("john", TermType.CONSTANT)
            >>> subst = {X: john}
            >>> result = engine.apply_substitution(X, subst)
            >>> result == john
            True
        """
        if term.is_variable():
            if term in subst:
                # Recursively apply substitution
                return self.apply_substitution(subst[term], subst)
            return term
        
        if term.is_constant():
            return term
        
        # Apply to function arguments
        new_args = tuple(self.apply_substitution(arg, subst) for arg in term.args)
        return Term(term.name, term.term_type, new_args)
    
    def apply_substitution_atom(self, atom: Atom, subst: Substitution) -> Atom:
        """Apply substitution to an atom"""
        new_terms = tuple(self.apply_substitution(term, subst) for term in atom.terms)
        return Atom(atom.predicate, new_terms)
    
    def apply_substitution_clause(self, clause: Clause, subst: Substitution) -> Clause:
        """Apply substitution to a clause"""
        new_head = self.apply_substitution_atom(clause.head, subst) if clause.head else None
        new_body = tuple(self.apply_substitution_atom(atom, subst) for atom in clause.body)
        return Clause(new_head, new_body)
    
    def rename_variables(self, clause: Clause, suffix: Optional[str] = None) -> Clause:
        """
        Rename all variables in a clause to avoid conflicts.
        
        Args:
            clause: Clause to rename
            suffix: Optional suffix for variable names
        
        Returns:
            Clause with renamed variables
        """
        if suffix is None:
            self._rename_counter += 1
            suffix = f"_{self._rename_counter}"
        
        # Build substitution for all variables
        variables = clause.get_variables()
        subst: Substitution = {}
        for var in variables:
            new_var = Term(f"{var.name}{suffix}", TermType.VARIABLE)
            subst[var] = new_var
        
        return self.apply_substitution_clause(clause, subst)
    
    def compose_substitutions(self, subst1: Substitution, subst2: Substitution) -> Substitution:
        """
        Compose two substitutions: subst1 ∘ subst2
        
        Result applies subst2 first, then subst1.
        """
        result: Substitution = {}
        
        # Apply subst1 to range of subst2
        for var, term in subst2.items():
            result[var] = self.apply_substitution(term, subst1)
        
        # Add bindings from subst1 not in subst2
        for var, term in subst1.items():
            if var not in result:
                result[var] = term
        
        return result
    
    def compute_proof_hash(self, clause: Clause, subst: Substitution) -> str:
        """
        Compute cryptographic hash of proof step.
        
        Used for immutable audit trail.
        """
        clause_str = str(clause)
        subst_str = str(sorted(subst.items(), key=lambda x: str(x[0])))
        combined = f"{clause_str}|{subst_str}"
        return hashlib.sha256(combined.encode()).hexdigest()


def create_constant(name: str) -> Term:
    """Helper: Create a constant term"""
    return Term(name, TermType.CONSTANT)


def create_variable(name: str) -> Term:
    """Helper: Create a variable term"""
    return Term(name, TermType.VARIABLE)


def create_function(name: str, *args: Term) -> Term:
    """Helper: Create a function term"""
    return Term(name, TermType.FUNCTION, tuple(args))


def create_atom(predicate: str, *terms: Term) -> Atom:
    """Helper: Create an atom"""
    return Atom(predicate, tuple(terms))


def create_fact(predicate: str, *terms: Term) -> Clause:
    """Helper: Create a fact"""
    return Clause(create_atom(predicate, *terms), tuple())


def create_rule(head: Atom, *body: Atom) -> Clause:
    """Helper: Create a rule"""
    return Clause(head, tuple(body))


def create_goal(*atoms: Atom) -> Clause:
    """Helper: Create a goal"""
    return Clause(None, tuple(atoms))

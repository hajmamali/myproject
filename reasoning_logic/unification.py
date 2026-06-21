"""
Unification Engine
==================

Robinson's unification algorithm with occurs-check for FOL.

Features:
- Most General Unifier (MGU) computation
- Occurs-check to prevent infinite structures
- Efficient substitution composition
- Type-safe variable dereferencing
"""

from typing import Dict, Optional, Set
from reasoning_logic.core import Term, Atom, TermType


class UnificationEngine:
    """
    Robinson's unification algorithm with occurs-check
    
    Ensures:
    - Most general unifier (MGU) computation
    - Occurs-check prevents infinite structures
    - Efficient substitution composition
    """
    
    @staticmethod
    def unify(term1: Term, term2: Term, bindings: Optional[Dict[str, Term]] = None) -> Optional[Dict[str, Term]]:
        """
        Unify two terms and return bindings (MGU)
        
        Args:
            term1: First term to unify
            term2: Second term to unify
            bindings: Existing variable bindings
        
        Returns:
            Dict mapping variable names to terms, or None if unification fails
        """
        if bindings is None:
            bindings = {}
        
        # Dereference variables
        term1 = UnificationEngine._deref(term1, bindings)
        term2 = UnificationEngine._deref(term2, bindings)
        
        # Same term
        if term1 == term2:
            return bindings
        
        # Variable unification
        if term1.is_variable():
            return UnificationEngine._unify_variable(term1, term2, bindings)
        if term2.is_variable():
            return UnificationEngine._unify_variable(term2, term1, bindings)
        
        # Function/constant unification
        if term1.name != term2.name or len(term1.args) != len(term2.args):
            return None
        
        # Recursively unify arguments
        for arg1, arg2 in zip(term1.args, term2.args):
            bindings = UnificationEngine.unify(arg1, arg2, bindings)
            if bindings is None:
                return None
        
        return bindings
    
    @staticmethod
    def _unify_variable(var: Term, term: Term, bindings: Dict[str, Term]) -> Optional[Dict[str, Term]]:
        """Unify a variable with a term"""
        # Occurs check: prevent infinite structures
        if UnificationEngine._occurs_check(var, term, bindings):
            return None
        
        # Add binding
        new_bindings = bindings.copy()
        new_bindings[var.name] = term
        return new_bindings
    
    @staticmethod
    def _occurs_check(var: Term, term: Term, bindings: Dict[str, Term]) -> bool:
        """Check if variable occurs in term (prevents infinite structures)"""
        term = UnificationEngine._deref(term, bindings)
        
        if var == term:
            return True
        
        if term.is_variable():
            return False
        
        return any(UnificationEngine._occurs_check(var, arg, bindings) for arg in term.args)
    
    @staticmethod
    def _deref(term: Term, bindings: Dict[str, Term]) -> Term:
        """
        Dereference variable to its binding with cycle detection
        
        Args:
            term: Term to dereference
            bindings: Variable bindings
            
        Returns:
            Dereferenced term
            
        Raises:
            ValueError: If circular binding detected
        """
        if not isinstance(term, Term):
            return term
        
        visited: Set[str] = set()
        max_depth = 1000  # Safety limit
        depth = 0
        
        while term.is_variable() and term.name in bindings:
            # Cycle detection
            if term.name in visited:
                raise ValueError(
                    f"Circular binding detected: {term.name} -> ... -> {term.name}. "
                    f"Binding chain: {' -> '.join(visited)} -> {term.name}"
                )
            
            # Depth limit (safety net)
            if depth >= max_depth:
                raise ValueError(
                    f"Dereferencing depth exceeded {max_depth}. "
                    f"Possible infinite loop in bindings."
                )
            
            visited.add(term.name)
            next_term = bindings[term.name]
            
            if not isinstance(next_term, Term):
                break
            
            term = next_term
            depth += 1
        
        return term
    
    @staticmethod
    def apply_bindings(atom: Atom, bindings: Dict[str, Term]) -> Atom:
        """Apply variable bindings to atom"""
        new_terms = tuple(UnificationEngine._apply_to_term(term, bindings) for term in atom.terms)
        return Atom(atom.predicate, new_terms)
    
    @staticmethod
    def _apply_to_term(term: Term, bindings: Dict[str, Term]) -> Term:
        """Apply bindings to a single term"""
        term = UnificationEngine._deref(term, bindings)
        
        if term.args:
            new_args = tuple(UnificationEngine._apply_to_term(arg, bindings) for arg in term.args)
            return Term(term.name, term.term_type, new_args)
        
        return term

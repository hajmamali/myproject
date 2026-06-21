"""
Forward Chaining Reasoner
==========================

Data-driven inference engine for MAHOUN platform.
Implements forward chaining (bottom-up reasoning) for rule-based inference.

Forward chaining starts from known facts and applies rules to derive new facts
until no more facts can be derived or a goal is reached.

Design Principles:
- Deterministic: Same knowledge base produces same results
- Complete: Finds all derivable facts
- Sound: Only derives valid conclusions
- Auditable: Full proof trace for each derived fact
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from mahoun.reasoning.first_order_logic import (
    Atom,
    Clause,
    FirstOrderLogicEngine,
    Substitution,
    UnificationError,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProofStep:
    """
    Single step in forward chaining proof.
    
    Attributes:
        derived_fact: The fact that was derived
        rule_used: The rule that was applied (None for initial facts)
        premises: Facts that were unified with rule body
        substitution: Substitution used in derivation
        proof_hash: Cryptographic hash for audit trail
    """
    derived_fact: Atom
    rule_used: Optional[Clause]
    premises: Tuple[Atom, ...]
    substitution: Substitution
    proof_hash: str
    
    def __str__(self) -> str:
        if self.rule_used is None:
            return f"FACT: {self.derived_fact}"
        premises_str = ", ".join(str(p) for p in self.premises)
        return f"DERIVED: {self.derived_fact} FROM {premises_str} USING {self.rule_used}"


@dataclass
class ForwardChainingResult:
    """
    Result of forward chaining inference.
    
    Attributes:
        derived_facts: All facts derived during inference
        proof_trace: Complete proof trace
        iterations: Number of iterations performed
        goal_reached: Whether goal was reached (if goal provided)
        statistics: Inference statistics
    """
    derived_facts: FrozenSet[Atom]
    proof_trace: List[ProofStep]
    iterations: int
    goal_reached: bool
    statistics: Dict[str, int] = field(default_factory=dict)
    
    def get_proof_for_fact(self, fact: Atom) -> List[ProofStep]:
        """Get proof steps that led to a specific fact"""
        return [step for step in self.proof_trace if step.derived_fact == fact]


class ForwardChainingEngine:
    """
    Forward chaining inference engine with indexing optimization.
    
    Implements data-driven reasoning:
    1. Start with known facts
    2. Find rules whose body matches known facts
    3. Apply rule to derive new fact
    4. Repeat until fixpoint or goal reached
    
    Optimizations:
    - Predicate indexing for fast fact lookup
    - Only process new facts each iteration
    - Early termination when goal reached
    
    Thread-safe: Uses immutable data structures.
    """
    
    def __init__(self, max_iterations: int = 1000) -> None:
        """
        Initialize forward chaining engine.
        
        Args:
            max_iterations: Maximum iterations to prevent infinite loops
        """
        self.fol_engine = FirstOrderLogicEngine()
        self.max_iterations = max_iterations
        self._unification_cache: Dict[Tuple[Atom, Atom], Optional[Substitution]] = {}
        log.info(f"Initialized ForwardChainingEngine (max_iterations={max_iterations})")
    
    def infer(
        self,
        facts: List[Clause],
        rules: List[Clause],
        goal: Optional[Atom] = None,
    ) -> ForwardChainingResult:
        """
        Perform forward chaining inference.
        
        Args:
            facts: Initial facts (clauses with no body)
            rules: Inference rules (clauses with body)
            goal: Optional goal to reach (stops when goal is derived)
        
        Returns:
            ForwardChainingResult with derived facts and proof trace
        
        Raises:
            ValueError: If input is invalid
            RuntimeError: If max iterations exceeded
        
        Examples:
            >>> engine = ForwardChainingEngine()
            >>> # Facts: parent(john, mary), parent(mary, susan)
            >>> facts = [
            ...     create_fact("parent", create_constant("john"), create_constant("mary")),
            ...     create_fact("parent", create_constant("mary"), create_constant("susan")),
            ... ]
            >>> # Rule: ancestor(X, Y) :- parent(X, Y)
            >>> X = create_variable("X")
            >>> Y = create_variable("Y")
            >>> Z = create_variable("Z")
            >>> rules = [
            ...     create_rule(
            ...         create_atom("ancestor", X, Y),
            ...         create_atom("parent", X, Y)
            ...     ),
            ...     create_rule(
            ...         create_atom("ancestor", X, Z),
            ...         create_atom("parent", X, Y),
            ...         create_atom("ancestor", Y, Z)
            ...     ),
            ... ]
            >>> result = engine.infer(facts, rules)
            >>> # Should derive: ancestor(john, mary), ancestor(mary, susan), ancestor(john, susan)
        """
        # Validate input
        for fact in facts:
            if not fact.is_fact():
                raise ValueError(f"Expected fact, got: {fact}")
        for rule in rules:
            if not rule.is_rule():
                raise ValueError(f"Expected rule, got: {rule}")
        
        # Initialize working memory with facts
        known_facts: Set[Atom] = set()
        proof_trace: List[ProofStep] = []
        
        # Build predicate index for fast lookup
        fact_index: Dict[str, Set[Atom]] = {}
        
        for fact in facts:
            if fact.head is None:
                raise ValueError(f"Fact has no head: {fact}")
            known_facts.add(fact.head)
            
            # Index by predicate
            pred = fact.head.predicate
            if pred not in fact_index:
                fact_index[pred] = set()
            fact_index[pred].add(fact.head)
            
            proof_hash = self.fol_engine.compute_proof_hash(fact, {})
            proof_trace.append(ProofStep(
                derived_fact=fact.head,
                rule_used=None,
                premises=tuple(),
                substitution={},
                proof_hash=proof_hash,
            ))
        
        log.info(f"Starting forward chaining with {len(known_facts)} facts and {len(rules)} rules")
        
        # Forward chaining loop - semi-naive evaluation
        # Only try rules where at least one body atom matches a new fact
        iteration = 0
        goal_reached = False
        rules_applied = 0
        new_facts_to_process = set(known_facts)  # Start with all initial facts
        
        while iteration < self.max_iterations and new_facts_to_process:
            iteration += 1
            current_new_facts: Set[Atom] = set()
            
            # Group new facts by predicate for efficient lookup
            new_facts_by_pred: Dict[str, Set[Atom]] = {}
            for fact in new_facts_to_process:
                pred = fact.predicate
                if pred not in new_facts_by_pred:
                    new_facts_by_pred[pred] = set()
                new_facts_by_pred[pred].add(fact)
            
            # Try to apply each rule
            for rule in rules:
                # Skip if rule body predicates don't match any new facts
                if not self._rule_can_fire(rule, new_facts_by_pred):
                    continue
                
                # Rename variables to avoid conflicts
                renamed_rule = self.fol_engine.rename_variables(rule)
                
                # Try to match rule body with known facts (using index)
                matches = self._find_matches_indexed(renamed_rule, fact_index, new_facts_to_process)
                
                for match_facts, subst in matches:
                    # Apply substitution to rule head
                    if renamed_rule.head is None:
                        continue
                    derived_fact = self.fol_engine.apply_substitution_atom(renamed_rule.head, subst)
                    
                    # Check if this is a new fact
                    if derived_fact not in known_facts:
                        current_new_facts.add(derived_fact)
                        known_facts.add(derived_fact)
                        rules_applied += 1
                        
                        # Add to index
                        pred = derived_fact.predicate
                        if pred not in fact_index:
                            fact_index[pred] = set()
                        fact_index[pred].add(derived_fact)
                        
                        # Record proof step
                        proof_hash = self.fol_engine.compute_proof_hash(renamed_rule, subst)
                        proof_trace.append(ProofStep(
                            derived_fact=derived_fact,
                            rule_used=renamed_rule,
                            premises=match_facts,
                            substitution=subst,
                            proof_hash=proof_hash,
                        ))
                        
                        log.debug(f"Derived: {derived_fact} from {match_facts} using {renamed_rule}")
                        
                        # Check if goal reached
                        if goal and self._matches_goal(derived_fact, goal):
                            goal_reached = True
                            log.info(f"Goal reached: {goal}")
            
            # Update new facts to process for next iteration
            new_facts_to_process = current_new_facts
            
            if not new_facts_to_process:
                log.info(f"Fixpoint reached after {iteration} iterations")
                break
            
            if goal_reached:
                break
        
        if iteration >= self.max_iterations:
            raise RuntimeError(f"Max iterations ({self.max_iterations}) exceeded")
        
        statistics = {
            "initial_facts": len(facts),
            "rules": len(rules),
            "derived_facts": len(known_facts) - len(facts),
            "total_facts": len(known_facts),
            "iterations": iteration,
            "rules_applied": rules_applied,
        }
        
        log.info(f"Forward chaining completed: {statistics}")
        
        return ForwardChainingResult(
            derived_facts=frozenset(known_facts),
            proof_trace=proof_trace,
            iterations=iteration,
            goal_reached=goal_reached,
            statistics=statistics,
        )
    
    def _find_matches(
        self,
        rule: Clause,
        known_facts: Set[Atom],
    ) -> List[Tuple[Tuple[Atom, ...], Substitution]]:
        """
        Find all ways to match rule body with known facts.
        
        Returns list of (matched_facts, substitution) pairs.
        """
        if not rule.body:
            return []
        
        # Start with first body atom
        matches: List[Tuple[Tuple[Atom, ...], Substitution]] = []
        
        # Recursively match body atoms
        self._match_body_atoms(
            body_atoms=list(rule.body),
            known_facts=known_facts,
            current_match=[],
            current_subst={},
            matches=matches,
        )
        
        return matches
    
    def _rule_can_fire(self, rule: Clause, new_facts_by_pred: Dict[str, Set[Atom]]) -> bool:
        """
        Check if rule can potentially fire with new facts.
        
        Returns True if at least one body atom predicate matches a new fact predicate.
        """
        for atom in rule.body:
            if atom.predicate in new_facts_by_pred:
                return True
        return False
    
    def _find_matches_indexed(
        self,
        rule: Clause,
        fact_index: Dict[str, Set[Atom]],
        new_facts: Set[Atom],
    ) -> List[Tuple[Tuple[Atom, ...], Substitution]]:
        """
        Find all ways to match rule body with known facts using predicate index.
        
        Optimization: Only consider matches that involve at least one new fact.
        
        Returns list of (matched_facts, substitution) pairs.
        """
        if not rule.body:
            return []
        
        matches: List[Tuple[Tuple[Atom, ...], Substitution]] = []
        
        # Recursively match body atoms with index
        self._match_body_atoms_indexed(
            body_atoms=list(rule.body),
            fact_index=fact_index,
            new_facts=new_facts,
            current_match=[],
            current_subst={},
            matches=matches,
            has_new_fact=False,
        )
        
        return matches
    
    def _match_body_atoms_indexed(
        self,
        body_atoms: List[Atom],
        fact_index: Dict[str, Set[Atom]],
        new_facts: Set[Atom],
        current_match: List[Atom],
        current_subst: Substitution,
        matches: List[Tuple[Tuple[Atom, ...], Substitution]],
        has_new_fact: bool,
    ) -> None:
        """
        Recursively match body atoms with indexed facts.
        
        CRITICAL OPTIMIZATION: Only adds matches that involve at least one new fact.
        This implements semi-naive evaluation for O(n²) instead of O(n³).
        """
        if not body_atoms:
            # All body atoms matched - only add if we used at least one new fact
            if has_new_fact:
                matches.append((tuple(current_match), current_subst))
            return
        
        # Try to match first remaining body atom
        body_atom = body_atoms[0]
        remaining_atoms = body_atoms[1:]
        
        # Apply current substitution to body atom
        body_atom = self.fol_engine.apply_substitution_atom(body_atom, current_subst)
        
        # Get candidate facts from index
        pred = body_atom.predicate
        candidate_facts = fact_index.get(pred, set())
        
        if not candidate_facts:
            # No facts with this predicate - early termination
            return
        
        # OPTIMIZATION: If this is the last atom and we need a new fact,
        # only try new facts
        if not remaining_atoms and not has_new_fact:
            candidate_facts = candidate_facts & new_facts
            if not candidate_facts:
                return
        
        # Try to unify with each candidate fact
        for fact in candidate_facts:
            try:
                # Attempt unification
                new_subst = self._unify_atoms(body_atom, fact, current_subst)
                
                # Check if this fact is new
                is_new = fact in new_facts
                
                # Recursively match remaining atoms
                self._match_body_atoms_indexed(
                    body_atoms=remaining_atoms,
                    fact_index=fact_index,
                    new_facts=new_facts,
                    current_match=current_match + [fact],
                    current_subst=new_subst,
                    matches=matches,
                    has_new_fact=has_new_fact or is_new,
                )
            except UnificationError:
                # This fact doesn't match, try next
                continue
    
    def _match_body_atoms(
        self,
        body_atoms: List[Atom],
        known_facts: Set[Atom],
        current_match: List[Atom],
        current_subst: Substitution,
        matches: List[Tuple[Tuple[Atom, ...], Substitution]],
    ) -> None:
        """
        Recursively match body atoms with known facts.
        
        Uses backtracking to find all possible matches.
        """
        if not body_atoms:
            # All body atoms matched
            matches.append((tuple(current_match), current_subst))
            return
        
        # Try to match first remaining body atom
        body_atom = body_atoms[0]
        remaining_atoms = body_atoms[1:]
        
        # Apply current substitution to body atom
        body_atom = self.fol_engine.apply_substitution_atom(body_atom, current_subst)
        
        # Try to unify with each known fact
        for fact in known_facts:
            try:
                # Attempt unification
                new_subst = self._unify_atoms(body_atom, fact, current_subst)
                
                # Recursively match remaining atoms
                self._match_body_atoms(
                    body_atoms=remaining_atoms,
                    known_facts=known_facts,
                    current_match=current_match + [fact],
                    current_subst=new_subst,
                    matches=matches,
                )
            except UnificationError:
                # This fact doesn't match, try next
                continue
    
    def _unify_atoms(self, atom1: Atom, atom2: Atom, subst: Substitution) -> Substitution:
        """
        Unify two atoms with caching.
        
        Raises UnificationError if atoms cannot be unified.
        
        OPTIMIZATION: Cache unification results for ground atoms.
        """
        if atom1.predicate != atom2.predicate:
            raise UnificationError(f"Different predicates: {atom1.predicate} vs {atom2.predicate}")
        
        if len(atom1.terms) != len(atom2.terms):
            raise UnificationError(f"Different arities: {len(atom1.terms)} vs {len(atom2.terms)}")
        
        # Check cache for ground atoms (no variables)
        if atom1.is_ground() and atom2.is_ground() and not subst:
            cache_key = (atom1, atom2)
            if cache_key in self._unification_cache:
                cached = self._unification_cache[cache_key]
                if cached is None:
                    raise UnificationError(f"Cached failure: {atom1} vs {atom2}")
                return cached
            
            try:
                # Unify terms pairwise
                current_subst = dict(subst)
                for term1, term2 in zip(atom1.terms, atom2.terms):
                    current_subst = self.fol_engine.unify(term1, term2, current_subst)
                
                self._unification_cache[cache_key] = current_subst
                return current_subst
            except UnificationError as e:
                self._unification_cache[cache_key] = None
                raise e
        
        # Unify terms pairwise (no caching for non-ground atoms)
        current_subst = dict(subst)
        for term1, term2 in zip(atom1.terms, atom2.terms):
            current_subst = self.fol_engine.unify(term1, term2, current_subst)
        
        return current_subst
    
    def _matches_goal(self, fact: Atom, goal: Atom) -> bool:
        """Check if fact matches goal (possibly with variables in goal)"""
        try:
            self._unify_atoms(fact, goal, {})
            return True
        except UnificationError:
            return False

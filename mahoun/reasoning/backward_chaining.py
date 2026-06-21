"""
Backward Chaining Reasoner
===========================

Goal-driven inference engine for MAHOUN platform.
Implements backward chaining (top-down reasoning) for rule-based inference.

Backward chaining starts from a goal and works backwards, finding rules
that could prove the goal, then recursively proving the rule premises.

Design Principles:
- Deterministic: Same knowledge base produces same results
- Goal-directed: Only explores relevant rules
- Sound: Only derives valid conclusions
- Auditable: Full proof tree for each goal
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
class ProofNode:
    """
    Node in backward chaining proof tree.
    
    Attributes:
        goal: The goal being proved
        rule_used: Rule used to prove goal (None for facts)
        subgoals: Subgoals that were proved
        substitution: Substitution used
        proof_hash: Cryptographic hash for audit trail
    """
    goal: Atom
    rule_used: Optional[Clause]
    subgoals: Tuple[ProofNode, ...]
    substitution: Substitution
    proof_hash: str
    depth: int = 0
    
    def __str__(self) -> str:
        indent = "  " * self.depth
        if self.rule_used is None:
            return f"{indent}FACT: {self.goal}"
        subgoals_str = "\n".join(str(sg) for sg in self.subgoals)
        return f"{indent}PROVE: {self.goal}\n{indent}USING: {self.rule_used}\n{subgoals_str}"
    
    def to_dict(self) -> Dict:
        """Convert proof tree to dictionary for serialization"""
        return {
            "goal": str(self.goal),
            "rule": str(self.rule_used) if self.rule_used else None,
            "subgoals": [sg.to_dict() for sg in self.subgoals],
            "substitution": {str(k): str(v) for k, v in self.substitution.items()},
            "proof_hash": self.proof_hash,
            "depth": self.depth,
        }


@dataclass
class BackwardChainingResult:
    """
    Result of backward chaining inference.
    
    Attributes:
        success: Whether goal was proved
        proof_tree: Proof tree (if successful)
        solutions: All solutions found (substitutions for goal variables)
        statistics: Inference statistics
    """
    success: bool
    proof_tree: Optional[ProofNode]
    solutions: List[Substitution]
    statistics: Dict[str, int] = field(default_factory=dict)
    
    def get_all_proof_nodes(self) -> List[ProofNode]:
        """Get all nodes in proof tree (depth-first traversal)"""
        if not self.proof_tree:
            return []
        
        nodes: List[ProofNode] = []
        self._collect_nodes(self.proof_tree, nodes)
        return nodes
    
    def _collect_nodes(self, node: ProofNode, nodes: List[ProofNode]) -> None:
        """Recursively collect all nodes"""
        nodes.append(node)
        for subgoal in node.subgoals:
            self._collect_nodes(subgoal, nodes)


class BackwardChainingEngine:
    """
    Backward chaining inference engine.
    
    Implements goal-driven reasoning:
    1. Start with goal to prove
    2. Find rules whose head unifies with goal
    3. Recursively prove rule body (subgoals)
    4. Backtrack if proof fails
    
    Thread-safe: Uses immutable data structures.
    """
    
    def __init__(self, max_depth: int = 100, find_all: bool = False) -> None:
        """
        Initialize backward chaining engine.
        
        Args:
            max_depth: Maximum proof depth to prevent infinite recursion
            find_all: Whether to find all solutions or stop at first
        """
        self.fol_engine = FirstOrderLogicEngine()
        self.max_depth = max_depth
        self.find_all = find_all
        log.info(f"Initialized BackwardChainingEngine (max_depth={max_depth}, find_all={find_all})")
    
    def prove(
        self,
        goal: Atom,
        facts: List[Clause],
        rules: List[Clause],
    ) -> BackwardChainingResult:
        """
        Prove a goal using backward chaining.
        
        Args:
            goal: Goal to prove
            facts: Known facts
            rules: Inference rules
        
        Returns:
            BackwardChainingResult with proof tree and solutions
        
        Raises:
            ValueError: If input is invalid
        
        Examples:
            >>> engine = BackwardChainingEngine()
            >>> # Facts: parent(john, mary)
            >>> facts = [create_fact("parent", create_constant("john"), create_constant("mary"))]
            >>> # Rule: ancestor(X, Y) :- parent(X, Y)
            >>> X = create_variable("X")
            >>> Y = create_variable("Y")
            >>> rules = [
            ...     create_rule(
            ...         create_atom("ancestor", X, Y),
            ...         create_atom("parent", X, Y)
            ...     )
            ... ]
            >>> # Goal: ancestor(john, mary)?
            >>> goal = create_atom("ancestor", create_constant("john"), create_constant("mary"))
            >>> result = engine.prove(goal, facts, rules)
            >>> result.success
            True
        """
        # Validate input
        for fact in facts:
            if not fact.is_fact():
                raise ValueError(f"Expected fact, got: {fact}")
        for rule in rules:
            if not rule.is_rule():
                raise ValueError(f"Expected rule, got: {rule}")
        
        log.info(f"Proving goal: {goal}")
        
        # Statistics
        stats = {
            "facts": len(facts),
            "rules": len(rules),
            "goals_explored": 0,
            "backtracks": 0,
            "max_depth_reached": 0,
        }
        
        # Find all solutions
        solutions: List[Tuple[ProofNode, Substitution]] = []
        visited: Set[Tuple[Atom, int]] = set()  # Cycle detection
        
        self._prove_goal(
            goal=goal,
            facts=facts,
            rules=rules,
            subst={},
            depth=0,
            solutions=solutions,
            stats=stats,
            visited=visited,
        )
        
        # Extract results
        success = len(solutions) > 0
        proof_tree = solutions[0][0] if solutions else None
        solution_substs = [sol[1] for sol in solutions]
        
        stats["solutions_found"] = len(solutions)
        
        log.info(f"Proof {'succeeded' if success else 'failed'}: {stats}")
        
        return BackwardChainingResult(
            success=success,
            proof_tree=proof_tree,
            solutions=solution_substs,
            statistics=stats,
        )
    
    def _prove_goal(
        self,
        goal: Atom,
        facts: List[Clause],
        rules: List[Clause],
        subst: Substitution,
        depth: int,
        solutions: List[Tuple[ProofNode, Substitution]],
        stats: Dict[str, int],
        visited: Set[Tuple[Atom, int]],
    ) -> None:
        """
        Recursively prove a goal.
        
        Uses depth-first search with backtracking.
        """
        # Update statistics
        stats["goals_explored"] += 1
        stats["max_depth_reached"] = max(stats["max_depth_reached"], depth)
        
        # Check depth limit
        if depth > self.max_depth:
            log.debug(f"Max depth exceeded at {goal}")
            return
        
        # Cycle detection
        goal_key = (goal, depth)
        if goal_key in visited:
            log.debug(f"Cycle detected at {goal}")
            return
        visited.add(goal_key)
        
        # Apply current substitution to goal
        goal = self.fol_engine.apply_substitution_atom(goal, subst)
        
        log.debug(f"{'  ' * depth}Proving: {goal}")
        
        # Try to match with facts
        for fact in facts:
            if fact.head is None:
                continue
            
            try:
                # Attempt unification with fact
                new_subst = self._unify_atoms(goal, fact.head, subst)
                
                # Success! Create proof node
                proof_hash = self.fol_engine.compute_proof_hash(fact, new_subst)
                proof_node = ProofNode(
                    goal=goal,
                    rule_used=None,
                    subgoals=tuple(),
                    substitution=new_subst,
                    proof_hash=proof_hash,
                    depth=depth,
                )
                
                solutions.append((proof_node, new_subst))
                log.debug(f"{'  ' * depth}Proved by fact: {fact}")
                
                if not self.find_all:
                    return
                # Continue to find more solutions
                
            except UnificationError:
                continue
        
        # Try to match with rules
        for rule in rules:
            # Rename variables to avoid conflicts
            renamed_rule = self.fol_engine.rename_variables(rule)
            
            if renamed_rule.head is None:
                continue
            
            try:
                # Attempt unification with rule head
                new_subst = self._unify_atoms(goal, renamed_rule.head, subst)
                
                # Recursively prove rule body
                subgoal_proofs: List[ProofNode] = []
                final_subst_container = [new_subst]  # Use container to pass by reference
                
                success = self._prove_body(
                    body_atoms=list(renamed_rule.body),
                    facts=facts,
                    rules=rules,
                    subst=new_subst,
                    depth=depth + 1,
                    subgoal_proofs=subgoal_proofs,
                    final_subst_out=final_subst_container,
                    stats=stats,
                    visited=visited,
                )
                
                if success:
                    # All subgoals proved! Create proof node
                    final_subst = final_subst_container[0]
                    proof_hash = self.fol_engine.compute_proof_hash(renamed_rule, final_subst)
                    proof_node = ProofNode(
                        goal=goal,
                        rule_used=renamed_rule,
                        subgoals=tuple(subgoal_proofs),
                        substitution=final_subst,
                        proof_hash=proof_hash,
                        depth=depth,
                    )
                    
                    solutions.append((proof_node, final_subst))
                    log.debug(f"{'  ' * depth}Proved by rule: {renamed_rule}")
                    
                    if not self.find_all:
                        return
                else:
                    stats["backtracks"] += 1
                
            except UnificationError:
                continue
        
        visited.remove(goal_key)
    
    def _prove_body(
        self,
        body_atoms: List[Atom],
        facts: List[Clause],
        rules: List[Clause],
        subst: Substitution,
        depth: int,
        subgoal_proofs: List[ProofNode],
        final_subst_out: List[Substitution],
        stats: Dict[str, int],
        visited: Set[Tuple[Atom, int]],
    ) -> bool:
        """
        Prove all atoms in rule body.
        
        Returns True if all subgoals proved, False otherwise.
        """
        if not body_atoms:
            # All subgoals proved
            final_subst_out[0] = subst
            return True
        
        # Prove first subgoal
        subgoal = body_atoms[0]
        remaining = body_atoms[1:]
        
        # Apply current substitution
        subgoal = self.fol_engine.apply_substitution_atom(subgoal, subst)
        
        # Find solutions for this subgoal
        subgoal_solutions: List[Tuple[ProofNode, Substitution]] = []
        self._prove_goal(
            goal=subgoal,
            facts=facts,
            rules=rules,
            subst=subst,
            depth=depth,
            solutions=subgoal_solutions,
            stats=stats,
            visited=visited,
        )
        
        # Try each solution
        for proof_node, new_subst in subgoal_solutions:
            subgoal_proofs.append(proof_node)
            
            # Recursively prove remaining subgoals
            success = self._prove_body(
                body_atoms=remaining,
                facts=facts,
                rules=rules,
                subst=new_subst,
                depth=depth,
                subgoal_proofs=subgoal_proofs,
                final_subst_out=final_subst_out,
                stats=stats,
                visited=visited,
            )
            
            if success:
                return True
            
            # Backtrack
            subgoal_proofs.pop()
        
        return False
    
    def _unify_atoms(self, atom1: Atom, atom2: Atom, subst: Substitution) -> Substitution:
        """
        Unify two atoms.
        
        Raises UnificationError if atoms cannot be unified.
        """
        if atom1.predicate != atom2.predicate:
            raise UnificationError(f"Different predicates: {atom1.predicate} vs {atom2.predicate}")
        
        if len(atom1.terms) != len(atom2.terms):
            raise UnificationError(f"Different arities: {len(atom1.terms)} vs {len(atom2.terms)}")
        
        # Unify terms pairwise
        current_subst = dict(subst)
        for term1, term2 in zip(atom1.terms, atom2.terms):
            current_subst = self.fol_engine.unify(term1, term2, current_subst)
        
        return current_subst

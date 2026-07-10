"""
Symbolic Reasoning Engine
==========================

High-level symbolic reasoning interface for MAHOUN platform.
Integrates first-order logic, forward chaining, and backward chaining.

This module provides deterministic, LLM-free reasoning for high-stakes decisions.

Design Principles:
- Zero hallucination: All inferences are rule-based
- Deterministic: Same input always produces same output
- Auditable: Complete proof traces
- Hybrid reasoning: Combines forward and backward chaining
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from mahoun.reasoning.backward_chaining import (
    BackwardChainingEngine,
    BackwardChainingResult,
)
from mahoun.reasoning.first_order_logic import (
    Atom,
    Clause,
    FirstOrderLogicEngine,
    Substitution,
    Term,
    create_atom,
    create_constant,
    create_fact,
    create_goal,
    create_rule,
    create_variable,
)
from mahoun.reasoning.forward_chaining import (
    ForwardChainingEngine,
    ForwardChainingResult,
)

log = logging.getLogger(__name__)


class ReasoningMode(Enum):
    """Reasoning modes"""
    FORWARD = "forward"  # Data-driven (bottom-up)
    BACKWARD = "backward"  # Goal-driven (top-down)
    HYBRID = "hybrid"  # Combine both


@dataclass
class KnowledgeBase:
    """
    Knowledge base for symbolic reasoning.
    
    Attributes:
        facts: Ground facts (no variables)
        rules: Inference rules
        metadata: Optional metadata for facts/rules
    """
    facts: List[Clause] = field(default_factory=list)
    rules: List[Clause] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_fact(self, fact: Clause) -> None:
        """Add a fact to knowledge base"""
        if not fact.is_fact():
            raise ValueError(f"Expected fact, got: {fact}")
        if fact not in self.facts:
            self.facts.append(fact)
            log.debug(f"Added fact: {fact}")
    
    def add_rule(self, rule: Clause) -> None:
        """Add a rule to knowledge base"""
        if not rule.is_rule():
            raise ValueError(f"Expected rule, got: {rule}")
        if rule not in self.rules:
            self.rules.append(rule)
            log.debug(f"Added rule: {rule}")
    
    def get_statistics(self) -> Dict[str, int]:
        """Get knowledge base statistics"""
        return {
            "facts": len(self.facts),
            "rules": len(self.rules),
            "total_clauses": len(self.facts) + len(self.rules),
        }


@dataclass
class ReasoningResult:
    """
    Result of symbolic reasoning.
    
    Attributes:
        success: Whether reasoning succeeded
        mode: Reasoning mode used
        forward_result: Forward chaining result (if applicable)
        backward_result: Backward chaining result (if applicable)
        derived_facts: All derived facts
        proof_trace: Complete proof trace
        statistics: Reasoning statistics
    """
    success: bool
    mode: ReasoningMode
    forward_result: Optional[ForwardChainingResult] = None
    backward_result: Optional[BackwardChainingResult] = None
    derived_facts: Set[Atom] = field(default_factory=set)
    proof_trace: List[Any] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            "success": self.success,
            "mode": self.mode.value,
            "derived_facts": [str(f) for f in self.derived_facts],
            "statistics": self.statistics,
        }


class SymbolicReasoningEngine:
    """
    High-level symbolic reasoning engine.
    
    Provides unified interface for:
    - Forward chaining (data-driven reasoning)
    - Backward chaining (goal-driven reasoning)
    - Hybrid reasoning (combine both)
    
    Thread-safe: All operations use immutable data structures.
    """
    
    def __init__(
        self,
        max_forward_iterations: int = 1000,
        max_backward_depth: int = 100,
    ) -> None:
        """
        Initialize symbolic reasoning engine.
        
        Args:
            max_forward_iterations: Max iterations for forward chaining
            max_backward_depth: Max depth for backward chaining
        """
        self.fol_engine = FirstOrderLogicEngine()
        self.forward_engine = ForwardChainingEngine(max_iterations=max_forward_iterations)
        self.backward_engine = BackwardChainingEngine(max_depth=max_backward_depth)
        self.knowledge_base = KnowledgeBase()
        
        log.info("Initialized SymbolicReasoningEngine")
    
    def add_fact(self, fact: Clause) -> None:
        """Add a fact to knowledge base"""
        self.knowledge_base.add_fact(fact)
    
    def add_rule(self, rule: Clause) -> None:
        """Add a rule to knowledge base"""
        self.knowledge_base.add_rule(rule)
    
    def add_facts_from_graph(self, graph_facts: List[Dict[str, Any]]) -> None:
        """
        Add facts from knowledge graph.
        
        Args:
            graph_facts: List of facts from graph (e.g., [{"predicate": "parent", "args": ["john", "mary"]}])
        """
        for fact_dict in graph_facts:
            predicate = fact_dict["predicate"]
            args = [create_constant(arg) for arg in fact_dict.get("args", [])]
            fact = create_fact(predicate, *args)
            self.add_fact(fact)
        
        log.info(f"Added {len(graph_facts)} facts from graph")
    
    def reason_forward(self, goal: Optional[Atom] = None) -> ReasoningResult:
        """
        Perform forward chaining reasoning.
        
        Args:
            goal: Optional goal to reach (stops when goal is derived)
        
        Returns:
            ReasoningResult with derived facts and proof trace
        """
        log.info("Starting forward chaining reasoning")
        
        forward_result = self.forward_engine.infer(
            facts=self.knowledge_base.facts,
            rules=self.knowledge_base.rules,
            goal=goal,
        )
        
        return ReasoningResult(
            success=True,
            mode=ReasoningMode.FORWARD,
            forward_result=forward_result,
            derived_facts=forward_result.derived_facts,
            proof_trace=forward_result.proof_trace,
            statistics={
                "mode": "forward",
                **forward_result.statistics,
                **self.knowledge_base.get_statistics(),
            },
        )
    
    def reason_backward(self, goal: Atom, find_all: bool = False) -> ReasoningResult:
        """
        Perform backward chaining reasoning.
        
        Args:
            goal: Goal to prove
            find_all: Whether to find all solutions
        
        Returns:
            ReasoningResult with proof tree and solutions
        """
        log.info(f"Starting backward chaining reasoning for goal: {goal}")
        
        # Configure engine
        self.backward_engine.find_all = find_all
        
        backward_result = self.backward_engine.prove(
            goal=goal,
            facts=self.knowledge_base.facts,
            rules=self.knowledge_base.rules,
        )
        
        # Extract derived facts from proof tree
        derived_facts: Set[Atom] = set()
        if backward_result.proof_tree:
            for node in backward_result.get_all_proof_nodes():
                derived_facts.add(node.goal)
        
        return ReasoningResult(
            success=backward_result.success,
            mode=ReasoningMode.BACKWARD,
            backward_result=backward_result,
            derived_facts=derived_facts,
            proof_trace=[backward_result.proof_tree] if backward_result.proof_tree else [],
            statistics={
                "mode": "backward",
                "solutions": len(backward_result.solutions),
                **backward_result.statistics,
                **self.knowledge_base.get_statistics(),
            },
        )
    
    def reason_hybrid(self, goal: Atom) -> ReasoningResult:
        """
        Perform hybrid reasoning (forward + backward).
        
        Strategy:
        1. Run forward chaining to derive all possible facts
        2. Run backward chaining on expanded knowledge base
        
        Args:
            goal: Goal to prove
        
        Returns:
            ReasoningResult combining both approaches
        """
        log.info(f"Starting hybrid reasoning for goal: {goal}")
        
        # Step 1: Forward chaining to expand knowledge base
        forward_result = self.forward_engine.infer(
            facts=self.knowledge_base.facts,
            rules=self.knowledge_base.rules,
        )
        
        # Step 2: Create expanded knowledge base
        expanded_facts = [
            Clause(head=fact, body=tuple())
            for fact in forward_result.derived_facts
        ]
        
        # Step 3: Backward chaining on expanded knowledge base
        backward_result = self.backward_engine.prove(
            goal=goal,
            facts=expanded_facts,
            rules=self.knowledge_base.rules,
        )
        
        # Combine results
        derived_facts = set(forward_result.derived_facts)
        if backward_result.proof_tree:
            for node in backward_result.get_all_proof_nodes():
                derived_facts.add(node.goal)
        
        return ReasoningResult(
            success=backward_result.success,
            mode=ReasoningMode.HYBRID,
            forward_result=forward_result,
            backward_result=backward_result,
            derived_facts=derived_facts,
            proof_trace=forward_result.proof_trace + ([backward_result.proof_tree] if backward_result.proof_tree else []),
            statistics={
                "mode": "hybrid",
                "forward": forward_result.statistics,
                "backward": backward_result.statistics,
                **self.knowledge_base.get_statistics(),
            },
        )
    
    def query(self, goal: Atom, mode: ReasoningMode = ReasoningMode.HYBRID) -> ReasoningResult:
        """
        Query the knowledge base.
        
        Args:
            goal: Goal to prove/derive
            mode: Reasoning mode to use
        
        Returns:
            ReasoningResult
        """
        if mode == ReasoningMode.FORWARD:
            return self.reason_forward(goal=goal)
        elif mode == ReasoningMode.BACKWARD:
            return self.reason_backward(goal=goal)
        elif mode == ReasoningMode.HYBRID:
            return self.reason_hybrid(goal=goal)
        else:
            raise ValueError(f"Unknown reasoning mode: {mode}")
    
    def explain_derivation(self, fact: Atom) -> Optional[str]:
        """
        Explain how a fact was derived.
        
        Args:
            fact: Fact to explain
        
        Returns:
            Human-readable explanation
        """
        # Run backward chaining to find proof
        result = self.reason_backward(goal=fact)
        
        if not result.success or not result.backward_result or not result.backward_result.proof_tree:
            return None
        
        # Generate explanation from proof tree
        return self._explain_proof_node(result.backward_result.proof_tree)
    
    def _explain_proof_node(self, node: Any, indent: int = 0) -> str:
        """Recursively explain proof node"""
        prefix = "  " * indent
        
        if node.rule_used is None:
            return f"{prefix}✓ {node.goal} (known fact)"
        
        explanation = f"{prefix}✓ {node.goal}\n"
        explanation += f"{prefix}  because:\n"
        
        for subgoal in node.subgoals:
            explanation += self._explain_proof_node(subgoal, indent + 2) + "\n"
        
        return explanation.rstrip()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            "knowledge_base": self.knowledge_base.get_statistics(),
            "forward_engine": {
                "max_iterations": self.forward_engine.max_iterations,
            },
            "backward_engine": {
                "max_depth": self.backward_engine.max_depth,
            },
        }
    
    def reset(self) -> None:
        """Reset knowledge base"""
        self.knowledge_base = KnowledgeBase()
        log.info("Reset knowledge base")


# Convenience functions for building knowledge bases

def build_legal_kb() -> SymbolicReasoningEngine:
    """
    Build a sample legal knowledge base.
    
    Example rules:
    - liable(X) :- negligent(X), caused_harm(X)
    - negligent(X) :- breached_duty(X), owed_duty(X)
    """
    engine = SymbolicReasoningEngine()
    
    # Variables
    X = create_variable("X")
    Y = create_variable("Y")
    
    # Rules
    engine.add_rule(create_rule(
        create_atom("liable", X),
        create_atom("negligent", X),
        create_atom("caused_harm", X),
    ))
    
    engine.add_rule(create_rule(
        create_atom("negligent", X),
        create_atom("breached_duty", X),
        create_atom("owed_duty", X),
    ))
    
    engine.add_rule(create_rule(
        create_atom("must_compensate", X, Y),
        create_atom("liable", X),
        create_atom("harmed", Y),
        create_atom("caused_by", Y, X),
    ))
    
    log.info("Built legal knowledge base")
    return engine


def build_contract_kb() -> SymbolicReasoningEngine:
    """
    Build a sample contract knowledge base.
    
    Example rules:
    - valid_contract(X) :- offer(X), acceptance(X), consideration(X)
    - enforceable(X) :- valid_contract(X), not_void(X)
    """
    engine = SymbolicReasoningEngine()
    
    X = create_variable("X")
    
    engine.add_rule(create_rule(
        create_atom("valid_contract", X),
        create_atom("offer", X),
        create_atom("acceptance", X),
        create_atom("consideration", X),
    ))
    
    engine.add_rule(create_rule(
        create_atom("enforceable", X),
        create_atom("valid_contract", X),
        create_atom("not_void", X),
    ))
    
    engine.add_rule(create_rule(
        create_atom("breach", X),
        create_atom("enforceable", X),
        create_atom("not_performed", X),
    ))
    
    log.info("Built contract knowledge base")
    return engine

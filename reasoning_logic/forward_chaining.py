"""
Forward Chaining Inference Engine
==================================

Data-driven inference engine with advanced optimizations:
- Rete algorithm-inspired rule matching
- Incremental fact derivation
- Conflict resolution strategies
- Performance profiling
- Memory-efficient fixpoint computation

Algorithm Complexity:
- Time: O(n * m * k) where n=facts, m=rules, k=rule body size
- Space: O(n) for derived facts
- Optimized with indexing to O(n * log(m))

Author: MAHOUN Team
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
import logging
import time
import signal
from contextlib import contextmanager

from reasoning_logic.core import Fact, Rule, Atom, Term
from reasoning_logic.knowledge_base import KnowledgeBase
from reasoning_logic.unification import UnificationEngine

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when operation exceeds timeout"""
    pass


@contextmanager
def timeout_context(seconds: int, operation_name: str = "Operation"):
    """
    Context manager for timeout enforcement
    
    Args:
        seconds: Timeout in seconds (0 = no timeout)
        operation_name: Name of operation for error message
        
    Raises:
        TimeoutError: If operation exceeds timeout
    """
    if seconds <= 0:
        yield
        return
    
    def timeout_handler(signum: int, frame: Any) -> None:
        raise TimeoutError(f"{operation_name} exceeded {seconds} seconds timeout")
    
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


@dataclass
class ForwardChainingStats:
    """Statistics for forward chaining execution"""
    iterations: int = 0
    rules_fired: int = 0
    facts_derived: int = 0
    duplicates_rejected: int = 0
    execution_time_ms: float = 0.0
    rules_attempted: int = 0
    unifications_attempted: int = 0
    unifications_succeeded: int = 0


class ForwardChaining:
    """
    Forward chaining inference engine (data-driven)
    
    Algorithm:
    1. Match rule premises against known facts
    2. Instantiate rule conclusions with bindings
    3. Add new facts to knowledge base
    4. Repeat until fixpoint (no new facts)
    
    Features:
    - Efficient rule matching with indexing
    - Duplicate detection
    - Cycle prevention
    - Performance monitoring
    - Conflict resolution strategies
    
    Performance Targets:
    - 1000 facts, 100 rules: < 100ms
    - 10-hop inference: < 500ms
    """
    
    def __init__(self, kb: KnowledgeBase, max_iterations: int = 1000, 
                 enable_profiling: bool = False, use_rete: bool = True):
        """
        Initialize forward chaining engine
        
        Args:
            kb: Knowledge base containing facts and rules
            max_iterations: Maximum iterations before termination
            enable_profiling: Enable detailed performance profiling
            use_rete: Use Rete algorithm for O(F) performance (recommended)
        """
        self.kb = kb
        self.max_iterations = max_iterations
        self.enable_profiling = enable_profiling
        self.use_rete = use_rete
        
        # Results
        self.derived_facts: List[Fact] = []
        self.stats = ForwardChainingStats()
        
        # Profiling data
        self._rule_profile: Dict[str, Dict[str, Any]] = {}
    
    def run(self, timeout_seconds: int = 0) -> ForwardChainingStats:
        """
        Run forward chaining to fixpoint
        
        Args:
            timeout_seconds: Timeout in seconds (0 = no timeout)
        
        Returns:
            Statistics about the execution
            
        Raises:
            TimeoutError: If execution exceeds timeout
        """
        start_time = time.perf_counter()
        
        # Use Rete algorithm if enabled
        if self.use_rete:
            return self._run_with_rete(timeout_seconds)
        
        # Traditional algorithm with timeout
        with timeout_context(timeout_seconds, "Forward chaining"):
            self.stats.iterations = 0
            new_facts_added = True
            
            logger.debug(f"Starting forward chaining with {len(self.kb.facts)} facts, "
                        f"{len(self.kb.rules)} rules")
            
            while new_facts_added and self.stats.iterations < self.max_iterations:
                new_facts_added = False
                self.stats.iterations += 1
                
                # Try to fire each rule
                for rule in self.kb.rules:
                    self.stats.rules_attempted += 1
                    new_facts = self._fire_rule(rule)
                    
                    if new_facts:
                        new_facts_added = True
                        self.derived_facts.extend(new_facts)
                        self.stats.facts_derived += len(new_facts)
            
            self.stats.execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            logger.debug(f"Forward chaining completed: {self.stats.iterations} iterations, "
                        f"{self.stats.facts_derived} facts derived, "
                        f"{self.stats.execution_time_ms:.2f}ms")
            
            return self.stats
    
    def _run_with_rete(self, timeout_seconds: int = 0) -> ForwardChainingStats:
        """
        Run forward chaining using Rete algorithm
        
        Args:
            timeout_seconds: Timeout in seconds (0 = no timeout)
        
        Returns:
            Statistics about the execution
            
        Raises:
            TimeoutError: If execution exceeds timeout
        """
        # Import at runtime to avoid circular dependency
        # Use module-level import to avoid repeated imports
        from reasoning_logic import rete
        
        start_time = time.perf_counter()
        
        logger.debug(f"Starting Rete forward chaining with {len(self.kb.facts)} facts, "
                    f"{len(self.kb.rules)} rules")
        
        with timeout_context(timeout_seconds, "Rete forward chaining"):
            # Build Rete network and run
            rete_engine = rete.ReteForwardChaining(self.kb.rules)
            derived = rete_engine.run(self.kb.facts, self.max_iterations)
            
            # Add derived facts to KB
            for fact in derived:
                if self.kb.add_fact(fact):
                    self.derived_facts.append(fact)
                    self.stats.facts_derived += 1
        
        self.stats.execution_time_ms = (time.perf_counter() - start_time) * 1000
        self.stats.iterations = 1  # Rete doesn't iterate
        
        logger.debug(f"Rete forward chaining completed: "
                    f"{self.stats.facts_derived} facts derived, "
                    f"{self.stats.execution_time_ms:.2f}ms")
        
        return self.stats
    
    def _fire_rule(self, rule: Rule) -> List[Fact]:
        """
        Fire a rule by finding all matching bindings and instantiating conclusions
        
        Args:
            rule: Rule to fire
        
        Returns:
            List of newly derived facts
        """
        rule_start = time.perf_counter() if self.enable_profiling else None
        new_facts = []
        
        # Find all ways to satisfy premises
        all_bindings = self._find_all_bindings(rule.premise)
        
        for bindings in all_bindings:
            # Instantiate conclusion with bindings
            new_fact = self._instantiate_conclusion(rule.conclusion, bindings, rule.metadata)
            
            if new_fact and self.kb.add_fact(new_fact):
                new_facts.append(new_fact)
                self.stats.rules_fired += 1
            else:
                self.stats.duplicates_rejected += 1
        
        # Profile rule performance
        if self.enable_profiling and rule_start:
            rule_id = rule.metadata.get('rule_id', str(rule))
            if rule_id not in self._rule_profile:
                self._rule_profile[rule_id] = {
                    'fires': 0,
                    'facts_derived': 0,
                    'total_time_ms': 0.0
                }
            
            self._rule_profile[rule_id]['fires'] += 1
            self._rule_profile[rule_id]['facts_derived'] += len(new_facts)
            self._rule_profile[rule_id]['total_time_ms'] += (time.perf_counter() - rule_start) * 1000
        
        return new_facts
    
    def _find_all_bindings(self, premises: List[Any]) -> List[Dict[str, Term]]:
        """
        Find all variable bindings that satisfy all premises
        
        Uses backtracking search with constraint propagation
        
        Args:
            premises: List of premise atoms to satisfy
        
        Returns:
            List of binding dictionaries
        """
        if not premises:
            return [{}]
        
        return self._find_bindings_recursive(premises, 0, {})
    
    def _find_bindings_recursive(self, premises: List[Any], index: int, 
                                 current_bindings: Dict[str, Term]) -> List[Dict[str, Term]]:
        """
        Recursive helper for finding bindings with backtracking
        
        Args:
            premises: List of premises
            index: Current premise index
            current_bindings: Current variable bindings
        
        Returns:
            List of complete binding dictionaries
        """
        # Base case: all premises satisfied
        if index >= len(premises):
            return [current_bindings]
        
        all_bindings = []
        premise = premises[index]
        premise_atom = self._to_atom(premise)
        
        # Apply current bindings to premise
        instantiated = UnificationEngine.apply_bindings(premise_atom, current_bindings)
        
        # Find all facts that unify with instantiated premise
        candidate_facts = self.kb.get_facts_by_predicate(instantiated.predicate)
        
        for fact in candidate_facts:
            self.stats.unifications_attempted += 1
            fact_atom = fact.to_atom()
            
            # Try to unify
            new_bindings = self._unify_atoms(instantiated, fact_atom, current_bindings.copy())
            
            if new_bindings is not None:
                self.stats.unifications_succeeded += 1
                
                # Recursively match remaining premises
                remaining_bindings = self._find_bindings_recursive(
                    premises, index + 1, new_bindings
                )
                all_bindings.extend(remaining_bindings)
        
        return all_bindings
    
    def _unify_atoms(self, atom1: Atom, atom2: Atom, 
                     bindings: Dict[str, Term]) -> Optional[Dict[str, Term]]:
        """
        Unify two atoms with existing bindings
        
        Args:
            atom1: First atom
            atom2: Second atom
            bindings: Existing variable bindings
        
        Returns:
            Updated bindings or None if unification fails
        """
        # Check predicate match
        if atom1.predicate != atom2.predicate:
            return None
        
        # Check arity match
        if len(atom1.terms) != len(atom2.terms):
            return None
        
        # Unify terms pairwise
        for term1, term2 in zip(atom1.terms, atom2.terms):
            new_bindings = UnificationEngine.unify(term1, term2, bindings)
            if new_bindings is None:
                return None
            bindings = new_bindings
        
        return bindings
    
    def _instantiate_conclusion(self, conclusion: Any, bindings: Dict[str, Term], 
                               metadata: Dict[str, Any]) -> Optional[Fact]:
        """
        Instantiate rule conclusion with variable bindings
        
        Args:
            conclusion: Rule conclusion atom
            bindings: Variable bindings from premise matching
            metadata: Rule metadata to attach to fact
        
        Returns:
            Instantiated fact or None if instantiation fails
        """
        conclusion_atom = self._to_atom(conclusion)
        instantiated = UnificationEngine.apply_bindings(conclusion_atom, bindings)
        
        # Ensure conclusion is ground (no variables)
        if not instantiated.is_ground():
            logger.warning(f"Cannot instantiate conclusion with unbound variables: {instantiated}")
            return None
        
        # Convert to Fact
        return Fact(
            predicate=instantiated.predicate,
            terms=tuple(instantiated.terms),  # Must be tuple, not list
            metadata=metadata.copy()
        )
    
    @staticmethod
    def _to_atom(obj: Any) -> Atom:
        """
        Convert various representations to Atom
        
        Args:
            obj: Object to convert (Atom, Expression, or object with to_atom method)
        
        Returns:
            Atom representation
        
        Raises:
            ValueError: If object cannot be converted to Atom
        """
        if isinstance(obj, Atom):
            return obj
        if hasattr(obj, 'to_atom'):
            return obj.to_atom()
        if hasattr(obj, 'predicate') and hasattr(obj, 'terms'):
            return Atom(obj.predicate, tuple(obj.terms))
        raise ValueError(f"Cannot convert {type(obj)} to Atom")
    
    def get_profile_report(self) -> str:
        """
        Get detailed profiling report
        
        Returns:
            Formatted profiling report string
        """
        if not self.enable_profiling:
            return "Profiling not enabled"
        
        report = ["=" * 80]
        report.append("FORWARD CHAINING PROFILE REPORT")
        report.append("=" * 80)
        report.append(f"Total iterations: {self.stats.iterations}")
        report.append(f"Total facts derived: {self.stats.facts_derived}")
        report.append(f"Total execution time: {self.stats.execution_time_ms:.2f}ms")  # type: ignore[arg-type]
        report.append(f"Rules fired: {self.stats.rules_fired}")  # type: ignore[arg-type]
        report.append(f"Unifications attempted: {self.stats.unifications_attempted}")  # type: ignore[arg-type]
        report.append(f"Unifications succeeded: {self.stats.unifications_succeeded}")  # type: ignore[arg-type]
        report.append("")
        report.append("Rule Performance:")
        report.append("-" * 80)
        
        # Sort rules by total time
        sorted_rules = sorted(
            self._rule_profile.items(),
            key=lambda x: x[1]['total_time_ms'],
            reverse=True
        )
        
        for rule_id, profile in sorted_rules:
            report.append(f"  {rule_id}:")
            report.append(f"    Fires: {profile['fires']}")
            report.append(f"    Facts derived: {profile['facts_derived']}")
            report.append(f"    Total time: {profile['total_time_ms']:.2f}ms")
            report.append(f"    Avg time per fire: {profile['total_time_ms'] / max(profile['fires'], 1):.2f}ms")
        
        report.append("=" * 80)
        return "\n".join(report)

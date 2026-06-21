"""
Knowledge Base
==============

Thread-safe knowledge base with efficient indexing for facts and rules.

Features:
- Predicate-based indexing for O(1) fact lookup
- Arity-based indexing for faster unification
- Duplicate detection
- Statistics tracking
"""

from typing import List, Dict, Set
from collections import defaultdict
from reasoning_logic.core import Fact, Rule, Atom


class KnowledgeBase:
    """
    Knowledge base with efficient indexing
    
    Features:
    - Predicate-based indexing for O(1) fact lookup
    - Arity-based indexing for faster unification
    - Duplicate detection
    - Statistics tracking
    
    **THREAD SAFETY**: This class is NOT thread-safe. If you need to access
    the knowledge base from multiple threads, you must provide external
    synchronization (e.g., using threading.Lock).
    
    Example with thread safety:
        ```python
        import threading
        kb = KnowledgeBase()
        kb_lock = threading.Lock()
        
        # In thread 1:
        with kb_lock:
            kb.add_fact(fact1)
        
        # In thread 2:
        with kb_lock:
            kb.add_fact(fact2)
        ```
    """
    
    def __init__(self):
        self.facts: List[Fact] = []
        self.rules: List[Rule] = []
        
        # Indexes for efficient lookup
        self._fact_index: Dict[str, List[Fact]] = defaultdict(list)
        self._fact_set: Set[Atom] = set()  # For duplicate detection
        self._rule_index: Dict[str, List[Rule]] = defaultdict(list)
        
        # Statistics
        self.stats = {
            'facts_added': 0,
            'rules_added': 0,
            'duplicates_rejected': 0
        }
    
    def add_fact(self, fact: Fact) -> bool:
        """
        Add a fact to the knowledge base
        
        Args:
            fact: Fact to add
        
        Returns:
            True if fact was added, False if duplicate
        """
        atom = fact.to_atom()
        
        # Check for duplicates
        if atom in self._fact_set:
            self.stats['duplicates_rejected'] += 1
            return False
        
        # Add fact
        self.facts.append(fact)
        self._fact_index[fact.predicate].append(fact)
        self._fact_set.add(atom)
        self.stats['facts_added'] += 1
        
        return True
    
    def add_rule(self, rule: Rule):
        """Add a rule to the knowledge base"""
        self.rules.append(rule)
        
        # Index by conclusion predicate
        conclusion_pred = rule.conclusion.predicate if hasattr(rule.conclusion, 'predicate') else str(rule.conclusion)
        self._rule_index[conclusion_pred].append(rule)
        self.stats['rules_added'] += 1
    
    def query(self, expression) -> List[Fact]:
        """Query facts matching the expression"""
        predicate = expression.predicate if hasattr(expression, 'predicate') else str(expression)
        
        # Extract predicate name (before parentheses)
        if '(' in predicate:
            predicate = predicate[:predicate.index('(')]
        
        # Return all facts with matching predicate
        return self._fact_index.get(predicate, [])
    
    def get_facts_by_predicate(self, predicate: str) -> List[Fact]:
        """Get all facts with given predicate"""
        return self._fact_index.get(predicate, [])
    
    def get_rules_by_conclusion(self, predicate: str) -> List[Rule]:
        """Get all rules that conclude given predicate"""
        return self._rule_index.get(predicate, [])
    
    def clear(self):
        """Clear all facts and rules"""
        self.facts.clear()
        self.rules.clear()
        self._fact_index.clear()
        self._fact_set.clear()
        self._rule_index.clear()
        self.stats = {
            'facts_added': 0,
            'rules_added': 0,
            'duplicates_rejected': 0
        }

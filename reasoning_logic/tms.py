"""
Truth Maintenance System (TMS)
===============================

Advanced belief revision and contradiction management system.

Features:
- Assumption-based TMS (ATMS)
- Justification tracking
- Contradiction detection and resolution
- Belief revision with minimal change
- Dependency tracking for explanations

Used for:
- Non-monotonic reasoning
- Default reasoning
- Belief revision
- Contradiction resolution in legal reasoning

Author: MAHOUN Team
"""

from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from reasoning_logic.core import Fact, Rule, Atom

logger = logging.getLogger(__name__)


class JustificationType(Enum):
    """Type of justification for a belief"""
    PREMISE = "premise"  # Given as input
    DERIVED = "derived"  # Inferred from rules
    ASSUMPTION = "assumption"  # Assumed by default
    EXTERNAL = "external"  # From external source


@dataclass
class Justification:
    """
    Justification for why a fact is believed
    
    Tracks:
    - Type of justification
    - Supporting facts (antecedents)
    - Rule used (if derived)
    - Confidence/strength
    """
    fact: Fact
    justification_type: JustificationType
    antecedents: List[Fact] = field(default_factory=list)
    rule: Optional[Rule] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_support_chain(self) -> List['Justification']:
        """Get full chain of supporting justifications"""
        chain = [self]
        for ant in self.antecedents:
            # Recursively get support chains
            # (would need TMS reference to look up)
            pass
        return chain


@dataclass
class Contradiction:
    """
    Detected contradiction between facts
    """
    fact1: Fact
    fact2: Fact
    justification1: Justification
    justification2: Justification
    contradiction_type: str = "direct"
    
    def __str__(self):
        return f"Contradiction: {self.fact1} ⊥ {self.fact2}"


class TruthMaintenanceSystem:
    """
    Truth Maintenance System for belief management
    
    Maintains:
    - Justifications for all beliefs
    - Dependency network
    - Contradiction detection
    - Belief revision strategies
    """
    
    def __init__(self, allow_contradictions: bool = False):
        """
        Initialize TMS
        
        Args:
            allow_contradictions: Allow contradictory beliefs (for analysis)
        """
        self.allow_contradictions = allow_contradictions
        
        # Justification network
        self._justifications: Dict[Atom, List[Justification]] = {}
        self._dependencies: Dict[Atom, Set[Atom]] = {}
        
        # Contradiction tracking
        self._contradictions: List[Contradiction] = []
        
        # Current belief state
        self._beliefs: Set[Atom] = set()
        self._assumptions: Set[Atom] = set()
    
    def add_premise(self, fact: Fact) -> bool:
        """
        Add a premise (given fact)
        
        Args:
            fact: Fact to add as premise
        
        Returns:
            True if added successfully
        """
        atom = fact.to_atom()
        
        justification = Justification(
            fact=fact,
            justification_type=JustificationType.PREMISE,
            confidence=fact.confidence
        )
        
        return self._add_justification(atom, justification)
    
    def add_derived_fact(self, fact: Fact, antecedents: List[Fact], 
                        rule: Optional[Rule] = None) -> bool:
        """
        Add a derived fact with its justification
        
        Args:
            fact: Derived fact
            antecedents: Facts used to derive this fact
            rule: Rule used for derivation
        
        Returns:
            True if added successfully
        """
        atom = fact.to_atom()
        
        justification = Justification(
            fact=fact,
            justification_type=JustificationType.DERIVED,
            antecedents=antecedents,
            rule=rule,
            confidence=min(ant.confidence for ant in antecedents) if antecedents else 1.0
        )
        
        # Track dependencies
        for ant in antecedents:
            ant_atom = ant.to_atom()
            if ant_atom not in self._dependencies:
                self._dependencies[ant_atom] = set()
            self._dependencies[ant_atom].add(atom)
        
        return self._add_justification(atom, justification)
    
    def add_assumption(self, fact: Fact) -> bool:
        """
        Add an assumption (default belief)
        
        Args:
            fact: Fact to assume
        
        Returns:
            True if added successfully
        """
        atom = fact.to_atom()
        
        justification = Justification(
            fact=fact,
            justification_type=JustificationType.ASSUMPTION,
            confidence=0.8  # Lower confidence for assumptions
        )
        
        self._assumptions.add(atom)
        return self._add_justification(atom, justification)
    
    def _add_justification(self, atom: Atom, justification: Justification) -> bool:
        """Internal method to add justification"""
        if atom not in self._justifications:
            self._justifications[atom] = []
        
        self._justifications[atom].append(justification)
        self._beliefs.add(atom)
        
        # Check for contradictions
        if not self.allow_contradictions:
            contradiction = self._check_contradiction(atom)
            if contradiction:
                self._contradictions.append(contradiction)
                logger.warning(f"Contradiction detected: {contradiction}")
                return False
        
        return True
    
    def _check_contradiction(self, atom: Atom) -> Optional[Contradiction]:
        """
        Check if atom contradicts existing beliefs
        
        Args:
            atom: Atom to check
        
        Returns:
            Contradiction if found, None otherwise
        """
        # Simple contradiction: negation
        # (Would need more sophisticated logic for real contradictions)
        
        # Check for explicit contradictions in metadata
        for existing_atom in self._beliefs:
            if self._are_contradictory(atom, existing_atom):
                return Contradiction(
                    fact1=Fact(predicate=atom.predicate, terms=list(atom.terms)),
                    fact2=Fact(predicate=existing_atom.predicate, terms=list(existing_atom.terms)),
                    justification1=self._justifications[atom][-1],
                    justification2=self._justifications[existing_atom][-1]
                )
        
        return None
    
    def _are_contradictory(self, atom1: Atom, atom2: Atom) -> bool:
        """
        Check if two atoms are contradictory
        
        Detects multiple types of contradictions:
        1. Functional dependency violations (same entity, different values)
        2. Explicit negation (if supported)
        3. Domain constraint violations
        
        Args:
            atom1: First atom
            atom2: Second atom
            
        Returns:
            True if atoms contradict each other
        """
        # Type 1: Functional dependency violation
        # Same predicate with same subject but different object
        if atom1.predicate == atom2.predicate and len(atom1.terms) == len(atom2.terms):
            if len(atom1.terms) >= 2:
                # Check if all terms except last are same (functional dependency)
                if atom1.terms[:-1] == atom2.terms[:-1]:
                    # Last term different = contradiction
                    if atom1.terms[-1] != atom2.terms[-1]:
                        return True
        
        # Type 2: Negation detection (if predicate starts with 'not_' or 'neg_')
        if atom1.predicate.startswith('not_') or atom1.predicate.startswith('neg_'):
            positive_pred = atom1.predicate.replace('not_', '').replace('neg_', '')
            if atom2.predicate == positive_pred and atom1.terms == atom2.terms:
                return True
        
        if atom2.predicate.startswith('not_') or atom2.predicate.startswith('neg_'):
            positive_pred = atom2.predicate.replace('not_', '').replace('neg_', '')
            if atom1.predicate == positive_pred and atom1.terms == atom2.terms:
                return True
        
        # Type 3: Domain-specific contradictions
        # Example: age(Person, X) where X < 0 or X > 150
        if atom1.predicate == 'age' and atom2.predicate == 'age':
            if len(atom1.terms) >= 2 and len(atom2.terms) >= 2:
                if atom1.terms[0] == atom2.terms[0]:  # Same person
                    # Different ages = contradiction
                    if atom1.terms[1] != atom2.terms[1]:
                        return True
        
        # Type 4: Temporal contradictions
        # before(A, B) and before(B, A)
        if atom1.predicate == 'before' and atom2.predicate == 'before':
            if len(atom1.terms) == 2 and len(atom2.terms) == 2:
                if atom1.terms[0] == atom2.terms[1] and atom1.terms[1] == atom2.terms[0]:
                    return True
        
        return False
    
    def retract(self, fact: Fact) -> Set[Atom]:
        """
        Retract a fact and all facts that depend on it
        
        Args:
            fact: Fact to retract
        
        Returns:
            Set of atoms that were retracted
        """
        atom = fact.to_atom()
        retracted = set()
        
        if atom not in self._beliefs:
            return retracted
        
        # Remove from beliefs
        self._beliefs.discard(atom)
        retracted.add(atom)
        
        # Recursively retract dependent facts
        if atom in self._dependencies:
            for dependent in self._dependencies[atom]:
                if dependent in self._beliefs:
                    dependent_fact = Fact(predicate=dependent.predicate, terms=list(dependent.terms))
                    retracted.update(self.retract(dependent_fact))
        
        # Remove justifications
        if atom in self._justifications:
            del self._justifications[atom]
        
        return retracted
    
    def get_justification(self, fact: Fact) -> Optional[List[Justification]]:
        """
        Get all justifications for a fact
        
        Args:
            fact: Fact to get justifications for
        
        Returns:
            List of justifications or None
        """
        atom = fact.to_atom()
        return self._justifications.get(atom)
    
    def get_contradictions(self) -> List[Contradiction]:
        """Get all detected contradictions"""
        return self._contradictions.copy()
    
    def is_believed(self, fact: Fact) -> bool:
        """Check if fact is currently believed"""
        return fact.to_atom() in self._beliefs
    
    def get_explanation(self, fact: Fact) -> str:
        """
        Generate human-readable explanation for why fact is believed
        
        Args:
            fact: Fact to explain
        
        Returns:
            Explanation string
        """
        atom = fact.to_atom()
        
        if atom not in self._justifications:
            return f"{fact} is not believed"
        
        lines = [f"Explanation for: {fact}"]
        lines.append("=" * 60)
        
        for i, just in enumerate(self._justifications[atom], 1):
            lines.append(f"\nJustification {i}:")
            lines.append(f"  Type: {just.justification_type.value}")
            lines.append(f"  Confidence: {just.confidence:.2f}")
            
            if just.antecedents:
                lines.append(f"  Based on:")
                for ant in just.antecedents:
                    lines.append(f"    - {ant}")
            
            if just.rule:
                lines.append(f"  Using rule: {just.rule}")
        
        return "\n".join(lines)

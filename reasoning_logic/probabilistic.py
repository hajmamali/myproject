"""
Probabilistic Reasoning Engine
===============================

Bayesian inference and probabilistic logic for uncertain reasoning.

Features:
- Bayesian networks
- Probabilistic logic programming (PLP)
- Markov Logic Networks (MLN)
- Uncertainty quantification
- Confidence propagation

Used for:
- Reasoning under uncertainty
- Confidence scoring
- Risk assessment
- Probabilistic legal reasoning

Author: MAHOUN Team
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import math
import logging

from reasoning_logic.core import Fact, Rule, Atom, Term

logger = logging.getLogger(__name__)


@dataclass
class ProbabilisticFact:
    """Fact with probability/confidence"""
    fact: Fact
    probability: float  # 0.0 to 1.0
    evidence: List[Fact] = field(default_factory=list)
    
    def __post_init__(self):
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"Probability must be in [0, 1], got {self.probability}")


@dataclass
class ProbabilisticRule:
    """Rule with conditional probability"""
    rule: Rule
    probability: float  # P(conclusion | premises)
    weight: float = 1.0  # MLN weight
    
    def __post_init__(self):
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"Probability must be in [0, 1], got {self.probability}")


class ProbabilisticReasoningEngine:
    """
    Probabilistic reasoning with Bayesian inference
    
    Supports:
    - Noisy-OR combination
    - Bayesian network inference
    - Markov Logic Networks
    - Confidence propagation
    """
    
    def __init__(self, default_probability: float = 0.5):
        """
        Initialize probabilistic reasoning engine
        
        Args:
            default_probability: Default probability for facts without explicit probability
        """
        self.default_probability = default_probability
        
        # Probabilistic knowledge base
        self._prob_facts: Dict[Atom, List[ProbabilisticFact]] = defaultdict(list)
        self._prob_rules: List[ProbabilisticRule] = []
        
        # Inference cache
        self._inference_cache: Dict[Atom, float] = {}
    
    def add_probabilistic_fact(self, fact: Fact, probability: float, 
                              evidence: Optional[List[Fact]] = None):
        """
        Add a probabilistic fact
        
        Args:
            fact: Fact to add
            probability: Probability of fact being true
            evidence: Supporting evidence
        """
        atom = fact.to_atom()
        prob_fact = ProbabilisticFact(
            fact=fact,
            probability=probability,
            evidence=evidence or []
        )
        self._prob_facts[atom].append(prob_fact)
        
        # Invalidate cache
        self._inference_cache.clear()
    
    def add_probabilistic_rule(self, rule: Rule, probability: float, weight: float = 1.0):
        """
        Add a probabilistic rule
        
        Args:
            rule: Rule to add
            probability: P(conclusion | premises)
            weight: MLN weight (log odds)
        """
        prob_rule = ProbabilisticRule(
            rule=rule,
            probability=probability,
            weight=weight
        )
        self._prob_rules.append(prob_rule)
        
        # Invalidate cache
        self._inference_cache.clear()
    
    def query_probability(self, fact: Fact) -> float:
        """
        Query probability of a fact
        
        Args:
            fact: Fact to query
        
        Returns:
            Probability in [0, 1]
        """
        atom = fact.to_atom()
        
        # Check cache
        if atom in self._inference_cache:
            return self._inference_cache[atom]
        
        # Direct evidence
        if atom in self._prob_facts:
            prob = self._combine_probabilities([pf.probability for pf in self._prob_facts[atom]])
            self._inference_cache[atom] = prob
            return prob
        
        # Infer from rules
        prob = self._infer_probability(atom)
        self._inference_cache[atom] = prob
        return prob
    
    def _infer_probability(self, atom: Atom) -> float:
        """
        Infer probability using probabilistic rules
        
        Uses noisy-OR combination for multiple derivation paths
        """
        probabilities = []
        
        for prob_rule in self._prob_rules:
            # Check if rule concludes this atom
            conclusion_atom = prob_rule.rule.conclusion.to_atom() if hasattr(prob_rule.rule.conclusion, 'to_atom') else None
            
            if conclusion_atom and conclusion_atom.predicate == atom.predicate:
                # Calculate probability of premises
                premise_prob = self._calculate_premise_probability(prob_rule.rule.premise)
                
                # P(conclusion) = P(conclusion | premises) * P(premises)
                derived_prob = prob_rule.probability * premise_prob
                probabilities.append(derived_prob)
        
        if not probabilities:
            return self.default_probability
        
        # Noisy-OR combination
        return self._noisy_or(probabilities)
    
    def _calculate_premise_probability(self, premises: List) -> float:
        """
        Calculate joint probability of premises
        
        Assumes independence (simplification)
        """
        if not premises:
            return 1.0
        
        prob = 1.0
        for premise in premises:
            premise_atom = premise.to_atom() if hasattr(premise, 'to_atom') else None
            if premise_atom:
                premise_prob = self.query_probability(
                    Fact(predicate=premise_atom.predicate, terms=list(premise_atom.terms))
                )
                prob *= premise_prob
        
        return prob
    
    def _noisy_or(self, probabilities: List[float]) -> float:
        """
        Noisy-OR combination of probabilities
        
        P(A or B or C) = 1 - (1-P(A)) * (1-P(B)) * (1-P(C))
        """
        if not probabilities:
            return 0.0
        
        complement_product = 1.0
        for p in probabilities:
            complement_product *= (1.0 - p)
        
        return 1.0 - complement_product
    
    def _combine_probabilities(self, probabilities: List[float]) -> float:
        """
        Combine multiple probability estimates
        
        Uses averaging for now (could use more sophisticated methods)
        """
        if not probabilities:
            return self.default_probability
        
        return sum(probabilities) / len(probabilities)
    
    def get_confidence_interval(self, fact: Fact, confidence_level: float = 0.95) -> Tuple[float, float]:
        """
        Get confidence interval for fact probability
        
        Args:
            fact: Fact to query
            confidence_level: Confidence level (e.g., 0.95 for 95%)
        
        Returns:
            (lower_bound, upper_bound)
        """
        prob = self.query_probability(fact)
        
        # Simple confidence interval (could use more sophisticated methods)
        margin = (1.0 - confidence_level) / 2
        lower = max(0.0, prob - margin)
        upper = min(1.0, prob + margin)
        
        return (lower, upper)
    
    def explain_probability(self, fact: Fact) -> str:
        """
        Explain how probability was derived
        
        Args:
            fact: Fact to explain
        
        Returns:
            Explanation string
        """
        atom = fact.to_atom()
        prob = self.query_probability(fact)
        
        lines = []
        lines.append(f"Probability of {fact}: {prob:.3f}")
        lines.append("=" * 60)
        
        # Direct evidence
        if atom in self._prob_facts:
            lines.append("\nDirect Evidence:")
            for pf in self._prob_facts[atom]:
                lines.append(f"  - P = {pf.probability:.3f}")
                if pf.evidence:
                    lines.append(f"    Based on: {', '.join(str(e) for e in pf.evidence)}")
        
        # Derived evidence
        lines.append("\nDerived from Rules:")
        for prob_rule in self._prob_rules:
            conclusion_atom = prob_rule.rule.conclusion.to_atom() if hasattr(prob_rule.rule.conclusion, 'to_atom') else None
            if conclusion_atom and conclusion_atom.predicate == atom.predicate:
                premise_prob = self._calculate_premise_probability(prob_rule.rule.premise)
                derived_prob = prob_rule.probability * premise_prob
                lines.append(f"  - Rule: {prob_rule.rule}")
                lines.append(f"    P(conclusion | premises) = {prob_rule.probability:.3f}")
                lines.append(f"    P(premises) = {premise_prob:.3f}")
                lines.append(f"    P(conclusion) = {derived_prob:.3f}")
        
        return "\n".join(lines)


class MarkovLogicNetwork:
    """
    Markov Logic Network for weighted first-order logic
    
    Combines logic and probability using weighted formulas
    """
    
    def __init__(self):
        """Initialize MLN"""
        self._formulas: List[Tuple[Rule, float]] = []  # (formula, weight)
        self._ground_network: Dict[Atom, Set[Atom]] = defaultdict(set)
    
    def add_formula(self, rule: Rule, weight: float):
        """
        Add weighted formula
        
        Args:
            rule: Logical formula
            weight: Weight (log odds)
        """
        self._formulas.append((rule, weight))
    
    def ground_network(self, constants: Set[Term]):
        """
        Ground the network with constants
        
        Args:
            constants: Set of constants to ground with
        """
        # TODO: Implement grounding
        pass
    
    def infer_map(self) -> Dict[Atom, bool]:
        """
        Maximum a posteriori (MAP) inference
        
        Returns:
            Most likely truth assignment
        """
        # TODO: Implement MAP inference
        return {}

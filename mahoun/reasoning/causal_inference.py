"""
Causal Inference Engine
========================

Infer causal relationships for legal reasoning.

Extracted from legacy code with upgrades.
"""


from typing import Any, Callable, Dict, List, Optional
import networkx as nx
import numpy as np
from mahoun.core.models import CausalRelation
from mahoun.core.logging import setup_logger

log = setup_logger("causal_inference")


class StructuralCausalModel:
    """
    Structural Causal Model (SCM)
    
    Features:
    - Represent causal mechanisms
    - Support interventions (do-operator)
    - Answer counterfactual queries
    """
    
    def __init__(self, dag: nx.DiGraph):
        """
        Initialize SCM
        
        Args:
            dag: Causal DAG
        """
        self.dag = dag
        self.mechanisms = {}  # Causal mechanisms f_i
        self.noise = {}  # Exogenous variables U_i
        
        log.info(f"Initialized SCM with {dag.number_of_nodes()} variables")
    
    def set_mechanism(self, variable: str, mechanism: Callable):
        """
        Set causal mechanism for variable
        
        Args:
            variable: Variable name
            mechanism: Function that computes variable from parents
        """
        self.mechanisms[variable] = mechanism
    
    def do(self, interventions: Dict[str, Any]) -> 'StructuralCausalModel':
        """
        Apply do-operator (intervention)
        
        Args:
            interventions: Dictionary of {variable: value}
            
        Returns:
            New SCM with interventions applied
        """
        # Create new DAG with intervention edges removed
        new_dag = self.dag.copy()
        
        for var in interventions:
            # Remove incoming edges (break causal mechanisms)
            if var in new_dag:
                new_dag.remove_edges_from(list(new_dag.in_edges(var)))
        
        # Create new SCM
        new_scm = StructuralCausalModel(new_dag)
        new_scm.mechanisms = self.mechanisms.copy()
        new_scm.noise = self.noise.copy()
        
        # Override mechanisms for intervened variables
        for var, value in interventions.items():
            new_scm.mechanisms[var] = lambda parents, v=value: v
        
        return new_scm
    
    def predict(
        self,
        query: str,
        evidence: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Predict value of query variable
        
        Args:
            query: Query variable
            evidence: Evidence (observed values)
            
        Returns:
            Predicted value
        """
        evidence = evidence or {}
        
        # Topological sort
        try:
            topo_order = list(nx.topological_sort(self.dag))
        except nx.NetworkXError:
            log.warning("DAG has cycles, using arbitrary order")
            topo_order = list(self.dag.nodes())
        
        # Compute values
        values = evidence.copy()
        
        for var in topo_order:
            if var in values:
                continue
            
            if var in self.mechanisms:
                # Get parent values
                parents = list(self.dag.predecessors(var))
                parent_values = {p: values.get(p, 0) for p in parents}
                
                # Apply mechanism
                values[var] = self.mechanisms[var](parent_values)
            else:
                # Use noise/default
                values[var] = self.noise.get(var, 0)
        
        return values.get(query)
    
    def counterfactual(
        self,
        query: str,
        intervention: Dict[str, Any],
        evidence: Dict[str, Any]
    ) -> Any:
        """
        Answer counterfactual query
        
        "What would Y be if we had done X=x, given that we observed Z=z?"
        
        Args:
            query: Query variable (Y)
            intervention: Intervention (X=x)
            evidence: Evidence (Z=z)
            
        Returns:
            Counterfactual value
        """
        # Step 1: Abduction - infer exogenous variables from evidence
        # (Simplified: assume noise is 0)
        
        # Step 2: Action - apply intervention
        intervened_scm = self.do(intervention)
        
        # Step 3: Prediction - predict query under intervention
        result = intervened_scm.predict(query, evidence)
        
        log.info(
            f"Counterfactual: {query} | do({intervention}) given {evidence} = {result}"
        )
        
        return result


class CausalInferenceEngine:
    """
    Causal inference for legal reasoning
    
    Features:
    - Add causal relationships
    - Infer causality from facts
    - Find primary causes
    
    Upgraded from legacy code with:
    - Pydantic models
    - Better structure
    - Type hints
    """
    
    def __init__(self):
        """Initialize causal inference engine"""
        self.causal_graph: Dict[str, List] = {}
        self.causal_relationships: List[Dict[str, Any]] = []
        
        log.info("Initialized CausalInferenceEngine")
    
    def add_causal_relationship(
        self,
        cause: str,
        effect: str,
        strength: float
    ):
        """
        Add causal relationship
        
        Args:
            cause: Cause fact
            effect: Effect fact
            strength: Relationship strength (0-1)
        """
        self.causal_relationships.append({
            "cause": cause,
            "effect": effect,
            "strength": strength
        })
        
        log.debug(f"Added causal relationship: {cause} → {effect} ({strength})")
    
    def infer_causality(
        self,
        facts: List[str],
        outcome: str
    ) -> Dict[str, Any]:
        """
        Infer causal relationships
        
        Args:
            facts: List of facts
            outcome: Outcome to explain
            
        Returns:
            Causal analysis with chain and primary cause
        """
        potential_causes: List[Any] = []
        for fact in facts:
            for relationship in self.causal_relationships:
                # Check if cause matches fact
                if relationship["cause"].lower() in fact.lower():
                    # Check if effect matches outcome
                    if relationship["effect"].lower() in outcome.lower():
                        causal_relation = CausalRelation(
                            cause=fact,
                            effect=outcome,
                            strength=relationship["strength"],
                            explanation=f"{fact} منجر به {outcome} می‌شود"
                        )
                        
                        potential_causes.append({
                            "cause": fact,
                            "effect": outcome,
                            "strength": relationship["strength"],
                            "explanation": causal_relation.explanation,
                            "relation": causal_relation
                        })
        
        # Find primary cause (highest strength)
        primary_cause: Optional[Any] = None
        if potential_causes:
            primary_cause = max(potential_causes, key=lambda x: x["strength"])
        
        # Calculate overall confidence
        confidence = (
            max([c["strength"] for c in potential_causes])
            if potential_causes
            else 0.0
        )
        
        log.debug(
            f"Inferred {len(potential_causes)} causal relationships, "
            f"confidence: {confidence:.2f}"
        )
        
        return {
            "causal_chain": [
                c["relation"] for c in potential_causes
            ],
            "primary_cause": primary_cause["relation"] if primary_cause else None,
            "confidence": confidence,
        }
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics"""
        return {
            "num_relationships": len(self.causal_relationships),
            "num_graph_nodes": len(self.causal_graph),
        }
    
    def clear(self):
        """Clear all relationships"""
        self.causal_graph.clear()
        self.causal_relationships.clear()
        log.info("Cleared causal relationships")

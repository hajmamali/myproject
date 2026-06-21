"""
Graph-Symbolic Bridge
=====================
Translates Neo4j Knowledge Graph subgraphs into First-Order Logic (FOL) facts
for the SymbolicReasoningEngine.

This ensures the Reasoning Engine can apply deterministic rules based on
real, grounded data retrieved from the KG.
"""

from typing import Any, Dict, List, Set
import logging
from mahoun.reasoning.first_order_logic import Atom, Term, TermType

logger = logging.getLogger(__name__)

class GraphSymbolicBridge:
    def __init__(self):
        self.predicate_mappings = {
            "HAS_PARTY": "has_role",
            "CITES": "refers_to",
            "ISSUED_BY": "issued_by"
        }
        
    def graph_to_facts(self, subgraph_nodes: List[Dict[str, Any]], subgraph_edges: List[Dict[str, Any]]) -> List[Atom]:
        """
        Translates a set of nodes and edges into FOL Atoms.
        
        Args:
            subgraph_nodes: List of Neo4j node dictionaries
            subgraph_edges: List of Neo4j relationship dictionaries
            
        Returns:
            List of Atom objects representing grounded facts
        """
        facts = []
        
        # Process Nodes (Unary Predicates)
        for node in subgraph_nodes:
            node_id = node.get("id", str(id(node)))
            label = node.get("label", "Entity").lower()
            
            term = Term(name=node_id, term_type=TermType.CONSTANT)
            
            if label == "verdict":
                facts.append(Atom("is_case", (term,)))
                # Add status facts if available
                if node.get("properties", {}).get("is_final"):
                    facts.append(Atom("is_final", (term,)))
            elif label == "person":
                facts.append(Atom("is_person", (term,)))
            elif label == "law":
                facts.append(Atom("is_law", (term,)))
                
        # Process Edges (Binary Predicates)
        for edge in subgraph_edges:
            source = edge.get("source")
            target = edge.get("target")
            rel_type = edge.get("type", "").upper()
            
            if not source or not target:
                continue
                
            source_term = Term(name=source, term_type=TermType.CONSTANT)
            target_term = Term(name=target, term_type=TermType.CONSTANT)
            pred_name = self.predicate_mappings.get(rel_type, rel_type.lower())
            
            if rel_type == "HAS_PARTY":
                role = edge.get("properties", {}).get("role", "party")
                role_pred = f"is_{role.lower().replace(' ', '_')}"
                facts.append(Atom(role_pred, (target_term, source_term)))
            else:
                facts.append(Atom(pred_name, (source_term, target_term)))
                
        logger.info(f"Bridge generated {len(facts)} symbolic facts from graph.")
        return facts

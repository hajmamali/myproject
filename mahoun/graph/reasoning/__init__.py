"""
Graph Reasoning Module
======================
Bridges Knowledge Graph and Symbolic Reasoner.

Components:
- GraphToFOLConverter: Converts graph nodes/edges to FOL facts
- PatternToRuleConverter: Extracts FOL rules from graph patterns
"""

from .graph_to_fol import GraphToFOLConverter, convert_graph_to_facts

__all__ = [
    "GraphToFOLConverter",
    "convert_graph_to_facts",
]

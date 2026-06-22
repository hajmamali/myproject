"""
Entity Linker Re-export
=======================
This file simply re-exports the canonical EntityLinker implementation
from mahoun.graph.builders.entity_linker to prevent duplication.
"""

from mahoun.graph.builders.entity_linker import (
    GraphNodeSpec,
    GraphEdgeSpec,
    LinkingResult,
    EntityLinker,
    link_entities_to_graph
)

__all__ = [
    "GraphNodeSpec",
    "GraphEdgeSpec",
    "LinkingResult",
    "EntityLinker",
    "link_entities_to_graph"
]

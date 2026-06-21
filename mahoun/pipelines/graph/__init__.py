"""
Graph Pipeline Package
======================
Entity linking and graph construction pipelines.
"""

from .entity_linker import EntityLinker, link_entities_to_graph

__all__ = ['EntityLinker', 'link_entities_to_graph']


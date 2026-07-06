from __future__ import annotations

import ast
from pathlib import Path
from .model import ProjectModel


class SemanticGraphBuilder:
    """
    Builds a Semantic Graph.
    Maps syntax entities to architectural roles (Controller, Service, Repository, etc.)
    based on naming conventions and structure.
    """
    def __init__(self, model: ProjectModel) -> None:
        self.model = model
        # Mapping of naming patterns to semantic roles
        self.role_patterns = {
            "Controller": ["controller", "api", "endpoint"],
            "Service": ["service", "manager", "logic"],
            "Repository": ["repository", "dao", "store"],
            "Policy": ["policy", "validator", "rule"],
            "Kernel": ["kernel", "core", "engine"],
            "Plugin": ["plugin", "extension", "adapter"],
            "Retriever": ["retriever", "fetcher", "loader"],
            "Pipeline": ["pipeline", "workflow", "sequence"],
        }

    def build_all(self) -> None:
        """
        Assigns semantic roles to symbols based on the ProjectModel.
        """
        for symbol in self.model.symbols:
            role = self._resolve_role(symbol.qualified_name)
            if role:
                self._add_semantic_node(symbol.qualified_name, role)

    def _resolve_role(self, qualified_name: str) -> str | None:
        name_lower = qualified_name.lower()
        for role, patterns in self.role_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                return role
        return None

    def _add_semantic_node(self, symbol_id: str, role: str) -> None:
        # Store as a mapping of symbol -> role in the semantic_graph
        self.model.semantic_graph[symbol_id] = {
            "role": role,
            "type": "architectural_entity"
        }

from __future__ import annotations

import ast
from pathlib import Path
from .model import ProjectModel


class DependencyAnalyzer:
    """
    Builds a Dependency Graph of the project.
    Represents import relationships and package hierarchy.
    """
    def __init__(self, model: ProjectModel) -> None:
        self.model = model

    def analyze_all(self) -> None:
        """
        Analyzes all parsed files to extract import relationships.
        """
        for file_path, tree in self.model.ast_forest.items():
            self._analyze_file(file_path, tree)

    def _analyze_file(self, file_path: Path, tree: ast.Module) -> None:
        current_module = self._get_module_name(file_path)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._add_dependency(current_module, alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._add_dependency(current_module, node.module)

    def _add_dependency(self, source: str, target: str) -> None:
        if source not in self.model.dependencies:
            self.model.dependencies[source] = set()
        self.model.dependencies[source].add(target)

    def _get_module_name(self, file_path: Path) -> str:
        relative = file_path.relative_to(self.model.root_path)
        return str(relative).replace("/", ".").replace(".py", "").strip(".")

from __future__ import annotations

import ast
from pathlib import Path
from .model import ProjectModel


class ProjectParser:
    """
    Reusable Parser Layer.
    Responsible for converting raw files into an AST Forest within the ProjectModel.
    """
    def __init__(self, project_model: ProjectModel) -> None:
        self.model = project_model

    def parse_all(self) -> None:
        """
        Parses all discovered files in the project and populates the AST forest.
        """
        for file_path in self.model.files:
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content)
                self.model.ast_forest[file_path] = tree
            except (SyntaxError, UnicodeDecodeError) as e:
                # Log error or store in model metadata for reporting
                self.model.metadata.setdefault("parse_errors", []).append({
                    "file": str(file_path),
                    "error": str(e)
                })

    def get_ast(self, file_path: Path) -> ast.Module | None:
        return self.model.ast_forest.get(file_path)

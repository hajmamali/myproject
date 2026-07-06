from __future__ import annotations

import ast
from pathlib import Path
from typing import Any
from .model import ProjectModel, Symbol


class SymbolIndexer:
    """
    Builds a comprehensive Symbol Index of the project.
    Traverses the AST Forest to extract every architectural entity.
    """
    def __init__(self, model: ProjectModel) -> None:
        self.model = model

    def index_all(self) -> None:
        """
        Indexes all symbols across all parsed files.
        """
        for file_path, tree in self.model.ast_forest.items():
            self._index_file(file_path, tree)

    def _index_file(self, file_path: Path, tree: ast.Module) -> None:
        module_name = self._get_module_name(file_path)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._add_symbol(
                    kind="class",
                    name=node.name,
                    file=file_path,
                    line=node.lineno,
                    column=node.col_offset,
                    module=module_name,
                    parent=None, # Logic for nesting classes can be added here
                )
                # Index methods inside class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        self._add_symbol(
                            kind="method",
                            name=item.name,
                            file=file_path,
                            line=item.lineno,
                            column=item.col_offset,
                            module=module_name,
                            parent=node.name,
                        )

            elif isinstance(node, ast.FunctionDef) and not self._is_inside_class(node, tree):
                self._add_symbol(
                    kind="function",
                    name=node.name,
                    file=file_path,
                    line=node.lineno,
                    column=node.col_offset,
                    module=module_name,
                    parent=None,
                )

    def _add_symbol(
        self, 
        kind: str, 
        name: str, 
        file: Path, 
        line: int, 
        column: int, 
        module: str, 
        parent: str | None
    ) -> None:
        symbol = Symbol(
            kind=kind,
            qualified_name=f"{module}.{name}" if not parent else f"{module}.{parent}.{name}",
            module=module,
            file=str(file),
            line=line,
            column=column,
            parent=parent,
        )
        self.model.symbols.append(symbol)

    def _get_module_name(self, file_path: Path) -> str:
        # Simplified module name extraction
        relative = file_path.relative_to(self.model.root_path)
        return str(relative).replace("/", ".").replace(".py", "").strip(".")

    def _is_inside_class(self, node: ast.FunctionDef, tree: ast.Module) -> bool:
        # This is a naive check; a full parent-map would be better
        # but sufficient for initial Symbol Index
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                if node in parent.body:
                    return True
        return False

from __future__ import annotations

import ast
from pathlib import Path
from .model import ProjectModel


class CallGraphBuilder:
    """
    Builds a Call Graph of the project.
    Represent runtime call relationships, including async and class methods.
    """
    def __init__(self, model: ProjectModel) -> None:
        self.model = model

    def build_all(self) -> None:
        """
        Traverses the AST forest to identify all function and method calls.
        """
        for file_path, tree in self.model.ast_forest.items():
            self._analyze_file(file_path, tree)

    def _analyze_file(self, file_path: Path, tree: ast.Module) -> None:
        current_scope = self._get_module_name(file_path)
        
        for node in ast.walk(tree):
            # We look for FunctionDef to establish the 'caller' scope
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                caller_name = self._get_qualified_name(node, file_path)
                
                # Search for calls inside this function
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Call):
                        callee = self._resolve_callee(subnode)
                        if callee:
                            self._add_call(caller_name, callee)

    def _resolve_callee(self, node: ast.Call) -> str | None:
        """
        Resolves the name of the function being called.
        Supports simple calls and attribute calls (e.g., obj.method()).
        """
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # For attribute calls, we capture the attribute name
            # Full resolution would require symbol table lookup
            return node.func.attr
        return None

    def _add_call(self, caller: str, callee: str) -> None:
        if caller not in self.model.call_graph:
            self.model.call_graph[caller] = set()
        self.model.call_graph[caller].add(callee)

    def _get_qualified_name(self, node: ast.FunctionDef, file_path: Path) -> str:
        module_name = self._get_module_name(file_path)
        return f"{module_name}.{node.name}"

    def _get_module_name(self, file_path: Path) -> str:
        relative = file_path.relative_to(self.model.root_path)
        return str(relative).replace("/", ".").replace(".py", "").strip(".")

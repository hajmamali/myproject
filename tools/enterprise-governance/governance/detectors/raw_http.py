from __future__ import annotations

import ast
from ..model import Detector, Finding, ProjectModel, Severity


class RawHttpDetector(Detector):
    def __init__(self) -> None:
        super().__init__(
            name="raw-http",
            category="architecture",
            severity=Severity.P1,
            description="Detects direct HTTP calls in Python source.",
            version="1.0",
            priority=5,
        )

    def analyze(self, model: ProjectModel) -> list[Finding]:
        findings: list[Finding] = []
        http_tokens = {"requests", "httpx", "urllib"}
        
        for file_path, tree in model.ast_forest.items():
            for node in ast.walk(tree):
                # Match imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(token in alias.name for token in http_tokens):
                            findings.append(self._create_finding(file_path, node))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and any(token in node.module for token in http_tokens):
                        findings.append(self._create_finding(file_path, node))
                
                # Match calls (e.g., requests.get)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name) and node.func.value.id in http_tokens:
                            findings.append(self._create_finding(file_path, node))
        return findings

    def _create_finding(self, file_path: Path, node: ast.AST) -> Finding:
        return Finding(
            severity=self.severity,
            category=self.category,
            title="Raw HTTP access",
            description="Direct HTTP calls detected in Python source.",
            recommendation="Wrap outbound calls behind a gateway or adapter.",
            confidence=0.85,
            fingerprint=f"raw-http:{file_path}",
            file=str(file_path),
            line=getattr(node, "lineno", 1),
            column=getattr(node, "col_offset", 1),
            symbol=None,
            detector=self.name,
        )

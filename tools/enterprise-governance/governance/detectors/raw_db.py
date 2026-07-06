from __future__ import annotations

import ast
from ..model import Detector, Finding, ProjectModel, Severity


class RawDatabaseDetector(Detector):
    def __init__(self) -> None:
        super().__init__(
            name="raw-db",
            category="architecture",
            severity=Severity.P1,
            description="Detects direct database access in Python source.",
            version="1.0",
            priority=10,  # Run early, but after any priority 0 detectors if any
        )

    def analyze(self, model: ProjectModel) -> list[Finding]:
        findings: list[Finding] = []
        for file_path, tree in model.ast_forest.items():
            # We look for imports of sqlite3 in the AST
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "sqlite3":
                            findings.append(
                                Finding(
                                    severity=self.severity,
                                    category=self.category,
                                    title="Raw DB access",
                                    description="Database access detected in Python source.",
                                    recommendation="Use a repository or service abstraction.",
                                    confidence=0.9,
                                    fingerprint=f"raw-db:{file_path}",
                                    file=str(file_path),
                                    line=node.lineno,
                                    column=node.col_offset,
                                    symbol=None,
                                    detector=self.name,
                                )
                            )
        return findings

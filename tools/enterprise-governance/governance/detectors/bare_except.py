from __future__ import annotations

import ast
from ..model import Detector, Finding, ProjectModel, Severity


class BareExceptDetector(Detector):
    def __init__(self) -> None:
        super().__init__(
            name="bare-except",
            category="exception",
            severity=Severity.P2,
            description="Detects bare except handlers in Python source.",
            version="1.0",
            priority=0,
        )

    def analyze(self, model: ProjectModel) -> list[Finding]:
        findings: list[Finding] = []
        for file_path, tree in model.ast_forest.items():
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    findings.append(
                        Finding(
                            severity=self.severity,
                            category=self.category,
                            title="Bare except",
                            description="A bare except handler was detected.",
                            recommendation="Catch specific exceptions and log with context.",
                            confidence=0.8,
                            fingerprint=f"bare-except:{file_path}",
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            symbol=None,
                            detector=self.name,
                        )
                    )
        return findings

from __future__ import annotations

import os
from pathlib import Path
from .model import Finding, ProjectModel, Severity
from .rule_engine import Rule


class FileSizeRule(Rule):
    """Rule that checks if files exceed a certain line count."""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        severity: Severity,
        category: str,
        recommendation: str,
        max_lines: int = 500
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            description=description,
            severity=severity,
            category=category,
            recommendation=recommendation
        )
        self.max_lines = max_lines
    
    def evaluate(self, model: ProjectModel) -> list[Finding]:
        findings = []
        for file_path in model.files:
            try:
                if not file_path.exists():
                    continue
                    
                with open(file_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f)
                
                if line_count > self.max_lines:
                    findings.append(
                        Finding(
                            severity=self.severity,
                            category=self.category,
                            title=f"File too large: {file_path.name}",
                            description=f"File {file_path} has {line_count} lines, which exceeds the limit of {self.max_lines} lines.",
                            recommendation=self.recommendation,
                            confidence=0.95,
                            fingerprint=f"file-size:{file_path}",
                            file=str(file_path),
                            line=1,
                            column=1,
                            symbol=None,
                            detector=self.name
                        )
                    )
            except (IOError, UnicodeDecodeError):
                # Skip files we can't read
                continue
                
        return findings


class NoRawDbInControllersRule(Rule):
    """Rule that checks for direct database access in controllers."""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        severity: Severity,
        category: str,
        recommendation: str
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            description=description,
            severity=severity,
            category=category,
            recommendation=recommendation
        )
    
    def evaluate(self, model: ProjectModel) -> list[Finding]:
        findings = []
        
        # Find all controller symbols
        controller_symbols = [
            s for s in model.symbols 
            if s.kind == "class" and "controller" in s.qualified_name.lower()
        ]
        
        # Find all files with raw database access
        db_access_files = {
            f.file for f in model.findings 
            if f.detector == "raw-db"
        }
        
        # Check if any controller files have database access
        for controller in controller_symbols:
            controller_file = controller.file
            if controller_file in db_access_files:
                findings.append(
                    Finding(
                        severity=self.severity,
                        category=self.category,
                        title="Direct database access in controller",
                        description=f"Controller class {controller.qualified_name} in {controller_file} directly accesses the database.",
                        recommendation=self.recommendation,
                        confidence=0.9,
                        fingerprint=f"no-db-controller:{controller_file}",
                        file=controller_file,
                        line=controller.line,
                        column=controller.column,
                        symbol=controller.qualified_name,
                        detector=self.name
                    )
                )
                
        return findings
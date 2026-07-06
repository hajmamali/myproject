from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional
from .model import Finding, ProjectModel, Severity


@dataclass(slots=True)
class Rule:
    """A governance rule that can be evaluated against a project model."""
    id: str
    name: str
    description: str
    severity: Severity
    category: str
    recommendation: str
    enabled: bool = True
    
    def evaluate(self, model: ProjectModel) -> List[Finding]:
        """Evaluate this rule against the model and return any violations.
        This method should be overridden by specific rule implementations."""
        if not self.enabled:
            return []
        return []  # To be implemented by subclasses


@dataclass(slots=True)
class FileSizeRule(Rule):
    """Rule that checks file sizes."""
    max_lines: int = 500
    
    def evaluate(self, model: ProjectModel) -> List[Finding]:
        if not self.enabled:
            return []
            
        findings = []
        for file_path in model.files:
            try:
                line_count = sum(1 for _ in file_path.open('r', encoding='utf-8'))
                if line_count > self.max_lines:
                    finding = Finding(
                        severity=self.severity,
                        category=self.category,
                        title=f"File too large: {file_path.name}",
                        description=f"File has {line_count} lines, which exceeds the limit of {self.max_lines} lines.",
                        recommendation=self.recommendation,
                        confidence=0.9,
                        fingerprint=f"rule:file-size:{file_path}",
                        file=str(file_path),
                        line=1,
                        column=1,
                        symbol=None,
                        detector=f"rule:{self.id}"
                    )
                    findings.append(finding)
            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read
                continue
        return findings


@dataclass(slots=True)
class NoRawDbInControllersRule(Rule):
    """Rule that prevents raw database access in controllers."""
    def evaluate(self, model: ProjectModel) -> List[Finding]:
        if not self.enabled:
            return []
            
        findings = []
        controller_files = set()
        
        # Find controller files based on semantic graph or naming
        for entity_id, entity_data in model.semantic_graph.items():
            if entity_data.get("role") == "Controller":
                # Extract file path from the entity
                # This is simplified - in reality we'd need to map back to files
                pass
                
        # For now, use a simpler approach: check for files with controller in name
        # that also have raw database access findings
        for finding in model.findings:
            if (finding.detector == "raw-db" and 
                "controller" in finding.file.lower()):
                # Create a new finding for the rule violation
                rule_finding = Finding(
                    severity=self.severity,
                    category=self.category,
                    title="Raw DB access in controller",
                    description="Direct database access detected in a controller file.",
                    recommendation=self.recommendation,
                    confidence=0.9,
                    fingerprint=f"rule:no-db-controller:{finding.file}",
                    file=finding.file,
                    line=finding.line,
                    column=finding.column,
                    symbol=finding.symbol,
                    detector=f"rule:{self.id}"
                )
                findings.append(rule_finding)
                
        return findings


class RuleEngine:
    """Engine for evaluating governance rules against a project model."""
    
    def __init__(self) -> None:
        self._rules: List[Rule] = []
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine."""
        self._rules.append(rule)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        for i, rule in enumerate(self._rules):
            if rule.id == rule_id:
                del self._rules[i]
                return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        for rule in self._rules:
            if rule.id == rule_id:
                return rule
        return None
    
    def get_all_rules(self) -> List[Rule]:
        """Get all rules."""
        return self._rules.copy()
    
    def evaluate_all(self, model: ProjectModel) -> List[Finding]:
        """Evaluate all rules against the model and return all findings."""
        findings = []
        for rule in self._rules:
            findings.extend(rule.evaluate(model))
        return findings
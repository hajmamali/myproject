from __future__ import annotations

from .model import ProjectModel, Severity


def score_project(project: ProjectModel) -> dict[str, float]:
    severity_weights = {
        Severity.INFO: 0.0,
        Severity.P2: 1.0,
        Severity.P1: 2.0,
        Severity.P0: 3.0,
        Severity.P0_BLOCKER: 4.0,
    }
    total = sum(severity_weights[finding.severity] for finding in project.findings)
    return {
        "architecture_score": max(0.0, 100.0 - total * 5.0),
        "governance_score": max(0.0, 100.0 - total * 4.0),
        "maintainability_score": max(0.0, 100.0 - total * 3.0),
        "complexity_score": min(100.0, 50.0 + len(project.files) * 0.1),
        "risk_score": min(100.0, total * 10.0),
        "confidence_score": 0.9,
        "trend_score": 0.0,
    }

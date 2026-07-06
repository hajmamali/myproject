from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .duplicates import DuplicateAnalysis


class Severity(str, Enum):
    INFO = "INFO"
    P2 = "P2"
    P1 = "P1"
    P0 = "P0"
    P0_BLOCKER = "P0_BLOCKER"


@dataclass(slots=True)
class Finding:
    severity: Severity
    category: str
    title: str
    description: str
    recommendation: str
    confidence: float
    fingerprint: str
    file: str
    line: int
    column: int
    symbol: str | None = None
    detector: str | None = None


@dataclass(slots=True)
class Detector:
    name: str
    category: str
    severity: Severity
    description: str
    version: str = "1.0"
    priority: int = 0  # Lower numbers run first

    def analyze(self, project: "Project") -> list[Finding]:
        raise NotImplementedError


@dataclass(slots=True)
class Symbol:
    kind: str
    qualified_name: str
    module: str
    file: str
    line: int
    column: int
    parent: str | None = None
    visibility: str = "public"
    decorators: list[str] = field(default_factory=list)
    inheritance: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    call_sites: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProjectModel:
    """
    Unified model of the project architecture.
    The single source of truth for all analysis subsystems.
    """
    root_path: Path
    files: list[Path] = field(default_factory=list)
    ast_forest: dict[Path, ast.Module] = field(default_factory=dict)
    symbols: list[Symbol] = field(default_factory=list)
    dependencies: dict[str, set[str]] = field(default_factory=dict)
    call_graph: dict[str, set[str]] = field(default_factory=dict)
    semantic_graph: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_file_ast(self, path: Path) -> ast.Module | None:
        return self.ast_forest.get(path)



@dataclass(slots=True)
class ScanResult:
    project: Project
    findings: list[Finding]
    scores: dict[str, float]
    fingerprint: str
    duplicate_analysis: "DuplicateAnalysis | None" = None

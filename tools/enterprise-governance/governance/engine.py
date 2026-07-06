from __future__ import annotations

from pathlib import Path

from .config import GovernanceConfig
from .detectors import BareExceptDetector, RawDatabaseDetector, RawHttpDetector
from .duplicates import analyze_p1_duplicates
from .indexer import SymbolIndexer
from .parser import ProjectParser
from .registry import DetectorRegistry
from .dependencies import DependencyAnalyzer
from .callgraph import CallGraphBuilder
from .semantics import SemanticGraphBuilder
from .model import Finding, ProjectModel, ScanResult, Severity
from .rule_engine import RuleEngine
from .scoring import score_project


class GovernanceEngine:
    def __init__(self, config: GovernanceConfig | None = None) -> None:
        self.config = config or GovernanceConfig()
        self.registry = DetectorRegistry()
        self.rule_engine = RuleEngine()
        
        # Register default detectors
        self.registry.register(RawDatabaseDetector())
        self.registry.register(RawHttpDetector())
        self.registry.register(BareExceptDetector())
        
        # Load default rules
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default governance rules."""
        # These would normally be loaded from configuration
        # For now, we'll skip loading default rules to keep it simple
        pass

    def scan(self, path: str | Path) -> ScanResult:
        project_path = Path(path)
        
        # 1. Initialize ProjectModel
        model = ProjectModel(
            root_path=project_path, 
            files=list(project_path.rglob("*.py"))
        )

        # 2. Run Parser Layer
        parser = ProjectParser(model)
        parser.parse_all()

        # 3. Build Symbol Index
        indexer = SymbolIndexer(model)
        indexer.index_all()

        # 4. Build Dependency Graph
        dep_analyzer = DependencyAnalyzer(model)
        dep_analyzer.analyze_all()

        # 5. Build Call Graph
        call_builder = CallGraphBuilder(model)
        call_builder.build_all()

        # 6. Build Semantic Graph
        semantic_builder = SemanticGraphBuilder(model)
        semantic_builder.build_all()

        # 7. Run Detectors (now consuming ProjectModel) in priority order
        findings: list[Finding] = []
        for detector in self.registry.get_all_detectors():
            findings.extend(detector.analyze(model))
        model.findings = findings

        # 8. Evaluate Rules
        rule_findings = self.rule_engine.evaluate_all(model)
        findings.extend(rule_findings)
        model.findings = findings

        # 9. Duplicate Analysis & Prioritization
        duplicate_analysis = analyze_p1_duplicates(findings)
        if duplicate_analysis.suggestions:
            prioritized_findings = _apply_duplicate_prioritization(findings, duplicate_analysis)
            model.findings = prioritized_findings

        # 10. Scoring
        scores = score_project(model)
        
        return ScanResult(
            project=model,
            findings=model.findings,
            scores=scores,
            fingerprint="stable",
            duplicate_analysis=duplicate_analysis if duplicate_analysis.groups else None,
        )


def _apply_duplicate_prioritization(
    findings: list[Finding],
    analysis: "DuplicateAnalysis",
) -> list[Finding]:
    files_by_priority: dict[str, str] = {}
    for group in analysis.groups:
        files_by_priority[group.file] = group.suggested_priority

    def sort_key(f: Finding) -> tuple[int, int]:
        priority_rank = {"critical": 0, "high": 1, "medium": 2}.get(
            files_by_priority.get(f.file, ""), 3
        )
        sev_rank = {
            Severity.P0_BLOCKER: 0,
            Severity.P0: 1,
            Severity.P1: 2,
            Severity.P2: 3,
            Severity.INFO: 4,
        }.get(f.severity, 5)
        return (priority_rank, sev_rank)

    return sorted(findings, key=sort_key)
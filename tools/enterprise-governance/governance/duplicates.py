from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .model import Finding, Severity


@dataclass(slots=True)
class DuplicateGroup:
    file: str
    detectors: list[str]
    category: str
    confidence: float
    suggested_priority: str

    @property
    def detector_count(self) -> int:
        return len(self.detectors)


@dataclass(slots=True)
class DuplicateAnalysis:
    groups: list[DuplicateGroup] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def total_duplicate_files(self) -> int:
        return len(self.groups)

    @property
    def high_priority_files(self) -> int:
        return sum(1 for g in self.groups if g.suggested_priority == "critical")

    @property
    def affected_detectors(self) -> set[str]:
        return {d for g in self.groups for d in g.detectors}


_PRIORITY_CONFIDENCE_BOOST_P1_OVERLAP = 0.95


def analyze_p1_duplicates(findings: list[Finding]) -> DuplicateAnalysis:
    p1_findings = [f for f in findings if f.severity == Severity.P1]
    if not p1_findings:
        return DuplicateAnalysis()

    by_file: dict[str, list[Finding]] = defaultdict(list)
    for f in p1_findings:
        by_file[f.file].append(f)

    groups: list[DuplicateGroup] = []
    suggestions: list[str] = []

    for file_path, file_findings in sorted(by_file.items()):
        if len(file_findings) < 2:
            continue

        detector_set = sorted({f.detector or "unknown" for f in file_findings})
        category_set = {f.category for f in file_findings}

        avg_confidence = sum(f.confidence for f in file_findings) / len(file_findings)
        overlap_confidence = min(avg_confidence * _PRIORITY_CONFIDENCE_BOOST_P1_OVERLAP, 1.0)

        category_label = ", ".join(sorted(category_set))

        priority = _compute_priority(file_findings, detector_set)
        group = DuplicateGroup(
            file=file_path,
            detectors=detector_set,
            category=category_label,
            confidence=overlap_confidence,
            suggested_priority=priority,
        )
        groups.append(group)

        suggestion = _generate_suggestion(file_path, file_findings, detector_set, priority)
        suggestions.append(suggestion)

    groups.sort(key=lambda g: (-g.detector_count, -g.confidence, g.file))
    suggestions.sort()

    return DuplicateAnalysis(groups=groups, suggestions=suggestions)


def _compute_priority(findings: list[Finding], detector_set: list[str]) -> str:
    count = len(detector_set)
    avg_confidence = sum(f.confidence for f in findings) / len(findings)

    if count >= 2 and avg_confidence >= 0.9:
        return "critical"
    if count >= 2 and avg_confidence >= 0.8:
        return "high"
    if count >= 2:
        return "medium"
    return "low"


def _generate_suggestion(
    file_path: str,
    findings: list[Finding],
    detector_set: list[str],
    priority: str,
) -> str:
    titles = sorted({f.title for f in findings})
    recs = sorted({f.recommendation for f in findings})
    combined_titles = ", ".join(titles)

    prefix = "[P1-DUPLICATE-CRITICAL]" if priority == "critical" else "[P1-DUPLICATE]"

    return (
        f"{prefix} {file_path}: {combined_titles} "
        f"[{', '.join(detector_set)}] "
        f"→ priority={priority} "
        f"→ {', '.join(recs)}"
    )
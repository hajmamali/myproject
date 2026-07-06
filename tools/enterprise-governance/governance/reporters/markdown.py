from __future__ import annotations

from pathlib import Path

from ..model import ScanResult


def write_markdown_report(result: ScanResult, output_path: Path) -> Path:
    lines = [
        "# Governance Report",
        "",
        f"- Files scanned: {len(result.project.files)}",
        f"- Findings: {len(result.findings)}",
    ]

    if result.duplicate_analysis and result.duplicate_analysis.groups:
        da = result.duplicate_analysis
        lines.extend([
            "",
            "## P1 Duplicate Analysis",
            "",
            f"- Files flagged by multiple detectors: {da.total_duplicate_files}",
            f"- High-priority (critical): {da.high_priority_files}",
            f"- Affected detectors: {', '.join(sorted(da.affected_detectors))}",
            "",
            "### Suggestions (fix these first)",
            "",
        ])
        for suggestion in da.suggestions:
            lines.append(f"- {suggestion}")
        lines.append("")

    duplicate_files = set()
    critical_files = set()
    if result.duplicate_analysis:
        for g in result.duplicate_analysis.groups:
            duplicate_files.add(g.file)
            if g.suggested_priority == "critical":
                critical_files.add(g.file)

    for finding in result.findings:
        tag = ""
        if finding.file in critical_files:
            tag = " **CRITICAL: flagged by multiple detectors**"
        elif finding.file in duplicate_files:
            tag = " *duplicate: flagged by multiple detectors*"
        lines.append(f"- [{finding.severity.value}] {finding.title} - {finding.file}{tag}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path

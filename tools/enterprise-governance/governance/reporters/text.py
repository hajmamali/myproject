from __future__ import annotations

from ..model import ScanResult


def write_text_report(result: ScanResult) -> str:
    lines = [
        f"Scanned {len(result.project.files)} files",
        f"Findings: {len(result.findings)}",
    ]

    if result.duplicate_analysis and result.duplicate_analysis.groups:
        da = result.duplicate_analysis
        lines.append("")
        lines.append(
            f"P1 Duplicates: {da.total_duplicate_files} file(s) flagged by multiple detectors"
        )
        lines.append(
            f"  Critical: {da.high_priority_files} | "
            f"Affected detectors: {', '.join(sorted(da.affected_detectors))}"
        )
        lines.append("  --- Suggestions (fix these first):")
        for suggestion in da.suggestions:
            lines.append(f"  {suggestion}")
        lines.append("")

    for finding in result.findings:
        priority_tag = ""
        if result.duplicate_analysis:
            for group in result.duplicate_analysis.groups:
                if group.file == finding.file and group.suggested_priority == "critical":
                    priority_tag = " *** CRITICAL (multi-detector overlap) ***"
                    break
                elif group.file == finding.file:
                    priority_tag = " ** DUPLICATE (multi-detector overlap) **"
                    break
        lines.append(
            f"- [{finding.severity.value}] {finding.title} ({finding.file}){priority_tag}"
        )
    return "\n".join(lines)

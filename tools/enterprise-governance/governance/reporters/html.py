from __future__ import annotations

from pathlib import Path

from ..model import ScanResult


def write_html_report(result: ScanResult, output_path: Path) -> Path:
    duplicate_block = ""
    if result.duplicate_analysis and result.duplicate_analysis.groups:
        da = result.duplicate_analysis
        suggestions_html = "".join(
            f"<li>{s}</li>" for s in da.suggestions
        )
        duplicate_block = f"""<section>
    <h2>P1 Duplicate Analysis</h2>
    <p>Files flagged by multiple detectors: {da.total_duplicate_files}</p>
    <p>High-priority (critical): {da.high_priority_files}</p>
    <p>Affected detectors: {', '.join(sorted(da.affected_detectors))}</p>
    <h3>Suggestions (fix first)</h3>
    <ul>{suggestions_html}</ul>
  </section>"""

    duplicate_files = set()
    critical_files = set()
    if result.duplicate_analysis:
        for g in result.duplicate_analysis.groups:
            duplicate_files.add(g.file)
            if g.suggested_priority == "critical":
                critical_files.add(g.file)

    rows = "".join(
        f"<tr{_row_class(finding.file, duplicate_files, critical_files)}>"
        f"<td>{finding.title}</td><td>{finding.severity.value}</td><td>{finding.file}</td></tr>"
        for finding in result.findings
    )
    html = f"""<!doctype html>
<html>
  <body>
    <h1>Governance Report</h1>
    {duplicate_block}
    <table>
      <tr><th>Title</th><th>Severity</th><th>File</th></tr>
      {rows}
    </table>
  </body>
</html>"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _row_class(file: str, duplicate_files: set[str], critical_files: set[str]) -> str:
    if file in critical_files:
        return ' style="background:#ffcccc"'
    if file in duplicate_files:
        return ' style="background:#fff3cc"'
    return ""

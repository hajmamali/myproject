from __future__ import annotations

from pathlib import Path

from ..model import ScanResult


def write_junit_report(result: ScanResult, output_path: Path) -> Path:
    cases = "".join(
        f"<testcase classname=\"governance\" name=\"{finding.title}\" />"
        for finding in result.findings
    )
    xml = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<testsuite name=\"governance\" tests=\"{len(result.findings)}\">{cases}</testsuite>"""
    output_path.write_text(xml, encoding="utf-8")
    return output_path

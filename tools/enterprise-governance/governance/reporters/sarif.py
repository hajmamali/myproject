from __future__ import annotations

import json
from pathlib import Path

from ..model import ScanResult


def write_sarif_report(result: ScanResult, output_path: Path) -> Path:
    payload = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {"name": "enterprise-governance"},
                "results": [
                    {
                        "ruleId": finding.detector or "unknown",
                        "level": "warning",
                        "message": {"text": finding.title},
                        "locations": [{"physicalLocation": {"artifactLocation": {"uri": finding.file}}}],
                    }
                    for finding in result.findings
                ],
            }
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path

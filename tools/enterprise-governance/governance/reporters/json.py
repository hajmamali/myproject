from __future__ import annotations

import json
from pathlib import Path

from ..model import ScanResult


def write_json_report(result: ScanResult, output_path: Path) -> Path:
    payload = {
        "findings": [
            {
                "severity": finding.severity.value,
                "category": finding.category,
                "title": finding.title,
                "description": finding.description,
                "recommendation": finding.recommendation,
                "confidence": finding.confidence,
                "fingerprint": finding.fingerprint,
                "file": finding.file,
                "line": finding.line,
                "column": finding.column,
                "symbol": finding.symbol,
                "detector": finding.detector,
            }
            for finding in result.findings
        ],
        "scores": result.scores,
    }

    if result.duplicate_analysis:
        payload["duplicate_analysis"] = {
            "total_duplicate_files": result.duplicate_analysis.total_duplicate_files,
            "high_priority_files": result.duplicate_analysis.high_priority_files,
            "affected_detectors": sorted(result.duplicate_analysis.affected_detectors),
            "suggestions": result.duplicate_analysis.suggestions,
            "groups": [
                {
                    "file": g.file,
                    "detectors": g.detectors,
                    "category": g.category,
                    "confidence": g.confidence,
                    "suggested_priority": g.suggested_priority,
                }
                for g in result.duplicate_analysis.groups
            ],
        }

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path

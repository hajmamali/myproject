from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .model import Finding, ScanResult
#- import Project # Removed unused import if it existed


def fingerprint_finding(finding: Finding) -> str:
    payload = {
        "category": finding.category,
        "title": finding.title,
        "description": finding.description,
        "file": finding.file,
        "symbol": finding.symbol,
        "detector": finding.detector,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def create_baseline(result: ScanResult, output_path: Path) -> Path:
    payload = {"findings": [fingerprint_finding(finding) for finding in result.findings]}
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def compare_baseline(result: ScanResult, baseline_path: Path) -> list[str]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    current = {fingerprint_finding(finding) for finding in result.findings}
    previous = set(baseline.get("findings", []))
    return sorted(current - previous)

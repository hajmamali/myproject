from pathlib import Path

from governance.engine import GovernanceEngine


def test_scan_detects_basic_findings(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text("import sqlite3\nimport requests\n\ntry:\n    pass\nexcept:\n    pass\n", encoding="utf-8")

    result = GovernanceEngine().scan(tmp_path)

    assert len(result.findings) >= 3
    assert any(finding.title == "Raw DB access" for finding in result.findings)
    assert any(finding.title == "Raw HTTP access" for finding in result.findings)
    assert any(finding.title == "Bare except" for finding in result.findings)

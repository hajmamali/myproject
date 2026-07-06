from pathlib import Path

from governance.engine import GovernanceEngine
from governance.reporters.html import write_html_report
from governance.reporters.json import write_json_report
from governance.reporters.junit import write_junit_report
from governance.reporters.markdown import write_markdown_report
from governance.reporters.sarif import write_sarif_report
from governance.reporters.text import write_text_report


def test_reports_are_written(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text("import sqlite3\n", encoding="utf-8")

    result = GovernanceEngine().scan(tmp_path)
    write_text_report(result)
    write_json_report(result, tmp_path / "report.json")
    write_html_report(result, tmp_path / "report.html")
    write_markdown_report(result, tmp_path / "report.md")
    write_junit_report(result, tmp_path / "report.xml")
    write_sarif_report(result, tmp_path / "report.sarif")

    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.html").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.xml").exists()
    assert (tmp_path / "report.sarif").exists()

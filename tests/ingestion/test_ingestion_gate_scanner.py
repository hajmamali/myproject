from pathlib import Path

from ci.ingestion_gate_scanner import (
    scan_directory,
    scan_file,
    scan_ingestion_file,
    scan_repository_scripts,
)


def test_real_specialized_adapter_is_gate_compliant():
    path = Path("mahoun/ingestion_adapters/banking_law_adapter.py")

    assert scan_file(path) == []


def test_scanner_rejects_adapter_without_gate(tmp_path: Path):
    adapter = tmp_path / "unsafe_adapter.py"
    adapter.write_text(
        "def extract(text):\n    return text\n",
        encoding="utf-8",
    )

    errors = scan_directory(tmp_path)

    assert len(errors) == 2
    assert "missing Execution Gate import" in errors[0]
    assert "missing Execution Gate call" in errors[1]


def test_scanner_identifies_legacy_ingestion_script(tmp_path: Path):
    script = tmp_path / "legacy_ingest.py"
    script.write_text(
        "from scripts.build_judgment_kg import EnterpriseJudgmentCompiler\n"
        "def ingest_judgments(items):\n"
        "    return EnterpriseJudgmentCompiler().compile(items)\n",
        encoding="utf-8",
    )

    errors = scan_ingestion_file(script)

    assert errors
    assert "missing Execution Gate import" in errors[0]


def test_repository_scan_isolated_from_non_ingestion_scripts(tmp_path: Path):
    (tmp_path / "utility.py").write_text(
        "def compile_report(value):\n    return value\n",
        encoding="utf-8",
    )
    (tmp_path / "ingest.py").write_text(
        "def ingest_corpus(value):\n    return value\n",
        encoding="utf-8",
    )

    errors = scan_repository_scripts(tmp_path)

    assert len(errors) == 2


def test_non_ingestion_parser_and_audit_are_not_false_positives(tmp_path: Path):
    (tmp_path / "parse_ara_judgments.py").write_text(
        "def parse(value):\n    return value\n", encoding="utf-8"
    )
    (tmp_path / "run_full_forensic_audit.py").write_text(
        "def audit(value):\n    return value\n", encoding="utf-8"
    )

    assert scan_repository_scripts(tmp_path) == []

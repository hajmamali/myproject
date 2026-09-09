"""AST gate for specialized ingestion adapters."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


GATE_MODULE = "mahoun.core.governance.ingestion_execution_gate"
INGESTION_NAMES = {
    "CanonicalJudgment",
    "EnterpriseJudgmentCompiler",
    "HardenedKnowledgeGraphCompiler",
    "GovernedIngestionRuntime",
    "SemanticMaterializer",
    "ingest_corpus",
    "ingest_judgment",
    "ingest_judgments",
}
INGESTION_SCRIPT_NAMES = {
    "build_judgment_kg.py",
    "build_legal_kg.py",
    "ingest_ara_judgments.py",
    "ingest_banking_laws.py",
    "ingest_engineering_and_4311.py",
    "kg_loader_enterprise.py",
    "materialize_phase_2b_semantic_graph.py",
    "simple_neo4j_ingest.py",
    "unified_ingest.py",
}


def scan_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports_gate = False
    calls_gate = False

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == GATE_MODULE:
            imports_gate = True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"enter", "require_active"}:
                calls_gate = True

    errors = []
    if not imports_gate:
        errors.append("missing Execution Gate import")
    if not calls_gate:
        errors.append("missing Execution Gate call")
    return [f"{path}: {error}" for error in errors]


def is_ingestion_implementation(path: Path, tree: ast.AST | None = None) -> bool:
    """Identify scripts that can extract or mutate legal graph data."""
    parsed = tree or ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    defined_names = {
        node.name
        for node in ast.walk(parsed)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    referenced_names = {
        node.id
        for node in ast.walk(parsed)
        if isinstance(node, ast.Name)
    }
    if defined_names & INGESTION_NAMES or referenced_names & INGESTION_NAMES:
        return True
    return path.name in INGESTION_SCRIPT_NAMES


def scan_ingestion_file(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if not is_ingestion_implementation(path, tree):
        return []
    errors = scan_file(path)
    return [f"ingestion implementation: {error}" for error in errors]


def scan_directory(directory: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(directory.glob("*.py")):
        if path.name == "__init__.py":
            continue
        errors.extend(scan_file(path))
    return errors


def scan_repository_scripts(scripts_directory: Path) -> list[str]:
    """Scan every repository script that looks like an ingestion implementation."""
    errors: list[str] = []
    for path in sorted(scripts_directory.glob("*.py")):
        if path.name == "__init__.py":
            continue
        errors.extend(scan_ingestion_file(path))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directory",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--scripts",
        type=Path,
        default=None,
        help="Also scan repository scripts for ingestion implementations.",
    )
    args = parser.parse_args(argv)
    errors = []
    if args.directory is not None:
        errors.extend(scan_directory(args.directory.resolve()))
    if args.scripts is not None:
        errors.extend(scan_repository_scripts(args.scripts.resolve()))
    if args.directory is None and args.scripts is None:
        errors.extend(
            scan_directory(
                (Path(__file__).parents[1] / "mahoun" / "ingestion_adapters")
            )
        )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK: all scanned ingestion implementations require Execution Gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

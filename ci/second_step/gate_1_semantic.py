#!/usr/bin/env python3
"""
Gate 1 — Semantic / Optional-aware Integrity Check (WARN-ONLY)

This gate inspects core/domain/orchestrator code for:
- Optional-return contracts around `return None`
- Silent exception patterns
- Predicate functions (`is_*`, `has_*`, `should_*`) returning None
- Docstring clarity for Optional-like functions

Initial mode (v1.1): REPORT-ONLY, EXIT CODE = 0
"""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INCLUDED_DIRS = [
    PROJECT_ROOT / "mahoun" / "core",
    PROJECT_ROOT / "mahoun" / "domain",
    PROJECT_ROOT / "mahoun" / "orchestrator",
]

EXCLUDED_PATH_PARTS = {
    "api",
    "tests",
    "ci",
}

OPTIONAL_NAME_PREFIXES = ("get_", "find_", "resolve_", "load_", "fetch_")
PREDICATE_NAME_PREFIXES = ("is_", "has_", "should_")


@dataclass
class Finding:
    file_path: Path
    line: int
    kind: str  # "ERROR" or "WARNING"
    code: str  # short code, e.g. SEMANTIC_VIOLATION
    message: str
    function: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers for AST inspection
# ---------------------------------------------------------------------------


def is_return_none(node: ast.Return) -> bool:
    if node.value is None:
        return False
    # Python 3.8+: ast.Constant
    if isinstance(node.value, ast.Constant):
        return node.value.value is None
    # Older style: ast.NameConstant
    if hasattr(ast, "NameConstant") and isinstance(node.value, ast.NameConstant):
        return node.value.value is None
    return False


def is_bool_annotation(returns: Optional[ast.expr], source: str) -> bool:
    if returns is None:
        return False
    ann = ast.get_source_segment(source, returns) or ""
    ann_str = ann.strip()
    if ann_str == "bool":
        return True
    # Handle Annotated[...] etc. approximately
    return "bool" in ann_str and "Optional" not in ann_str and "None" not in ann_str


def annotation_str(returns: Optional[ast.expr], source: str) -> str:
    if returns is None:
        return ""
    seg = ast.get_source_segment(source, returns)
    return (seg or "").strip()


def has_optional_contract(
    func_name: str,
    ann_str: str,
    docstring: str,
) -> bool:
    """
    Optional contract is considered present if ANY of:
    - Annotation contains Optional[...] or Union[..., None] or T | None
    - Function name has Optional-style prefix (get/find/resolve/load/fetch)
    - Docstring explicitly mentions None
    """
    # From type annotation
    lower_ann = ann_str.replace(" ", "")
    if "Optional[" in lower_ann:
        return True
    if "Union[" in lower_ann and "None" in lower_ann:
        return True
    if "|" in lower_ann and "None" in lower_ann:
        return True
    if lower_ann == "None":
        return True  # functions that only return None

    # From function naming convention
    for prefix in OPTIONAL_NAME_PREFIXES:
        if func_name.startswith(prefix):
            return True

    # From docstring
    if docstring:
        if "none" in docstring.lower():
            return True

    return False


def docstring_mentions_none(docstring: str) -> bool:
    if not docstring:
        return False
    return "none" in docstring.lower()


def is_predicate_function(func_name: str, returns: Optional[ast.expr], source: str) -> bool:
    for prefix in PREDICATE_NAME_PREFIXES:
        if func_name.startswith(prefix):
            return True
    return is_bool_annotation(returns, source)


# ---------------------------------------------------------------------------
# Core analysis logic
# ---------------------------------------------------------------------------


def analyze_function(
    func: ast.FunctionDef,
    source: str,
    file_path: Path,
) -> List[Finding]:
    findings: List[Finding] = []

    func_name = func.name
    docstring = ast.get_docstring(func) or ""
    ann_str = annotation_str(func.returns, source)

    has_ret_none = False
    # Collect all return statements and except handlers within the function
    returns: List[ast.Return] = []
    except_handlers: List[ast.ExceptHandler] = []

    for node in ast.walk(func):
        if isinstance(node, ast.Return):
            returns.append(node)
        elif isinstance(node, ast.ExceptHandler):
            except_handlers.append(node)

    for r in returns:
        if is_return_none(r):
            has_ret_none = True
            break

    is_predicate = is_predicate_function(func_name, func.returns, source)
    has_opt_contract = has_optional_contract(func_name, ann_str, docstring)
    doc_has_none = docstring_mentions_none(docstring)

    # RULE 2 — Silent Exception
    for handler in except_handlers:
        # except Exception:  (no alias name)
        if (
            isinstance(handler.type, ast.Name)
            and handler.type.id == "Exception"
            and handler.name is None
        ):
            # Does this handler return None anywhere?
            handler_returns_none = any(
                isinstance(n, ast.Return) and is_return_none(n)
                for n in ast.walk(handler)
            )
            if handler_returns_none:
                findings.append(
                    Finding(
                        file_path=file_path,
                        line=handler.lineno,
                        kind="ERROR",
                        code="SILENT_EXCEPTION",
                        message="Silent exception: 'except Exception' followed by 'return None'.",
                        function=func_name,
                    )
                )

    # RULE 1 / RULE 3 / RULE 4 — Optional & Predicate logic
    if has_ret_none:
        # Rule 3: Predicate functions must NOT return None
        if is_predicate:
            # Predicate returning None is always an error, regardless of Optional contract
            first_ret_line = next((r.lineno for r in returns if is_return_none(r)), func.lineno)
            findings.append(
                Finding(
                    file_path=file_path,
                    line=first_ret_line,
                    kind="ERROR",
                    code="PREDICATE_RETURNS_NONE",
                    message="Predicate function returns None (must be strictly bool).",
                    function=func_name,
                )
            )
        else:
            # Rule 1: Optional contract must be explicit if returning None
            if not has_opt_contract:
                first_ret_line = next((r.lineno for r in returns if is_return_none(r)), func.lineno)
                findings.append(
                    Finding(
                        file_path=file_path,
                        line=first_ret_line,
                        kind="ERROR",
                        code="SEMANTIC_VIOLATION",
                        message="None returned without explicit Optional contract.",
                        function=func_name,
                    )
                )
            else:
                # Rule 4: Docstring clarity (when Optional is allowed)
                if not doc_has_none:
                    first_ret_line = next((r.lineno for r in returns if is_return_none(r)), func.lineno)
                    findings.append(
                        Finding(
                            file_path=file_path,
                            line=first_ret_line,
                            kind="WARNING",
                            code="DOCSTRING_NONE_CLARITY",
                            message="Function can return None but docstring does not explain when/why.",
                            function=func_name,
                        )
                    )

    return findings


def analyze_file(path: Path) -> List[Finding]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        # Gate 0 should already have guaranteed structural validity
        return []

    findings: List[Finding] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            findings.extend(analyze_function(node, text, path))
        elif isinstance(node, ast.AsyncFunctionDef):
            findings.extend(analyze_function(node, text, path))

    return findings


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDED_PATH_PARTS:
        return True
    # Skip obvious test files even inside included dirs
    if "tests" in parts:
        return True
    if path.name.startswith("test_"):
        return True
    return False


def collect_files() -> List[Path]:
    files: List[Path] = []
    for base in INCLUDED_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if should_skip(p):
                continue
            files.append(p)
    return sorted(files)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_report(all_findings: List[Finding]) -> None:
    if not all_findings:
        print("Gate 1 — Semantic Integrity: No issues found.")
        return

    print("================================================")
    print("🧠 Gate 1: Semantic Integrity Report (WARN-ONLY)")
    print("================================================")
    print("")

    # Group by file
    by_file: dict[Path, List[Finding]] = {}
    for f in all_findings:
        by_file.setdefault(f.file_path, []).append(f)

    error_count = 0
    warning_count = 0

    for file_path in sorted(by_file.keys()):
        print(f"File: {file_path.relative_to(PROJECT_ROOT)}")
        for f in sorted(by_file[file_path], key=lambda x: x.line):
            prefix = f"{f.kind}: {f.code}"
            location = f"line {f.line}"
            if f.function:
                location += f", in {f.function}()"
            print(f"  {prefix} @ {location}")
            print(f"    {f.message}")
            if f.kind == "ERROR":
                error_count += 1
            else:
                warning_count += 1
        print("")

    print("Summary:")
    print(f"  Errors : {error_count}")
    print(f"  Warnings: {warning_count}")
    print("")
    print("Note: Gate 1 is currently in REPORT-ONLY mode (v1.1).")
    print("      Exit code is always 0. Future versions may block on ERROR findings.")


def main() -> None:
    files = collect_files()
    all_findings: List[Finding] = []
    for path in files:
        all_findings.extend(analyze_file(path))
    print_report(all_findings)
    # v1.1: always exit 0 (report-only)
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
API Database Access Firewall
=============================

AST-based static analysis to enforce governance-compliant database access.
Prevents direct Neo4j driver instantiation and imports in the API layer.

Constitutional Authority:
- AGENTS.md Section 1-A: Canonical Neo4j Connection
- CONSTITUTION.md Section 7: Source of Truth Principle
- docs/governance/API_DATABASE_ACCESS_AUDIT.md

Exit Codes:
- 0: All checks passed (governance compliant)
- 1: Violations detected (CI failure)
- 2: Script error or configuration issue
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple, Set, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ViolationSeverity(Enum):
    """Severity levels for governance violations"""
    P0_CRITICAL = "P0-CRITICAL"  # Blocks merge
    P1_HIGH = "P1-HIGH"  # Warning, should fix
    P2_MEDIUM = "P2-MEDIUM"  # Advisory


@dataclass
class Violation:
    """Represents a detected governance violation"""
    file_path: str
    line_number: int
    column: int
    severity: ViolationSeverity
    rule_id: str
    message: str
    code_snippet: Optional[str] = None


class DatabaseAccessFirewall(ast.NodeVisitor):
    """
    AST visitor that detects forbidden database access patterns.
    
    Forbidden patterns in api/ directory:
    1. Direct neo4j imports: `from neo4j import GraphDatabase`
    2. Direct driver creation: `GraphDatabase.driver()` or `AsyncGraphDatabase.driver()`
    3. Raw session access: `driver.session()`
    
    Allowed patterns:
    - Import from canonical layer: `from mahoun.graph.neo4j.connection import ...`
    - Using canonical factories: `get_connection()`, `initialize_canonical_async_driver()`
    """
    
    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.violations: List[Violation] = []
    
    def visit_Import(self, node: ast.Import) -> None:
        """Check for forbidden `import neo4j` statements"""
        for alias in node.names:
            if alias.name == 'neo4j' or alias.name.startswith('neo4j.'):
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    column=node.col_offset,
                    severity=ViolationSeverity.P0_CRITICAL,
                    rule_id="API-DB-001",
                    message=(
                        f"Forbidden direct neo4j import: 'import {alias.name}'. "
                        f"Use 'from mahoun.graph.neo4j.connection import ...' instead."
                    ),
                    code_snippet=self._get_code_snippet(node.lineno)
                ))
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for forbidden `from neo4j import ...` statements"""
        if node.module and (node.module == 'neo4j' or node.module.startswith('neo4j.')):
            # Exception: Importing from canonical connection layer is allowed
            # (it re-exports neo4j types for typing purposes)
            if 'mahoun.graph.neo4j.connection' not in self.file_path:
                imported_names = [alias.name for alias in node.names]
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    column=node.col_offset,
                    severity=ViolationSeverity.P0_CRITICAL,
                    rule_id="API-DB-002",
                    message=(
                        f"Forbidden direct neo4j import: 'from {node.module} import {', '.join(imported_names)}'. "
                        f"All Neo4j access must route through mahoun.graph.neo4j.connection."
                    ),
                    code_snippet=self._get_code_snippet(node.lineno)
                ))
        
        # NEW: Check for imports of raw driver objects from API database layer
        if node.module == 'api.database':
            imported_names = [alias.name for alias in node.names]
            forbidden_imports = [name for name in imported_names if 'driver' in name.lower() or name in ('neo4j_driver', 'async_driver')]
            if forbidden_imports:
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    column=node.col_offset,
                    severity=ViolationSeverity.P0_CRITICAL,
                    rule_id="API-DB-004", 
                    message=(
                        f"Forbidden driver import from API layer: 'from api.database import {', '.join(forbidden_imports)}'. "
                        f"Use 'from mahoun.graph.neo4j.connection import get_connection' instead."
                    ),
                    code_snippet=self._get_code_snippet(node.lineno)
                ))
        
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Check for forbidden driver instantiation calls"""
        # Pattern: GraphDatabase.driver(...) or AsyncGraphDatabase.driver(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'driver':
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id in ('GraphDatabase', 'AsyncGraphDatabase'):
                        self.violations.append(Violation(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            severity=ViolationSeverity.P0_CRITICAL,
                            rule_id="API-DB-003",
                            message=(
                                f"Forbidden direct driver instantiation: '{node.func.value.id}.driver()'. "
                                f"Use 'initialize_canonical_async_driver()' from mahoun.graph.neo4j.connection instead."
                            ),
                            code_snippet=self._get_code_snippet(node.lineno)
                        ))
        
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check for raw driver.session() access"""
        # Pattern: some_driver.session()
        if node.attr == 'session':
            # Check if this is accessing session on a driver-like object
            # This is a heuristic - look for variable names containing 'driver'
            if isinstance(node.value, ast.Name):
                if 'driver' in node.value.id.lower():
                    # Don't flag usage inside canonical connection module
                    if 'mahoun/graph/neo4j/connection.py' in self.file_path:
                        self.generic_visit(node)
                        return
                    
                    # Check for documented bootstrap exemption
                    # Look for "BOOTSTRAP EXEMPTION" comment in surrounding lines
                    exemption_found = False
                    context_start = max(0, node.lineno - 10)
                    context_end = min(len(self.source_lines), node.lineno + 2)
                    
                    for i in range(context_start, context_end):
                        if 'BOOTSTRAP EXEMPTION' in self.source_lines[i]:
                            exemption_found = True
                            break
                    
                    if not exemption_found:
                        self.violations.append(Violation(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            severity=ViolationSeverity.P1_HIGH,
                            rule_id="API-DB-004",
                            message=(
                                f"Suspicious raw session access: '{node.value.id}.session'. "
                                f"Verify this routes through GovernedNeo4jSession or add BOOTSTRAP EXEMPTION comment."
                            ),
                            code_snippet=self._get_code_snippet(node.lineno)
                        ))
        
        self.generic_visit(node)
    
    def _get_code_snippet(self, line_number: int, context_lines: int = 2) -> str:
        """Extract code snippet with context"""
        start = max(0, line_number - context_lines - 1)
        end = min(len(self.source_lines), line_number + context_lines)
        
        snippet_lines = []
        for i in range(start, end):
            prefix = ">>>" if i == line_number - 1 else "   "
            snippet_lines.append(f"{prefix} {i+1:4d} | {self.source_lines[i]}")
        
        return "\n".join(snippet_lines)


def scan_file(file_path: Path) -> List[Violation]:
    """
    Scan a single Python file for database access violations
    
    Args:
        file_path: Path to Python file to scan
    
    Returns:
        List of detected violations
    """
    try:
        source_code = file_path.read_text(encoding='utf-8')
        tree = ast.parse(source_code, filename=str(file_path))
        
        firewall = DatabaseAccessFirewall(str(file_path), source_code)
        firewall.visit(tree)
        
        return firewall.violations
        
    except SyntaxError as e:
        return [Violation(
            file_path=str(file_path),
            line_number=e.lineno or 0,
            column=e.offset or 0,
            severity=ViolationSeverity.P2_MEDIUM,
            rule_id="API-DB-SYN",
            message=f"Syntax error in file (skipping): {e}",
            code_snippet=None
        )]
    except Exception as e:
        return [Violation(
            file_path=str(file_path),
            line_number=0,
            column=0,
            severity=ViolationSeverity.P2_MEDIUM,
            rule_id="API-DB-ERR",
            message=f"Error scanning file: {e}",
            code_snippet=None
        )]


def scan_directory(
    directory: Path,
    *,
    exclude_patterns: Optional[List[str]] = None
) -> Dict[str, List[Violation]]:
    """
    Recursively scan directory for violations
    
    Args:
        directory: Root directory to scan
        exclude_patterns: List of path patterns to exclude (e.g., ['test_', '__pycache__'])
    
    Returns:
        Dictionary mapping file paths to their violations
    """
    exclude_patterns = exclude_patterns or ['test_', '__pycache__', '.pyc', 'venv/', '.git/']
    
    results: Dict[str, List[Violation]] = {}
    
    for py_file in directory.rglob('*.py'):
        # Skip excluded paths
        if any(pattern in str(py_file) for pattern in exclude_patterns):
            continue
        
        violations = scan_file(py_file)
        if violations:
            results[str(py_file.relative_to(directory))] = violations
    
    return results


def format_violation_report(
    violations_by_file: Dict[str, List[Violation]],
    *,
    show_snippets: bool = True
) -> str:
    """Format violations into a human-readable report"""
    lines = []
    
    # Count by severity
    severity_counts = {severity: 0 for severity in ViolationSeverity}
    for violations in violations_by_file.values():
        for v in violations:
            severity_counts[v.severity] += 1
    
    total_violations = sum(severity_counts.values())
    
    # Header
    lines.append("=" * 80)
    lines.append("API DATABASE ACCESS FIREWALL - VIOLATION REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    if total_violations == 0:
        lines.append("✅ NO VIOLATIONS DETECTED - Governance compliant!")
        lines.append("")
        return "\n".join(lines)
    
    # Summary
    lines.append(f"⚠️  VIOLATIONS DETECTED: {total_violations} total")
    lines.append("")
    for severity, count in severity_counts.items():
        if count > 0:
            icon = "🔴" if severity == ViolationSeverity.P0_CRITICAL else "🟡" if severity == ViolationSeverity.P1_HIGH else "🔵"
            lines.append(f"  {icon} {severity.value}: {count}")
    lines.append("")
    lines.append("-" * 80)
    lines.append("")
    
    # Detailed violations
    for file_path, violations in sorted(violations_by_file.items()):
        lines.append(f"📄 {file_path}")
        lines.append("")
        
        for v in violations:
            lines.append(f"  [{v.severity.value}] {v.rule_id} at line {v.line_number}:{v.column}")
            lines.append(f"  {v.message}")
            
            if show_snippets and v.code_snippet:
                lines.append("")
                for snippet_line in v.code_snippet.split('\n'):
                    lines.append(f"    {snippet_line}")
            
            lines.append("")
        
        lines.append("-" * 80)
        lines.append("")
    
    # Remediation guidance
    lines.append("REMEDIATION GUIDANCE:")
    lines.append("")
    lines.append("1. Replace `from neo4j import ...` with:")
    lines.append("   from mahoun.graph.neo4j.connection import get_connection, initialize_canonical_async_driver")
    lines.append("")
    lines.append("2. Replace `AsyncGraphDatabase.driver(...)` with:")
    lines.append("   driver = await initialize_canonical_async_driver(uri, auth, **config)")
    lines.append("")
    lines.append("3. Replace raw `driver.session()` with:")
    lines.append("   connection = get_connection()")
    lines.append("   result = connection.execute_query(query)  # for reads")
    lines.append("   session = connection.governed_session()   # for writes")
    lines.append("")
    lines.append("See: docs/governance/API_DATABASE_ACCESS_AUDIT.md")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def main() -> int:
    """Main entry point for firewall enforcement"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enforce governance-compliant database access in API layer"
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default='api',
        help='Directory to scan (default: api)'
    )
    parser.add_argument(
        '--exclude',
        nargs='*',
        default=['test_', '__pycache__'],
        help='Patterns to exclude from scanning'
    )
    parser.add_argument(
        '--no-snippets',
        action='store_true',
        help='Disable code snippet display in report'
    )
    parser.add_argument(
        '--fail-on',
        choices=['P0', 'P1', 'P2', 'none'],
        default='P0',
        help='Severity level to fail CI on (default: P0)'
    )
    
    args = parser.parse_args()
    
    # Resolve directory
    workspace_root = Path(__file__).parent.parent.parent
    scan_dir = workspace_root / args.directory
    
    if not scan_dir.exists():
        print(f"❌ Error: Directory not found: {scan_dir}", file=sys.stderr)
        return 2
    
    # Scan directory
    print(f"🔍 Scanning {scan_dir} for governance violations...", file=sys.stderr)
    violations_by_file = scan_directory(scan_dir, exclude_patterns=args.exclude)
    
    # Generate report
    report = format_violation_report(
        violations_by_file,
        show_snippets=not args.no_snippets
    )
    print(report)
    
    # Determine exit code based on severity
    has_p0 = any(
        v.severity == ViolationSeverity.P0_CRITICAL
        for violations in violations_by_file.values()
        for v in violations
    )
    has_p1 = any(
        v.severity == ViolationSeverity.P1_HIGH
        for violations in violations_by_file.values()
        for v in violations
    )
    has_p2 = any(
        v.severity == ViolationSeverity.P2_MEDIUM
        for violations in violations_by_file.values()
        for v in violations
    )
    
    if args.fail_on == 'none':
        return 0
    elif args.fail_on == 'P2' and (has_p2 or has_p1 or has_p0):
        return 1
    elif args.fail_on == 'P1' and (has_p1 or has_p0):
        return 1
    elif args.fail_on == 'P0' and has_p0:
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

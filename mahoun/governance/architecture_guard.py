"""
MAHOUN Architecture Guard
=========================

Constitutional Architecture Enforcement Layer

Responsibilities:
- Detect forbidden imports using AST analysis
- Detect layer violations (Tier-0 importing from higher tiers)
- Detect governance bypass attempts
- Detect duplicate symbols across critical modules
- Enforce architecture boundaries defined in kernel.manifest.yaml

Architecture:
- Tier-1 component (depends on Tier-0 for read-only inspection only)
- Uses Python AST for semantic analysis (not just grep)
- Fail-closed: any violation causes immediate exit with code 1

Detection Capabilities:
1. Forbidden imports (blacklist)
2. Layer violations (Tier-0 importing from Tier-1, Tier-2, Tier-3)
3. Governance bypass detection
4. Duplicate symbol detection
5. Raw session/direct database access detection
"""

import ast
import argparse
import os
import re
import sys
import yaml
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional, Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST_PATH = os.path.join(ROOT_DIR, "constitution", "kernel.manifest.yaml")


class ArchitectureGuardError(Exception):
    """Base exception for architecture guard violations."""
    pass


class ForbiddenImportError(ArchitectureGuardError):
    """Raised when a forbidden import is detected."""
    pass


class LayerViolationError(ArchitectureGuardError):
    """Raised when a layer violation is detected."""
    pass


class GovernanceBypassError(ArchitectureGuardError):
    """Raised when a governance bypass attempt is detected."""
    pass


class DuplicateSymbolError(ArchitectureGuardError):
    """Raised when duplicate symbols are detected."""
    pass


def load_manifest() -> Dict[str, Any]:
    """Load and validate the kernel manifest."""
    if not os.path.exists(MANIFEST_PATH):
        print(f"ARCHITECTURE_GUARD_ERROR: Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)
    
    try:
        with open(MANIFEST_PATH, "r") as f:
            manifest = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ARCHITECTURE_GUARD_ERROR: Invalid YAML in manifest: {e}")
        sys.exit(1)
    
    if not manifest or not isinstance(manifest, dict):
        print("ARCHITECTURE_GUARD_ERROR: Manifest is empty or invalid")
        sys.exit(1)
    
    return manifest


def get_file_path_module(filepath: str) -> str:
    """Convert a file path to a module path."""
    # Remove .py extension
    if filepath.endswith(".py"):
        filepath = filepath[:-3]
    
    # Convert path separators to dots
    module_path = filepath.replace("/", ".")
    
    # Remove leading dots
    while module_path.startswith("."):
        module_path = module_path[1:]
    
    return module_path


def is_governance_tooling_file(filepath: str) -> bool:
    """
    Check if a file is part of the governance tooling (Tier-1).
    
    These files are allowed to contain bypass detection logic without being flagged.
    
    Args:
        filepath: The file path to check
        
    Returns:
        True if the file is governance tooling, False otherwise
    """
    governance_tooling_files = [
        "mahoun/governance/architecture_guard.py",
        "mahoun/governance/kernel_guard.py",
        "mahoun/governance/api_guard.py",
        "mahoun/governance/",  # Any file in the governance directory
    ]
    
    for pattern in governance_tooling_files:
        if pattern in filepath:
            return True
    
    return False


def extract_imports_from_ast(tree: ast.AST, filepath: str) -> Dict[str, List[Tuple[int, str]]]:
    """
    Extract all imports from an AST tree.
    
    Returns:
        Dict mapping import names to list of (line_number, alias) tuples
    """
    imports = defaultdict(list)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_name = alias.name
                as_name = alias.asname or alias.name
                imports[import_name].append((node.lineno, as_name))
        
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                import_name = f"{module}.{alias.name}" if module else alias.name
                as_name = alias.asname or alias.name
                imports[import_name].append((node.lineno, as_name))
    
    return dict(imports)


def extract_defined_symbols(tree: ast.AST) -> Dict[str, List[int]]:
    """
    Extract all defined symbols (classes, functions, variables) from AST.
    
    Returns:
        Dict mapping symbol names to list of line numbers where defined
    """
    symbols = defaultdict(list)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols[node.name].append(node.lineno)
        elif isinstance(node, ast.FunctionDef):
            symbols[node.name].append(node.lineno)
        elif isinstance(node, ast.AsyncFunctionDef):
            symbols[node.name].append(node.lineno)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            # Variable assignment
            symbols[node.id].append(node.lineno)
    
    return dict(symbols)


def extract_string_patterns(tree: ast.AST) -> List[Tuple[int, str]]:
    """Extract all string literals from AST."""
    strings = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append((node.lineno, node.value))
        elif isinstance(node, ast.Str):  # Python 3.7 compatibility
            strings.append((node.lineno, node.s))
    
    return strings


def check_forbidden_imports(
    filepath: str, 
    manifest: Dict[str, Any]
) -> List[str]:
    """
    Check for forbidden imports in a file.
    
    Args:
        filepath: Path to the file to check
        manifest: The kernel manifest
    
    Returns:
        List of violation messages
    """
    abs_path = os.path.join(ROOT_DIR, filepath)
    
    if not os.path.exists(abs_path):
        return [f"ARCHITECTURE_GUARD_WARNING: File not found: {filepath}"]
    
    # Determine which tier this file belongs to
    tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
    tier_1_files = manifest.get("tiers", {}).get("tier_1", {}).get("protected_files", [])
    
    # Get forbidden imports for the appropriate tier
    forbidden_imports = []
    if filepath in tier_0_files:
        forbidden_imports = manifest.get("boundaries", {}).get("forbidden_imports", {}).get("tier_0", [])
    elif filepath in tier_1_files:
        forbidden_imports = manifest.get("tiers", {}).get("tier_1", {}).get("forbidden_imports", [])
    else:
        # File not in any tier, use Tier-0 rules by default
        forbidden_imports = manifest.get("boundaries", {}).get("forbidden_imports", {}).get("tier_0", [])
    
    if not forbidden_imports:
        return []
    
    violations = []
    
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
        return [f"ARCHITECTURE_GUARD_ERROR: Failed to parse {filepath}: {e}"]
    
    imports = extract_imports_from_ast(tree, filepath)
    
    for import_name, occurrences in imports.items():
        for forbidden in forbidden_imports:
            # Exact match
            if import_name == forbidden:
                for lineno, alias in occurrences:
                    violations.append(
                        f"FORBIDDEN_IMPORT: '{import_name}' (as '{alias}') in {filepath}:{lineno}"
                    )
            # Prefix match (e.g., forbidding "neo4j" matches "neo4j.driver")
            elif import_name.startswith(forbidden + "."):
                for lineno, alias in occurrences:
                    violations.append(
                        f"FORBIDDEN_IMPORT: '{import_name}' (prefix '{forbidden}') (as '{alias}') in {filepath}:{lineno}"
                    )
            # Substring match for modules like "mahoun.governance"
            elif forbidden in import_name.split("."):
                for lineno, alias in occurrences:
                    violations.append(
                        f"FORBIDDEN_IMPORT: '{import_name}' (contains '{forbidden}') (as '{alias}') in {filepath}:{lineno}"
                    )
    
    return violations


def check_layer_violations(
    filepath: str,
    manifest: Dict[str, Any]
) -> List[str]:
    """
    Check for layer violations (Tier-0 importing from higher tiers).
    
    Args:
        filepath: Path to the file to check
        manifest: The kernel manifest
    
    Returns:
        List of violation messages
    """
    abs_path = os.path.join(ROOT_DIR, filepath)
    
    if not os.path.exists(abs_path):
        return []
    
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
        return [f"ARCHITECTURE_GUARD_ERROR: Failed to parse {filepath}: {e}"]
    
    violations = []
    file_module = get_file_path_module(filepath)
    
    # Check if this is a Tier-0 file
    tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
    
    if filepath not in tier_0_files:
        # Only check Tier-0 files for layer violations
        return []
    
    imports = extract_imports_from_ast(tree, filepath)
    
    # Get forbidden layers for Tier-0
    forbidden_layers = manifest.get("boundaries", {}).get("layer_violations", {}).get("forbidden_layers_for_tier_0", [])
    
    # Also check tier boundary violations
    tier_boundary_violations = manifest.get("boundaries", {}).get("tier_boundary_violations", {}).get("tier_0_cannot_import", [])
    
    all_forbidden = forbidden_layers + tier_boundary_violations
    
    for import_name, occurrences in imports.items():
        for forbidden in all_forbidden:
            # Check if import is from a forbidden layer
            if forbidden in import_name.split("."):
                for lineno, alias in occurrences:
                    violations.append(
                        f"LAYER_VIOLATION: Tier-0 file '{filepath}' imports from forbidden layer '{forbidden}' in {filepath}:{lineno}"
                    )
    
    return violations


def check_governance_bypass(
    filepath: str,
    manifest: Dict[str, Any]
) -> List[str]:
    """
    Check for governance bypass patterns.
    
    Detects:
    - Raw database sessions
    - Unauthorized execution paths
    - Bypass patterns in code
    
    Args:
        filepath: Path to the file to check
        manifest: The kernel manifest
    
    Returns:
        List of violation messages
    """
    abs_path = os.path.join(ROOT_DIR, filepath)
    
    if not os.path.exists(abs_path):
        return []
    
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
        return [f"ARCHITECTURE_GUARD_ERROR: Failed to parse {filepath}: {e}"]
    
    violations = []
    
    # Get bypass detection configuration
    detection_config = manifest.get("detection", {}).get("governance_bypass", {})
    patterns = detection_config.get("patterns", [])
    detect_raw_sessions = detection_config.get("detect_raw_sessions", True)
    detect_direct_db = detection_config.get("detect_direct_database_access", True)
    detect_unauthorized_exec = detection_config.get("detect_unauthorized_execution", True)
    
    # Check for pattern matches in code (skip comments, docstrings, and string literals)
    if patterns:
        # Context-aware: Skip pattern matching for governance tooling files
        if not is_governance_tooling_file(filepath):
            for lineno, line in enumerate(source.splitlines(), 1):
                # Skip empty lines and lines that are only whitespace
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                
                # Skip comment-only lines
                if stripped_line.startswith("#"):
                    continue
                
                # Skip docstring lines (lines starting with """ or ''')
                if stripped_line.startswith('"""') or stripped_line.startswith("'''"):
                    continue
                
                # Skip string literals (lines that look like string assignments or definitions)
                # This is a simple heuristic - lines that start with quotes or have string patterns
                if (stripped_line.startswith('"') and stripped_line.endswith('"')) or \
                   (stripped_line.startswith("'") and stripped_line.endswith("'")):
                    # Could be a string literal assignment
                    if "=" in stripped_line and not "==" in stripped_line:
                        # Likely a string assignment, skip it
                        continue
                
                for pattern in patterns:
                    if re.search(pattern, stripped_line, re.IGNORECASE):
                        violations.append(
                            f"GOVERNANCE_BYPASS_PATTERN: Pattern '{pattern}' matched in {filepath}:{lineno}"
                        )
    
    # Check for raw session creation
    if detect_raw_sessions:
        # Context-aware: Skip raw session detection for governance tooling files
        # (they may need to analyze session patterns in other code)
        if not is_governance_tooling_file(filepath):
            session_patterns = [
                r"\bSession\s*\(",
                r"\bcreate_session\s*\(",
                r"\bget_session\s*\(",
                r"\bengine\.connect\s*\(",
            ]
            
            for lineno, line in enumerate(source.splitlines(), 1):
                for pattern in session_patterns:
                    try:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append(
                                f"RAW_SESSION_DETECTED: Potential raw session creation in {filepath}:{lineno}"
                            )
                    except re.error:
                        # Skip invalid regex patterns
                        pass
    
    # Check for direct database access
    if detect_direct_db:
        # Context-aware: Skip direct DB access detection for governance tooling files
        if not is_governance_tooling_file(filepath):
            db_patterns = [
                r"\bexecute\s*\(",
                r"\braw\s*\(",
                r"\btext\s*\(",
            ]
            
            for lineno, line in enumerate(source.splitlines(), 1):
                for pattern in db_patterns:
                    if re.search(r"\." + pattern, line, re.IGNORECASE):
                        violations.append(
                            f"DIRECT_DB_ACCESS: Potential direct database access in {filepath}:{lineno}"
                        )
    
    # Check AST for specific function calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for function calls
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            
            # Context-aware bypass detection: Skip if this is in governance tooling files
            # that are responsible for detecting bypasses
            if is_governance_tooling_file(filepath):
                continue
            
            bypass_keywords = ["bypass", "disable", "override", "skip", "circumvent"]
            for keyword in bypass_keywords:
                if keyword in func_name.lower() and "governance" in func_name.lower():
                    violations.append(
                        f"GOVERNANCE_BYPASS_FUNCTION: Suspicious function '{func_name}' in {filepath}:{node.lineno}"
                    )
    
    return violations


def check_duplicate_symbols(
    filepath: str,
    manifest: Dict[str, Any],
    all_symbols: Dict[str, Dict[str, List[int]]]
) -> List[str]:
    """
    Check for duplicate symbols across critical modules.
    
    Args:
        filepath: Current file path
        manifest: The kernel manifest
        all_symbols: Accumulated symbols from all files
    
    Returns:
        List of violation messages
    """
    abs_path = os.path.join(ROOT_DIR, filepath)
    
    if not os.path.exists(abs_path):
        return []
    
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
        return [f"ARCHITECTURE_GUARD_ERROR: Failed to parse {filepath}: {e}"]
    
    violations = []
    
    # Get duplicate detection configuration
    detection_config = manifest.get("detection", {}).get("duplicate_symbols", {})
    forbidden_duplicates = detection_config.get("forbidden_duplicates", [])
    
    # Extract symbols from this file
    current_symbols = extract_defined_symbols(tree)
    
    # Store symbols by file
    file_symbols = {filepath: current_symbols}
    
    # Check for duplicates with previously processed files
    for prev_file, prev_symbols in all_symbols.items():
        for symbol, lines in current_symbols.items():
            if symbol in prev_symbols and symbol in forbidden_duplicates:
                violations.append(
                    f"DUPLICATE_SYMBOL: '{symbol}' defined in both {prev_file} and {filepath}"
                )
    
    return violations


def verify_architecture(manifest: Dict[str, Any]) -> bool:
    """
    Main architecture verification function.
    
    Checks all protected files for:
    1. Forbidden imports
    2. Layer violations
    3. Governance bypass attempts
    4. Duplicate symbols
    
    Args:
        manifest: The kernel manifest
    
    Returns:
        True if all checks pass
    
    Raises:
        SystemExit: If violations are found (exit code 1)
    """
    # Get all files to check
    tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
    tier_1_files = manifest.get("tiers", {}).get("tier_1", {}).get("protected_files", [])
    
    all_check_files = tier_0_files + tier_1_files
    
    # Filter to only Python files
    python_files = [f for f in all_check_files if f.endswith(".py")]
    
    if not python_files:
        print("ARCHITECTURE_GUARD_WARNING: No Python files to check")
        return True
    
    all_violations = []
    all_symbols: Dict[str, Dict[str, List[int]]] = {}
    
    print(f"Checking {len(python_files)} files for architecture violations...")
    
    for filepath in python_files:
        print(f"  Checking: {filepath}")
        
        # Check forbidden imports
        violations = check_forbidden_imports(filepath, manifest)
        all_violations.extend(violations)
        
        # Check layer violations
        violations = check_layer_violations(filepath, manifest)
        all_violations.extend(violations)
        
        # Check governance bypass
        violations = check_governance_bypass(filepath, manifest)
        all_violations.extend(violations)
        
        # Extract symbols for duplicate checking
        abs_path = os.path.join(ROOT_DIR, filepath)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source, filename=filepath)
                symbols = extract_defined_symbols(tree)
                all_symbols[filepath] = symbols
            except Exception:
                pass
    
    # Check for duplicate symbols across all files
    for filepath in python_files:
        violations = check_duplicate_symbols(filepath, manifest, all_symbols)
        all_violations.extend(violations)
    
    # Report results
    if all_violations:
        print("\n" + "=" * 70)
        print("ARCHITECTURE_VIOLATION:")
        print("=" * 70)
        
        # Group violations by type
        forbidden_imports = [v for v in all_violations if v.startswith("FORBIDDEN_IMPORT")]
        layer_violations = [v for v in all_violations if v.startswith("LAYER_VIOLATION")]
        bypass_violations = [v for v in all_violations if "BYPASS" in v or "GOVERNANCE" in v]
        duplicate_violations = [v for v in all_violations if v.startswith("DUPLICATE_SYMBOL")]
        
        if forbidden_imports:
            print(f"\nForbidden Imports ({len(forbidden_imports)}):")
            for v in forbidden_imports:
                print(f"  - {v}")
        
        if layer_violations:
            print(f"\nLayer Violations ({len(layer_violations)}):")
            for v in layer_violations:
                print(f"  - {v}")
        
        if bypass_violations:
            print(f"\nGovernance Bypass Attempts ({len(bypass_violations)}):")
            for v in bypass_violations:
                print(f"  - {v}")
        
        if duplicate_violations:
            print(f"\nDuplicate Symbols ({len(duplicate_violations)}):")
            for v in duplicate_violations:
                print(f"  - {v}")
        
        print("\n" + "=" * 70)
        print(f"TOTAL VIOLATIONS: {len(all_violations)}")
        print("=" * 70)
        
        sys.exit(1)
    else:
        print("\nArchitecture verified successfully.")
        return True


def check_specific_file(filepath: str, manifest: Dict[str, Any]) -> List[str]:
    """
    Check a specific file for architecture violations.
    
    Args:
        filepath: Path to the file to check
        manifest: The kernel manifest
    
    Returns:
        List of violation messages
    """
    violations = []
    
    # Check forbidden imports
    violations.extend(check_forbidden_imports(filepath, manifest))
    
    # Check layer violations
    violations.extend(check_layer_violations(filepath, manifest))
    
    # Check governance bypass
    violations.extend(check_governance_bypass(filepath, manifest))
    
    return violations


def main():
    """Main entry point for architecture guard CLI."""
    parser = argparse.ArgumentParser(
        description="MAHOUN Architecture Guard - Architecture Enforcement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m mahoun.governance.architecture_guard --verify
  python -m mahoun.governance.architecture_guard --check-file mahoun/core/some_file.py
  python -m mahoun.governance.architecture_guard --check-imports
  python -m mahoun.governance.architecture_guard --check-bypass
        """
    )
    
    parser.add_argument(
        "--verify", 
        action="store_true", 
        help="Verify architecture for all protected files"
    )
    parser.add_argument(
        "--check-file",
        type=str,
        help="Check a specific file for violations"
    )
    parser.add_argument(
        "--check-imports",
        action="store_true",
        help="Check only for forbidden imports"
    )
    parser.add_argument(
        "--check-layers",
        action="store_true",
        help="Check only for layer violations"
    )
    parser.add_argument(
        "--check-bypass",
        action="store_true",
        help="Check only for governance bypass attempts"
    )
    parser.add_argument(
        "--check-duplicates",
        action="store_true",
        help="Check only for duplicate symbols"
    )
    
    args = parser.parse_args()
    
    if not any([
        args.verify, args.check_file, args.check_imports,
        args.check_layers, args.check_bypass, args.check_duplicates
    ]):
        parser.print_help()
        sys.exit(1)
    
    manifest = load_manifest()
    
    try:
        if args.verify:
            verify_architecture(manifest)
        
        elif args.check_file:
            violations = check_specific_file(args.check_file, manifest)
            if violations:
                print("\nViolations found:")
                for v in violations:
                    print(f"  - {v}")
                sys.exit(1)
            else:
                print(f"No violations found in {args.check_file}")
        
        elif args.check_imports:
            # Check all files for forbidden imports only
            tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
            all_violations = []
            for filepath in tier_0_files:
                if filepath.endswith(".py"):
                    all_violations.extend(check_forbidden_imports(filepath, manifest))
            
            if all_violations:
                print("Forbidden imports found:")
                for v in all_violations:
                    print(f"  - {v}")
                sys.exit(1)
            else:
                print("No forbidden imports found.")
        
        elif args.check_layers:
            # Check all files for layer violations only
            tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
            all_violations = []
            for filepath in tier_0_files:
                if filepath.endswith(".py"):
                    all_violations.extend(check_layer_violations(filepath, manifest))
            
            if all_violations:
                print("Layer violations found:")
                for v in all_violations:
                    print(f"  - {v}")
                sys.exit(1)
            else:
                print("No layer violations found.")
        
        elif args.check_bypass:
            # Check all files for governance bypass only
            tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
            all_violations = []
            for filepath in tier_0_files:
                if filepath.endswith(".py"):
                    all_violations.extend(check_governance_bypass(filepath, manifest))
            
            if all_violations:
                print("Governance bypass attempts found:")
                for v in all_violations:
                    print(f"  - {v}")
                sys.exit(1)
            else:
                print("No governance bypass attempts found.")
        
    except Exception as e:
        print(f"ARCHITECTURE_GUARD_ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

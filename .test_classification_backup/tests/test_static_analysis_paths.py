"""
Static Analysis Test: No Hardcoded Absolute Paths
=================================================
Property 8: No Hardcoded Absolute Paths

*For any* Python file in mahoun/ directory, the file SHALL NOT contain
hardcoded absolute paths (e.g., /home/, /Users/, /var/, /opt/).

**Validates: Requirements 5.1**
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple, Set

import pytest


# Patterns that indicate hardcoded absolute paths
ABSOLUTE_PATH_PATTERNS = [
    r'["\']\/home\/',           # Linux home directories
    r'["\']\/Users\/',          # macOS home directories
    r'["\']\/var\/',            # Linux var directories
    r'["\']\/opt\/',            # Linux opt directories
    r'["\']\/etc\/',            # Linux etc directories
    r'["\']\/tmp\/',            # Temp directories (should use tempfile)
    r'["\']\/usr\/',            # Linux usr directories
    r'["\']C:\\\\Users\\\\',    # Windows user directories
    r'["\']C:\\\\Program',      # Windows program directories
    r'["\']D:\\\\',             # Windows D drive
]

# Files/patterns to exclude from checking
EXCLUDED_PATTERNS = [
    '**/test_*.py',
    '**/*_test.py',
    '**/conftest.py',
    '**/__pycache__/**',
]

# Allowed exceptions (with justification)
ALLOWED_EXCEPTIONS: Set[str] = {
    # Example: '/etc/hosts' might be needed for network config
    # Add specific exceptions here with comments explaining why
}


def get_python_files(directory: Path) -> List[Path]:
    """Get all Python files in directory, excluding test files."""
    python_files = []
    
    for py_file in directory.rglob('*.py'):
        # Skip test files
        if any(py_file.match(pattern) for pattern in EXCLUDED_PATTERNS):
            continue
        
        # Skip __pycache__
        if '__pycache__' in str(py_file):
            continue
        
        python_files.append(py_file)
    
    return python_files


def find_hardcoded_paths(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Find hardcoded absolute paths in a Python file.
    
    Returns:
        List of (line_number, matched_pattern, line_content) tuples
    """
    violations = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception:
        return violations
    
    lines = content.split('\n')
    
    for line_num, line in enumerate(lines, start=1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        
        # Skip docstrings (simple heuristic)
        if stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        
        # Check each pattern
        for pattern in ABSOLUTE_PATH_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                # Check if it's in allowed exceptions
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    matched_text = match.group(0)
                    # Extract the full path if possible
                    path_match = re.search(r'["\']([^"\']+)["\']', line)
                    if path_match:
                        full_path = path_match.group(1)
                        if full_path in ALLOWED_EXCEPTIONS:
                            continue
                    
                    violations.append((line_num, pattern, line.strip()))
    
    return violations


def find_hardcoded_paths_ast(file_path: Path) -> List[Tuple[int, str]]:
    """
    Find hardcoded absolute paths using AST analysis.
    More accurate than regex for string literals.
    
    Returns:
        List of (line_number, path_value) tuples
    """
    violations = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
    except Exception:
        return violations
    
    class PathVisitor(ast.NodeVisitor):
        def visit_Constant(self, node: ast.Constant) -> None:
            if isinstance(node.value, str):
                value = node.value
                # Check for absolute paths
                if (value.startswith('/home/') or
                    value.startswith('/Users/') or
                    value.startswith('/var/') or
                    value.startswith('/opt/') or
                    value.startswith('/etc/') or
                    value.startswith('/tmp/') or
                    value.startswith('/usr/') or
                    value.startswith('C:\\Users\\') or
                    value.startswith('C:\\Program')):
                    
                    if value not in ALLOWED_EXCEPTIONS:
                        violations.append((node.lineno, value))
            
            self.generic_visit(node)
        
        # For Python < 3.8 compatibility
        def visit_Str(self, node: ast.Str) -> None:
            value = node.s
            if (value.startswith('/home/') or
                value.startswith('/Users/') or
                value.startswith('/var/') or
                value.startswith('/opt/') or
                value.startswith('/etc/') or
                value.startswith('/tmp/') or
                value.startswith('/usr/')):
                
                if value not in ALLOWED_EXCEPTIONS:
                    violations.append((node.lineno, value))
            
            self.generic_visit(node)
    
    visitor = PathVisitor()
    visitor.visit(tree)
    
    return violations


class TestNoHardcodedPaths:
    """
    Static analysis tests for Property 8: No Hardcoded Absolute Paths.
    
    **Feature: platform-hardening, Property 8: No Hardcoded Absolute Paths**
    **Validates: Requirements 5.1**
    """
    
    @pytest.fixture
    def mahoun_directory(self) -> Path:
        """Get the mahoun source directory."""
        # Find project root
        current = Path(__file__).parent
        while current != current.parent:
            if (current / 'mahoun').is_dir():
                return current / 'mahoun'
            current = current.parent
        
        # Fallback
        return Path('mahoun')
    
    def test_no_hardcoded_absolute_paths_regex(self, mahoun_directory: Path) -> None:
        """
        Test that no Python files contain hardcoded absolute paths (regex check).
        
        **Property 8: No Hardcoded Absolute Paths**
        *For any* Python file in mahoun/ directory, the file SHALL NOT contain
        hardcoded absolute paths.
        """
        if not mahoun_directory.exists():
            pytest.skip(f"Directory {mahoun_directory} not found")
        
        all_violations: List[Tuple[Path, int, str, str]] = []
        
        for py_file in get_python_files(mahoun_directory):
            violations = find_hardcoded_paths(py_file)
            for line_num, pattern, line in violations:
                all_violations.append((py_file, line_num, pattern, line))
        
        if all_violations:
            error_msg = "Found hardcoded absolute paths:\n"
            for file_path, line_num, pattern, line in all_violations:
                rel_path = file_path.relative_to(mahoun_directory.parent)
                error_msg += f"  {rel_path}:{line_num}: {line}\n"
            
            pytest.fail(error_msg)
    
    def test_no_hardcoded_absolute_paths_ast(self, mahoun_directory: Path) -> None:
        """
        Test that no Python files contain hardcoded absolute paths (AST check).
        
        More accurate than regex as it only checks actual string literals.
        """
        if not mahoun_directory.exists():
            pytest.skip(f"Directory {mahoun_directory} not found")
        
        all_violations: List[Tuple[Path, int, str]] = []
        
        for py_file in get_python_files(mahoun_directory):
            violations = find_hardcoded_paths_ast(py_file)
            for line_num, path_value in violations:
                all_violations.append((py_file, line_num, path_value))
        
        if all_violations:
            error_msg = "Found hardcoded absolute paths (AST analysis):\n"
            for file_path, line_num, path_value in all_violations:
                rel_path = file_path.relative_to(mahoun_directory.parent)
                error_msg += f"  {rel_path}:{line_num}: '{path_value}'\n"
            
            pytest.fail(error_msg)
    
    def test_config_files_use_env_vars(self) -> None:
        """
        Test that config files use environment variables for paths.
        """
        config_dir = Path('config')
        if not config_dir.exists():
            pytest.skip("Config directory not found")
        
        violations = []
        
        for config_file in config_dir.glob('*.json'):
            content = config_file.read_text(encoding='utf-8')
            
            # Check for absolute paths that aren't env var references
            for pattern in ABSOLUTE_PATH_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Check if it's inside an env var reference like ${VAR:-default}
                    if not re.search(r'\$\{[^}]+' + re.escape(match), content):
                        violations.append((config_file, match))
        
        if violations:
            error_msg = "Found hardcoded paths in config files:\n"
            for file_path, match in violations:
                error_msg += f"  {file_path}: {match}\n"
            
            pytest.fail(error_msg)
    
    def test_paths_are_relative_or_configurable(self, mahoun_directory: Path) -> None:
        """
        Test that Path() calls use relative paths or config values.
        """
        if not mahoun_directory.exists():
            pytest.skip(f"Directory {mahoun_directory} not found")
        
        violations = []
        
        for py_file in get_python_files(mahoun_directory):
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
            except Exception:
                continue
            
            class PathCallVisitor(ast.NodeVisitor):
                def visit_Call(self, node: ast.Call) -> None:
                    # Check for Path() calls
                    if isinstance(node.func, ast.Name) and node.func.id == 'Path':
                        if node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                path_value = arg.value
                                # Check if it's an absolute path
                                if path_value.startswith('/') and not path_value.startswith('/tmp'):
                                    if path_value not in ALLOWED_EXCEPTIONS:
                                        violations.append((py_file, node.lineno, path_value))
                    
                    self.generic_visit(node)
            
            visitor = PathCallVisitor()
            visitor.visit(tree)
        
        if violations:
            error_msg = "Found Path() calls with absolute paths:\n"
            for file_path, line_num, path_value in violations:
                rel_path = file_path.relative_to(mahoun_directory.parent)
                error_msg += f"  {rel_path}:{line_num}: Path('{path_value}')\n"
            
            pytest.fail(error_msg)


# =============================================================================
# CLI for manual checking
# =============================================================================

def main() -> None:
    """Run static analysis from command line."""
    import sys
    
    mahoun_dir = Path('mahoun')
    if not mahoun_dir.exists():
        print("Error: mahoun/ directory not found")
        sys.exit(1)
    
    print("Checking for hardcoded absolute paths...")
    print("=" * 60)
    
    total_violations = 0
    
    for py_file in get_python_files(mahoun_dir):
        # Regex check
        regex_violations = find_hardcoded_paths(py_file)
        
        # AST check
        ast_violations = find_hardcoded_paths_ast(py_file)
        
        if regex_violations or ast_violations:
            rel_path = py_file.relative_to(mahoun_dir.parent)
            print(f"\n{rel_path}:")
            
            for line_num, pattern, line in regex_violations:
                print(f"  Line {line_num} (regex): {line}")
                total_violations += 1
            
            for line_num, path_value in ast_violations:
                print(f"  Line {line_num} (AST): '{path_value}'")
                total_violations += 1
    
    print("\n" + "=" * 60)
    
    if total_violations == 0:
        print("✓ No hardcoded absolute paths found!")
        sys.exit(0)
    else:
        print(f"✗ Found {total_violations} violation(s)")
        sys.exit(1)


if __name__ == '__main__':
    main()
